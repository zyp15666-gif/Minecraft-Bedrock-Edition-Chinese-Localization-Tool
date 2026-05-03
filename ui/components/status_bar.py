#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
状态栏组件模块

提供应用状态显示。

使用方式：
    from ui.components.status_bar import StatusBar

    status_bar = StatusBar(ui_scale)
    status_bar.create()
"""

import flet as ft
from typing import Dict, Any


class StatusBar:
    """
    状态栏组件

    显示：
    - 当前状态
    - 可用 API 数量
    """

    def __init__(self, ui_scale: Dict[str, Any]):
        """
        初始化状态栏

        Args:
            ui_scale: UI 缩放配置
        """
        self.ui_scale = ui_scale

        self.status_text = ft.Text(
            "就绪",
            size=ui_scale['small_size'],
            color=ft.Colors.GREY_600
        )
        self.api_count_text = ft.Text(
            "",
            size=ui_scale['small_size'],
            color=ft.Colors.GREY_600
        )

    def create(self) -> ft.Container:
        """
        创建状态栏

        Returns:
            状态栏容器
        """
        return ft.Container(
            content=ft.Row([
                ft.Text("📌 状态:", size=self.ui_scale['small_size'], color=ft.Colors.GREY_500),
                self.status_text,
                ft.Container(expand=True),
                self.api_count_text,
            ]),
            padding=ft.padding.only(left=10, right=10, top=5, bottom=5),
            bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.GREY_400),
        )

    def set_status(self, text: str):
        """
        设置状态文本

        Args:
            text: 状态文本
        """
        self.status_text.value = text
        self.status_text.update()

    def set_api_count(self, count: int, available: int):
        """
        设置 API 数量

        Args:
            count: 总 API 数量
            available: 可用 API 数量
        """
        if count > 0:
            self.api_count_text.value = f"🔌 API: {available}/{count}"
        else:
            self.api_count_text.value = "🔌 API: 未检测"
        self.api_count_text.update()

    def set_working(self):
        """设置工作中状态"""
        self.set_status("工作中...")

    def set_ready(self):
        """设置就绪状态"""
        self.set_status("就绪")

    def set_complete(self):
        """设置完成状态"""
        self.set_status("✅ 完成")

    def set_error(self, message: str = "错误"):
        """设置错误状态"""
        self.set_status(f"❌ {message}")
