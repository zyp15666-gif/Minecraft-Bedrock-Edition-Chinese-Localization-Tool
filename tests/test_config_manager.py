#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
config/config_manager.py 单元测试
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock
from config.config_manager import ConfigManager


class TestConfigManager:
    def test_default_config(self):
        manager = ConfigManager()
        config = manager.config
        assert isinstance(config, dict)

    def test_load_config(self):
        manager = ConfigManager()
        config = manager.load_config()
        assert isinstance(config, dict)

    def test_env_variable_resolution(self):
        os.environ["DEEPSEEK_API_KEY"] = "env-test-key-1234567890"
        try:
            manager = ConfigManager()
            test_config = {
                "deepseek": [{
                    "name": "deepseek-test",
                    "type": "openai_compatible",
                    "api_url": "https://api.deepseek.com",
                    "api_key": "你的API密钥",
                    "model": "deepseek-chat",
                }]
            }
            manager._resolve_env_variables(test_config)

            for api in test_config["deepseek"]:
                if isinstance(api, dict) and api.get("name") == "deepseek-test":
                    assert api.get("api_key") == "env-test-key-1234567890"
        finally:
            del os.environ["DEEPSEEK_API_KEY"]

    def test_env_variable_not_overwrite_valid_key(self):
        os.environ["DEEPSEEK_API_KEY"] = "env-key"
        try:
            manager = ConfigManager()
            test_config = {
                "deepseek": [{
                    "name": "deepseek-test",
                    "api_key": "sk-valid-key-1234567890",
                }]
            }
            manager._resolve_env_variables(test_config)

            for api in test_config["deepseek"]:
                if isinstance(api, dict) and api.get("name") == "deepseek-test":
                    assert api.get("api_key") == "sk-valid-key-1234567890"
        finally:
            del os.environ["DEEPSEEK_API_KEY"]

    def test_merge_configs(self):
        manager = ConfigManager()
        base = {"a": 1, "b": {"c": 2}}
        override = {"b": {"d": 3}, "e": 4}
        manager._merge_configs(base, override)
        assert base["b"]["c"] == 2
        assert base["b"]["d"] == 3
        assert base["e"] == 4

    def test_get_config_path(self):
        manager = ConfigManager()
        path = manager._get_config_path()
        assert isinstance(path, Path)

    def test_find_valid_documents_path(self):
        manager = ConfigManager()
        path = manager._find_valid_documents_path()
        assert isinstance(path, Path)
        assert path.exists()
        assert path.is_dir()

    def test_url_pattern_validation(self):
        manager = ConfigManager()
        valid_urls = [
            "http://api.example.com",
            "https://api.example.com",
            "http://localhost:8080",
            "http://192.168.1.1:5000",
            "https://api.deepseek.com/v1",
        ]
        invalid_urls = [
            "ftp://api.example.com",
            "api.example.com",
            "not a url",
            "",
        ]
        for url in valid_urls:
            assert manager._URL_PATTERN.match(url), f"URL should be valid: {url}"
        for url in invalid_urls:
            assert not manager._URL_PATTERN.match(url), f"URL should be invalid: {url}"

    def test_validate_config_warns_invalid_api_url(self):
        manager = ConfigManager()
        test_config = {
            "basic": {
                "namespace": "test",
                "max_workers": 5,
                "cache_max_size": 1000,
            },
            "rate_limit": {"default": 0.1},
            "deepseek": [{
                "name": "test-api",
                "api_url": "not-a-valid-url",
            }]
        }
        result = manager.validate_config(test_config)
        assert len(result["warnings"]) > 0
        assert any("api_url" in w.lower() for w in result["warnings"])

    def test_author_config_in_default_config(self):
        manager = ConfigManager()
        assert "author" in manager.config
        assert "description" in manager.config["author"]
        desc = manager.config["author"]["description"]
        assert isinstance(desc, str)
        assert len(desc) > 0

    def test_strip_runtime_paths(self):
        manager = ConfigManager()
        test_config = {
            "bp_folder": "/some/path",
            "rp_folder": "/some/path",
            "basic": {
                "bp_path": "/another/path",
                "last_folder": "/last/path",
            }
        }
        manager._strip_runtime_paths(test_config)
        assert "bp_folder" not in test_config
        assert "rp_folder" not in test_config
        assert "bp_path" not in test_config.get("basic", {})
        assert "last_folder" not in test_config.get("basic", {})

    def test_restore_default_config_preserves_api_keys(self):
        manager = ConfigManager()
        original_deepseek = manager.config.get("deepseek", [])
        manager.config["deepseek"] = [{"name": "test", "api_key": "sk-test123"}]
        manager.restore_default_config(keep_api_keys=True)
        assert any(api.get("api_key") == "sk-test123" for api in manager.config.get("deepseek", []))
        manager.config["deepseek"] = original_deepseek

    def test_export_import_config(self, tmp_path):
        manager = ConfigManager()
        export_file = tmp_path / "export.yml"
        result = manager.export_config(str(export_file))
        assert result is True
        assert export_file.exists()

        new_manager = ConfigManager()
        new_manager.config = {"test": "value"}
        result = new_manager.import_config(str(export_file), merge=False)
        assert result is True
        assert new_manager.config.get("basic", {}).get("namespace") == "sgs_farm"

    def test_get_function_buttons_config(self):
        manager = ConfigManager()
        buttons = manager.get_function_buttons_config()
        assert isinstance(buttons, list)
        if buttons:
            assert 'id' in buttons[0]
            assert 'label' in buttons[0]
            assert 'icon' in buttons[0]
            assert 'enabled' in buttons[0]
            assert 'order' in buttons[0]
            assert all(b.get('order', 999) <= 999 for b in buttons)

    def test_update_function_buttons_config(self):
        manager = ConfigManager()
        test_buttons = [
            {'id': 'test_btn', 'label': 'Test', 'icon': 'BUG_REPORT', 'enabled': False, 'order': 1}
        ]
        result = manager.update_function_buttons_config(test_buttons)
        assert result is True
        assert 'ui' in manager.config
        assert 'function_buttons' in manager.config['ui']

    def test_get_function_button_by_id(self):
        manager = ConfigManager()
        buttons = manager.get_function_buttons_config()
        if buttons:
            first_btn_id = buttons[0].get('id')
            found = manager.get_function_button_by_id(first_btn_id)
            assert found is not None
            assert found.get('id') == first_btn_id

        not_found = manager.get_function_button_by_id('nonexistent_btn_id')
        assert not_found is None


