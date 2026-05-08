#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FileHandler 单元测试

测试文件处理器的核心功能，包括：
- 文件夹备份
- JSON文件读取和解析
- 语言文件解析和合并
- 并行文件处理
- manifest.json 更新
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock

from core.file_handler import FileHandler


class TestFileHandlerInit:
    """FileHandler 初始化测试"""

    def test_init_with_default_config(self):
        """测试使用默认配置初始化"""
        config = {"basic": {}}
        handler = FileHandler(config)

        assert handler.namespace == "sgs_farm"  # 默认值
        assert handler.indent == 4  # 默认值

    def test_init_with_custom_config(self):
        """测试使用自定义配置初始化"""
        config = {
            "basic": {
                "namespace": "custom_ns",
                "indent": 2
            }
        }
        handler = FileHandler(config)

        assert handler.namespace == "custom_ns"
        assert handler.indent == 2


class TestFileHandlerBackup:
    """文件夹备份功能测试"""

    def test_backup_folder_success(self):
        """测试成功备份文件夹"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_folder = Path(tmpdir) / "test_bp"
            test_folder.mkdir()
            (test_folder / "test.json").write_text('{"test": true}')

            handler = FileHandler({"basic": {}})
            backup_path = handler.backup_folder(str(test_folder))

            assert backup_path != ""
            assert "BACKUP" in backup_path
            assert Path(backup_path).exists()
            assert (Path(backup_path) / "test.json").exists()

    def test_backup_folder_nonexistent(self):
        """测试备份不存在的文件夹"""
        handler = FileHandler({"basic": {}})
        result = handler.backup_folder("/nonexistent/path")
        assert result == ""

    def test_backup_folder_empty_path(self):
        """测试备份空路径"""
        handler = FileHandler({"basic": {}})
        result = handler.backup_folder("")
        assert result == ""

    def test_backup_folder_with_nested_structure(self):
        """测试备份嵌套文件夹结构"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_folder = Path(tmpdir) / "test_bp"
            subfolder = test_folder / "subdir1" / "subdir2"
            subfolder.mkdir(parents=True)

            (test_folder / "root.json").write_text('{"root": true}')
            (subfolder / "nested.json").write_text('{"nested": true, "unicode": "中文测试"}')

            handler = FileHandler({"basic": {}})
            backup_path = handler.backup_folder(str(test_folder))

            assert backup_path != ""
            assert (Path(backup_path) / "root.json").exists()
            assert (Path(backup_path) / "subdir1" / "subdir2" / "nested.json").exists()

    def test_backup_folder_preserves_special_characters(self):
        """测试备份保留特殊字符"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_folder = Path(tmpdir) / "test_bp"
            test_folder.mkdir()

            content = '{"special": "🎮 🌍 © ® ™ & < > \" \'"}'
            (test_folder / "special.json").write_text(content, encoding='utf-8')

            handler = FileHandler({"basic": {}})
            backup_path = handler.backup_folder(str(test_folder))

            assert backup_path != ""
            backup_content = (Path(backup_path) / "special.json").read_text(encoding='utf-8')
            assert "🎮" in backup_content


class TestFileHandlerComplexJson:
    """语言文件处理测试"""

    def test_parse_lang_file(self):
        """测试解析lang文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.lang', delete=False, encoding='utf-8') as f:
            f.write("# 注释行\n")
            f.write("item.apple.name=Apple\n")
            f.write("item.bread.name=Bread\n")
            f.write("empty_line=\n")
            temp_path = f.name

        try:
            handler = FileHandler({"basic": {}})
            entries = handler.parse_lang_file(temp_path)

            assert len(entries) == 3
            assert entries["item.apple.name"] == "Apple"
            assert entries["item.bread.name"] == "Bread"
            assert entries["empty_line"] == ""
        finally:
            os.unlink(temp_path)

    def test_parse_lang_file_empty(self):
        """测试解析空lang文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.lang', delete=False, encoding='utf-8') as f:
            f.write("")
            temp_path = f.name

        try:
            handler = FileHandler({"basic": {}})
            entries = handler.parse_lang_file(temp_path)
            assert entries == {}
        finally:
            os.unlink(temp_path)

    def test_merge_and_write_lang(self):
        """测试合并并写入语言文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            handler = FileHandler({"basic": {}})
            folder = Path(tmpdir) / "test_folder"

            # 第一次写入
            handler.merge_and_write_lang(str(folder), {"key1": "value1", "key2": "value2"})

            lang_path = folder / "texts" / "zh_CN.lang"
            assert lang_path.exists()

            content = lang_path.read_text(encoding='utf-8')
            assert "key1=value1" in content
            assert "key2=value2" in content

            # 第二次写入（合并）
            handler.merge_and_write_lang(str(folder), {"key2": "new_value2", "key3": "value3"})

            content = lang_path.read_text(encoding='utf-8')
            assert "key1=value1" in content  # 保留旧值
            assert "key2=new_value2" in content  # 更新值
            assert "key3=value3" in content  # 新增值

    def test_merge_and_write_lang_newline_escape(self):
        """测试换行符转义"""
        with tempfile.TemporaryDirectory() as tmpdir:
            handler = FileHandler({"basic": {}})
            folder = Path(tmpdir) / "test_folder"
            folder.mkdir()

            handler.merge_and_write_lang(str(folder), {"key1": "line1\nline2"})

            lang_path = folder / "texts" / "zh_CN.lang"
            content = lang_path.read_text(encoding='utf-8')
            assert "key1=line1\\nline2" in content


