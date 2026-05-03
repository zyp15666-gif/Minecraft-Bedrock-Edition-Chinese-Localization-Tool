#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UseCase基类模块 - 提供统一的用例执行框架

建议所有UseCase类继承此基类，以获得：
- 统一的进度回调包装
- 统一的日志回调包装
- 统一的异常处理
- 统一的返回结果格式
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import traceback


@dataclass
class UseCaseResult:
    """统一用例执行结果"""
    success: bool
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    error: str = ""
    traceback_str: str = ""
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'message': self.message,
            'data': self.data,
            'error': self.error,
            'duration_ms': self.duration_ms
        }


class BaseUseCase(ABC):
    """UseCase基类 - 提供统一的执行框架

    建议所有UseCase类继承此基类。
    现有UseCase可直接继承以获得统一的功能，也可在后续迭代中逐步重构。
    """

    def __init__(self, name: str = None):
        """
        初始化UseCase

        Args:
            name: 用例名称，用于日志和统计
        """
        self.name = name or self.__class__.__name__
        self._execution_count = 0

    def execute(
        self,
        progress_callback: Optional[Callable] = None,
        log_callback: Optional[Callable[[str], None]] = None,
        **kwargs
    ) -> UseCaseResult:
        """
        统一的用例执行入口

        Args:
            progress_callback: 进度回调 (progress: float, remaining: int, time: int)
            log_callback: 日志回调
            **kwargs: 子类特定参数

        Returns:
            UseCaseResult: 统一的执行结果
        """
        self._execution_count += 1
        start_time = datetime.now()

        wrapped_progress = self._wrap_progress(progress_callback)
        wrapped_log = self._wrap_log(log_callback)

        try:
            result = self._execute_impl(wrapped_progress, wrapped_log, **kwargs)

            end_time = datetime.now()
            duration_ms = (end_time - start_time).total_seconds() * 1000

            return UseCaseResult(
                success=True,
                message=result.get('message', '执行成功'),
                data=result.get('data', {}),
                start_time=start_time,
                end_time=end_time,
                duration_ms=duration_ms
            )

        except Exception as e:
            end_time = datetime.now()
            duration_ms = (end_time - start_time).total_seconds() * 1000
            error_trace = traceback.format_exc()

            wrapped_log(f"执行失败: {str(e)}")

            return UseCaseResult(
                success=False,
                message=str(e),
                error=str(e),
                traceback_str=error_trace,
                start_time=start_time,
                end_time=end_time,
                duration_ms=duration_ms
            )

    @abstractmethod
    def _execute_impl(
        self,
        progress_callback: Optional[Callable],
        log_callback: Optional[Callable[[str], None]],
        **kwargs
    ) -> Dict[str, Any]:
        """
        子类实现的具体业务逻辑

        Args:
            progress_callback: 进度回调
            log_callback: 日志回调
            **kwargs: 子类特定参数

        Returns:
            Dict包含:
                - message: 执行消息
                - data: 执行数据
        """
        pass

    def _wrap_progress(self, callback: Optional[Callable]) -> Optional[Callable]:
        """包装进度回调"""
        if callback is None:
            return None

        def wrapped(value: float, remaining: int = 0, time_est: int = 0):
            value = max(0.0, min(1.0, value))
            callback(value, remaining, time_est)

        return wrapped

    def _wrap_log(self, callback: Optional[Callable[[str], None]]) -> Callable[[str], None]:
        """包装日志回调"""
        if callback is None:
            def noop(msg: str):
                pass
            return noop
        return callback

    def _create_progress_mapper(self, start: float, end: float) -> Callable[[float], None]:
        """
        创建进度映射器 - 将子进度映射到总进度区间

        Args:
            start: 起始进度（如0.2）
            end: 结束进度（如0.8）

        Returns:
            映射函数
        """
        range_size = end - start

        def mapper(progress: float):
            mapped = start + progress * range_size
            return max(start, min(end, mapped))

        return mapper

    def get_execution_stats(self) -> Dict[str, Any]:
        """获取执行统计"""
        return {
            'name': self.name,
            'execution_count': self._execution_count
        }
