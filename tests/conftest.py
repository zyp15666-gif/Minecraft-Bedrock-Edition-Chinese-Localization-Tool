#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pytest fixtures 和共享测试资源
"""

import sys
from unittest.mock import MagicMock, Mock

import pytest


@pytest.fixture
def ui_scale():
    """DialogManager 等组件所需的最小 ui_scale 字典。"""
    return {
        "section_title_size": 16,
        "body_size": 12,
        "label_size": 11,
    }


@pytest.fixture(scope="session")
def mock_logger():
    """提供共享的 mock logger"""
    return Mock()


@pytest.fixture(scope="session")
def mock_core_modules(mock_logger):
    """在 session 级别 Mock 所有核心模块"""
    mock_modules = {
        'core.quality_checker': Mock(),
        'core.log_manager': Mock(),
        'core.utils': Mock(),
        'core.metrics_collector': Mock(),
        'core.exceptions': Mock(),
    }

    mock_modules['core.log_manager'].get_logger.return_value = mock_logger

    for module_name, mock_module in mock_modules.items():
        if module_name not in sys.modules:
            sys.modules[module_name] = mock_module

    yield mock_modules

    for module_name in mock_modules:
        if module_name in sys.modules:
            del sys.modules[module_name]


@pytest.fixture(scope="session")
def mock_api_modules(mock_logger):
    """在 session 级别 Mock 所有 API 模块"""
    mock_modules = {
        'api.translation_prompts': Mock(),
        'api.api_client': Mock(),
        'api.translation_cache': Mock(),
        'api.load_balancer': Mock(),
        'api.api_monitor': Mock(),
        'api.translation_strategy': Mock(),
        'api.interfaces': Mock(),
        'api.terminology_service': Mock(),
    }

    for module_name, mock_module in mock_modules.items():
        if module_name not in sys.modules:
            sys.modules[module_name] = mock_module

    yield mock_modules

    for module_name in mock_modules:
        if module_name in sys.modules:
            del sys.modules[module_name]


@pytest.fixture
def mock_api_response():
    """提供标准 API 响应 Mock"""
    return MagicMock()


@pytest.fixture
def mock_api_config():
    """提供标准 API 配置"""
    return {
        "name": "test_api",
        "api_url": "https://api.test.com/v1/chat/completions",
        "api_key": "test-key-123",
        "model": "test-model",
        "enabled": True,
        "priority": 1,
        "weight": 1.0,
        "max_tokens": 2000,
        "temperature": 0.3,
    }


@pytest.fixture
def sample_translation_dict():
    """提供样例翻译字典"""
    return {
        "item.diamond_sword": "钻石剑",
        "entity.minecraft.pig": "猪",
        "tile.stone.name": "石头",
    }


@pytest.fixture
def sample_lang_content():
    """提供样例 .lang 文件内容"""
    return """# Test Language File
item.diamond_sword=钻石剑
entity.minecraft.pig=猪
tile.stone.name=石头
action.hint=点击 %1$s 执行操作"""


@pytest.fixture
def temp_config_file(tmp_path):
    """提供临时配置文件路径"""
    config_file = tmp_path / "test_config.yml"
    return config_file
