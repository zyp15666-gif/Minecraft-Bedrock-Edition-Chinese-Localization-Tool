#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI协调器 - 统一管理UI组件协调和后台任务调度

从MinecraftTranslatorApp中分离出的UI协调逻辑，负责：
- 后台任务调度和状态管理
- 进度更新协调
- 按钮状态管理
- 日志显示协调
"""

import threading
from typing import Dict, Any, Optional, Callable, List
import flet as ft

from core.log_manager import get_logger

logger = get_logger(__name__)


class UICoordinator:
    """UI协调器 - 统一管理UI组件协调和后台任务调度"""

    def __init__(
        self,
        page: ft.Page,
        task_service,
        log_callback: Callable[[str], None],
        show_error: Callable[[str, str], None],
        show_success: Callable[[str, str], None],
    ):
        """
        初始化UI协调器

        Args:
            page: Flet页面对象
            task_service: 后台任务服务
            log_callback: 日志回调
            show_error: 显示错误对话框回调
            show_success: 显示成功对话框回调
        """
        self.page = page
        self.task_service = task_service
        self.log = log_callback
        self.show_error = show_error
        self.show_success = show_success

        self.progress_bar: Optional[ft.ProgressBar] = None
        self.progress_text: Optional[ft.Text] = None
        self.function_buttons: List[ft.ElevatedButton] = []
        self.log_display: Optional[ft.ListView] = None

        self._progress_lock = threading.Lock()
        self._buttons_lock = threading.Lock()

    def register_progress_controls(self, progress_bar: ft.ProgressBar, progress_text: ft.Text):
        """注册进度控件"""
        with self._progress_lock:
            self.progress_bar = progress_bar
            self.progress_text = progress_text

    def register_function_buttons(self, buttons: List[ft.ElevatedButton]):
        """注册功能按钮列表"""
        with self._buttons_lock:
            self.function_buttons = buttons

    def register_log_display(self, log_display: ft.ListView):
        """注册日志显示控件"""
        self.log_display = log_display

    def update_progress(self, value: float, text: str, remaining_count: int = 0, remaining_time: int = 0):
        """
        更新进度条和文本（线程安全）

        Args:
            value: 进度值 (0.0 - 1.0)
            text: 进度文本
            remaining_count: 剩余条目数
            remaining_time: 剩余时间（秒）
        """
        def update_ui():
            with self._progress_lock:
                if self.progress_bar:
                    self.progress_bar.value = value
                if self.progress_text:
                    progress_msg = text
                    if remaining_count > 0:
                        progress_msg += f" | 剩余: {remaining_count} 条"
                    if remaining_time > 0:
                        progress_msg += f" | 预计: {remaining_time} 秒"
                    self.progress_text.value = progress_msg
            try:
                self.page.update()
            except Exception as e:
                logger.debug(f"进度更新失败: {e}")

        self.task_service.schedule_on_main_thread(update_ui)

    def disable_all_buttons(self, disabled: bool = True):
        """
        禁用/启用所有功能按钮（线程安全）

        Args:
            disabled: True为禁用，False为启用
        """
        def update_buttons():
            with self._buttons_lock:
                for btn in self.function_buttons:
                    btn.disabled = disabled
            try:
                self.page.update()
            except Exception as e:
                logger.debug(f"按钮状态更新失败: {e}")

        self.task_service.schedule_on_main_thread(update_buttons)

    def enable_all_buttons(self):
        """启用所有功能按钮"""
        self.disable_all_buttons(disabled=False)

    def add_log_entry(self, message: str):
        """
        添加日志条目到日志显示控件

        Args:
            message: 日志消息
        """
        def add_entry():
            if self.log_display:
                from datetime import datetime
                timestamp = datetime.now().strftime("%H:%M:%S")
                self.log_display.controls.append(
                    ft.Text(f"[{timestamp}] {message}", size=12)
                )
                if len(self.log_display.controls) > 100:
                    self.log_display.controls.pop(0)
            try:
                self.page.update()
            except Exception as e:
                logger.debug(f"日志显示更新失败: {e}")

        self.task_service.schedule_on_main_thread(add_entry)

    def clear_log_display(self):
        """清空日志显示"""
        def clear():
            if self.log_display:
                self.log_display.controls.clear()
                self.log_display.controls.append(
                    ft.Text("📝 暂无日志记录", color=ft.Colors.GREY, italic=True)
                )
            try:
                self.page.update()
            except Exception as e:
                logger.debug(f"日志清空失败: {e}")

        self.task_service.schedule_on_main_thread(clear)

    def show_snack_bar(self, message: str, action: str = None, on_action: Callable = None):
        """
        显示SnackBar通知

        Args:
            message: 消息内容
            action: 操作按钮文本（可选）
            on_action: 操作按钮回调（可选）
        """
        def show():
            snack = ft.SnackBar(
                content=ft.Text(message),
                action=action,
                on_action=lambda e: on_action() if on_action else None,
                duration=3000,
            )
            self.page.snack_bar = snack
            snack.open = True
            self.page.update()

        self.task_service.schedule_on_main_thread(show)

    def run_background_task(
        self,
        task_func: Callable,
        on_progress: Optional[Callable[[float, int, int], None]] = None,
        on_log: Optional[Callable[[str], None]] = None,
        on_result: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
    ):
        """
        运行后台任务（统一调度）

        Args:
            task_func: 任务函数
            on_progress: 进度回调
            on_log: 日志回调
            on_result: 结果回调
            on_error: 错误回调
        """
        self.disable_all_buttons()

        def wrapped_task():
            try:
                result = task_func()
                if on_result:
                    self.task_service.schedule_on_main_thread(
                        lambda: on_result(result)
                    )
            except Exception as e:
                logger.error(f"后台任务执行失败: {e}")
                if on_error:
                    self.task_service.schedule_on_main_thread(
                        lambda: on_error(e)
                    )
            finally:
                self.task_service.schedule_on_main_thread(
                    self.enable_all_buttons
                )

        self.task_service.run(wrapped_task)

    def run_feature_task(
        self,
        feature_name: str,
        task_func: Callable,
        success_message: str = "操作完成",
        error_message: str = "操作失败",
    ):
        """
        运行功能任务（简化版，自动处理进度和结果）

        Args:
            feature_name: 功能名称
            task_func: 任务函数
            success_message: 成功消息
            error_message: 失败消息
        """
        self.log(f"🚀 开始{feature_name}...")
        self.update_progress(0, f"{feature_name}中...", 0, 0)

        def on_result(result: Dict[str, Any]):
            if result.get('success'):
                self.update_progress(1.0, "完成", 0, 0)
                self.show_success(feature_name, result.get('message', success_message))
                self.log(f"✅ {result.get('message', success_message)}")
            else:
                self.show_error(feature_name, result.get('message', error_message))
                self.log(f"❌ {result.get('message', error_message)}")

        def on_error(error: Exception):
            self.show_error(feature_name, str(error))
            self.log(f"❌ {feature_name}失败: {error}")

        self.run_background_task(
            task_func=task_func,
            on_result=on_result,
            on_error=on_error,
        )
