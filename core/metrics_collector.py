"""
性能指标采集器 — 环形缓冲区存储最近 N 个数据点，供实时图表使用
"""

import threading
import time
from collections import deque
from typing import Dict, Optional

from core.log_manager import get_logger

logger = get_logger(__name__)


class MetricsCollector:
    """线程安全的性能指标采集器"""

    def __init__(self, buffer_size: int = 120):
        self.buffer_size = buffer_size
        self._lock = threading.Lock()

        self._timestamps: deque = deque(maxlen=buffer_size)
        self._translation_rate: deque = deque(maxlen=buffer_size)  # 条/秒
        self._api_response_times: deque = deque(maxlen=buffer_size)  # 秒
        self._memory_mb: deque = deque(maxlen=buffer_size)

        self._total_translated = 0
        self._total_api_calls = 0
        self._total_api_errors = 0
        self._session_start = time.time()

    def record_translation(self, count: int, elapsed: float):
        with self._lock:
            t = time.time()
            rate = count / max(elapsed, 0.001)
            self._timestamps.append(t)
            self._translation_rate.append(rate)
            self._total_translated += count
            if self._total_translated > 0 and self._total_translated % 50 == 0:
                logger.debug(
                    "metrics: 累计翻译 %s 条, 最近速率 %.2f 条/秒",
                    self._total_translated,
                    rate,
                )

    def record_api_call(self, response_time: float, success: bool):
        with self._lock:
            self._api_response_times.append(response_time)
            self._total_api_calls += 1
            if not success:
                self._total_api_errors += 1

    def record_memory(self):
        try:
            import os

            import psutil
            process = psutil.Process(os.getpid())
            mb = process.memory_info().rss / 1024 / 1024
            with self._lock:
                self._memory_mb.append(mb)
        except Exception:
            pass

    def get_snapshot(self) -> Dict:
        with self._lock:
            tss = list(self._timestamps)
            rates = list(self._translation_rate)
            times = list(self._api_response_times)
            mem = list(self._memory_mb)

        avg_rate = sum(rates) / len(rates) if rates else 0.0
        avg_rt = sum(times) / len(times) if times else 0.0
        uptime = time.time() - self._session_start

        return {
            "uptime_seconds": uptime,
            "total_translated": self._total_translated,
            "total_api_calls": self._total_api_calls,
            "total_api_errors": self._total_api_errors,
            "avg_translation_rate": avg_rate,
            "avg_response_time": avg_rt,
            "timestamps": tss,
            "translation_rate_history": rates,
            "response_time_history": times,
            "memory_history_mb": mem,
        }


_global_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    global _global_collector
    if _global_collector is None:
        _global_collector = MetricsCollector()
    return _global_collector
