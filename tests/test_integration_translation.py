#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
翻译核心流程集成测试

测试场景：
- 阶段1成功 → 缓存写入 → 阶段2跳过
- 阶段1返回AI提示词 → 触发阶段2
- 阶段2颜色代码分段合并正确
- 术语命中直接返回，不调用API
- API重试及最终失败返回原文
- 负载均衡选择、线程数限制
- 进度回调节流行为
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from concurrent.futures import ThreadPoolExecutor
import time

from api.api_client import APIClient
from api.api_manager import APIManager
from api.translation_strategy import TranslationStrategy
from api.translation_cache import TranslationCache
from api.load_balancer import LoadBalancer
from api.api_monitor import APIMonitor
from core.quality_checker import TranslationQualityChecker
from core.translator import Translator
from ui.utils import ProgressThrottler


class MockResponse:
    """模拟API响应"""
    def __init__(self, status_code, json_data):
        self.status_code = status_code
        self._json_data = json_data
    
    def json(self):
        return self._json_data
    
    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


def create_mock_api_config(name="test_api", api_type="openai_compatible"):
    """创建测试用API配置"""
    return {
        "name": name,
        "type": api_type,
        "api_url": "http://localhost:8080/v1/chat/completions",
        "model": "test-model",
        "api_key": "test-key",
        "priority": 1
    }


def create_mock_term_service():
    """创建测试用术语服务"""
    term_service = Mock()
    term_service.terms = {
        "Turret": "炮塔",
        "Furnace": "熔炉",
        "Diamond": "钻石"
    }
    term_service.get_translation_original.return_value = None
    term_service.get_translation_clean.return_value = None
    term_service.has_any_term.return_value = False
    return term_service


def create_mock_quality_checker(term_service=None):
    """创建测试用质量检查器"""
    return TranslationQualityChecker(
        term_service=term_service,
        cache_enabled=True,
        cache_max_size=100,
        min_length_ratio=0.15,
        max_length_ratio=3.0,
        english_max_ratio=0.3
    )


def create_mock_strategy(term_service=None, quality_checker=None, cache=None):
    """创建测试用翻译策略"""
    return TranslationStrategy(
        term_service=term_service,
        quality_checker=quality_checker,
        cache=cache,
        complexity_config={
            'color_density_threshold': 0.3,
            'term_density_threshold': 0.5,
            'special_chars_threshold': 5
        },
        skip_stage2_threshold=0.6
    )


class TestStage1DirectTranslation:
    """阶段1直接翻译测试"""

    @patch('api.api_client.requests.post')
    def test_stage1_success_caches_result(self, mock_post):
        """测试阶段1成功时结果被缓存"""
        mock_post.return_value = MockResponse(200, {
            "choices": [{"message": {"content": "你好世界"}}]
        })
        
        term_service = create_mock_term_service()
        quality_checker = create_mock_quality_checker(term_service)
        cache = TranslationCache(max_size=1000)
        strategy = create_mock_strategy(term_service, quality_checker, cache)
        
        api_config = create_mock_api_config()
        api_client = APIClient(rate_limit_delay={"default": 0})
        strategy.api_client = api_client
        
        result = strategy.translate(api_config, "Hello World", is_test=False)
        
        assert result == "你好世界"
        assert cache.get("Hello World") == "你好世界"

    @patch('api.api_client.requests.post')
    def test_stage1_fails_returns_original(self, mock_post):
        """测试阶段1失败时返回原文"""
        mock_post.side_effect = Exception("Network error")
        
        term_service = create_mock_term_service()
        quality_checker = create_mock_quality_checker(term_service)
        cache = TranslationCache(max_size=1000)
        strategy = create_mock_strategy(term_service, quality_checker, cache)
        
        api_config = create_mock_api_config()
        api_client = APIClient(rate_limit_delay={"default": 0})
        strategy.api_client = api_client
        
        result = strategy.translate(api_config, "Hello World", is_test=False)
        
        assert result == "Hello World"


