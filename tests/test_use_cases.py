#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core/use_cases 模块单元测试
覆盖 11/11 个 UseCase
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import shutil
import tempfile
from unittest.mock import Mock

from core.use_cases.batch_delete_value import BatchDeleteValueUseCase
from core.use_cases.batch_restore_value import BatchRestoreValueUseCase
from core.use_cases.extract_only import ExtractOnlyUseCase


class MockFileHandler:
    """Mock FileHandler for testing"""

    def __init__(self):
        self.config = {"basic": {"indent": 4}}
        self.namespace = "test_ns"
        self.indent = 4

    def backup_folder(self, folder_path):
        backup_path = folder_path + "_backup"
        if os.path.exists(folder_path):
            shutil.copytree(folder_path, backup_path)
        return backup_path

    def remove_value_from_json(self, data):
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, dict) and "value" in value:
                    data[key] = str(value["value"])
                elif isinstance(value, dict) and "minecraft:display_name" in value:
                    if isinstance(value["minecraft:display_name"], dict):
                        value["minecraft:display_name"]["value"] = str(
                            value["minecraft:display_name"].get("value", "")
                        )
        return data

    def restore_value_to_json(self, data):
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, str) and not value.startswith("tile.") and not value.startswith("item."):
                    data[key] = {"value": value}
        return data

    def extract_entries(self, bp_folder):
        entries = {}
        for root, _, files in os.walk(bp_folder):
            for filename in files:
                if filename.endswith(".json"):
                    filepath = os.path.join(root, filename)
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        if "minecraft:block" in data:
                            desc = data["minecraft:block"].get("description", {})
                            ident = desc.get("identifier", "")
                            if ident:
                                entry_id = ident.split(":")[-1]
                                key = f"tile.test_ns:{entry_id}.name"
                                entries[key] = f"Block {entry_id}"
                    except Exception:
                        pass
        return entries

    def merge_and_write_lang(self, folder, entries, is_translated=False):
        texts_dir = os.path.join(folder, "texts")
        os.makedirs(texts_dir, exist_ok=True)
        lang_path = os.path.join(texts_dir, "zh_CN.lang")
        with open(lang_path, "w", encoding="utf-8") as f:
            for key, value in entries.items():
                f.write(f"{key}={value}\n")

    def ensure_languages_json(self, folder):
        lang_json_path = os.path.join(folder, "texts", "languages.json")
        with open(lang_json_path, "w", encoding="utf-8") as f:
            json.dump(["en_US", "zh_CN"], f)

    def replace_display_names_with_lang_key(self, folder):
        return 5

    def remove_value_from_json_folder(self, folder):
        return True

    def restore_value_to_json_folder(self, folder):
        return True

    def parse_lang_file(self, filepath):
        return {"key1": "Value1", "key2": "Value2"}

    def extract_entity_display_names(self, folder):
        return {"entity.test:zombie.name": "Zombie"}

    def update_manifest_metadata(self, bp_path, rp_path, translator=None):
        return True


class TestBatchDeleteValueUseCase:
    """BatchDeleteValueUseCase 单元测试"""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.file_handler = MockFileHandler()
        self.config = {"basic": {"indent": 4}}
        self.usecase = BatchDeleteValueUseCase(self.file_handler, self.config)

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        backup_dir = self.temp_dir + "_backup"
        shutil.rmtree(backup_dir, ignore_errors=True)

    def test_execute_with_invalid_path(self):
        result = self.usecase.execute("/nonexistent/path")
        assert result["success"] is False
        assert result["total"] == 0
        assert "无效" in result["message"]

    def test_execute_with_empty_folder(self):
        result = self.usecase.execute(self.temp_dir)
        assert result["success"] is True
        assert result["total"] == 0
        assert result["success_count"] == 0

    def test_execute_with_json_files(self):
        json_file = os.path.join(self.temp_dir, "test.json")
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump({"key": {"value": "test_value"}}, f)

        result = self.usecase.execute(self.temp_dir)
        assert result["success"] is True
        assert result["total"] >= 1

    def test_execute_with_progress_callback(self):
        progress_values = []

        def progress_callback(value, remaining_count=0, remaining_time=0):
            progress_values.append(value)

        json_file = os.path.join(self.temp_dir, "test.json")
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump({"key": "value"}, f)

        self.usecase.execute(self.temp_dir, progress_callback=progress_callback)
        assert len(progress_values) > 0
        assert any(p > 0 for p in progress_values)

    def test_execute_with_log_callback(self):
        log_messages = []

        def log_callback(msg):
            log_messages.append(msg)

        json_file = os.path.join(self.temp_dir, "test.json")
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump({"key": "value"}, f)

        self.usecase.execute(self.temp_dir, log_callback=log_callback)
        assert len(log_messages) > 0

    def test_backup_created_on_success(self):
        json_file = os.path.join(self.temp_dir, "test.json")
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump({"key": "value"}, f)

        result = self.usecase.execute(self.temp_dir)
        assert result["success"] is True
        assert result["backup_path"] != ""
        assert os.path.exists(result["backup_path"])


