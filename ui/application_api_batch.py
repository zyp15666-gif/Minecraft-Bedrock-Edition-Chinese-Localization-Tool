"""批量启用或禁用 API（MinecraftTranslatorApp 混入）。"""

from __future__ import annotations

from ui.user_interaction import mark_interaction


class ApplicationApiBatchMixin:
    def enable_all_apis(self, e=None):
        """批量启用所有API"""
        mark_interaction("button_click", "批量启用所有API")

        try:
            providers = ["deepseek", "qwen", "zhipu", "doubao", "local_ollama",
                         "openai", "azure_openai", "baidu_ernie", "iflytek_spark", "google_gemini"]
            changed = False
            for provider in providers:
                apis = self.config.get(provider, [])
                if isinstance(apis, list):
                    for api in apis:
                        if not api.get("enabled", True):
                            api["enabled"] = True
                            changed = True

            if changed:
                self.save_config()
                self.refresh_config_tab()
                self.log("✅ 已批量启用所有API")
                self.show_success_dialog("成功", "所有API已启用")
            else:
                self.log("ℹ️ 所有API已经处于启用状态")
                self.show_info_dialog("提示", "所有API已经是启用状态")

        except Exception as ex:
            self.log(f"❌ 批量启用API失败: {ex}")
            self.show_error_dialog("错误", f"批量启用失败: {ex}")

    def disable_all_apis(self, e=None):
        """批量禁用所有API"""
        mark_interaction("button_click", "批量禁用所有API")

        try:
            providers = ["deepseek", "qwen", "zhipu", "doubao", "local_ollama",
                         "openai", "azure_openai", "baidu_ernie", "iflytek_spark", "google_gemini"]
            changed = False
            for provider in providers:
                apis = self.config.get(provider, [])
                if isinstance(apis, list):
                    for api in apis:
                        if api.get("enabled", True):
                            api["enabled"] = False
                            changed = True

            if changed:
                self.save_config()
                self.refresh_config_tab()
                self.log("✅ 已批量禁用所有API")
                self.show_success_dialog("成功", "所有API已禁用")
            else:
                self.log("ℹ️ 所有API已经处于禁用状态")
                self.show_info_dialog("提示", "所有API已经是禁用状态")

        except Exception as ex:
            self.log(f"❌ 批量禁用API失败: {ex}")
            self.show_error_dialog("错误", f"批量禁用失败: {ex}")
