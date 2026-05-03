#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CircuitBreaker 熔断器单元测试
"""

import pytest
import time
from unittest.mock import Mock, patch
from api.circuit_breaker import (
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
    get_global_circuit_breaker,
    reset_global_circuit_breaker
)


class TestCircuitBreaker:
    """熔断器测试"""

    @pytest.fixture
    def cb(self):
        """创建熔断器实例"""
        return CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=1,
            half_open_max_calls=2,
            success_threshold=1
        )

    def test_initial_state(self, cb):
        """测试初始状态"""
        assert cb.get_state("unknown_api") == CircuitState.CLOSED
        assert cb.is_available("unknown_api") is True

    def test_successful_call(self, cb):
        """测试成功调用"""
        mock_func = Mock(return_value="result")
        result = cb.call("test_api", mock_func, "arg1", kwarg1="value")

        assert result == "result"
        mock_func.assert_called_once_with("arg1", kwarg1="value")
        assert cb.get_state("test_api") == CircuitState.CLOSED

    def test_failure_increments_counter(self, cb):
        """测试失败时增加失败计数"""
        mock_func = Mock(side_effect=Exception("API Error"))

        for _ in range(2):
            try:
                cb.call("test_api", mock_func)
            except Exception:
                pass

        assert cb.get_state("test_api") == CircuitState.CLOSED

    def test_circuit_opens_after_threshold(self, cb):
        """测试达到阈值后熔断器打开"""
        mock_func = Mock(side_effect=Exception("API Error"))

        for _ in range(3):
            try:
                cb.call("test_api", mock_func)
            except Exception:
                pass

        assert cb.get_state("test_api") == CircuitState.OPEN
        assert cb.is_available("test_api") is False

    def test_call_rejected_when_open(self, cb):
        """测试熔断器打开时拒绝请求"""
        mock_func = Mock(side_effect=Exception("API Error"))

        for _ in range(3):
            try:
                cb.call("test_api", mock_func)
            except Exception:
                pass

        mock_func.reset_mock()

        with pytest.raises(CircuitOpenError):
            cb.call("test_api", mock_func)

        mock_func.assert_not_called()

    def test_recovery_after_timeout(self, cb):
        """测试超时后进入半开状态"""
        mock_func = Mock(side_effect=Exception("API Error"))

        for _ in range(3):
            try:
                cb.call("test_api", mock_func)
            except Exception:
                pass

        assert cb.get_state("test_api") == CircuitState.OPEN

        time.sleep(1.5)

        assert cb.is_available("test_api") is True

        mock_func.side_effect = None
        mock_func.return_value = "success"
        result = cb.call("test_api", mock_func)

        assert result == "success"
        assert cb.get_state("test_api") == CircuitState.CLOSED

    def test_half_open_to_closed_on_success(self, cb):
        """测试半开状态成功后关闭熔断器"""
        mock_func = Mock(side_effect=Exception("API Error"))

        for _ in range(3):
            try:
                cb.call("test_api", mock_func)
            except Exception:
                pass

        time.sleep(1.5)

        mock_func.side_effect = None
        mock_func.return_value = "success"

        cb.call("test_api", mock_func)

        assert cb.get_state("test_api") == CircuitState.CLOSED

    def test_half_open_to_open_on_failure(self, cb):
        """测试半开状态失败后重新打开熔断器"""
        mock_func = Mock(side_effect=Exception("API Error"))

        for _ in range(3):
            try:
                cb.call("test_api", mock_func)
            except Exception:
                pass

        time.sleep(1.5)

        try:
            cb.call("test_api", mock_func)
        except Exception:
            pass

        assert cb.get_state("test_api") == CircuitState.OPEN

    def test_reset_single_api(self, cb):
        """测试重置单个 API"""
        mock_func = Mock(side_effect=Exception("API Error"))

        for _ in range(3):
            try:
                cb.call("test_api", mock_func)
            except Exception:
                pass

        assert cb.get_state("test_api") == CircuitState.OPEN

        cb.reset("test_api")

        assert cb.get_state("test_api") == CircuitState.CLOSED
        assert cb.is_available("test_api") is True

    def test_reset_all(self, cb):
        """测试重置所有 API"""
        mock_func = Mock(side_effect=Exception("API Error"))

        for i in range(3):
            try:
                cb.call(f"api_{i}", mock_func)
            except Exception:
                pass

        cb.reset()

        assert cb.get_state("api_0") == CircuitState.CLOSED
        assert cb.get_state("api_1") == CircuitState.CLOSED
        assert cb.get_state("api_2") == CircuitState.CLOSED

    def test_get_stats(self, cb):
        """测试获取统计信息"""
        mock_func = Mock(side_effect=Exception("API Error"))

        for _ in range(3):
            try:
                cb.call("test_api", mock_func)
            except Exception:
                pass

        stats = cb.get_stats()

        assert "test_api" in stats
        assert stats["test_api"]["failure_count"] == 3
        assert stats["test_api"]["state"] == "open"

    def test_global_circuit_breaker_singleton(self):
        """测试全局熔断器单例"""
        reset_global_circuit_breaker()

        cb1 = get_global_circuit_breaker()
        cb2 = get_global_circuit_breaker()

        assert cb1 is cb2

        reset_global_circuit_breaker()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
