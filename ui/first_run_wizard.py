#!/usr/bin/env python3
import os
import platform
import sys

import flet as ft

from core.log_manager import get_logger

logger = get_logger(__name__)


class FirstRunWizard:
    """首次运行环境汇总页

    在应用首次启动时展示环境检测结果，
    帮助用户确认系统依赖是否就绪。
    """

    FIRST_RUN_FLAG_FILE = ".first_run_completed"

    def __init__(self, page: ft.Page, config: dict, on_continue=None):
        self.page = page
        self.config = config
        self.on_continue = on_continue
        self._flag_path = self._get_flag_path()

    def _get_flag_path(self) -> str:
        try:
            from core.app_paths import get_documents_app_dir
            app_dir = get_documents_app_dir()
        except Exception:
            app_dir = os.path.join(os.path.expanduser("~"), "Documents", "Minecraft基岩版汉化工具")
        os.makedirs(app_dir, exist_ok=True)
        return os.path.join(app_dir, self.FIRST_RUN_FLAG_FILE)

    def is_first_run(self) -> bool:
        return not os.path.exists(self._flag_path)

    def mark_completed(self):
        try:
            with open(self._flag_path, "w", encoding="utf-8") as f:
                f.write(platform.node())
        except Exception as e:
            logger.debug(f"无法写入首次运行标记: {e}")

    def _check_webview2(self) -> tuple:
        try:
            from core.webview2_checker import check_webview2_installed
            installed, info = check_webview2_installed()
            return installed, info or ""
        except Exception as e:
            return False, str(e)

    def _check_python_version(self) -> tuple:
        version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        ok = sys.version_info >= (3, 9)
        return ok, version

    def _check_config(self) -> tuple:
        try:
            has_apis = bool(self.config.get("apis") or self.config.get("deepseek") or self.config.get("local_ollama"))
            return has_apis, "已配置API" if has_apis else "未配置API"
        except Exception:
            return False, "配置读取失败"

    def _check_os(self) -> tuple:
        return True, f"{platform.system()} {platform.release()} ({platform.machine()})"

    def build_status_row(self, label: str, ok: bool, detail: str) -> ft.Row:
        icon = ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN, size=20) if ok else ft.Icon(ft.Icons.WARNING, color=ft.Colors.ORANGE, size=20)
        return ft.Row(
            controls=[
                icon,
                ft.Text(label, width=160, size=14, weight=ft.FontWeight.W_500),
                ft.Text(detail, size=13, color=ft.Colors.GREY_700, expand=True),
            ],
            alignment=ft.MainAxisAlignment.START,
        )

    def show(self):
        webview2_ok, webview2_info = self._check_webview2()
        python_ok, python_info = self._check_python_version()
        config_ok, config_info = self._check_config()
        os_ok, os_info = self._check_os()

        all_ok = webview2_ok and python_ok

        status_rows = [
            self.build_status_row("操作系统", os_ok, os_info),
            self.build_status_row("Python 版本", python_ok, python_info),
            self.build_status_row("WebView2 运行时", webview2_ok, webview2_info or "未安装"),
            self.build_status_row("API 配置", config_ok, config_info),
        ]

        def on_continue_click(e):
            self.mark_completed()
            self.page.close_dialog()
            if self.on_continue:
                self.on_continue()

        def on_download_webview2(e):
            try:
                from core.webview2_checker import open_webview2_download_page
                open_webview2_download_page()
            except Exception:
                import webbrowser
                webbrowser.open("https://go.microsoft.com/fwlink/p/?LinkId=2124703")

        action_controls = []
        if not webview2_ok:
            action_controls.append(
                ft.Button(
                    "下载 WebView2 运行时",
                    icon=ft.Icons.DOWNLOAD,
                    on_click=on_download_webview2,
                    style=ft.ButtonStyle(
                        bgcolor={"": ft.Colors.BLUE_400},
                        color={"": ft.Colors.WHITE},
                    ),
                )
            )

        action_controls.append(
            ft.Button(
                "继续使用" if all_ok else "仍然继续",
                icon=ft.Icons.ARROW_FORWARD,
                on_click=on_continue_click,
                style=ft.ButtonStyle(
                    bgcolor={"": ft.Colors.GREEN if all_ok else ft.Colors.ORANGE},
                    color={"": ft.Colors.WHITE},
                ),
            )
        )

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.FACT_CHECK, size=28, color=ft.Colors.BLUE_400),
                    ft.Text("环境检测", size=22, weight=ft.FontWeight.BOLD),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(
                            "首次运行 — 系统环境检测结果如下：",
                            size=14,
                            color=ft.Colors.GREY_700,
                        ),
                        ft.Divider(height=8),
                        *status_rows,
                        ft.Divider(height=8),
                        ft.Text(
                            "提示：缺少 WebView2 时应用可能无法正常显示界面。"
                            if not webview2_ok else
                            "所有关键依赖已就绪，可以开始使用！",
                            size=12,
                            color=ft.Colors.GREY_500,
                            italic=True,
                        ),
                    ],
                    spacing=8,
                    width=460,
                ),
                padding=10,
            ),
            actions=action_controls,
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self.page.show_dialog(dialog)
