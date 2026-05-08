"""
启动 Minecraft 基岩版汉化工具 - Flet 桌面客户端模式
使用桌面客户端，可以完全控制窗口大小和位置

使用方式：
    python run_flet_desktop.py
"""

import os
import sys
import warnings

warnings.filterwarnings("ignore", category=SyntaxWarning)

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from core.update_checker import check_update_on_startup, get_current_version
from core.webview2_checker import check_webview2_installed, ensure_webview2


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
    """Flet 入口：委托给 main_window.main（含 on_close 清理）。"""
    from ui.main_window import main as run_app
    run_app(page)


if __name__ == "__main__":
    import flet as ft

    from config.config_manager import ConfigManager

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

    import ui.main_window  # noqa: F401 — 安装日志与全局 excepthook
    from core.log_manager import get_log_manager

    log_mgr = get_log_manager()
    if log_mgr:
        log_mgr.get_logger(__name__).info("应用程序启动")

    try:
        config_manager = ConfigManager()
        config = config_manager.load_config()
    except Exception as e:
        print(f"⚠️  加载配置失败: {e}")
        config = None

    import threading
    update_thread = threading.Thread(
        target=lambda: check_update_on_startup(show_dialog=True, config=config),
        daemon=True
    )
    update_thread.start()

    if hasattr(ft, 'run'):
        ft.run(main=main)
    else:
        ft.app(target=main)
