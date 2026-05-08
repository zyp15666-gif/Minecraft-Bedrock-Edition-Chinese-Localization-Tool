#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实体显示名称适配的用例
"""

import os
from typing import Any, Callable, Dict, Optional


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

    @staticmethod
    def _validate_input(bp_path: str) -> Optional[Dict[str, Any]]:
        """验证输入参数

        Args:
            bp_path: BP文件夹路径

        Returns:
            错误结果字典，验证通过返回None
        """
        if not bp_path:
            return {
                'success': False,
                'count': 0,
                'preview': [],
                'message': '请先选择 BP 文件夹'
            }
        return None

    @staticmethod
    def _generate_display_entries(base_name_dict: Dict, translated_dict: Dict) -> Dict[str, str]:
        """根据翻译结果生成最终语言条目

        Args:
            base_name_dict: 基础实体名到lang键的映射
            translated_dict: 翻译结果字典

        Returns:
            生成的语言条目字典
        """
        new_entries = {}
        for base_name, lang_keys in base_name_dict.items():
            chinese_base = translated_dict.get(base_name, base_name)
            for lang_key in lang_keys:
                if lang_key.endswith("_m.name"):
                    display_name = f"{chinese_base}(雄{chinese_base})"
                else:
                    display_name = f"{chinese_base}(雌{chinese_base})"
                new_entries[lang_key] = display_name
        return new_entries

    def _write_results(self, bp_path: str, rp_path: Optional[str], new_entries: Dict[str, str],
                       log_callback, progress_callback) -> None:
        """写入翻译结果到文件

        Args:
            bp_path: BP文件夹路径
            rp_path: RP文件夹路径
            new_entries: 生成的语言条目
            log_callback: 日志回调
            progress_callback: 进度回调
        """
        def log(msg):
            if log_callback:
                log_callback(msg)

        log("正在写入文件...")
        self.file_handler.merge_and_write_lang(bp_path, new_entries, is_translated=True)
        self.file_handler.ensure_languages_json(bp_path)

        if rp_path and os.path.exists(rp_path):
            self.file_handler.merge_and_write_lang(rp_path, new_entries, is_translated=True)
            self.file_handler.ensure_languages_json(rp_path)

        if progress_callback:
            progress_callback(1.0)

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
            validation_error = self._validate_input(bp_path)
            if validation_error:
                return validation_error

            log("开始提取实体显示名称...")
            progress(0.1)

            # 提取实体信息
            base_name_dict = self.file_handler.extract_entity_display_names(bp_path)

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

            # 构造翻译字典并翻译
            temp_dict = {name: name for name in base_names}
            log(f"正在翻译 {len(base_names)} 个基础实体名...")

            def translate_progress(p, remaining_count=0, remaining_time=0):
                if p < 1.0:
                    p = max(p, 0.2)
                    mapped_progress = 0.3 + (p - 0.2) * 0.625
                    progress(mapped_progress, remaining_count, remaining_time)
                else:
                    progress(0.8, 0, 0)

            translated_dict = self.translator.translate_entries_batch(
                temp_dict, translate_progress, log)

            # 处理翻译失败的情况
            for name in base_names:
                if name not in translated_dict or not translated_dict[name]:
                    translated_dict[name] = name

            # 生成最终语言条目
            new_entries = self._generate_display_entries(base_name_dict, translated_dict)

            progress(0.8)

            # 写入文件
            self._write_results(bp_path, rp_path, new_entries, log_callback, progress_callback)

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
