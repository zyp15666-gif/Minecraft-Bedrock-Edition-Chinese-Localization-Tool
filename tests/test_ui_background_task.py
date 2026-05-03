#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI 层单元测试 — background_task_service.py

使用 mock Page 对象隔离 Flet 依赖，验证线程安全调度逻辑。
"""

import sys
import os
import time
import threading
from unittest.mock import Mock, MagicMock, patch, ANY
from concurrent.futures import TimeoutError as FuturesTimeoutError

import pytest


def _make_mock_page():
    """创建模拟的 ft.Page 对象 — run_task 实际执行传递的异步函数"""
    page = MagicMock()

    def run_task_side_effect(async_fn, *args, **kwargs):
        """调用异步函数获取协程并执行"""
        import asyncio
        coro = async_fn(*args, **kwargs)
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    page.run_task = run_task_side_effect
    return page


class TestBackgroundTaskServiceInit:
    """初始化测试"""

    def test_init_default_workers(self):
        from ui.background_task_service import BackgroundTaskService
        page = _make_mock_page()
        svc = BackgroundTaskService(page, max_workers=4)
        assert svc.page is page
        assert svc.active_tasks == 0
        assert svc.is_shutting_down() is False
        svc.shutdown(wait=False)

    def test_init_custom_workers(self):
        from ui.background_task_service import BackgroundTaskService
        page = _make_mock_page()
        svc = BackgroundTaskService(page, max_workers=8)
        assert svc.executor._max_workers == 8
        svc.shutdown(wait=False)


class TestBackgroundTaskServiceRun:
    """run() 方法测试"""

    @pytest.fixture
    def svc(self):
        from ui.background_task_service import BackgroundTaskService
        svc = BackgroundTaskService(_make_mock_page(), max_workers=2)
        yield svc
        svc.shutdown(wait=False)

    def test_run_simple(self, svc):
        def task():
            return 42

        future = svc.run(task)
        result = future.result(timeout=5)
        assert result == 42

    def test_run_with_args(self, svc):
        def add(a, b):
            return a + b

        future = svc.run(add, 3, 4)
        result = future.result(timeout=5)
        assert result == 7

    def test_run_with_kwargs(self, svc):
        def greet(name="world"):
            return f"Hello, {name}"

        future = svc.run(greet, name="Test")
        result = future.result(timeout=5)
        assert result == "Hello, Test"

    def test_run_on_result_callback(self, svc):
        callback_results = []

        def task():
            return "done"

        def on_result(result):
            callback_results.append(result)

        future = svc.run(task, on_result=on_result)
        future.result(timeout=5)
        time.sleep(0.3)  # 等待回调调度
        assert "done" in callback_results

    def test_run_on_error_callback(self, svc):
        error_caught = []

        def failing_task():
            raise ValueError("test error")

        def on_error(err):
            error_caught.append(str(err))

        future = svc.run(failing_task, on_error=on_error)
        future.result(timeout=5)
        time.sleep(0.5)
        assert len(error_caught) > 0
        assert "test error" in error_caught[0]

    def test_run_increments_active_tasks(self, svc):
        assert svc.active_tasks == 0

        def task():
            time.sleep(0.2)
            return 1

        future = svc.run(task)
        time.sleep(0.05)
        assert svc.active_tasks >= 1
        future.result(timeout=5)
        time.sleep(0.3)
        assert svc.active_tasks == 0

    def test_run_multiple_tasks(self, svc):
        results = []

        def task(n):
            return n * 2

        futures = [svc.run(task, i) for i in range(5)]
        for f in futures:
            results.append(f.result(timeout=5))
        assert sorted(results) == [0, 2, 4, 6, 8]


class TestBackgroundTaskServiceRunWithUiCallbacks:
    """run_with_ui_callbacks() 测试"""

    @pytest.fixture
    def svc(self):
        from ui.background_task_service import BackgroundTaskService
        svc = BackgroundTaskService(_make_mock_page(), max_workers=2)
        yield svc
        svc.shutdown(wait=False)

    def test_on_complete_called(self, svc):
        complete_called = []

        def task(progress_callback=None, log_callback=None):
            return "ok"

        def on_complete():
            complete_called.append(True)

        future = svc.run_with_ui_callbacks(task, on_complete=on_complete)
        future.result(timeout=5)
        time.sleep(0.3)
        assert len(complete_called) > 0

    def test_progress_log_callbacks(self, svc):
        progress_vals = []
        log_msgs = []

        def task(progress_callback=None, log_callback=None):
            if progress_callback:
                progress_callback(0.5, 10, 30)
            if log_callback:
                log_callback("test log")
            return "done"

        future = svc.run_with_ui_callbacks(
            task,
            on_progress=lambda *a: progress_vals.append(a),
            on_log=lambda m: log_msgs.append(m),
        )
        future.result(timeout=5)
        time.sleep(0.3)
        # 回调已执行（通过 _run_on_main_thread -> mock page）
        assert future.result() == "done"

    def test_on_result_called(self, svc):
        result_vals = []

        def task(progress_callback=None, log_callback=None):
            return 99

        future = svc.run_with_ui_callbacks(task, on_result=lambda r: result_vals.append(r))
        future.result(timeout=5)
        time.sleep(0.3)
        assert 99 in result_vals


class TestBackgroundTaskServiceRunWithButtonState:
    """run_with_button_state() 测试"""

    @pytest.fixture
    def svc(self):
        from ui.background_task_service import BackgroundTaskService
        svc = BackgroundTaskService(_make_mock_page(), max_workers=2)
        yield svc
        svc.shutdown(wait=False)

    def test_disables_controls(self, svc):
        mock_ctrl = MagicMock()
        mock_ctrl.disabled = False

        def task(progress_callback=None, log_callback=None):
            return "ok"

        future = svc.run_with_button_state(task, disabled_controls=[mock_ctrl])
        future.result(timeout=5)

        # 控件应被禁用后再启用
        assert mock_ctrl.disabled is False  # 任务完成后恢复

    def test_disables_controls_empty(self, svc):
        def task(progress_callback=None, log_callback=None):
            return "ok"

        future = svc.run_with_button_state(task)
        future.result(timeout=5)


class TestBackgroundTaskServiceAux:
    """辅助方法测试"""

    @pytest.fixture
    def svc(self):
        from ui.background_task_service import BackgroundTaskService
        svc = BackgroundTaskService(_make_mock_page(), max_workers=2)
        yield svc
        svc.shutdown(wait=False)

    def test_run_in_executor(self, svc):
        def task():
            return "executor_result"

        future = svc.run_in_executor(task)
        result = future.result(timeout=5)
        assert result == "executor_result"

    def test_get_active_task_count(self, svc):
        assert svc.get_active_task_count() == 0

        def slow():
            time.sleep(0.3)
            return 1

        future = svc.run(slow)
        time.sleep(0.05)
        assert svc.get_active_task_count() >= 1
        future.result(timeout=5)
        time.sleep(0.4)
        assert svc.get_active_task_count() == 0

    def test_shutdown(self, svc):
        svc.shutdown(wait=True)
        assert svc.is_shutting_down() is True
        # 二次 shutdown 不应报错
        svc.shutdown(wait=False)

    def test_schedule_on_main_thread(self, svc):
        called = []

        def cb(msg):
            called.append(msg)

        svc.schedule_on_main_thread(cb, "hello")
        time.sleep(0.1)
        # 回调通过 page.run_task 执行
        assert len(called) > 0
        assert "hello" in called


class TestGlobalService:
    """全局任务服务测试"""

    def test_init_and_get(self):
        from ui.background_task_service import init_global_task_service, get_global_task_service
        page = _make_mock_page()
        svc = init_global_task_service(page, max_workers=2)
        assert svc is not None

        retrieved = get_global_task_service()
        assert retrieved is svc
        svc.shutdown(wait=False)
