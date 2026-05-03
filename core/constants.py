#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目常量定义 - 统一管理所有魔法数字和枚举值

避免在代码中散布魔法数字，提高可维护性。
"""

from enum import Enum
from typing import Final


class TranslationQualityThresholds:
    """翻译质量阈值"""
    ENGLISH_RATIO_THRESHOLD: Final[float] = 0.8
    MIN_CHINESE_RATIO: Final[float] = 0.3
    LENGTH_MIN_RATIO: Final[float] = 0.15
    LENGTH_MAX_RATIO: Final[float] = 3.0
    OVERALL_SCORE_THRESHOLD: Final[float] = 85.0
    COMPLETENESS_THRESHOLD: Final[float] = 90.0
    IDENTIFIER_PROTECTION_THRESHOLD: Final[float] = 95.0


class CacheConfig:
    """缓存配置"""
    DEFAULT_MAX_SIZE: Final[int] = 2000
    AST_CACHE_MAX_SIZE: Final[int] = 128
    QUALITY_CHECK_CACHE_MAX_SIZE: Final[int] = 1000
    LRU_ACCESS_ORDER_MAX: Final[int] = 10000


class ThreadingConfig:
    """线程配置"""
    MAX_THREADS_PER_API: Final[int] = 3
    DEFAULT_MAX_WORKERS: Final[int] = 20
    UI_UPDATE_INTERVAL: Final[float] = 0.3
    UI_UPDATE_BATCH_SIZE: Final[int] = 10


class BatchConfig:
    """批处理配置"""
    DEFAULT_BATCH_SIZE: Final[int] = 100
    BATCH_FALLBACK_SIZE: Final[int] = 5
    DYNAMIC_BATCH_MIN_CHARS: Final[int] = 200
    DYNAMIC_BATCH_MAX_CHARS: Final[int] = 600


class RetryConfig:
    """重试配置"""
    MAX_RETRIES: Final[int] = 3
    BASE_DELAY: Final[float] = 1.0
    MAX_DELAY: Final[float] = 10.0
    BACKOFF_FACTOR: Final[float] = 2.0
    JITTER_FACTOR: Final[float] = 0.1


class CircuitBreakerConfig:
    """熔断器配置"""
    FAILURE_THRESHOLD: Final[int] = 5
    RECOVERY_TIMEOUT: Final[int] = 60
    HALF_OPEN_MAX_CALLS: Final[int] = 3
    SUCCESS_THRESHOLD: Final[int] = 2


class RateLimitConfig:
    """速率限制配置"""
    DEFAULT_DELAY: Final[float] = 0.15
    LOCAL_OLLAMA_DELAY: Final[float] = 0.0


class UIConfig:
    """UI配置"""
    DEFAULT_WINDOW_SIZE: tuple = (800, 600)
    MIN_WINDOW_SIZE: tuple = (600, 400)
    DARK_MODE_ENABLED: Final[bool] = True
    DEFAULT_LANGUAGE: Final[str] = "zh_CN"
    STARTUP_ANIMATION_DURATION: Final[float] = 2.0
    PROGRESS_THROTTLE_MIN_INTERVAL: Final[float] = 0.1
    PROGRESS_THROTTLE_SIGNIFICANT_DELTA: Final[float] = 0.05


class APITimeoutConfig:
    """API超时配置"""
    CONNECT_TIMEOUT: Final[float] = 10.0
    READ_TIMEOUT: Final[float] = 30.0
    TEST_CONNECT_TIMEOUT: Final[float] = 5.0
    TEST_READ_TIMEOUT: Final[float] = 10.0


class ComplexityThresholds:
    """复杂度阈值"""
    COLOR_DENSITY_THRESHOLD: Final[float] = 0.3
    TERM_DENSITY_THRESHOLD: Final[float] = 0.5
    SPECIAL_CHARS_THRESHOLD: Final[int] = 5
    SKIP_STAGE2_COMPLEXITY_THRESHOLD: Final[float] = 0.6


class BackupConfig:
    """备份配置"""
    TIMESTAMP_FORMAT: Final[str] = "%Y%m%d_%H%M%S_%f"
    MAX_BACKUP_COUNT: Final[int] = 10
    BACKUP_FILE_EXTENSION: Final[str] = ".bak"


class LogConfig:
    """日志配置"""
    MAX_LOG_FILES: Final[int] = 10
    MAX_LOG_FILE_SIZE: Final[int] = 10 * 1024 * 1024
    LOG_RETENTION_DAYS: Final[int] = 7


class APIProviderPlaceholders:
    """API提供商占位符检测"""
    PATTERNS: tuple = (
        '你的', 'your_', 'your-key', 'your_key', 'placeholder',
        'xxx', 'XXXX', '***', 'api_key_here', 'key_here',
        'sk-test', 'test-key', 'test_key', 'fake_', 'mock_'
    )


class FunctionButtonGroups(Enum):
    """功能按钮分组枚举"""
    EXTRACTION = "提取类"
    TRANSLATION = "翻译类"
    BATCH_OPERATION = "批处理类"
    MANAGEMENT = "管理类"


class FunctionButtonOrder:
    """功能按钮顺序配置"""
    EXTRACT_ONLY = 1
    EXTRACT_AND_TRANSLATE = 2
    REPLACE_DISPLAY_NAMES = 3
    BATCH_DELETE_VALUE = 4
    BATCH_RESTORE_VALUE = 5
    TRANSLATE_LANG_FILE = 6
    ONE_CLICK_SERVICE = 7
    ADAPT_ENTITY_DISPLAY_NAMES = 8
    TRANSLATE_SINGLE_JS_FILE = 9
    SCRIPT_HARDCODE_TRANSLATION = 10
    BACKUP_MANAGEMENT = 11


FUNCTION_BUTTON_GROUPS: dict = {
    'extract_only': FunctionButtonGroups.EXTRACTION,
    'extract_and_translate': FunctionButtonGroups.TRANSLATION,
    'replace_display_names': FunctionButtonGroups.BATCH_OPERATION,
    'batch_delete_value': FunctionButtonGroups.BATCH_OPERATION,
    'batch_restore_value': FunctionButtonGroups.BATCH_OPERATION,
    'translate_lang_file': FunctionButtonGroups.TRANSLATION,
    'one_click_service': FunctionButtonGroups.TRANSLATION,
    'adapt_entity_display_names': FunctionButtonGroups.TRANSLATION,
    'translate_single_js_file': FunctionButtonGroups.TRANSLATION,
    'script_hardcode_translation': FunctionButtonGroups.TRANSLATION,
    'backup_management': FunctionButtonGroups.MANAGEMENT,
}
