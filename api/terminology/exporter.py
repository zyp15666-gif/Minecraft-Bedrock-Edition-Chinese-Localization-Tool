#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
术语导出器 - 负责导入/导出术语、合并词典、更新检查
"""

import json
import os
import re
import shutil
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import requests

from core.log_manager import get_logger

from .loader import TerminologyLoader

logger = get_logger(__name__)


class ExtractTermsResult(Dict[str, Any]):
    """提取术语结果类型定义"""
    sorted_terms: List[Tuple[str, int]]
    term_context: Dict[str, List[str]]
    missing_terms: List[str]
    total_unique_terms: int
    filtered_terms: int


class TerminologyExporter:
    """术语导出器"""

    def __init__(self, loader: TerminologyLoader):
        """初始化术语导出器

        Args:
            loader: 术语加载器实例
        """
        self.loader = loader

    def export_terms(self, output_path: str, format: str = 'json') -> bool:
        """导出当前术语词典到文件（含元数据）"""
        try:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

            if format.lower() == 'json':
                data = dict(self.loader.terms)
                meta = dict(getattr(self.loader, 'meta', {}))
                meta.update({
                    'version': meta.get('version', '1.0'),
                    'updated': datetime.now().strftime('%Y-%m-%d'),
                    'total_terms': len(self.loader.terms),
                })
                result = {'_meta': meta}
                result.update(data)
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
            elif format.lower() == 'tsv':
                with open(output_path, 'w', encoding='utf-8') as f:
                    for key, value in self.loader.terms.items():
                        f.write(f"{key}\t{value}\n")
            else:
                logger.error(f"不支持的格式: {format}")
                return False

            logger.info(f"术语词典已导出: {output_path} ({len(self.loader.terms)} 条)")
            return True

        except Exception as e:
            logger.error(f"导出术语词典失败: {e}")
            return False

    def import_terms(self, input_path: str, overwrite: bool = False, replace: bool = False) -> int:
        """从文件导入术语到当前词典

        Args:
            input_path: 输入文件路径
            overwrite: 是否覆盖现有术语（单个键覆盖）
            replace: 是否完全替换当前词典（清空后导入）

        Returns:
            导入的术语数量
        """
        try:
            if not os.path.exists(input_path):
                logger.error(f"文件不存在: {input_path}")
                return 0

            if input_path.lower().endswith('.json'):
                with open(input_path, 'r', encoding='utf-8') as f:
                    imported_terms = json.load(f)
            else:
                imported_terms = {}
                with open(input_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            parts = line.split('\t')
                            if len(parts) >= 2:
                                key, value = parts[0], parts[1]
                                imported_terms[key] = value

            if replace:
                self.loader.terms.clear()
                logger.info("已清空现有术语词典，准备完全替换")

            imported_count = self.add_terms_batch(imported_terms, overwrite)
            logger.info(f"已从 {input_path} 导入 {imported_count} 条术语")

            if replace and self.loader.dict_path:
                try:
                    os.makedirs(os.path.dirname(os.path.abspath(self.loader.dict_path)), exist_ok=True)
                    with open(self.loader.dict_path, 'w', encoding='utf-8') as f:
                        json.dump(self.loader.terms, f, ensure_ascii=False, indent=2)
                    logger.info(f"已将新术语词典保存到原始文件: {self.loader.dict_path}")
                except Exception as e:
                    logger.error(f"保存术语词典到原始文件失败: {e}")

            return imported_count

        except Exception as e:
            logger.error(f"导入术语词典失败: {e}")
            return 0

    def add_terms_batch(self, terms_dict: Dict[str, str], overwrite: bool = False) -> int:
        """批量添加术语到当前词典

        Args:
            terms_dict: 术语字典 {英文: 中文}
            overwrite: 是否覆盖现有术语

        Returns:
            添加/更新的术语数量
        """
        added_count = 0
        for key, value in terms_dict.items():
            if key not in self.loader.terms or overwrite:
                self.loader.terms[key] = value
                added_count += 1

        logger.info(f"批量添加完成: {added_count} 条术语，总术语数 {len(self.loader.terms)}")
        return added_count

    @staticmethod
    def _load_terms_from_file(file_path: str) -> Dict[str, str]:
        """从文件加载术语词典（支持 JSON 和 TSV 格式）

        Args:
            file_path: 词典文件路径

        Returns:
            加载的术语字典
        """
        if file_path.lower().endswith('.json'):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)

        terms: Dict[str, str] = {}
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        terms[parts[0]] = parts[1]
        return terms

    @staticmethod
    def _save_terms_to_file(file_path: str, terms: Dict[str, str]) -> None:
        """将术语词典保存到文件（支持 JSON 和 TSV 格式）

        Args:
            file_path: 词典文件路径
            terms: 术语字典
        """
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)

        if file_path.lower().endswith('.json'):
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(terms, f, ensure_ascii=False, indent=2)
        else:
            with open(file_path, 'w', encoding='utf-8') as f:
                for key, value in terms.items():
                    f.write(f"{key}\t{value}\n")

    def merge_term_dicts(self, source_dict_path: str, target_dict_path: Optional[str] = None, overwrite: bool = False) -> Dict[str, str]:
        """合并术语词典

        Args:
            source_dict_path: 源词典文件路径
            target_dict_path: 目标词典文件路径（None则使用当前词典）
            overwrite: 是否覆盖现有术语（False则保留现有术语）

        Returns:
            合并后的术语词典
        """
        try:
            source_terms = self._load_terms_from_file(source_dict_path)
            logger.info(f"已加载源术语词典: {len(source_terms)} 条")

            if target_dict_path is None:
                target_terms = self.loader.terms.copy()
            elif os.path.exists(target_dict_path):
                target_terms = self._load_terms_from_file(target_dict_path)
            else:
                target_terms = {}

            merged_count = 0
            for key, value in source_terms.items():
                if key not in target_terms or overwrite:
                    target_terms[key] = value
                    merged_count += 1

            logger.info(f"合并完成: 新增/更新 {merged_count} 条术语，总术语数 {len(target_terms)}")

            if target_dict_path:
                self._save_terms_to_file(target_dict_path, target_terms)
                logger.info(f"已保存到: {target_dict_path}")

            if target_dict_path is None:
                self.loader.terms = target_terms
                logger.info(f"当前术语词典已更新: {len(self.loader.terms)} 条")

            return target_terms

        except Exception as e:
            logger.error(f"合并术语词典失败: {e}")
            return {}

    def check_for_updates(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """检查术语词典更新

        Args:
            config: 包含术语配置的字典

        Returns:
            更新检查结果字典
        """
        update_result = {
            'update_available': False,
            'last_checked': datetime.now().isoformat(),
            'message': '',
            'local_file_mtime': None,
            'local_file_size': None,
            'update_url': config.get('update_url', '')
        }

        try:
            dict_path = config.get('dict_path', self.loader.dict_path)
            if os.path.exists(dict_path):
                stat_info = os.stat(dict_path)
                update_result['local_file_mtime'] = datetime.fromtimestamp(
                    stat_info.st_mtime).isoformat()
                update_result['local_file_size'] = stat_info.st_size
                update_result['local_file_path'] = dict_path

            update_url = config.get('update_url')
            auto_update = config.get('auto_update', False)
            config.get('update_check_interval_days', 30)

            if update_url and auto_update:
                update_result['message'] = '自动更新已启用，但远程检查未实现'
                update_result['update_available'] = False
            else:
                if not update_url:
                    update_result['message'] = '未配置更新URL'
                if not auto_update:
                    update_result['message'] = '自动更新未启用'

            logger.info(f"术语更新检查完成: {update_result['message']}")
            return update_result

        except Exception as e:
            logger.error(f"检查术语更新失败: {e}")
            update_result['message'] = f'检查失败: {str(e)}'
            return update_result

    def update_terms_from_url(self, url: str, backup: bool = True) -> Dict[str, Any]:
        """从URL更新术语词典

        Args:
            url: 术语词典URL
            backup: 是否备份现有词典

        Returns:
            更新结果字典
        """
        update_result = {
            'success': False,
            'downloaded': False,
            'imported': False,
            'backup_created': False,
            'new_terms_count': 0,
            'total_terms_count': 0,
            'error': None
        }

        try:
            if not url or not url.startswith(('http://', 'https://')):
                update_result['error'] = f'无效的URL: {url}'
                return update_result

            if backup and self.loader.dict_path and os.path.exists(self.loader.dict_path):
                backup_path = f"{self.loader.dict_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                shutil.copy2(self.loader.dict_path, backup_path)
                update_result['backup_created'] = True
                update_result['backup_path'] = backup_path
                logger.info(f"已创建术语词典备份: {backup_path}")

            try:
                response = requests.get(url, timeout=30)
                response.raise_for_status()

                temp_path = f"{self.loader.dict_path}.download_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                with open(temp_path, 'w', encoding='utf-8') as f:
                    f.write(response.text)

                update_result['downloaded'] = True
                update_result['temp_path'] = temp_path
                logger.info(f"已从 {url} 下载术语词典到 {temp_path}")

                imported_count = self.import_terms(temp_path, overwrite=True)
                update_result['imported'] = True
                update_result['new_terms_count'] = imported_count
                update_result['total_terms_count'] = len(self.loader.terms)
                update_result['success'] = True

                try:
                    os.remove(temp_path)
                except OSError:
                    pass

                logger.info(f"成功更新术语词典，导入 {imported_count} 条术语，总计 {len(self.loader.terms)} 条")

            except requests.exceptions.RequestException as e:
                update_result['error'] = f'下载失败: {str(e)}'
                logger.error(f"下载术语词典失败: {e}")

        except Exception as e:
            update_result['error'] = f'更新失败: {str(e)}'
            logger.error(f"更新术语词典失败: {e}")

        return update_result

    @staticmethod
    def _clean_lang_value(value: str) -> str:
        """清洗 .lang 文件中的值，移除格式代码和特殊字符

        Args:
            value: 原始值字符串

        Returns:
            清洗后的字符串
        """
        clean = re.sub(r'§[0-9a-fklmnor]', '', value)
        clean = re.sub(r'~LINEBREAK~', ' ', clean)
        clean = re.sub(r'%[0-9]*\$?[sdf]', '', clean)
        clean = re.sub(r'\\n', ' ', clean)
        clean = re.sub(r'[\[\]{}()<>]', '', clean)
        return clean

    @staticmethod
    def _extract_terms_from_line(key: str, value: str) -> List[str]:
        """从单行 .lang 条目中提取潜在术语

        Args:
            key: 条目的键
            value: 条目的值

        Returns:
            提取到的术语列表
        """
        clean_value = TerminologyExporter._clean_lang_value(value)

        uppercase_words = re.findall(r'\b[A-Z]{2,}\b', clean_value)
        titlecase_words = re.findall(r'\b[A-Z][a-z]+\b', clean_value)
        compound_terms = re.findall(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b', clean_value)
        multiword_terms = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b', clean_value)

        if ':' in key:
            identifier = key.split(':')[-1]
            parts = re.split(r'[._]', identifier)
            for part in parts:
                if part and part[0].isupper():
                    titlecase_words.append(part)

        return uppercase_words + titlecase_words + compound_terms + multiword_terms

    def _find_missing_terms(self, sorted_terms: List[Tuple[str, int]]) -> List[str]:
        """从排序后的术语列表中找出缺失的术语

        Args:
            sorted_terms: 排序后的 (术语, 频率) 列表

        Returns:
            缺失的术语列表
        """
        existing_lower = {k.lower(): v for k, v in self.loader.terms.items()}
        missing_terms = []

        for term, _freq in sorted_terms:
            term_lower = term.lower()
            if term_lower in existing_lower:
                continue
            is_part_of_existing = any(
                term_lower in existing.lower() or existing.lower() in term_lower
                for existing in self.loader.terms.keys()
            )
            if not is_part_of_existing:
                missing_terms.append(term)

        return missing_terms

    def extract_terms_from_lang_file(self, file_path: str, min_frequency: int = 1) -> Dict[str, Any]:
        """从.lang文件提取潜在术语

        Args:
            file_path: .lang文件路径
            min_frequency: 最小出现频率（默认1）

        Returns:
            字典包含提取的术语统计信息
        """
        empty_result = {
            'sorted_terms': [],
            'term_context': {},
            'missing_terms': [],
            'total_unique_terms': 0,
            'filtered_terms': 0
        }

        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            return empty_result

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"读取文件失败 {file_path}: {e}")
            return empty_result

        terms: List[str] = []
        term_context: Dict[str, List[str]] = {}

        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('##'):
                continue
            if '=' not in line:
                continue

            key, value = line.split('=', 1)
            key, value = key.strip(), value.strip()
            if not value:
                continue

            all_terms = self._extract_terms_from_line(key, value)
            for term in all_terms:
                if len(term) > 2:
                    terms.append(term)
                    if term not in term_context:
                        term_context[term] = []
                    term_context[term].append(f"{key}={value[:50]}...")

        term_freq: Dict[str, int] = {}
        for term in terms:
            term_freq[term] = term_freq.get(term, 0) + 1

        sorted_terms = [(term, freq) for term, freq in sorted(term_freq.items(), key=lambda x: x[1], reverse=True)
                        if freq >= min_frequency]

        missing_terms = self._find_missing_terms(sorted_terms)

        return {
            'sorted_terms': sorted_terms,
            'term_context': term_context,
            'missing_terms': missing_terms,
            'total_unique_terms': len(term_freq),
            'filtered_terms': len(sorted_terms)
        }

    def get_term_stats(self) -> Dict[str, Any]:
        """获取术语词典统计信息

        Returns:
            统计信息字典
        """
        length_groups: Dict[int, int] = {}
        for term in self.loader.terms.keys():
            length = len(term)
            length_groups[length] = length_groups.get(length, 0) + 1

        length_ratios = []
        for en, zh in self.loader.terms.items():
            if en and zh:
                ratio = len(zh) / len(en) if len(en) > 0 else 0
                length_ratios.append(ratio)

        avg_ratio = sum(length_ratios) / len(length_ratios) if length_ratios else 0

        return {
            'total_terms': len(self.loader.terms),
            'avg_term_length': sum(len(term) for term in self.loader.terms.keys()) / len(self.loader.terms) if self.loader.terms else 0,
            'length_groups': dict(sorted(length_groups.items())),
            'avg_translation_ratio': avg_ratio,
            'sample_terms': list(self.loader.terms.items())[:10] if self.loader.terms else []
        }
