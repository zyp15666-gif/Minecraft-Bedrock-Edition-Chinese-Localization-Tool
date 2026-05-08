#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
进度条组件模块

提供进度条和状态显示组件。

使用方式：
    from ui.tabs.progress import create_progress_section

    container, progress_bar = create_progress_section(context, progress_text)
"""

from typing import TYPE_CHECKING

import flet as ft

if TYPE_CHECKING:
    from ui.tabs.context import UIContext


def create_progress_section(
    context: 'UIContext',
    progress_text: ft.Text
) -> tuple[ft.Control, ft.ProgressBar]:
    """
    创建进度条和状态显示区域（使用响应式设计）

    Args:
        context: UI上下文对象
        progress_text: 进度文本控件

    Returns:
        元组(container, progress_bar):
            container: 进度区域容器
            progress_bar: 进度条控件引用
    """
    s = context.ui_scale

    progress_bar = ft.ProgressBar(
        value=0,
        expand=True,
        color=ft.Colors.BLUE,
        bgcolor=context.get_color('tertiary_bg'),
    )

    container = ft.Container(
        content=ft.Column([
            ft.Text("📊 进度", size=s['section_title_size'],
                    weight=ft.FontWeight.BOLD, color=context.get_color('text_primary')),
            ft.Container(
                content=progress_bar,
                padding=ft.padding.only(top=5, bottom=5),
            ),
            ft.Container(
                content=progress_text,
                padding=ft.padding.only(top=3),
            ),
        ]),
        padding=s['padding'],
        bgcolor=context.get_color('primary_bg'),
        border_radius=s['border_radius'],
    )

    return container, progress_bar
