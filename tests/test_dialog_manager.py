#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI对话框管理器测试
"""

from unittest.mock import Mock

import flet as ft
import pytest


class TestDialogManager:
    """DialogManager单元测试"""

    @pytest.fixture
    def mock_page(self):
        """创建模拟的Flet页面"""
        page = Mock()
        page.show_dialog = Mock()
        page.pop_dialog = Mock()
        return page

    @pytest.fixture
    def mock_config_manager(self):
        """创建模拟的配置管理器"""
        manager = Mock()
        manager.config = {'basic': {'log_level': 'INFO'}}
        return manager

    @pytest.fixture
    def mock_api_manager(self):
        """创建模拟的API管理器"""
        manager = Mock()
        manager.api_stats = {'total_calls': 100}
        return manager

    @pytest.fixture
    def log_callback(self):
        """创建日志回调"""
        return Mock()

    @pytest.fixture
    def dialog_manager(self, mock_page, mock_config_manager, mock_api_manager, log_callback):
        """创建DialogManager实例"""
        from ui.dialog_manager import DialogManager
        return DialogManager(
            page=mock_page,
            config_manager=mock_config_manager,
            api_manager=mock_api_manager,
            log_callback=log_callback
        )

    def test_show_error_dialog(self, dialog_manager, mock_page):
        """测试错误对话框显示"""
        dialog_manager.show_error_dialog("测试错误", "这是一条错误消息")

        mock_page.show_dialog.assert_called_once()
        dialog = mock_page.show_dialog.call_args[0][0]
        assert isinstance(dialog, ft.AlertDialog)
        mock_page.pop_dialog.assert_not_called()

    def test_show_success_dialog(self, dialog_manager, mock_page):
        """测试成功对话框显示"""
        dialog_manager.show_success_dialog("测试成功", "操作已成功完成")

        mock_page.show_dialog.assert_called_once()
        dialog = mock_page.show_dialog.call_args[0][0]
        assert isinstance(dialog, ft.AlertDialog)

    def test_show_info_dialog(self, dialog_manager, mock_page):
        """测试信息对话框显示"""
        dialog_manager.show_info_dialog("提示", "这是一条信息")

        mock_page.show_dialog.assert_called_once()

    def test_show_confirm_dialog_calls_on_confirm(self, dialog_manager, mock_page):
        """测试确认对话框回调"""
        on_confirm = Mock()

        dialog_manager.show_confirm_dialog(
            title="确认操作",
            message="确定要继续吗？",
            on_confirm=on_confirm
        )

        mock_page.show_dialog.assert_called_once()
        dialog = mock_page.show_dialog.call_args[0][0]

        assert isinstance(dialog, ft.AlertDialog)
        assert len(dialog.actions) == 2

    def test_show_confirm_dialog_dangerous_style(self, dialog_manager, mock_page):
        """测试危险操作确认对话框使用红色按钮"""
        dialog_manager.show_confirm_dialog(
            title="危险操作",
            message="此操作不可撤销！",
            on_confirm=Mock(),
            is_dangerous=True
        )

        mock_page.show_dialog.assert_called_once()

    def test_show_log_dialog(self, dialog_manager, mock_page):
        """测试日志对话框显示"""
        log_text = ["[2024-01-01] 信息1", "[2024-01-01] 信息2", "错误日志"]

        dialog_manager.show_log_dialog(log_text, "测试日志")

        mock_page.show_dialog.assert_called_once()

    def test_show_performance_monitor_dialog(self, dialog_manager, mock_page, ui_scale):
        """测试性能监控对话框显示"""
        stats = {
            'system': {
                'memory_usage_mb': 100.5,
                'cpu_percent': 25.0,
                'thread_count': 8
            },
            'translation_cache': {
                'hits': 80,
                'misses': 20
            },
            'api': {
                'total_calls': 100,
                'successful_calls': 95,
                'failed_calls': 5
            }
        }

        dialog_manager.show_performance_monitor_dialog(stats, ui_scale)

        mock_page.show_dialog.assert_called_once()

    def test_show_backup_preview_dialog(self, dialog_manager, mock_page):
        """测试备份预览对话框"""
        backup_info = {
            'filename': 'test.json.bak',
            'content': '{"key": "value"}' * 100
        }

        dialog_manager.show_backup_preview_dialog(backup_info)

        mock_page.show_dialog.assert_called_once()

    def test_show_backup_restore_confirm_dialog(self, dialog_manager, mock_page):
        """测试备份恢复确认对话框"""
        backup_info = {'filename': 'test.json.bak'}
        on_confirm = Mock()

        dialog_manager.show_backup_restore_confirm_dialog(backup_info, on_confirm)

        mock_page.show_dialog.assert_called_once()

    def test_show_backup_delete_confirm_dialog(self, dialog_manager, mock_page):
        """测试备份删除确认对话框"""
        backup_info = {'filename': 'test.json.bak'}
        on_confirm = Mock()

        dialog_manager.show_backup_delete_confirm_dialog(backup_info, on_confirm)

        mock_page.show_dialog.assert_called_once()

    def test_show_js_translation_preview_dialog(self, dialog_manager, mock_page):
        """测试JS翻译预览对话框"""
        analysis_result = {
            'total_files': 5,
            'total_strings': 100,
            'estimated_time': 30.5,
            'files': [
                {'name': 'test1.js', 'needs_translation': 10, 'total': 20},
                {'name': 'test2.js', 'needs_translation': 5, 'total': 15},
            ]
        }
        on_confirm = Mock()

        dialog_manager.show_js_translation_preview_dialog(analysis_result, on_confirm)

        mock_page.show_dialog.assert_called_once()

    def test_show_mode_selection_dialog(self, dialog_manager, mock_page):
        """测试模式选择对话框"""
        options = [
            {'label': '模式1', 'description': '描述1'},
            {'label': '模式2', 'description': '描述2'},
        ]
        on_select = Mock()

        dialog_manager.show_mode_selection_dialog("选择模式", options, on_select)

        mock_page.show_dialog.assert_called_once()


class TestDialogManagerEdgeCases:
    """DialogManager边界情况测试"""

    @pytest.fixture
    def mock_page(self):
        page = Mock()
        page.show_dialog = Mock()
        page.pop_dialog = Mock()
        return page

    @pytest.fixture
    def dialog_manager(self, mock_page):
        from ui.dialog_manager import DialogManager
        return DialogManager(
            page=mock_page,
            config_manager=Mock(),
            api_manager=Mock(),
            log_callback=Mock()
        )

    def test_empty_log_text(self, dialog_manager, mock_page):
        """测试空日志文本"""
        dialog_manager.show_log_dialog([], "空日志")
        mock_page.show_dialog.assert_called_once()

    def test_long_log_text_truncation(self, dialog_manager, mock_page):
        """测试长日志文本截断"""
        log_text = ["line"] * 200
        dialog_manager.show_log_dialog(log_text, "长日志")
        mock_page.show_dialog.assert_called_once()

    def test_backup_content_truncation(self, dialog_manager, mock_page):
        """测试备份内容截断"""
        backup_info = {
            'filename': 'test.bak',
            'content': 'x' * 5000
        }
        dialog_manager.show_backup_preview_dialog(backup_info)
        mock_page.show_dialog.assert_called_once()
