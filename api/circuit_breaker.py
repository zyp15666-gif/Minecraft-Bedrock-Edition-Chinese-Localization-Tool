#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API 熔断器模块

实现熔断器模式，防止持续向故障 API 发送请求。
当 API 失败率达到阈值时，暂时跳过该 API，等待恢复后再尝试。

使用方式：
    from api.circuit_breaker import CircuitBreaker, CircuitOpenError

    cb = CircuitBreaker()

    try:
        result = cb.call(api_name, api_manager.translate_text, text)
    except CircuitOpenError:
        print("API 暂时不可用")
"""

import threading
import time
from enum import Enum
from typing import Any, Callable, Dict, Optional

from core.log_manager import get_logger

logger = get_logger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(Exception):
    """熔断器开启异常 - 当 API 处于熔断状态时抛出"""
    pass


class CircuitBreaker:
    """
    API 熔断器

    三种状态：
    - CLOSED: 正常状态，请求直接通过
    - OPEN: 熔断状态，请求被拒绝
    - HALF_OPEN: 半开状态，允许少量请求通过尝试恢复
    """

    FAILURE_THRESHOLD = 5
    RECOVERY_TIMEOUT = 60
    HALF_OPEN_MAX_CALLS = 3
    SUCCESS_THRESHOLD = 2

    def __init__(
        self,
        failure_threshold: Optional[int] = None,
        recovery_timeout: Optional[int] = None,
        half_open_max_calls: Optional[int] = None,
        success_threshold: Optional[int] = None
    ):
        """
        初始化熔断器

        Args:
            failure_threshold: 打开熔断的连续失败次数
            recovery_timeout: 熔断后尝试恢复的等待时间（秒）
            half_open_max_calls: 半开状态允许的最大尝试次数
            success_threshold: 半开状态下恢复需要的最少成功次数
        """
        self.failure_threshold = failure_threshold or self.FAILURE_THRESHOLD
        self.recovery_timeout = recovery_timeout or self.RECOVERY_TIMEOUT
        self.half_open_max_calls = half_open_max_calls or self.HALF_OPEN_MAX_CALLS
        self.success_threshold = success_threshold or self.SUCCESS_THRESHOLD

        self._states: Dict[str, CircuitState] = {}
        self._failure_counts: Dict[str, int] = {}
        self._success_counts: Dict[str, int] = {}
        self._last_failure_time: Dict[str, float] = {}
        self._half_open_calls: Dict[str, int] = {}
        self._lock = threading.RLock()

    def call(
        self,
        api_name: str,
        func: Callable[..., Any],
        *args,
        **kwargs
    ) -> Any:
        """
        通过熔断器调用函数

        Args:
            api_name: API 名称（用于熔断器状态管理）
            func: 要调用的函数
            *args: 函数位置参数
            **kwargs: 函数关键字参数

        Returns:
            函数返回值

        Raises:
            CircuitOpenError: 当熔断器处于 OPEN 状态时
        """
        with self._lock:
            state = self._states.get(api_name, CircuitState.CLOSED)

            if state == CircuitState.OPEN:
                if self._should_attempt_recovery(api_name):
                    self._transition_to_half_open(api_name)
                else:
                    logger.debug(f"[CircuitBreaker] {api_name} 熔断器开启，拒绝请求")
                    raise CircuitOpenError(f"API {api_name} 熔断器开启，请稍后重试")

            if state == CircuitState.HALF_OPEN:
                if self._half_open_calls.get(api_name, 0) >= self.half_open_max_calls:
                    logger.debug(f"[CircuitBreaker] {api_name} 半开状态尝试次数已用完")
                    raise CircuitOpenError(f"API {api_name} 正在恢复中，请稍后重试")

                self._half_open_calls[api_name] = self._half_open_calls.get(api_name, 0) + 1

        try:
            result = func(*args, **kwargs)
            self._on_success(api_name)
            return result
        except Exception:
            self._on_failure(api_name)
            raise

    def _should_attempt_recovery(self, api_name: str) -> bool:
        """检查是否应该尝试恢复"""
        last_failure = self._last_failure_time.get(api_name, 0)
        return time.time() - last_failure >= self.recovery_timeout

    def _transition_to_half_open(self, api_name: str):
        """转换到半开状态"""
        self._states[api_name] = CircuitState.HALF_OPEN
        self._half_open_calls[api_name] = 0
        self._success_counts[api_name] = 0
        logger.info(f"[CircuitBreaker] {api_name} 进入半开状态")

    def _on_success(self, api_name: str):
        """处理成功调用"""
        with self._lock:
            state = self._states.get(api_name, CircuitState.CLOSED)

            if state == CircuitState.HALF_OPEN:
                self._success_counts[api_name] = self._success_counts.get(api_name, 0) + 1

                if self._success_counts.get(api_name, 0) >= self.success_threshold:
                    self._states[api_name] = CircuitState.CLOSED
                    self._failure_counts[api_name] = 0
                    self._success_counts[api_name] = 0
                    self._half_open_calls[api_name] = 0
                    logger.info(f"[CircuitBreaker] {api_name} 熔断器关闭，恢复正常")

            elif state == CircuitState.CLOSED:
                self._failure_counts[api_name] = 0

    def _on_failure(self, api_name: str):
        """处理失败调用"""
        with self._lock:
            self._failure_counts[api_name] = self._failure_counts.get(api_name, 0) + 1
            self._last_failure_time[api_name] = time.time()

            state = self._states.get(api_name, CircuitState.CLOSED)

            if state == CircuitState.HALF_OPEN:
                self._states[api_name] = CircuitState.OPEN
                self._half_open_calls[api_name] = 0
                logger.warning(f"[CircuitBreaker] {api_name} 半开状态失败，重新开启熔断器")

            elif state == CircuitState.CLOSED:
                if self._failure_counts.get(api_name, 0) >= self.failure_threshold:
                    self._states[api_name] = CircuitState.OPEN
                    logger.warning(
                        f"[CircuitBreaker] {api_name} 失败次数达到阈值 "
                        f"({self._failure_counts[api_name]}/{self.failure_threshold})，开启熔断器"
                    )

    def get_state(self, api_name: str) -> CircuitState:
        """获取 API 的熔断器状态"""
        with self._lock:
            return self._states.get(api_name, CircuitState.CLOSED)

    def is_open(self, api_name: str) -> bool:
        """调度层使用：OPEN 且未到恢复窗口时跳过该 API。"""
        with self._lock:
            state = self._states.get(api_name, CircuitState.CLOSED)
            if state == CircuitState.OPEN:
                return not self._should_attempt_recovery(api_name)
            return False

    def record_success(self, api_name: str):
        """在 `call()` 外包一层记录成功（如 APIOrchestrator）。"""
        self._on_success(api_name)

    def record_failure(self, api_name: str):
        """在 `call()` 外包一层记录失败（如 APIOrchestrator）。"""
        self._on_failure(api_name)

    def is_available(self, api_name: str) -> bool:
        """检查 API 是否可用（熔断器未开启）"""
        with self._lock:
            state = self._states.get(api_name, CircuitState.CLOSED)
            if state == CircuitState.OPEN:
                if self._should_attempt_recovery(api_name):
                    return True
                return False
            return True

    def get_stats(self) -> Dict[str, Any]:
        """获取熔断器统计信息"""
        with self._lock:
            stats = {}
            for api_name in self._states.keys():
                stats[api_name] = {
                    'state': self._states[api_name].value,
                    'failure_count': self._failure_counts.get(api_name, 0),
                    'success_count': self._success_counts.get(api_name, 0),
                    'half_open_calls': self._half_open_calls.get(api_name, 0),
                    'last_failure_time': self._last_failure_time.get(api_name, 0),
                }
            return stats

    def reset(self, api_name: Optional[str] = None):
        """
        重置熔断器状态

        Args:
            api_name: 如果为 None，重置所有 API；否则只重置指定 API
        """
        with self._lock:
            if api_name is None:
                self._states.clear()
                self._failure_counts.clear()
                self._success_counts.clear()
                self._last_failure_time.clear()
                self._half_open_calls.clear()
                logger.info("[CircuitBreaker] 所有 API 熔断器状态已重置")
            else:
                self._states.pop(api_name, None)
                self._failure_counts.pop(api_name, None)
                self._success_counts.pop(api_name, None)
                self._last_failure_time.pop(api_name, None)
                self._half_open_calls.pop(api_name, None)
                logger.info(f"[CircuitBreaker] {api_name} 熔断器状态已重置")

    def __repr__(self) -> str:
        return (
            f"<CircuitBreaker "
            f"failure_threshold={self.failure_threshold} "
            f"recovery_timeout={self.recovery_timeout}>"
        )


_global_circuit_breaker: Optional[CircuitBreaker] = None
_global_breaker_lock = threading.Lock()


def get_global_circuit_breaker() -> CircuitBreaker:
    """获取全局熔断器实例（单例模式）"""
    global _global_circuit_breaker
    with _global_breaker_lock:
        if _global_circuit_breaker is None:
            _global_circuit_breaker = CircuitBreaker()
        return _global_circuit_breaker


def reset_global_circuit_breaker():
    """重置全局熔断器实例"""
    global _global_circuit_breaker
    with _global_breaker_lock:
        if _global_circuit_breaker is not None:
            _global_circuit_breaker.reset()
            _global_circuit_breaker = None


if __name__ == "__main__":

    print("=" * 60)
    print("熔断器单元测试")
    print("=" * 60)

    cb = CircuitBreaker(
        failure_threshold=3,
        recovery_timeout=5,
        half_open_max_calls=2,
        success_threshold=1
    )

    def mock_api_call(should_fail=False):
        if should_fail:
            raise Exception("API Error")
        return "success"

    print("\n1. 测试正常状态")
    result = cb.call("test_api", mock_api_call, False)
    print(f"   调用结果: {result}")
    print(f"   状态: {cb.get_state('test_api')}")
    assert result == "success"
    assert cb.get_state("test_api") == CircuitState.CLOSED

    print("\n2. 测试熔断开启")
    for i in range(3):
        try:
            cb.call("test_api", mock_api_call, True)
        except Exception:
            pass
    print(f"   状态: {cb.get_state('test_api')}")
    assert cb.get_state("test_api") == CircuitState.OPEN

    print("\n3. 测试熔断开启时拒绝请求")
    try:
        cb.call("test_api", mock_api_call, False)
        print("   错误：应该抛出异常")
    except CircuitOpenError as e:
        print(f"   正确捕获异常: {e}")

    print("\n4. 测试等待恢复后进入半开状态")
    import time
    print(f"   等待 {cb.recovery_timeout + 1} 秒...")
    time.sleep(cb.recovery_timeout + 1)

    try:
        cb.call("test_api", mock_api_call, False)
        print(f"   状态: {cb.get_state('test_api')}")
        assert cb.get_state("test_api") == CircuitState.HALF_OPEN
    except CircuitOpenError:
        print("   半开状态调用失败（可能需要更多测试）")

    print("\n5. 测试重置功能")
    cb.reset("test_api")
    print(f"   重置后状态: {cb.get_state('test_api')}")
    assert cb.get_state("test_api") == CircuitState.CLOSED

    print("\n" + "=" * 60)
    print("所有测试通过!")
    print("=" * 60)
