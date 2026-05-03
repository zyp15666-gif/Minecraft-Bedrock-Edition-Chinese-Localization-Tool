"""
端到端文件处理器测试 — 在临时目录构建BP结构，执行提取→写入完整流程
"""

import os
import json
import tempfile
import shutil
from pathlib import Path
import pytest

from core.file_handler import FileHandler


@pytest.fixture
def temp_bp():
    """创建临时BP目录结构"""
    tmp = tempfile.mkdtemp()
    bp = os.path.join(tmp, "BP")
    os.makedirs(os.path.join(bp, "blocks"), exist_ok=True)
    os.makedirs(os.path.join(bp, "items"), exist_ok=True)
    yield bp
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def file_handler():
    return FileHandler({"basic": {"namespace": "test_mod"}})


class TestExtractEntries:
    """提取条目测试"""

    def test_extract_block_with_display_name(self, temp_bp, file_handler):
        block_json = {
            "minecraft:block": {
                "description": {"identifier": "test_mod:stone_block"},
                "components": {
                    "minecraft:display_name": {"value": "Stone Block"}
                }
            }
        }
        path = os.path.join(temp_bp, "blocks", "stone.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(block_json, f)

        entries = file_handler.extract_entries(temp_bp)
        assert "tile.test_mod:stone_block.name" in entries
        assert entries["tile.test_mod:stone_block.name"] == "Stone Block"

    def test_extract_item_with_display_name(self, temp_bp, file_handler):
        item_json = {
            "minecraft:item": {
                "description": {"identifier": "test_mod:sword"},
                "components": {
                    "minecraft:display_name": {"value": "Steel Sword"}
                }
            }
        }
        path = os.path.join(temp_bp, "items", "sword.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(item_json, f)

        entries = file_handler.extract_entries(temp_bp)
        assert "item.test_mod:sword.name" in entries
        assert entries["item.test_mod:sword.name"] == "Steel Sword"

    def test_extract_skips_lang_key_display_name(self, temp_bp, file_handler):
        block_json = {
            "minecraft:block": {
                "description": {"identifier": "test_mod:gem"},
                "components": {
                    "minecraft:display_name": "tile.test_mod:gem.name"
                }
            }
        }
        path = os.path.join(temp_bp, "blocks", "gem.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(block_json, f)

        entries = file_handler.extract_entries(temp_bp)
        assert "tile.test_mod:gem.name" not in entries

    def test_extract_empty_folder(self, temp_bp, file_handler):
        entries = file_handler.extract_entries(temp_bp)
        assert entries == {}


class TestMergeAndWriteLang:
    """合并写入语言文件测试"""

    def test_merge_creates_file(self, temp_bp, file_handler):
        texts_dir = os.path.join(temp_bp, "texts")
        os.makedirs(texts_dir, exist_ok=True)

        entries = {
            "tile.test_mod:stone.name": "Stone Block",
            "item.test_mod:sword.name": "Steel Sword",
        }
        file_handler.merge_and_write_lang(temp_bp, entries)
        lang_path = os.path.join(temp_bp, "texts", "zh_CN.lang")
        assert os.path.exists(lang_path)

        with open(lang_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "tile.test_mod:stone.name=Stone Block" in content
        assert "item.test_mod:sword.name=Steel Sword" in content

    def test_merge_preserves_existing(self, temp_bp, file_handler):
        texts_dir = os.path.join(temp_bp, "texts")
        os.makedirs(texts_dir, exist_ok=True)
        lang_path = os.path.join(texts_dir, "zh_CN.lang")
        with open(lang_path, "w", encoding="utf-8") as f:
            f.write("tile.test_mod:old.name=Old Name\n")

        file_handler.merge_and_write_lang(temp_bp, {"tile.test_mod:new.name": "New Name"})
        with open(lang_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "Old Name" in content
        assert "New Name" in content

    def test_merge_newline_escaping(self, temp_bp, file_handler):
        texts_dir = os.path.join(temp_bp, "texts")
        os.makedirs(texts_dir, exist_ok=True)

        file_handler.merge_and_write_lang(temp_bp, {"tile.test_mod:multi.name": "Line1\nLine2"})
        lang_path = os.path.join(temp_bp, "texts", "zh_CN.lang")
        with open(lang_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "Line1\\nLine2" in content


class TestParseLangFile:
    """解析语言文件测试"""

    def test_parse_basic(self, file_handler):
        content = "key1=value1\nkey2=value2\n"
        tmp = tempfile.mktemp(suffix=".lang")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(content)
        try:
            entries = file_handler.parse_lang_file(tmp)
            assert entries == {"key1": "value1", "key2": "value2"}
        finally:
            os.unlink(tmp)

    def test_parse_unescapes_newline(self, file_handler):
        content = "key1=Line1\\nLine2\n"
        tmp = tempfile.mktemp(suffix=".lang")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(content)
        try:
            entries = file_handler.parse_lang_file(tmp)
            assert entries["key1"] == "Line1\nLine2"
        finally:
            os.unlink(tmp)

    def test_parse_skips_comments(self, file_handler):
        content = "## Comment\nkey1=value1\n"
        tmp = tempfile.mktemp(suffix=".lang")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(content)
        try:
            entries = file_handler.parse_lang_file(tmp)
            assert "## Comment" not in entries
            assert entries == {"key1": "value1"}
        finally:
            os.unlink(tmp)
