#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多API验证器 - 负责多API投票和翻译质量评估

从APIManager中分离出的职责：
- 多API翻译协调
- 翻译质量评估
- 投票和评分机制
- 结果选择
"""

from typing import Any, Dict, List, Optional, Tuple

from core.log_manager import get_logger
from core.utils import contains_known_terms

logger = get_logger(__name__)


class MultiAPIVerifier:
    """多API验证器 - 管理多API翻译投票和质量评估"""

    def __init__(self, config: Dict[str, Any], term_service=None, quality_checker=None):
        """初始化多API验证器

        Args:
            config: 配置字典
            term_service: 术语服务实例
            quality_checker: 质量检查器实例
        """
        self.config = config
        self.term_service = term_service
        self.quality_checker = quality_checker

        advanced_config = config.get('advanced', {})
        quality_config = advanced_config.get('quality', {})

        self.min_score_threshold = quality_config.get('min_score_threshold', 0.6)
        self.enable_voting = quality_config.get('enable_voting', True)

        logger.info(f"[MultiAPIVerifier] 初始化完成: voting={self.enable_voting}")

    def multi_api_translate(
        self,
        api_client,
        text: str,
        available_apis: List[Dict[str, Any]],
        custom_prompt: Optional[str] = None
    ) -> str:
        """多API翻译并选择最佳结果

        Args:
            api_client: API客户端
            text: 待翻译文本
            available_apis: 可用API列表
            custom_prompt: 自定义提示词

        Returns:
            最佳翻译结果
        """
        if not available_apis:
            logger.warning("没有可用的API进行多API翻译")
            return text

        if not self.enable_voting or len(available_apis) == 1:
            api_config = available_apis[0]
            try:
                result = api_client.translate(api_config, text, custom_prompt=custom_prompt)
                return result if result else text
            except Exception as e:
                logger.error(f"单API翻译失败: {e}")
                return text

        translations = self._collect_translations_from_apis(
            api_client, text, available_apis, custom_prompt
        )

        if not translations:
            logger.warning("所有API翻译都失败")
            return text

        best_translation = self._select_best_translation(text, translations)

        logger.info(f"多API翻译完成: {len(translations)} 个候选，选择最佳结果")
        return best_translation

    def _collect_translations_from_apis(
        self,
        api_client,
        text: str,
        available_apis: List[Dict[str, Any]],
        custom_prompt: Optional[str]
    ) -> List[Tuple[str, str]]:
        """从多个API收集翻译结果

        Args:
            api_client: API客户端
            text: 待翻译文本
            available_apis: 可用API列表
            custom_prompt: 自定义提示词

        Returns:
            [(api_name, translation), ...] 列表
        """
        translations = []

        for api_config in available_apis:
            api_name = api_config.get('name', 'unknown')

            try:
                translation = api_client.translate(
                    api_config, text, custom_prompt=custom_prompt
                )

                if translation:
                    translations.append((api_name, translation))
                    logger.debug(f"API {api_name} 翻译成功")

            except Exception as e:
                logger.warning(f"API {api_name} 翻译失败: {e}")

        return translations

    def _select_best_translation(self, original: str, translations: List[Tuple[str, str]]) -> str:
        """选择最佳翻译结果

        Args:
            original: 原始文本
            translations: [(api_name, translation), ...] 列表

        Returns:
            最佳翻译结果
        """
        if not translations:
            return original

        if len(translations) == 1:
            return translations[0][1]

        scored_translations = []
        for api_name, translation in translations:
            score = self._evaluate_translation_quality(translation, original)
            scored_translations.append((api_name, translation, score))

        scored_translations.sort(key=lambda x: x[2], reverse=True)

        best_api, best_translation, best_score = scored_translations[0]

        logger.debug(f"最佳翻译来自 {best_api}，得分: {best_score:.2f}")

        if best_score < self.min_score_threshold:
            logger.warning(f"最佳翻译得分 {best_score:.2f} 低于阈值 {self.min_score_threshold}")

        return best_translation

    def _evaluate_translation_quality(self, translation: str, original: str) -> float:
        """评估翻译质量

        Args:
            translation: 翻译结果
            original: 原始文本

        Returns:
            质量得分 (0.0 - 1.0)
        """
        if not translation:
            return 0.0

        score = 1.0

        if self._contains_excessive_english(translation, original):
            score -= 0.3

        if self._has_formatting_issues(translation, original):
            score -= 0.2

        if self._is_too_short(translation, original):
            score -= 0.3

        if self._contains_repetitive_patterns(translation):
            score -= 0.2

        if self.term_service and contains_known_terms(original, self.term_service):
            if not contains_known_terms(translation, self.term_service):
                score -= 0.2

        return max(0.0, min(1.0, score))

    def _contains_excessive_english(self, translation: str, original: str) -> bool:
        """检查是否包含过多英文"""
        english_chars = sum(1 for c in translation if c.isascii() and c.isalpha())
        total_chars = len(translation.replace(" ", ""))

        if total_chars == 0:
            return False

        english_ratio = english_chars / total_chars

        original_english_chars = sum(1 for c in original if c.isascii() and c.isalpha())
        original_total_chars = len(original.replace(" ", ""))
        original_english_ratio = original_english_chars / original_total_chars if original_total_chars > 0 else 0

        return english_ratio > 0.5 and english_ratio > original_english_ratio + 0.1

    def _has_formatting_issues(self, translation: str, original: str) -> bool:
        """检查格式问题"""
        original_has_color = '§' in original
        translation_has_color = '§' in translation

        if original_has_color and not translation_has_color:
            return True

        original_newlines = original.count('\n')
        translation_newlines = translation.count('\n')

        if abs(original_newlines - translation_newlines) > 1:
            return True

        return False

    def _is_too_short(self, translation: str, original: str) -> bool:
        """检查翻译是否过短"""
        if len(original) < 10:
            return False

        length_ratio = len(translation) / len(original)

        return length_ratio < 0.3

    def _contains_repetitive_patterns(self, translation: str) -> bool:
        """检查是否包含重复模式"""
        words = translation.split()
        if len(words) < 4:
            return False

        word_counts = {}
        for word in words:
            word_counts[word] = word_counts.get(word, 0) + 1

        max_count = max(word_counts.values())
        total_words = len(words)

        return max_count > total_words * 0.3

    def verify_translation(self, original: str, translation: str) -> Dict[str, Any]:
        """验证翻译质量

        Args:
            original: 原始文本
            translation: 翻译结果

        Returns:
            验证结果字典
        """
        score = self._evaluate_translation_quality(translation, original)

        return {
            'original': original,
            'translation': translation,
            'score': score,
            'passed': score >= self.min_score_threshold,
            'issues': self._identify_issues(translation, original)
        }

    def _identify_issues(self, translation: str, original: str) -> List[str]:
        """识别翻译问题

        Args:
            translation: 翻译结果
            original: 原始文本

        Returns:
            问题列表
        """
        issues = []

        if self._contains_excessive_english(translation, original):
            issues.append("excessive_english")

        if self._has_formatting_issues(translation, original):
            issues.append("formatting_issues")

        if self._is_too_short(translation, original):
            issues.append("too_short")

        if self._contains_repetitive_patterns(translation):
            issues.append("repetitive_patterns")

        return issues
