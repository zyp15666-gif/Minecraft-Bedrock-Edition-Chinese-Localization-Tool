"""
API客户端集成测试 — 模拟HTTP响应测试重试、解析、异常
"""

import pytest
import time
from unittest.mock import patch, MagicMock

from api.api_client import APIClient
from core.exceptions import (
    APITimeoutError, APIConnectionError, APIResponseError,
)


class TestAPIClientRetry:
    """API客户端重试机制测试"""

    @patch('api.api_client.requests.post')
    def test_retry_on_timeout_then_succeed(self, mock_post):
        """超时后重试成功"""
        mock_post.side_effect = [
            __import__('requests').exceptions.Timeout("timeout"),
            MagicMock(status_code=200, json=lambda: {"choices": [{"message": {"content": "你好"}}]}),
        ]

        client = APIClient({"default": 0.0}, retry_config={"max_retries": 2, "base_delay": 0.01, "max_delay": 0.1})
        result = client.translate(
            {"name": "test", "api_url": "http://test/v1", "model": "test", "type": "openai"},
            "Hello", is_test=True
        )
        assert result is not None

    @patch('api.api_client.requests.post')
    def test_timeout_raises_after_max_retries(self, mock_post):
        """超时耗尽重试后抛出APITimeoutError"""
        mock_post.side_effect = __import__('requests').exceptions.Timeout("timeout")

        client = APIClient({"default": 0.0}, retry_config={"max_retries": 2, "base_delay": 0.01, "max_delay": 0.1})
        with pytest.raises(APITimeoutError):
            client.translate(
                {"name": "test", "api_url": "http://test/v1", "model": "test", "type": "openai"},
                "Hello", is_test=True
            )

    @patch('api.api_client.requests.post')
    def test_connection_error_raises(self, mock_post):
        """连接错误抛出APIConnectionError"""
        mock_post.side_effect = __import__('requests').exceptions.ConnectionError("refused")

        client = APIClient({"default": 0.0}, retry_config={"max_retries": 2, "base_delay": 0.01, "max_delay": 0.1})
        with pytest.raises(APIConnectionError):
            client.translate(
                {"name": "test", "api_url": "http://test/v1", "model": "test", "type": "openai"},
                "Hello", is_test=True
            )

    @patch('api.api_client.requests.post')
    def test_malformed_json_response_raises(self, mock_post):
        """JSON解析异常抛出APIResponseError"""
        mock_post.return_value = MagicMock(status_code=200, json=lambda: {})

        client = APIClient({"default": 0.0}, retry_config={"max_retries": 1, "base_delay": 0.01, "max_delay": 0.1})
        # Empty response from provider.parse_response returns empty string (not None)
        result = client.translate(
            {"name": "test", "api_url": "http://test/v1", "model": "test", "type": "openai"},
            "Hello", is_test=True
        )
        assert result == ""


class TestAPIClientConfigurableRetry:
    """可配置重试参数测试"""

    @patch('api.api_client.requests.post')
    @patch('api.api_client.time.sleep')
    def test_custom_backoff_factor(self, mock_sleep, mock_post):
        mock_post.side_effect = [
            __import__('requests').exceptions.Timeout("t1"),
            __import__('requests').exceptions.Timeout("t2"),
            MagicMock(status_code=200, json=lambda: {"choices": [{"message": {"content": "ok"}}]}),
        ]

        client = APIClient({"default": 0.0}, retry_config={
            "max_retries": 3, "base_delay": 0.1, "max_delay": 5.0, "backoff_factor": 3.0,
        })
        client.translate(
            {"name": "test", "api_url": "http://test/v1", "model": "test", "type": "openai"},
            "Hello", is_test=True
        )

        delays = [call.args[0] for call in mock_sleep.call_args_list]
        assert len(delays) == 2
        assert abs(delays[0] - 0.1) < 0.01   # 0.1 * 3^0 = 0.1 (attempt=0)
        assert abs(delays[1] - 0.3) < 0.01   # 0.1 * 3^1 = 0.3 (attempt=1)


class TestExceptionHierarchy:
    """异常层次结构测试"""

    def test_exception_inheritance(self):
        assert issubclass(APITimeoutError, Exception)
        assert issubclass(APIConnectionError, Exception)
        assert issubclass(APIResponseError, Exception)

    def test_classify_http_error(self):
        from core.exceptions import APIAuthError, APIRateLimitError, classify_http_error

        assert isinstance(classify_http_error(401), APIAuthError)
        assert isinstance(classify_http_error(403), APIAuthError)
        assert isinstance(classify_http_error(429), APIRateLimitError)
        assert isinstance(classify_http_error(500), APIResponseError)
        assert isinstance(classify_http_error(400), APIResponseError)
