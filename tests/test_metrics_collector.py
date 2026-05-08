#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core/metrics_collector.py 单元测试
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import threading
import time

import pytest

from core.metrics_collector import MetricsCollector, get_metrics_collector


class TestMetricsCollector:
    """MetricsCollector 单元测试"""

    def setup_method(self):
        self.collector = MetricsCollector(buffer_size=10)

    def test_initialization(self):
        assert self.collector.buffer_size == 10
        assert self.collector._total_translated == 0
        assert self.collector._total_api_calls == 0
        assert self.collector._total_api_errors == 0

    def test_record_translation(self):
        self.collector.record_translation(count=10, elapsed=1.0)
        assert self.collector._total_translated == 10
        assert len(self.collector._translation_rate) == 1
        assert len(self.collector._timestamps) == 1

    def test_record_api_call_success(self):
        self.collector.record_api_call(response_time=0.5, success=True)
        assert self.collector._total_api_calls == 1
        assert self.collector._total_api_errors == 0
        assert len(self.collector._api_response_times) == 1

    def test_record_api_call_failure(self):
        self.collector.record_api_call(response_time=0.5, success=False)
        assert self.collector._total_api_calls == 1
        assert self.collector._total_api_errors == 1

    def test_record_translation_multiple(self):
        for i in range(15):
            self.collector.record_translation(count=1, elapsed=0.1)
        assert self.collector._total_translated == 15
        assert len(self.collector._translation_rate) == 10

    def test_record_memory(self):
        self.collector.record_memory()
        if len(self.collector._memory_mb) == 0:
            pytest.skip("psutil not available")

    def test_get_snapshot(self):
        self.collector.record_translation(count=10, elapsed=1.0)
        self.collector.record_api_call(response_time=0.5, success=True)

        snapshot = self.collector.get_snapshot()

        assert "uptime_seconds" in snapshot
        assert snapshot["total_translated"] == 10
        assert snapshot["total_api_calls"] == 1
        assert snapshot["total_api_errors"] == 0
        assert snapshot["avg_translation_rate"] > 0
        assert snapshot["avg_response_time"] == 0.5

    def test_snapshot_contains_history(self):
        for _ in range(5):
            self.collector.record_translation(count=1, elapsed=0.1)
            self.collector.record_api_call(response_time=0.1, success=True)

        snapshot = self.collector.get_snapshot()

        assert len(snapshot["translation_rate_history"]) == 5
        assert len(snapshot["response_time_history"]) == 5

    def test_thread_safety(self):
        errors = []

        def worker(n):
            try:
                for _ in range(100):
                    self.collector.record_translation(count=1, elapsed=0.01)
                    self.collector.record_api_call(response_time=0.01, success=True)
                    self.collector.get_snapshot()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

    def test_uptime_increases(self):
        time.sleep(0.1)
        snapshot1 = self.collector.get_snapshot()
        time.sleep(0.1)
        snapshot2 = self.collector.get_snapshot()
        assert snapshot2["uptime_seconds"] > snapshot1["uptime_seconds"]

    def test_empty_snapshot(self):
        snapshot = self.collector.get_snapshot()
        assert snapshot["total_translated"] == 0
        assert snapshot["total_api_calls"] == 0
        assert snapshot["avg_translation_rate"] == 0.0
        assert snapshot["avg_response_time"] == 0.0


class TestGetMetricsCollector:
    """全局 MetricsCollector 获取函数测试"""

    def setup_method(self):
        import core.metrics_collector as mc
        mc._global_collector = None

    def test_returns_singleton(self):
        collector1 = get_metrics_collector()
        collector2 = get_metrics_collector()
        assert collector1 is collector2

    def test_singleton_persists(self):
        collector = get_metrics_collector()
        collector.record_translation(count=5, elapsed=1.0)
        collector2 = get_metrics_collector()
        assert collector2._total_translated == 5
