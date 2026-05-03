#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API模块化组件单元测试

测试新创建的三个组件：
- APIOrchestrator
- BatchTranslationCoordinator
- MultiAPIVerifier
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from api.api_orchestrator import APIOrchestrator
from api.batch_translation_coordinator import BatchTranslationCoordinator
from api.multi_api_verifier import MultiAPIVerifier


class TestAPIOrchestrator:
    """APIOrchestrator单元测试"""

    @pytest.fixture
    def config(self):
        """测试配置"""
        return {
            'basic': {
                'max_threads_per_api': 3
            },
            'advanced': {
                'circuit_breaker': {
                    'failure_threshold': 5,
                    'recovery_timeout': 60
                }
            },
            'apis': [
                {'name': 'test_api_1', 'type': 'openai', 'enabled': True},
                {'name': 'test_api_2', 'type': 'ollama', 'enabled': True}
            ]
        }

    @pytest.fixture
    def orchestrator(self, config):
        """创建APIOrchestrator实例"""
        return APIOrchestrator(config)

    def test_init(self, orchestrator, config):
        """测试初始化"""
        assert orchestrator.config == config
        assert orchestrator.max_threads_per_api == 3
        assert orchestrator.circuit_breaker is not None
        assert orchestrator.load_balancer is not None

    def test_build_api_list(self, orchestrator):
        """测试构建API列表"""
        api_list = orchestrator.build_api_list()
        assert len(api_list) == 2
        assert api_list[0]['name'] == 'test_api_1'
        assert api_list[1]['name'] == 'test_api_2'

    def test_acquire_release_thread(self, orchestrator):
        """测试线程槽位获取和释放"""
        api_config = {'name': 'test_api'}
        
        # 获取线程槽位
        assert orchestrator.acquire_api_thread(api_config) is True
        assert orchestrator.api_active_threads['test_api'] == 1
        
        # 再次获取
        assert orchestrator.acquire_api_thread(api_config) is True
        assert orchestrator.api_active_threads['test_api'] == 2
        
        # 释放线程槽位
        orchestrator.release_api_thread(api_config)
        assert orchestrator.api_active_threads['test_api'] == 1

    def test_record_success_failure(self, orchestrator):
        """测试成功/失败记录"""
        orchestrator.record_success('test_api')
        orchestrator.record_failure('test_api')
        
        # 应该不会抛出异常
        assert True

    def test_get_api_stats(self, orchestrator):
        """测试获取API统计"""
        stats = orchestrator.get_api_stats()
        
        assert 'total_apis' in stats
        assert 'active_threads' in stats
        assert 'max_threads_per_api' in stats
        assert 'circuit_breaker_status' in stats


class TestBatchTranslationCoordinator:
    """BatchTranslationCoordinator单元测试"""

    @pytest.fixture
    def config(self):
        """测试配置"""
        return {
            'advanced': {
                'translation': {
                    'enable_adaptive_batch': True,
                    'max_batch_size': 10,
                    'min_batch_size': 2
                }
            }
        }

    @pytest.fixture
    def coordinator(self, config):
        """创建BatchTranslationCoordinator实例"""
        return BatchTranslationCoordinator(config)

    def test_init(self, coordinator, config):
        """测试初始化"""
        assert coordinator.config == config
        assert coordinator.enable_adaptive_batch is True
        assert coordinator.max_batch_size == 10

    def test_fixed_batch(self, coordinator):
        """测试固定大小分批"""
        items = ['a', 'b', 'c', 'd', 'e']
        batches = coordinator._fixed_batch(items, 2)
        
        assert len(batches) == 3
        assert batches[0] == ['a', 'b']
        assert batches[1] == ['c', 'd']
        assert batches[2] == ['e']

    def test_adaptive_batch_fragments(self, coordinator):
        """测试自适应分批"""
        texts = ['short', 'medium length text', 'very long text that should be in its own batch']
        batches = coordinator._adaptive_batch_fragments(texts)
        
        assert len(batches) >= 1
        assert all(isinstance(batch, list) for batch in batches)

    def test_robust_split_translated_text(self, coordinator):
        """测试鲁棒的文本拆分"""
        # 正常情况
        text = "翻译1 <<<SEP>>> 翻译2 <<<SEP>>> 翻译3"
        parts = coordinator._robust_split_translated_text(text, 3)
        assert len(parts) == 3
        
        # 分隔符不足
        text = "翻译1 <<<SEP>>> 翻译2"
        parts = coordinator._robust_split_translated_text(text, 3)
        assert len(parts) == 3


