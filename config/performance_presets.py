#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能预设：按项目体量调整 worker / 批大小，避免默认值一刀切。

在 config.yml 的 basic.performance_preset 中填写 small | balanced | large。
"""

from typing import Any, Dict

PRESETS: Dict[str, Dict[str, Any]] = {
    "small": {
        "max_workers": 6,
        "batch_size": 40,
        "max_threads_per_api": 2,
        "update_batch_size": 6,
    },
    "balanced": {
        "max_workers": 12,
        "batch_size": 100,
        "max_threads_per_api": 3,
        "update_batch_size": 10,
    },
    "large": {
        "max_workers": 20,
        "batch_size": 150,
        "max_threads_per_api": 5,
        "update_batch_size": 14,
    },
}
