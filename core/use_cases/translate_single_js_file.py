#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
翻译单个JS文件的用例
"""

import os
from typing import Dict, Optional, Callable, Any


class TranslateSingleJsFileUseCase:
    """翻译单个JS文件的用例类"""
    
    def __init__(self, translator):
        self.translator = translator
    
    def execute(
        self,
        js_file_path: str,
        mode: int = 2,
        progress_callback: Optional[Callable[[float, int, float], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        from ..script_translation import ScriptTranslation

        if not os.path.exists(js_file_path):
            return {
                'success': False,
                'message': '文件不存在',
                'translated_files': [],
                'backup_files': [],
                'failed_files': []
            }

        try:
            if log_callback:
                log_callback(f"开始翻译单个 JS 文件: {js_file_path}")
            if progress_callback:
                progress_callback(0.05, 0, 0)

            script_trans = ScriptTranslation(self.translator)

            result = script_trans.translate_js_files_with_ast(
                js_files=[js_file_path],
                mode=mode,
                progress_callback=progress_callback,
                log_callback=log_callback
            )
            return result
        except Exception as e:
            if log_callback:
                log_callback(f"翻译 JS 文件失败: {e}")
            return {
                'success': False,
                'message': str(e),
                'translated_files': [],
                'backup_files': [],
                'failed_files': [js_file_path]
            }