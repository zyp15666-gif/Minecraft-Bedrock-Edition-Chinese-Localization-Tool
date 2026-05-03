#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
替换display_name的用例
"""

from typing import Dict, Optional, Callable, Any


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
        执行替换display_name操作
        
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
            # 检查BP路径
            if not bp_path:
                return {
                    'success': False,
                    'file_count': 0,
                    'backup_path': '',
                    'message': '请先选择 BP 文件夹'
                }

            log("开始替换 display_name...")
            progress(0.1)

            # 备份BP文件夹
            backup = self.file_handler.backup_folder(bp_path)
            if not backup:
                return {
                    'success': False,
                    'file_count': 0,
                    'backup_path': '',
                    'message': '备份失败，操作取消'
                }

            log(f"已备份至: {backup}")
            progress(0.3)

            # 执行替换
            log("正在替换 display_name...")
            count = self.file_handler.replace_display_names_with_lang_key(
                bp_path)

            progress(1.0)
            log(f"替换完成: {count} 个文件")

            return {
                'success': True,
                'file_count': count,
                'backup_path': backup,
                'message': f'替换完成，共处理 {count} 个JSON文件'
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
