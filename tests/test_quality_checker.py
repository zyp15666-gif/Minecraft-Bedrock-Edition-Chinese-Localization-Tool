#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core/quality_checker.py 单元测试
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from core.quality_checker import TranslationQualityChecker


@pytest.fixture
def checker():
    return TranslationQualityChecker(cache_enabled=False)


class TestAI_PROMPTS:
    def test_detects_chinese_ai_prompt(self):
        checker = TranslationQualityChecker(cache_enabled=False)
        assert checker._has_ai_prompts("请提供英文文本") is True

    def test_detects_english_ai_prompt(self):
        checker = TranslationQualityChecker(cache_enabled=False)
        assert checker._has_ai_prompts("Please provide the English text") is True

    def test_normal_translation_passes(self):
        checker = TranslationQualityChecker(cache_enabled=False)
        assert checker._has_ai_prompts("你好世界") is False


class TestCheckLengthRatio:
    def test_normal_ratio(self):
        checker = TranslationQualityChecker(cache_enabled=False)
        ok, msg = checker._check_length_ratio("Hello World", "你好世界")
        assert ok is True

    def test_too_short(self):
        checker = TranslationQualityChecker(cache_enabled=False)
        ok, msg = checker._check_length_ratio("Hello World This Is A Long Text", "短")
        assert ok is False

    def test_too_long(self):
        checker = TranslationQualityChecker(cache_enabled=False)
        ok, msg = checker._check_length_ratio("Hi", "这是一个非常非常非常非常非常非常非常非常非常非常非常长的翻译")
        assert ok is False


class TestCheckColorCodes:
    def test_color_codes_preserved(self):
        checker = TranslationQualityChecker(cache_enabled=False)
        ok, msg = checker._check_color_codes("§6Golden§f", "§6金色§f")
        assert ok is True

    def test_color_codes_lost(self):
        checker = TranslationQualityChecker(cache_enabled=False)
        ok, msg = checker._check_color_codes("§6Golden§f", "金色")
        assert ok is False

    def test_no_color_codes(self):
        checker = TranslationQualityChecker(cache_enabled=False)
        ok, msg = checker._check_color_codes("Golden", "金色")
        assert ok is True


class TestCheckPlaceholders:
    def test_placeholders_preserved(self):
        checker = TranslationQualityChecker(cache_enabled=False)
        ok, msg = checker._check_placeholders("Item %s found", "物品 %s 已找到")
        assert ok is True

    def test_placeholders_lost(self):
        checker = TranslationQualityChecker(cache_enabled=False)
        ok, msg = checker._check_placeholders("Item %s found", "物品已找到")
        assert ok is False


class TestCheckEnglishRatio:
    def test_low_english_ratio(self):
        checker = TranslationQualityChecker(cache_enabled=False)
        ok, msg = checker._check_english_ratio("Hello World", "你好世界测试文本")
        assert ok is True

    def test_high_english_ratio(self):
        checker = TranslationQualityChecker(cache_enabled=False)
        ok, msg = checker._check_english_ratio(
            "Hello World", "Hello World translation test")
        assert ok is False

    def test_short_text_skipped(self):
        checker = TranslationQualityChecker(cache_enabled=False)
        ok, msg = checker._check_english_ratio("Hi", "你好")
        assert ok is True


class TestCheckQuality:
    def test_good_translation(self):
        checker = TranslationQualityChecker(cache_enabled=False)
        assert checker.check_quality("Hello World", "你好世界") is True

    def test_ai_prompt_detected(self):
        checker = TranslationQualityChecker(cache_enabled=False)
        assert checker.check_quality("Hello", "请提供英文文本") is False

    def test_color_codes_lost(self):
        checker = TranslationQualityChecker(cache_enabled=False)
        assert checker.check_quality("§6Golden§f", "金色") is False

    def test_detailed_report(self):
        checker = TranslationQualityChecker(cache_enabled=False)
        ok, report = checker.check_quality("Hello World", "你好世界", detailed_report=True)
        assert 'quality_ok' in report
        assert 'issues' in report


class TestAnalyzeBatch:
    def test_batch_analysis(self):
        checker = TranslationQualityChecker(cache_enabled=False)
        pairs = [
            ("Hello", "你好"),
            ("§6Golden§f", "金色"),
            ("Hello", "请提供英文文本"),
        ]
        result = checker.analyze_batch(pairs)
        assert result['total'] == 3
        assert 'pass_rate' in result
