#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
替换display_name的用例

处理三层替换：
- 第1层：minecraft:display_name → 替换为语言键引用
- 第2层：战利品表书籍内容 → 硬编码替换翻译结果
- 第3层：包含 § 颜色代码的字符串 → 硬编码替换翻译结果
"""

import os
from typing import Dict, Optional, Callable, Any
from pathlib import Path


class ReplaceDisplayNamesUseCase:
    """替换display_name的用例类"""
    
    def __init__(self, file_handler):
        """
        初始化用例
        
        Args:
            file_handler: FileHandler实例
        """
        self.file_handler = file_handler
    
    def execute(
        self,
        bp_path: str,
        progress_callback: Optional[Callable[[float, int, int], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        执行替换display_name操作（三层处理）
        
        Args:
            bp_path: BP文件夹路径
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
            if not bp_path:
                return {
                    'success': False,
                    'file_count': 0,
                    'backup_path': '',
                    'message': '请先选择 BP 文件夹'
                }

            log("开始三层替换...")
            progress(0.05)

            backup = self.file_handler.backup_folder(bp_path)
            if not backup:
                return {
                    'success': False,
                    'file_count': 0,
                    'backup_path': '',
                    'message': '备份失败，操作取消'
                }

            log(f"已备份至: {backup}")
            progress(0.1)

            total_files = 0
            hardcoded_count = 0

            zh_cn_path = os.path.join(bp_path, "texts", "zh_CN.lang")
            lang_entries = {}
            if os.path.exists(zh_cn_path):
                lang_entries = self.file_handler.parse_lang_file(zh_cn_path)
                log(f"从 zh_CN.lang 读取 {len(lang_entries)} 条翻译")
            else:
                log("⚠️ 未找到 zh_CN.lang，跳过硬编码替换")

            log("第1层: 替换 display_name 为语言键引用...")
            layer1_count = self.file_handler.replace_display_names_with_lang_key(bp_path)
            log(f"  第1层完成: {layer1_count} 个文件")
            total_files += layer1_count
            progress(0.4)

            if lang_entries:
                hardcoded_entries = {
                    k: v for k, v in lang_entries.items()
                    if k.startswith('book.') or k.startswith('auto.')
                }

                if hardcoded_entries:
                    log(f"第2层/第3层: 硬编码替换 {len(hardcoded_entries)} 条...")
                    hardcoded_count = self.file_handler.apply_hardcoded_translations(
                        bp_path, hardcoded_entries)
                    log(f"  第2层/第3层完成: {hardcoded_count} 条")
                    total_files += hardcoded_count
                else:
                    log("  无第2层/第3层条目需要处理")

            progress(1.0)

            summary = f"替换完成: 第1层 {layer1_count} 个文件"
            if hardcoded_count > 0:
                summary += f", 第2层/第3层 {hardcoded_count} 条硬编码"

            log(summary)

            return {
                'success': True,
                'file_count': total_files,
                'layer1_count': layer1_count,
                'hardcoded_count': hardcoded_count,
                'backup_path': backup,
                'message': summary
            }

        except Exception as ex:
            log(f"替换失败: {str(ex)}")
            progress(0)
            return {
                'success': False,
                'file_count': 0,
                'backup_path': '',
                'message': str(ex)
            }
