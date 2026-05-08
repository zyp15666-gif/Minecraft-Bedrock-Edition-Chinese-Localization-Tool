#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API提供商模块

包含提供商注册表和工厂函数，统一管理各API提供商。
"""

from typing import Any, Dict, Type

from core.log_manager import get_logger

from .base import BaseProvider
from .doubao import DoubaoProvider
from .ollama import OllamaProvider
from .openai_compatible import OpenAICompatibleProvider
from .zhipu import ZhipuProvider

logger = get_logger(__name__)

PROVIDER_REGISTRY: Dict[str, Type] = {
    "local_ollama": OllamaProvider,
    "openai_compatible": OpenAICompatibleProvider,
    "openai": OpenAICompatibleProvider,
    "azure_openai": OpenAICompatibleProvider,
    "zhipu": ZhipuProvider,
    "doubao": DoubaoProvider,
}


def get_provider(api_config: Dict[str, Any]) -> BaseProvider:
    """根据API配置获取对应的提供商实例

    Args:
        api_config: API配置字典

    Returns:
        提供商实例

    Raises:
        ValueError: 不支持的API类型
    """
    api_type = api_config.get("type", "openai_compatible")
    provider_class = PROVIDER_REGISTRY.get(api_type)

    if provider_class is None:
        logger.warning(f"未知的API类型: {api_type}，回退到OpenAI兼容格式")
        provider_class = OpenAICompatibleProvider

    return provider_class(api_config)


def register_provider(provider_type: str, provider_class: Type):
    """注册自定义提供商

    Args:
        provider_type: 提供商类型标识
        provider_class: 提供商类（必须继承BaseProvider）
    """
    if not issubclass(provider_class, BaseProvider):
        raise TypeError(f"{provider_class} 必须继承 BaseProvider")
    PROVIDER_REGISTRY[provider_type] = provider_class
    logger.info(f"已注册API提供商: {provider_type} -> {provider_class.__name__}")


__all__ = [
    "BaseProvider",
    "OllamaProvider",
    "OpenAICompatibleProvider",
    "ZhipuProvider",
    "DoubaoProvider",
    "PROVIDER_REGISTRY",
    "get_provider",
    "register_provider",
]
