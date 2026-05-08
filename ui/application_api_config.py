"""API 列表编辑与配置保存（MinecraftTranslatorApp 混入）。"""

from __future__ import annotations

import flet as ft

from ui import dialogs


class ApplicationApiConfigMixin:
    def generate_api_name(self, api_type, model):
        """自动生成 API 名称（类型_数字 或 类型_模型_数字）"""
        try:
            # 获取该类型下已有的 API 数量
            type_key_map = {
                "智谱": "zhipu",
                "DeepSeek": "deepseek",
                "通义千问": "qwen",
                "豆包": "doubao",
                "本地 Ollama": "local_ollama",
                "OpenAI": "openai",
                "Azure OpenAI": "azure_openai",
                "百度文心一言": "baidu_ernie",
                "讯飞星火": "iflytek_spark",
                "Google Gemini": "google_gemini",
            }

            type_key = type_key_map.get(api_type, "zhipu")

            if type_key in self.config:
                existing_count = len(self.config[type_key])
            else:
                existing_count = 0

            new_number = existing_count + 1

            # 如果模型为空，只生成：类型_数字
            if not model or model.strip() == "":
                return f"{api_type}_{new_number}"

            # 如果有模型，生成：类型_模型_数字
            return f"{api_type}_{model}_{new_number}"
        except Exception:
            return f"{api_type}_1"

    def on_api_type_changed(self, e):
        """当 API 类型改变时的事件处理"""
        pass  # 这个方法会在 show_add_api_dialog 内部定义

    def show_add_api_dialog(self, e):
        """显示添加 API 对话框 - 调用dialogs模块"""
        # 准备回调函数字典
        callbacks = {
            'save_config': self.save_config,
            'show_error_dialog': dialogs.show_error_dialog,
            'show_success_dialog': dialogs.show_success_dialog,
            'log': self.log,
            'show_add_api_dialog': self.show_add_api_dialog,
            'get_api_list': self.get_api_list,
            'show_import_export_dialog': self.show_import_export_dialog,
            # 新增
            'enable_all_apis': self.enable_all_apis,
            'disable_all_apis': self.disable_all_apis,
            'refresh_config_tab': self.refresh_config_tab,
            'detect_apis': self.detect_apis,
        }

        # 使用实例方法作为生成API名称的函数
        # 注意：这里传递的是self.generate_api_name方法引用
        generate_api_name_func = self.generate_api_name

        # 调用dialogs模块显示添加API对话框
        dialogs.show_add_api_dialog(
            page=self.page,
            callbacks=callbacks,
            config=self.config,
            generate_api_name_func=generate_api_name_func
        )

    def edit_api(self, api, api_type):
        """编辑 API"""
        try:
            # 创建编辑表单
            name_field = ft.TextField(
                label="API 名称", value=api.get('name', ''), width=300)
            api_key_field = ft.TextField(label="API 密钥", value=api.get(
                'api_key', ''), password=True, can_reveal_password=True, width=300)
            model_field = ft.TextField(
                label="模型名称", value=api.get('model', ''), width=300)
            api_url_field = ft.TextField(
                label="API URL", value=api.get('api_url', ''), width=300)
            priority_field = ft.TextField(label="优先级", value=str(
                api.get('priority', 1)), width=300, keyboard_type=ft.KeyboardType.NUMBER)
            enabled_switch = ft.Switch(
                label="启用", value=api.get('enabled', True))

            def save_changes(e):
                """保存修改"""
                try:
                    api['name'] = name_field.value
                    api['api_key'] = api_key_field.value
                    api['model'] = model_field.value
                    api['api_url'] = api_url_field.value
                    api['priority'] = int(
                        priority_field.value) if priority_field.value.isdigit() else 1
                    api['enabled'] = enabled_switch.value

                    # 保存配置
                    self.save_config()

                    self.log(f"已编辑 API: {api['name']}")
                    self.page.pop_dialog()
                    self.refresh_config_tab()
                    self.show_success_dialog("成功", f"API '{api['name']}' 已更新")

                    # 在后台检测API，不阻塞UI
                    import threading
                    def background_detect():
                        # 延迟一下，让UI先更新
                        import time
                        time.sleep(0.5)
                        self.detect_apis()

                    # 启动后台线程
                    detect_thread = threading.Thread(target=background_detect, daemon=True)
                    detect_thread.start()

                    self.page.update()
                except Exception as ex:
                    self.log(f"保存编辑失败: {str(ex)}")
                    self.show_error_dialog("错误", str(ex))

            def cancel(e):
                """取消编辑"""
                self.page.pop_dialog()

            # 创建对话框
            dialog = ft.AlertDialog(
                title=ft.Text("✏️ 编辑 API"),
                content=ft.Column([
                    name_field,
                    api_key_field,
                    model_field,
                    api_url_field,
                    priority_field,
                    enabled_switch,
                ], tight=True, spacing=10),
                actions=[
                    ft.TextButton("取消", on_click=cancel),
                    ft.TextButton("保存", on_click=save_changes),
                ],
            )

            # 显示对话框
            self.page.show_dialog(dialog)
        except Exception as ex:
            self.log(f"打开编辑 API 对话框失败: {str(ex)}")
            self.show_error_dialog("错误", str(ex))

    def delete_api(self, api, api_type):
        """删除 API"""
        try:
            # 确认删除
            def confirm_delete(e):
                try:
                    if api_type in self.config:
                        api_list = self.config[api_type]
                        if api in api_list:
                            api_name = api.get('name', '未知')
                            api_list.remove(api)
                            # 保存配置到文件
                            self.save_config()
                            self.log(f"已删除 API: {api_name}")

                    # 关闭对话框
                    self.page.pop_dialog()
                    self.refresh_config_tab()
                    self.show_success_dialog(
                        "成功", f"API '{api.get('name', '未知')}' 已删除")

                    # 在后台检测API，不阻塞UI
                    import threading
                    def background_detect():
                        # 延迟一下，让UI先更新
                        import time
                        time.sleep(0.5)
                        self.detect_apis()

                    # 启动后台线程
                    detect_thread = threading.Thread(target=background_detect, daemon=True)
                    detect_thread.start()

                    self.page.update()
                except Exception as ex:
                    self.log(f"删除 API 失败: {str(ex)}")
                    self.show_error_dialog("错误", str(ex))

            def cancel(e):
                """取消删除"""
                self.page.pop_dialog()

            # 创建对话框
            dialog = ft.AlertDialog(
                title=ft.Text("🗑️ 确认删除"),
                content=ft.Text("确定要删除此 API 吗？此操作不可恢复。"),
                actions=[
                    ft.TextButton("取消", on_click=cancel),
                    ft.TextButton("删除", on_click=confirm_delete),
                ],
            )

            # 显示对话框
            self.page.show_dialog(dialog)
        except Exception as ex:
            self.log(f"打开删除确认对话框失败: {str(ex)}")
            self.show_error_dialog("错误", str(ex))

    def save_config(self, e=None):
        """保存配置"""
        try:
            success = self.config_manager.save_config(self.config)
            if success:
                self.log("配置已保存")
            else:
                raise Exception("保存失败")
        except Exception as ex:
            self.show_error_dialog("保存失败", str(ex))

    def restore_default_config(self, e=None):
        """恢复默认配置（保留API密钥）"""
        try:
            restored = self.config_manager.restore_default_config(keep_api_keys=True)
            self.config = restored
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text("✅ 已恢复默认配置（API密钥已保留）"), duration=3000)
            self.page.snack_bar.open = True
            self.page.update()
            self.log("已恢复默认配置（API密钥已保留）")
            return restored
        except Exception as ex:
            self.show_error_dialog("恢复失败", str(ex))
            return None
