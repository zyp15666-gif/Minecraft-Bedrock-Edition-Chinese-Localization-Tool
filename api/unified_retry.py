#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一重试策略管理器

集中管理所有API重试逻辑，消除多层重试造成的混乱。
使用装饰器模式提供灵活的重试配置。

使用示例:
    from api.unified_retry import with_retry, RetryPolicy

    @with_retry()
    def my_api_function():
        ...

    @with_retry(RetryPolicy.quick())
    def fast_api_call():
        ...
"""

import functools
import random
import time
from enum import Enum
from typing import Any, Callable, Dict, Optional, Tuple, Type

from core.log_manager import get_logger

logger = get_logger(__name__)


class RetryableError(Enum):
    """可重试的错误类型"""
    NETWORK_ERROR = "network"
    TIMEOUT_ERROR = "timeout"
    RATE_LIMIT_ERROR = "rate_limit"
    SERVER_ERROR = "server"
    UNKNOWN_ERROR = "unknown"


class RetryPolicy:
    """重试策略配置类"""

    DEFAULT_RETRYABLE_ERRORS: Tuple[Type[Exception], ...] = (
        ConnectionError,
        TimeoutError,
        ConnectionResetError,
        ConnectionRefusedError,
    )

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 10.0,
        backoff_factor: float = 2.0,
        jitter: float = 0.1,
        retryable_exceptions: Tuple[Type[Exception], ...] = None,
        enable_exponential_backoff: bool = True,
        enable_jitter: bool = True,
    ):
        """初始化重试策略

        Args:
            max_attempts: 最大尝试次数
            base_delay: 基础延迟时间（秒）
            max_delay: 最大延迟时间（秒）
            backoff_factor: 退避因子
            jitter: 抖动因子（0-1之间）
            retryable_exceptions: 可重试的异常类型元组
            enable_exponential_backoff: 是否启用指数退避
            enable_jitter: 是否启用抖动
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or self.DEFAULT_RETRYABLE_ERRORS
        self.enable_exponential_backoff = enable_exponential_backoff
        self.enable_jitter = enable_jitter

    def calculate_delay(self, attempt: int) -> float:
        """计算延迟时间

        Args:
            attempt: 当前尝试次数（从1开始）

        Returns:
            延迟时间（秒）
        """
        if self.enable_exponential_backoff:
            delay = min(self.base_delay * (self.backoff_factor ** (attempt - 1)), self.max_delay)
        else:
            delay = self.base_delay

        if self.enable_jitter:
            delay = delay * (1 + random.uniform(-self.jitter, self.jitter))

        return delay

    def should_retry(self, attempt: int, exception: Exception) -> bool:
        """判断是否应该重试

        Args:
            attempt: 当前尝试次数
            exception: 发生的异常

        Returns:
            是否应该重试
        """
        if attempt >= self.max_attempts:
            return False

        return isinstance(exception, self.retryable_exceptions)

    def classify_error(self, exception: Exception) -> RetryableError:
        """对错误进行分类

        Args:
            exception: 异常对象

        Returns:
            错误类型
        """
        error_msg = str(exception).lower()

        if isinstance(exception, (ConnectionError, ConnectionResetError, ConnectionRefusedError)):
            return RetryableError.NETWORK_ERROR
        elif isinstance(exception, TimeoutError):
            return RetryableError.TIMEOUT_ERROR
        elif 'rate' in error_msg or '429' in error_msg or 'too many' in error_msg:
            return RetryableError.RATE_LIMIT_ERROR
        elif '500' in error_msg or '502' in error_msg or '503' in error_msg or 'server' in error_msg:
            return RetryableError.SERVER_ERROR
        else:
            return RetryableError.UNKNOWN_ERROR

    @classmethod
    def default(cls) -> 'RetryPolicy':
        """获取默认重试策略"""
        return cls(
            max_attempts=3,
            base_delay=1.0,
            max_delay=10.0,
            backoff_factor=2.0,
            jitter=0.1,
        )

    @classmethod
    def quick(cls) -> 'RetryPolicy':
        """快速重试策略（短延迟，高频率）"""
        return cls(
            max_attempts=3,
            base_delay=0.5,
            max_delay=3.0,
            backoff_factor=2.0,
            jitter=0.2,
        )

    @classmethod
    def steady(cls) -> 'RetryPolicy':
        """稳定重试策略（长延迟，低频率）"""
        return cls(
            max_attempts=5,
            base_delay=2.0,
            max_delay=30.0,
            backoff_factor=2.0,
            jitter=0.1,
        )

    @classmethod
    def api_call(cls) -> 'RetryPolicy':
        """API调用专用策略"""
        return cls(
            max_attempts=3,
            base_delay=1.0,
            max_delay=10.0,
            backoff_factor=2.0,
            jitter=0.1,
            retryable_exceptions=(ConnectionError, TimeoutError, ConnectionResetError),
        )


