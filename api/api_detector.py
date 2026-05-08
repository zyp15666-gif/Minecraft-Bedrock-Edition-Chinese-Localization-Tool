#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API检测模块 — 负责API配置构建、连通性测试和可用性检测

从 api_manager.py 拆分出来的独立组件，职责：
1. 根据 YAML 配置构建标准化 API 列表
2. 测试单个 API 是否可用
3. 并行检测所有已配置 API 并返回可用列表
"""

import copy
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

import requests

from core.log_manager import get_logger

logger = get_logger(__name__)


class APIDetector:
    """API检测器 — 构建API配置列表并检测可用性"""

    # 支持的云服务提供商列表
    CLOUD_PROVIDERS = ["deepseek", "qwen", "zhipu", "doubao"]

    def __init__(self, config: Dict[str, Any]):
        """
        初始化API检测器

        Args:
            config: 完整配置字典
        """
        self.config = config

    # ──────────── API 列表构建 ────────────

    def build_api_list(self) -> List[Dict[str, Any]]:
        """构建API列表（深拷贝以避免修改原始配置）

        从配置中提取所有 API 配置（包括 local_ollama 和云服务商），
        自动推断类型并为每个条目添加 type 字段，最后按优先级排序。

        Returns:
            排序后的 API 配置列表（深拷贝副本）
        """
        all_apis = []

        # 处理 local_ollama 配置
        local_ollama_configs = self.config.get("local_ollama", [])
        if isinstance(local_ollama_configs, list):
            for api in local_ollama_configs:
                api_copy = copy.deepcopy(api)
                api_copy["type"] = "local_ollama"
                all_apis.append(api_copy)

        # 云服务提供商列表
        for provider in self.CLOUD_PROVIDERS:
            apis = self.config.get(provider, [])
            if not isinstance(apis, list):
                logger.warning(f"配置项 {provider} 不是列表格式，已跳过")
                continue

            for api in apis:
                api_copy = copy.deepcopy(api)
                if "type" not in api_copy:
                    if provider == "zhipu":
                        api_copy["type"] = "zhipu"
                    elif provider == "doubao":
                        api_copy["type"] = "doubao"
                    else:
                        api_copy["type"] = "openai_compatible"
                all_apis.append(api_copy)

        # 过滤启用的 API 并按优先级排序
        enabled = [api for api in all_apis if api.get("enabled", True)]
        enabled.sort(key=lambda x: x.get("priority", 999))

        logger.info(f"已构建 {len(enabled)} 个可用 API 配置")
        return enabled

    # ──────────── 单个 API 测试 ────────────

    def test_single(self, api_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """测试单个API是否可用

        对所有类型都使用简单 HTTP 请求验证连通性，避免依赖完整翻译流程。

        Args:
            api_config: 单个 API 配置字典

        Returns:
            API配置（可用时）或 None（不可用时）
        """
        api_name = api_config.get("name", "unknown")
        model = api_config.get("model", "unknown")
        logger.info(f"检测 {api_name} ({model})...")

        try:
            if not api_config.get("api_key") or any(
                kw in api_config.get("api_key", "").lower()
                for kw in ["你的", "your", "your_key"]
            ):
                logger.warning(f"API [{api_name}] Key未配置")
                return None

            # 统一使用简单HTTP连通性测试，不依赖翻译流程
            return self._test_http_connectivity(api_config)

        except Exception as e:
            logger.warning(f"连接失败 [{api_name}]: {str(e)[:80]}")
            return None

    def _test_http_connectivity(self, api_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """统一的 HTTP 连通性测试方法（兼容所有类型 API）"""
        api_name = api_config.get("name", "unknown")
        try:
            test_url = api_config.get("api_url", "")
            if not test_url:
                logger.warning(f"{api_name} 未配置 api_url")
                return None

            headers = {"Content-Type": "application/json"}
            api_key = api_config.get("api_key", "")
            if api_key and "你的" not in api_key and "your" not in api_key.lower():
                headers["Authorization"] = f"Bearer {api_key}"

            # 使用最小化 payload 测试连通性（不要求完整翻译）
            payload = {
                "model": api_config.get("model", "gpt-3.5-turbo"),
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 2,
                "stream": False,
            }
            resp = requests.post(test_url, json=payload, headers=headers, timeout=10)

            if resp.status_code in (200, 400, 401, 429):  # 4xx表示 API 存在但可能参数或鉴权问题，但 API 是通的
                logger.info(f"{api_name} 可用 (状态码 {resp.status_code})")
                return api_config
            else:
                logger.warning(f"{api_name} 返回状态码 {resp.status_code}")
                return None

        except Exception as e:
            logger.warning(f"{api_name} 连接失败: {type(e).__name__}: {str(e)[:60]}")
            return None

    def _test_local_ollama(self, api_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """测试本地 Ollama API 是否可用（保留向后兼容）"""
        return self._test_http_connectivity(api_config)

    def _call_translate(self, api_config: Dict[str, Any], text: str) -> Optional[str]:
        """通过翻译调用测试API可用性

        注意：此方法需要在 APIManager 上下文中使用。
        当前作为占位，实际由外部传入的 translate 函数完成。
        """
        # 实际使用时通过回调注入翻译能力，保持 APIDetector 不依赖具体翻译逻辑
        if hasattr(self, '_translate_hook') and self._translate_hook:
            return self._translate_hook(api_config, text, is_test=True)
        return None

    def set_translate_hook(self, hook):
        """设置翻译钩子函数，用于测试云 API

        Args:
            hook: callable(api_config, text, is_test) -> str
        """
        self._translate_hook = hook

    # ──────────── 批量并行检测 ────────────

    def detect_available(self, translate_hook=None) -> List[Dict[str, Any]]:
        """检测所有可用的API（并行验证）

        构建 API 列表后，使用 ThreadPoolExecutor 并行测试每个 API，
        返回可用列表并同时记录到 self.available_apis。

        Args:
            translate_hook: 可选的翻译回调函数，用于测试云 API

        Returns:
            可用 API 配置列表
        """
        if translate_hook:
            self.set_translate_hook(translate_hook)

        logger.info("\n正在检测所有已配置的API...")
        logger.info("-" * 60)

        all_apis = self.build_api_list()
        logger.info(f"共配置 {len(all_apis)} 个API")

        available = []
        if all_apis:
            max_workers = min(len(all_apis), 6)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_api = {
                    executor.submit(self.test_single, api): api
                    for api in all_apis
                }
                for future in as_completed(future_to_api):
                    api = future_to_api[future]
                    try:
                        result = future.result()
                        if result:
                            available.append(result)
                    except Exception as e:
                        logger.error(
                            f"验证 {api.get('name', '未知API')} 时发生错误: {e}"
                        )

        logger.info("-" * 60)
        if available:
            logger.info(f"检测到 {len(available)} 个可用API:")
            for i, api in enumerate(available, 1):
                logger.info(f"   {i}. {api['name']} (模型: {api.get('model', 'N/A')})")
        else:
            logger.error("未检测到任何可用API，请检查网络和API配置！")

        return available