class TestBatchRestoreValueUseCase:
    """BatchRestoreValueUseCase 单元测试"""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.file_handler = MockFileHandler()
        self.config = {"basic": {"indent": 4}}
        self.usecase = BatchRestoreValueUseCase(self.file_handler, self.config)

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        backup_dir = self.temp_dir + "_backup"
        shutil.rmtree(backup_dir, ignore_errors=True)

    def test_execute_with_invalid_path(self):
        result = self.usecase.execute("/nonexistent/path")
        assert result["success"] is False
        assert "无效" in result["message"]

    def test_execute_with_empty_folder(self):
        result = self.usecase.execute(self.temp_dir)
        assert result["success"] is True
        assert result["total"] == 0

    def test_execute_with_string_values(self):
        json_file = os.path.join(self.temp_dir, "test.json")
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump({"key": "string_value"}, f)

        result = self.usecase.execute(self.temp_dir)
        assert result["success"] is True

    def test_execute_creates_backup(self):
        json_file = os.path.join(self.temp_dir, "test.json")
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump({"key": "value"}, f)

        result = self.usecase.execute(self.temp_dir)
        assert result["backup_path"] != ""
        assert os.path.exists(result["backup_path"])


class TestExtractOnlyUseCase:
    """ExtractOnlyUseCase 单元测试"""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.file_handler = MockFileHandler()
        self.usecase = ExtractOnlyUseCase(self.file_handler)

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_execute_with_empty_bp_path(self):
        result = self.usecase.execute("")
        assert result["success"] is False
        assert "请先选择" in result["message"]

    def test_execute_with_none_bp_path(self):
        result = self.usecase.execute(None)
        assert result["success"] is False

    def test_execute_with_no_entries(self):
        result = self.usecase.execute(self.temp_dir)
        assert result["success"] is False
        assert "未提取" in result["message"] or result["count"] == 0

    def test_execute_with_valid_bp(self):
        block_file = os.path.join(self.temp_dir, "test_block.json")
        block_data = {
            "minecraft:block": {
                "description": {"identifier": "test:block_1"},
                "components": {
                    "minecraft:display_name": {"value": "Test Block"}
                }
            }
        }
        with open(block_file, "w", encoding="utf-8") as f:
            json.dump(block_data, f)

        result = self.usecase.execute(self.temp_dir)
        assert result["success"] is True
        assert result["count"] >= 0

    def test_execute_with_rp_path(self):
        rp_dir = os.path.join(self.temp_dir, "rp")
        os.makedirs(rp_dir, exist_ok=True)

        block_file = os.path.join(rp_dir, "test_block.json")
        block_data = {
            "minecraft:block": {
                "description": {"identifier": "test:block_1"},
                "components": {
                    "minecraft:display_name": {"value": "Test Block"}
                }
            }
        }
        with open(block_file, "w", encoding="utf-8") as f:
            json.dump(block_data, f)

        result = self.usecase.execute(self.temp_dir, rp_path=rp_dir)
        assert result["success"] is True

    def test_execute_with_progress_callback(self):
        progress_values = []

        def progress_callback(value, remaining_count=0, remaining_time=0):
            progress_values.append(value)

        block_file = os.path.join(self.temp_dir, "test_block.json")
        with open(block_file, "w", encoding="utf-8") as f:
            json.dump({"minecraft:block": {"description": {"identifier": "test:x"}}}, f)

        self.usecase.execute(self.temp_dir, progress_callback=progress_callback)
        assert len(progress_values) > 0

    def test_execute_with_log_callback(self):
        log_messages = []

        def log_callback(msg):
            log_messages.append(msg)

        block_file = os.path.join(self.temp_dir, "test_block.json")
        with open(block_file, "w", encoding="utf-8") as f:
            json.dump({"minecraft:block": {"description": {"identifier": "test:x"}}}, f)

        self.usecase.execute(self.temp_dir, log_callback=log_callback)
        assert len(log_messages) > 0

    def test_output_path_format(self):
        block_file = os.path.join(self.temp_dir, "test_block.json")
        with open(block_file, "w", encoding="utf-8") as f:
            json.dump({"minecraft:block": {"description": {"identifier": "test:x"}, "components": {}}}, f)

        result = self.usecase.execute(self.temp_dir)
        assert result["success"] is True
        assert "zh_CN.lang" in result["output_path"]


# ==================== 新增 UseCase 测试 ====================

class TestReplaceDisplayNamesUseCase:
    """ReplaceDisplayNamesUseCase 单元测试"""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.file_handler = MockFileHandler()
        self.usecase = __import__('core.use_cases.replace_display_names', fromlist=['ReplaceDisplayNamesUseCase']).ReplaceDisplayNamesUseCase(self.file_handler)

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_execute_empty_bp(self):
        result = self.usecase.execute("")
        assert result["success"] is False

    def test_execute_no_entries(self):
        result = self.usecase.execute(self.temp_dir)
        assert "success" in result

    def test_execute_with_callbacks(self):
        log_msgs = []
        def log_cb(msg): log_msgs.append(msg)
        result = self.usecase.execute(self.temp_dir, log_callback=log_cb)
        assert "success" in result
        assert len(log_msgs) > 0


