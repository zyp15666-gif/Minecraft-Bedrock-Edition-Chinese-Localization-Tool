#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
APIManager 单元测试

测试API管理器的核心功能，包括：
- API列表构建
- 负载均衡
- 批量翻译
- 统计更新

注意：此测试使用 monkeypatch 隔离依赖，不会污染全局 sys.modules。
"""

import pytest
import json
import time
import types
from unittest.mock import Mock, patch, MagicMock, call
import sys
from pathlib import Path


# ──────────── 辅助函数 ────────────

def _mock_api_modules(monkeypatch):
    """使用 monkeypatch 安全地 Mock 依赖模块，自动清理"""
    mock_logger = Mock()
    mock_logger_instance = Mock()

    # 注册 mock 模块
    mock_modules = {
        'core.quality_checker': Mock(),
        'core.log_manager': Mock(),
        'core.utils': Mock(),
        'api.translation_prompts': Mock(),
        'api.api_client': Mock(),
        'api.translation_cache': Mock(),
        'api.api_monitor': Mock(),
        'api.terminology_service': Mock(),
    }

    # api.interfaces 需要特殊处理：提供 ITranslationEngine
    interfaces_mod = types.ModuleType('api.interfaces')
    interfaces_mod.ITranslationEngine = object
    mock_modules['api.interfaces'] = interfaces_mod

    # 使用真实的 LoadBalancer（不 mock）
    from api.load_balancer import LoadBalancer
    load_balancer_mod = types.ModuleType('api.load_balancer')
    load_balancer_mod.LoadBalancer = LoadBalancer
    mock_modules['api.load_balancer'] = load_balancer_mod

    # 设置 logger
    mock_modules['core.log_manager'].get_logger.return_value = mock_logger_instance

    # 注册所有 mock 到 sys.modules
    for name, mod in mock_modules.items():
        monkeypatch.setitem(sys.modules, name, mod)

    return mock_modules, mock_logger_instance


def _create_apimanager(config=None, monkeypatch=None):
    """创建 APIManager 实例（自动处理依赖 Mock）"""
    if monkeypatch:
        _mock_api_modules(monkeypatch)

    from api.api_manager import APIManager
    if config is None:
        config = {"basic": {}}
    return APIManager(config)


# ──────────── 测试类 ────────────

class TestAPIManagerInit:
    """APIManager 初始化测试"""

    def test_init_with_default_config(self, monkeypatch):
        """测试使用默认配置初始化"""
        api_mgr = _create_apimanager({"basic": {}}, monkeypatch)
        assert api_mgr.config == {"basic": {}}
        assert api_mgr.available_apis == []
        assert api_mgr.max_threads_per_api == 3

    def test_init_with_custom_config(self, monkeypatch):
        """测试使用自定义配置初始化"""
        config = {
            "basic": {
                "max_threads_per_api": 5,
                "cache_max_size": 1000
            },
            "rate_limit": {"default": 0.2}
        }
        api_mgr = _create_apimanager(config, monkeypatch)
        assert api_mgr.max_threads_per_api == 5
        assert api_mgr.rate_limit_delay == {"default": 0.2}


class TestAPIManagerBuildApiList:
    """API列表构建测试"""

    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch):
        _mock_api_modules(monkeypatch)

    def test_build_api_list_empty(self):
        config = {"basic": {}}
        from api.api_manager import APIManager
        api_mgr = APIManager(config)
        apis = api_mgr.build_api_list()
        assert apis == []

    def test_build_api_list_with_local_ollama(self):
        config = {
            "basic": {},
            "local_ollama": [
                {"name": "Local Ollama", "api_url": "http://localhost:11434/v1/chat/completions", "model": "qwen2.5", "enabled": True, "priority": 1}
            ]
        }
        from api.api_manager import APIManager
        api_mgr = APIManager(config)
        apis = api_mgr.build_api_list()
        assert len(apis) == 1
        assert apis[0]["name"] == "Local Ollama"
        assert apis[0]["type"] == "local_ollama"

    def test_build_api_list_type_inference(self):
        config = {
            "basic": {},
            "deepseek": [
                {"name": "DeepSeek", "api_url": "https://api.deepseek.com/v1/chat/completions", "api_key": "sk-test", "model": "deepseek-chat", "enabled": True}
            ],
            "zhipu": [
                {"name": "智谱", "api_url": "https://open.bigmodel.cn/api/paas/v4/chat/completions", "api_key": "test-key", "model": "glm-4", "enabled": True}
            ],
            "doubao": [
                {"name": "豆包", "api_url": "https://ark.cn-beijing.volces.com/api/v3/chat/completions", "api_key": "test-key", "model": "doubao-1.5-pro", "enabled": True}
            ]
        }
        from api.api_manager import APIManager
        api_mgr = APIManager(config)
        apis = api_mgr.build_api_list()
        type_map = {api["name"]: api["type"] for api in apis}
        assert type_map["DeepSeek"] == "openai_compatible"
        assert type_map["智谱"] == "zhipu"
        assert type_map["豆包"] == "doubao"

    def test_build_api_list_priority_sorting(self):
        config = {
            "basic": {},
            "deepseek": [
                {"name": "API-B", "api_url": "https://api.test.com/v1", "api_key": "sk-test", "model": "test", "enabled": True, "priority": 10},
                {"name": "API-A", "api_url": "https://api.test.com/v1", "api_key": "sk-test", "model": "test", "enabled": True, "priority": 1}
            ]
        }
        from api.api_manager import APIManager
        api_mgr = APIManager(config)
        apis = api_mgr.build_api_list()
        assert len(apis) == 2
        assert apis[0]["name"] == "API-A"
        assert apis[1]["name"] == "API-B"

    def test_build_api_list_disabled_filter(self):
        config = {
            "basic": {},
            "deepseek": [
                {"name": "Enabled API", "api_url": "https://api.test.com/v1", "api_key": "sk-test", "model": "test", "enabled": True},
                {"name": "Disabled API", "api_url": "https://api.test.com/v1", "api_key": "sk-test", "model": "test", "enabled": False}
            ]
        }
        from api.api_manager import APIManager
        api_mgr = APIManager(config)
        apis = api_mgr.build_api_list()
        assert len(apis) == 1
        assert apis[0]["name"] == "Enabled API"

    def test_build_api_list_not_list_skipped(self):
        config = {"basic": {}, "deepseek": "not_a_list"}
        from api.api_manager import APIManager
        api_mgr = APIManager(config)
        apis = api_mgr.build_api_list()
        assert apis == []


class TestAPIManagerGetNextApi:
    """get_next_api 测试"""

    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch):
        _mock_api_modules(monkeypatch)

    def test_get_next_api_no_apis(self):
        from api.api_manager import APIManager
        api_mgr = APIManager({"basic": {}})
        api = api_mgr.get_next_api()
        assert api is None

    def test_get_next_api_single_api(self):
        from api.api_manager import APIManager
        api_mgr = APIManager({"basic": {}})
        test_api = {"name": "Test API", "type": "openai_compatible"}
        api_mgr.available_apis = [test_api]
        api_mgr.api_orchestrator = None
        api = api_mgr.get_next_api()
        assert api == test_api


class TestAPIManagerTranslate:
    """翻译功能测试"""

    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch):
        _mock_api_modules(monkeypatch)

    def test_translate_text_no_apis(self):
        from api.api_manager import APIManager
        api_mgr = APIManager({"basic": {}})
        result = api_mgr.translate_text("Hello")
        assert result == "Hello"

    def test_is_available_false(self):
        from api.api_manager import APIManager
        api_mgr = APIManager({"basic": {}})
        assert not api_mgr.is_available()

    def test_is_available_true(self):
        from api.api_manager import APIManager
        api_mgr = APIManager({"basic": {}})
        api_mgr.available_apis = [{"name": "Test"}]
        assert api_mgr.is_available()

    def test_get_available_apis(self):
        from api.api_manager import APIManager
        api_mgr = APIManager({"basic": {}})
        apis = [{"name": "Test1"}, {"name": "Test2"}]
        api_mgr.available_apis = apis
        result = api_mgr.get_available_apis()
        assert result == apis
        result.append({"name": "Test3"})
        assert len(api_mgr.available_apis) == 2


class TestAPIManagerStats:
    """统计功能测试"""

    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch):
        _mock_api_modules(monkeypatch)

    def test_get_api_stats_empty(self):
        from api.api_manager import APIManager
        api_mgr = APIManager({"basic": {}})
        stats = api_mgr.get_api_stats()
        assert stats["available"] == 0
        assert "monitor_summary" in stats
        assert "cache_stats" in stats

    def test_reset_stats(self):
        from api.api_manager import APIManager
        api_mgr = APIManager({"basic": {}})
        api_mgr.term_service.terms = {}
        api_mgr.api_error_logs.append({"test": "error"})
        api_mgr.reset_stats()
        assert len(api_mgr.api_error_logs) == 0
        assert len(api_mgr.api_alerts) == 0


class TestAPIManagerUpdateApiStats:
    """update_api_stats 测试"""

    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch):
        _mock_api_modules(monkeypatch)

    def test_update_api_stats_success(self):
        from api.api_manager import APIManager
        api_mgr = APIManager({"basic": {}})
        api_mgr.update_api_stats("test_api", success=True, response_time=0.5)
        assert len(api_mgr.api_error_logs) == 0

    def test_update_api_stats_failure(self):
        from api.api_manager import APIManager
        api_mgr = APIManager({"basic": {}})
        api_mgr.update_api_stats("test_api", success=False, response_time=1.0,
                                  error_type="timeout", error_message="连接超时")
        assert len(api_mgr.api_error_logs) == 1
        assert api_mgr.api_error_logs[0]["error_type"] == "timeout"
        assert api_mgr.api_error_logs[0]["api_name"] == "test_api"


class TestAPIManagerMultiApiTranslate:
    """multi_api_translate 测试"""

    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch):
        _mock_api_modules(monkeypatch)

    def test_multi_api_translate_empty_text(self):
        from api.api_manager import APIManager
        api_mgr = APIManager({"basic": {}})
        result = api_mgr.multi_api_translate("")
        assert result == ""

    def test_multi_api_translate_no_apis(self):
        from api.api_manager import APIManager
        api_mgr = APIManager({"basic": {}})
        result = api_mgr.multi_api_translate("Hello")
        assert result == "Hello"


class TestAPIManagerThreadSafety:
    """线程安全测试"""

    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch):
        _mock_api_modules(monkeypatch)

    def test_get_next_api_thread_safety(self):
        import threading
        from api.api_manager import APIManager

        api_mgr = APIManager({"basic": {}})
        api_mgr.available_apis = [
            {"name": f"API-{i}", "type": "openai_compatible"}
            for i in range(3)
        ]
        api_mgr.api_orchestrator = None

        results = []
        errors = []

        def get_api():
            try:
                api = api_mgr.get_next_api()
                if api:
                    results.append(api["name"])
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=get_api) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) > 0

    def test_api_active_threads_count(self):
        from api.api_manager import APIManager
        api_mgr = APIManager({"basic": {"max_threads_per_api": 2}})
        api_mgr.available_apis = [{"name": "Test-API", "type": "openai_compatible"}]
        api_mgr.api_orchestrator = None

        api = api_mgr.get_next_api()
        assert api is not None
        assert api_mgr.api_active_threads["Test-API"] == 1

        api_mgr._release_api_thread(api, is_test=False)
        assert api_mgr.api_active_threads["Test-API"] == 0
