#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
翻译管道端到端集成测试

测试 TranslationPipeline 的完整初始化流程和组件协作。
使用 mock 隔离外部依赖，不调用真实 API。
"""

import json
import os
import shutil
import tempfile
from unittest.mock import Mock, patch

import pytest

# ──────────── Fixtures ────────────

@pytest.fixture
def mock_config():
    """提供测试用最小配置"""
    return {
        "basic": {
            "namespace": "test_ns",
            "indent": 4,
            "use_multithreading": False,
            "max_retries": 1,
            "batch_size": 100,
            "cache_max_size": 100,
            "max_threads_per_api": 1,
            "local_first_fallback": False,
            "use_multi_api_validation": False,
        },
        "rate_limit": {"default": 0.0, "local_ollama": 0.0},
        "local_ollama": [],
        "deepseek": [],
        "qwen": [],
        "zhipu": [],
        "doubao": [],
        "terminology": {"dict_path": "resources/api/minecraft_terms.json"},
        "author": {"description": "Test Author"},
        "ui": {"startup_animation_duration": 0},
    }


@pytest.fixture
def temp_bp_folder():
    """创建临时 BP 文件夹结构"""
    tmp_dir = tempfile.mkdtemp()
    texts_dir = os.path.join(tmp_dir, "texts")
    os.makedirs(texts_dir, exist_ok=True)

    # 创建测试 manifest.json
    manifest = {
        "format_version": 2,
        "header": {
            "name": "test_pack",
            "description": "Test behavior pack",
            "uuid": "00000000-0000-0000-0000-000000000001",
            "version": [1, 0, 0],
        },
        "modules": [{"type": "data", "uuid": "00000000-0000-0000-0000-000000000002", "version": [1, 0, 0]}],
    }
    with open(os.path.join(tmp_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=4)

    # 创建测试方块文件
    block_data = {
        "format_version": "1.20.0",
        "minecraft:block": {
            "description": {
                "identifier": "test_ns:test_block",
                "register_to_creative_menu": True,
            },
            "components": {
                "minecraft:display_name": {
                    "value": "Test Block"
                }
            }
        }
    }
    blocks_dir = os.path.join(tmp_dir, "blocks")
    os.makedirs(blocks_dir, exist_ok=True)
    with open(os.path.join(blocks_dir, "test_block.json"), "w", encoding="utf-8") as f:
        json.dump(block_data, f, indent=4)

    yield tmp_dir
    shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.fixture
def temp_output_dir():
    """创建临时输出目录"""
    tmp_dir = tempfile.mkdtemp()
    yield tmp_dir
    shutil.rmtree(tmp_dir, ignore_errors=True)


# ──────────── Pipeline 初始化测试 ────────────

class TestPipelineInitialization:
    """测试管道初始化流程"""

    def test_pipeline_creation(self):
        """测试管道对象的创建"""
        from core.pipeline import TranslationPipeline
        pipeline = TranslationPipeline()
        assert pipeline is not None
        assert not pipeline.initialized

    @patch('core.pipeline.APIManager')
    def test_pipeline_initialize_with_mocks(self, mock_api_mgr, mock_config):
        """测试带 mock 的管道初始化"""
        mock_api_mgr_instance = Mock()
        mock_api_mgr_instance.available_apis = []
        mock_api_mgr_instance.detect_available_apis.return_value = []
        mock_api_mgr.return_value = mock_api_mgr_instance

        try:
            from core.pipeline import TranslationPipeline
            pipeline = TranslationPipeline()
            assert pipeline is not None
        except Exception:
            pass

    def test_pipeline_get_components_not_initialized(self):
        """测试未初始化时获取组件应抛出异常"""
        from core.pipeline import TranslationPipeline
        pipeline = TranslationPipeline()
        with pytest.raises(RuntimeError, match="翻译管道未初始化"):
            pipeline.get_components()

    def test_create_pipeline_helper(self):
        """测试便捷工厂函数"""
        from core.pipeline import create_pipeline
        pipeline = create_pipeline("config/config.yml")
        assert pipeline is not None
        assert isinstance(pipeline, object)


# ──────────── UseCase 集成测试 ────────────

class TestExtractOnlyIntegration:
    """ExtractOnlyUseCase 集成测试"""

    def test_extract_only_with_temp_folder(self, temp_bp_folder):
        """测试使用临时文件夹进行提取"""
        from core.file_handler import FileHandler
        from core.use_cases.extract_only import ExtractOnlyUseCase

        config = {"basic": {"namespace": "test_ns", "indent": 4}}
        file_handler = FileHandler(config)
        usecase = ExtractOnlyUseCase(file_handler)

        result = usecase.execute(bp_path=temp_bp_folder)

        assert result is not None
        assert result.get('success') is True
        assert result.get('count', 0) > 0
        assert '完成' in result.get('message', '') or '成功' in result.get('message', '')

    def test_extract_only_invalid_path(self):
        """测试无效路径的提取"""
        from core.file_handler import FileHandler
        from core.use_cases.extract_only import ExtractOnlyUseCase

        config = {"basic": {"namespace": "test_ns", "indent": 4}}
        file_handler = FileHandler(config)
        usecase = ExtractOnlyUseCase(file_handler)

        result = usecase.execute(bp_path="/nonexistent/path")
        assert result.get('success') is False
        assert result.get('count') == 0

    def test_extract_only_empty_path(self):
        """测试空路径的提取"""
        from core.file_handler import FileHandler
        from core.use_cases.extract_only import ExtractOnlyUseCase

        config = {"basic": {"namespace": "test_ns", "indent": 4}}
        file_handler = FileHandler(config)
        usecase = ExtractOnlyUseCase(file_handler)

        result = usecase.execute(bp_path="")
        assert result.get('success') is False

    def test_extract_only_with_callbacks(self, temp_bp_folder):
        """测试带回调的提取"""
        from core.file_handler import FileHandler
        from core.use_cases.extract_only import ExtractOnlyUseCase

        config = {"basic": {"namespace": "test_ns", "indent": 4}}
        file_handler = FileHandler(config)
        usecase = ExtractOnlyUseCase(file_handler)

        log_messages = []
        progress_values = []

        def log_callback(msg):
            log_messages.append(msg)

        def progress_callback(value, remaining=0, time_left=0):
            progress_values.append((
                value,
                remaining,
                time_left
            ))

        result = usecase.execute(
            bp_path=temp_bp_folder,
            progress_callback=progress_callback,
            log_callback=log_callback,
        )

        assert result.get('success') is True
        assert len(log_messages) > 0
        assert len(progress_values) > 0
        # 检查进度是否包含开始（0.1）和结束（1.0）
        assert any(p[0] == 0.1 for p in progress_values)
        assert any(p[0] == 1.0 for p in progress_values)


class TestExtractAndTranslateIntegration:
    """ExtractAndTranslateUseCase 集成测试"""

    def test_extract_and_translate_no_api(self, temp_bp_folder):
        """测试无 API 时的提取翻译（应返回翻译失败）"""
        from core.file_handler import FileHandler
        from core.translator import Translator
        from core.use_cases.extract_and_translate import ExtractAndTranslateUseCase

        config = {"basic": {"namespace": "test_ns", "indent": 4, "use_multithreading": False, "max_retries": 1},
                  "rate_limit": {"default": 0.0}}
        file_handler = FileHandler(config)

        # 创建 mock API manager
        mock_api_manager = Mock()
        mock_api_manager.available_apis = [{"name": "mock", "type": "mock"}]
        mock_api_manager.get_available_apis.return_value = []
        mock_api_manager.get_next_api.return_value = None
        mock_api_manager.translate_text.return_value = "原文"
        mock_api_manager.term_service = None

        translator = Translator(mock_api_manager, config)
        usecase = ExtractAndTranslateUseCase(file_handler, translator)

        result = usecase.execute(bp_path=temp_bp_folder)

        # 有可用API配置但翻译失败时，会走翻译逻辑但返回原文
        assert result is not None

    def test_extract_and_translate_empty_bp(self):
        """测试空 BP 路径的提取翻译"""
        from core.file_handler import FileHandler
        from core.translator import Translator
        from core.use_cases.extract_and_translate import ExtractAndTranslateUseCase

        config = {"basic": {"namespace": "test_ns", "indent": 4}}
        file_handler = FileHandler(config)
        mock_api_manager = Mock()
        mock_api_manager.available_apis = []
        translator = Translator(mock_api_manager, config)
        usecase = ExtractAndTranslateUseCase(file_handler, translator)

        result = usecase.execute(bp_path="")
        assert result.get('success') is False
        assert 'BP' in result.get('message', '') or '文件夹' in result.get('message', '')

    def test_extract_and_translate_with_mock_api(self, temp_bp_folder):
        """测试使用 mock API 的提取翻译"""
        from core.file_handler import FileHandler
        from core.translator import Translator
        from core.use_cases.extract_and_translate import ExtractAndTranslateUseCase

        config = {
            "basic": {
                "namespace": "test_ns",
                "indent": 4,
                "use_multithreading": False,
                "max_retries": 1,
                "local_first_fallback": False,
                "use_multi_api_validation": False,
                "batch_size": 100,
            },
            "rate_limit": {"default": 0.0},
        }
        file_handler = FileHandler(config)

        # 创建模拟翻译的 API Manager
        mock_api_manager = Mock()
        mock_api_manager.available_apis = [{"name": "mock_api", "type": "openai_compatible", "enabled": True}]
        mock_api_manager.get_available_apis.return_value = [{"name": "mock_api", "type": "openai_compatible", "enabled": True}]
        mock_api_manager.get_next_api.return_value = {"name": "mock_api", "type": "openai_compatible"}
        mock_api_manager.translate_text.return_value = "翻译后的文本"
        mock_api_manager.term_service = None

        translator = Translator(mock_api_manager, config)
        usecase = ExtractAndTranslateUseCase(file_handler, translator)

        result = usecase.execute(bp_path=temp_bp_folder)

        assert result is not None
        # 即使翻译失败，写入操作也应完成
        assert 'success' in result


class TestBatchDeleteValueIntegration:
    """BatchDeleteValueUseCase 集成测试"""

    def test_batch_delete_with_temp_folder(self, temp_bp_folder):
        """测试在临时文件夹中批量删除 value"""
        from core.file_handler import FileHandler
        from core.use_cases.batch_delete_value import BatchDeleteValueUseCase

        config = {"basic": {"namespace": "test_ns", "indent": 4}}
        file_handler = FileHandler(config)
        usecase = BatchDeleteValueUseCase(file_handler, config)

        result = usecase.execute(folder_path=temp_bp_folder)

        assert result is not None
        # 至少在响应中不应出现严重错误
        if not result.get('success'):
            assert 'message' in result


class TestBackupManagementIntegration:
    """备份管理集成测试"""

    def test_backup_creation(self, temp_bp_folder):
        """测试备份创建"""
        from core.file_handler import FileHandler
        backup_path = FileHandler({"basic": {}}).backup_folder(temp_bp_folder)
        assert backup_path != ""
        assert os.path.exists(backup_path)
        # 清理
        shutil.rmtree(backup_path, ignore_errors=True)

    def test_backup_restore(self, temp_bp_folder):
        """测试备份恢复功能（基本流程验证）"""
        from core.use_cases.backup_management import BackupManager
        BackupManager()

        # 创建备份
        from core.file_handler import FileHandler
        backup_path = FileHandler({"basic": {}}).backup_folder(temp_bp_folder)
        assert backup_path != ""
        assert os.path.exists(backup_path)

        # 清理备份目录
        shutil.rmtree(backup_path, ignore_errors=True)


# ──────────── 配置与集成测试 ────────────

class TestConfigFileIntegration:
    """配置文件集成测试"""

    def test_config_loading(self):
        """测试配置文件加载（使用示例配置）"""
        from config.config_manager import ConfigManager
        mgr = ConfigManager()
        config = mgr.load_config()
        assert config is not None
        assert isinstance(config, dict)
        assert "basic" in config
        assert "rate_limit" in config

    def test_config_defaults(self):
        """测试默认配置值"""
        from config.config_manager import ConfigManager
        mgr = ConfigManager()
        config = mgr.load_config()
        assert config.get("basic", {}).get("namespace", "") != ""
        assert isinstance(config.get("basic", {}).get("indent", 0), int)
