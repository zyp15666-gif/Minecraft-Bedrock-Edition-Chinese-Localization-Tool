"""
UI标签页模块 - 从main_window_flet.py分离出的标签页组件

本模块包含所有独立的标签页构建函数，不再依赖于MinecraftTranslatorApp类。
所有函数接收必要的参数并返回ft.Control对象。

模块结构：
- context.py: UIContext 类
- status_bar.py: 状态栏组件
- function_buttons.py: 功能按钮组件
- progress.py: 进度条组件
- config_tab.py: 配置标签页
- log_tab.py: 日志标签页

使用方式：
    from ui.tabs import UIContext, create_status_bar, create_function_buttons
"""

from ui.tabs.context import UIContext
from ui.tabs.status_bar import create_status_bar
from ui.tabs.function_buttons import create_function_buttons
from ui.tabs.progress import create_progress_section
from ui.tabs.config_tab import create_config_tab
from ui.tabs.log_tab import create_log_tab

__all__ = [
    'UIContext',
    'create_status_bar',
    'create_function_buttons',
    'create_progress_section',
    'create_config_tab',
    'create_log_tab',
]
