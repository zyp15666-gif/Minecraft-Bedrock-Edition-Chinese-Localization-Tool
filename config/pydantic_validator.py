#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pydantic配置验证器

提供强类型的配置验证，支持：
- 配置结构验证
- 类型检查
- 默认值填充
- 配置文档生成
"""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class APIConfig(BaseModel):
    """API提供商配置"""
    name: str
    api_key: Optional[str] = None
    api_url: Optional[str] = None
    model: Optional[str] = None
    enabled: bool = True
    priority: int = 0

    @field_validator('name')
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('API名称不能为空')
        return v.strip()


class RateLimitConfig(BaseModel):
    """速率限制配置"""
    default: float = 0.15
    local_ollama: float = 0.0


class AdvancedRetryConfig(BaseModel):
    """重试配置"""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 10.0
    backoff_factor: float = 2.0

    @field_validator('max_retries')
    @classmethod
    def max_retries_positive(cls, v: int) -> int:
        if v < 0:
            raise ValueError('max_retries必须为非负数')
        return v


class CircuitBreakerConfig(BaseModel):
    """熔断器配置"""
    failure_threshold: int = 5
    recovery_timeout: int = 60
    half_open_max_calls: int = 3
    success_threshold: int = 2

    @field_validator('failure_threshold', 'success_threshold')
    @classmethod
    def threshold_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError('阈值必须为正数')
        return v


class TranslationConfig(BaseModel):
    """翻译配置"""
    dynamic_batch_enabled: bool = True
    min_batch_chars: int = 200
    max_batch_chars: int = 600
    batch_fallback_size: int = 5


class QualityConfig(BaseModel):
    """质量检查配置"""
    enabled: bool = True
    auto_retry_threshold: float = 0.5


class AdvancedConfig(BaseModel):
    """高级配置"""
    retry: AdvancedRetryConfig = Field(default_factory=AdvancedRetryConfig)
    circuit_breaker: CircuitBreakerConfig = Field(default_factory=CircuitBreakerConfig)
    translation: TranslationConfig = Field(default_factory=TranslationConfig)
    quality: QualityConfig = Field(default_factory=QualityConfig)


class BasicConfig(BaseModel):
    """基础配置"""
    namespace: str = "sgs_farm"
    indent: int = 4
    max_threads_per_api: int = 3
    max_workers: int = 20
    cache_max_size: int = 2000


class UIConfig(BaseModel):
    """UI配置"""
    theme: Literal["dark", "light", "auto"] = "dark"
    ui_scale: float = 1.0
    function_buttons: List[Dict[str, Any]] = Field(default_factory=list)

    @field_validator('ui_scale')
    @classmethod
    def scale_in_range(cls, v: float) -> float:
        if not 0.5 <= v <= 2.0:
            raise ValueError('ui_scale必须在0.5到2.0之间')
        return v


class ConfigSchema(BaseModel):
    """完整配置结构"""
    basic: BasicConfig = Field(default_factory=BasicConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    advanced: AdvancedConfig = Field(default_factory=AdvancedConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    apis: Dict[str, List[APIConfig]] = Field(default_factory=dict)

    @model_validator(mode='before')
    @classmethod
    def coerce_types(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """类型强制转换"""
        if not isinstance(data, dict):
            return {}

        if 'basic' in data and isinstance(data['basic'], dict):
            if 'max_threads_per_api' in data['basic']:
                data['basic']['max_threads_per_api'] = int(data['basic']['max_threads_per_api'])
            if 'cache_max_size' in data['basic']:
                data['basic']['cache_max_size'] = int(data['basic']['cache_max_size'])

        return data


class ConfigValidator:
    """配置验证器"""

    @staticmethod
    def validate(config: Dict[str, Any]) -> tuple[bool, Optional[str], Dict[str, Any]]:
        """验证配置

        Args:
            config: 配置字典

        Returns:
            (是否有效, 错误消息, 修正后的配置)
        """
        try:
            validated = ConfigSchema.model_validate(config)
            return True, None, validated.model_dump()
        except Exception as e:
            return False, str(e), config

    @staticmethod
    def validate_partial(config: Dict[str, Any]) -> tuple[bool, List[str], Dict[str, Any]]:
        """部分验证（只验证存在的字段）

        Args:
            config: 配置字典

        Returns:
            (是否有效, 错误列表, 修正后的配置)
        """
        errors = []

        try:
            if 'basic' in config:
                BasicConfig.model_validate(config['basic'])
        except Exception as e:
            errors.append(f"basic: {e}")

        try:
            if 'rate_limit' in config:
                RateLimitConfig.model_validate(config['rate_limit'])
        except Exception as e:
            errors.append(f"rate_limit: {e}")

        try:
            if 'ui' in config:
                UIConfig.model_validate(config['ui'])
        except Exception as e:
            errors.append(f"ui: {e}")

        return len(errors) == 0, errors, config

    @staticmethod
    def get_default_config() -> Dict[str, Any]:
        """获取默认配置"""
        schema = ConfigSchema()
        return schema.model_dump()

    @staticmethod
    def get_config_schema() -> Dict[str, Any]:
        """获取配置schema（用于文档生成）"""
        return ConfigSchema.model_json_schema()