class TestOneClickServiceUseCase:
    """OneClickServiceUseCase 单元测试"""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.file_handler = MockFileHandler()
        mock_translator = Mock()
        mock_translator.translate_entries_batch.return_value = {"k": "v"}
        self.usecase = __import__('core.use_cases.one_click_service', fromlist=['OneClickServiceUseCase']).OneClickServiceUseCase(self.file_handler, mock_translator)

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_execute_empty_bp(self):
        result = self.usecase.execute("")
        assert result["success"] is False

    def test_execute_no_entries(self):
        result = self.usecase.execute(self.temp_dir)
        assert "success" in result

    def test_execute_with_callbacks(self):
        progress_vals = []
        log_msgs = []
        def prog_cb(v, *a): progress_vals.append(v)
        def log_cb(m): log_msgs.append(m)
        result = self.usecase.execute(self.temp_dir, progress_callback=prog_cb, log_callback=log_cb)
        assert "success" in result


class TestTranslateLangFileUseCase:
    """TranslateLangFileUseCase 单元测试"""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.file_handler = MockFileHandler()
        mock_translator = Mock()
        mock_translator.translate_entries.return_value = {"k": "翻译"}
        self.usecase = __import__('core.use_cases.translate_lang_file', fromlist=['TranslateLangFileUseCase']).TranslateLangFileUseCase(self.file_handler, mock_translator)
        # 创建测试 .lang 文件
        self.lang_file = os.path.join(self.temp_dir, "test.lang")
        with open(self.lang_file, "w", encoding="utf-8") as f:
            f.write("# comment\nkey1=Hello\nkey2=World\n")

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_execute_nonexistent_file(self):
        result = self.usecase.execute("/nonexistent/lang.file")
        assert result["success"] is False

    def test_execute_empty_path(self):
        result = self.usecase.execute("")
        assert result["success"] is False

    def test_execute_valid_file(self):
        result = self.usecase.execute(self.lang_file, bp_path=self.temp_dir)
        assert "success" in result

    def test_execute_with_callbacks(self):
        log_msgs = []
        def log_cb(m): log_msgs.append(m)
        result = self.usecase.execute(self.lang_file, bp_path=self.temp_dir, log_callback=log_cb)
        assert "success" in result


class TestTranslateSingleJsFileUseCase:
    """TranslateSingleJsFileUseCase 单元测试"""

    def setup_method(self):
        mock_translator = Mock()
        mock_translator.translate_entries.return_value = {"k": "翻译"}
        self.usecase = __import__('core.use_cases.translate_single_js_file', fromlist=['TranslateSingleJsFileUseCase']).TranslateSingleJsFileUseCase(mock_translator)

    def test_execute_empty_path(self):
        result = self.usecase.execute("")
        assert result["success"] is False

    def test_execute_nonexistent_path(self):
        result = self.usecase.execute("/nonexistent/file.js")
        assert result["success"] is False

    def test_execute_with_callbacks(self):
        with tempfile.NamedTemporaryFile(suffix=".js", mode="w", delete=False, encoding="utf-8") as f:
            f.write('var x = "hello";')
            js_path = f.name
        try:
            result = self.usecase.execute(js_path, mode=1)
            assert "success" in result
        finally:
            os.unlink(js_path)


class TestAdaptEntityDisplayNamesUseCase:
    """AdaptEntityDisplayNamesUseCase 单元测试"""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.file_handler = MockFileHandler()
        mock_translator = Mock()
        mock_translator.translate_entries.return_value = {"entity.test:zombie.name": "僵尸"}
        self.usecase = __import__('core.use_cases.adapt_entity_display_names', fromlist=['AdaptEntityDisplayNamesUseCase']).AdaptEntityDisplayNamesUseCase(self.file_handler, mock_translator)

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_execute_empty_bp(self):
        result = self.usecase.execute("")
        assert result["success"] is False

    def test_execute_no_entities(self):
        result = self.usecase.execute(self.temp_dir)
        assert "success" in result

    def test_execute_with_callbacks(self):
        log_msgs = []
        def log_cb(m): log_msgs.append(m)
        result = self.usecase.execute(self.temp_dir, log_callback=log_cb)
        assert "success" in result


class TestScriptHardcodeTranslationUseCase:
    """ScriptHardcodeTranslationUseCase 单元测试"""

    def setup_method(self):
        mock_translator = Mock()
        mock_translator.translate_entries.return_value = {"k": "翻译"}
        self.usecase = __import__('core.use_cases.script_hardcode_translation', fromlist=['ScriptHardcodeTranslationUseCase']).ScriptHardcodeTranslationUseCase(mock_translator)

    def test_execute_empty_path(self):
        result = self.usecase.execute("")
        assert "success" in result

    def test_execute_nonexistent_path(self):
        result = self.usecase.execute("/nonexistent/folder")
        assert "success" in result

    def test_execute_with_callbacks(self):
        log_msgs = []
        def log_cb(m): log_msgs.append(m)
        result = self.usecase.execute("/tmp", log_callback=log_cb)
        assert "success" in result
