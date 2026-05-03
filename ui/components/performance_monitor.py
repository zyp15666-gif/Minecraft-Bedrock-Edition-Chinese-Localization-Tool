#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能监控组件

提供翻译性能监控功能，包括：
- 翻译速度（条/秒）
- API 响应时间统计
- 缓存命中率
- 熔断器状态

使用方式：
    from ui.components.performance_monitor import PerformanceMonitor

    monitor = PerformanceMonitor(ui_scale)
    container = monitor.create()
"""

import flet as ft
from typing import Dict, Any, Optional, Callable


class PerformanceMonitor:
    """
    性能监控组件

    显示：
    - 翻译速度
    - API 响应时间
    - 缓存命中率
    - 熔断器状态
    """

    def __init__(
        self,
        ui_scale: Dict[str, Any],
        get_stats_func: Optional[Callable] = None
    ):
        """
        初始化性能监控组件

        Args:
            ui_scale: UI 缩放配置
            get_stats_func: 获取统计数据的回调函数
        """
        self.ui_scale = ui_scale
        self.get_stats_func = get_stats_func

        self.translation_speed_text = ft.Text("--", size=14, weight=ft.FontWeight.BOLD)
        self.cache_hit_rate_text = ft.Text("--", size=14, weight=ft.FontWeight.BOLD)
        self.api_stats_text = ft.Text("--", size=12)
        self.circuit_breaker_text = ft.Text("--", size=12)

    def create(self) -> ft.Container:
        """
        创建性能监控区域

        Returns:
            性能监控容器
        """
        s = self.ui_scale

        return ft.Container(
            content=ft.Column([
                ft.Text("📊 性能监控", size=s['section_title_size'], weight=ft.FontWeight.BOLD),
                ft.Divider(height=10),

                ft.Row([
                    ft.Container(
                        content=ft.Column([
                            ft.Text("翻译速度", size=12, color=ft.Colors.GREY),
                            self.translation_speed_text,
                            ft.Text("条/秒", size=10, color=ft.Colors.GREY),
                        ]),
                        padding=10,
                        bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.BLUE),
                        border_radius=5,
                    ),
                    ft.Container(
                        content=ft.Column([
                            ft.Text("缓存命中率", size=12, color=ft.Colors.GREY),
                            self.cache_hit_rate_text,
                            ft.Text("", size=10, color=ft.Colors.GREY),
                        ]),
                        padding=10,
                        bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.GREEN),
                        border_radius=5,
                    ),
                ], spacing=10),

                ft.Divider(height=5),

                ft.Text("API 统计:", size=12, weight=ft.FontWeight.BOLD),
                self.api_stats_text,

                ft.Divider(height=5),

                ft.Text("熔断器:", size=12, weight=ft.FontWeight.BOLD),
                self.circuit_breaker_text,
            ], scroll=ft.ScrollMode.AUTO),
            padding=10,
            bgcolor=ft.Colors.with_opacity(0.2, ft.Colors.GREY),
            border_radius=8,
        )

    def update_stats(self, stats: Dict[str, Any]):
        """
        更新性能统计

        Args:
            stats: 统计数据字典
        """
        if not stats:
            return

        if 'translation_speed' in stats:
            speed = stats['translation_speed']
            self.translation_speed_text.value = f"{speed:.1f}" if speed else "--"
            self.translation_speed_text.update()

        if 'cache_stats' in stats:
            cache_stats = stats['cache_stats']
            if cache_stats:
                hit_rate = cache_stats.get('hit_rate', 0)
                self.cache_hit_rate_text.value = f"{hit_rate:.0%}" if hit_rate else "--"
                self.cache_hit_rate_text.update()

        if 'circuit_breaker_stats' in stats:
            cb_stats = stats['circuit_breaker_stats']
            if cb_stats:
                states = {}
                for api_name, state_info in cb_stats.items():
                    state = state_info.get('state', 'unknown')
                    states[state] = states.get(state, 0) + 1

                state_text = ", ".join([f"{k}: {v}" for k, v in states.items()])
                self.circuit_breaker_text.value = state_text or "--"
                self.circuit_breaker_text.update()

    def refresh(self):
        """刷新统计数据"""
        if self.get_stats_func:
            stats = self.get_stats_func()
            self.update_stats(stats)
