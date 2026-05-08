"""
API 客户端集成测试 — 单次请求语义（重试由 APIManager + unified_retry 处理）
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from api.api_client import APIClient
from core.exceptions import (
    APIConnectionError,
    APIResponseError,
    APITimeoutError,
)


class TestAPIClientSingleCall:
    """APIClient.translate 不做内部重试"""

    @patch("api.api_client.requests.post")
    def test_success_returns_translation(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"choices": [{"message": {"content": "你好"}}]}
        mock_resp.raise_for_status = Mock()
        mock_post.return_value = mock_resp

        client = APIClient({"default": 0.0}, retry_config={"max_retries": 3})
        result = client.translate(
            {"name": "test", "api_url": "http://test/v1", "model": "test", "type": "openai"},
            "Hello",
            is_test=True,
        )
        assert result == "你好"
        assert mock_post.call_count == 1

    @patch("api.api_client.requests.post")
    def test_timeout_propagates(self, mock_post):
        import requests

        mock_post.side_effect = requests.exceptions.Timeout("timeout")
        client = APIClient({"default": 0.0}, retry_config={"max_retries": 3})
        with pytest.raises(requests.exceptions.Timeout):
            client.translate(
                {"name": "test", "api_url": "http://test/v1", "model": "test", "type": "openai"},
                "Hello",
                is_test=True,
            )

    @patch("api.api_client.requests.post")
    def test_connection_error_propagates(self, mock_post):
        import requests

        mock_post.side_effect = requests.exceptions.ConnectionError("refused")
        client = APIClient({"default": 0.0}, retry_config={"max_retries": 3})
        with pytest.raises(requests.exceptions.ConnectionError):
            client.translate(
                {"name": "test", "api_url": "http://test/v1", "model": "test", "type": "openai"},
                "Hello",
                is_test=True,
            )

    @patch("api.api_client.requests.post")
    def test_empty_parse_returns_empty_string(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {}
        mock_resp.raise_for_status = Mock()
        mock_post.return_value = mock_resp

        client = APIClient({"default": 0.0}, retry_config={"max_retries": 1})
        result = client.translate(
            {"name": "test", "api_url": "http://test/v1", "model": "test", "type": "openai"},
            "Hello",
            is_test=True,
        )
        assert result == ""


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
