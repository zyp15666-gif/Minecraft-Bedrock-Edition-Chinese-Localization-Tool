#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API提供商抽象基类

定义统一的API提供商接口，各提供商实现子类。
符合开闭原则：扩展新API只需新增子类文件。
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
from core.log_manager import get_logger

logger = get_logger(__name__)


class BaseProvider(ABC):
    """API提供商抽象基类"""

    PROVIDER_TYPE: str = "base"

    def __init__(self, api_config: Dict[str, Any]):
        self.api_config = api_config
        self.name = api_config.get("name", "unknown")
        self.model = api_config.get("model", "unknown")
        self.temperature = api_config.get("temperature", 0.3)

    @abstractmethod
    def build_request(
        self,
        text: str,
        system_prompt: Optional[str] = None,
        is_test: bool = False
    ) -> Tuple[str, Dict[str, str], Dict[str, Any]]:
        """构建API请求

        Args:
            text: 待翻译文本
            system_prompt: 系统提示词
            is_test: 是否为测试模式

        Returns:
            (api_url, headers, payload) 三元组
        """
        pass

    @abstractmethod
    def parse_response(self, response_data: Dict[str, Any]) -> str:
        """解析API响应

        Args:
            response_data: API响应的JSON数据

        Returns:
            翻译结果文本
        """
        pass

    def get_timeout(self, is_test: bool = False) -> Tuple[int, int]:
        """获取请求超时时间

        Args:
            is_test: 是否为测试模式

        Returns:
            (connect_timeout, read_timeout) 二元组
        """
        return (10, 15 if is_test else 120)

    def validate_config(self) -> bool:
        """验证API配置是否有效

        Returns:
            配置是否有效
        """
        return bool(self.api_config.get("api_url"))

    def classify_error(self, error: Exception, response_data: Optional[Dict[str, Any]] = None) -> Tuple[str, str]:
        """统一错误分类和处理

        Args:
            error: 发生的异常
            response_data: API响应数据（如果有）

        Returns:
            (error_type, user_message) 元组
        """
        error_str = str(error)
        error_type = type(error).__name__

        if response_data:
            if isinstance(response_data, dict):
                if response_data.get("error"):
                    error_msg = response_data["error"]
                    if "authentication" in error_str.lower() or "api" in error_str.lower():
                        return ("auth", "API认证失败，请检查API密钥是否正确")
                    elif "rate" in error_str.lower():
                        return ("rate_limit", "API请求频率超限，请稍后重试")
                    elif "quota" in error_str.lower():
                        return ("quota", "API配额不足，请检查使用量")
                    return ("api_error", f"API错误: {error_msg}")

        if "timeout" in error_str.lower():
            return ("timeout", "请求超时，请检查网络连接")
        elif "connection" in error_str.lower():
            return ("connection", "网络连接失败，请检查网络")
        elif "SSL" in error_str or "ssl" in error_str.lower():
            return ("ssl", "SSL连接失败，请检查证书配置")
        elif "401" in error_str or "403" in error_str:
            return ("auth", "API认证失败，请检查API密钥是否正确")
        elif "429" in error_str:
            return ("rate_limit", "API请求频率超限，请稍后重试")
        elif "500" in error_str or "502" in error_str or "503" in error_str:
            return ("server", "API服务器错误，请稍后重试")

        return ("unknown", f"发生错误: {error_type}")

    def get_error_user_message(self, error: Exception, response_data: Optional[Dict[str, Any]] = None) -> str:
        """获取用户友好的错误消息

        Args:
            error: 发生的异常
            response_data: API响应数据（如果有）

        Returns:
            用户友好的错误消息
        """
        _, user_message = self.classify_error(error, response_data)
        return user_message

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name} model={self.model}>"
