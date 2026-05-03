#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API 重试策略模块

提供增强的重试逻辑，支持：
- 指数退避
- Jitter（随机延迟）
- 条件重试（仅在特定异常时重试）
- 熔断器集成

使用方式：
    from api.retry_strategy import RetryStrategy, retry_on_api_error

    strategy = RetryStrategy()

    @retry_on_api_error(strategy)
    def translate_text(api_manager, text):
        return api_manager.translate_text(text)
"""

import random
import time
import functools
from typing import Callable, Type, Tuple, Optional, Any, TypeVar

from core.log_manager import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


class RetryStrategy:
    """
    可配置的重试策略

    支持：
    - 最大重试次数
    - 指数退避
    - Jitter（随机延迟）
    - 条件重试
    """

    DEFAULT_MAX_ATTEMPTS = 3
    DEFAULT_BASE_DELAY = 1.0
    DEFAULT_MAX_DELAY = 10.0
    DEFAULT_BACKOFF_FACTOR = 2.0
    DEFAULT_JITTER = 0.1

    def __init__(
        self,
        max_attempts: Optional[int] = None,
        base_delay: float = DEFAULT_BASE_DELAY,
        max_delay: float = DEFAULT_MAX_DELAY,
        backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
        jitter: float = DEFAULT_JITTER,
        exceptions: Tuple[Type[Exception], ...] = (Exception,)
    ):
        """
        初始化重试策略

        Args:
            max_attempts: 最大尝试次数
            base_delay: 基础延迟（秒）
            max_delay: 最大延迟（秒）
            backoff_factor: 退避因子
            jitter: Jitter 比例（0-1），用于避免惊群效应
            exceptions: 需要重试的异常类型元组
        """
        self.max_attempts = max_attempts or self.DEFAULT_MAX_ATTEMPTS
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self.exceptions = exceptions

    def calculate_delay(self, attempt: int) -> float:
        """
        计算延迟时间（指数退避 + Jitter）

        Args:
            attempt: 当前尝试次数（从1开始）

        Returns:
            延迟时间（秒）
        """
        delay = min(
            self.base_delay * (self.backoff_factor ** (attempt - 1)),
            self.max_delay
        )

        if self.jitter > 0:
            jitter_amount = delay * self.jitter
            delay = delay + random.uniform(-jitter_amount, jitter_amount)

        return max(0, delay)

    def should_retry(self, attempt: int, exception: Exception) -> bool:
        """
        判断是否应该重试

        Args:
            attempt: 当前尝试次数
            exception: 发生的异常

        Returns:
            是否应该重试
        """
        if attempt >= self.max_attempts:
            return False

        return isinstance(exception, self.exceptions)

    def execute(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        执行函数并在失败时重试

        Args:
            func: 要执行的函数
            *args: 函数位置参数
            **kwargs: 函数关键字参数

        Returns:
            函数返回值

        Raises:
            最后一次尝试的异常
        """
        last_exception = None

        for attempt in range(1, self.max_attempts + 1):
            try:
                return func(*args, **kwargs)
            except self.exceptions as e:
                last_exception = e

                if not self.should_retry(attempt, e):
                    raise

                delay = self.calculate_delay(attempt)
                logger.warning(
                    f"[Retry] 尝试 {attempt}/{self.max_attempts} 失败: {type(e).__name__}, "
                    f"{delay:.2f}秒后重试..."
                )
                time.sleep(delay)

        raise last_exception


def retry_on_api_error(
    strategy: Optional[RetryStrategy] = None,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    装饰器：为函数添加重试逻辑

    使用示例：
        @retry_on_api_error()
        def translate_text(text):
            return api_manager.translate_text(text)

        @retry_on_api_error(exceptions=(ConnectionError, TimeoutError))
        def fetch_data(url):
            return requests.get(url)

    Args:
        strategy: RetryStrategy 实例，如果为 None 使用默认策略
        exceptions: 需要重试的异常类型

    Returns:
        装饰器函数
    """
    if strategy is None:
        strategy = RetryStrategy(exceptions=exceptions)

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            return strategy.execute(func, *args, **kwargs)
        return wrapper
    return decorator


def create_quick_retry_strategy() -> RetryStrategy:
    """创建快速重试策略（短延迟，高频率）"""
    return RetryStrategy(
        max_attempts=3,
        base_delay=0.5,
        max_delay=3.0,
        backoff_factor=1.5,
        jitter=0.1
    )


def create_steady_retry_strategy() -> RetryStrategy:
    """创建稳定重试策略（长延迟，低频率）"""
    return RetryStrategy(
        max_attempts=5,
        base_delay=2.0,
        max_delay=30.0,
        backoff_factor=2.0,
        jitter=0.2
    )


def create_api_retry_strategy() -> RetryStrategy:
    """创建适合 API 调用的重试策略"""
    return RetryStrategy(
        max_attempts=3,
        base_delay=1.0,
        max_delay=10.0,
        backoff_factor=2.0,
        jitter=0.1,
        exceptions=(ConnectionError, TimeoutError, OSError)
    )


if __name__ == "__main__":
    print("=" * 60)
    print("重试策略测试")
    print("=" * 60)

    strategy = RetryStrategy(
        max_attempts=4,
        base_delay=0.5,
        max_delay=5.0,
        backoff_factor=2.0,
        jitter=0.1
    )

    print("\n1. 延迟计算测试")
    for attempt in range(1, 5):
        delay = strategy.calculate_delay(attempt)
        print(f"   尝试 {attempt}: {delay:.3f}s")

    print("\n2. 装饰器测试")
    call_count = [0]

    @retry_on_api_error(strategy)
    def flaky_function():
        call_count[0] += 1
        if call_count[0] < 3:
            raise ConnectionError("模拟连接失败")
        return "success"

    result = flaky_function()
    print(f"   函数返回: {result}, 调用次数: {call_count[0]}")
    assert result == "success"
    assert call_count[0] == 3

    print("\n3. 策略工厂测试")
    quick = create_quick_retry_strategy()
    steady = create_steady_retry_strategy()
    api = create_api_retry_strategy()

    print(f"   快速策略: max_attempts={quick.max_attempts}, base_delay={quick.base_delay}")
    print(f"   稳定策略: max_attempts={steady.max_attempts}, base_delay={steady.base_delay}")
    print(f"   API策略: max_attempts={api.max_attempts}, exceptions={api.exceptions}")

    print("\n" + "=" * 60)
    print("所有测试通过!")
    print("=" * 60)