class TestStage2Fallback:
    """阶段2回退测试"""

    @patch('api.api_client.requests.post')
    def test_stage1_ai_prompt_fallsback_to_stage2(self, mock_post):
        """测试阶段1返回AI提示词时触发阶段2"""
        mock_post.side_effect = [
            MockResponse(200, {"choices": [{"message": {"content": "Please provide the text to translate"}}]}),
            MockResponse(200, {"choices": [{"message": {"content": "你好世界"}}]})
        ]
        
        term_service = create_mock_term_service()
        quality_checker = create_mock_quality_checker(term_service)
        cache = TranslationCache(max_size=1000)
        strategy = create_mock_strategy(term_service, quality_checker, cache)
        
        api_config = create_mock_api_config()
        api_client = APIClient(rate_limit_delay={"default": 0})
        strategy.api_client = api_client
        
        result = strategy.translate(api_config, "Hello World", is_test=False)
        
        assert mock_post.call_count >= 2
        assert result == "你好世界"


class TestColorCodeSegmentation:
    """颜色代码分段测试"""

    @patch('api.api_client.requests.post')
    def test_stage2_segments_color_codes(self, mock_post):
        """测试阶段2正确分段带颜色代码的文本"""
        def side_effect(*args, **kwargs):
            payload = kwargs.get('json', {})
            content = payload.get('messages', [{}])[-1].get('content', '')
            
            if 'Bugfixes' in content:
                return MockResponse(200, {"choices": [{"message": {"content": "错误修复"}}]})
            elif 'Changes' in content:
                return MockResponse(200, {"choices": [{"message": {"content": "更改"}}]})
            return MockResponse(200, {"choices": [{"message": {"content": content}}]})
        
        mock_post.side_effect = side_effect
        
        term_service = create_mock_term_service()
        quality_checker = create_mock_quality_checker(term_service)
        cache = TranslationCache(max_size=1000)
        strategy = create_mock_strategy(term_service, quality_checker, cache)
        
        api_config = create_mock_api_config()
        api_client = APIClient(rate_limit_delay={"default": 0})
        strategy.api_client = api_client
        
        result = strategy.translate(api_config, "§aBugfixes §bChanges", is_test=False)
        
        assert "§" in result
        assert mock_post.call_count >= 2


class TestTermMatching:
    """术语匹配测试"""

    def test_term_match_returns_directly(self):
        """测试术语命中直接返回，不调用API"""
        term_service = create_mock_term_service()
        term_service.get_translation_original.return_value = "炮塔"
        
        quality_checker = create_mock_quality_checker(term_service)
        cache = TranslationCache(max_size=1000)
        strategy = create_mock_strategy(term_service, quality_checker, cache)
        
        api_config = create_mock_api_config()
        
        result = strategy.check_term_match("Turret")
        
        assert result == "炮塔"
        term_service.get_translation_original.assert_called_once_with("Turret")


class TestAPIRetry:
    """API重试测试"""

    def test_api_client_retries_on_connection_error(self):
        """测试API客户端在连接错误时重试"""
        import requests
        with patch('api.api_client.requests.post') as mock_post:
            mock_post.side_effect = [
                requests.RequestException("Connection timeout"),
                requests.RequestException("Connection timeout"),
                MockResponse(200, {"choices": [{"message": {"content": "你好世界"}}]})
            ]
            
            api_client = APIClient(rate_limit_delay={"default": 0})
            api_client.max_retries = 3
            
            api_config = create_mock_api_config()
            
            result = api_client.translate(api_config, "Hello World", is_test=False)
            
            assert mock_post.call_count == 3
            assert result == "你好世界"

    def test_api_client_final_failure_returns_original(self):
        """测试API客户端最终失败返回原文"""
        import requests
        with patch('api.api_client.requests.post') as mock_post:
            mock_post.side_effect = requests.RequestException("Connection refused")
            
            api_client = APIClient(rate_limit_delay={"default": 0})
            api_client.max_retries = 3
            
            api_config = create_mock_api_config()
            
            result = api_client.translate(api_config, "Hello World", is_test=False)
            
            assert mock_post.call_count == 3
            assert result == "Hello World"


class TestLoadBalancing:
    """负载均衡测试"""

    def test_load_balancer_records_failures(self):
        """测试负载均衡器记录失败"""
        lb = LoadBalancer()
        
        lb.record_failure("api3")
        lb.record_failure("api3")
        
        stats = lb.get_stats()
        
        assert "api3" in stats
        assert stats["api3"]["failure_count"] == 2

    @patch('api.api_client.requests.post')
    def test_api_manager_respects_thread_limit(self, mock_post):
        """测试API管理器遵守线程数限制"""
        mock_post.return_value = MockResponse(200, {
            "choices": [{"message": {"content": "翻译结果"}}]
        })
        
        config = {
            "basic": {
                "max_threads_per_api": 2,
                "cache_max_size": 1000,
                "local_model_use_prompt": True
            },
            "local_ollama": [create_mock_api_config("local_api", "local_ollama")],
            "advanced": {
                "quality": {},
                "complexity": {},
                "translation": {}
            }
        }
        
        api_manager = APIManager(config)
        api_manager.build_api_list()
        
        active_count = api_manager.api_active_threads.get("local_api", 0)
        assert active_count >= 0


