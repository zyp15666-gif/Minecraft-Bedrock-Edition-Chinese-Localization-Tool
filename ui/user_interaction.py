"""用户交互标记辅助模块。"""

from __future__ import annotations

from core.log_manager import get_log_manager


def mark_interaction(event_type: str, description: str):
    """标记用户交互事件，供各 mixin 调用。"""
    lm = get_log_manager()
    if lm:
        lm.mark_user_interaction(event_type, description)
