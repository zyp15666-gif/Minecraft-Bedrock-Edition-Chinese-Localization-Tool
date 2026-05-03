"""
UI工具函数模块 - 从main_window_flet.py分离出的通用辅助函数

本模块包含所有独立的工具函数，不再依赖于MinecraftTranslatorApp类。
所有函数接收必要的参数并返回计算结果。
"""

import flet as ft
from typing import Dict, Any, Optional, List, Tuple


def get_theme_color(page: ft.Page, theme_colors: Dict[str, Dict[str, Any]], color_name: str) -> Any:
    """
    获取当前主题下的颜色
    
    Args:
        page: ft.Page对象，用于获取当前主题模式
        theme_colors: 主题颜色字典，包含'dark'和'light'键
        color_name: 颜色名称
        
    Returns:
        对应主题模式下的颜色值
    """
    mode = page.theme_mode
    if mode == ft.ThemeMode.DARK:
        return theme_colors['dark'].get(color_name, ft.Colors.BLACK)
    else:
        return theme_colors['light'].get(color_name, ft.Colors.WHITE)


def generate_api_name(config: Dict[str, Any], provider: str) -> str:
    """
    生成唯一的API名称
    
    Args:
        config: 配置字典
        provider: API提供商名�?        
    Returns:
        唯一的API名称
    """
    base_name = f"{provider}_"
    existing_names = set()
    
    # 收集现有API名称
    for provider_key in ["deepseek", "qwen", "zhipu", "doubao", "local_ollama"]:
        apis = config.get(provider_key, [])
        if isinstance(apis, list):
            for api in apis:
                if "name" in api:
                    existing_names.add(api["name"])
    
    # 生成唯一名称
    counter = 1
    while True:
        name = f"{base_name}{counter}"
        if name not in existing_names:
            return name
        counter += 1


def create_ui_scale(scale: float) -> Dict[str, Any]:
    """
    创建UI缩放配置
    
    Args:
        scale: 缩放因子
        
    Returns:
        UI缩放配置字典
    """
    return {
        'title_size': int(24 * scale),
        'subtitle_size': int(18 * scale),
        'section_title_size': int(16 * scale),
        'body_size': int(14 * scale),
        'small_size': int(12 * scale),
        'padding': int(15 * scale),
        'border_radius': int(8 * scale),
        'button_padding': int(10 * scale),
        'button_height': int(40 * scale),
    }


def format_file_size(size_bytes: int) -> str:
    """
    格式化文件大�?    
    Args:
        size_bytes: 文件大小（字节）
        
    Returns:
        格式化后的文件大小字符串
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def truncate_text(text: str, max_length: int, ellipsis: str = "...") -> str:
    """
    截断文本，添加省略号
    
    Args:
        text: 原始文本
        max_length: 最大长度
        ellipsis: 省略号字符串
        
    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(ellipsis)] + ellipsis


class ProgressThrottler:
    """UI进度更新节流器

    合并同一时间段内的多次进度更新，限制更新频率。
    避免后台线程频繁通过 page.run_task 更新进度导致UI卡顿。

    使用示例:
        throttler = ProgressThrottler(min_interval=0.1)
        throttler.update(0.5, "翻译中", 10, 5.0)
        # 仅在间隔足够时才触发实际更新
    """

    def __init__(self, min_interval: float = 0.1, significant_delta: float = 0.05):
        """初始化节流器

        Args:
            min_interval: 最小更新间隔（秒），默认100ms
            significant_delta: 显著进度变化阈值，默认5%
        """
        self.min_interval = min_interval
        self.significant_delta = significant_delta
        self._last_update_time: float = 0.0
        self._last_value: float = -1.0
        self._last_text: str = ""
        self._last_remaining: int = -1
        self._pending_update = None

    def should_update(
        self,
        value: float,
        text: str = "",
        remaining_count: int = 0,
        remaining_time: float = 0.0
    ) -> bool:
        """判断是否应该执行UI更新

        策略：
        1. 进度变化超过阈值 -> 立即更新
        2. 进度从0到1或1到0 -> 立即更新
        3. 距离上次更新超过最小间隔 -> 更新
        4. 文本或剩余数变化 -> 更新（但受间隔限制）
        5. 无实质变化 -> 跳过

        Args:
            value: 进度值 (0.0-1.0)
            text: 进度文本
            remaining_count: 剩余条目数
            remaining_time: 预计剩余时间

        Returns:
            是否应该执行UI更新
        """
        import time
        current_time = time.time()

        value = max(0.0, min(1.0, float(value))) if value is not None else 0.0

        progress_delta = abs(value - self._last_value) if self._last_value >= 0 else 1.0

        is_significant = (
            progress_delta >= self.significant_delta or
            (value == 1.0 and self._last_value < 1.0) or
            (value == 0.0 and self._last_value > 0.0)
        )

        text_changed = text != self._last_text
        remaining_changed = remaining_count != self._last_remaining

        time_elapsed = current_time - self._last_update_time >= self.min_interval

        if is_significant:
            should = True
        elif time_elapsed and (text_changed or remaining_changed or progress_delta > 0):
            should = True
        elif time_elapsed and progress_delta > 0.01:
            should = True
        else:
            should = False

        if should:
            self._last_update_time = current_time
            self._last_value = value
            self._last_text = text
            self._last_remaining = remaining_count

        return should