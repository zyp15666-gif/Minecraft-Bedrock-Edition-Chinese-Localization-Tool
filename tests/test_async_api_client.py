#!/usr/bin/env python3
import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from api.async_api_client import AIOHTTP_AVAILABLE, AsyncAPIClient


def run_async(coro):
    return asyncio.run(coro)


@pytest.mark.skipif(not AIOHTTP_AVAILABLE, reason="aiohttp not installed")
class TestAsyncAPIClientInit:
    def test_default_values(self):
        client = AsyncAPIClient(rate_limit_delay={"default": 0.15})
        assert client.max_retries == 3
        assert client.base_delay == 1.0
        assert client.max_delay == 10.0
        assert client._backoff_factor == 2

    def test_custom_retry_config(self):
        client = AsyncAPIClient(
            rate_limit_delay={"default": 0.1},
            retry_config={"max_retries": 5, "base_delay": 2.0, "max_delay": 30.0, "backoff_factor": 3}
        )
        assert client.max_retries == 5
        assert client.base_delay == 2.0
        assert client.max_delay == 30.0
        assert client._backoff_factor == 3


@pytest.mark.skipif(not AIOHTTP_AVAILABLE, reason="aiohttp not installed")
class TestTranslate:
    def test_empty_text_returns_unchanged(self):
        client = AsyncAPIClient(rate_limit_delay={"default": 0.0})
        result = run_async(client.translate({"name": "test"}, ""))
        assert result == ""

    def test_whitespace_text_returns_unchanged(self):
        client = AsyncAPIClient(rate_limit_delay={"default": 0.0})
        result = run_async(client.translate({"name": "test"}, "   "))
        assert result == "   "


@pytest.mark.skipif(not AIOHTTP_AVAILABLE, reason="aiohttp not installed")
class TestEnforceRateLimit:
    def test_no_delay_when_no_previous_call(self):
        client = AsyncAPIClient(rate_limit_delay={"default": 0.0})
        run_async(client._enforce_rate_limit("test_api"))
        assert "test_api" in client.last_call_time

    def test_ollama_uses_local_delay(self):
        client = AsyncAPIClient(rate_limit_delay={"local_ollama": 0.0, "default": 0.15})
        run_async(client._enforce_rate_limit("ollama_local"))
        assert "ollama_local" in client.last_call_time


@pytest.mark.skipif(not AIOHTTP_AVAILABLE, reason="aiohttp not installed")
class TestTestApiAvailability:
    def test_available_api(self):
        client = AsyncAPIClient(rate_limit_delay={"default": 0.0})
        with patch.object(client, "translate", new_callable=AsyncMock, return_value="你好世界"):
            result = run_async(client.test_api_availability({"name": "test"}))
        assert result is True

    def test_unavailable_api(self):
        client = AsyncAPIClient(rate_limit_delay={"default": 0.0})
        with patch.object(client, "translate", new_callable=AsyncMock, side_effect=Exception("fail")):
            result = run_async(client.test_api_availability({"name": "test"}))
        assert result is False

    def test_same_text_returned(self):
        client = AsyncAPIClient(rate_limit_delay={"default": 0.0})
        with patch.object(client, "translate", new_callable=AsyncMock, return_value="Hello, world!"):
            result = run_async(client.test_api_availability({"name": "test"}))
        assert result is False


@pytest.mark.skipif(not AIOHTTP_AVAILABLE, reason="aiohttp not installed")
class TestTranslateBatch:
    def test_batch_success(self):
        client = AsyncAPIClient(rate_limit_delay={"default": 0.0})
        with patch.object(client, "translate", new_callable=AsyncMock, return_value="翻译"):
            results = run_async(client.translate_batch(
                [{"name": "api1"}, {"name": "api2"}],
                ["text1", "text2"]
            ))
        assert len(results) == 2
        assert all(r == "翻译" for r in results)

    def test_batch_with_exception(self):
        client = AsyncAPIClient(rate_limit_delay={"default": 0.0})

        async def mock_translate(api_config, text, **kwargs):
            if text == "fail":
                raise ConnectionError("network error")
            return "翻译"

        with patch.object(client, "translate", side_effect=mock_translate):
            results = run_async(client.translate_batch(
                [{"name": "api1"}, {"name": "api2"}],
                ["ok", "fail"]
            ))
        assert results[0] == "翻译"
        assert results[1] is None


@pytest.mark.skipif(not AIOHTTP_AVAILABLE, reason="aiohttp not installed")
class TestGetProvider:
    def test_provider_cached(self):
        client = AsyncAPIClient(rate_limit_delay={"default": 0.0})
        mock_provider = Mock()
        with patch("api.async_api_client.get_provider", return_value=mock_provider):
            p1 = run_async(client._get_provider({"name": "test"}))
            p2 = run_async(client._get_provider({"name": "test"}))
        assert p1 is p2
