#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI 层单元测试 — function_handlers.py

使用 mock app 对象验证功能事件处理器的回调逻辑。
"""

from unittest.mock import MagicMock, patch

import pytest


def _make_mock_app():
    """创建模拟的 MinecraftTranslatorApp 对象"""
    app = MagicMock()
    app.bp_path = "/test/bp"
    app.rp_path = None
    app.log = MagicMock()
    app.show_error_dialog = MagicMock()
    app.show_success_dialog = MagicMock()

    # 模拟 functions 对象
    app.functions = MagicMock()

    # 模拟 run_background_task
    app.run_background_task = MagicMock()
    # 让 run_background_task 立即执行 task_fn
    def run_task_side_effect(task_fn, **kwargs):
        result = task_fn(
            progress_callback=lambda *a: None,
            log_callback=lambda m: None,
        )
        if kwargs.get('on_result'):
            kwargs['on_result'](result)
        return MagicMock()
    app.run_background_task.side_effect = run_task_side_effect

    return app


class TestFunctionHandlersInit:
    """初始化测试"""

    def test_init(self):
        from ui.function_handlers import FunctionHandlers
        app = _make_mock_app()
        handlers = FunctionHandlers(app)
        assert handlers.app is app


class TestFunctionHandlersRunFeature:
    """_run_feature 通用方法测试"""

    @pytest.fixture
    def handlers(self):
        from ui.function_handlers import FunctionHandlers
        return FunctionHandlers(_make_mock_app())

    def test_run_feature_no_bp_path(self, handlers):
        handlers.app.bp_path = None
        handlers._run_feature("extract_only", "测试", "test")
        handlers.app.show_error_dialog.assert_called_once()

    def test_run_feature_calls_function(self, handlers):
        handlers._run_feature("extract_only", "测试", "test")
        # 验证 run_background_task 被调用
        handlers.app.run_background_task.assert_called_once()

    def test_run_feature_with_rp_path(self, handlers):
        handlers.app.rp_path = "/test/rp"
        handlers._run_feature("extract_only", "测试", "test", extra=True)
        handlers.app.run_background_task.assert_called_once()


class TestFunctionHandlersOnExtractOnly:
    """on_extract_only 测试"""

    def test_calls_run_feature(self):
        from ui.function_handlers import FunctionHandlers
        app = _make_mock_app()
        handlers = FunctionHandlers(app)
        with patch.object(handlers, '_run_feature') as mock_run:
            handlers.on_extract_only()
            mock_run.assert_called_once_with("extract_only", "仅提取汉化 Key", "extract_only")


class TestFunctionHandlersOnExtractAndTranslate:
    """on_extract_and_translate 测试"""

    def test_calls_run_feature(self):
        from ui.function_handlers import FunctionHandlers
        app = _make_mock_app()
        handlers = FunctionHandlers(app)
        with patch.object(handlers, '_run_feature') as mock_run:
            handlers.on_extract_and_translate()
            mock_run.assert_called_once_with("extract_and_translate", "提取+AI翻译", "extract_and_translate")


class TestFunctionHandlersReplaceDisplayNames:
    """replace_display_names 测试"""

    def test_calls_run_feature(self):
        from ui.function_handlers import FunctionHandlers
        app = _make_mock_app()
        handlers = FunctionHandlers(app)
        with patch.object(handlers, '_run_feature') as mock_run:
            handlers.replace_display_names()
            mock_run.assert_called_once_with("replace_display_names", "替换 display_name", "replace_display_names")


class TestFunctionHandlersOtherFeatures:
    """其他功能测试"""

    @pytest.mark.parametrize("method_name, log_prefix, feature_tag", [
        ("on_batch_delete_value", "批量删除 value", "batch_delete_value"),
        ("on_batch_restore_value", "批量还原 value", "batch_restore_value"),
        ("on_translate_lang_file", "翻译 .lang 文件", "translate_lang_file"),
        ("on_one_click_service", "一条龙服务", "one_click_service"),
        ("on_adapt_entity_display_names", "实体显示名称适配", "adapt_entity_display_names"),
        ("on_translate_single_js_file", "翻译单个 JS 文件", "translate_single_js_file"),
        ("on_script_hardcode_translation", "脚本硬编码汉化", "script_hardcode_translation"),
    ])
    def test_feature_routes_correctly(self, method_name, log_prefix, feature_tag):
        from ui.function_handlers import FunctionHandlers
        app = _make_mock_app()
        handlers = FunctionHandlers(app)
        with patch.object(handlers, '_run_feature') as mock_run:
            getattr(handlers, method_name)()
            mock_run.assert_called_once()
            args, _ = mock_run.call_args
            assert args[2] == feature_tag  # 第三个参数是 feature_tag


class TestFunctionHandlersResultHandling:
    """结果处理测试"""

    @pytest.fixture
    def handlers(self):
        from ui.function_handlers import FunctionHandlers
        return FunctionHandlers(_make_mock_app())

    def test_handle_result_success(self, handlers):
        result = {"success": True, "message": "操作成功完成"}
        handlers._handle_result(result)
        handlers.app.show_success_dialog.assert_called_once()

    def test_handle_result_failure(self, handlers):
        result = {"success": False, "message": "发生错误"}
        handlers._handle_result(result)
        handlers.app.show_error_dialog.assert_called_once()

    def test_handle_result_with_message(self, handlers):
        result = {"success": False, "message": "自定义错误"}
        handlers._handle_result(result)
        handlers.app.show_error_dialog.assert_called_with("操作结果", "自定义错误")

    def test_handle_error(self, handlers):
        error = ValueError("测试错误")
        handlers._handle_error(error)
        handlers.app.show_error_dialog.assert_called_once()
        handlers.app.log.assert_called()


class TestFunctionHandlersBackup:
    """备份管理测试"""

    def test_on_backup_management(self):
        from ui.function_handlers import FunctionHandlers
        app = _make_mock_app()
        handlers = FunctionHandlers(app)
        handlers.on_backup_management()
        app.show_backup_management_dialog.assert_called_once()


class TestDefaultCallbacks:
    """默认回调函数测试"""

    def test_default_progress_callback(self):
        from ui.function_handlers import _default_progress_callback
        assert _default_progress_callback(0.5, 10, 30) is None

    def test_default_log_callback(self):
        from ui.function_handlers import _default_log_callback
        assert _default_log_callback("test") is None
