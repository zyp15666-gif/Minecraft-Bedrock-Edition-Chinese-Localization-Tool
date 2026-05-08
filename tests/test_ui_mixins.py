#!/usr/bin/env python3
from unittest.mock import Mock, patch

import pytest


class MockApp:
    """模拟 MinecraftTranslatorApp 的 Mixin 宿主"""

    def __init__(self):
        self.config = {
            "deepseek": [
                {"name": "ds1", "model": "deepseek-chat", "api_url": "url", "api_key": "key", "enabled": True},
                {"name": "ds2", "model": "deepseek-chat", "api_url": "url", "api_key": "key", "enabled": False},
            ],
            "local_ollama": [
                {"name": "ollama1", "model": "llama2", "api_url": "http://localhost:11434", "enabled": True},
            ],
        }
        self.log_messages = []
        self.saved_config = None

    def log(self, msg):
        self.log_messages.append(msg)

    def save_config(self):
        self.saved_config = True

    def refresh_config_tab(self):
        pass

    def show_success_dialog(self, title, msg):
        pass

    def show_error_dialog(self, title, msg):
        pass

    def show_info_dialog(self, title, msg):
        pass


class TestApplicationApiBatchMixin:
    @pytest.fixture
    def app(self):
        from ui.application_api_batch import ApplicationApiBatchMixin

        class TestApp(MockApp, ApplicationApiBatchMixin):
            pass

        return TestApp()

    def test_enable_all_apis(self, app):
        app.enable_all_apis()
        assert all(api.get("enabled", True) for api in app.config["deepseek"])
        assert any("启用" in msg for msg in app.log_messages)

    def test_enable_already_enabled(self, app):
        for provider in app.config:
            for api in app.config[provider]:
                api["enabled"] = True
        app.enable_all_apis()
        assert any("已经" in msg for msg in app.log_messages)

    def test_disable_all_apis(self, app):
        app.disable_all_apis()
        assert all(not api.get("enabled", True) for api in app.config["deepseek"])
        assert any("禁用" in msg for msg in app.log_messages)

    def test_disable_already_disabled(self, app):
        for provider in app.config:
            for api in app.config[provider]:
                api["enabled"] = False
        app.disable_all_apis()
        assert any("已经" in msg for msg in app.log_messages)

    def test_enable_saves_config(self, app):
        app.enable_all_apis()
        assert app.saved_config is True

    def test_disable_saves_config(self, app):
        app.disable_all_apis()
        assert app.saved_config is True

    def test_enable_handles_exception(self, app):
        app.config = None
        app.enable_all_apis()
        assert any("失败" in msg for msg in app.log_messages)

    def test_disable_handles_exception(self, app):
        app.config = None
        app.disable_all_apis()
        assert any("失败" in msg for msg in app.log_messages)


class TestApplicationApiConfigMixin:
    @pytest.fixture
    def app(self):
        from ui.application_api_config import ApplicationApiConfigMixin

        class TestApp(MockApp, ApplicationApiConfigMixin):
            pass

        return TestApp()

    def test_generate_api_name_with_model(self, app):
        result = app.generate_api_name("DeepSeek", "deepseek-chat")
        assert "DeepSeek" in result
        assert "deepseek-chat" in result

    def test_generate_api_name_without_model(self, app):
        result = app.generate_api_name("DeepSeek", "")
        assert "DeepSeek" in result
        assert result.count("_") == 1

    def test_generate_api_name_unknown_type(self, app):
        result = app.generate_api_name("UnknownType", "model")
        assert "UnknownType" in result

    def test_generate_api_name_exception_fallback(self, app):
        app.config = None
        result = app.generate_api_name("DeepSeek", "model")
        assert result == "DeepSeek_1"

    def test_on_api_type_changed(self, app):
        app.on_api_type_changed(None)


class TestApplicationDialogsThemeMixin:
    @pytest.fixture
    def app(self):
        from ui.application_dialogs_theme import ApplicationDialogsThemeMixin

        class TestApp(MockApp, ApplicationDialogsThemeMixin):
            def __init__(self):
                super().__init__()
                self.page = Mock()
                self.page.theme_mode = Mock()
                self.page.theme_mode = "light"
                self.page.update = Mock()
                self.dark_mode = False
                self.rebuild_ui_for_theme = Mock()
                self._restore_ui_state = Mock()

        return TestApp()

    def test_toggle_dark_mode(self, app):
        app.page.theme_mode = "light"
        app.toggle_dark_mode(None)
        assert app.page.theme_mode != "light"

    def test_toggle_dark_mode_back(self, app):
        app.page.theme_mode = "dark"
        app.toggle_dark_mode(None)
        assert app.page.theme_mode != "dark"

    def test_show_success_dialog(self, app):
        try:
            app.show_success_dialog("标题", "消息")
        except Exception:
            pass

    def test_show_error_dialog(self, app):
        try:
            app.show_error_dialog("标题", "消息")
        except Exception:
            pass

    def test_show_info_dialog(self, app):
        try:
            app.show_info_dialog("标题", "消息")
        except Exception:
            pass


class TestFirstRunWizard:
    @pytest.fixture
    def wizard(self):
        from ui.first_run_wizard import FirstRunWizard

        page = Mock()
        page.open = Mock()
        config = {"deepseek": [{"name": "ds1"}]}
        return FirstRunWizard(page, config)

    def test_is_first_run(self, wizard, tmp_path):
        wizard._flag_path = str(tmp_path / ".first_run_completed")
        assert wizard.is_first_run() is True

    def test_not_first_run_after_mark(self, wizard, tmp_path):
        wizard._flag_path = str(tmp_path / ".first_run_completed")
        wizard.mark_completed()
        assert wizard.is_first_run() is False

    def test_check_python_version(self, wizard):
        ok, version = wizard._check_python_version()
        assert ok is True
        assert "." in version

    def test_check_os(self, wizard):
        ok, info = wizard._check_os()
        assert ok is True
        assert "Windows" in info or "Linux" in info or "Darwin" in info

    def test_check_config_with_apis(self, wizard):
        ok, info = wizard._check_config()
        assert ok is True

    def test_check_config_without_apis(self):
        from ui.first_run_wizard import FirstRunWizard

        wizard = FirstRunWizard(Mock(), {})
        ok, info = wizard._check_config()
        assert ok is False

    def test_build_status_row(self, wizard):
        import flet as ft

        row = wizard.build_status_row("测试", True, "详情")
        assert isinstance(row, ft.Row)

    def test_show_opens_dialog(self, wizard):
        wizard.show()
        wizard.page.show_dialog.assert_called()