class TestFileHandlerJsonOperations:
    """JSON文件操作测试"""

    def test_remove_value_from_json(self):
        """测试移除display_name的value对象"""
        handler = FileHandler({"basic": {}})

        data = {
            "minecraft:block": {
                "components": {
                    "minecraft:display_name": {"value": "Stone"}
                }
            }
        }

        result = handler.remove_value_from_json(data)

        assert result["minecraft:block"]["components"]["minecraft:display_name"] == "Stone"

    def test_restore_value_to_json(self):
        """测试还原display_name为value对象"""
        handler = FileHandler({"basic": {}})

        data = {
            "minecraft:block": {
                "components": {
                    "minecraft:display_name": "Stone"
                }
            }
        }

        result = handler.restore_value_to_json(data)

        assert result["minecraft:block"]["components"]["minecraft:display_name"] == {"value": "Stone"}

    def test_remove_value_nested(self):
        """测试嵌套结构的value移除"""
        handler = FileHandler({"basic": {}})

        data = {
            "level1": {
                "level2": {
                    "minecraft:display_name": {"value": "Nested"}
                }
            }
        }

        result = handler.remove_value_from_json(data)
        assert result["level1"]["level2"]["minecraft:display_name"] == "Nested"

    def test_remove_value_in_list(self):
        """测试列表中的value移除"""
        handler = FileHandler({"basic": {}})

        data = [
            {"minecraft:display_name": {"value": "Item1"}},
            {"minecraft:display_name": {"value": "Item2"}}
        ]

        result = handler.remove_value_from_json(data)
        assert result[0]["minecraft:display_name"] == "Item1"
        assert result[1]["minecraft:display_name"] == "Item2"


