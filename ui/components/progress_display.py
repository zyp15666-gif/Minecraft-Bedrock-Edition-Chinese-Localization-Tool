#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
进度显示组件模块

提供翻译进度条、剩余数量和预计剩余时间显示。

使用方式：
    from ui.components.progress_display import ProgressDisplay

    progress_display = ProgressDisplay(ui_scale, update_func)
    progress_section = progress_display.create()
"""

from typing import Any, Callable, Dict, Optional

import flet as ft


class ProgressDisplay:
    """
    进度显示组件

    提供：
    - 进度条
    - 百分比显示
    - 剩余条目数
    - 预计剩余时间
    """

    def __init__(self, ui_scale: Dict[str, Any], update_func: Optional[Callable] = None):
        """
        初始化进度显示

        Args:
            ui_scale: UI 缩放配置
            update_func: 进度更新回调函数
        """
        self.ui_scale = ui_scale
        self.update_func = update_func

        self.progress_bar = ft.ProgressBar(width=400, value=0, bar_height=8)
        self.progress_text = ft.Text(
            "就绪",
            size=ui_scale['body_size'],
            weight=ft.FontWeight.BOLD
        )
        self.stats_text = ft.Text(
            "",
            size=ui_scale['small_size'],
            color=ft.Colors.GREY_600
        )

    def create(self) -> ft.Container:
        """
        创建进度显示区域

        Returns:
            进度显示容器
        """
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("🔄 进度:", size=self.ui_scale['body_size']),
                    self.progress_text,
                ], alignment=ft.MainAxisAlignment.START),
                ft.Container(height=5),
                self.progress_bar,
                ft.Container(height=3),
                self.stats_text,
            ]),
            padding=10,
            bgcolor=ft.Colors.with_opacity(0.2, ft.Colors.GREY_300),
            border_radius=8,
        )

    def update(self, value: float, text: str = "", remaining_count: int = 0, remaining_time: float = 0.0):
        """
        更新进度显示

        Args:
            value: 进度值 (0.0-1.0)
            text: 进度文本
            remaining_count: 剩余条目数
            remaining_time: 预计剩余时间（秒）
        """
        self.progress_bar.value = value

        if text:
            self.progress_text.value = text
        else:
            percentage = int(value * 100)
            self.progress_text.value = f"{percentage}%"

        stats_parts = []
        if remaining_count > 0:
            stats_parts.append(f"剩余: {remaining_count} 条")
        if remaining_time > 0:
            if remaining_time >= 60:
                stats_parts.append(f"预计: {int(remaining_time / 60)}分")
            else:
                stats_parts.append(f"预计: {int(remaining_time)}秒")

        self.stats_text.value = " | ".join(stats_parts) if stats_parts else ""

        self.progress_bar.update()
        self.progress_text.update()
        self.stats_text.update()

        if self.update_func:
            self.update_func(value, text, remaining_count, remaining_time)

    def set_ready(self):
        """设置就绪状态"""
        self.progress_bar.value = 0
        self.progress_text.value = "就绪"
        self.stats_text.value = ""
        self.progress_bar.update()
        self.progress_text.update()
        self.stats_text.update()

    def set_complete(self):
        """设置完成状态"""
        self.progress_bar.value = 1.0
        self.progress_text.value = "✅ 完成"
        self.stats_text.value = ""
        self.progress_bar.update()
        self.progress_text.update()

    def set_error(self, message: str = "错误"):
        """设置错误状态"""
        self.progress_text.value = f"❌ {message}"
        self.stats_text.value = ""
        self.progress_text.update()
        self.stats_text.update()
