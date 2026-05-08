#!/usr/bin/env python3
from unittest.mock import Mock, patch

import requests

from api.api_detector import APIDetector


class TestAPIDetectorInit:
    def test_init_stores_config(self):
        config = {"local_ollama": []}
        detector = APIDetector(config)
        assert detector.config is config


class TestBuildApiList:
    def test_empty_config(self):
        detector = APIDetector({})
        result = detector.build_api_list()
        assert result == []

    def test_local_ollama_apis(self):
        config = {
            "local_ollama": [
                {"name": "ollama1", "model": "llama2", "api_url": "http://localhost:11434"},
            ]
        }
        detector = APIDetector(config)
        result = detector.build_api_list()
        assert len(result) == 1
        assert result[0]["type"] == "local_ollama"
        assert result[0]["name"] == "ollama1"

    def test_cloud_provider_apis(self):
        config = {
            "deepseek": [
                {"name": "ds1", "model": "deepseek-chat", "api_url": "https://api.deepseek.com/v1/chat/completions", "api_key": "sk-xxx"},
            ]
        }
        detector = APIDetector(config)
        result = detector.build_api_list()
        assert len(result) == 1
        assert result[0]["type"] == "openai_compatible"

    def test_zhipu_type(self):
        config = {
            "zhipu": [
                {"name": "zhipu1", "model": "glm-4", "api_url": "https://open.bigmodel.cn/api/paas/v4/chat/completions", "api_key": "xxx"},
            ]
        }
        detector = APIDetector(config)
        result = detector.build_api_list()
        assert result[0]["type"] == "zhipu"

    def test_doubao_type(self):
        config = {
            "doubao": [
                {"name": "doubao1", "model": "doubao-pro", "api_url": "https://ark.cn-beijing.volces.com/api/v3/chat/completions", "api_key": "xxx"},
            ]
        }
        detector = APIDetector(config)
        result = detector.build_api_list()
        assert result[0]["type"] == "doubao"

    def test_disabled_apis_filtered(self):
        config = {
            "deepseek": [
                {"name": "ds1", "model": "deepseek-chat", "api_url": "url", "api_key": "key", "enabled": True},
                {"name": "ds2", "model": "deepseek-chat", "api_url": "url", "api_key": "key", "enabled": False},
            ]
        }
        detector = APIDetector(config)
        result = detector.build_api_list()
        assert len(result) == 1
        assert result[0]["name"] == "ds1"

    def test_priority_sorting(self):
        config = {
            "deepseek": [
                {"name": "low", "model": "m", "api_url": "url", "api_key": "key", "priority": 10},
                {"name": "high", "model": "m", "api_url": "url", "api_key": "key", "priority": 1},
                {"name": "mid", "model": "m", "api_url": "url", "api_key": "key", "priority": 5},
            ]
        }
        detector = APIDetector(config)
        result = detector.build_api_list()
        assert [api["name"] for api in result] == ["high", "mid", "low"]

    def test_default_enabled_true(self):
        config = {
            "deepseek": [
                {"name": "ds1", "model": "m", "api_url": "url", "api_key": "key"},
            ]
        }
        detector = APIDetector(config)
        result = detector.build_api_list()
        assert len(result) == 1

    def test_deep_copy_prevents_mutation(self):
        config = {
            "deepseek": [
                {"name": "ds1", "model": "m", "api_url": "url", "api_key": "key"},
            ]
        }
        detector = APIDetector(config)
        result = detector.build_api_list()
        result[0]["name"] = "mutated"
        original = config["deepseek"][0]["name"]
        assert original == "ds1"

    def test_non_list_provider_skipped(self):
        config = {"deepseek": "not_a_list"}
        detector = APIDetector(config)
        result = detector.build_api_list()
        assert result == []

    def test_explicit_type_preserved(self):
        config = {
            "deepseek": [
                {"name": "ds1", "model": "m", "api_url": "url", "api_key": "key", "type": "custom_type"},
            ]
        }
        detector = APIDetector(config)
        result = detector.build_api_list()
        assert result[0]["type"] == "custom_type"


