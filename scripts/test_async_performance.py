#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
异步翻译性能测试脚本

对比同步和异步翻译模式的性能差异：
- 启动时间
- 内存占用
- 翻译速度
- 吞吐量
"""

import asyncio
import os
import sys
import time
import tracemalloc
from typing import Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.api_manager import APIManager
from config.config_manager import ConfigManager
from core.log_manager import get_logger
from core.translator import Translator

logger = get_logger(__name__)


class TranslationPerformanceTest:
    """翻译性能测试类"""

    def __init__(self):
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load_config()
        self.api_manager = None
        self.translator = None

    def setup(self):
        """初始化测试环境"""
        print("=" * 60)
        print("翻译性能测试")
        print("=" * 60)

        print("\n📦 初始化测试环境...")
        self.api_manager = APIManager(self.config)
        self.translator = Translator(self.api_manager, self.config)

        apis = self.api_manager.detect_available_apis()
        if not apis:
            print("❌ 未检测到可用API，无法进行测试")
            return False

        print(f"✅ 检测到 {len(apis)} 个可用API")
        for api in apis:
            print(f"   - {api.get('name', 'Unknown')}: {api.get('type', 'Unknown')}")

        return True

    def generate_test_data(self, count: int = 100) -> Dict[str, str]:
        """生成测试数据"""
        print(f"\n📝 生成 {count} 条测试数据...")

        test_entries = {}
        for i in range(count):
            key = f"test.entry.{i}"
            value = f"This is test entry number {i} for translation performance testing."
            test_entries[key] = value

        print(f"✅ 已生成 {len(test_entries)} 条测试数据")
        return test_entries

    def test_sync_translation(self, entries: Dict[str, str]) -> Dict[str, float]:
        """测试同步翻译性能"""
        print("\n🔄 测试同步翻译模式...")

        tracemalloc.start()
        start_time = time.time()

        translated = self.translator.translate_entries(
            entries,
            progress_callback=lambda p, r, t: None,
            log_callback=lambda msg: None
        )

        end_time = time.time()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        elapsed = end_time - start_time
        throughput = len(entries) / elapsed if elapsed > 0 else 0

        results = {
            'mode': '同步模式',
            'entries': len(entries),
            'translated': len(translated),
            'elapsed': elapsed,
            'throughput': throughput,
            'memory_mb': peak / 1024 / 1024
        }

        print("✅ 同步翻译完成")
        print(f"   - 翻译条目: {results['translated']}/{results['entries']}")
        print(f"   - 耗时: {results['elapsed']:.2f} 秒")
        print(f"   - 吞吐量: {results['throughput']:.2f} 条/秒")
        print(f"   - 内存峰值: {results['memory_mb']:.2f} MB")

        return results

    async def test_async_translation(self, entries: Dict[str, str]) -> Dict[str, float]:
        """测试异步翻译性能"""
        print("\n⚡ 测试异步翻译模式...")

        if not hasattr(self.api_manager, 'async_api_client') or not self.api_manager.async_api_client:
            print("⚠️ 异步API客户端不可用，跳过异步测试")
            return None

        tracemalloc.start()
        start_time = time.time()

        translated = await self.translator.translate_entries_async(
            entries,
            progress_callback=lambda p, r, t: None,
            log_callback=lambda msg: None
        )

        end_time = time.time()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        elapsed = end_time - start_time
        throughput = len(entries) / elapsed if elapsed > 0 else 0

        results = {
            'mode': '异步模式',
            'entries': len(entries),
            'translated': len(translated),
            'elapsed': elapsed,
            'throughput': throughput,
            'memory_mb': peak / 1024 / 1024
        }

        print("✅ 异步翻译完成")
        print(f"   - 翻译条目: {results['translated']}/{results['entries']}")
        print(f"   - 耗时: {results['elapsed']:.2f} 秒")
        print(f"   - 吞吐量: {results['throughput']:.2f} 条/秒")
        print(f"   - 内存峰值: {results['memory_mb']:.2f} MB")

        return results

    def compare_results(self, sync_results: Dict, async_results: Dict):
        """对比测试结果"""
        print("\n" + "=" * 60)
        print("📊 性能对比结果")
        print("=" * 60)

        if not sync_results or not async_results:
            print("⚠️ 测试结果不完整，无法对比")
            return

        print(f"\n{'指标':<20} {'同步模式':<20} {'异步模式':<20} {'提升':<20}")
        print("-" * 80)

        speedup = sync_results['elapsed'] / async_results['elapsed'] if async_results['elapsed'] > 0 else 0
        print(f"{'耗时 (秒)':<20} {sync_results['elapsed']:<20.2f} {async_results['elapsed']:<20.2f} {speedup:<20.2f}x")

        throughput_improvement = (async_results['throughput'] / sync_results['throughput'] - 1) * 100 if sync_results['throughput'] > 0 else 0
        print(f"{'吞吐量 (条/秒)':<20} {sync_results['throughput']:<20.2f} {async_results['throughput']:<20.2f} {throughput_improvement:<19.1f}%")

        memory_reduction = (1 - async_results['memory_mb'] / sync_results['memory_mb']) * 100 if sync_results['memory_mb'] > 0 else 0
        print(f"{'内存峰值 (MB)':<20} {sync_results['memory_mb']:<20.2f} {async_results['memory_mb']:<20.2f} {memory_reduction:<19.1f}%")

        print("\n✨ 结论:")
        if speedup > 1.2:
            print(f"   🚀 异步模式显著更快，性能提升 {(speedup - 1) * 100:.1f}%")
        elif speedup > 1.0:
            print(f"   ✅ 异步模式略快，性能提升 {(speedup - 1) * 100:.1f}%")
        else:
            print("   ℹ️  同步模式更快，建议使用同步模式")

        if memory_reduction > 20:
            print(f"   💾 异步模式内存占用显著降低 {memory_reduction:.1f}%")
        elif memory_reduction > 0:
            print(f"   💾 异步模式内存占用略低 {memory_reduction:.1f}%")

    def run_tests(self, test_sizes: List[int] = [10, 50, 100]):
        """运行性能测试"""
        if not self.setup():
            return

        print("\n" + "=" * 60)
        print("开始性能测试")
        print("=" * 60)

        for size in test_sizes:
            print(f"\n{'='*60}")
            print(f"测试规模: {size} 条条目")
            print(f"{'='*60}")

            entries = self.generate_test_data(size)

            sync_results = self.test_sync_translation(entries)

            async_results = asyncio.run(self.test_async_translation(entries))

            self.compare_results(sync_results, async_results)

        print("\n" + "=" * 60)
        print("性能测试完成")
        print("=" * 60)


def main():
    """主函数"""
    test = TranslationPerformanceTest()
    test.run_tests(test_sizes=[10, 50])


if __name__ == "__main__":
    main()
