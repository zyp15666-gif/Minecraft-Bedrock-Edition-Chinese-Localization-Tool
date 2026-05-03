#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FileHandler + Translator 联合集成测试

测试文件处理和翻译引擎的协作。
使用 mock 隔离外部 API 调用。
"""

import sys
import os
import json
import tempfile
import shutil
from unittest.mock import Mock, patch

import pytest


@pytest.fixture
def temp_project():
    """创建完整测试项目文件夹"""
    tmp_dir = tempfile.mkdtemp()
    texts_dir = os.path.join(tmp_dir, "texts")
    os.makedirs(texts_dir, exist_ok=True)

    # 创建 manifest
    manifest = {
        "format_version": 2,
        "header": {"name": "test", "description": "test", "uuid": "1" * 36, "version": [1, 0, 0]},
        "modules": [{"type": "data", "uuid": "2" * 36, "version": [1, 0, 0]}],
    }
    with open(os.path.join(tmp_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f)

    # 创建多个测试方块文件
    for i in range(3):
        block = {
            "format_version": "1.20.0",
            "minecraft:block": {
                "description": {"identifier": f"test_ns:block_{i}", "register_to_creative_menu": True},
                "components": {"minecraft:display_name": {"value": f"Block {i} Name"}}
            }
        }
        blocks_dir = os.path.join(tmp_dir, "blocks")
        os.makedirs(blocks_dir, exist_ok=True)
        with open(os.path.join(blocks_dir, f"block_{i}.json"), "w") as f:
            json.dump(block, f)

    # 创建测试实体文件
    entity = {
        "format_version": "1.20.0",
        "minecraft:entity": {
            "description": {"identifier": "test_ns:test_entity"},
            "components": {"minecraft:display_name": {"value": "Test Entity"}}
        }
    }
    entities_dir = os.path.join(tmp_dir, "entities")
    os.makedirs(entities_dir, exist_ok=True)
    with open(os.path.join(entities_dir, "test_entity.json"), "w") as f:
        json.dump(entity, f)

    yield tmp_dir
    shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.fixture
def file_handler():
    from core.file_handler import FileHandler
    return FileHandler({"basic": {"namespace": "test_ns", "indent": 4}})


class TestFileHandlerExtraction:
    """测试 FileHandler 提取功能"""

    def test_extract_entries_from_temp(self, temp_project, file_handler):
        entries = file_handler.extract_entries(temp_project)
        assert entries is not None
        assert len(entries) >= 3  # at least the 3 blocks

    def test_extract_entries_with_display_name(self, temp_project, file_handler):
        entries = file_handler.extract_entries(temp_project)
        for key, value in entries.items():
            assert isinstance(key, str)
            assert isinstance(value, str)
            assert len(key) > 0

    def test_lang_file_generation(self, temp_project, file_handler):
        entries = file_handler.extract_entries(temp_project)
        assert len(entries) > 0

        # 写入 lang 文件
        file_handler.merge_and_write_lang(temp_project, entries, is_translated=False)
        lang_path = os.path.join(temp_project, "texts", "zh_CN.lang")
        assert os.path.exists(lang_path)

        # 验证文件内容
        with open(lang_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "test_ns" in content
        assert "=" in content

    def test_languages_json_creation(self, temp_project, file_handler):
        file_handler.ensure_languages_json(temp_project)
        lang_json_path = os.path.join(temp_project, "texts", "languages.json")
        assert os.path.exists(lang_json_path)
        with open(lang_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # ensure_languages_json 会添加 zh_CN，如果不存在则创建
        assert "zh_CN" in data

    def test_extract_empty_folder(self, file_handler):
        with tempfile.TemporaryDirectory() as empty_dir:
            entries = file_handler.extract_entries(empty_dir)
            assert entries == {}


class TestTranslatorMockIntegration:
    """测试 Translator 与 FileHandler 协作"""

    def test_translate_entries_empty(self, file_handler):
        from core.translator import Translator
        mock_api = Mock()
        mock_api.available_apis = []
        translator = Translator(mock_api, {"basic": {}})
        result = translator.translate_entries({})
        assert result == {}

    def test_translate_entries_no_api(self, file_handler):
        from core.translator import Translator
        mock_api = Mock()
        mock_api.available_apis = [{"name": "mock", "type": "mock"}]
        mock_api.get_available_apis.return_value = [{"name": "mock", "type": "mock"}]
        mock_api.term_service = None
        # translate_text 应该返回传入的文本（模拟API不可用）
        mock_api.translate_text.side_effect = lambda text: text
        translator = Translator(mock_api, {"basic": {}, "rate_limit": {"default": 0.0}})
        entries = {"key1": "Hello", "key2": "World"}
        result = translator.translate_entries(entries)
        assert result is not None
        # 没有可用 API 时应该返回原文（mock 会通过 side_effect 返回原文）
        assert result == entries

    def test_translate_single_item_lang_key(self, file_handler):
        """测试语言键格式的条目被跳过"""
        from core.translator import Translator, is_lang_key_format
        mock_api = Mock()
        mock_api.available_apis = []
        mock_api.term_service = None
        translator = Translator(mock_api, {"basic": {}})

        # 调用 translate_single_item
        keys_set = {"item.test_ns:diamond.name"}
        result = translator.translate_single_item(
            ("key", "item.test_ns:diamond.name", 1, keys_set)
        )
        assert result[1] == "item.test_ns:diamond.name"  # 跳过翻译

    def test_translate_single_item_regular_text(self, file_handler):
        """测试普通文本走翻译流程"""
        from core.translator import Translator
        mock_api = Mock()
        mock_api.available_apis = [{"name": "mock", "type": "openai_compatible"}]
        mock_api.get_available_apis.return_value = [{"name": "mock", "type": "openai_compatible"}]
        mock_api.term_service = None
        mock_api.get_next_api.return_value = {"name": "mock", "type": "openai_compatible"}
        mock_api.translate_with_api.return_value = "翻译结果"
        translator = Translator(mock_api, {"basic": {"local_first_fallback": False, "use_multi_api_validation": False}})

        keys_set = set()
        result = translator.translate_single_item(("key", "Hello", 1, keys_set))
        assert result[0] == "key"

    def test_quality_check_inline(self, file_handler):
        """测试内置的质量检查方法"""
        from core.translator import Translator
        mock_api = Mock()
        mock_api.available_apis = []
        translator = Translator(mock_api, {"basic": {}})

        # _is_poor_quality 方法测试
        assert translator._is_poor_quality("Hello", "") is True  # 空翻译
        assert translator._is_poor_quality("Hello", "HelloWorldTest") is True  # 全英文
        assert translator._is_poor_quality("Hello", "你好世界") is False  # 中文翻译
        assert translator._is_poor_quality("Hello", "Hello Hello") is True  # 英文比例过高


class TestUseCaseMockIntegration:
    """测试 UseCase 与 Translator + FileHandler 协作"""

    def test_extract_only_use_case(self, temp_project, file_handler):
        from core.use_cases.extract_only import ExtractOnlyUseCase
        usecase = ExtractOnlyUseCase(file_handler)
        result = usecase.execute(bp_path=temp_project)
        assert result.get('success') is True

    def test_batch_delete_use_case(self, temp_project, file_handler):
        from core.use_cases.batch_delete_value import BatchDeleteValueUseCase
        usecase = BatchDeleteValueUseCase(file_handler, {"basic": {"indent": 4}})
        result = usecase.execute(folder_path=temp_project)
        assert result is not None

    def test_batch_restore_use_case(self, temp_project, file_handler):
        from core.use_cases.batch_restore_value import BatchRestoreValueUseCase
        usecase = BatchRestoreValueUseCase(file_handler, {"basic": {"indent": 4}})
        result = usecase.execute(folder_path=temp_project)
        assert result is not None


class TestUtilsIntegration:
    """工具函数集成测试"""

    def test_lang_key_detection(self):
        from core.translator import is_lang_key_format
        assert is_lang_key_format("item.test_ns:diamond.name") is True
        assert is_lang_key_format("tile.minecraft:stone.name") is True
        assert is_lang_key_format("entity.zombie:zombie.name") is True
        assert is_lang_key_format("Hello World") is False
        assert is_lang_key_format("") is False
        assert is_lang_key_format(None) is False

    def test_has_color_codes(self):
        from core.utils import has_color_codes
        assert has_color_codes("§6Test§f") is True
        assert has_color_codes("Normal text") is False
        assert has_color_codes("") is False
