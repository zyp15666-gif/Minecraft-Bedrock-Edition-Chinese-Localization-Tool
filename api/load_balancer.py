#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
负载均衡器 - 基于响应时间的加权轮询策略

从 APIManager 中拆分出来的独立组件。

职责：
- 响应时间统计
- 加权轮询选择

注意：健康状态检查由 CircuitBreaker 统一管理，不再在此维护。
"""

import time
import threading
from typing import Dict, Any, List, Optional
from core.log_manager import get_logger

logger = get_logger(__name__)


class LoadBalancer:
    """基于响应时间的加权轮询负载均衡器

    健康状态由 CircuitBreaker 统一管理，本类仅负责响应时间统计和选择策略。
    """

    def __init__(self):
        self.response_times: Dict[str, List[float]] = {}
        self.last_used: Dict[str, float] = {}
        self.max_history = 10
        self._lock = threading.Lock()

    def select_api(self, available_apis: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """选择最佳API

        策略：
        1. 优先选择响应时间最短的API
        2. 响应时间相同时，优先选择最近未使用的API

        注意：健康状态过滤由调用方（APIManager）通过 CircuitBreaker.is_available() 完成

        Args:
            available_apis: 可用API列表（已由调用方过滤健康状态）

        Returns:
            选中的API配置，无可用API时返回None
        """
        if not available_apis:
            return None

        if len(available_apis) == 1:
            return available_apis[0]

        with self._lock:
            scored = []
            for api in available_apis:
                name = api.get('name', 'unknown')
                avg_time = self._get_avg_response_time(name)
                last_used = self.last_used.get(name, 0)
                if last_used > 0:
                    idle_minutes = min((time.time() - last_used) / 60.0, 10.0)
                else:
                    idle_minutes = 0.0
                idle_bonus = idle_minutes * 0.5
                score = avg_time - idle_bonus
                scored.append((score, api))

            scored.sort(key=lambda x: x[0])
            selected = scored[0][1]
            self.last_used[selected.get('name', 'unknown')] = time.time()
            return selected

    def record_response_time(self, api_name: str, response_time: float):
        """记录响应时间

        Args:
            api_name: API名称
            response_time: 响应时间（秒）
        """
        with self._lock:
            if api_name not in self.response_times:
                self.response_times[api_name] = []
            self.response_times[api_name].append(response_time)
            if len(self.response_times[api_name]) > self.max_history:
                self.response_times[api_name] = self.response_times[api_name][-self.max_history:]

    def _get_avg_response_time(self, api_name: str) -> float:
        """获取API平均响应时间

        Args:
            api_name: API名称

        Returns:
            平均响应时间（秒），无数据时返回默认值
        """
        times = self.response_times.get(api_name, [])
        if not times:
            all_times = [t for tl in self.response_times.values() for t in tl]
            if all_times:
                return sorted(all_times)[len(all_times) // 2]
            return 2.0
        return sum(times) / len(times)

    def get_stats(self) -> Dict[str, Any]:
        """获取负载均衡统计信息"""
        with self._lock:
            stats = {}
            for name in self.response_times.keys():
                stats[name] = {
                    'avg_response_time': self._get_avg_response_time(name),
                    'last_used': self.last_used.get(name, 0),
                }
            return stats
