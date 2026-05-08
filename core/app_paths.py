#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应用数据路径（单一来源）

打包与多个模块此前各自拼接「文档目录 / Minecraft基岩版汉化工具」，此处统一，
避免遗漏「My Documents」或路径不一致。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_FOLDER_NAME = "Minecraft基岩版汉化工具"


def get_documents_base() -> Path:
    """当前用户下可用的 Documents 目录（兼容 My Documents）。"""
    user_profile = os.environ.get("USERPROFILE", os.path.expanduser("~"))
    candidates = (
        Path(user_profile) / "Documents",
        Path(user_profile) / "My Documents",
    )
    for path in candidates:
        if path.is_dir():
            return path
    return Path(os.path.expanduser("~")) / "Documents"


def get_documents_app_dir() -> Path:
    """用户文档下的应用目录 Documents/<APP_FOLDER_NAME>（日志、打包后的配置等）。"""
    p = get_documents_base() / APP_FOLDER_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_project_root() -> Path:
    """开发时项目根目录（core 的上一级）。"""
    return Path(__file__).resolve().parent.parent


def get_secure_storage_path() -> Path:
    """安全存储文件路径（.secure_storage）。开发环境在项目根，打包后在文档应用目录。"""
    if getattr(sys, "frozen", False):
        base = get_documents_app_dir()
    else:
        base = get_project_root()
    base.mkdir(parents=True, exist_ok=True)
    return base / ".secure_storage"


def get_update_check_state_path() -> Path:
    """更新检查状态文件 .update_check。开发环境在项目根，打包后在文档应用目录。"""
    if getattr(sys, "frozen", False):
        base = get_documents_app_dir()
    else:
        base = get_project_root()
    base.mkdir(parents=True, exist_ok=True)
    return base / ".update_check"
