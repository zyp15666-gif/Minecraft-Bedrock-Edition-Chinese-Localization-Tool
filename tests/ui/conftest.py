#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI测试配置文件 - 简化版

提供基本的mock对象用于UI层测试
"""

import os
import sys
from unittest.mock import Mock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class MockPage:
    """模拟Flet页面对象"""

    def __init__(self):
        self.controls = []
        self.snack_bar = None
        self.dialog = None
        self.data = {}
        self.session = {}
        self._update_called = False

    def update(self):
        """模拟页面更新"""
        self._update_called = True

    def run_task(self, coro):
        """模拟运行异步任务"""
        pass


@pytest.fixture
def mock_page():
    """创建mock页面对象"""
    return MockPage()


@pytest.fixture
def mock_app_service():
    """创建mock应用服务"""
    service = Mock()
    service.available_apis = []
    service.extract_only = Mock(return_value={'success': True, 'message': '提取成功'})
    service.extract_and_translate = Mock(return_value={'success': True, 'message': '翻译成功'})
    service.one_click_service = Mock(return_value={'success': True, 'message': '一条龙服务完成'})
    return service


@pytest.fixture
def mock_dialog_manager():
    """创建mock对话框管理器"""
    manager = Mock()
    manager.last_error_title = None
    manager.last_error_message = None
    manager.last_success_title = None
    manager.last_success_message = None

    def mock_show_error(title, message):
        manager.last_error_title = title
        manager.last_error_message = message

    def mock_show_success(title, message):
        manager.last_success_title = title
        manager.last_success_message = message

    manager.show_error = mock_show_error
    manager.show_success = mock_show_success

    return manager


@pytest.fixture
def mock_task_service():
    """创建mock后台任务服务"""
    service = Mock()
    service.run = Mock()
    service.schedule_on_main_thread = Mock()
    return service


@pytest.fixture
def mock_config():
    """创建mock配置"""
    return {
        'basic': {
            'max_threads': 4,
            'cache_max_size': 2000
        },
        'apis': []
    }


@pytest.fixture
def mock_bp_path(tmp_path):
    """创建mock BP文件夹路径"""
    bp_dir = tmp_path / "test_bp"
    bp_dir.mkdir()

    # 创建一些测试文件
    (bp_dir / "manifest.json").write_text('{"format_version": 1}')
    texts_dir = bp_dir / "texts"
    texts_dir.mkdir()
    (texts_dir / "en_US.lang").write_text("test.key=Test Value\n")

    return str(bp_dir)
