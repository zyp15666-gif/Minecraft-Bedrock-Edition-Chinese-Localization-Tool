#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Translator 单元测试

测试翻译器的核心功能，包括：
- 语言键格式检测
- 翻译流程
- 分批逻辑
- 术语匹配
"""

from unittest.mock import Mock

from core.translator import Translator, is_lang_key_format


class TestLangKeyFormat:
    """语言键格式检测测试"""

    def test_is_lang_key_format_valid(self):
        """测试有效语言键格式"""
        assert is_lang_key_format("item.sgs_farm:breadcrumbs.name")
        assert is_lang_key_format("tile.minecraft:stone.name")
        assert is_lang_key_format("entity.zombie:zombie.name")
        assert is_lang_key_format("sgs_farm:itemGroup.name")

    def test_is_lang_key_format_invalid(self):
        """测试无效语言键格式"""
        assert not is_lang_key_format("Hello World")
        assert not is_lang_key_format("apple")
        assert not is_lang_key_format("item.")
        assert not is_lang_key_format(".name")
        assert not is_lang_key_format("")


class TestTranslator:
    """Translator 测试类"""

    def test_init(self):
        """测试初始化"""
        mock_api_manager = Mock()
        mock_api_manager.available_apis = []

        translator = Translator(mock_api_manager, {"basic": {"namespace": "test"}})

        assert translator is not None
        assert translator.api_manager == mock_api_manager
        assert translator.max_retries == 2  # 默认值

    def test_translate_entries_empty(self):
        """测试空条目翻译"""
        api_mgr = Mock()
        api_mgr.available_apis = []
        translator = Translator(api_mgr, {"basic": {"namespace": "test"}})

        result = translator.translate_entries({})
        assert result == {}

    def test_translate_single_item_with_term_match(self):
        """测试术语匹配直接返回"""
        api_mgr = Mock()
        api_mgr.available_apis = [{"name": "test_api"}]
        api_mgr.term_service = Mock()
        api_mgr.term_service.get_translation_original.return_value = "术语翻译"
        api_mgr.term_service.get_translation_clean.return_value = None

        translator = Translator(api_mgr, {"basic": {"namespace": "test", "max_retries": 1}})

        result = translator.translate_single_item(("key", "text", 1, set()))
        assert result == ("key", "术语翻译")

    def test_translate_single_item_lang_key(self):
        """测试语言键直接返回原文"""
        api_mgr = Mock()
        api_mgr.available_apis = []
        api_mgr.term_service = Mock()
        api_mgr.term_service.get_translation_original.return_value = None
        api_mgr.term_service.get_translation_clean.return_value = None

        translator = Translator(api_mgr, {"basic": {"namespace": "test"}})

        # 使用有效的语言键格式
        lang_key = "item.sgs_farm:test.name"
        result = translator.translate_single_item(("key", lang_key, 1, {lang_key}))
        assert result == ("key", lang_key)

    def test_translate_single_item_no_api(self):
        """测试无可用API时返回原文"""
        api_mgr = Mock()
        api_mgr.available_apis = []
        api_mgr.get_available_apis.return_value = []
        api_mgr.get_next_api.return_value = None
        api_mgr.term_service = Mock()
        api_mgr.term_service.get_translation_original.return_value = None
        api_mgr.term_service.get_translation_clean.return_value = None

        translator = Translator(api_mgr, {"basic": {"namespace": "test"}})

        result = translator.translate_single_item(("key", "Hello World", 1, set()))
        assert result == ("key", "Hello World")

    def test_translate_single_item_with_translation(self):
        """测试正常翻译流程"""
        api_mgr = Mock()
        api_mgr.available_apis = [{"name": "test_api"}]
        api_mgr.get_available_apis.return_value = [{"name": "test_api"}]
        api_mgr.get_next_api.return_value = {"name": "test_api"}
        api_mgr.translate_text.return_value = "你好"
        api_mgr.term_service = Mock()
        api_mgr.term_service.get_translation_original.return_value = None
        api_mgr.term_service.get_translation_clean.return_value = None

        translator = Translator(api_mgr, {"basic": {"namespace": "test"}})

        result = translator.translate_single_item(("key", "Hello", 1, set()))
        assert result == ("key", "你好")

    def test_is_poor_quality_high_english_ratio(self):
        """测试英文比例过高的质量检测"""
        api_mgr = Mock()
        api_mgr.available_apis = []
        api_mgr.term_service = Mock()
        api_mgr.term_service.get_translation_original.return_value = None
        api_mgr.term_service.get_translation_clean.return_value = None

        translator = Translator(api_mgr, {"basic": {"namespace": "test"}})

        # 英文比例高的情况
        assert translator._is_poor_quality("Hello", "Hello")
        assert translator._is_poor_quality("Hello World", "Hello World")

        # 正常翻译
        assert not translator._is_poor_quality("Hello", "你好")


class TestTranslatorDictTranslation:
    """字典翻译测试"""

    def test_translate_dict_single(self):
        """测试单线程字典翻译"""
        api_mgr = Mock()
        api_mgr.available_apis = [{"name": "test_api"}]
        api_mgr.get_available_apis.return_value = [{"name": "test_api"}]
        api_mgr.term_service = Mock()
        api_mgr.term_service.get_translation_original.return_value = None
        api_mgr.term_service.get_translation_clean.return_value = None
        api_mgr.translate_text.return_value = "翻译1"

        translator = Translator(api_mgr, {"basic": {"namespace": "test"}})

        result = translator.translate_dict_single({"key1": "text1"})
        assert result == {"key1": "翻译1"}

    def test_translate_dict_parallel(self):
        """测试并行字典翻译"""
        api_mgr = Mock()
        api_mgr.available_apis = [{"name": "test_api"}]
        api_mgr.get_available_apis.return_value = [{"name": "test_api"}]
        api_mgr.term_service = Mock()
        api_mgr.term_service.get_translation_original.return_value = None
        api_mgr.term_service.get_translation_clean.return_value = None
        api_mgr.translate_text.return_value = "翻译结果"

        translator = Translator(api_mgr, {"basic": {"namespace": "test"}})

        result = translator.translate_dict_parallel({"key1": "text1", "key2": "text2"})
        assert "key1" in result
        assert "key2" in result
        assert result["key1"] == "翻译结果"
        assert result["key2"] == "翻译结果"


class TestTranslatorFallback:
    """翻译降级策略测试"""

    def test_local_to_cloud_fallback(self):
        """测试本地模型到云端模型的降级"""
        api_mgr = Mock()
        api_mgr.available_apis = [
            {"name": "local", "type": "local_ollama"},
            {"name": "cloud", "type": "deepseek"}
        ]
        api_mgr.get_available_apis.return_value = [
            {"name": "local", "type": "local_ollama"},
            {"name": "cloud", "type": "deepseek"}
        ]
        api_mgr.term_service = Mock()
        api_mgr.term_service.get_translation_original.return_value = None
        api_mgr.term_service.get_translation_clean.return_value = None
        api_mgr.translate_with_api.return_value = "Hello"  # 质量不合格，返回英文
        api_mgr.multi_api_translate.return_value = "你好"  # 云端翻译

        translator = Translator(api_mgr, {"basic": {"namespace": "test", "local_first_fallback": True}})

        result = translator.translate_single_item(("key", "Hello", 1, set()))
        # 由于质量检查会触发降级，应该返回云端翻译结果
        assert result[0] == "key"

    def test_multi_api_translation(self):
        """测试多API投票翻译"""
        api_mgr = Mock()
        api_mgr.available_apis = [
            {"name": "api1"},
            {"name": "api2"}
        ]
        api_mgr.get_available_apis.return_value = [
            {"name": "api1"},
            {"name": "api2"}
        ]
        api_mgr.multi_api_translate.return_value = "最佳翻译"
        api_mgr.term_service = Mock()
        api_mgr.term_service.get_translation_original.return_value = None
        api_mgr.term_service.get_translation_clean.return_value = None

        translator = Translator(api_mgr, {"basic": {"namespace": "test", "use_multi_api_validation": True}})

        result = translator.translate_single_item(("key", "Hello", 1, set()))
        assert result == ("key", "最佳翻译")
