#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
异步API客户端 - 使用aiohttp实现异步HTTP请求

提供与APIClient相同的接口，但使用异步执行，避免阻塞线程池。
"""

import asyncio
import time
from typing import Dict, Optional, Any
from core.log_manager import get_logger
from core.exceptions import (
    APIConnectionError, APITimeoutError, APIAuthError,
    APIRateLimitError, APIResponseError, classify_http_error
)
from api.providers import get_provider, BaseProvider

logger = get_logger(__name__)

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    logger.warning("aiohttp未安装，异步API客户端不可用。请运行: pip install aiohttp")


class AsyncAPIClient:
    """异步API客户端 - 使用aiohttp实现异步HTTP请求（避免阻塞线程池）"""

    def __init__(self, rate_limit_delay: Dict[str, float], retry_config: Dict[str, Any] = None):
        """初始化异步API客户端

        Args:
            rate_limit_delay: 速率限制延迟，键为API类型，值为延迟时间（秒）
            retry_config: 重试配置，可选键: max_retries, base_delay, max_delay, backoff_factor
        """
        if not AIOHTTP_AVAILABLE:
            raise ImportError("aiohttp未安装，无法使用异步API客户端")

        self.rate_limit_delay = rate_limit_delay
        self.last_call_time: Dict[str, float] = {}
        rc = retry_config or {}
        self.max_retries = rc.get('max_retries', 3)
        self.base_delay = rc.get('base_delay', 1.0)
        self.max_delay = rc.get('max_delay', 10.0)
        self._backoff_factor = rc.get('backoff_factor', 2)
        self._provider_cache: Dict[str, BaseProvider] = {}
        self._provider_lock = asyncio.Lock()
        self._rate_limit_lock = asyncio.Lock()

    async def _get_provider(self, api_config: Dict[str, Any]) -> BaseProvider:
        """获取或创建API配置对应的Provider实例（异步，带缓存）

        Args:
            api_config: API配置

        Returns:
            Provider实例
        """
        cache_key = api_config.get('name', 'unknown')
        async with self._provider_lock:
            if cache_key not in self._provider_cache:
                self._provider_cache[cache_key] = get_provider(api_config)
            return self._provider_cache[cache_key]

    async def translate(self, api_config: Dict[str, Any], text: str, is_test: bool = False, system_prompt: Optional[str] = None) -> Optional[str]:
        """执行单次API翻译请求（异步，无重试）

        Args:
            api_config: API配置
            text: 待翻译文本
            is_test: 是否为测试模式
            system_prompt: 可选的自定义系统提示词，None则使用默认

        Returns:
            翻译结果

        Raises:
            aiohttp.ClientError: 网络请求异常
        """
        if not text or not text.strip():
            return text

        api_name = api_config.get('name', 'unknown')
        await self._enforce_rate_limit(api_name)

        provider = await self._get_provider(api_config)
        api_url, headers, payload = provider.build_request(text, system_prompt, is_test)
        connect_timeout, read_timeout = provider.get_timeout(is_test)

        timeout = aiohttp.ClientTimeout(total=connect_timeout + read_timeout)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(api_url, headers=headers, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise aiohttp.ClientResponseError(
                        request_info=None,
                        history=None,
                        status=response.status,
                        message=error_text
                    )
                
                result = await response.json()
                translated = provider.parse_response(result)

                if not translated:
                    top_keys = list(result.keys()) if isinstance(result, dict) else type(result).__name__
                    logger.warning(f"API响应解析结果为空，API={api_config.get('name', api_name)}，顶层键={top_keys}")
                    return ""

                return translated

    async def _enforce_rate_limit(self, api_name: str):
        """强制执行速率限制（异步）

        Args:
            api_name: API名称
        """
        async with self._rate_limit_lock:
            current_time = time.time()
            last_call = self.last_call_time.get(api_name, 0)

            if 'ollama' in api_name.lower():
                delay = self.rate_limit_delay.get('local_ollama', 0.0)
            else:
                delay = self.rate_limit_delay.get('default', 0.15)

            elapsed = current_time - last_call
            if elapsed < delay:
                wait_time = delay - elapsed
                await asyncio.sleep(wait_time)

            self.last_call_time[api_name] = time.time()

    async def test_api_availability(self, api_config: Dict[str, Any]) -> bool:
        """测试API可用性（异步）

        Args:
            api_config: API配置

        Returns:
            API是否可用
        """
        try:
            test_text = "Hello, world!"
            result = await self.translate(api_config, test_text, is_test=True)
            return bool(result and result != test_text)
        except Exception as e:
            logger.warning(f"API测试失败: {e}")
            return False

    async def translate_batch(self, api_configs: list, texts: list, system_prompt: Optional[str] = None) -> list:
        """批量翻译（异步并发）

        Args:
            api_configs: API配置列表（每个文本对应一个API配置）
            texts: 待翻译文本列表
            system_prompt: 可选的自定义系统提示词

        Returns:
            翻译结果列表
        """
        tasks = [
            self.translate(api_config, text, system_prompt=system_prompt)
            for api_config, text in zip(api_configs, texts)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"批量翻译第{i}项失败: {result}")
                processed_results.append(None)
            else:
                processed_results.append(result)
        
        return processed_results
