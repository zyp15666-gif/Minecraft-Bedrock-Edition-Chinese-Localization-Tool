#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
状态栏组件模块

提供应用状态栏组件。

使用方式：
    from ui.tabs.status_bar import create_status_bar

    status_bar = create_status_bar(context)
"""

from typing import TYPE_CHECKING

import flet as ft

if TYPE_CHECKING:
    from ui.tabs.context import UIContext


def create_status_bar(context: 'UIContext') -> ft.Control:
    """
    创建状态栏（使用动态缩放）

    Args:
        context: UI上下文对象

    Returns:
        状态栏容器
    """
    s = context.ui_scale

    def get_theme_toggle_text():
        if context.page.theme_mode == ft.ThemeMode.LIGHT:
            return "🌙 暗夜模式"
        else:
            return "🌞 日间模式"

    return ft.Container(
        content=ft.Row([
            ft.Row([
                ft.ElevatedButton(
                    get_theme_toggle_text(),
                    on_click=context.get_callback('toggle_dark_mode'),
                ),
                ft.Text(
                    context.get_callback('get_author_text')() if context.get_callback('get_author_text') else "Minecraft基岩版汉化工具",
                    size=int(s['body_size'] * 1.2),
                    weight=ft.FontWeight.BOLD,
                    color=context.get_color('accent_text')
                ),
            ], alignment=ft.MainAxisAlignment.END),
        ], alignment=ft.MainAxisAlignment.END),
        padding=s['padding'],
        bgcolor=context.get_color('secondary_bg'),
        border_radius=s['border_radius'],
    )
