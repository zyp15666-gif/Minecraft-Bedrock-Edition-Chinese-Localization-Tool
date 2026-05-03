#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
仅提取汉化key的用例
"""

import os
from typing import Dict, Optional, Callable, Any


class ExtractOnlyUseCase:
    """仅提取汉化key的用例类"""
    
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
        rp_path: Optional[str] = None,
        progress_callback: Optional[Callable[[float, int, int], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        执行仅提取汉化key操作
        
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
                    'count': 0,
                    'message': '请先选择 BP 文件夹',
                    'output_path': ''
                }

            log("开始提取汉化 key...")
            progress(0.1)

            # 提取条目
            entries = self.file_handler.extract_entries(bp_path)

            if not entries:
                return {
                    'success': False,
                    'count': 0,
                    'message': '未提取到任何条目',
                    'output_path': ''
                }

            log(f"已提取 {len(entries)} 条语言条目")
            progress(0.5)

            # 写入BP
            self.file_handler.merge_and_write_lang(
                bp_path, entries, is_translated=False)
            self.file_handler.ensure_languages_json(bp_path)

            # 写入RP（如果存在）
            if rp_path and os.path.exists(rp_path):
                self.file_handler.merge_and_write_lang(
                    rp_path, entries, is_translated=False)
                self.file_handler.ensure_languages_json(rp_path)
                log(f"同时写入RP: {rp_path}")

            progress(1.0)
            output_path = os.path.join(bp_path, "texts", "zh_CN.lang")

            log(f"提取完成: {output_path}")

            return {
                'success': True,
                'count': len(entries),
                'message': f'提取完成，共 {len(entries)} 条',
                'output_path': output_path
            }

        except Exception as ex:
            log(f"提取失败: {str(ex)}")
            progress(0)
            return {
                'success': False,
                'count': 0,
                'message': str(ex),
                'output_path': ''
            }