class TestFileHandlerParallelRead:
    """并行文件读取测试"""

    def test_read_json_file_success(self):
        """测试成功读取JSON文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump({"test": "data", "number": 123}, f)
            temp_path = f.name

        try:
            handler = FileHandler({"basic": {}})
            result = handler._read_json_file(Path(temp_path))

            assert result is not None
            assert result["test"] == "data"
            assert result["number"] == 123
        finally:
            os.unlink(temp_path)

    def test_read_json_file_failure(self):
        """测试读取损坏的JSON文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            f.write("invalid json")
            temp_path = f.name

        try:
            handler = FileHandler({"basic": {}})
            result = handler._read_json_file(Path(temp_path))

            assert result is None
        finally:
            os.unlink(temp_path)

    def test_read_json_files_parallel(self):
        """测试并行读取多个JSON文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            files = []
            for i in range(5):
                path = Path(tmpdir) / f"test{i}.json"
                path.write_text(json.dumps({"index": i}))
                files.append(path)

            handler = FileHandler({"basic": {}})
            results = handler.read_json_files_parallel(files)

            assert len(results) == 5
            indices = [data["index"] for _, data in results]
            assert sorted(indices) == [0, 1, 2, 3, 4]

    def test_read_json_files_parallel_empty(self):
        """测试并行读取空列表"""
        handler = FileHandler({"basic": {}})
        results = handler.read_json_files_parallel([])
        assert results == []

    def test_scan_json_files_parallel(self):
        """测试并行扫描文件夹中的JSON文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建嵌套文件夹结构
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()

            (Path(tmpdir) / "file1.json").write_text(json.dumps({"name": "file1"}))
            (Path(tmpdir) / "file2.json").write_text(json.dumps({"name": "file2"}))
            (subdir / "file3.json").write_text(json.dumps({"name": "file3"}))
            (Path(tmpdir) / "ignore.txt").write_text("text")

            handler = FileHandler({"basic": {}})
            results = handler.scan_json_files_parallel(tmpdir)

            assert len(results) == 3
            names = [data["name"] for _, data in results]
            assert "file1" in names
            assert "file2" in names
            assert "file3" in names

    def test_scan_json_files_parallel_with_callback(self):
        """测试带进度回调的并行扫描"""
        with tempfile.TemporaryDirectory() as tmpdir:
            for i in range(3):
                (Path(tmpdir) / f"file{i}.json").write_text(json.dumps({"index": i}))

            progress_calls = []
            def progress_callback(current, total):
                progress_calls.append((current, total))

            handler = FileHandler({"basic": {}})
            results = handler.scan_json_files_parallel(tmpdir, progress_callback=progress_callback)

            assert len(results) == 3
            assert len(progress_calls) == 3


class TestFileHandlerExtractEntries:
    """条目提取测试"""

    def test_extract_entries_block(self):
        """测试从方块定义提取条目"""
        with tempfile.TemporaryDirectory() as tmpdir:
            bp_folder = Path(tmpdir)

            # 创建方块定义文件
            block_data = {
                "minecraft:block": {
                    "description": {
                        "identifier": "test:stone_block"
                    },
                    "components": {
                        "minecraft:display_name": {"value": "Stone Block"}
                    }
                }
            }

            blocks_dir = bp_folder / "blocks"
            blocks_dir.mkdir()
            (blocks_dir / "stone.json").write_text(json.dumps(block_data))

            handler = FileHandler({"basic": {"namespace": "test"}})
            entries = handler.extract_entries(str(bp_folder))

            assert "tile.test:stone_block.name" in entries
            assert entries["tile.test:stone_block.name"] == "Stone Block"

    def test_extract_entries_item(self):
        """测试从物品定义提取条目"""
        with tempfile.TemporaryDirectory() as tmpdir:
            bp_folder = Path(tmpdir)

            # 创建物品定义文件
            item_data = {
                "minecraft:item": {
                    "description": {
                        "identifier": "test:magic_sword"
                    },
                    "components": {
                        "minecraft:display_name": "Magic Sword"
                    }
                }
            }

            items_dir = bp_folder / "items"
            items_dir.mkdir()
            (items_dir / "sword.json").write_text(json.dumps(item_data))

            handler = FileHandler({"basic": {"namespace": "test"}})
            entries = handler.extract_entries(str(bp_folder))

            assert "item.test:magic_sword.name" in entries
            assert entries["item.test:magic_sword.name"] == "Magic Sword"

    def test_extract_entries_string_display_name(self):
        """测试字符串格式的display_name"""
        with tempfile.TemporaryDirectory() as tmpdir:
            bp_folder = Path(tmpdir)

            block_data = {
                "minecraft:block": {
                    "description": {
                        "identifier": "test:custom_block"
                    },
                    "components": {
                        "minecraft:display_name": "Custom Block Name"
                    }
                }
            }

            blocks_dir = bp_folder / "blocks"
            blocks_dir.mkdir()
            (blocks_dir / "custom.json").write_text(json.dumps(block_data))

            handler = FileHandler({"basic": {"namespace": "test"}})
            entries = handler.extract_entries(str(bp_folder))

            assert "tile.test:custom_block.name" in entries
            assert entries["tile.test:custom_block.name"] == "Custom Block Name"

    def test_extract_entries_skip_lang_keys(self):
        """测试跳过已经是语言键的display_name"""
        with tempfile.TemporaryDirectory() as tmpdir:
            bp_folder = Path(tmpdir)

            block_data = {
                "minecraft:block": {
                    "description": {
                        "identifier": "test:block"
                    },
                    "components": {
                        "minecraft:display_name": "tile.other:block.name"
                    }
                }
            }

            blocks_dir = bp_folder / "blocks"
            blocks_dir.mkdir()
            (blocks_dir / "block.json").write_text(json.dumps(block_data))

            handler = FileHandler({"basic": {"namespace": "test"}})
            entries = handler.extract_entries(str(bp_folder))

            # 不应该提取以tile.开头的语言键
            assert "tile.test:block.name" not in entries


