"""标签页壳层：主功能 / 配置 / 日志区组装（供 MinecraftTranslatorApp 混入）。"""

from __future__ import annotations

import flet as ft

from ui import dialogs, tabs


class ApplicationTabShellMixin:
    """build_ui、各 Tab 构建、配置区 API 列表等与页面结构相关的逻辑。"""

    def build_ui(self):
        s = self.ui_scale

        self.page.add(
            ft.Container(
                content=ft.Column([
                    ft.Text("Minecraft 基岩版汉化工具", size=s['title_size'], weight=ft.FontWeight.BOLD, color=self.get_color('accent_text')),
                    ft.Text("现代化、易用、高效的翻译工具", size=s['subtitle_size'], color=self.get_color('text_secondary'))
                ], spacing=int(5 * self.scale), alignment=ft.MainAxisAlignment.CENTER),
                padding=int(20 * self.scale),
                bgcolor=self.get_color('primary_bg'),
                border_radius=ft.BorderRadius(top_left=0, top_right=0, bottom_left=s['border_radius'], bottom_right=s['border_radius'])
            )
        )

        tabs_control = ft.Tabs(
            selected_index=0,
            length=3,
            expand=True,
            content=ft.Column([
                ft.TabBar(
                    tabs=[
                        ft.Tab(label="主功能"),
                        ft.Tab(label="配置"),
                        ft.Tab(label="日志"),
                    ]
                ),
                ft.TabBarView(
                    expand=True,
                    controls=[
                        self.create_main_tab(),
                        self.create_config_tab(),
                        self.create_log_tab(),
                    ]
                ),
            ])
        )
        self.page.add(tabs_control)

    def create_main_tab(self):
        """创建主功能标签页"""
        column = ft.Column([
            # 文件夹选择和 API 检测
            self.create_folder_and_api_section(),
            ft.Divider(height=10),

            # 功能按钮
            self.create_function_buttons(),
            ft.Divider(height=10),

            # 进度条和状态
            self.create_progress_section(),
            ft.Divider(height=10),

            self.create_status_bar(),
        ], scroll=ft.ScrollMode.AUTO, spacing=10)
        return column

    def create_folder_section(self):
        """创建文件夹选择区域（使用动态缩放 + 自适应文字）"""
        s = self.ui_scale
        return ft.Container(
            content=ft.Column([
                ft.Text("📁 文件夹选择", size=s['section_title_size'],
                        weight=ft.FontWeight.BOLD, color=self.get_color('text_primary')),
                ft.Row([
                    ft.Column([
                        ft.Row([
                            ft.Text("BP 文件夹:",
                                    weight=ft.FontWeight.BOLD,
                                    no_wrap=True,
                                    size=s['body_size'],
                                    color=self.get_color('text_primary')),
                            self.bp_path_label,
                            ft.ElevatedButton(
                                "选择",
                                icon=ft.Icons.FOLDER,
                                on_click=self.on_select_bp_folder,
                            ),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Row([
                            ft.Text("RP 文件夹:",
                                    weight=ft.FontWeight.BOLD,
                                    no_wrap=True,
                                    size=s['body_size'],
                                    color=self.get_color('text_primary')),
                            self.rp_path_label,
                            ft.ElevatedButton(
                                "选择",
                                icon=ft.Icons.FOLDER,
                                on_click=self.on_select_rp_folder,
                            ),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ], expand=True),
                ]),
            ]),
            padding=s['padding'],
            bgcolor=self.get_color('primary_bg'),
            border_radius=s['border_radius'],
        )

    def create_folder_and_api_section(self):
        """创建文件夹选择和 API 检测区域（使用动态缩放）"""
        s = self.ui_scale
        return ft.Container(
            content=ft.Row([
                # 左侧：文件夹选择（占4份）
                ft.Column([
                    self.create_folder_section(),
                ], expand=4, spacing=int(10 * self.scale)),

                # 右侧：API 检测（占3份）
                ft.Column([
                    ft.Container(
                        content=ft.Column([
                            ft.Text("🔌 API 检测", size=s['section_title_size'], weight=ft.FontWeight.BOLD, color=self.get_color(
                                'text_primary')),
                            ft.ElevatedButton(
                                "检测可用 API",
                                icon=ft.Icons.SEARCH,
                                on_click=self.detect_apis,
                                ref=lambda e: setattr(
                                    self, 'api_detect_button', e),
                            ),
                            ft.Divider(height=int(10 * self.scale)),
                            self.api_status_label,
                        ]),
                        padding=s['padding'],
                        bgcolor=self.get_color('primary_bg'),
                        border_radius=s['border_radius'],
                    ),
                ], expand=3, spacing=int(10 * self.scale)),
            ], spacing=int(20 * self.scale)),
        )

    def create_function_buttons(self):
        """创建功能按钮区域（使用动态缩放 + 2K下1.2倍放大 + 文件夹检查） - 调用tabs模块"""
        callbacks = {
            'on_extract_only': self.func_handlers.on_extract_only,
            'on_extract_and_translate': self.func_handlers.on_extract_and_translate,
            'replace_display_names': self.func_handlers.replace_display_names,
            'one_click_service': self.func_handlers.on_one_click_service,
            'remove_value_for_specified_folder': self.func_handlers.on_batch_delete_value,
            'restore_value_for_specified_folder': self.func_handlers.on_batch_restore_value,
            'translate_lang_file': self.func_handlers.on_translate_lang_file,
            'process_guidebook_js': self.process_guidebook_js,
            'extract_entity_display_names': self.func_handlers.on_adapt_entity_display_names,
            'script_hardcode_translation': self.script_hardcode_translation,
            'on_backup_management': self.func_handlers.on_backup_management,
            'translate_mcstructure': self.func_handlers.on_translate_mcstructure,
        }

        # 调用tabs模块创建功能按钮
        container, button_dict, function_buttons = tabs.create_function_buttons(
            context=self.ui_context,
            callbacks=callbacks
        )

        # 存储按钮引用到实例属性
        self.btn_extract_only = button_dict.get('extract_only')
        self.btn_extract_translate = button_dict.get('extract_and_translate')
        self.btn_replace_display = button_dict.get('replace_display_names')
        self.btn_one_click = button_dict.get('one_click_service')
        self.btn_remove_value = button_dict.get('batch_delete_value')
        self.btn_restore_value = button_dict.get('batch_restore_value')
        self.btn_translate_lang = button_dict.get('translate_lang_file')
        self.btn_guidebook = button_dict.get('translate_single_js_file')
        self.btn_entity = button_dict.get('adapt_entity_display_names')
        self.btn_script_hardcode = button_dict.get('script_hardcode_translation')
        self.btn_backup_management = button_dict.get('backup_management')
        self.btn_mcstructure = button_dict.get('translate_mcstructure')

        self.function_buttons = function_buttons

        self.ui_coordinator.register_function_buttons(function_buttons)

        return container

    def disable_all_buttons(self, disabled=True):
        """禁用或启用所有功能按钮 - 委托给UICoordinator"""
        self.ui_coordinator.disable_all_buttons(disabled)

    def enable_all_buttons(self):
        """启用所有功能按钮 - 委托给UICoordinator"""
        self.ui_coordinator.enable_all_buttons()

    def create_progress_section(self):
        """创建进度条和状态显示区域（使用动态缩放） - 调用tabs模块"""
        container, progress_bar = tabs.create_progress_section(
            context=self.ui_context,
            progress_text=self.progress_text
        )

        self.progress_bar = progress_bar

        self.ui_coordinator.register_progress_controls(progress_bar, self.progress_text)

        return container

    def create_status_bar(self):
        """创建状态栏（使用动态缩放） - 调用tabs模块"""
        return tabs.create_status_bar(self.ui_context)

    def create_config_tab(self):
        """创建配置标签页 - 调用tabs模块"""
        callbacks = {
            'save_config': self.save_config,
            'restore_default_config': self.restore_default_config,
            'show_error_dialog': dialogs.show_error_dialog,
            'show_success_dialog': dialogs.show_success_dialog,
            'log': self.log,
            'show_add_api_dialog': self.show_add_api_dialog,
            'get_api_list': self.get_api_list,
            'show_import_export_dialog': self.show_import_export_dialog,
            'enable_all_apis': self.enable_all_apis,
            'disable_all_apis': self.disable_all_apis,
            'get_function_buttons_config': self.config_manager.get_function_buttons_config,
            'update_function_buttons_config': self.config_manager.update_function_buttons_config,
        }

        result = tabs.create_config_tab(
            context=self.ui_context,
            config=self.config,
            callbacks=callbacks
        )
        return result

    def build_config_tab_content(self):
        """构建配置标签页内容（可刷新）"""
        # 调用create_config_tab方法（已模块化）
        return self.create_config_tab()

    def refresh_config_tab(self):
        """刷新配置标签页"""
        try:
            # 找到 Tabs 控件并重建整个配置标签页
            tabs_control = None

            # 查找 Tabs 控件
            for control in self.page.controls:
                if isinstance(control, ft.Tabs):
                    tabs_control = control
                    break

            if tabs_control:
                # 重新构建配置标签页内容
                new_config_content = self.build_config_tab_content()

                # 更新 TabBarView 中的第二个控件（配置标签页）
                if hasattr(tabs_control, 'content') and tabs_control.content:
                    tabbar_view = tabs_control.content.controls[1]
                    tabbar_view.controls[1] = new_config_content

                self.page.update()
                self.log("配置标签页已刷新")
            else:
                self.log("警告：未找到 Tabs 控件")
        except Exception as ex:
            self.log(f"刷新配置标签页失败: {str(ex)}")

    def create_log_tab(self):
        """创建日志标签页（使用动态缩放 + 内嵌日志窗口） - 调用tabs模块"""
        callbacks = {
            'show_log_in_page': self.show_log_in_page,
            'clear_log_display': self.clear_log_display,
        }

        container, log_display = tabs.create_log_tab(
            context=self.ui_context,
            callbacks=callbacks
        )

        self.log_display = log_display
        return container

    def show_log_in_page(self, e):
        """在页面内显示详细日志"""
        try:
            # 清空现有内容
            self.log_display.controls.clear()

            # 获取日志内容
            if not self.full_log_text:
                self.log_display.controls.append(
                    ft.Text("📝 暂无日志记录",
                            size=self.ui_scale['body_size'],
                            color=ft.Colors.GREY_500,
                            italic=True)
                )
            else:
                # 显示最近200条日志
                recent_logs = self.full_log_text[-200:]

                for log_entry in recent_logs:
                    # 根据日志类型设置不同颜色和图标
                    if "⚠️" in log_entry or "错误" in log_entry or "失败" in log_entry:
                        color = ft.Colors.RED_700
                        prefix = "❌"
                    elif "✅" in log_entry or "成功" in log_entry or "完成" in log_entry:
                        color = ft.Colors.GREEN_700
                        prefix = "✅"
                    elif "检测到" in log_entry or "已" in log_entry:
                        color = ft.Colors.BLUE_700
                        prefix = "ℹ️"
                    else:
                        color = ft.Colors.BLACK
                        prefix = "•"

                    self.log_display.controls.append(
                        ft.Text(f"{prefix} {log_entry}",
                                size=self.ui_scale['small_size'],
                                color=color,
                                font_family="Consolas")
                    )

            # 滚动到底部（异步方法需要通过 run_task 调用）
            if self.page:
                self.page.run_task(self._scroll_log_to_bottom)
                self.page.update()

            self.log(f"已在页面内显示 {len(self.full_log_text)} 条日志记录")
        except Exception as ex:
            self.log(f"显示日志失败: {str(ex)}")

    async def _scroll_log_to_bottom(self):
        """异步滚动日志到底部"""
        try:
            await self.log_display.scroll_to(offset=-1, duration=200)
        except Exception:
            pass

    def clear_log_display(self, e):
        """清空日志显示"""
        try:
            self.log_display.controls.clear()
            self.log_display.controls.append(
                ft.Text("📝 日志已清空",
                        size=self.ui_scale['body_size'],
                        color=ft.Colors.GREY_500,
                        italic=True)
            )
            self.page.update()
            self.log("日志显示已清空")
        except Exception as ex:
            self.log(f"清空日志失败: {str(ex)}")

    def get_api_list(self):
        """获取 API 列表显示"""
        apis = []
        for api_type in ['zhipu', 'deepseek', 'qwen', 'doubao', 'local_ollama', 'openai', 'azure_openai', 'baidu_ernie', 'iflytek_spark', 'google_gemini']:
            if api_type in self.config:
                apis.extend([(api, api_type) for api in self.config[api_type]])

        if not apis:
            return ft.Text("暂无配置的 API", color=ft.Colors.GREY, italic=True)

        # 创建 API 条目（用于2列显示）
        api_items = []
        for api, api_type in apis:
            api_type_name = {
                'zhipu': '智谱',
                'deepseek': 'DeepSeek',
                'qwen': '通义千问',
                'doubao': '豆包',
                'local_ollama': '本地 Ollama',
                'openai': 'OpenAI',
                'azure_openai': 'Azure OpenAI',
                'baidu_ernie': '百度文心一言',
                'iflytek_spark': '讯飞星火',
                'google_gemini': 'Google Gemini'
            }.get(api_type, api_type)

            # 创建一个容器来显示每个 API 条目
            api_item = ft.Container(
                content=ft.Column([
                    ft.Text(f"{api.get('name', '未命名')} ({api_type_name})",
                            weight=ft.FontWeight.BOLD,
                            size=self.ui_scale['body_size'],
                            no_wrap=True),
                    ft.Text(f"模型：{api.get('model', '未知')}",
                            size=self.ui_scale['small_size'],
                            color=ft.Colors.GREY_600),
                    ft.Row([
                        ft.TextButton(
                            "编辑",
                            icon=ft.Icons.EDIT,
                            on_click=lambda e, api=api, api_type=api_type: self.edit_api(
                                api, api_type),
                        ),
                        ft.TextButton(
                            "删除",
                            icon=ft.Icons.DELETE,
                            on_click=lambda e, api=api, api_type=api_type: self.delete_api(
                                api, api_type),
                        ),
                    ], spacing=int(5 * self.scale))
                ]),
                padding=int(10 * self.scale),
                bgcolor=self.get_color('card_bg'),
                border=ft.Border.all(1, self.get_color('border_color')),
                border_radius=self.ui_scale['border_radius'],
                margin=ft.Margin(0, int(5 * self.scale),
                                 0, int(5 * self.scale))
            )
            api_items.append(api_item)

        # 使用 GridView 实现2列布局
        return ft.GridView(
            controls=api_items,
            max_extent=int(380 * self.scale),  # 每列最大宽度
            child_aspect_ratio=1.5,  # 宽高比
            spacing=int(10 * self.scale),
            run_spacing=int(10 * self.scale),
            expand=True,
        )
