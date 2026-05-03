#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
翻译引擎接口定义

定义 Translator 与 APIManager 之间的清晰接口，
降低核心模块对具体实现的直接依赖。
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable


class ITranslationEngine(ABC):
    """翻译引擎抽象接口

    Translator 通过此接口调用翻译服务，
    不直接依赖 APIManager 的具体实现。
    """

    @abstractmethod
    def translate_text(
        self,
        text: str,
        is_test: bool = False,
        custom_prompt: Optional[str] = None
    ) -> str:
        """翻译单条文本

        Args:
            text: 待翻译文本
            is_test: 是否为测试模式
            custom_prompt: 自定义提示词

        Returns:
            翻译结果
        """
        pass

    @abstractmethod
    def translate_batch(
        self,
        items: Dict[str, str],
        max_workers: int = 4,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, str]:
        """批量翻译

        Args:
            items: 待翻译的键值对 {key: text}
            max_workers: 最大并发数
            progress_callback: 进度回调

        Returns:
            翻译结果 {key: translated_text}
        """
        pass

    def get_available_apis(self) -> List[Dict[str, Any]]:
        """获取可用的API列表

        Returns:
            API配置列表
        """
        pass

    def is_available(self) -> bool:
        """检查翻译引擎是否可用

        Returns:
            是否有可用的API
        """
        pass

    def translate_with_api(
        self,
        api_config: Dict[str, Any],
        text: str,
        is_test: bool = False,
        custom_prompt: Optional[str] = None
    ) -> str:
        """使用指定的API配置翻译文本

        Args:
            api_config: API配置字典
            text: 待翻译文本
            is_test: 是否为测试模式
            custom_prompt: 自定义提示词

        Returns:
            翻译结果
        """
        pass