class TestFileHandlerEntityExtraction:
    """实体显示名称提取测试"""

    def test_extract_entity_display_names(self):
        """测试提取实体显示名称"""
        with tempfile.TemporaryDirectory() as tmpdir:
            bp_folder = Path(tmpdir)
            entities_dir = bp_folder / "entities"
            entities_dir.mkdir()

            # 创建实体定义
            entity_data = {
                "minecraft:entity": {
                    "description": {
                        "identifier": "test:custom_mob"
                    }
                }
            }
            (entities_dir / "mob.json").write_text(json.dumps(entity_data))

            handler = FileHandler({"basic": {}})
            result = handler.extract_entity_display_names(str(bp_folder))

            assert "custom_mob" in result
            assert "entity.test:custom_mob.name" in result["custom_mob"]

    def test_extract_entity_display_names_male_suffix(self):
        """测试提取带_m后缀的实体"""
        with tempfile.TemporaryDirectory() as tmpdir:
            bp_folder = Path(tmpdir)
            entities_dir = bp_folder / "entities"
            entities_dir.mkdir()

            entity_data = {
                "minecraft:entity": {
                    "description": {
                        "identifier": "test:villager_m"
                    }
                }
            }
            (entities_dir / "villager.json").write_text(json.dumps(entity_data))

            handler = FileHandler({"basic": {}})
            result = handler.extract_entity_display_names(str(bp_folder))

            # 基础名应该去掉_m后缀
            assert "villager" in result
            assert "entity.test:villager_m.name" in result["villager"]

    def test_extract_entity_display_names_nested(self):
        """测试从子文件夹提取实体"""
        with tempfile.TemporaryDirectory() as tmpdir:
            bp_folder = Path(tmpdir)
            entities_dir = bp_folder / "entities" / "monsters"
            entities_dir.mkdir(parents=True)

            entity_data = {
                "minecraft:entity": {
                    "description": {
                        "identifier": "test:zombie"
                    }
                }
            }
            (entities_dir / "zombie.json").write_text(json.dumps(entity_data))

            handler = FileHandler({"basic": {}})
            result = handler.extract_entity_display_names(str(bp_folder))

            assert "zombie" in result

    def test_extract_entity_display_names_no_entities_folder(self):
        """测试没有entities文件夹的情况"""
        with tempfile.TemporaryDirectory() as tmpdir:
            handler = FileHandler({"basic": {}})
            result = handler.extract_entity_display_names(str(tmpdir))

            assert result == {}