class TestMultiAPIVerifier:
    """MultiAPIVerifier单元测试"""

    @pytest.fixture
    def config(self):
        """测试配置"""
        return {
            'advanced': {
                'quality': {
                    'min_score_threshold': 0.6,
                    'enable_voting': True
                }
            }
        }

    @pytest.fixture
    def verifier(self, config):
        """创建MultiAPIVerifier实例"""
        return MultiAPIVerifier(config)

    def test_init(self, verifier, config):
        """测试初始化"""
        assert verifier.config == config
        assert verifier.min_score_threshold == 0.6
        assert verifier.enable_voting is True

    def test_evaluate_translation_quality(self, verifier):
        """测试翻译质量评估"""
        # 高质量翻译
        original = "This is a test sentence."
        translation = "这是一个测试句子。"
        score = verifier._evaluate_translation_quality(translation, original)
        assert score > 0.5
        
        # 低质量翻译（过多英文）
        translation = "This is 测试 sentence."
        score = verifier._evaluate_translation_quality(translation, original)
        assert score < 1.0

    def test_select_best_translation(self, verifier):
        """测试选择最佳翻译"""
        original = "Hello world"
        translations = [
            ('api1', '你好世界'),
            ('api2', '您好世界'),
            ('api3', '你好世界！')
        ]
        
        best = verifier._select_best_translation(original, translations)
        assert best is not None
        assert isinstance(best, str)

    def test_verify_translation(self, verifier):
        """测试翻译验证"""
        original = "This is a test."
        translation = "这是一个测试。"
        
        result = verifier.verify_translation(original, translation)
        
        assert 'original' in result
        assert 'translation' in result
        assert 'score' in result
        assert 'passed' in result
        assert 'issues' in result

    def test_identify_issues(self, verifier):
        """测试识别翻译问题"""
        # 正常翻译
        translation = "这是一个测试。"
        original = "This is a test."
        issues = verifier._identify_issues(translation, original)
        assert isinstance(issues, list)
        
        # 过多英文
        translation = "This is 测试。"
        issues = verifier._identify_issues(translation, original)
        assert 'excessive_english' in issues


class TestIntegration:
    """集成测试"""

    @pytest.fixture
    def full_config(self):
        """完整配置"""
        return {
            'basic': {
                'max_threads_per_api': 3
            },
            'advanced': {
                'circuit_breaker': {
                    'failure_threshold': 5,
                    'recovery_timeout': 60
                },
                'translation': {
                    'enable_adaptive_batch': True,
                    'max_batch_size': 10
                },
                'quality': {
                    'min_score_threshold': 0.6,
                    'enable_voting': True
                }
            }
        }

    def test_orchestrator_coordinator_integration(self, full_config):
        """测试Orchestrator和Coordinator集成"""
        orchestrator = APIOrchestrator(full_config)
        coordinator = BatchTranslationCoordinator(full_config)
        
        assert orchestrator is not None
        assert coordinator is not None

    def test_all_components_integration(self, full_config):
        """测试所有组件集成"""
        orchestrator = APIOrchestrator(full_config)
        coordinator = BatchTranslationCoordinator(full_config)
        verifier = MultiAPIVerifier(full_config)
        
        assert orchestrator is not None
        assert coordinator is not None
        assert verifier is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
