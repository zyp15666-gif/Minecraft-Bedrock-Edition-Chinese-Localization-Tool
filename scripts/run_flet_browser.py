#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动 Minecraft 基岩版汉化工具 - Flet 浏览器模式
无需下载桌面客户端，直接在浏览器中运行
"""

import sys
import os
import warnings
warnings.filterwarnings("ignore", category=SyntaxWarning)

# 添加项目根目录到路径（使用统一的路径处理）
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)


def main(page):
    """Flet应用主函数"""
    from ui.main_window import MinecraftTranslatorApp
    app = MinecraftTranslatorApp(page)


if __name__ == "__main__":
    import flet as ft

    print("=" * 60)
    print("🎮 正在启动 Minecraft 基岩版汉化工具...")
    print("✨ Flet 现代化 UI 界面（浏览器模式）")
    print("=" * 60)
    print()
    print("提示：浏览器模式无需下载桌面客户端")
    print("      适合快速测试和轻量级使用")
    print()

    # 使用新版API（0.85+）
    if hasattr(ft, 'run'):
        ft.run(main=main)
    else:
        # 兼容旧版本
        ft.app(target=main)