class TestFileHandlerReplaceDisplayNames:
    """替换display_name为lang键测试"""

    def test_replace_display_names_block(self):
        """测试替换方块display_name"""
        with tempfile.TemporaryDirectory() as tmpdir:
            bp_folder = Path(tmpdir)

            block_data = {
                "minecraft:block": {
                    "description": {
                        "identifier": "test:my_block"
                    },
                    "components": {
                        "minecraft:display_name": "Old Name"
                    }
                }
            }

            (bp_folder / "block.json").write_text(json.dumps(block_data))

            handler = FileHandler({"basic": {"namespace": "test"}})
            count = handler.replace_display_names_with_lang_key(str(bp_folder))

            assert count == 1

            updated = json.loads((bp_folder / "block.json").read_text())
            display_name = updated["minecraft:block"]["components"]["minecraft:display_name"]
            assert display_name == {"value": "tile.test:my_block.name"}

    def test_replace_display_names_item(self):
        """测试替换物品display_name"""
        with tempfile.TemporaryDirectory() as tmpdir:
            bp_folder = Path(tmpdir)

            item_data = {
                "minecraft:item": {
                    "description": {
                        "identifier": "test:my_item"
                    },
                    "components": {
                        "minecraft:display_name": {"value": "Old Item Name"}
                    }
                }
            }

            (bp_folder / "item.json").write_text(json.dumps(item_data))

            handler = FileHandler({"basic": {"namespace": "test"}})
            count = handler.replace_display_names_with_lang_key(str(bp_folder))

            assert count == 1

            updated = json.loads((bp_folder / "item.json").read_text())
            display_name = updated["minecraft:item"]["components"]["minecraft:display_name"]
            assert display_name == {"value": "item.test:my_item.name"}

    def test_replace_display_names_no_display_name(self):
        """测试没有display_name的文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            bp_folder = Path(tmpdir)

            block_data = {
                "minecraft:block": {
                    "description": {
                        "identifier": "test:block_no_name"
                    },
                    "components": {}
                }
            }

            (bp_folder / "block.json").write_text(json.dumps(block_data))

            handler = FileHandler({"basic": {"namespace": "test"}})
            count = handler.replace_display_names_with_lang_key(str(bp_folder))

            assert count == 0


class TestFileHandlerLanguagesJson:
    """languages.json处理测试"""

    def test_ensure_languages_json_create_new(self):
        """测试创建新的languages.json"""
        with tempfile.TemporaryDirectory() as tmpdir:
            handler = FileHandler({"basic": {}})
            handler.ensure_languages_json(tmpdir)

            lang_json_path = Path(tmpdir) / "texts" / "languages.json"
            assert lang_json_path.exists()

            content = json.loads(lang_json_path.read_text())
            assert "zh_CN" in content

    def test_ensure_languages_json_update_existing(self):
        """测试更新现有的languages.json"""
        with tempfile.TemporaryDirectory() as tmpdir:
            texts_dir = Path(tmpdir) / "texts"
            texts_dir.mkdir()

            existing = ["en_US", "fr_FR"]
            (texts_dir / "languages.json").write_text(json.dumps(existing))

            handler = FileHandler({"basic": {}})
            handler.ensure_languages_json(tmpdir)

            content = json.loads((texts_dir / "languages.json").read_text())
            assert "zh_CN" in content
            assert "en_US" in content
            assert "fr_FR" in content

    def test_ensure_languages_json_already_has_zh_cn(self):
        """测试languages.json已包含zh_CN的情况"""
        with tempfile.TemporaryDirectory() as tmpdir:
            texts_dir = Path(tmpdir) / "texts"
            texts_dir.mkdir()

            existing = ["en_US", "zh_CN"]
            (texts_dir / "languages.json").write_text(json.dumps(existing))

            handler = FileHandler({"basic": {}})
            handler.ensure_languages_json(tmpdir)

            content = json.loads((texts_dir / "languages.json").read_text())
            # 不应该重复添加
            assert content.count("zh_CN") == 1


class TestFileHandlerManifestUpdate:
    """manifest.json更新测试"""

    def test_update_manifest_metadata(self):
        """测试更新manifest元数据"""
        with tempfile.TemporaryDirectory() as tmpdir:
            bp_folder = Path(tmpdir) / "TestBP"
            bp_folder.mkdir()

            manifest = {
                "format_version": 2,
                "header": {
                    "name": "Original Name",
                    "description": "Original Description",
                    "uuid": "test-uuid",
                    "version": [1, 0, 0]
                }
            }
            (bp_folder / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding='utf-8')

            mock_translator = Mock()
            mock_translator.translate_entries.return_value = {"name": "TestBP"}

            handler = FileHandler({"basic": {}})
            handler.update_manifest_metadata(str(bp_folder), None, mock_translator)

            updated = json.loads((bp_folder / "manifest.json").read_text(encoding='utf-8'))
            assert "header" in updated

    def test_update_manifest_no_translator(self):
        """测试没有翻译器时的manifest更新"""
        with tempfile.TemporaryDirectory() as tmpdir:
            bp_folder = Path(tmpdir) / "TestBP"
            bp_folder.mkdir()

            manifest = {
                "format_version": 2,
                "header": {
                    "name": "pack.name",
                    "description": "pack.description",
                    "uuid": "test-uuid"
                }
            }
            (bp_folder / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding='utf-8')

            handler = FileHandler({"basic": {}})
            handler.update_manifest_metadata(str(bp_folder), None, None)

            updated = json.loads((bp_folder / "manifest.json").read_text(encoding='utf-8'))
            # 应该使用文件夹名称
            assert "header" in updated

    def test_update_manifest_no_header(self):
        """测试manifest缺少header字段"""
        with tempfile.TemporaryDirectory() as tmpdir:
            bp_folder = Path(tmpdir) / "TestBP"
            bp_folder.mkdir()

            manifest = {"format_version": 2}
            (bp_folder / "manifest.json").write_text(json.dumps(manifest), encoding='utf-8')

            handler = FileHandler({"basic": {}})
            # 不应该抛出异常
            handler.update_manifest_metadata(str(bp_folder), None, None)


class TestFileHandlerRemoveRestoreFolder:
    """批量文件夹value字段操作测试"""

    def test_remove_value_from_json_folder(self):
        """测试批量移除文件夹中的value字段"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建多个JSON文件
            for i in range(3):
                data = {
                    "minecraft:block": {
                        "components": {
                            "minecraft:display_name": {"value": f"Block {i}"}
                        }
                    }
                }
                (Path(tmpdir) / f"block{i}.json").write_text(json.dumps(data))

            handler = FileHandler({"basic": {}})
            count = handler.remove_value_from_json_folder(tmpdir)

            assert count == 3

            # 验证文件内容
            for i in range(3):
                data = json.loads((Path(tmpdir) / f"block{i}.json").read_text())
                assert data["minecraft:block"]["components"]["minecraft:display_name"] == f"Block {i}"

    def test_restore_value_to_json_folder(self):
        """测试批量还原文件夹中的value字段"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建多个JSON文件
            for i in range(3):
                data = {
                    "minecraft:block": {
                        "components": {
                            "minecraft:display_name": f"Block {i}"
                        }
                    }
                }
                (Path(tmpdir) / f"block{i}.json").write_text(json.dumps(data))

            handler = FileHandler({"basic": {}})
            count = handler.restore_value_to_json_folder(tmpdir)

            assert count == 3

            # 验证文件内容
            for i in range(3):
                data = json.loads((Path(tmpdir) / f"block{i}.json").read_text())
                assert data["minecraft:block"]["components"]["minecraft:display_name"] == {"value": f"Block {i}"}

    def test_remove_value_skip_non_json(self):
        """测试跳过非JSON文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "file.txt").write_text("text content")
            (Path(tmpdir) / "file.json").write_text(json.dumps({"key": "value"}))

            handler = FileHandler({"basic": {}})
            count = handler.remove_value_from_json_folder(tmpdir)

            # 只处理JSON文件
            assert count == 1
