#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API编排器 - 负责API检测、负载均衡、熔断器管理

从APIManager中分离出的职责：
- API检测和可用性管理
- 负载均衡和API选择
- 熔断器管理
- 线程管理
"""

import threading
from typing import Any, Dict, List, Optional

from api.circuit_breaker import CircuitBreaker
from api.load_balancer import LoadBalancer
from core.log_manager import get_logger

logger = get_logger(__name__)


class APIOrchestrator:
    """API编排器 - 管理API检测、负载均衡和熔断器"""

    def __init__(self, config: Dict[str, Any]):
        """初始化API编排器

        Args:
            config: 配置字典
        """
        self.config = config
        self.available_apis: List[Dict[str, Any]] = []
        self.current_api_index = 0
        self.api_lock = threading.Lock()

        self.api_active_threads: Dict[str, int] = {}
        self.max_threads_per_api = config.get("basic", {}).get("max_threads_per_api", 3)

        advanced_config = config.get('advanced', {})
        circuit_breaker_config = advanced_config.get('circuit_breaker', {})
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=circuit_breaker_config.get('failure_threshold', 5),
            recovery_timeout=circuit_breaker_config.get('recovery_timeout', 60),
            half_open_max_calls=circuit_breaker_config.get('half_open_max_calls', 3),
            success_threshold=circuit_breaker_config.get('success_threshold', 2)
        )

        self.load_balancer = LoadBalancer()

        logger.info(f"[APIOrchestrator] 初始化完成: max_threads_per_api={self.max_threads_per_api}")

    def build_api_list(self) -> List[Dict[str, Any]]:
        """构建API列表（从配置）"""
        api_list = []
        api_configs = self.config.get("apis", [])

        for api_config in api_configs:
            if api_config.get("enabled", True):
                api_list.append(api_config)

        return api_list

    def detect_available_apis(self) -> List[Dict[str, Any]]:
        """检测可用API（需要API客户端配合）"""
        from api.api_detector import APIDetector

        detector = APIDetector(self.config)
        self.available_apis = detector.detect_available()

        with self.api_lock:
            self.current_api_index = 0

        logger.info(f"检测到 {len(self.available_apis)} 个可用API")
        return self.available_apis

    def get_next_api(self) -> Optional[Dict[str, Any]]:
        """获取下一个可用API（负载均衡 + 熔断器）"""
        with self.api_lock:
            if not self.available_apis:
                logger.warning("没有可用的API")
                return None

            for _ in range(len(self.available_apis)):
                api_config = self.available_apis[self.current_api_index]
                self.current_api_index = (self.current_api_index + 1) % len(self.available_apis)

                api_name = api_config.get('name', 'unknown')

                if self.circuit_breaker.is_open(api_name):
                    logger.debug(f"API {api_name} 熔断器开启，跳过")
                    continue

                active_threads = self.api_active_threads.get(api_name, 0)
                if active_threads >= self.max_threads_per_api:
                    logger.debug(f"API {api_name} 线程数已达上限 {active_threads}/{self.max_threads_per_api}")
                    continue

                return api_config

            logger.warning("所有API都不可用（熔断或线程数达上限）")
            return None

    def acquire_api_thread(self, api_config: Dict[str, Any]) -> bool:
        """获取API线程槽位

        Args:
            api_config: API配置

        Returns:
            是否成功获取
        """
        api_name = api_config.get('name', 'unknown')

        with self.api_lock:
            active_threads = self.api_active_threads.get(api_name, 0)
            if active_threads >= self.max_threads_per_api:
                return False

            self.api_active_threads[api_name] = active_threads + 1
            logger.debug(f"API {api_name} 线程数: {active_threads + 1}/{self.max_threads_per_api}")
            return True

    def release_api_thread(self, api_config: Dict[str, Any]):
        """释放API线程槽位

        Args:
            api_config: API配置
        """
        api_name = api_config.get('name', 'unknown')

        with self.api_lock:
            active_threads = self.api_active_threads.get(api_name, 0)
            if active_threads > 0:
                self.api_active_threads[api_name] = active_threads - 1
                logger.debug(f"API {api_name} 线程数: {active_threads - 1}/{self.max_threads_per_api}")

    def record_success(self, api_name: str):
        """记录API成功调用"""
        self.circuit_breaker.record_success(api_name)
        logger.debug(f"API {api_name} 调用成功")

    def record_failure(self, api_name: str):
        """记录API失败调用"""
        self.circuit_breaker.record_failure(api_name)
        logger.warning(f"API {api_name} 调用失败")

    def get_available_apis(self) -> List[Dict[str, Any]]:
        """获取可用API列表"""
        with self.api_lock:
            return self.available_apis.copy()

    def get_api_stats(self) -> Dict[str, Any]:
        """获取API统计信息"""
        with self.api_lock:
            return {
                'total_apis': len(self.available_apis),
                'active_threads': dict(self.api_active_threads),
                'max_threads_per_api': self.max_threads_per_api,
                'circuit_breaker_status': {
                    api.get('name', 'unknown'): self.circuit_breaker.get_state(api.get('name', 'unknown'))
                    for api in self.available_apis
                }
            }
