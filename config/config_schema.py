#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置 Schema 验证模块

定义配置的结构定义和校验规则，无需外部依赖。
在 ConfigManager.load_config() 末尾调用 validate() 以尽早发现配置问题。
"""

import re
from typing import Dict, Any, List, Optional, Tuple


# ──────────── Schema 定义 ────────────

CONFIG_SCHEMA = {
    "basic": {
        "type": dict,
        "required": True,
        "description": "基础设置",
        "fields": {
            "namespace": {"type": str, "required": True, "pattern": r"^[a-z_]+$"},
            "indent": {"type": int, "required": True, "min": 0, "max": 8},
            "use_multithreading": {"type": bool, "required": False, "default": True},
            "max_workers": {"type": int, "required": False, "min": 1, "max": 128},
            "max_retries": {"type": int, "required": False, "min": 0, "max": 10},
            "batch_size": {"type": int, "required": False, "min": 1, "max": 10000},
            "cache_max_size": {"type": int, "required": False, "min": 0},
            "max_threads_per_api": {"type": int, "required": False, "min": 1, "max": 20},
            "log_level": {"type": str, "required": False, "choices": ["DEBUG", "INFO", "WARNING", "ERROR"]},
            "local_first_fallback": {"type": bool, "required": False},
            "use_multi_api_validation": {"type": bool, "required": False},
        }
    },
    "rate_limit": {
        "type": dict,
        "required": False,
        "description": "速率限制",
        "fields": {
            "default": {"type": (int, float), "required": False, "min": 0},
            "local_ollama": {"type": (int, float), "required": False, "min": 0},
        }
    },
    "terminology": {
        "type": dict,
        "required": False,
        "description": "术语词典配置",
        "fields": {
            "dict_path": {"type": str, "required": False},
            "enabled": {"type": bool, "required": False},
            "mode": {"type": str, "required": False, "choices": ["aggressive", "normal", "conservative"]},
            "auto_update": {"type": bool, "required": False},
        }
    },
    "local_ollama": {
        "type": list,
        "required": False,
        "description": "本地 Ollama API 配置列表",
        "item_schema": {
            "type": dict,
            "fields": {
                "name": {"type": str, "required": True},
                "api_url": {"type": str, "required": True, "pattern": r"^https?://"},
                "api_key": {"type": str, "required": False},
                "model": {"type": str, "required": True},
                "enabled": {"type": bool, "required": False, "default": True},
                "priority": {"type": int, "required": False, "min": 0},
            }
        }
    },
    "deepseek": {"type": list, "required": False, "description": "DeepSeek API 配置"},
    "qwen": {"type": list, "required": False, "description": "通义千问 API 配置"},
    "zhipu": {"type": list, "required": False, "description": "智谱 API 配置"},
    "doubao": {"type": list, "required": False, "description": "豆包 API 配置"},
    "ui": {
        "type": dict,
        "required": False,
        "description": "UI 配置",
        "fields": {
            "dark_mode": {"type": bool, "required": False},
            "language": {"type": str, "required": False, "choices": ["zh_CN", "en_US"]},
        }
    },
    "advanced": {
        "type": dict,
        "required": False,
        "description": "高级配置",
        "fields": {
            "translation": {"type": dict, "required": False},
            "quality": {"type": dict, "required": False},
            "complexity": {"type": dict, "required": False},
            "retry": {"type": dict, "required": False},
        }
    },
    "author": {
        "type": dict,
        "required": False,
        "description": "作者信息",
        "fields": {
            "description": {"type": str, "required": False},
        }
    },
}


# ──────────── 验证函数 ────────────

ValidationResult = List[Tuple[str, str]]  # [(field_path, error_message), ...]


def validate_config(config: Dict[str, Any]) -> ValidationResult:
    """验证配置字典是否符合 Schema

    Args:
        config: 要验证的配置字典

    Returns:
        错误列表，每个元素为 (字段路径, 错误信息)
        空列表表示验证通过
    """
    errors: ValidationResult = []
    _validate_dict(config, CONFIG_SCHEMA, "", errors)
    return errors


def _validate_dict(
    data: Dict[str, Any],
    schema: Dict[str, Any],
    path: str,
    errors: ValidationResult,
) -> None:
    """递归验证字典"""
    for field_name, field_schema in schema.items():
        field_path = f"{path}.{field_name}" if path else field_name
        value = data.get(field_name)

        # 检查必需字段
        if field_schema.get("required", False) and value is None:
            errors.append((field_path, f"缺少必需字段"))
            continue

        if value is None:
            continue  # 可选字段且未提供

        # 检查类型
        expected_type = field_schema.get("type")
        if expected_type and not isinstance(value, expected_type):
            errors.append((field_path, f"类型错误: 期望 {expected_type.__name__}, 实际 {type(value).__name__}"))
            continue

        # 检查子字段递归
        sub_fields = field_schema.get("fields")
        if sub_fields and isinstance(value, dict):
            _validate_dict(value, sub_fields, field_path, errors)

        # 检查列表元素
        item_schema = field_schema.get("item_schema")
        if item_schema and isinstance(value, list):
            for i, item in enumerate(value):
                item_path = f"{field_path}[{i}]"
                if isinstance(item, dict):
                    _validate_dict(item, item_schema.get("fields", {}), item_path, errors)

        # 范围检查（数字）
        min_val = field_schema.get("min")
        max_val = field_schema.get("max")
        if isinstance(value, (int, float)):
            if min_val is not None and value < min_val:
                errors.append((field_path, f"值 {value} 小于最小值 {min_val}"))
            if max_val is not None and value > max_val:
                errors.append((field_path, f"值 {value} 大于最大值 {max_val}"))

        # 模式检查（字符串）
        pattern = field_schema.get("pattern")
        if pattern and isinstance(value, str) and not re.match(pattern, value):
            errors.append((field_path, f"'{value}' 不匹配模式 {pattern}"))

        # 枚举检查
        choices = field_schema.get("choices")
        if choices and isinstance(value, str) and value not in choices:
            errors.append((field_path, f"'{value}' 不在允许值 {choices} 中"))


def format_validation_errors(errors: ValidationResult) -> str:
    """将验证错误格式化为可读字符串"""
    if not errors:
        return "配置验证通过"
    lines = [f"配置验证发现 {len(errors)} 个问题:"]
    for field, msg in errors:
        lines.append(f"  - [{field}] {msg}")
    return "\n".join(lines)


def ensure_config_valid(config: Dict[str, Any]) -> Dict[str, Any]:
    """验证配置并在有错误时打印警告（不阻断执行）

    Args:
        config: 配置字典

    Returns:
        原配置字典（不修改）
    """
    errors = validate_config(config)
    if errors:
        import logging
        logging.getLogger(__name__).warning(format_validation_errors(errors))
    return config
