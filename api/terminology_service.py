#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
术语处理服务 - 作为门面类，整合加载器、匹配器和导出器
"""

from typing import Dict, Optional, List, Tuple, Any

from core.log_manager import get_logger
from api.terminology import TerminologyLoader, TerminologyMatcher, TerminologyExporter

logger = get_logger(__name__)


class TerminologyService:
    """术语处理服务 - 门面类，提供统一接口"""

    def __init__(self, dict_path: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        """初始化术语处理服务
        
        Args:
            dict_path: 术语词典文件路径，None表示使用内置词典
            config: 配置字典，用于读取高级配置
        """
        # 初始化子组件
        self.loader = TerminologyLoader(dict_path, config)
        self.matcher = TerminologyMatcher(self.loader)
        self.exporter = TerminologyExporter(self.loader)
        
        # 向后兼容的快捷方法映射
        self.preprocess = self.matcher.preprocess
        self.postprocess = self.matcher.postprocess
        self.get_translation = self.matcher.get_translation
        self.get_translation_original = self.matcher.get_translation_original
        self.get_translation_clean = self.matcher.get_translation_clean
        self.get_translation_ignore_case = self._get_translation_ignore_case
        self.has_any_term = self.matcher.has_any_term
        self.fix_spelling_mistakes = self.matcher.fix_spelling
        self.add_spelling_correction = self.loader.add_spelling_correction
        self.export_terms = self.exporter.export_terms
        self.import_terms = self.exporter.import_terms
        self.merge_term_dicts = self.exporter.merge_term_dicts
        self.add_terms_batch = self.exporter.add_terms_batch
        self.extract_terms_from_lang_file = self.exporter.extract_terms_from_lang_file
        self.get_term_stats = self.exporter.get_term_stats
        self.check_for_updates = self.exporter.check_for_updates
        self.update_terms_from_url = self.exporter.update_terms_from_url
        
        # 向后兼容的属性
        self.terms = self.loader.terms
        self._lower_terms = self.loader.lower_terms
        self._clean_terms = self.loader.clean_terms
        self._clean_lower_terms = self.loader.clean_lower_terms
        
        # 保持旧的属性名（用于向后兼容）
        if hasattr(self.loader, '_spelling_mistakes'):
            self._spelling_mistakes = self.loader.spelling_mistakes

    def _get_translation_ignore_case(self, text: str) -> Optional[str]:
        """不区分大小写地获取术语翻译（向后兼容）"""
        if not text:
            return None
        if text in self.loader.terms:
            return self.loader.terms[text]
        return self.loader.lower_terms.get(text.lower())

    def get_translation_with_fallback(self, text: str) -> Optional[str]:
        """两步匹配策略（向后兼容）"""
        result = self.get_translation_original(text)
        if result:
            return result
        return self.get_translation_clean(text)

    def _load_spelling_corrections(self, file_path: Optional[str] = None):
        """加载拼写修正映射表（向后兼容）"""
        self.loader._load_spelling_corrections(file_path)

    def add_spelling_correction(self, mistake: str, correction: str, save_to_file: bool = False) -> bool:
        """添加新的拼写修正规则（向后兼容，支持保存到文件）"""
        self.loader.add_spelling_correction(mistake, correction)
        
        if save_to_file:
            return self.loader.save_spelling_corrections()
        
        return True
