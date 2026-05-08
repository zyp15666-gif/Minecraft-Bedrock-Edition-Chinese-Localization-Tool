#!/usr/bin/env python3
from unittest.mock import Mock, patch

import pytest

from api.retry_strategy import (
    RetryStrategy,
    create_api_retry_strategy,
    create_quick_retry_strategy,
    create_steady_retry_strategy,
    retry_on_api_error,
)


class TestRetryStrategy:
    @pytest.fixture
    def strategy(self):
        return RetryStrategy(
            max_attempts=3,
            base_delay=0.01,
            max_delay=0.05,
            backoff_factor=2.0,
            jitter=0.0,
        )

    def test_default_values(self):
        s = RetryStrategy()
        assert s.max_attempts == RetryStrategy.DEFAULT_MAX_ATTEMPTS
        assert s.base_delay == RetryStrategy.DEFAULT_BASE_DELAY
        assert s.max_delay == RetryStrategy.DEFAULT_MAX_DELAY
        assert s.backoff_factor == RetryStrategy.DEFAULT_BACKOFF_FACTOR
        assert s.jitter == RetryStrategy.DEFAULT_JITTER
        assert s.exceptions == (Exception,)

    def test_custom_values(self):
        s = RetryStrategy(
            max_attempts=5,
            base_delay=2.0,
            max_delay=30.0,
            backoff_factor=3.0,
            jitter=0.2,
            exceptions=(ConnectionError, TimeoutError),
        )
        assert s.max_attempts == 5
        assert s.base_delay == 2.0
        assert s.max_delay == 30.0
        assert s.backoff_factor == 3.0
        assert s.jitter == 0.2
        assert s.exceptions == (ConnectionError, TimeoutError)

    def test_calculate_delay_no_jitter(self, strategy):
        delay1 = strategy.calculate_delay(1)
        assert delay1 == pytest.approx(0.01, abs=0.001)

        delay2 = strategy.calculate_delay(2)
        assert delay2 == pytest.approx(0.02, abs=0.001)

        delay3 = strategy.calculate_delay(3)
        assert delay3 == pytest.approx(0.04, abs=0.001)

    def test_calculate_delay_capped_at_max(self):
        s = RetryStrategy(base_delay=10.0, max_delay=5.0, backoff_factor=2.0, jitter=0.0)
        delay = s.calculate_delay(1)
        assert delay == 5.0

    def test_calculate_delay_with_jitter(self):
        s = RetryStrategy(base_delay=1.0, max_delay=10.0, backoff_factor=2.0, jitter=0.5)
        delays = [s.calculate_delay(1) for _ in range(100)]
        assert min(delays) >= 0
        assert all(d > 0 for d in delays)

    def test_should_retry_within_limit(self, strategy):
        assert strategy.should_retry(1, Exception("err")) is True
        assert strategy.should_retry(2, Exception("err")) is True

    def test_should_retry_at_limit(self, strategy):
        assert strategy.should_retry(3, Exception("err")) is False

    def test_should_retry_non_matching_exception(self):
        s = RetryStrategy(exceptions=(ConnectionError,))
        assert s.should_retry(1, ValueError("err")) is False
        assert s.should_retry(1, ConnectionError("err")) is True

    def test_execute_success_first_try(self, strategy):
        func = Mock(return_value="ok")
        result = strategy.execute(func, "arg1", key="val")
        assert result == "ok"
        func.assert_called_once_with("arg1", key="val")

    def test_execute_retries_on_failure(self, strategy):
        func = Mock(side_effect=[ConnectionError("fail"), "ok"])
        result = strategy.execute(func)
        assert result == "ok"
        assert func.call_count == 2

    def test_execute_raises_after_max_attempts(self, strategy):
        func = Mock(side_effect=ConnectionError("always fail"))
        with pytest.raises(ConnectionError, match="always fail"):
            strategy.execute(func)
        assert func.call_count == 3

    def test_execute_non_retryable_exception_propagates(self):
        s = RetryStrategy(exceptions=(ConnectionError,))
        func = Mock(side_effect=ValueError("not retryable"))
        with pytest.raises(ValueError, match="not retryable"):
            s.execute(func)
        assert func.call_count == 1

    @patch("api.retry_strategy.time.sleep")
    def test_execute_sleeps_between_retries(self, mock_sleep, strategy):
        func = Mock(side_effect=[ConnectionError("fail"), "ok"])
        strategy.execute(func)
        mock_sleep.assert_called_once()
        call_args = mock_sleep.call_args[0][0]
        assert call_args >= 0


class TestRetryOnApiErrorDecorator:
    def test_decorator_with_default_strategy(self):
        call_count = [0]

        @retry_on_api_error()
        def flaky():
            call_count[0] += 1
            if call_count[0] < 2:
                raise Exception("fail")
            return "success"

        with patch("api.retry_strategy.time.sleep"):
            result = flaky()
        assert result == "success"
        assert call_count[0] == 2

    def test_decorator_with_custom_strategy(self):
        strategy = RetryStrategy(max_attempts=2, base_delay=0.001, jitter=0.0)

        @retry_on_api_error(strategy=strategy)
        def always_fail():
            raise ConnectionError("fail")

        with patch("api.retry_strategy.time.sleep"):
            with pytest.raises(ConnectionError):
                always_fail()

    def test_decorator_preserves_function_name(self):
        @retry_on_api_error()
        def my_function():
            pass

        assert my_function.__name__ == "my_function"

    def test_decorator_with_specific_exceptions(self):
        call_count = [0]

        @retry_on_api_error(exceptions=(ConnectionError,))
        def mixed_errors():
            call_count[0] += 1
            if call_count[0] == 1:
                raise ConnectionError("retryable")
            return "ok"

        with patch("api.retry_strategy.time.sleep"):
            result = mixed_errors()
        assert result == "ok"


class TestFactoryFunctions:
    def test_create_quick_retry_strategy(self):
        s = create_quick_retry_strategy()
        assert s.max_attempts == 3
        assert s.base_delay == 0.5
        assert s.max_delay == 3.0
        assert s.backoff_factor == 1.5
        assert s.jitter == 0.1

    def test_create_steady_retry_strategy(self):
        s = create_steady_retry_strategy()
        assert s.max_attempts == 5
        assert s.base_delay == 2.0
        assert s.max_delay == 30.0
        assert s.backoff_factor == 2.0
        assert s.jitter == 0.2

    def test_create_api_retry_strategy(self):
        s = create_api_retry_strategy()
        assert s.max_attempts == 3
        assert s.base_delay == 1.0
        assert s.max_delay == 10.0
        assert s.exceptions == (ConnectionError, TimeoutError, OSError)
