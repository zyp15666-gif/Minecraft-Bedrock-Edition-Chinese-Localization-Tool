#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本文件夹硬编码汉化的用例
"""

from typing import Any, Callable, Dict, List, Optional


class ScriptHardcodeTranslationUseCase:
    """脚本文件夹硬编码汉化的用例类"""

    def __init__(self, translator):
        """
        初始化用例

        Args:
            translator: Translator实例
        """
        self.translator = translator

    def execute(
        self,
        bp_path: str,
        mode: int = 2,
        progress_callback: Optional[Callable[[float, int, int], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None,
        ui_keywords: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        执行脚本文件夹硬编码汉化操作

        Args:
            bp_path: BP文件夹路径
            mode: 翻译模式 (1: 颜色代码模式, 2: AI智能模式)
            progress_callback: 进度回调函数
            log_callback: 日志回调函数
            ui_keywords: UI关键词列表

        Returns:
            操作结果
        """
        from ..script_translation import create_script_translation

        # 创建脚本汉化分析实例
        script_translator = create_script_translation(self.translator)

        # 调用独立模块的功能
        return script_translator.script_hardcode_translation(
            bp_path=bp_path,
            mode=mode,
            progress_callback=progress_callback,
            log_callback=log_callback,
            ui_keywords=ui_keywords
        )
