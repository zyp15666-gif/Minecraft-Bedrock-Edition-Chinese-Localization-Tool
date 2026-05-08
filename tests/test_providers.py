#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
api/providers 抽象提供商 单元测试
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from api.providers import (
    PROVIDER_REGISTRY,
    BaseProvider,
    OllamaProvider,
    OpenAICompatibleProvider,
    ZhipuProvider,
    get_provider,
    register_provider,
)


class TestOllamaProvider:
    @pytest.fixture
    def ollama_config(self):
        return {
            "name": "local-ollama",
            "type": "local_ollama",
            "api_url": "http://localhost:11434/api/chat",
            "model": "qwen2.5:7b",
            "temperature": 0.3,
        }

    def test_build_request(self, ollama_config):
        provider = OllamaProvider(ollama_config)
        url, headers, payload = provider.build_request("Hello", "Translate this")
        assert url == "http://localhost:11434/api/chat"
        assert "Content-Type" in headers
        assert payload["model"] == "qwen2.5:7b"
        assert payload["stream"] is False

    def test_parse_response(self, ollama_config):
        provider = OllamaProvider(ollama_config)
        result = provider.parse_response({"message": {"content": "你好"}})
        assert result == "你好"

    def test_validate_config(self, ollama_config):
        provider = OllamaProvider(ollama_config)
        assert provider.validate_config() is True

    def test_validate_config_missing_url(self):
        provider = OllamaProvider({"name": "test", "type": "local_ollama"})
        assert provider.validate_config() is False


class TestOpenAICompatibleProvider:
    @pytest.fixture
    def openai_config(self):
        return {
            "name": "deepseek-test",
            "type": "openai_compatible",
            "api_url": "https://api.deepseek.com/v1/chat/completions",
            "api_key": "sk-test123456789",
            "model": "deepseek-chat",
            "temperature": 0.3,
        }

    def test_build_request(self, openai_config):
        provider = OpenAICompatibleProvider(openai_config)
        url, headers, payload = provider.build_request("Hello", "Translate this")
        assert url == "https://api.deepseek.com/v1/chat/completions"
        assert "Authorization" in headers
        assert "Bearer" in headers["Authorization"]
        assert payload["model"] == "deepseek-chat"
        assert len(payload["messages"]) == 2

    def test_parse_response(self, openai_config):
        provider = OpenAICompatibleProvider(openai_config)
        result = provider.parse_response({
            "choices": [{"message": {"content": "你好"}}]
        })
        assert result == "你好"

    def test_validate_config(self, openai_config):
        provider = OpenAICompatibleProvider(openai_config)
        assert provider.validate_config() is True


class TestZhipuProvider:
    @pytest.fixture
    def zhipu_config(self):
        return {
            "name": "zhipu-test",
            "type": "zhipu",
            "api_url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
            "api_key": "zhipu-test-key",
            "model": "glm-4-flash",
            "temperature": 0.95,
        }

    def test_temperature_capped_at_1(self, zhipu_config):
        provider = ZhipuProvider(zhipu_config)
        _, _, payload = provider.build_request("Hello", "Translate")
        assert payload["temperature"] <= 1.0
        assert payload["do_sample"] is True


class TestGetProvider:
    def test_get_ollama_provider(self):
        config = {"type": "local_ollama", "name": "test", "api_url": "http://localhost:11434", "model": "test"}
        provider = get_provider(config)
        assert isinstance(provider, OllamaProvider)

    def test_get_openai_provider(self):
        config = {"type": "openai_compatible", "name": "test", "api_url": "http://api.test.com", "api_key": "key"}
        provider = get_provider(config)
        assert isinstance(provider, OpenAICompatibleProvider)

    def test_get_zhipu_provider(self):
        config = {"type": "zhipu", "name": "test", "api_url": "http://api.test.com", "api_key": "key"}
        provider = get_provider(config)
        assert isinstance(provider, ZhipuProvider)

    def test_unknown_type_fallback(self):
        config = {"type": "unknown_type", "name": "test", "api_url": "http://api.test.com", "api_key": "key"}
        provider = get_provider(config)
        assert isinstance(provider, OpenAICompatibleProvider)


class TestRegisterProvider:
    def test_register_custom_provider(self):
        class CustomProvider(BaseProvider):
            PROVIDER_TYPE = "custom"
            def build_request(self, text, system_prompt=None, is_test=False):
                return ("", {}, {})
            def parse_response(self, response_data):
                return ""

        register_provider("custom", CustomProvider)
        assert "custom" in PROVIDER_REGISTRY
        assert PROVIDER_REGISTRY["custom"] == CustomProvider

        del PROVIDER_REGISTRY["custom"]

    def test_register_invalid_class(self):
        with pytest.raises(TypeError):
            register_provider("invalid", str)
