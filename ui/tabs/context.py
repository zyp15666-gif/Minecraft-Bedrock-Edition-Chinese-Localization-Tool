#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI 上下文模块

提供 UIContext 类，封装标签页构建所需的共享状态。

使用方式：
    from ui.tabs.context import UIContext

    context = UIContext(page, ui_scale, scale, theme_colors, callbacks)
"""

import threading
from typing import Dict, Any, Callable, Optional, List

import flet as ft

from ui.utils import get_theme_color


class UIContext:
    """
    UI上下文类，封装标签页构建所需的共享状态（线程安全）

    这个类用于替代 MinecraftTranslatorApp 实例的依赖，
    提供标签页构建函数所需的所有参数。
    """

    def __init__(
        self,
        page: ft.Page,
        ui_scale: Dict[str, Any],
        scale: float,
        theme_colors: Dict[str, Dict[str, Any]],
        callbacks: Dict[str, Callable]
    ):
        """
        初始化UI上下文

        Args:
            page: Flet页面对象
            ui_scale: UI缩放配置字典
            scale: 缩放因子
            theme_colors: 主题颜色字典，包含'dark'和'light'键
            callbacks: 回调函数字典，如{'toggle_dark_mode': func}
        """
        self._page = page
        self._ui_scale = ui_scale
        self._scale = scale
        self._theme_colors = theme_colors
        self._callbacks = callbacks
        self._lock = threading.RLock()
        self._cached_theme_mode = None
        self._cached_colors: Dict[str, Any] = {}

    @property
    def page(self) -> ft.Page:
        """获取页面对象"""
        return self._page

    @property
    def ui_scale(self) -> Dict[str, Any]:
        """获取UI缩放配置"""
        return self._ui_scale

    @property
    def scale(self) -> float:
        """获取缩放因子"""
        return self._scale

    def get_color(self, color_name: str) -> Any:
        """
        获取当前主题下的颜色（线程安全，带缓存）

        Args:
            color_name: 颜色名称

        Returns:
            对应主题模式下的颜色值
        """
        with self._lock:
            current_mode = self._page.theme_mode if hasattr(self._page, 'theme_mode') else None

            cache_key = f"{current_mode}_{color_name}"
            if cache_key in self._cached_colors:
                return self._cached_colors[cache_key]

            color = get_theme_color(self._page, self._theme_colors, color_name)
            self._cached_colors[cache_key] = color
            return color

    def get_function_buttons_config(self) -> List[Dict[str, Any]]:
        """获取功能按钮配置列表（线程安全）"""
        with self._lock:
            getter = self._callbacks.get('get_function_buttons_config')
            if getter:
                return getter()
            return []

    def get_callback(self, key: str) -> Optional[Callable]:
        """获取回调函数（线程安全）"""
        with self._lock:
            return self._callbacks.get(key)

    def invalidate_theme_cache(self):
        """清除主题颜色缓存"""
        with self._lock:
            self._cached_colors.clear()

    def clear_color_cache(self):
        """清除主题颜色缓存（别名方法）"""
        self.invalidate_theme_cache()
