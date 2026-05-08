#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API模块化组件性能测试

对比新旧实现的性能差异：
- API选择性能
- 批量翻译性能
- 多API投票性能
- 内存占用
"""

import os
import statistics
import sys
import time
import tracemalloc

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.api_orchestrator import APIOrchestrator
from api.batch_translation_coordinator import BatchTranslationCoordinator
from api.multi_api_verifier import MultiAPIVerifier
from config.config_manager import ConfigManager
from core.log_manager import get_logger

logger = get_logger(__name__)


class APIPerformanceTest:
    """API模块化组件性能测试"""

    def __init__(self):
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load_config()

    def test_api_selection_performance(self, iterations: int = 1000):
        """测试API选择性能"""
        print("\n" + "=" * 60)
        print("API选择性能测试")
        print("=" * 60)

        orchestrator = APIOrchestrator(self.config)

        # 模拟API列表
        mock_apis = [
            {'name': f'api_{i}', 'type': 'openai', 'enabled': True}
            for i in range(5)
        ]
        orchestrator.available_apis = mock_apis

        # 性能测试
        start_time = time.time()
        for _ in range(iterations):
            orchestrator.get_next_api()
        end_time = time.time()

        elapsed = end_time - start_time
        avg_time = elapsed / iterations * 1000  # 毫秒

        print(f"✅ 完成 {iterations} 次API选择")
        print(f"   总耗时: {elapsed:.4f} 秒")
        print(f"   平均耗时: {avg_time:.4f} 毫秒/次")
        print(f"   吞吐量: {iterations/elapsed:.2f} 次/秒")

        return {
            'iterations': iterations,
            'elapsed': elapsed,
            'avg_time_ms': avg_time,
            'throughput': iterations/elapsed
        }

    def test_batch_translation_performance(self, text_count: int = 100):
        """测试批量翻译性能"""
        print("\n" + "=" * 60)
        print("批量翻译性能测试")
        print("=" * 60)

        coordinator = BatchTranslationCoordinator(self.config)

        # 生成测试数据
        test_texts = [
            f"This is test text number {i} for batch translation performance testing."
            for i in range(text_count)
        ]

        # 测试分批性能
        start_time = time.time()
        batches = coordinator._adaptive_batch_fragments(test_texts)
        end_time = time.time()

        elapsed = end_time - start_time

        print(f"✅ 完成 {text_count} 条文本的分批")
        print(f"   批次数: {len(batches)}")
        print(f"   平均批次大小: {statistics.mean(len(b) for b in batches):.1f}")
        print(f"   耗时: {elapsed*1000:.4f} 毫秒")

        return {
            'text_count': text_count,
            'batch_count': len(batches),
            'elapsed_ms': elapsed * 1000
        }

    def test_translation_quality_evaluation_performance(self, iterations: int = 1000):
        """测试翻译质量评估性能"""
        print("\n" + "=" * 60)
        print("翻译质量评估性能测试")
        print("=" * 60)

        verifier = MultiAPIVerifier(self.config)

        # 测试数据
        original = "This is a test sentence for quality evaluation performance testing."
        translation = "这是一个用于质量评估性能测试的测试句子。"

        # 性能测试
        start_time = time.time()
        for _ in range(iterations):
            verifier._evaluate_translation_quality(translation, original)
        end_time = time.time()

        elapsed = end_time - start_time
        avg_time = elapsed / iterations * 1000  # 毫秒

        print(f"✅ 完成 {iterations} 次质量评估")
        print(f"   总耗时: {elapsed:.4f} 秒")
        print(f"   平均耗时: {avg_time:.4f} 毫秒/次")
        print(f"   吞吐量: {iterations/elapsed:.2f} 次/秒")

        return {
            'iterations': iterations,
            'elapsed': elapsed,
            'avg_time_ms': avg_time,
            'throughput': iterations/elapsed
        }

    def test_memory_usage(self):
        """测试内存占用"""
        print("\n" + "=" * 60)
        print("内存占用测试")
        print("=" * 60)

        tracemalloc.start()

        # 创建组件
        APIOrchestrator(self.config)
        current, peak = tracemalloc.get_traced_memory()
        print(f"APIOrchestrator 内存占用: {peak / 1024:.2f} KB")

        BatchTranslationCoordinator(self.config)
        current, peak = tracemalloc.get_traced_memory()
        print(f"BatchTranslationCoordinator 内存占用: {peak / 1024:.2f} KB")

        MultiAPIVerifier(self.config)
        current, peak = tracemalloc.get_traced_memory()
        print(f"MultiAPIVerifier 内存占用: {peak / 1024:.2f} KB")

        tracemalloc.stop()

        return {
            'orchestrator_memory_kb': peak / 1024,
            'coordinator_memory_kb': peak / 1024,
            'verifier_memory_kb': peak / 1024
        }

    def run_all_tests(self):
        """运行所有性能测试"""
        print("=" * 60)
        print("API模块化组件性能测试套件")
        print("=" * 60)

        results = {}

        # API选择性能
        results['api_selection'] = self.test_api_selection_performance()

        # 批量翻译性能
        results['batch_translation'] = self.test_batch_translation_performance()

        # 质量评估性能
        results['quality_evaluation'] = self.test_translation_quality_evaluation_performance()

        # 内存占用
        results['memory_usage'] = self.test_memory_usage()

        # 总结
        print("\n" + "=" * 60)
        print("性能测试总结")
        print("=" * 60)

        print("\n✅ API选择性能:")
        print(f"   平均耗时: {results['api_selection']['avg_time_ms']:.4f} 毫秒")
        print(f"   吞吐量: {results['api_selection']['throughput']:.2f} 次/秒")

        print("\n✅ 批量翻译性能:")
        print(f"   批次数: {results['batch_translation']['batch_count']}")
        print(f"   耗时: {results['batch_translation']['elapsed_ms']:.4f} 毫秒")

        print("\n✅ 质量评估性能:")
        print(f"   平均耗时: {results['quality_evaluation']['avg_time_ms']:.4f} 毫秒")
        print(f"   吞吐量: {results['quality_evaluation']['throughput']:.2f} 次/秒")

        print("\n✅ 内存占用:")
        print(f"   总内存: {results['memory_usage']['orchestrator_memory_kb']:.2f} KB")

        return results


def main():
    """主函数"""
    test = APIPerformanceTest()
    test.run_all_tests()


if __name__ == "__main__":
    main()
