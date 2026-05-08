"""简单对话框包装与深色模式主题切换（MinecraftTranslatorApp 混入）。"""

from __future__ import annotations

import flet as ft

from ui import dialogs


class ApplicationDialogsThemeMixin:
    def show_log_dialog(self, e=None):
        """显示日志对话框（包装器，调用dialogs模块）"""
        dialogs.show_log_dialog(self.page, self.full_log_text, "📋 操作日志")

    def show_terminal_dialog(self, e=None):
        """显示终端对话框（包装器，调用dialogs模块）"""
        dialogs.show_terminal_dialog(self.page, self.terminal_text, "💻 终端输出")

    def show_success_dialog(self, title, message):
        """显示成功对话框（包装器，调用dialogs模块）"""
        dialogs.show_success_dialog(self.page, title, message)

    def show_error_dialog(self, title, message):
        """显示错误对话框（用户友好版，包装器，调用dialogs模块）"""
        dialogs.show_error_dialog(self.page, title, message)

    def show_info_dialog(self, title, message):
        """显示信息对话框（包装器，调用dialogs模块）"""
        dialogs.show_info_dialog(self.page, title, message)

    def toggle_dark_mode(self, e=None):
        """切换暗夜模式（UIState快照 → 重建 → 恢复）"""
        saved_state = self._save_ui_state()

        if self.page.theme_mode == ft.ThemeMode.LIGHT:
            self.page.theme_mode = ft.ThemeMode.DARK
            self.log("已切换到暗夜模式")
        else:
            self.page.theme_mode = ft.ThemeMode.LIGHT
            self.log("已切换到日间模式")

        if hasattr(self, 'ui_context') and self.ui_context:
            self.ui_context.clear_color_cache()

        self.rebuild_ui_for_theme()
        self._restore_ui_state(saved_state)
        self.page.update()

    def _save_ui_state(self):
        """保存主题切换前的 UI 状态"""
        state = {}
        if hasattr(self, 'api_status_label') and self.api_status_label:
            state['api_status_value'] = self.api_status_label.value
            state['api_status_color'] = self.api_status_label.color
        if hasattr(self, 'bp_path_label') and self.bp_path_label:
            state['bp_label_value'] = self.bp_path_label.value
            state['bp_label_color'] = self.bp_path_label.color
        if hasattr(self, 'rp_path_label') and self.rp_path_label:
            state['rp_label_value'] = self.rp_path_label.value
            state['rp_label_color'] = self.rp_path_label.color
        if hasattr(self, 'bp_path'):
            state['bp_path'] = self.bp_path
        if hasattr(self, 'rp_path'):
            state['rp_path'] = self.rp_path
        return state

    def _restore_ui_state(self, state):
        """恢复主题切换后的 UI 状态"""
        if state.get('api_status_value') and hasattr(self, 'api_status_label'):
            self.api_status_label.value = state['api_status_value']
            self.api_status_label.color = state['api_status_color']
        if state.get('bp_label_value') and hasattr(self, 'bp_path_label'):
            self.bp_path_label.value = state['bp_label_value']
            self.bp_path_label.color = state['bp_label_color']
        if state.get('rp_label_value') and hasattr(self, 'rp_path_label'):
            self.rp_path_label.value = state['rp_label_value']
            self.rp_path_label.color = state['rp_label_color']
        if state.get('bp_path'):
            self.bp_path = state['bp_path']
        if state.get('rp_path'):
            self.rp_path = state['rp_path']
        if hasattr(self, 'update_function_buttons_state'):
            self.update_function_buttons_state()

    def rebuild_ui_for_theme(self):
        """重新构建UI以应用主题颜色"""
        try:
            self.page.controls.clear()
            self.build_ui()
            self.log("UI已根据新主题重新构建")
        except Exception as ex:
            self.log(f"重新构建UI失败: {str(ex)}")
