#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flet 应用启动钩子：初始化日志、全局崩溃处理（含简短错误 ID 便于反馈）。
"""

from __future__ import annotations

import hashlib
import sys
import traceback

_hooks_installed = False


def install_app_hooks() -> None:
    """幂等安装：日志初始化 + sys.excepthook。"""
    global _hooks_installed
    if _hooks_installed:
        return

    from core.log_manager import get_log_manager, get_logger, init_logger

    init_logger()
    logger = get_logger(__name__)

    def handle_exception(exc_type, exc_value, exc_tb):
        error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        err_id = hashlib.sha256(error_msg.encode("utf-8", errors="replace")).hexdigest()[:10]
        logger.error("应用崩溃 [ERR-%s]: %s", err_id, error_msg)

        lm = get_log_manager()
        if lm:
            lm.mark_crash()

    sys.excepthook = handle_exception
    _hooks_installed = True
