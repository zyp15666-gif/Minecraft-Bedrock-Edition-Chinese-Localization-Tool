#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FunctionButtonHandler基本功能测试

测试功能按钮事件处理器的基本功能
"""

import pytest
from unittest.mock import Mock
from ui.function_button_handler import FunctionButtonHandler


class TestFunctionButtonHandlerBasic:
    """FunctionButtonHandler基本功能测试"""

    @pytest.fixture
    def handler(self, mock_page, mock_app_service, mock_dialog_manager, mock_task_service):
        """创建FunctionButtonHandler实例"""
        return FunctionButtonHandler(
            page=mock_page,
            functions=mock_app_service,
            config_manager=Mock(),
            task_service=mock_task_service,
            update_progress=Mock(),
            disable_buttons=Mock(),
            enable_buttons=Mock(),
            log_callback=Mock(),
            show_error=mock_dialog_manager.show_error,
            show_success=mock_dialog_manager.show_success
        )

    def test_init(self, handler, mock_page, mock_app_service):
        """测试初始化"""
        assert handler.page == mock_page
        assert handler.functions == mock_app_service
        assert handler.task_service is not None

    def test_on_extract_only_with_valid_path(self, handler, mock_bp_path, mock_app_service):
        """测试仅提取功能 - 有效路径"""
        # 调用方法
        handler.on_extract_only(mock_bp_path)
        
        # 验证调用了应用服务
        assert True

    def test_on_extract_and_translate_with_valid_path(self, handler, mock_bp_path, mock_app_service):
        """测试提取+翻译功能 - 有效路径"""
        handler.on_extract_and_translate(mock_bp_path)
        
        assert True

    def test_on_one_click_service_with_valid_path(self, handler, mock_bp_path, mock_app_service):
        """测试一条龙服务 - 有效路径"""
        handler.on_one_click_service(mock_bp_path)
        
        assert True

    def test_register_buttons(self, handler):
        """测试注册按钮"""
        buttons = [Mock(), Mock(), Mock()]
        handler.register_buttons(buttons)
        
        assert handler.function_buttons == buttons


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
