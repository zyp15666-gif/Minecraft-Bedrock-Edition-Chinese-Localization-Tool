#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API 管理组件模块

提供 API 配置、检测和管理功能。

使用方式：
    from ui.components.api_manager import APIManagerComponent

    api_component = APIManagerComponent(ui_scale, get_api_list, callbacks)
    container = api_component.create()
"""

from typing import Any, Callable, Dict

import flet as ft


class APIManagerComponent:
    """
    API 管理组件

    提供：
    - API 列表显示
    - API 添加/编辑/删除
    - API 检测
    - API 启用/禁用
    """

    def __init__(
        self,
        ui_scale: Dict[str, Any],
        get_api_list_func: Callable,
        callbacks: Dict[str, Callable]
    ):
        """
        初始化 API 管理组件

        Args:
            ui_scale: UI 缩放配置
            get_api_list_func: 获取 API 列表的函数
            callbacks: 回调函数字典
        """
        self.ui_scale = ui_scale
        self.get_api_list_func = get_api_list_func
        self.callbacks = callbacks

    def create(self) -> ft.Container:
        """
        创建 API 管理区域

        Returns:
            API 管理容器
        """
        s = self.ui_scale

        # 按钮定义
        add_button = ft.ElevatedButton(
            "➕ 添加 API",
            icon=ft.Icons.ADD,
            on_click=self.callbacks.get('show_add_api_dialog'),
            style=ft.ButtonStyle(text_style=ft.TextStyle(size=s['body_size'])),
        )

        enable_all_button = ft.ElevatedButton(
            "✅ 全部启用",
            icon=ft.Icons.CHECK_CIRCLE,
            on_click=self.callbacks.get('enable_all_apis'),
            style=ft.ButtonStyle(text_style=ft.TextStyle(size=s['body_size'])),
            tooltip="一键启用所有已配置的API"
        )

        disable_all_button = ft.ElevatedButton(
            "❌ 全部禁用",
            icon=ft.Icons.CANCEL,
            on_click=self.callbacks.get('disable_all_apis'),
            style=ft.ButtonStyle(text_style=ft.TextStyle(size=s['body_size'])),
            tooltip="一键禁用所有已配置的API"
        )

        detect_apis_button = ft.ElevatedButton(
            "🔌 检测可用 API",
            icon=ft.Icons.BLUETOOTH_SEARCHING,
            on_click=self.callbacks.get('detect_apis'),
            style=ft.ButtonStyle(text_style=ft.TextStyle(size=s['body_size'])),
            tooltip="检测哪些 API 可用"
        )

        # API 列表
        api_list_container = ft.Container(
            content=self._build_api_list(),
            expand=True,
        )

        container = ft.Container(
            content=ft.Column([
                ft.Text("🔌 API 管理", size=s['section_title_size'], weight=ft.FontWeight.BOLD),
                ft.Divider(height=10),

                # 按钮行
                ft.Row([
                    add_button,
                    enable_all_button,
                    disable_all_button,
                    detect_apis_button,
                ], spacing=10, alignment=ft.MainAxisAlignment.START),

                ft.Divider(height=10),

                # API 列表标题
                ft.Text("已配置的 API:", size=s['body_size'], weight=ft.FontWeight.BOLD),

                # API 列表
                ft.Container(
                    content=api_list_container,
                    expand=True,
                    padding=10,
                    bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.GREY),
                    border_radius=5,
                ),
            ], scroll=ft.ScrollMode.AUTO),
            padding=15,
            bgcolor=ft.Colors.with_opacity(0.3, ft.Colors.BLUE_100),
            border_radius=10,
        )

        return container

    def _build_api_list(self) -> ft.Control:
        """构建 API 列表"""
        api_list = self.get_api_list_func() if self.get_api_list_func else []

        if not api_list:
            return ft.Text(
                "暂无 API 配置，请点击上方「添加 API」按钮添加",
                color=ft.Colors.GREY,
                italic=True
            )

        api_rows = []
        for api in api_list:
            api_name = api.get('name', 'Unknown')
            api_type = api.get('type', 'unknown')
            api_enabled = api.get('enabled', True)
            api_key_preview = self._mask_api_key(api.get('api_key', ''))

            row = ft.Container(
                content=ft.Row([
                    ft.Icon(
                        ft.Icons.CHECK_CIRCLE if api_enabled else ft.Icons.CANCEL,
                        color=ft.Colors.GREEN if api_enabled else ft.Colors.RED
                    ),
                    ft.Column([
                        ft.Text(api_name, weight=ft.FontWeight.BOLD),
                        ft.Text(f"类型: {api_type} | 密钥: {api_key_preview}", size=12, color=ft.Colors.GREY),
                    ], expand=True),
                    ft.IconButton(
                        icon=ft.Icons.EDIT,
                        on_click=lambda e, a=api: self._edit_api(a),
                        tooltip="编辑",
                    ),
                    ft.IconButton(
                        icon=ft.Icons.DELETE,
                        on_click=lambda e, a=api: self._delete_api(a),
                        tooltip="删除",
                    ),
                ], spacing=10),
                padding=10,
                bgcolor=ft.Colors.WHITE,
                border_radius=5,
                margin=5,
            )
            api_rows.append(row)

        return ft.Column(api_rows, spacing=5)

    def _mask_api_key(self, api_key: str) -> str:
        """隐藏 API 密钥"""
        if not api_key:
            return "未设置"
        if len(api_key) <= 8:
            return "***"
        return api_key[:4] + "****" + api_key[-4:]

    def _edit_api(self, api: Dict[str, Any]):
        """编辑 API"""
        callback = self.callbacks.get('edit_api')
        if callback:
            callback(api)

    def _delete_api(self, api: Dict[str, Any]):
        """删除 API"""
        callback = self.callbacks.get('delete_api')
        if callback:
            callback(api)

    def refresh(self):
        """刷新 API 列表"""
        # 这个方法可以在 API 列表更新后调用
        pass