def with_retry(
    policy: Optional[RetryPolicy] = None,
    retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    max_attempts: Optional[int] = None,
):
    """重试装饰器

    Args:
        policy: RetryPolicy实例，如果为None则使用默认策略
        retryable_exceptions: 可重试的异常类型元组
        max_attempts: 最大尝试次数，会覆盖policy中的设置

    Returns:
        装饰器函数

    Example:
        @with_retry()
        def api_call():
            return requests.get(url)

        @with_retry(policy=RetryPolicy.quick())
        def fast_call():
            return api.quick_request()
    """
    _policy = policy or RetryPolicy.default()

    if retryable_exceptions:
        _policy = RetryPolicy(
            max_attempts=max_attempts or _policy.max_attempts,
            base_delay=_policy.base_delay,
            max_delay=_policy.max_delay,
            backoff_factor=_policy.backoff_factor,
            jitter=_policy.jitter,
            retryable_exceptions=retryable_exceptions,
        )

    if max_attempts:
        _policy.max_attempts = max_attempts

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(1, _policy.max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if not _policy.should_retry(attempt, e):
                        logger.error(
                            f"[Retry] {func.__name__} 失败（非重试类型错误）: {type(e).__name__}: {e}"
                        )
                        raise

                    error_type = _policy.classify_error(e)
                    delay = _policy.calculate_delay(attempt)

                    logger.warning(
                        f"[Retry] {func.__name__} 尝试 {attempt}/{_policy.max_attempts} "
                        f"失败（{error_type.value}）: {type(e).__name__}, "
                        f"{'不重试' if attempt >= _policy.max_attempts else f'等待 {delay:.2f}秒后重试'}"
                    )

                    if attempt < _policy.max_attempts:
                        time.sleep(delay)

            if last_exception:
                raise last_exception

        return wrapper

    return decorator


class RetryMetrics:
    """重试指标收集器"""

    def __init__(self):
        self.total_calls: int = 0
        self.successful_calls: int = 0
        self.failed_calls: int = 0
        self.total_retries: int = 0
        self.error_counts: Dict[str, int] = {}

    def record_call(self, success: bool, retry_count: int = 0, error_type: str = None):
        """记录调用结果"""
        self.total_calls += 1
        if success:
            self.successful_calls += 1
        else:
            self.failed_calls += 1

        self.total_retries += retry_count

        if error_type:
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1

    def get_stats(self) -> Dict[str, Any]:
        """获取统计数据"""
        return {
            'total_calls': self.total_calls,
            'successful_calls': self.successful_calls,
            'failed_calls': self.failed_calls,
            'total_retries': self.total_retries,
            'success_rate': (
                self.successful_calls / self.total_calls * 100
                if self.total_calls > 0 else 0
            ),
            'average_retries': (
                self.total_retries / self.total_calls
                if self.total_calls > 0 else 0
            ),
            'error_counts': dict(self.error_counts),
        }

    def reset(self):
        """重置统计"""
        self.total_calls = 0
        self.successful_calls = 0
        self.failed_calls = 0
        self.total_retries = 0
        self.error_counts = {}


retry_metrics = RetryMetrics()
