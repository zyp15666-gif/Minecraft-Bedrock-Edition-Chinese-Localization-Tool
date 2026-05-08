#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
功能按钮处理器测试
"""

from unittest.mock import Mock

import pytest


class TestFunctionButtonHandler:
    """FunctionButtonHandler单元测试"""

    @pytest.fixture
    def mock_page(self):
        """创建模拟的Flet页面"""
        page = Mock()
        return page

    @pytest.fixture
    def mock_functions(self):
        """创建模拟的ApplicationService"""
        functions = Mock()
        functions.extract_only = Mock(return_value={'success': True, 'message': '提取完成'})
        functions.extract_and_translate = Mock(return_value={'success': True, 'message': '翻译完成'})
        functions.replace_display_names = Mock(return_value={'success': True, 'message': '替换完成'})
        functions.batch_delete_value = Mock(return_value={'success': True, 'message': '删除完成'})
        functions.batch_restore_value = Mock(return_value={'success': True, 'message': '还原完成'})
        functions.translate_lang_file = Mock(return_value={'success': True, 'message': '翻译完成'})
        functions.one_click_service = Mock(return_value={'success': True, 'message': '一条龙完成'})
        functions.extract_entity_display_names = Mock(return_value={'success': True, 'message': '适配完成'})
        functions.translate_single_js_file = Mock(return_value={'success': True, 'message': 'JS翻译完成'})
        functions.script_hardcode_translation = Mock(return_value={'success': True, 'message': '脚本汉化完成'})
        return functions

    @pytest.fixture
    def mock_config_manager(self):
        """创建模拟的配置管理器"""
        return Mock()

    @pytest.fixture
    def mock_task_service(self):
        """创建模拟的后台任务服务"""
        service = Mock()
        service.run_with_button_state = Mock()
        return service

    @pytest.fixture
    def mock_callbacks(self):
        """创建模拟的回调函数"""
        return {
            'update_progress': Mock(),
            'disable_buttons': Mock(),
            'enable_buttons': Mock(),
            'log': Mock(),
            'show_error': Mock(),
            'show_success': Mock(),
        }

    @pytest.fixture
    def handler(self, mock_page, mock_functions, mock_config_manager, mock_task_service, mock_callbacks):
        """创建FunctionButtonHandler实例"""
        from ui.function_button_handler import FunctionButtonHandler
        return FunctionButtonHandler(
            page=mock_page,
            functions=mock_functions,
            config_manager=mock_config_manager,
            task_service=mock_task_service,
            update_progress=mock_callbacks['update_progress'],
            disable_buttons=mock_callbacks['disable_buttons'],
            enable_buttons=mock_callbacks['enable_buttons'],
            log_callback=mock_callbacks['log'],
            show_error=mock_callbacks['show_error'],
            show_success=mock_callbacks['show_success'],
        )

    def test_initialization(self, handler, mock_callbacks):
        """测试初始化"""
        assert handler.page is not None
        assert handler.functions is not None
        assert handler.config_manager is not None
        assert handler.task_service is not None

    def test_register_buttons(self, handler):
        """测试按钮注册"""
        buttons = [Mock(), Mock(), Mock()]
        handler.register_buttons(buttons)
        assert handler.function_buttons == buttons

    def test_on_extract_only(self, handler, mock_functions, mock_task_service):
        """测试提取功能"""
        handler.on_extract_only('/path/to/bp')

        mock_task_service.run_with_button_state.assert_called_once()
        args, kwargs = mock_task_service.run_with_button_state.call_args
        assert callable(args[0])
        assert "disabled_controls" in kwargs

    def test_on_extract_and_translate(self, handler, mock_functions, mock_task_service):
        """测试提取翻译功能"""
        handler.on_extract_and_translate('/path/to/bp', '/path/to/rp')

        mock_task_service.run_with_button_state.assert_called()

    def test_on_replace_display_names(self, handler, mock_functions, mock_task_service):
        """测试替换display_name功能"""
        handler.on_replace_display_names('/path/to/bp')

        mock_task_service.run_with_button_state.assert_called()

    def test_on_batch_delete_value(self, handler, mock_functions, mock_task_service):
        """测试批量删除功能"""
        handler.on_batch_delete_value('/path/to/folder')

        mock_task_service.run_with_button_state.assert_called()

    def test_on_batch_restore_value(self, handler, mock_functions, mock_task_service):
        """测试批量还原功能"""
        handler.on_batch_restore_value('/path/to/folder')

        mock_task_service.run_with_button_state.assert_called()

    def test_on_translate_lang_file(self, handler, mock_functions, mock_task_service):
        """测试翻译lang文件功能"""
        handler.on_translate_lang_file('/path/to/lang.file')

        mock_task_service.run_with_button_state.assert_called()

    def test_on_one_click_service(self, handler, mock_functions, mock_task_service):
        """测试一条龙服务"""
        handler.on_one_click_service('/path/to/bp')

        mock_task_service.run_with_button_state.assert_called()

    def test_on_adapt_entity_display_names(self, handler, mock_functions, mock_task_service):
        """测试实体显示名称适配"""
        handler.on_adapt_entity_display_names('/path/to/bp')

        mock_task_service.run_with_button_state.assert_called()

    def test_on_translate_single_js_file(self, handler, mock_functions, mock_task_service):
        """测试单个JS文件翻译"""
        handler.on_translate_single_js_file('/path/to/file.js', mode=1)

        mock_task_service.run_with_button_state.assert_called()

    def test_on_script_hardcode_translation(self, handler, mock_functions, mock_task_service):
        """测试脚本硬编码翻译"""
        handler.on_script_hardcode_translation('/path/to/bp', mode=1)

        mock_task_service.run_with_button_state.assert_called()

    def test_progress_callback_creation(self, handler):
        """测试进度回调创建"""
        callback = handler._create_progress_callback("测试操作")

        callback(0.5, 50, 100)
        callback(1.0, 0, 0)

    def test_log_callback_creation(self, handler):
        """测试日志回调创建"""
        callback = handler._create_log_callback()
        callback("测试日志")
        handler.log.assert_called_with("测试日志")


class TestFunctionButtonHandlerEdgeCases:
    """FunctionButtonHandler边界情况测试"""

    @pytest.fixture
    def mock_page(self):
        return Mock()

    @pytest.fixture
    def mock_functions(self):
        functions = Mock()
        functions.extract_only = Mock(side_effect=Exception("模拟错误"))
        return functions

    @pytest.fixture
    def mock_task_service(self):
        service = Mock()

        def mock_run(task_fn, **kwargs):
            try:
                task_fn()
            except Exception as e:
                if kwargs.get('on_error'):
                    kwargs['on_error'](e)

        service.run_with_button_state = mock_run
        return service

    @pytest.fixture
    def handler(self, mock_page, mock_functions, mock_task_service):
        from ui.function_button_handler import FunctionButtonHandler
        return FunctionButtonHandler(
            page=mock_page,
            functions=mock_functions,
            config_manager=Mock(),
            task_service=mock_task_service,
            update_progress=Mock(),
            disable_buttons=Mock(),
            enable_buttons=Mock(),
            log_callback=Mock(),
            show_error=Mock(),
            show_success=Mock(),
        )

    def test_exception_handling(self, handler):
        """测试异常处理"""
        handler.on_extract_only('/path/to/bp')
