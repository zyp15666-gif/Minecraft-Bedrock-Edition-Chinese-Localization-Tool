"""
Minecraft 基岩版汉化工具 — UI 入口（兼容旧 import 路径）。

实现位于 ui.application；启动前安装全局钩子。
"""

from ui.bootstrap import install_app_hooks

install_app_hooks()

from ui.application import MinecraftTranslatorApp, main  # noqa: E402

__all__ = ["MinecraftTranslatorApp", "main"]
