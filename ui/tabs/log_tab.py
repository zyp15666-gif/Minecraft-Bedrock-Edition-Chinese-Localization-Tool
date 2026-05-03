#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志标签页组件

提供日志显示和管理功能。

使用方式：
    from ui.tabs.log_tab import create_log_tab

    container, log_display = create_log_tab(context, callbacks)
"""

import os
import subprocess
import flet as ft
from typing import TYPE_CHECKING, Dict, Any, Callable, Tuple

if TYPE_CHECKING:
    from ui.tabs.context import UIContext


def _get_log_dir() -> str:
    """获取日志目录路径"""
    documents_dir = os.path.join(os.path.expanduser("~"), "Documents")
    return os.path.join(documents_dir, "Minecraft基岩版汉化工具", "logs")


def _open_log_folder(e):
    """打开日志文件夹"""
    log_dir = _get_log_dir()
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    subprocess.run(['explorer', log_dir], check=False)


def create_log_tab(
    context: 'UIContext',
    callbacks: Dict[str, Callable]
) -> Tuple[ft.Control, ft.ListView]:
    """
    创建日志标签页（使用动态缩放 + 内嵌日志窗口）

    Args:
        context: UI上下文对象
        callbacks: 回调函数字典，包含以下键：
            - show_log_in_page: 在页面内显示详细日志函数
            - clear_log_display: 清空日志显示函数

    Returns:
        Tuple[container, log_display]:
            container: 日志标签页容器
            log_display: 日志显示列表视图控件引用
    """
    s = context.ui_scale
    scale = context.scale

    show_log_in_page = callbacks.get('show_log_in_page')
    clear_log_display = callbacks.get('clear_log_display')

    log_display = ft.ListView(
        expand=True,
        spacing=int(5 * scale),
        padding=int(10 * scale),
        auto_scroll=True,
    )

    log_display.controls.append(
        ft.Text("📝 暂无日志记录",
                size=s['body_size'],
                color=context.get_color('text_secondary'),
                italic=True,
                text_align=ft.TextAlign.CENTER)
    )

    container = ft.Column([
        ft.Container(
            content=ft.Column([
                ft.Text("📋 操作日志", size=s['section_title_size'], weight=ft.FontWeight.BOLD, color=context.get_color(
                    'text_primary')),
                ft.Divider(height=int(5 * scale)),
                ft.Row([
                    ft.ElevatedButton(
                        "🗑️ 清空日志",
                        icon=ft.Icons.DELETE_OUTLINE,
                        on_click=clear_log_display if clear_log_display else None,
                        style=ft.ButtonStyle(
                            text_style=ft.TextStyle(size=s['body_size'])
                        ),
                        tooltip="清空当前显示的日志内容",
                    ),
                    ft.ElevatedButton(
                        "📄 查看完整日志",
                        icon=ft.Icons.DESCRIPTION,
                        on_click=show_log_in_page if show_log_in_page else None,
                        style=ft.ButtonStyle(
                            text_style=ft.TextStyle(size=s['body_size'])
                        ),
                        tooltip="在新窗口中查看完整的运行日志",
                    ),
                    ft.ElevatedButton(
                        "📁 打开日志文件夹",
                        icon=ft.Icons.FOLDER_OPEN,
                        on_click=_open_log_folder,
                        style=ft.ButtonStyle(
                            text_style=ft.TextStyle(size=s['body_size'])
                        ),
                        tooltip="在文件管理器中打开日志文件夹",
                    ),
                ], spacing=int(10 * scale), wrap=True),
            ]),
            padding=int(10 * scale),
            bgcolor=context.get_color('primary_bg'),
            border_radius=s['border_radius'],
        ),

        ft.Container(
            content=log_display,
            expand=True,
            padding=int(10 * scale),
            bgcolor=context.get_color('card_bg'),
            border_radius=s['border_radius'],
        ),
    ], expand=True, spacing=int(10 * scale))

    return container, log_display
