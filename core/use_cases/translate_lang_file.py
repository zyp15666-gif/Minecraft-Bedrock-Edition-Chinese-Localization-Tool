#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
翻译.lang文件的用例
"""

import json
import os
from pathlib import Path
from typing import Any, Callable, Dict, Optional


class TranslateLangFileUseCase:
    """翻译.lang文件的用例类"""

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
    def _validate_input(lang_file_path: str) -> Optional[Dict[str, Any]]:
        """验证输入参数

        Args:
            lang_file_path: .lang文件路径

        Returns:
            错误结果字典，验证通过返回None
        """
        if not lang_file_path or not os.path.exists(lang_file_path):
            return {
                'success': False,
                'count': 0,
                'output_paths': [],
                'message': '无效的.lang文件路径'
            }
        return None

    def _write_to_bp_rp(self, bp_path: Optional[str], rp_path: Optional[str],
                        translated: Dict[str, str], log_callback) -> List[str]:
        """写入翻译结果到BP/RP目录

        Args:
            bp_path: BP文件夹路径
            rp_path: RP文件夹路径
            translated: 翻译结果字典
            log_callback: 日志回调

        Returns:
            输出文件路径列表
        """
        def log(msg):
            if log_callback:
                log_callback(msg)

        output_paths = []

        if bp_path and os.path.exists(bp_path):
            self.file_handler.merge_and_write_lang(bp_path, translated, is_translated=True)
            self.file_handler.ensure_languages_json(bp_path)
            output_path = os.path.join(bp_path, "texts", "zh_CN.lang")
            output_paths.append(output_path)
            log(f"已写入BP: {output_path}")

        if rp_path and os.path.exists(rp_path):
            self.file_handler.merge_and_write_lang(rp_path, translated, is_translated=True)
            self.file_handler.ensure_languages_json(rp_path)
            output_path = os.path.join(rp_path, "texts", "zh_CN.lang")
            output_paths.append(output_path)
            log(f"已写入RP: {output_path}")

        return output_paths

    @staticmethod
    def _write_to_source_dir(lang_file_path: str, translated: Dict[str, str], log_callback) -> str:
        """写入翻译结果到源文件同级目录

        Args:
            lang_file_path: 原始.lang文件路径
            translated: 翻译结果字典
            log_callback: 日志回调

        Returns:
            输出文件路径
        """
        def log(msg):
            if log_callback:
                log_callback(msg)

        source_path = Path(lang_file_path)
        texts_dir = source_path.parent / "texts"
        texts_dir.mkdir(exist_ok=True)
        output_file = texts_dir / "zh_CN.lang"

        # 读取现有条目
        existing = {}
        if output_file.exists():
            with open(output_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if '=' in line:
                        k, v = line.split('=', 1)
                        existing[k] = v

        # 合并并写入
        existing.update(translated)
        with open(output_file, 'w', encoding='utf-8') as f:
            for key in sorted(existing.keys()):
                value = existing[key].replace('\n', '\\n')
                f.write(f"{key}={value}\n")

        log(f"已保存到同级目录: {output_file}")

        # 更新languages.json
        lang_json_path = texts_dir / "languages.json"
        if lang_json_path.exists():
            with open(lang_json_path, 'r', encoding='utf-8') as f:
                langs = json.load(f)
        else:
            langs = []

        if "zh_CN" not in langs:
            langs.append("zh_CN")
            with open(lang_json_path, 'w', encoding='utf-8') as f:
                json.dump(langs, f, indent=2)
            log("已更新 languages.json，添加 zh_CN")

        return str(output_file)

    def execute(
        self,
        lang_file_path: str,
        bp_path: Optional[str] = None,
        rp_path: Optional[str] = None,
        progress_callback: Optional[Callable[[float, int, int], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        执行翻译.lang文件操作

        Args:
            lang_file_path: .lang文件路径
            bp_path: BP文件夹路径（可选，用于输出）
            rp_path: RP文件夹路径（可选，用于输出）
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
            # 检查文件
            validation_error = self._validate_input(lang_file_path)
            if validation_error:
                return validation_error

            log(f"开始翻译 lang 文件: {lang_file_path}")
            progress(0.1)

            # 解析lang文件
            entries = self.file_handler.parse_lang_file(lang_file_path)

            if not entries:
                return {
                    'success': False,
                    'count': 0,
                    'output_paths': [],
                    'message': '未从文件中提取到任何条目'
                }

            log(f"已解析 {len(entries)} 条条目，开始翻译...")
            progress(0.3)

            # 翻译
            log(f"正在翻译 {len(entries)} 条...")

            def translate_progress(p, remaining_count=0, remaining_time=0):
                if p < 1.0:
                    p = max(p, 0.2)
                    mapped_progress = 0.3 + (p - 0.2) * 0.625
                    progress(mapped_progress, remaining_count, remaining_time)
                else:
                    progress(0.8, 0, 0)

            translated = self.translator.translate_entries_batch(
                entries, translate_progress, log)

            if not translated:
                return {
                    'success': False,
                    'count': 0,
                    'output_paths': [],
                    'message': '翻译失败'
                }

            # 写入BP/RP（如果选择了）
            progress(0.8)
            log("正在写入文件...")

            output_paths = self._write_to_bp_rp(bp_path, rp_path, translated, log_callback)

            # 如果没有指定输出目录，保存到源文件同级目录
            if not output_paths:
                output_path = self._write_to_source_dir(lang_file_path, translated, log_callback)
                output_paths.append(output_path)

            progress(1.0)
            log(f"翻译完成: {len(translated)} 条")

            return {
                'success': True,
                'count': len(translated),
                'output_paths': output_paths,
                'message': f'Lang文件翻译完成\n共 {len(translated)} 条语言条目'
            }

        except Exception as ex:
            log(f"翻译失败: {str(ex)}")
            progress(0)
            return {
                'success': False,
                'count': 0,
                'output_paths': [],
                'message': str(ex)
            }
