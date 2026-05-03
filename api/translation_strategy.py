#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
翻译策略 - 简化版二阶段流程

从 APIManager 中拆分出来的独立组件。
封装术语预处理、分批合并、质量检查等翻译策略逻辑。

新流程：
  - 有颜色符号 → 直接二阶段分割翻译
  - 无颜色符号 → 仅一阶段翻译
"""

import re
import time
from typing import Dict, Any, List, Tuple, Optional, Callable
from core.log_manager import get_logger
from core.utils import split_by_color_codes, has_color_codes, is_lang_key_format
from api.translation_prompts import get_prompt_for_provider

logger = get_logger(__name__)


class TranslationStrategy:
    """翻译策略 - 简化版流程管理"""

    MERGE_SEPARATOR = " <<<SEP>>> "
    BATCH_SIZE = 5
    MAX_MERGE_LENGTH = 600

    def __init__(self, term_service=None, quality_checker=None, cache=None, api_client=None):
        self.term_service = term_service
        self.quality_checker = quality_checker
        self.cache = cache
        self.api_client = api_client

    def preprocess(self, text: str) -> Tuple[str, str, Dict[str, Any]]:
        """预处理待翻译文本
        
        Args:
            text: 原始文本

        Returns:
            (core_text, suffix, context) 三元组
        """
        # 简单清洗：去除首尾空格
        core_text = text.strip()
        suffix = ''
        
        # 如果原文本有尾空格，保留
        if text.endswith(' ') and not core_text.endswith(' '):
            suffix = ' '

        context = {
            'original_text': text,
            'has_color_codes': has_color_codes(text),
            'suffix': suffix,
        }

        return core_text, suffix, context

    def check_term_match(self, text: str) -> Optional[str]:
        """检查术语匹配

        Args:
            text: 待检查文本

        Returns:
            匹配到的术语翻译，无匹配返回None
        """
        if not self.term_service or not self.term_service.terms:
            return None

        translation = self.term_service.get_translation_original(text)
        if translation:
            return translation

        core_text, _, _ = self.preprocess(text)
        if core_text != text:
            translation = self.term_service.get_translation_clean(core_text)
            if translation:
                return translation

        return None

    def should_merge_texts(self, texts: List[str]) -> bool:
        """判断是否应该合并多个文本进行批量翻译

        Args:
            texts: 待合并的文本列表

        Returns:
            是否应该合并
        """
        if len(texts) < 2:
            return False

        total_length = sum(len(t) for t in texts)
        if total_length > self.MAX_MERGE_LENGTH:
            return False

        for text in texts:
            if has_color_codes(text) and len(text) > 100:
                return False

        return True

    def merge_texts(self, texts: List[str]) -> str:
        """合并多个文本用于批量翻译

        Args:
            texts: 待合并的文本列表

        Returns:
            合并后的文本
        """
        return self.MERGE_SEPARATOR.join(texts)

    def split_merged_result(self, merged_result: str, expected_count: int) -> List[str]:
        """拆分合并翻译的结果

        Args:
            merged_result: 合并翻译的结果
            expected_count: 期望的拆分数量

        Returns:
            拆分后的翻译列表
        """
        parts = merged_result.split(self.MERGE_SEPARATOR)

        if len(parts) == expected_count:
            return [p.strip() for p in parts]

        if len(parts) > expected_count:
            merged_parts = []
            idx = 0
            for i in range(expected_count - 1):
                merged_parts.append(parts[idx].strip())
                idx += 1
            merged_parts.append(self.MERGE_SEPARATOR.join(parts[idx:]).strip())
            return merged_parts

        logger.warning(
            f"合并翻译拆分数量不足: 期望{expected_count}，实际{len(parts)}")
        while len(parts) < expected_count:
            parts.append(parts[-1] if parts else "")
        return [p.strip() for p in parts]

    def postprocess(
        self,
        original: str,
        translated: str,
        context: Dict[str, Any]
    ) -> Tuple[str, bool]:
        """后处理翻译结果

        Args:
            original: 原始文本
            translated: 翻译结果
            context: 预处理时的上下文

        Returns:
            (processed_text, quality_ok) 二元组
        """
        quality_ok = True

        if self.quality_checker:
            quality_ok = self.quality_checker.check_quality(original, translated)
            if not quality_ok:
                logger.info(f"质量检查未通过: '{original[:30]}' -> '{translated[:30]}'")

        suffix = context.get('suffix', '')
        if suffix and not translated.endswith(suffix):
            translated = translated.rstrip() + ' ' + suffix

        return translated, quality_ok

    def _translate_stage1(self, api_config: Dict[str, Any], text: str, is_test: bool, custom_prompt: Optional[str] = None) -> str:
        """第一阶段翻译：纯直接翻译"""
        if not self.api_client:
            return text

        return self.api_client.translate(api_config, text, is_test, system_prompt=custom_prompt)

    def _translate_stage2(self, api_config: Dict[str, Any], text: str, is_test: bool, custom_prompt: Optional[str] = None) -> str:
        """第二阶段翻译：处理颜色代码的分段翻译"""
        if not self.api_client:
            return text

        segments = split_by_color_codes(text)
        if not segments:
            return text

        translated_segments = []
        for codes, part in segments:
            if part.strip():
                trans = self.api_client.translate(api_config, part, is_test, system_prompt=custom_prompt)
                translated_segments.append((codes, trans if trans else part))
            else:
                translated_segments.append((codes, part))

        return ''.join(codes + trans for codes, trans in translated_segments)

    def translate(
        self,
        api_config: Dict[str, Any],
        text: str,
        is_test: bool = False,
        custom_prompt: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> str:
        """执行简化后的翻译流程

        新流程：
          - 有颜色符号 → 直接二阶段分割翻译
          - 无颜色符号 → 仅一阶段翻译

        Args:
            api_config: API配置
            text: 待翻译文本
            is_test: 是否为测试模式
            custom_prompt: 自定义提示词
            config: 额外配置

        Returns:
            翻译结果
        """
        api_name = api_config.get('name', '未知API')
        logger.info(f"[翻译策略] 开始翻译: API={api_name}, 原文='{text[:50]}...'")

        # ========== 0. 空文本检查 ==========
        if not text or not text.strip():
            return text

        # ========== 1. 预处理 ==========
        core_text, suffix, context = self.preprocess(text)
        original_text = text

        # ========== 2. 语言键拦截 ==========
        if is_lang_key_format(core_text):
            logger.info(f"[术语/语言键] 检测到语言键格式，保留原文")
            return original_text

        # ========== 3. 术语匹配 ==========
        term_result = self.check_term_match(text)
        if term_result:
            logger.info(f"[术语命中] '{text[:50]}' -> '{term_result[:50]}'")
            if not is_test and self.cache:
                self.cache.set(text, term_result)
            return term_result + suffix

        term_result = self.check_term_match(core_text)
        if term_result:
            logger.info(f"[术语命中-清洗] '{core_text[:50]}' -> '{term_result[:50]}'")
            if not is_test and self.cache:
                self.cache.set(core_text, term_result)
            return term_result + suffix

        # ========== 4. 缓存检查 ==========
        cache_key = core_text
        if not is_test and self.cache:
            cached = self.cache.get(cache_key)
            if cached:
                logger.info(f"[缓存命中]")
                return cached + suffix

        # ========== 5. 核心流程：颜色符号判断 ==========
        has_color = context.get('has_color_codes', has_color_codes(core_text))

        if has_color:
            # ====== 有颜色符号 → 直接二阶段分割翻译 ======
            logger.info(f"[流程] 检测到颜色符号，执行二阶段分割翻译")

            result = self._translate_stage2(api_config, core_text, is_test, custom_prompt)

            if result and result != core_text:
                if not is_test and self.cache:
                    self.cache.set(cache_key, result)
                return result + suffix
            else:
                return core_text + suffix
        else:
            # ====== 无颜色符号 → 仅一阶段翻译 ======
            logger.info(f"[流程] 无颜色符号，执行一阶段直接翻译")

            # 本地模型：根据模型类型选择提示词
            prompt = custom_prompt
            if not prompt and api_config.get('type') == 'local_ollama':
                use_prompt = config.get('basic', {}).get('local_model_use_prompt', True) if config else True
                if use_prompt:
                    provider_type = api_config.get('type', 'openai')
                    prompt = get_prompt_for_provider(provider_type, 'stage1') + core_text

            result = self._translate_stage1(api_config, core_text, is_test, prompt)

            if result and result != core_text:
                if not is_test and self.cache:
                    self.cache.set(cache_key, result)
                return result + suffix
            else:
                return core_text + suffix
