#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
可访问性工具模块

提供 UI 可访问性支持：
- 屏幕阅读器语义标签
- 键盘导航支持
- 高对比度模式检测
- 焦点管理

Windows 10/11 可访问性特性：
- Windows 讲述人 (Narrator)
- NVDA 屏幕阅读器
- 高对比度模式
- 放大镜
"""

import os
import sys
import logging
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_IS_WINDOWS = sys.platform == 'win32'


@dataclass
class AccessibilityConfig:
    """可访问性配置"""
    high_contrast_mode: bool = False
    screen_reader_active: bool = False
    text_scale: float = 1.0
    focus_visible: bool = True


def detect_high_contrast_mode() -> bool:
    """检测系统是否启用了高对比度模式

    Returns:
        True 表示高对比度模式已启用
    """
    if not _IS_WINDOWS:
        return False

    try:
        import ctypes
        high_contrast = ctypes.c_uint()
        result = ctypes.windll.user32.SystemParametersInfoW(
            0x0042,  # SPI_GETHIGHCONTRAST
            ctypes.sizeof(high_contrast),
            ctypes.byref(high_contrast),
            0
        )
        if result:
            return bool(high_contrast.value & 0x00000001)
    except Exception as e:
        logger.debug(f"检测高对比度模式失败: {e}")

    return False


def detect_screen_reader() -> bool:
    """检测是否有屏幕阅读器正在运行

    Returns:
        True 表示检测到屏幕阅读器
    """
    if not _IS_WINDOWS:
        return False

    screen_reader_processes = [
        'nvda',       # NVDA
        'nvdaw',      # NVDA
        'jfw',        # JAWS
        'jfw64',      # JAWS 64-bit
        'narrator',   # Windows 讲述人
        'Narrator',   # Windows 讲述人
        'ZoomText',   # ZoomText
        'fusion',     # Freedom Scientific Fusion
    ]

    try:
        import psutil
        for proc in psutil.process_iter(['name']):
            name = proc.info.get('name', '').lower()
            if any(sr.lower() in name for sr in screen_reader_processes):
                logger.info(f"检测到屏幕阅读器: {name}")
                return True
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"检测屏幕阅读器失败: {e}")

    return False


def get_system_text_scale() -> float:
    """获取系统文本缩放比例

    Returns:
        文本缩放比例（1.0 = 100%）
    """
    if not _IS_WINDOWS:
        return 1.0

    try:
        import ctypes
        dc = ctypes.windll.user32.GetDC(0)
        if dc:
            LOGPIXELSY = 90
            dpi = ctypes.windll.gdi32.GetDeviceCaps(dc, LOGPIXELSY)
            ctypes.windll.user32.ReleaseDC(0, dc)
            return dpi / 96.0
    except Exception as e:
        logger.debug(f"获取系统文本缩放失败: {e}")

    return 1.0


def get_accessibility_config() -> AccessibilityConfig:
    """获取当前可访问性配置

    Returns:
        AccessibilityConfig 实例
    """
    return AccessibilityConfig(
        high_contrast_mode=detect_high_contrast_mode(),
        screen_reader_active=detect_screen_reader(),
        text_scale=get_system_text_scale()
    )


class AccessibilityHelper:
    """可访问性辅助类 - 为 Flet 控件添加可访问性支持"""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return

        self._config = get_accessibility_config()
        self._focus_order: List[str] = []
        self._focus_index = 0

        self._initialized = True

        if self._config.screen_reader_active:
            logger.info("检测到屏幕阅读器，已启用增强可访问性支持")
        if self._config.high_contrast_mode:
            logger.info("检测到高对比度模式，已启用高对比度主题")

    @property
    def config(self) -> AccessibilityConfig:
        return self._config

    def is_screen_reader_active(self) -> bool:
        return self._config.screen_reader_active

    def is_high_contrast_mode(self) -> bool:
        return self._config.high_contrast_mode

    def get_text_scale(self) -> float:
        return self._config.text_scale

    def create_accessible_button(
        self,
        label: str,
        on_click: Optional[Callable] = None,
        tooltip: Optional[str] = None,
        icon: Optional[str] = None,
        focus_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """创建可访问性按钮

        Args:
            label: 按钮文本
            on_click: 点击回调
            tooltip: 工具提示
            icon: 图标
            focus_id: 焦点 ID（用于键盘导航）

        Returns:
            按钮配置字典
        """
        import flet as ft

        tooltip_text = tooltip or label

        button = ft.ElevatedButton(
            text=label,
            on_click=on_click,
            tooltip=tooltip_text,
            icon=icon,
        )

        if focus_id:
            button.data = focus_id
            if focus_id not in self._focus_order:
                self._focus_order.append(focus_id)

        return button

    def create_accessible_text(
        self,
        value: str,
        label: Optional[str] = None,
        semantic_label: Optional[str] = None
    ) -> Dict[str, Any]:
        """创建可访问性文本

        Args:
            value: 文本内容
            label: 关联标签
            semantic_label: 语义标签（屏幕阅读器读取）

        Returns:
            文本配置字典
        """
        import flet as ft

        return ft.Text(
            value=value,
            tooltip=semantic_label or label,
        )

    def create_accessible_text_field(
        self,
        label: str,
        value: str = "",
        hint_text: Optional[str] = None,
        on_change: Optional[Callable] = None,
        focus_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """创建可访问性文本输入框

        Args:
            label: 标签
            value: 初始值
            hint_text: 提示文本
            on_change: 变化回调
            focus_id: 焦点 ID

        Returns:
            文本输入框配置字典
        """
        import flet as ft

        return ft.TextField(
            label=label,
            value=value,
            hint_text=hint_text or f"请输入{label}",
            on_change=on_change,
        )

    def get_high_contrast_colors(self) -> Dict[str, str]:
        """获取高对比度配色方案

        Returns:
            颜色配置字典
        """
        if self._config.high_contrast_mode:
            return {
                'background': '#000000',
                'text': '#FFFFFF',
                'primary': '#FFFF00',
                'secondary': '#00FFFF',
                'error': '#FF0000',
                'success': '#00FF00',
                'border': '#FFFFFF',
                'focus': '#FFFF00',
            }
        return {
            'background': '#FFFFFF',
            'text': '#000000',
            'primary': '#1976D2',
            'secondary': '#424242',
            'error': '#D32F2F',
            'success': '#388E3C',
            'border': '#BDBDBD',
            'focus': '#1976D2',
        }

    def announce_to_screen_reader(self, page, message: str):
        """向屏幕阅读器发送通知

        Args:
            page: Flet 页面对象
            message: 通知消息
        """
        if not self._config.screen_reader_active:
            return

        try:
            import flet as ft
            page.snack_bar = ft.SnackBar(
                content=ft.Text(message),
                duration=3000,
            )
            page.snack_bar.open = True
            page.update()
        except Exception as e:
            logger.debug(f"发送屏幕阅读器通知失败: {e}")


_accessibility_helper: Optional[AccessibilityHelper] = None


def get_accessibility_helper() -> AccessibilityHelper:
    """获取可访问性辅助器单例"""
    global _accessibility_helper
    if _accessibility_helper is None:
        _accessibility_helper = AccessibilityHelper()
    return _accessibility_helper


def create_accessible_button(
    label: str,
    on_click: Optional[Callable] = None,
    tooltip: Optional[str] = None,
    icon: Optional[str] = None,
    focus_id: Optional[str] = None
):
    """便捷函数：创建可访问性按钮"""
    return get_accessibility_helper().create_accessible_button(
        label=label,
        on_click=on_click,
        tooltip=tooltip,
        icon=icon,
        focus_id=focus_id
    )


def announce(message: str, page=None):
    """便捷函数：向屏幕阅读器发送通知"""
    helper = get_accessibility_helper()
    if page and helper.is_screen_reader_active():
        helper.announce_to_screen_reader(page, message)


if __name__ == "__main__":
    config = get_accessibility_config()
    print(f"高对比度模式: {config.high_contrast_mode}")
    print(f"屏幕阅读器: {config.screen_reader_active}")
    print(f"文本缩放: {config.text_scale * 100:.0f}%")
