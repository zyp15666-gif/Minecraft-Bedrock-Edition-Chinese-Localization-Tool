#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一条龙服务的用例
"""

import os
from typing import Dict, Optional, Callable, Any


class OneClickServiceUseCase:
    """一条龙服务的用例类"""
    
    def __init__(self, file_handler, translator):
        """
        初始化用例
        
        Args:
            file_handler: FileHandler实例
            translator: Translator实例
        """
        self.file_handler = file_handler
        self.translator = translator
    
    def execute(
        self,
        bp_path: str,
        rp_path: Optional[str] = None,
        progress_callback: Optional[Callable[[float, int, int], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        执行一条龙服务操作
        
        Args:
            bp_path: BP文件夹路径
            rp_path: RP文件夹路径（可选）
            progress_callback: 进度回调函数
            log_callback: 日志回调函数
            
        Returns:
            操作结果
        """
        def log(msg):
            if log_callback:
                log_callback(msg)
        
        def progress(value, remaining_count=0, remaining_time=0):
            if progress_callback:
                progress_callback(value, remaining_count, remaining_time)
        
        try:
            # 检查BP路径
            if not bp_path:
                return {
                    'success': False,
                    'backup_path': '',
                    'replace_count': 0,
                    'translate_count': 0,
                    'message': '请先选择 BP 文件夹'
                }

            log("开始一条龙服务...")

            progress(0.15)

            # 步骤2: 先提取原始英文文本（在替换之前！）
            log("步骤2/4: 提取文本...")
            entries = self.file_handler.extract_entries(bp_path)

            if not entries:
                log("未找到需要翻译的条目")
                return {
                    'success': True,
                    'backup_path': '',
                    'replace_count': 0,
                    'translate_count': 0,
                    'message': '一条龙完成，但未找到需要翻译的条目'
                }

            log(f"已提取 {len(entries)} 条")
            progress(0.25)

            # 步骤3: 替换display_name为lang键
            log("步骤3/4: 替换display_name...")
            replace_count = self.file_handler.replace_display_names_with_lang_key(
                bp_path)
            log(f"替换了 {replace_count} 个display_name")
            progress(0.45)

            # 步骤4: 翻译+写入
            log(f"步骤4/4: 翻译{len(entries)}条...")

            def translate_progress(p, remaining_count=0, remaining_time=0):
                # 翻译进度映射到 0.45-0.75 区间，留 0.25 给后续操作
                if p < 1.0:
                    p = max(p, 0.2)
                    mapped_progress = 0.35 + (p - 0.2) * 0.5
                    progress(mapped_progress, remaining_count, remaining_time)
                else:
                    # 翻译完成但未完全结束，保持在 0.75
                    progress(0.75, 0, 0)

            # 使用批量AI翻译方法
            translated = self.translator.translate_entries_batch(
                entries, translate_progress, log)

            if not translated:
                return {
                    'success': False,
                    'backup_path': '',
                    'replace_count': replace_count,
                    'translate_count': 0,
                    'message': '翻译失败'
                }

            # 步骤4: 删除value + 写入lang
            log("步骤4/4: 删除value并写入...")
            progress(0.75)

            self.file_handler.remove_value_from_json_folder(bp_path)
            self.file_handler.merge_and_write_lang(
                bp_path, translated, is_translated=True)
            self.file_handler.ensure_languages_json(bp_path)

            # 如果有RP也处理
            if rp_path and os.path.exists(rp_path):
                self.file_handler.remove_value_from_json_folder(rp_path)
                self.file_handler.merge_and_write_lang(
                    rp_path, translated, is_translated=True)
                self.file_handler.ensure_languages_json(rp_path)
                log(f"同时处理RP: {rp_path}")

            progress(1.0)
            log(f"一条龙服务完成: {len(translated)}条")

            return {
                'success': True,
                'backup_path': '',
                'replace_count': replace_count,
                'translate_count': len(translated),
                'message': f'一条龙服务完成！\n替换: {replace_count}个文件\n翻译: {len(translated)}条'
            }

        except Exception as ex:
            log(f"操作失败: {str(ex)}")
            progress(0)
            return {
                'success': False,
                'backup_path': '',
                'replace_count': 0,
                'translate_count': 0,
                'message': str(ex)
            }
