#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API监控器 - 统计与告警

从 APIManager 中拆分出来的独立组件。
"""

import threading
import time
from typing import Dict, Any, Optional
from core.log_manager import get_logger

logger = get_logger(__name__)


class APIMonitor:
    """API调用监控与统计（线程安全）"""

    def __init__(self):
        self.stats: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self.alert_thresholds: Dict[str, float] = {
            'error_rate': 0.5,
            'avg_response_time': 30.0,
            'consecutive_failures': 5,
        }

    def record_call(self, api_name: str, response_time: float, success: bool, tokens_used: int = 0):
        """记录一次API调用（线程安全）

        Args:
            api_name: API名称
            response_time: 响应时间
            success: 是否成功
            tokens_used: 使用的token数量
        """
        with self._lock:
            if api_name not in self.stats:
                self.stats[api_name] = {
                    'total_calls': 0,
                    'successful_calls': 0,
                    'failed_calls': 0,
                    'total_response_time': 0.0,
                    'total_tokens': 0,
                    'consecutive_failures': 0,
                    'last_call_time': 0.0,
                    'last_error': None,
                }

            s = self.stats[api_name]
            s['total_calls'] += 1
            s['total_response_time'] += response_time
            s['last_call_time'] = time.time()

            if success:
                s['successful_calls'] += 1
                s['consecutive_failures'] = 0
            else:
                s['failed_calls'] += 1
                s['consecutive_failures'] += 1

            s['total_tokens'] += tokens_used

            self._check_alerts(api_name, s)

    def _check_alerts(self, api_name: str, stats: Dict[str, Any]):
        """检查是否触发告警

        Args:
            api_name: API名称
            stats: 统计数据
        """
        if stats['total_calls'] < 3:
            return

        error_rate = stats['failed_calls'] / stats['total_calls']
        if error_rate > self.alert_thresholds['error_rate']:
            logger.warning(
                f"[告警] API [{api_name}] 错误率过高: {error_rate:.1%} "
                f"(阈值: {self.alert_thresholds['error_rate']:.1%})")

        avg_time = stats['total_response_time'] / stats['total_calls']
        if avg_time > self.alert_thresholds['avg_response_time']:
            logger.warning(
                f"[告警] API [{api_name}] 平均响应时间过长: {avg_time:.1f}s "
                f"(阈值: {self.alert_thresholds['avg_response_time']:.1f}s)")

        if stats['consecutive_failures'] >= self.alert_thresholds['consecutive_failures']:
            logger.warning(
                f"[告警] API [{api_name}] 连续失败 {stats['consecutive_failures']} 次 "
                f"(阈值: {self.alert_thresholds['consecutive_failures']})")

    def get_api_stats(self, api_name: str) -> Optional[Dict[str, Any]]:
        """获取指定API的统计信息（线程安全）"""
        with self._lock:
            return self.stats.get(api_name)

    def get_summary(self) -> Dict[str, Dict[str, Any]]:
        """获取所有API的统计摘要（线程安全）"""
        with self._lock:
            summary = {}
            for name, s in self.stats.items():
                total = s['total_calls']
                summary[name] = {
                    'total_calls': total,
                    'success_rate': s['successful_calls'] / total if total > 0 else 0,
                    'avg_response_time': s['total_response_time'] / total if total > 0 else 0,
                    'total_tokens': s['total_tokens'],
                    'consecutive_failures': s['consecutive_failures'],
                    'is_healthy': s['consecutive_failures'] < self.alert_thresholds['consecutive_failures'],
                }
            return summary

    def reset_stats(self, api_name: Optional[str] = None):
        """重置统计信息（线程安全）

        Args:
            api_name: 指定API名称，None则重置所有
        """
        with self._lock:
            if api_name:
                self.stats.pop(api_name, None)
            else:
                self.stats.clear()