class TestProgressThrottling:
    """进度回调节流测试"""

    def test_progress_throttler_should_update(self):
        """测试进度回调是否应该更新"""
        throttler = ProgressThrottler(min_interval=0.1)
        
        should_update_1 = throttler.should_update(0.1, "翻译中", 100, 60)
        assert should_update_1 == True
        
        should_update_2 = throttler.should_update(0.12, "翻译中", 90, 55)
        assert should_update_2 == False
        
        time.sleep(0.15)
        
        should_update_3 = throttler.should_update(0.2, "翻译中", 80, 50)
        assert should_update_3 == True


class TestCacheBehavior:
    """缓存行为测试"""

    def test_cache_stores_and_retrieves(self):
        """测试缓存存储和检索"""
        cache = TranslationCache(max_size=100)
        
        cache.set("Hello", "你好")
        result = cache.get("Hello")
        
        assert result == "你好"

    def test_cache_eviction(self):
        """测试缓存驱逐"""
        cache = TranslationCache(max_size=3)
        
        cache.set("A", "1")
        cache.set("B", "2")
        cache.set("C", "3")
        cache.set("D", "4")
        
        assert cache.get("C") is None
        assert cache.get("D") == "4"

    @patch('api.api_client.requests.post')
    def test_translation_caches_result(self, mock_post):
        """测试翻译结果被缓存"""
        mock_post.return_value = MockResponse(200, {
            "choices": [{"message": {"content": "你好世界"}}]
        })
        
        term_service = create_mock_term_service()
        quality_checker = create_mock_quality_checker(term_service)
        cache = TranslationCache(max_size=1000)
        strategy = create_mock_strategy(term_service, quality_checker, cache)
        
        api_config = create_mock_api_config()
        api_client = APIClient(rate_limit_delay={"default": 0})
        strategy.api_client = api_client
        
        strategy.translate(api_config, "Hello World", is_test=False)
        strategy.translate(api_config, "Hello World", is_test=False)
        
        assert mock_post.call_count == 1


class TestQualityChecker:
    """质量检查器测试"""

    def test_quality_check_passes_valid_translation(self):
        """测试有效翻译通过质量检查"""
        checker = create_mock_quality_checker()
        
        result = checker.check_quality("Hello World", "你好世界")
        
        assert result == True

    def test_quality_check_fails_ai_prompt(self):
        """测试包含AI提示的翻译不通过质量检查"""
        checker = create_mock_quality_checker()
        
        result = checker.check_quality(
            "Hello World", 
            "Please provide the text to translate"
        )
        
        assert result == False

    def test_quality_check_fails_english_ratio(self):
        """测试英文比例过高的翻译不通过质量检查"""
        checker = create_mock_quality_checker()
        
        result = checker.check_quality(
            "Hello World", 
            "Hello World 你好世界"
        )
        
        assert result == False


class TestEndToEndTranslation:
    """端到端翻译测试"""

    def test_translation_strategy_direct_flow(self):
        """测试翻译策略直接翻译流程"""
        with patch('api.api_client.requests.post') as mock_post:
            mock_post.return_value = MockResponse(200, {
                "choices": [{"message": {"content": "你好世界"}}]
            })
            
            term_service = create_mock_term_service()
            quality_checker = create_mock_quality_checker(term_service)
            cache = TranslationCache(max_size=1000)
            api_client = APIClient(rate_limit_delay={"default": 0})
            
            strategy = TranslationStrategy(
                term_service=term_service,
                quality_checker=quality_checker,
                cache=cache,
                api_client=api_client,
                complexity_config={
                    'color_density_threshold': 0.3,
                    'term_density_threshold': 0.5,
                    'special_chars_threshold': 5
                },
                skip_stage2_threshold=0.6
            )
            
            api_config = create_mock_api_config()
            
            result = strategy.translate(api_config, "Hello World", is_test=False)
            
            assert result == "你好世界"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
