#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebView2 运行时检测模块

Flet 桌面应用依赖 Microsoft Edge WebView2 运行时。
此模块在应用启动时检测 WebView2 是否已安装，并提供引导安装功能。

Windows 10 1909+ / Windows 11 通常已预装 WebView2。
但 LTSC/LTSB 版本、企业定制镜像可能缺失。
"""

import os
import sys
import subprocess
import logging
import webbrowser
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

_IS_WINDOWS = sys.platform == 'win32'

WEBVIEW2_BOOTSTRAPPER_URL = "https://go.microsoft.com/fwlink/p/?LinkId=2124703"
WEBVIEW2_OFFLINE_URL = "https://developer.microsoft.com/en-us/microsoft-edge/webview2/"

WEBVIEW2_REGISTRY_PATHS = [
    r"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}",
    r"SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}",
]

WEBVIEW2_DLL_PATHS = [
    Path(os.environ.get('ProgramFiles(x86)', '')) / 'Microsoft' / 'EdgeWebView' / 'Application' / 'msedge_webview2.dll',
    Path(os.environ.get('ProgramFiles', '')) / 'Microsoft' / 'EdgeWebView' / 'Application' / 'msedge_webview2.dll',
    Path(os.environ.get('ProgramFiles(x86)', '')) / 'Microsoft' / 'Edge' / 'Application' / 'msedge_webview2.dll',
]


class WebView2Status:
    """WebView2 状态"""
    NOT_CHECKED = "not_checked"
    INSTALLED = "installed"
    NOT_INSTALLED = "not_installed"
    CHECK_FAILED = "check_failed"


def check_webview2_installed() -> Tuple[bool, Optional[str]]:
    """检查 WebView2 运行时是否已安装

    Returns:
        (is_installed, version_or_error)
        - is_installed: True 表示已安装
        - version_or_error: 版本号或错误信息
    """
    if not _IS_WINDOWS:
        return True, "非 Windows 平台，跳过 WebView2 检测"

    version = _check_registry()
    if version:
        logger.info(f"WebView2 运行时已安装 (注册表检测): {version}")
        return True, version

    dll_path = _check_dll_exists()
    if dll_path:
        logger.info(f"WebView2 DLL 已找到: {dll_path}")
        return True, "DLL 存在"

    version = _check_via_powershell()
    if version:
        logger.info(f"WebView2 运行时已安装 (PowerShell 检测): {version}")
        return True, version

    logger.warning("WebView2 运行时未检测到")
    return False, "WebView2 运行时未安装"


def _check_registry() -> Optional[str]:
    """通过注册表检查 WebView2 版本"""
    if not _IS_WINDOWS:
        return None

    try:
        import winreg
        for reg_path in WEBVIEW2_REGISTRY_PATHS:
            try:
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path)
                version, _ = winreg.QueryValueEx(key, "pv")
                winreg.CloseKey(key)
                if version:
                    return str(version)
            except (FileNotFoundError, PermissionError, OSError):
                continue
    except ImportError:
        pass

    return None


def _check_dll_exists() -> Optional[str]:
    """检查 WebView2 DLL 文件是否存在"""
    for dll_path in WEBVIEW2_DLL_PATHS:
        if dll_path.exists():
            return str(dll_path)
    return None


def _check_via_powershell() -> Optional[str]:
    """通过 PowerShell 检查 WebView2"""
    if not _IS_WINDOWS:
        return None

    try:
        cmd = [
            'powershell', '-Command',
            'Get-ItemProperty -Path "HKLM:\\SOFTWARE\\WOW6432Node\\Microsoft\\EdgeUpdate\\Clients\\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}" -Name "pv" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty "pv"'
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception as e:
        logger.debug(f"PowerShell 检测 WebView2 失败: {e}")

    return None


def get_webview2_download_url(offline: bool = False) -> str:
    """获取 WebView2 下载链接

    Args:
        offline: 是否获取离线安装包链接

    Returns:
        下载链接
    """
    if offline:
        return WEBVIEW2_OFFLINE_URL
    return WEBVIEW2_BOOTSTRAPPER_URL


def open_webview2_download_page():
    """打开 WebView2 下载页面"""
    url = get_webview2_download_url()
    try:
        webbrowser.open(url)
        logger.info(f"已打开 WebView2 下载页面: {url}")
    except Exception as e:
        logger.error(f"打开下载页面失败: {e}")


def ensure_webview2(show_dialog: bool = True) -> bool:
    """确保 WebView2 已安装，未安装时提示用户

    Args:
        show_dialog: 是否显示对话框提示用户安装

    Returns:
        True 表示 WebView2 可用，False 表示不可用
    """
    is_installed, info = check_webview2_installed()

    if is_installed:
        return True

    if not show_dialog:
        return False

    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)

        message = (
            "此应用需要 Microsoft Edge WebView2 运行时才能运行。\n\n"
            "点击\"确定\"打开下载页面，安装完成后重新启动应用。\n\n"
            "如果您的网络环境受限，可以搜索\"WebView2 离线安装包\"下载完整安装程序。"
        )

        result = messagebox.showwarning(
            "缺少 WebView2 运行时",
            message,
            type=messagebox.OKCANCEL
        )

        root.destroy()

        if result == messagebox.OK:
            open_webview2_download_page()

    except ImportError:
        print("\n" + "=" * 60)
        print("错误：缺少 Microsoft Edge WebView2 运行时")
        print("=" * 60)
        print(f"请访问以下链接下载并安装：")
        print(get_webview2_download_url())
        print("=" * 60 + "\n")

    return False


def check_and_exit_if_missing():
    """检查 WebView2，如果缺失则退出程序"""
    is_installed, info = check_webview2_installed()

    if not is_installed:
        logger.critical("WebView2 运行时未安装，应用无法启动")
        ensure_webview2(show_dialog=True)
        sys.exit(1)

    return True


if __name__ == "__main__":
    is_installed, version = check_webview2_installed()
    if is_installed:
        print(f"✅ WebView2 已安装: {version}")
    else:
        print(f"❌ WebView2 未安装: {version}")
        print(f"下载链接: {get_webview2_download_url()}")
