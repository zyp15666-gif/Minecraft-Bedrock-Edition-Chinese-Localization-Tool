#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
术语匹配器 - 负责预处理、后处理、术语匹配
"""

import re
from collections import OrderedDict
from typing import Dict, Optional, Tuple

from core.log_manager import get_logger

from .loader import TerminologyLoader

logger = get_logger(__name__)


class TerminologyMatcher:
    """术语匹配器"""

    def __init__(self, loader: TerminologyLoader):
        """初始化术语匹配器

        Args:
            loader: 术语加载器实例
        """
        self.loader = loader
        self.placeholder_prefix = "[["
        self.placeholder_suffix = "]]"
        self._preprocess_cache = OrderedDict()
        self._cache_max_size = 1000

    def _get_from_cache(self, text: str) -> Optional[Tuple[str, Dict[str, str]]]:
        """从缓存获取预处理结果

        Args:
            text: 原始文本

        Returns:
            缓存的预处理结果，如果不存在返回 None
        """
        if text in self._preprocess_cache:
            result = self._preprocess_cache.pop(text)
            self._preprocess_cache[text] = result
            return result
        return None

    def _add_to_cache(self, text: str, result: Tuple[str, Dict[str, str]]):
        """添加预处理结果到缓存

        Args:
            text: 原始文本
            result: 预处理结果
        """
        if len(self._preprocess_cache) >= self._cache_max_size:
            self._preprocess_cache.popitem(last=False)
        self._preprocess_cache[text] = result

    def preprocess(self, text: str) -> Tuple[str, Dict[str, str]]:
        """预处理文本，将术语替换为占位符

        Args:
            text: 原始文本

        Returns:
            预处理后的文本和占位符映射
        """
        if not text:
            return text, {}

        cached_result = self._get_from_cache(text)
        if cached_result is not None:
            return cached_result

        placeholder_counter = 0
        placeholder_map: Dict[str, str] = {}

        if self.loader.use_automaton and not self._has_any_term(text):
            result = (text, {})
            self._add_to_cache(text, result)
            return result

        processed_text = text

        if self.loader.use_automaton and self.loader.automaton:
            matched_terms = set()
            text_lower = text.lower()
            for _, term in self.loader.automaton.iter(text_lower):
                matched_terms.add(term)

            sorted_matched_terms = sorted(matched_terms, key=len, reverse=True)

            for term in sorted_matched_terms:
                translation = self.loader.terms.get(term)
                if translation:
                    pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
                    if pattern.search(processed_text):
                        placeholder = f"{self.placeholder_prefix}TERM_{placeholder_counter}{self.placeholder_suffix}"
                        placeholder_map[placeholder] = translation
                        placeholder_counter += 1
                        processed_text = pattern.sub(placeholder, processed_text)
        else:
            sorted_terms = sorted(self.loader.terms.items(),
                                  key=lambda x: len(x[0]), reverse=True)

            for term, translation in sorted_terms:
                if term in processed_text:
                    pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
                    if pattern.search(processed_text):
                        placeholder = f"{self.placeholder_prefix}TERM_{placeholder_counter}{self.placeholder_suffix}"
                        placeholder_map[placeholder] = translation
                        placeholder_counter += 1
                        processed_text = pattern.sub(placeholder, processed_text)

        if not placeholder_map:
            result = (text, {})
        else:
            result = (processed_text, placeholder_map)

        self._add_to_cache(text, result)
        return result

    def _normalize_placeholder_prefix(self, prefix: str) -> str:
        """标准化占位符前缀

        Args:
            prefix: 原始前缀字符串

        Returns:
            标准化后的前缀
        """
        return 'TERM' if prefix in ['TERM', '术语'] else prefix

    def _build_placeholder(self, prefix: str, num: str) -> str:
        """构建占位符字符串

        Args:
            prefix: 前缀
            num: 编号

        Returns:
            完整的占位符字符串
        """
        normalized_prefix = self._normalize_placeholder_prefix(prefix)
        return f"{self.placeholder_prefix}{normalized_prefix}_{num}{self.placeholder_suffix}"

    def _replace_remaining_placeholders(self, text: str) -> str:
        """替换文本中残留的未处理占位符

        Args:
            text: 包含残留占位符的文本

        Returns:
            处理后的文本
        """
        remaining_pattern = re.compile(r'\[(?:TERM|术语)_\d+\]|\*\*术语\*\*|\[\[(?:TERM|术语)_\d+\]\]')
        if not remaining_pattern.search(text):
            return text

        logger.warning(f"检测到未处理的占位符: {text}")

        for term, trans in self.loader.terms.items():
            if len(term) <= 20:
                text = re.sub(
                    r'\b' + re.escape(term) + r'\b', trans, text, flags=re.IGNORECASE)

        return remaining_pattern.sub('', text)

    def postprocess(self, text: str, placeholder_map: Optional[Dict[str, str]] = None) -> str:
        """后处理文本，还原占位符为术语翻译

        Args:
            text: 包含占位符的文本
            placeholder_map: 占位符映射字典

        Returns:
            后处理后的文本，占位符被还原为术语翻译
        """
        if not text:
            return text

        processed_text = text

        if placeholder_map:
            for placeholder, translation in placeholder_map.items():
                processed_text = processed_text.replace(placeholder, translation)

        pattern1 = re.compile(r'\[(TERM|术语)_(\d+)\]')
        pattern2 = re.compile(r'\*\*(术语)\*\*')
        pattern3 = re.compile(r'\[\[(TERM|术语)_(\d+)\]\]')

        def replace_single_bracket(match):
            prefix = match.group(1)
            num = match.group(2)
            placeholder = self._build_placeholder(prefix, num)
            if placeholder_map and placeholder in placeholder_map:
                return placeholder_map[placeholder]
            else:
                try:
                    idx = int(num)
                    values = list(placeholder_map.values()) if placeholder_map else []
                    if idx < len(values):
                        return values[idx]
                except (ValueError, TypeError):
                    pass
                return match.group(0)

        def replace_markdown(match):
            match.group(1)
            if placeholder_map:
                for placeholder, translation in placeholder_map.items():
                    if '术语' in placeholder:
                        return translation
            return match.group(0)

        def replace_double_bracket(match):
            prefix = match.group(1)
            num = match.group(2)
            placeholder = self._build_placeholder(prefix, num)
            if placeholder_map and placeholder in placeholder_map:
                return placeholder_map[placeholder]
            return match.group(0)

        processed_text = pattern1.sub(replace_single_bracket, processed_text)
        processed_text = pattern2.sub(replace_markdown, processed_text)
        processed_text = pattern3.sub(replace_double_bracket, processed_text)

        processed_text = self._replace_remaining_placeholders(processed_text)

        return processed_text

    def get_translation(self, text: str) -> Optional[str]:
        """获取术语翻译（两步匹配策略）

        Args:
            text: 待翻译文本

        Returns:
            翻译结果，如果未找到返回None
        """
        result = self.get_translation_original(text)
        if result:
            return result
        return self.get_translation_clean(text)

    def get_translation_original(self, text: str) -> Optional[str]:
        """使用原始文本匹配（不区分大小写），并标准化换行符和空白

        Args:
            text: 待匹配文本

        Returns:
            翻译结果，如果未找到返回None
        """
        if not text:
            return None

        normalized_text = text.replace('\r\n', '\n').replace('\r', '\n')
        normalized_text = re.sub(r'\s+', ' ', normalized_text).strip()

        if text in self.loader.terms:
            logger.debug(f"[术语匹配] 原始精确匹配成功: {text}")
            return self.loader.terms[text]

        if normalized_text in self.loader.terms:
            logger.debug(f"[术语匹配] 标准化后精确匹配成功: {normalized_text}")
            return self.loader.terms[normalized_text]

        lower_text = normalized_text.lower()
        if lower_text in self.loader.lower_terms:
            logger.debug(f"[术语匹配] 小写匹配成功: {lower_text}")
            return self.loader.lower_terms[lower_text]

        return None

    def get_translation_clean(self, text: str) -> Optional[str]:
        """使用清洗后的文本匹配（不区分大小写）

        Args:
            text: 待匹配文本

        Returns:
            翻译结果，如果未找到返回None
        """
        if not text:
            return None
        if text in self.loader.clean_terms:
            return self.loader.clean_terms[text]
        return self.loader.clean_lower_terms.get(text.lower())

    def has_any_term(self, text: str) -> bool:
        """快速检查文本是否包含任意术语（公开接口）

        Args:
            text: 待检查文本

        Returns:
            True如果文本包含至少一个术语，否则False
        """
        return self._has_any_term(text)

    def _has_any_term(self, text: str) -> bool:
        """快速检查文本是否包含任意术语（不区分大小写）

        Args:
            text: 待检查文本

        Returns:
            True如果文本包含至少一个术语，否则False
        """
        if not self.loader.use_automaton or not self.loader.automaton:
            return True

        text_lower = text.lower()
        for _ in self.loader.automaton.iter(text_lower):
            return True
        return False

    def fix_spelling(self, text: str) -> str:
        """修复常见的拼写错误

        Args:
            text: 原始文本

        Returns:
            修复后的文本
        """
        fixed_text = text
        for mistake, correction in self.loader.spelling_mistakes.items():
            fixed_text = fixed_text.replace(mistake, correction)
        return fixed_text