class TestConfigValidation:
    """配置校验测试"""

    def test_validate_button_config_valid(self):
        """测试有效按钮配置校验"""
        manager = ConfigManager()
        valid_button = {
            'id': 'test_btn',
            'label': 'Test Button',
            'icon': 'BUG_REPORT',
            'enabled': True,
            'order': 1
        }
        result = manager._validate_button_config(valid_button)
        assert result is not None
        assert result['id'] == 'test_btn'

    def test_validate_button_config_missing_fields(self):
        """测试缺少字段的按钮配置"""
        manager = ConfigManager()
        invalid_button = {'id': 'test_btn', 'label': 'Test'}
        result = manager._validate_button_config(invalid_button)
        assert result is None

    def test_validate_button_config_invalid_type(self):
        """测试无效类型的按钮配置"""
        manager = ConfigManager()
        invalid_button = {
            'id': 'test_btn',
            'label': 'Test',
            'icon': 'BUG_REPORT',
            'enabled': 'yes',
            'order': 1
        }
        result = manager._validate_button_config(invalid_button)
        assert result is not None
        assert result['enabled'] is True

    def test_validate_env_value_valid(self):
        """测试有效的环境变量值"""
        manager = ConfigManager()
        valid_value = "sk-1234567890abcdef"
        assert manager._validate_env_value(valid_value, "TEST_KEY") is True

    def test_validate_env_value_with_injection(self):
        """测试包含注入风险的环境变量值"""
        manager = ConfigManager()
        dangerous_value = "sk-123'; rm -rf /;"
        assert manager._validate_env_value(dangerous_value, "TEST_KEY") is False

    def test_validate_env_value_with_newline(self):
        """测试包含换行符的环境变量值"""
        manager = ConfigManager()
        dangerous_value = "sk-123\ncurl malicious.com"
        assert manager._validate_env_value(dangerous_value, "TEST_KEY") is False

    def test_validate_env_value_too_long(self):
        """测试过长的环境变量值"""
        manager = ConfigManager()
        long_value = "a" * 600
        assert manager._validate_env_value(long_value, "TEST_KEY") is False

    def test_validate_env_value_empty(self):
        """测试空的环境变量值"""
        manager = ConfigManager()
        assert manager._validate_env_value("", "TEST_KEY") is False
        assert manager._validate_env_value(None, "TEST_KEY") is False


class TestLoadConfigWithValidation:
    """加载配置时校验测试"""

    def test_load_config_raise_on_error_false(self):
        """测试不抛出异常的加载"""
        manager = ConfigManager()
        config = manager.load_config(raise_on_error=False)
        assert config is not None

    def test_load_config_with_errors(self):
        """测试加载包含错误的配置"""
        manager = ConfigManager()
        manager.config = {
            'basic': {
                'namespace': 'test',
                'max_workers': 999,
                'cache_max_size': -100
            }
        }
        result = manager.validate_config(manager.config)
        assert result['valid'] is False or len(result['warnings']) > 0
