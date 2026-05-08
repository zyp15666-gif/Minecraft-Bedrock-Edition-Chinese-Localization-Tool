#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
窗口管理器模块

处理窗口初始化、分辨率适配和主题感知。

使用方式：
    from ui.window.window_manager import WindowManager

    window_manager = WindowManager(page, log_func)
    window_manager.initialize_window()
"""

from typing import Any, Callable, Dict, Optional, Tuple

import flet as ft


class WindowManager:
    """
    窗口管理器

    负责：
    - 窗口初始化
    - 分辨率检测和适配
    - 窗口大小锁定
    - 缩放比例计算
    """

    BASE_WIDTH = 885
    BASE_HEIGHT = 900

    def __init__(self, page: ft.Page, log_func: Optional[Callable] = None):
        """
        初始化窗口管理器

        Args:
            page: Flet 页面对象
            log_func: 日志回调函数
        """
        self.page = page
        self.log_func = log_func or (lambda x: None)

        self.is_low_resolution = False
        self.initial_window_size = (700, 750)
        self.target_height = 750
        self.scale = 1.0
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.button_scale = 1.0

        self.ui_scale: Dict[str, Any] = {}
        self.theme_colors: Dict[str, Dict[str, Any]] = {}

    def log(self, message: str):
        """记录日志"""
        self.log_func(message)

    def initialize_window(self) -> Tuple[int, int, int, int]:
        """
        初始化窗口设置

        Returns:
            (window_width, window_height, min_window_width, min_window_height)
        """
        primary_monitor = None
        _default_width, _default_height = 700, 750

        try:
            import screeninfo

            for monitor in screeninfo.get_monitors():
                if monitor.is_primary:
                    primary_monitor = monitor
                    break

            if primary_monitor:
                screen_width = primary_monitor.width
                screen_height = primary_monitor.height
            else:
                raise RuntimeError("未检测到主显示器")
        except Exception as e:
            self.log(f"⚠️ 无法检测屏幕分辨率 ({e})，使用默认窗口大小")
            screen_width = 1920
            screen_height = 1080

        self.log(f"检测到屏幕分辨率: {screen_width}x{screen_height}")

        window_width, window_height, min_width, max_width, min_height, max_height = \
            self._calculate_window_size(screen_width, screen_height)

        self.page.window.width = window_width
        self.page.window.height = window_height
        self.page.window.min_width = min_width
        self.page.window.max_width = max_width
        self.page.window.min_height = min_height
        self.page.window.max_height = max_height

        self.initial_window_size = (window_width, window_height)
        self.target_height = window_height

        self.log(f"窗口初始大小设置为: {window_width}x{window_height}")
        self.log(f"尺寸范围: {min_width}-{max_width} × {min_height}-{max_height}")

        if self.is_low_resolution:
            self.page.window.resizable = True
            self.log("已启用窗口调整功能（低分辨率模式）")
        else:
            self.page.window.resizable = False
            self.log("窗口大小已完全锁定（2K+模式）")

        self._calculate_scale(window_width, window_height, screen_width)

        return window_width, window_height, min_width, min_height

    def _calculate_window_size(self, screen_width: int, screen_height: int) -> Tuple[int, int, int, int, int, int]:
        """根据屏幕分辨率计算窗口大小"""
        if screen_width >= 2560:
            self.is_low_resolution = False
            self.log("模式: 2K+ 完全锁定 (高度905)")
            return 885, 905, 885, 885, 905, 905

        elif screen_width >= 1920:
            self.is_low_resolution = True
            self.log("模式: 1080p 可拉伸 (600-885 × 650-900)")
            return 700, 750, 600, 885, 650, 900

        elif screen_width >= 1600:
            self.is_low_resolution = True
            self.log("模式: 900p 可拉伸 (500-800 × 500-850)")
            return 550, 600, 500, 800, 500, 850

        elif screen_width >= 1366:
            self.is_low_resolution = True
            self.log("模式: 笔记本 可拉伸 (400-700 × 450-800)")
            return 450, 500, 400, 700, 450, 800

        else:
            self.is_low_resolution = True
            self.log("模式: 小屏 可拉伸 (350-600 × 400-700)")
            return 380, 420, 350, 600, 400, 700

    def _calculate_scale(self, window_width: int, window_height: int, screen_width: int):
        """计算缩放比例"""
        self.scale_x = window_width / self.BASE_WIDTH
        self.scale_y = window_height / self.BASE_HEIGHT
        self.scale = min(self.scale_x, self.scale_y)

        if screen_width >= 2560:
            self.button_scale = self.scale * 1.2
            self.log("功能按钮适度放大: 1.2x (2K+模式)")
        else:
            self.button_scale = self.scale

        self.log(f"UI缩放比例: {self.scale:.2f} (宽度{self.scale_x:.2f}, 高度{self.scale_y:.2f})")
        self.log(f"按钮缩放: {self.button_scale:.2f}")

        self.ui_scale = {
            'title_size': int(24 * self.scale),
            'subtitle_size': int(14 * self.scale),
            'section_title_size': int(18 * self.scale),
            'body_size': int(14 * self.scale),
            'small_size': int(12 * self.scale),
            'button_width': int(150 * self.scale),
            'field_width': int(300 * self.scale),
            'padding': int(15 * self.scale),
            'spacing': int(10 * self.scale),
            'border_radius': int(10 * self.scale),
            'icon_size': int(20 * self.scale),
            'button_text_size': int(13 * self.button_scale),
            'button_icon_size': int(24 * self.button_scale),
            'button_height': int(34 * self.scale),
        }

        self.log(f"UI基准参数已设置: 标题={self.ui_scale['title_size']}px, 按钮={self.ui_scale['button_width']}px")
        self.log(f"功能按钮参数: 文字={self.ui_scale['button_text_size']}px, 图标={self.ui_scale['button_icon_size']}px")

    def init_theme_colors(self) -> Dict[str, Dict[str, Any]]:
        """
        初始化主题颜色

        Returns:
            主题颜色字典
        """
        self.theme_colors = {
            'light': {
                'primary_bg': ft.Colors.BLUE_50,
                'secondary_bg': ft.Colors.GREY_100,
                'tertiary_bg': ft.Colors.GREY_200,
                'card_bg': ft.Colors.WHITE,
                'input_bg': ft.Colors.GREY_50,
                'text_primary': ft.Colors.BLACK,
                'text_secondary': ft.Colors.GREY_600,
                'border_color': ft.Colors.GREY_300,
                'accent_text': ft.Colors.BLUE_700,
            },
            'dark': {
                'primary_bg': '#1E3A5F',
                'secondary_bg': '#2D2D2D',
                'tertiary_bg': '#3A3A3A',
                'card_bg': '#2D3748',
                'input_bg': '#1A202C',
                'text_primary': ft.Colors.WHITE,
                'text_secondary': ft.Colors.GREY_400,
                'border_color': ft.Colors.GREY_700,
                'accent_text': ft.Colors.BLUE_400,
            }
        }
        return self.theme_colors

    def get_theme_color(self, color_name: str) -> Any:
        """
        获取当前主题下的颜色

        Args:
            color_name: 颜色名称

        Returns:
            颜色值
        """
        mode = self.page.theme_mode
        if mode == ft.ThemeMode.DARK:
            return self.theme_colors['dark'].get(color_name, ft.Colors.BLACK)
        else:
            return self.theme_colors['light'].get(color_name, ft.Colors.WHITE)

    def create_window_resize_handler(self):
        """
        创建窗口大小变化处理器

        Returns:
            窗口大小变化回调函数
        """
        def on_window_resized(e):
            try:
                current_height = self.page.window.height
                initial_width, initial_height = self.initial_window_size
                target_h = self.target_height

                if self.is_low_resolution:
                    if current_height != target_h:
                        self.page.window.height = target_h
                        self.page.update()
            except Exception as ex:
                self.log(f"⚠️ 窗口大小调整失败: {ex}")

        return on_window_resized

    def get_window_state(self) -> Dict[str, Any]:
        """
        获取窗口状态

        Returns:
            窗口状态字典
        """
        return {
            'is_low_resolution': self.is_low_resolution,
            'initial_window_size': self.initial_window_size,
            'target_height': self.target_height,
            'scale': self.scale,
            'scale_x': self.scale_x,
            'scale_y': self.scale_y,
            'button_scale': self.button_scale,
            'ui_scale': self.ui_scale,
        }
