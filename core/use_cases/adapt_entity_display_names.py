#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实体显示名称适配的用例
"""

import os
from typing import Dict, Optional, Callable, Any, List


class AdaptEntityDisplayNamesUseCase:
    """实体显示名称适配的用例类"""
    
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
        执行实体显示名称适配操作
        
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
                    'preview': [],
                    'message': '请先选择 BP 文件夹'
                }

            log("开始提取实体显示名称...")
            progress(0.1)

            # 提取实体信息
            base_name_dict = self.file_handler.extract_entity_display_names(
                bp_path)

            if not base_name_dict:
                return {
                    'success': False,
                    'count': 0,
                    'preview': [],
                    'message': '未提取到任何有效的实体信息'
                }

            base_names = list(base_name_dict.keys())
            log(f"提取到 {len(base_names)} 个基础实体名")

            # 预览前5条
            preview = []
            for i, name in enumerate(base_names[:5]):
                preview.append(
                    {'key': name, 'lang_keys': base_name_dict[name][:2]})
                log(f"   {name} → {len(base_name_dict[name])} 个lang键")

            progress(0.3)

            # 构造翻译字典
            temp_dict = {name: name for name in base_names}

            # 翻译
            log(f"正在翻译 {len(base_names)} 个基础实体名...")

            def translate_progress(p, remaining_count=0, remaining_time=0):
                # 翻译进度映射到 0.3-0.8 区间，留 0.2 给写入操作
                if p < 1.0:
                    p = max(p, 0.2)
                    mapped_progress = 0.3 + (p - 0.2) * 0.625
                    progress(mapped_progress, remaining_count, remaining_time)
                else:
                    # 翻译完成但未完全结束，保持在 0.8
                    progress(0.8, 0, 0)

            # 使用批量AI翻译方法
            translated_dict = self.translator.translate_entries_batch(
                temp_dict, translate_progress, log)

            # 处理翻译失败的情况
            for name in base_names:
                if name not in translated_dict or not translated_dict[name]:
                    translated_dict[name] = name

            # 生成最终语言条目
            new_entries = {}
            for base_name, lang_keys in base_name_dict.items():
                chinese_base = translated_dict.get(base_name, base_name)
                for lang_key in lang_keys:
                    if lang_key.endswith("_m.name"):
                        display_name = f"{chinese_base}(雄{chinese_base})"
                    else:
                        display_name = f"{chinese_base}(雌{chinese_base})"
                    new_entries[lang_key] = display_name

            progress(0.8)

            # 写入文件
            log("正在写入文件...")
            self.file_handler.merge_and_write_lang(
                bp_path, new_entries, is_translated=True)
            self.file_handler.ensure_languages_json(bp_path)

            if rp_path and os.path.exists(rp_path):
                self.file_handler.merge_and_write_lang(
                    rp_path, new_entries, is_translated=True)
                self.file_handler.ensure_languages_json(rp_path)

            progress(1.0)
            log(f"实体显示名称适配完成: {len(new_entries)} 条")

            return {
                'success': True,
                'count': len(new_entries),
                'preview': preview[:5],
                'message': f'实体显示名称适配完成\n共生成 {len(new_entries)} 条语言条目'
            }

        except Exception as ex:
            log(f"操作失败: {str(ex)}")
            progress(0)
            return {
                'success': False,
                'count': 0,
                'preview': [],
                'message': str(ex)
            }
