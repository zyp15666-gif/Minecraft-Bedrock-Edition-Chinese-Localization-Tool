#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提取并翻译的用例
"""

import os
from typing import Any, Callable, Dict, Optional


class ExtractAndTranslateUseCase:
    """提取并翻译的用例类"""

    def __init__(self, file_handler, translator):
        self.file_handler = file_handler
        self.translator = translator

    def execute(
        self,
        bp_path: str,
        rp_path: Optional[str] = None,
        progress_callback: Optional[Callable[[float, int, int], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        def log(msg):
            if log_callback:
                log_callback(msg)

        def progress(value, remaining_count=0, remaining_time=0):
            if progress_callback:
                progress_callback(value, remaining_count, remaining_time)

        try:
            if not bp_path:
                return {
                    'success': False,
                    'count': 0,
                    'message': '请先选择 BP 文件夹',
                    'translated_entries': {}
                }

            log("开始提取并翻译...")
            progress(0.05)

            # 步骤1: 提取条目
            log("正在提取文本...")
            entries = self.file_handler.extract_entries(bp_path)

            if not entries:
                return {
                    'success': False,
                    'count': 0,
                    'message': '未提取到任何条目',
                    'translated_entries': {}
                }

            log(f"已提取 {len(entries)} 条，开始翻译...")
            progress(0.2)

            # 步骤2: 翻译
            log(f"正在翻译 {len(entries)} 条...")

            def translate_progress(p, remaining_count=0, remaining_time=0):
                if p < 1.0:
                    p = max(p, 0.2)
                    mapped_progress = 0.2 + (p - 0.2) * 0.75
                    progress(mapped_progress, remaining_count, remaining_time)
                else:
                    progress(0.8, 0, 0)

            translated = self.translator.translate_entries_batch(
                entries, translate_progress, log)

            if not translated:
                return {
                    'success': False,
                    'count': 0,
                    'message': '翻译失败',
                    'translated_entries': {}
                }

            progress(0.8)

            # ===== 新增步骤：硬编码汉化（二、三层） =====
            log("正在应用硬编码汉化...")
            hardcoded = {k: v for k, v in translated.items()
                         if k.startswith('book.') or k.startswith('auto.')}
            if hardcoded:
                self.file_handler.apply_hardcoded_translations(bp_path, hardcoded)
                if rp_path and os.path.exists(rp_path):
                    self.file_handler.apply_hardcoded_translations(rp_path, hardcoded)
                log(f"硬编码汉化完成: {len(hardcoded)} 条")
            else:
                log("没有需要硬编码汉化的条目")

            # 步骤3: 写入文件
            log("正在写入文件...")
            self.file_handler.merge_and_write_lang(
                bp_path, translated, is_translated=True)
            self.file_handler.ensure_languages_json(bp_path)

            if rp_path and os.path.exists(rp_path):
                self.file_handler.merge_and_write_lang(
                    rp_path, translated, is_translated=True)
                self.file_handler.ensure_languages_json(rp_path)
                log(f"同时写入RP: {rp_path}")

            progress(1.0)
            log(f"翻译完成: {len(translated)} 条")

            return {
                'success': True,
                'count': len(translated),
                'message': f'翻译完成，共 {len(translated)} 条',
                'translated_entries': translated
            }

        except Exception as ex:
            log(f"操作失败: {str(ex)}")
            progress(0)
            return {
                'success': False,
                'count': 0,
                'message': str(ex),
                'translated_entries': {}
            }
