"""
启动 Minecraft 基岩版汉化工具 - Flet 桌面客户端模式
使用桌面客户端，可以完全控制窗口大小和位置

使用方式：
    python run_flet_desktop.py
"""

import sys
import os
import warnings
warnings.filterwarnings("ignore", category=SyntaxWarning)

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from core.webview2_checker import check_webview2_installed, ensure_webview2
from core.update_checker import check_update_on_startup, get_current_version


def check_dependencies():
    """检查运行时依赖"""
    is_installed, info = check_webview2_installed()
    if not is_installed:
        print("\n" + "=" * 60)
        print("⚠️  缺少 WebView2 运行时")
        print("=" * 60)
        print("Flet 桌面应用依赖 Microsoft Edge WebView2 运行时。")
        print("请安装 WebView2 后重新启动应用。")
        print("=" * 60 + "\n")
        ensure_webview2(show_dialog=True)
        return False
    return True


def main(page):
    """Flet应用主函数"""
    from ui.main_window import MinecraftTranslatorApp
    app = MinecraftTranslatorApp(page)


if __name__ == "__main__":
    import flet as ft
    from core.log_manager import init_logger, get_log_manager

    print("🎮 正在启动 Minecraft 基岩版汉化工具...")
    print("✨ Flet 现代化 UI 界面（桌面客户端模式）")
    print(f"📦 版本: {get_current_version()}")
    print("=" * 50)

    if not check_dependencies():
        print("❌ 缺少必要依赖，应用无法启动。")
        print("   请安装 WebView2 运行时后重试。")
        sys.exit(1)

    print("✅ 运行时依赖检查通过")
    print("=" * 50)

    init_logger()
    log_mgr = get_log_manager()
    if log_mgr:
        logger = log_mgr.get_logger(__name__)
        logger.info("应用程序启动")

    import threading
    update_thread = threading.Thread(
        target=lambda: check_update_on_startup(show_dialog=True),
        daemon=True
    )
    update_thread.start()

    if hasattr(ft, 'run'):
        ft.run(main=main)
    else:
        ft.app(target=main)
