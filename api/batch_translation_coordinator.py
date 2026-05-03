#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量翻译协调器 - 负责分批、合并、拆分等批处理逻辑

从APIManager中分离出的职责：
- 文本分批处理
- 批量翻译协调
- 结果拆分和合并
- 术语处理
"""

import re
from typing import Dict, Any, List, Optional, Callable
from core.log_manager import get_logger
from core.utils import contains_known_terms, normalize_game_text

logger = get_logger(__name__)


class BatchTranslationCoordinator:
    """批量翻译协调器 - 管理批量翻译的分批、合并、拆分逻辑"""

    MERGE_SEPARATOR = " <<<SEP>>> "
    BATCH_SIZE = 5

    def __init__(self, config: Dict[str, Any], term_service=None):
        """初始化批量翻译协调器

        Args:
            config: 配置字典
            term_service: 术语服务实例
        """
        self.config = config
        self.term_service = term_service
        
        advanced_config = config.get('advanced', {})
        translation_config = advanced_config.get('translation', {})
        
        self.enable_adaptive_batch = translation_config.get('enable_adaptive_batch', True)
        self.max_batch_size = translation_config.get('max_batch_size', 10)
        self.min_batch_size = translation_config.get('min_batch_size', 2)
        
        logger.info(f"[BatchTranslationCoordinator] 初始化完成: adaptive_batch={self.enable_adaptive_batch}")

    def batch_translate_fragments(
        self,
        api_client,
        api_config: Dict[str, Any],
        plain_texts: List[str],
        progress_callback: Optional[Callable] = None,
        log_callback: Optional[Callable] = None
    ) -> List[str]:
        """批量翻译文本片段

        Args:
            api_client: API客户端
            api_config: API配置
            plain_texts: 待翻译的文本列表
            progress_callback: 进度回调
            log_callback: 日志回调

        Returns:
            翻译结果列表
        """
        if not plain_texts:
            return []

        batches = self._adaptive_batch_fragments(plain_texts)
        
        if log_callback:
            log_callback(f"批量翻译: {len(plain_texts)} 个片段，分为 {len(batches)} 批")

        all_translated = []
        total_batches = len(batches)

        for batch_idx, batch in enumerate(batches):
            if progress_callback:
                progress = (batch_idx + 1) / total_batches
                progress_callback(progress, total_batches - batch_idx - 1, 0)

            merged_text = self.MERGE_SEPARATOR.join(batch)
            
            try:
                translated_merged = api_client.translate(api_config, merged_text)
                
                if translated_merged:
                    translated_parts = self._robust_split_translated_text(
                        translated_merged, len(batch)
                    )
                    all_translated.extend(translated_parts)
                else:
                    all_translated.extend(batch)
                    
            except Exception as e:
                logger.error(f"批量翻译失败: {e}")
                all_translated.extend(batch)

        return all_translated

    def _adaptive_batch_fragments(self, plain_texts: List[str]) -> List[List[str]]:
        """自适应分批

        Args:
            plain_texts: 文本列表

        Returns:
            分批后的文本列表
        """
        if not self.enable_adaptive_batch:
            return self._fixed_batch(plain_texts, self.BATCH_SIZE)

        batches = []
        current_batch = []
        current_length = 0
        max_length = 2000

        for text in plain_texts:
            text_length = len(text)
            
            if current_length + text_length > max_length or len(current_batch) >= self.max_batch_size:
                if current_batch:
                    batches.append(current_batch)
                current_batch = [text]
                current_length = text_length
            else:
                current_batch.append(text)
                current_length += text_length

        if current_batch:
            batches.append(current_batch)

        return batches

    def _fixed_batch(self, items: List[str], size: int) -> List[List[str]]:
        """固定大小分批

        Args:
            items: 项目列表
            size: 批次大小

        Returns:
            分批后的列表
        """
        return [items[i:i + size] for i in range(0, len(items), size)]

    def _robust_split_translated_text(self, translated_text: str, expected_parts: int) -> List[str]:
        """鲁棒的翻译文本拆分

        Args:
            translated_text: 翻译后的文本
            expected_parts: 期望的部分数量

        Returns:
            拆分后的文本列表
        """
        if expected_parts <= 1:
            return [translated_text]

        parts = translated_text.split(self.MERGE_SEPARATOR)
        
        if len(parts) == expected_parts:
            return parts

        if len(parts) > expected_parts:
            result = []
            current = ""
            for i, part in enumerate(parts):
                current += part
                if i < len(parts) - 1:
                    current += self.MERGE_SEPARATOR
                if len(result) < expected_parts - 1:
                    result.append(current)
                    current = ""
            result.append(current)
            return result[:expected_parts]

        parts.extend([""] * (expected_parts - len(parts)))
        return parts

    def batch_translate_with_terms(
        self,
        api_client,
        api_config: Dict[str, Any],
        plain_texts: List[str],
        progress_callback: Optional[Callable] = None,
        log_callback: Optional[Callable] = None
    ) -> List[str]:
        """带术语处理的批量翻译

        Args:
            api_client: API客户端
            api_config: API配置
            plain_texts: 待翻译的文本列表
            progress_callback: 进度回调
            log_callback: 日志回调

        Returns:
            翻译结果列表
        """
        if not plain_texts:
            return []

        if self.term_service:
            processed_texts = []
            term_replacements = []
            
            for text in plain_texts:
                processed_text, replacements = self._preprocess_with_terms(text)
                processed_texts.append(processed_text)
                term_replacements.append(replacements)
        else:
            processed_texts = plain_texts
            term_replacements = [{} for _ in plain_texts]

        translated_texts = self.batch_translate_fragments(
            api_client, api_config, processed_texts,
            progress_callback, log_callback
        )

        if self.term_service:
            final_texts = []
            for translated, replacements in zip(translated_texts, term_replacements):
                final_text = self._postprocess_with_terms(translated, replacements)
                final_texts.append(final_text)
            return final_texts
        
        return translated_texts

    def _preprocess_with_terms(self, text: str) -> tuple:
        """术语预处理

        Args:
            text: 原始文本

        Returns:
            (处理后的文本, 替换映射)
        """
        if not self.term_service:
            return text, {}

        replacements = {}
        processed_text = text
        
        known_terms = self.term_service.find_terms_in_text(text)
        
        for term_info in known_terms:
            original = term_info['original']
            translation = term_info['translation']
            placeholder = f"__TERM_{len(replacements)}__"
            
            processed_text = processed_text.replace(original, placeholder)
            replacements[placeholder] = translation
        
        return processed_text, replacements

    def _postprocess_with_terms(self, text: str, replacements: Dict[str, str]) -> str:
        """术语后处理

        Args:
            text: 翻译后的文本
            replacements: 替换映射

        Returns:
            最终文本
        """
        for placeholder, translation in replacements.items():
            text = text.replace(placeholder, translation)
        
        return text
