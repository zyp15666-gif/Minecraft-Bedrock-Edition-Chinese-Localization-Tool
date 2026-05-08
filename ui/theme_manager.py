#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI主题和样式管理器

统一管理应用的视觉主题、配色方案和样式配置。
支持高对比度模式（跟随系统设置）。
"""

from typing import Any, Dict

import flet as ft

try:
    from ui.accessibility import detect_high_contrast_mode, get_system_text_scale
    ACCESSIBILITY_AVAILABLE = True
except ImportError:
    ACCESSIBILITY_AVAILABLE = False


class UITheme:
    """UI主题定义"""

    DARK_COLORS = {
        'bg_primary': '#1E1E2E',
        'bg_secondary': '#2D2D44',
        'bg_elevated': '#363654',
        'text_primary': '#FFFFFF',
        'text_secondary': '#B0B0C0',
        'accent': '#6C9BF2',
        'accent_hover': '#8AB4F2',
        'success': '#4CAF50',
        'warning': '#FF9800',
        'error': '#F44336',
        'border': '#404060',
    }

    LIGHT_COLORS = {
        'bg_primary': '#F5F5F5',
        'bg_secondary': '#FFFFFF',
        'bg_elevated': '#FFFFFF',
        'text_primary': '#1E1E2E',
        'text_secondary': '#606080',
        'accent': '#4A90D9',
        'accent_hover': '#3A7BC8',
        'success': '#4CAF50',
        'warning': '#FF9800',
        'error': '#F44336',
        'border': '#E0E0E0',
    }

    HIGH_CONTRAST_COLORS = {
        'bg_primary': '#000000',
        'bg_secondary': '#000000',
        'bg_elevated': '#1A1A1A',
        'text_primary': '#FFFFFF',
        'text_secondary': '#FFFFFF',
        'accent': '#FFFF00',
        'accent_hover': '#FFFF00',
        'success': '#00FF00',
        'warning': '#FFFF00',
        'error': '#FF0000',
        'border': '#FFFFFF',
    }

    @classmethod
    def get_colors(cls, is_dark: bool = True, high_contrast: bool = False) -> Dict[str, str]:
        """获取主题颜色

        Args:
            is_dark: 是否使用暗色模式
            high_contrast: 是否使用高对比度模式

        Returns:
            颜色配置字典
        """
        if high_contrast:
            return cls.HIGH_CONTRAST_COLORS
        return cls.DARK_COLORS if is_dark else cls.LIGHT_COLORS


class ThemeManager:
    """主题管理器"""

    def __init__(self, is_dark_mode: bool = True, detect_system_high_contrast: bool = True):
        """初始化主题管理器

        Args:
            is_dark_mode: 是否使用暗色模式
            detect_system_high_contrast: 是否检测系统高对比度模式
        """
        self.is_dark_mode = is_dark_mode
        self._high_contrast_mode = False

        if detect_system_high_contrast and ACCESSIBILITY_AVAILABLE:
            self._high_contrast_mode = detect_high_contrast_mode()

        self.colors = UITheme.get_colors(is_dark_mode, self._high_contrast_mode)

    @property
    def high_contrast_mode(self) -> bool:
        return self._high_contrast_mode

    def update_colors(self, is_dark_mode: bool):
        """更新主题颜色"""
        self.is_dark_mode = is_dark_mode
        self.colors = UITheme.get_colors(is_dark_mode, self._high_contrast_mode)

    def set_high_contrast_mode(self, enabled: bool):
        """设置高对比度模式"""
        self._high_contrast_mode = enabled
        self.colors = UITheme.get_colors(self.is_dark_mode, enabled)

    def get_page_dark_mode_config(self) -> ft.DarkModeConfig:
        """获取页面深色模式配置"""
        return ft.DarkModeConfig(
            theme_mode=ft.ThemeMode.DARK if self.is_dark_mode else ft.ThemeMode.LIGHT,
            primary_color=ft.Colors.BLUE,
        )

    def get_button_style(self) -> ft.ButtonStyle:
        """获取按钮样式"""
        return ft.ButtonStyle(
            bgcolor={
                ft.MaterialState.DEFAULT: self.colors['bg_elevated'],
                ft.MaterialState.HOVERED: self.colors['accent'],
            },
            color={
                ft.MaterialState.DEFAULT: self.colors['text_primary'],
                ft.MaterialState.HOVERED: self.colors['text_primary'],
            },
            padding=10,
            shape=ft.RoundedRectangleBorder(radius=8),
        )

    def get_textfield_style(self) -> ft.TextFieldStyle:
        """获取文本框样式"""
        return ft.TextFieldStyle(
            border_color=self.colors['border'],
            focused_border_color=self.colors['accent'],
            text_style=ft.TextStyle(color=self.colors['text_primary']),
            label_style=ft.TextStyle(color=self.colors['text_secondary']),
        )

    def get_card_style(self) -> ft.CardStyle:
        """获取卡片样式"""
        return ft.CardStyle(
            bgcolor=self.colors['bg_secondary'],
            elevation=ft.CardElevationElevation(),
            shape=ft.RoundedRectangleBorder(radius=12),
        )

    def get_container_style(self) -> Dict[str, Any]:
        """获取容器样式"""
        return {
            'padding': 15,
            'border_radius': 10,
            'bgcolor': self.colors['bg_secondary'],
        }

    def get_divider_style(self) -> ft.DividerStyle:
        """获取分割线样式"""
        return ft.DividerStyle(
            color=self.colors['border'],
            thickness=1,
        )


class UIScaleManager:
    """UI缩放管理器"""

    def __init__(self, scale: float = 1.0):
        """初始化UI缩放管理器

        Args:
            scale: 缩放比例，1.0表示原始大小
        """
        self._scale = max(0.5, min(2.0, scale))

    @property
    def scale(self) -> float:
        """获取当前缩放比例"""
        return self._scale

    @scale.setter
    def scale(self, value: float):
        """设置缩放比例"""
        self._scale = max(0.5, min(2.0, value))

    def scaled_size(self, base_size: float) -> float:
        """获取缩放后的大小"""
        return base_size * self._scale

    def scaled_padding(self, base_padding: float) -> float:
        """获取缩放后的内边距"""
        return base_padding * self._scale

    def get_font_size(self, base_size: float) -> float:
        """获取缩放后的字体大小"""
        return base_size * self._scale

    def get_icon_size(self, base_size: float) -> float:
        """获取缩放后的图标大小"""
        return base_size * self._scale
