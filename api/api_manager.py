#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API管理模块 - 精简版

职责：初始化和协调各子模块，不再包含批量翻译/多API验证的具体实现。
具体逻辑委托给：
  - TranslationStrategy: 单条翻译策略
  - BatchTranslationCoordinator: 批量翻译协调
  - MultiAPIVerifier: 多API验证
  - APIOrchestrator: API检测/负载均衡/熔断器
  - APIDetector: API列表构建与检测
"""

import time
import threading
import logging
from typing import List, Dict, Any, Optional, Callable
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed

from core.log_manager import get_logger
from core.utils import resolve_resource_path
from api.api_client import APIClient
from api.translation_cache import TranslationCache
from api.translation_strategy import TranslationStrategy
from api.interfaces import ITranslationEngine
from api.api_detector import APIDetector
from api.circuit_breaker import CircuitBreaker, CircuitOpenError
from api.unified_retry import with_retry, RetryPolicy
from api.api_orchestrator import APIOrchestrator
from api.batch_translation_coordinator import BatchTranslationCoordinator
from api.multi_api_verifier import MultiAPIVerifier
from api.load_balancer import LoadBalancer
from api.api_monitor import APIMonitor
from api.terminology_service import TerminologyService

try:
    from api.async_api_client import AsyncAPIClient, AIOHTTP_AVAILABLE
except ImportError:
    AIOHTTP_AVAILABLE = False
    AsyncAPIClient = None

logger = get_logger(__name__)


class APIManager(ITranslationEngine):
    """API管理器 - 协调者角色，委托具体逻辑给子模块

    实现 ITranslationEngine 接口，对外提供统一的翻译 API。
    内部将职责委托给：
      - TranslationStrategy: 单条翻译（术语匹配、缓存、颜色代码处理）
      - BatchTranslationCoordinator: 批量翻译（分批、合并、拆分、术语处理）
      - MultiAPIVerifier: 多API验证（投票、质量评估、最佳选择）
      - APIOrchestrator: API检测、负载均衡、熔断器、线程管理
    """

    def __init__(self, config: Dict[str, Any], term_service=None, quality_checker=None):
        """初始化API管理器

        Args:
            config: 配置字典
            term_service: 术语服务实例，可选，用于依赖注入
            quality_checker: 质量检查器实例，可选，用于依赖注入
        """
        self.config = config
        self.available_apis: List[Dict[str, Any]] = []
        self.current_api_index = 0
        self.api_lock = threading.Lock()
        self.rate_limit_delay = config.get(
            "rate_limit", {"default": 0.15, "local_ollama": 0.0})
        self.api_active_threads: Dict[str, int] = {}
        self.max_threads_per_api = config.get("basic", {}).get("max_threads_per_api", 3)
        self._api_capacity_condition = threading.Condition(self.api_lock)

        advanced_config = config.get('advanced', {})

        circuit_breaker_config = advanced_config.get('circuit_breaker', {})
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=circuit_breaker_config.get('failure_threshold', 5),
            recovery_timeout=circuit_breaker_config.get('recovery_timeout', 60),
            half_open_max_calls=circuit_breaker_config.get('half_open_max_calls', 3),
            success_threshold=circuit_breaker_config.get('success_threshold', 2)
        )
        logger.info(f"[APIManager] 熔断器初始化: failure_threshold={self.circuit_breaker.failure_threshold}, recovery_timeout={self.circuit_breaker.recovery_timeout}s")

        quality_config = advanced_config.get('quality', {})
        self.MIN_LENGTH_RATIO = quality_config.get('length_min_ratio', 0.15)
        self.MAX_LENGTH_RATIO = quality_config.get('length_max_ratio', 3.0)
        self.ENGLISH_MAX_RATIO = quality_config.get('english_max_ratio', 0.3)

        if term_service is None:
            dict_path = self.config.get("terminology", {}).get(
                "dict_path", "resources/api/minecraft_terms.json")
            dict_path = str(resolve_resource_path(dict_path))
            self.term_service = TerminologyService(dict_path, config)
        else:
            self.term_service = term_service

        retry_config = self.config.get("advanced", {}).get("retry", {})
        self.api_client = APIClient(self.rate_limit_delay, retry_config)

        if AIOHTTP_AVAILABLE:
            try:
                self.async_api_client = AsyncAPIClient(self.rate_limit_delay, retry_config)
                logger.info("✅ 异步API客户端已初始化 (使用aiohttp，性能优化)")
            except Exception as e:
                logger.warning(f"异步API客户端初始化失败，回退到同步模式: {e}")
                self.async_api_client = None
        else:
            self.async_api_client = None
            logger.info("ℹ️  aiohttp未安装，使用同步API客户端（建议安装aiohttp以获得更好性能）")

        cache_max_size = self.config.get("basic", {}).get("cache_max_size", 2000)
        self.cache = TranslationCache(max_size=cache_max_size)

        if quality_checker is not None:
            self.quality_checker = quality_checker
        else:
            from core.quality_checker import TranslationQualityChecker
            self.quality_checker = TranslationQualityChecker(
                term_service=self.term_service,
                cache_enabled=True,
                cache_max_size=1000,
                min_length_ratio=self.MIN_LENGTH_RATIO,
                max_length_ratio=self.MAX_LENGTH_RATIO,
                english_max_ratio=self.ENGLISH_MAX_RATIO
            )

        self.api_error_logs: deque = deque(maxlen=1000)
        self.api_alerts: deque = deque(maxlen=500)
        self.last_stat_reset_time = time.time()

        self.load_balancer = LoadBalancer()
        self.api_monitor = APIMonitor()

        self.translation_strategy = TranslationStrategy(
            term_service=self.term_service,
            quality_checker=self.quality_checker,
            cache=self.cache,
            api_client=self.api_client
        )

        self.api_detector = APIDetector(config)

        self.api_orchestrator = APIOrchestrator(config)
        self.batch_coordinator = BatchTranslationCoordinator(config, self.term_service)
        self.multi_api_verifier = MultiAPIVerifier(config, self.term_service, self.quality_checker)
        logger.info("✅ 模块化组件已初始化 (APIOrchestrator + BatchTranslationCoordinator + MultiAPIVerifier)")

    # ──────────── API 列表构建与检测 ────────────

    def build_api_list(self) -> List[Dict[str, Any]]:
        """构建API列表（委托给 APIDetector）"""
        return self.api_detector.build_api_list()

    def test_single_api(self, api_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """测试单个API是否可用（委托给 APIDetector）"""
        return self.api_detector.test_single(api_config)

    def detect_available_apis(self) -> List[Dict[str, Any]]:
        """检测所有可用的API（并行验证）"""
        available = self.api_detector.detect_available(translate_hook=self.call_api_translate)
        with self.api_lock:
            self.available_apis = available
            self.api_orchestrator.available_apis = available
        return available

    def get_next_api(self) -> Optional[Dict[str, Any]]:
        """基于响应时间的加权轮询获取下一个可用API

        使用 threading.Condition 替代 sleep 轮询，
        当有线程释放时立即唤醒等待者，减少延迟。
        """
        with self._api_capacity_condition:
            max_wait = 30.0
            deadline = time.monotonic() + max_wait

            while time.monotonic() < deadline:
                if not self.available_apis:
                    return None

                available_apis_with_capacity = []
                for api in self.available_apis:
                    api_name = api['name']
                    active_threads = self.api_active_threads.get(api_name, 0)

                    if active_threads >= self.max_threads_per_api:
                        continue

                    if not self.circuit_breaker.is_available(api_name):
                        logger.debug(f"[APIManager] API {api_name} 熔断器开启，跳过")
                        continue

                    available_apis_with_capacity.append(api)

                if available_apis_with_capacity:
                    selected = self.load_balancer.select_api(available_apis_with_capacity)
                    if selected is None:
                        selected = available_apis_with_capacity[0]

                    api_name = selected['name']
                    self.api_active_threads[api_name] = self.api_active_threads.get(
                        api_name, 0) + 1
                    return selected

                remaining = deadline - time.monotonic()
                if remaining > 0:
                    self._api_capacity_condition.wait(timeout=min(remaining, 1.0))

            logger.warning("所有API线程已满，等待超时")
            return None

    # ──────────── 单条翻译 ────────────

    def call_api_translate(self, api_config: Dict[str, Any], text: str, is_test: bool = False, custom_prompt: Optional[str] = None) -> str:
        """调用API翻译文本（委托给 TranslationStrategy）

        Args:
            api_config: API 配置字典
            text: 待翻译文本
            is_test: True 表示仅测试API可用性（不计入统计、不更新缓存、不释放线程配额）；
                     False 表示正常翻译流程
            custom_prompt: 自定义提示词
        """
        api_name = api_config.get('name', 'unknown')
        try:
            result = self.translation_strategy.translate(
                api_config=api_config,
                text=text,
                is_test=is_test,
                custom_prompt=custom_prompt,
                config=self.config
            )
            self.circuit_breaker._on_success(api_name)
            return result
        except Exception as e:
            self.circuit_breaker._on_failure(api_name)
            logger.warning(f"[APIManager] API {api_name} 调用失败，触发熔断检查: {type(e).__name__}: {e}")
            raise
        finally:
            self._release_api_thread(api_config, is_test)

    # ──────────── 批量翻译（委托给 BatchTranslationCoordinator） ────────────

    def batch_translate_fragments(self, api_config: Dict[str, Any], plain_texts: List[str],
                                  is_test: bool = False, prompt: str = None,
                                  batch_size: int = None) -> List[str]:
        """分批翻译文本片段（委托给 BatchTranslationCoordinator）"""
        return self.batch_coordinator.batch_translate_fragments(
            self.api_client, api_config, plain_texts,
            progress_callback=None, log_callback=self._log_debug
        )

    def batch_translate_with_terms(self, api_config: Dict[str, Any], plain_texts: List[str],
                                    is_test: bool = False, prompt: str = None,
                                    batch_size: int = None) -> List[str]:
        """带术语处理的批量翻译（委托给 BatchTranslationCoordinator）"""
        return self.batch_coordinator.batch_translate_with_terms(
            self.api_client, api_config, plain_texts,
            progress_callback=None, log_callback=self._log_debug
        )

    # ──────────── 多API验证（委托给 MultiAPIVerifier） ────────────

    def multi_api_translate(self, text: str, custom_prompt: Optional[str] = None) -> str:
        """多重API翻译验证：调用多个API，选择最佳结果（委托给 MultiAPIVerifier）"""
        return self.multi_api_verifier.multi_api_translate(
            self.api_client, text, self.available_apis, custom_prompt
        )

    # ──────────── ITranslationEngine 接口实现 ────────────

    @with_retry(policy=RetryPolicy.api_call())
    def translate_text(
        self,
        text: str,
        is_test: bool = False,
        custom_prompt: Optional[str] = None
    ) -> str:
        """ITranslationEngine.translate_text 实现（统一重试策略）

        Args:
            text: 待翻译文本
            is_test: True 表示仅测试API可用性（不计入统计、不更新缓存、不释放线程配额）；
                     False 表示正常翻译流程
            custom_prompt: 自定义提示词
        """
        api_config = self.get_next_api()
        if api_config is None:
            logger.warning("无可用API（可能所有API都处于熔断状态）")
            return text
        try:
            return self.call_api_translate(api_config, text, is_test, custom_prompt)
        except CircuitOpenError as e:
            logger.warning(f"[APIManager] {e}")
            raise
        finally:
            self._release_api_thread(api_config, is_test=False)

    def translate_batch(
        self,
        items: Dict[str, str],
        max_workers: int = 4,
        progress_callback: Optional[Callable[[float, int, float], None]] = None
    ) -> Dict[str, str]:
        """ITranslationEngine.translate_batch 实现"""
        results = {}
        total = len(items)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for key, text in items.items():
                future = executor.submit(self.translate_text, text)
                futures[future] = key

            for i, future in enumerate(as_completed(futures)):
                key = futures[future]
                try:
                    results[key] = future.result()
                except Exception as e:
                    logger.error(f"批量翻译失败 key={key}: {e}")
                    results[key] = items[key]

                if progress_callback:
                    progress_callback((i + 1) / total, total - i - 1, 0)

        return results

    def get_available_apis(self) -> List[Dict[str, Any]]:
        """ITranslationEngine.get_available_apis 实现"""
        return self.available_apis.copy()

    def is_available(self) -> bool:
        """ITranslationEngine.is_available 实现"""
        return len(self.available_apis) > 0

    def translate_with_api(
        self,
        api_config: Dict[str, Any],
        text: str,
        is_test: bool = False,
        custom_prompt: Optional[str] = None
    ) -> str:
        """ITranslationEngine.translate_with_api 实现"""
        return self.call_api_translate(api_config, text, is_test, custom_prompt)

    # ──────────── 统计与监控 ────────────

    def update_api_stats(self, api_name: str, success: bool, response_time: float = None,
                         error_type: str = None, error_message: str = None):
        """更新API使用统计"""
        if response_time is not None:
            self.api_monitor.record_call(api_name, response_time, success)

        if response_time is not None:
            self.load_balancer.record_response_time(api_name, response_time)

        if not success:
            current_time = time.time()
            error_entry = {
                'timestamp': current_time,
                'api_name': api_name,
                'error_type': error_type or 'unknown',
                'error_message': error_message or '未知错误',
                'response_time': response_time
            }
            with self.api_lock:
                self.api_error_logs.append(error_entry)

    def get_api_stats(self) -> Dict[str, Any]:
        """获取API统计信息"""
        with self.api_lock:
            monitor_summary = self.api_monitor.get_summary()
            recent_errors = list(self.api_error_logs)[-20:]
            recent_alerts = list(self.api_alerts)[-10:]
            cache_stats = {}
            if hasattr(self.cache, 'get_stats'):
                cache_stats = self.cache.get_stats()
            circuit_breaker_stats = self.circuit_breaker.get_stats()

            return {
                "available": len(self.available_apis),
                "monitor_summary": monitor_summary,
                "recent_errors": recent_errors,
                "recent_alerts": recent_alerts,
                "cache_stats": cache_stats,
                "circuit_breaker_stats": circuit_breaker_stats,
                "stat_reset_time": self.last_stat_reset_time,
                "current_time": time.time()
            }

    def reset_stats(self):
        """重置所有统计信息"""
        with self.api_lock:
            self.api_error_logs = []
            self.api_alerts = []
            self.last_stat_reset_time = time.time()
            self.api_monitor.reset_stats()
            self.circuit_breaker.reset()
            self._preload_terms_to_cache()
            if hasattr(self.cache, 'reset_stats'):
                self.cache.reset_stats()
            logger.info("API统计信息已重置")

    # ──────────── 内部辅助方法 ────────────

    def _log_debug(self, message: str):
        """调试日志辅助方法"""
        if logger.isEnabledFor(logging.DEBUG):
            logger.info(message)

    def _preload_terms_to_cache(self):
        """将术语词典预加载到翻译缓存中"""
        if not self.term_service or not self.term_service.terms:
            logger.info("术语词典为空，跳过缓存预加载")
            return

        preload_count = 0
        for en_term, zh_term in self.term_service.terms.items():
            if len(en_term) <= 50:
                self.cache.set(en_term, zh_term)
                preload_count += 1

        logger.info(f"已将 {preload_count} 条术语预加载到翻译缓存")

    def _release_api_thread(self, api_config: Dict[str, Any], is_test: bool):
        """减少API的活跃线程计数，并通知等待的线程"""
        if not is_test:
            api_name = api_config['name']
            with self._api_capacity_condition:
                current = self.api_active_threads.get(api_name, 0)
                if current > 0:
                    self.api_active_threads[api_name] = current - 1
                self._api_capacity_condition.notify_all()

    def close(self):
        """关闭资源（缓存数据库连接等）"""
        if hasattr(self, 'cache') and self.cache:
            self.cache.close()
