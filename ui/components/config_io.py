#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置导入导出组件

提供配置、术语库和翻译记忆库的导入导出功能。

使用方式：
    from ui.components.config_io import ConfigIO

    config_io = ConfigIO(ui_scale, callbacks)
    dialog = config_io.create_export_dialog()
"""

import flet as ft
import json
import os
from typing import Dict, Any, Callable, Optional
from datetime import datetime


class ConfigIO:
    """
    配置导入导出组件

    提供：
    - 导出配置（不含 API 密钥）
    - 导出术语库
    - 导出翻译记忆库
    - 导入配置
    - 导入术语库
    - 导入翻译记忆库
    """

    def __init__(
        self,
        ui_scale: Dict[str, Any],
        callbacks: Dict[str, Callable]
    ):
        """
        初始化配置导入导出组件

        Args:
            ui_scale: UI 缩放配置
            callbacks: 回调函数字典
        """
        self.ui_scale = ui_scale
        self.callbacks = callbacks

        self.export_type = "config"
        self.import_type = "config"

    def create_export_dialog(self) -> ft.AlertDialog:
        """创建导出对话框"""
        s = self.ui_scale

        self.export_type = "config"

        def on_export_type_change(e):
            self.export_type = e.control.value

        def on_export_click(e):
            self._do_export()
            self.callbacks.get('close_dialog', lambda: None)()

        return ft.AlertDialog(
            title=ft.Text("📤 导出", size=s['section_title_size']),
            content=ft.Column([
                ft.Text("选择导出类型:", size=s['body_size']),
                ft.RadioGroup(
                    content=ft.Column([
                        ft.Radio("配置（不含 API 密钥）", value="config"),
                        ft.Radio("术语库 (minecraft_terms.json)", value="terms"),
                        ft.Radio("翻译记忆库 (cache)", value="cache"),
                        ft.Radio("全部", value="all"),
                    ]),
                    on_change=on_export_type_change,
                    value="config",
                ),
                ft.Container(height=10),
                ft.Text(
                    "导出的文件将保存在您选择的位置。",
                    size=s['small_size'],
                    color=ft.Colors.GREY,
                ),
            ]),
            actions=[
                ft.TextButton("取消", on_click=lambda e: self.callbacks.get('close_dialog', lambda: None)()),
                ft.ElevatedButton("导出", icon=ft.Icons.DOWNLOAD, on_click=on_export_click),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

    def create_import_dialog(self) -> ft.AlertDialog:
        """创建导入对话框"""
        s = self.ui_scale

        self.import_type = "config"

        def on_import_type_change(e):
            self.import_type = e.control.value

        def on_import_click(e):
            self._do_import()
            self.callbacks.get('close_dialog', lambda: None)()

        return ft.AlertDialog(
            title=ft.Text("📥 导入", size=s['section_title_size']),
            content=ft.Column([
                ft.Text("选择导入类型:", size=s['body_size']),
                ft.RadioGroup(
                    content=ft.Column([
                        ft.Radio("配置", value="config"),
                        ft.Radio("术语库", value="terms"),
                        ft.Radio("翻译记忆库", value="cache"),
                    ]),
                    on_change=on_import_type_change,
                    value="config",
                ),
                ft.Container(height=10),
                ft.Text(
                    "导入将覆盖现有数据，请谨慎操作。",
                    size=s['small_size'],
                    color=ft.Colors.ORANGE,
                ),
            ]),
            actions=[
                ft.TextButton("取消", on_click=lambda e: self.callbacks.get('close_dialog', lambda: None)()),
                ft.ElevatedButton("选择文件", icon=ft.Icons.UPLOAD, on_click=on_import_click),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

    def _do_export(self):
        """执行导出"""
        export_data = {}

        if self.export_type in ["config", "all"]:
            config = self.callbacks.get('get_config', lambda: {})()
            export_data['config'] = self._sanitize_config(config)

        if self.export_type in ["terms", "all"]:
            terms = self.callbacks.get('get_terms', lambda: {})()
            export_data['terms'] = terms

        if self.export_type in ["cache", "all"]:
            cache = self.callbacks.get('get_cache', lambda: {})()
            export_data['cache'] = cache

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"wodeshijie_export_{timestamp}.json"

        self.callbacks.get('save_file', lambda f, d: None)(filename, export_data)
        self.callbacks.get('show_message', lambda m: None)(f"已导出到: {filename}")

    def _do_import(self):
        """执行导入"""
        def on_file_selected(file_path: str):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                if 'config' in data and self.import_type in ["config", "all"]:
                    self.callbacks.get('load_config', lambda c: None)(data['config'])

                if 'terms' in data and self.import_type in ["terms", "all"]:
                    self.callbacks.get('load_terms', lambda t: None)(data['terms'])

                if 'cache' in data and self.import_type in ["cache", "all"]:
                    self.callbacks.get('load_cache', lambda c: None)(data['cache'])

                self.callbacks.get('show_message', lambda m: None)("导入成功！")
            except Exception as e:
                self.callbacks.get('show_error', lambda m: None)(f"导入失败: {str(e)}")

        self.callbacks.get('open_file_picker', on_file_selected)

    def _sanitize_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """清除配置中的敏感信息"""
        import copy
        sanitized = copy.deepcopy(config)

        providers = ['deepseek', 'qwen', 'zhipu', 'doubao', 'local_ollama']
        for provider in providers:
            if provider in sanitized and isinstance(sanitized[provider], list):
                for api_entry in sanitized[provider]:
                    if isinstance(api_entry, dict):
                        api_entry['api_key'] = '***'

        return sanitized