class TestTestSingle:
    def test_no_api_key_returns_none(self):
        detector = APIDetector({})
        api_config = {"name": "test", "model": "m", "api_url": "url"}
        result = detector.test_single(api_config)
        assert result is None

    def test_placeholder_key_returns_none(self):
        detector = APIDetector({})
        api_config = {"name": "test", "model": "m", "api_url": "url", "api_key": "你的API密钥"}
        result = detector.test_single(api_config)
        assert result is None

    def test_your_key_placeholder_returns_none(self):
        detector = APIDetector({})
        api_config = {"name": "test", "model": "m", "api_url": "url", "api_key": "your_key_here"}
        result = detector.test_single(api_config)
        assert result is None

    @patch("api.api_detector.requests.post")
    def test_http_200_returns_config(self, mock_post):
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        detector = APIDetector({})
        api_config = {"name": "test", "model": "m", "api_url": "https://api.test.com/v1/chat/completions", "api_key": "sk-valid-key"}
        result = detector.test_single(api_config)
        assert result is api_config

    @patch("api.api_detector.requests.post")
    def test_http_401_returns_config(self, mock_post):
        mock_resp = Mock()
        mock_resp.status_code = 401
        mock_post.return_value = mock_resp

        detector = APIDetector({})
        api_config = {"name": "test", "model": "m", "api_url": "https://api.test.com/v1/chat/completions", "api_key": "sk-valid-key"}
        result = detector.test_single(api_config)
        assert result is api_config

    @patch("api.api_detector.requests.post")
    def test_http_500_returns_none(self, mock_post):
        mock_resp = Mock()
        mock_resp.status_code = 500
        mock_post.return_value = mock_resp

        detector = APIDetector({})
        api_config = {"name": "test", "model": "m", "api_url": "https://api.test.com/v1/chat/completions", "api_key": "sk-valid-key"}
        result = detector.test_single(api_config)
        assert result is None

    @patch("api.api_detector.requests.post")
    def test_connection_error_returns_none(self, mock_post):
        mock_post.side_effect = requests.ConnectionError("timeout")

        detector = APIDetector({})
        api_config = {"name": "test", "model": "m", "api_url": "https://api.test.com/v1/chat/completions", "api_key": "sk-valid-key"}
        result = detector.test_single(api_config)
        assert result is None

    @patch("api.api_detector.requests.post")
    def test_no_api_url_returns_none(self, mock_post):
        detector = APIDetector({})
        api_config = {"name": "test", "model": "m", "api_key": "sk-valid-key"}
        result = detector.test_single(api_config)
        assert result is None
        mock_post.assert_not_called()


class TestDetectAvailable:
    @patch.object(APIDetector, "test_single", return_value=None)
    def test_no_apis_available(self, mock_test):
        config = {
            "deepseek": [
                {"name": "ds1", "model": "m", "api_url": "url", "api_key": "key"},
            ]
        }
        detector = APIDetector(config)
        result = detector.detect_available()
        assert result == []

    @patch.object(APIDetector, "test_single")
    def test_some_apis_available(self, mock_test):
        api1 = {"name": "ds1", "model": "m", "api_url": "url", "api_key": "key"}
        api2 = {"name": "ds2", "model": "m", "api_url": "url", "api_key": "key"}

        def side_effect(api_config):
            return api_config if api_config["name"] == "ds1" else None

        mock_test.side_effect = side_effect

        config = {
            "deepseek": [api1, api2]
        }
        detector = APIDetector(config)
        result = detector.detect_available()
        assert len(result) == 1
        assert result[0]["name"] == "ds1"

    def test_empty_config_returns_empty(self):
        detector = APIDetector({})
        result = detector.detect_available()
        assert result == []

    @patch.object(APIDetector, "test_single")
    def test_translate_hook_set(self, mock_test):
        mock_test.return_value = {"name": "test"}
        hook = Mock()

        config = {
            "deepseek": [
                {"name": "ds1", "model": "m", "api_url": "url", "api_key": "key"},
            ]
        }
        detector = APIDetector(config)
        detector.detect_available(translate_hook=hook)
        assert detector._translate_hook is hook


class TestTestLocalOllama:
    @patch("api.api_detector.requests.post")
    def test_delegates_to_http_connectivity(self, mock_post):
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        detector = APIDetector({})
        api_config = {"name": "ollama", "model": "llama2", "api_url": "http://localhost:11434", "api_key": ""}
        result = detector._test_local_ollama(api_config)
        assert result is api_config


class TestCallTranslate:
    def test_without_hook_returns_none(self):
        detector = APIDetector({})
        result = detector._call_translate({"name": "test"}, "hello")
        assert result is None

    def test_with_hook(self):
        detector = APIDetector({})
        hook = Mock(return_value="translated")
        detector._translate_hook = hook
        result = detector._call_translate({"name": "test"}, "hello")
        assert result == "translated"
        hook.assert_called_once_with({"name": "test"}, "hello", is_test=True)
