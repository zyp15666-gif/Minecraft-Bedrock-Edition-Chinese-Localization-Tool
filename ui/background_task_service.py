#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
后台任务服务 - 提供线程安全的任务调度

统一管理所有后台任务，确保UI更新都通过主线程执行，
消除后台线程直接操作UI的风险。
"""

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Callable, Any, Optional

import flet as ft

from core.log_manager import get_logger

logger = get_logger(__name__)


class BackgroundTaskService:
    """后台任务服务 - 线程安全的任务调度器"""

    def __init__(self, page: ft.Page, max_workers: int = 4):
        """初始化后台任务服务
        
        Args:
            page: Flet Page实例，用于UI线程调度
            max_workers: 最大工作线程数
        """
        self.page = page
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.lock = threading.Lock()
        self.active_tasks = 0
        self._shutdown_event = threading.Event()
        
        logger.info(f"后台任务服务已初始化，最大线程数: {max_workers}")

    def run(self, fn: Callable, *args,
            on_result: Optional[Callable[[Any], None]] = None,
            on_error: Optional[Callable[[Exception], None]] = None,
            timeout: Optional[float] = None,
            **kwargs) -> Future:
        """安全执行后台任务，通过 page.run_task 返回结果

        Args:
            fn: 要执行的后台函数
            *args: 函数参数
            on_result: 成功回调（在主线程执行）
            on_error: 错误回调（在主线程执行）
            timeout: 任务超时时间（秒），None表示不限制
            **kwargs: 关键字参数

        Returns:
            Future对象，可用于取消任务或获取结果
        """
        task_id = id(threading.current_thread())
        timeout_flag = threading.Event()
        result_holder = [None]
        error_holder = [None]

        def wrapper():
            try:
                logger.debug(f"任务 {task_id} 开始执行")
                result = fn(*args, **kwargs)
                result_holder[0] = ('result', result)
                if timeout_flag.is_set():
                    return None
                if on_result:
                    self._run_on_main_thread(on_result, result)
                logger.debug(f"任务 {task_id} 执行完成")
                return result
            except Exception as e:
                error_holder[0] = ('error', e)
                if timeout_flag.is_set():
                    return None
                logger.error(f"任务 {task_id} 执行失败: {e}", exc_info=True)
                if on_error:
                    self._run_on_main_thread(on_error, e)
                return None
            finally:
                with self.lock:
                    self.active_tasks -= 1

        with self.lock:
            self.active_tasks += 1

        future = self.executor.submit(wrapper)

        if timeout is not None:
            def timeout_watcher():
                timeout_flag.set()
                with self.lock:
                    self.active_tasks -= 1
                error_msg = f"任务执行超时: {timeout}秒"
                logger.error(error_msg)
                timeout_error = TimeoutError(error_msg)
                error_holder[0] = ('error', timeout_error)
                if on_error:
                    self._run_on_main_thread(
                        lambda: getattr(self.page, 'show_error_dialog', print)(
                            "任务执行超时", f"任务执行时间超过 {timeout} 秒"))
                try:
                    future.result(0)
                except Exception:
                    pass

            timeout_thread = threading.Timer(timeout, timeout_watcher)
            timeout_thread.daemon = True
            timeout_thread.start()

        return future

    def run_with_button_state(
        self, fn: Callable,
        *args,
        disabled_controls: Optional[list] = None,
        on_result: Optional[Callable[[Any], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
        **kwargs,
    ) -> Future:
        """执行后台任务，自动管理控件禁用/启用状态

        Args:
            fn: 后台函数
            disabled_controls: 任务期间需禁用的 Flet 控件列表
            on_result: 成功回调（主线程执行）
            on_error: 错误回调（主线程执行，按异常类型自动分类提示）
        """
        if disabled_controls is None:
            disabled_controls = []

        def _disable():
            for ctrl in disabled_controls:
                try:
                    ctrl.disabled = True
                except Exception as e:
                    logger.debug(f"禁用控件失败: {e}")
            if hasattr(self, 'page') and self.page:
                self.page.update()

        def _enable():
            for ctrl in disabled_controls:
                try:
                    ctrl.disabled = False
                except Exception as e:
                    logger.debug(f"启用控件失败: {e}")
            if hasattr(self, 'page') and self.page:
                self.page.update()

        def _on_error(err: Exception):
            _enable()
            if on_error:
                on_error(err)
            else:
                try:
                    from core.exceptions import (
                        APIAuthError, APITimeoutError, APIConnectionError,
                        APIRateLimitError, AllAPIsExhaustedError,
                    )
                    if isinstance(err, APIAuthError):
                        self._run_on_main_thread(
                            lambda: getattr(self.page, 'show_error_dialog', print)("API认证失败", str(err)))
                    elif isinstance(err, (APITimeoutError, APIConnectionError)):
                        self._run_on_main_thread(
                            lambda: getattr(self.page, 'show_error_dialog', print)("网络错误", str(err)))
                    elif isinstance(err, APIRateLimitError):
                        self._run_on_main_thread(
                            lambda: getattr(self.page, 'show_error_dialog', print)("请求过于频繁", str(err)))
                    else:
                        self._run_on_main_thread(
                            lambda: getattr(self.page, 'show_error_dialog', print)("操作失败", str(err)))
                except ImportError:
                    pass

        def _on_complete():
            _enable()

        _disable()
        return self.run_with_ui_callbacks(
            fn, *args,
            on_result=on_result,
            on_error=_on_error,
            on_complete=_on_complete,
            **kwargs,
        )
    
    def run_with_ui_callbacks(self, fn: Callable, 
                              *args,
                              on_progress: Optional[Callable[..., None]] = None,
                              on_log: Optional[Callable[[str], None]] = None,
                              on_result: Optional[Callable[[Any], None]] = None,
                              on_error: Optional[Callable[[Exception], None]] = None,
                              on_complete: Optional[Callable[[], None]] = None,
                              **kwargs) -> Future:
        """执行后台任务，提供完整的UI回调支持
        
        Args:
            fn: 要执行的后台函数
            *args: 函数参数
            on_progress: 进度回调 (value, text, remaining_count, remaining_time)
            on_log: 日志回调 (message)
            on_result: 成功回调 (result)
            on_error: 错误回调 (exception)
            on_complete: 完成回调（无论成功失败都会调用）
            **kwargs: 关键字参数
            
        Returns:
            Future对象
        """
        def wrapper():
            task_id = id(threading.current_thread())
            try:
                logger.debug(f"任务 {task_id} 开始执行")
                
                # 创建包装后的回调函数
                wrapped_progress = None
                wrapped_log = None
                
                if on_progress:
                    def wrapped_progress(*progress_args):
                        self._run_on_main_thread(on_progress, *progress_args)
                
                if on_log:
                    def wrapped_log(msg):
                        self._run_on_main_thread(on_log, msg)
                
                # 传递包装后的回调给任务函数
                result = fn(*args, 
                            progress_callback=wrapped_progress,
                            log_callback=wrapped_log,
                            **kwargs)
                
                if on_result:
                    self._run_on_main_thread(on_result, result)
                    
                logger.debug(f"任务 {task_id} 执行完成")
                return result
                
            except Exception as e:
                logger.error(f"任务 {task_id} 执行失败: {e}", exc_info=True)
                
                if on_error:
                    self._run_on_main_thread(on_error, e)
                
                raise
            finally:
                if on_complete:
                    self._run_on_main_thread(on_complete)
                with self.lock:
                    self.active_tasks -= 1

        with self.lock:
            self.active_tasks += 1
        
        future = self.executor.submit(wrapper)
        return future

    def _run_on_main_thread(self, callback: Callable, *args) -> None:
        """在主线程上执行回调函数

        page.run_task() 自身已处理跨线程调度，无需包裹 asyncio.run_coroutine_threadsafe。
        """
        async def _runner():
            try:
                callback(*args)
            except Exception as e:
                logger.error(f"回调执行失败: {e}", exc_info=True)

        try:
            self.page.run_task(_runner)
        except Exception as e:
            logger.error(f"调度到主线程失败: {e}", exc_info=True)

    def run_in_executor(self, fn: Callable, *args, **kwargs) -> Future:
        """直接在执行器中运行任务（无回调）
        
        Args:
            fn: 要执行的函数
            *args: 函数参数
            **kwargs: 关键字参数
            
        Returns:
            Future对象
        """
        def wrapper():
            with self.lock:
                self.active_tasks += 1
            try:
                return fn(*args, **kwargs)
            finally:
                with self.lock:
                    self.active_tasks -= 1
        
        return self.executor.submit(wrapper)

    def schedule_on_main_thread(self, callback: Callable, *args) -> None:
        """在主线程上调度执行（同步）
        
        Args:
            callback: 要执行的回调函数
            *args: 回调函数参数
        """
        self._run_on_main_thread(callback, *args)

    def get_active_task_count(self) -> int:
        """获取当前活跃任务数
        
        Returns:
            活跃任务数量
        """
        with self.lock:
            return self.active_tasks

    def shutdown(self, wait: bool = True) -> None:
        """关闭任务服务
        
        Args:
            wait: 是否等待所有任务完成
        """
        self._shutdown_event.set()
        self.executor.shutdown(wait=wait)
        logger.info("后台任务服务已关闭")

    def is_shutting_down(self) -> bool:
        """检查服务是否正在关闭
        
        Returns:
            True如果正在关闭
        """
        return self._shutdown_event.is_set()


class SafeUIAccess:
    """UI安全访问装饰器/上下文管理器"""
    
    def __init__(self, page: ft.Page):
        self.page = page
        
    def __call__(self, func: Callable) -> Callable:
        """装饰器模式，确保函数在主线程执行"""
        def wrapper(*args, **kwargs):
            if threading.current_thread() is threading.main_thread():
                return func(*args, **kwargs)

            async def run_on_main():
                return func(*args, **kwargs)

            future = asyncio.run_coroutine_threadsafe(
                run_on_main(),
                self.page.loop
            )
            return future.result()

        return wrapper


# 全局任务服务实例（用于简单场景）
_global_task_service = None


def init_global_task_service(page: ft.Page, max_workers: int = 4) -> BackgroundTaskService:
    """初始化全局任务服务
    
    Args:
        page: Flet Page实例
        max_workers: 最大工作线程数
        
    Returns:
        全局任务服务实例
    """
    global _global_task_service
    _global_task_service = BackgroundTaskService(page, max_workers)
    return _global_task_service


def get_global_task_service() -> Optional[BackgroundTaskService]:
    """获取全局任务服务
    
    Returns:
        全局任务服务实例，如果未初始化返回None
    """
    return _global_task_service
