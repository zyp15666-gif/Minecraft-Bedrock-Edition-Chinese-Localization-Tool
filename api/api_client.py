#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API客户端 - 负责与API的底层通信（发送请求、处理响应、重试）

重构版：使用 Provider 抽象层，将请求构建和响应解析委托给具体的 Provider。
"""

import threading
import time
from typing import Any, Dict, Optional

import requests

from api.providers import BaseProvider, get_provider
from core.log_manager import get_logger

logger = get_logger(__name__)


class APIClient:
    """API客户端 - 基于Provider模式的统一通信层（线程安全）"""

    def __init__(self, rate_limit_delay: Dict[str, float], retry_config: Dict[str, Any] = None):
        """初始化API客户端

        Args:
            rate_limit_delay: 速率限制延迟，键为API类型，值为延迟时间（秒）
            retry_config: 重试配置，可选键: max_retries, base_delay, max_delay, backoff_factor
        """
        self.rate_limit_delay = rate_limit_delay
        self.last_call_time: Dict[str, float] = {}
        rc = retry_config or {}
        self.max_retries = rc.get('max_retries', 3)
        self.base_delay = rc.get('base_delay', 1.0)
        self.max_delay = rc.get('max_delay', 10.0)
        self._backoff_factor = rc.get('backoff_factor', 2)
        self._provider_cache: Dict[str, BaseProvider] = {}
        self._provider_lock = threading.Lock()

    def _get_provider(self, api_config: Dict[str, Any]) -> BaseProvider:
        """获取或创建API配置对应的Provider实例（线程安全，带缓存）

        Args:
            api_config: API配置

        Returns:
            Provider实例
        """
        cache_key = api_config.get('name', 'unknown')
        with self._provider_lock:
            if cache_key not in self._provider_cache:
                self._provider_cache[cache_key] = get_provider(api_config)
            return self._provider_cache[cache_key]

    def translate(self, api_config: Dict[str, Any], text: str, is_test: bool = False, system_prompt: Optional[str] = None) -> Optional[str]:
        """执行单次API翻译请求（无重试，重试由APIManager统一处理）

        Args:
            api_config: API配置
            text: 待翻译文本
            is_test: 是否为测试模式
            system_prompt: 可选的自定义系统提示词，None则使用默认

        Returns:
            翻译结果

        Raises:
            requests.RequestException: 网络请求异常
        """
        if not text or not text.strip():
            return text

        api_name = api_config.get('name', 'unknown')
        self._enforce_rate_limit(api_name)

        provider = self._get_provider(api_config)
        api_url, headers, payload = provider.build_request(text, system_prompt, is_test)
        connect_timeout, read_timeout = provider.get_timeout(is_test)

        response = requests.post(
            api_url, headers=headers, json=payload,
            timeout=(connect_timeout, read_timeout))
        response.raise_for_status()

        result = response.json()
        translated = provider.parse_response(result)

        if not translated:
            top_keys = list(result.keys()) if isinstance(result, dict) else type(result).__name__
            logger.warning(f"API响应解析结果为空，API={api_config.get('name', api_name)}，顶层键={top_keys}")
            return ""

        return translated

    def _enforce_rate_limit(self, api_name: str):
        """强制执行速率限制

        Args:
            api_name: API名称
        """
        current_time = time.time()
        last_call = self.last_call_time.get(api_name, 0)

        if 'ollama' in api_name.lower():
            delay = self.rate_limit_delay.get('local_ollama', 0.0)
        else:
            delay = self.rate_limit_delay.get('default', 0.15)

        elapsed = current_time - last_call
        if elapsed < delay:
            wait_time = delay - elapsed
            time.sleep(wait_time)

        self.last_call_time[api_name] = time.time()

    def test_api_availability(self, api_config: Dict[str, Any]) -> bool:
        """测试API可用性

        Args:
            api_config: API配置

        Returns:
            API是否可用
        """
        try:
            test_text = "Hello, world!"
            result = self.translate(api_config, test_text, is_test=True)
            return bool(result and result != test_text)
        except Exception as e:
            logger.warning(f"API测试失败: {e}")
            return False
