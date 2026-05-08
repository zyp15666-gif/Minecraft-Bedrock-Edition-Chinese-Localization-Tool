#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量删除value的用例
"""

import json
import os
from typing import Any, Callable, Dict, Optional


class BatchDeleteValueUseCase:
    """批量删除value的用例类"""

    def __init__(self, file_handler, config):
        """
        初始化用例

        Args:
            file_handler: FileHandler实例
            config: 配置字典
        """
        self.file_handler = file_handler
        self.config = config

    def execute(
        self,
        folder_path: str,
        progress_callback: Optional[Callable[[float, int, int], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        执行批量删除value操作

        Args:
            folder_path: 目标文件夹路径
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
            # 检查路径
            if not folder_path or not os.path.exists(folder_path):
                return {
                    'success': False,
                    'total': 0,
                    'success_count': 0,
                    'backup_path': '',
                    'message': '无效的文件夹路径'
                }

            log(f"开始批量删除 value: {folder_path}")
            progress(0.05)

            # 备份文件夹
            backup = self.file_handler.backup_folder(folder_path)
            if not backup:
                return {
                    'success': False,
                    'total': 0,
                    'success_count': 0,
                    'backup_path': '',
                    'message': '备份失败，操作取消'
                }

            log(f"已备份至: {backup}")
            progress(0.1)

            total = 0
            success = 0
            indent = self.config.get("basic", {}).get("indent", 4)

            for root, _, files in os.walk(folder_path):
                for filename in files:
                    if not filename.lower().endswith(".json"):
                        continue

                    filepath = os.path.join(root, filename)
                    total += 1

                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            data = json.load(f)

                        data = self.file_handler.remove_value_from_json(data)

                        with open(filepath, "w", encoding="utf-8") as f:
                            json.dump(data, f, ensure_ascii=False,
                                      indent=indent)

                        success += 1
                        log(f"{filename} → 已删除value（转为字符串格式）")
                    except Exception as ex:
                        log(f"{filename} → 错误：{str(ex)}")

                    # 更新进度
                    if total > 0:
                        p = 0.1 + (total / max(total * 2, 1)) * 0.9
                        progress(min(p, 0.99))

            progress(1.0)
            log(f"删除完成: 总计{total}个 | 成功{success}个")

            return {
                'success': True,
                'total': total,
                'success_count': success,
                'backup_path': backup,
                'message': f'批量删除value完成\n总计 {total} 个 | 成功 {success} 个'
            }

        except Exception as ex:
            log(f"删除失败: {str(ex)}")
            progress(0)
            return {
                'success': False,
                'total': 0,
                'success_count': 0,
                'backup_path': '',
                'message': str(ex)
            }
