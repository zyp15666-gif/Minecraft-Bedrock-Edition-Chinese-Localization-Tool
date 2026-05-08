#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
依赖注入容器 - 统一构建应用组件

消除 core/pipeline.py 和 ui/main_window.py 中的重复初始化逻辑。
所有组件的创建和组装都通过此模块完成，确保依赖链一致。
"""

from dataclasses import dataclass, field
from typing import Callable, Optional

from core.log_manager import get_logger

logger = get_logger(__name__)


@dataclass
class AppContainer:
    """应用组件容器 - 持有所有核心组件的引用"""

    config: dict = field(default_factory=dict)
    config_manager: object = None
    api_manager: object = None
    translator: object = None
    file_handler: object = None
    app_service: object = None


def build_app_container(
    log_callback: Optional[Callable[[str], None]] = None,
    show_error: Optional[Callable[[str, str], None]] = None,
    show_success: Optional[Callable[[str, str], None]] = None,
) -> AppContainer:
    """构建应用组件容器

    统一的组件初始化入口，替代 pipeline.py 和 main_window.py 中的重复逻辑。

    Args:
        log_callback: 日志回调（UI 传入 self.log）
        show_error: 错误对话框回调（UI 传入 self.show_error_dialog）
        show_success: 成功对话框回调（UI 传入 self.show_success_dialog）

    Returns:
        AppContainer 实例，包含所有已初始化的组件
    """
    from api.api_manager import APIManager
    from config.config_manager import ConfigManager
    from core.application_service import ApplicationService
    from core.file_handler import FileHandler
    from core.translator import Translator

    config_manager = ConfigManager()
    config = config_manager.load_config()

    if log_callback:
        log_callback(f"✅ 配置加载成功，配置文件路径: {config_manager.config_path}")

    api_manager = APIManager(config)
    translator = Translator(api_manager, config)
    file_handler = FileHandler(config)

    app_service = ApplicationService(
        api_manager=api_manager,
        config_manager=config_manager,
        file_handler=file_handler,
        translator=translator,
        log_callback=log_callback,
        show_error=show_error,
        show_success=show_success,
    )

    if log_callback:
        log_callback("✅ 应用服务层已初始化 (core/application_service.py)")

    return AppContainer(
        config=config,
        config_manager=config_manager,
        api_manager=api_manager,
        translator=translator,
        file_handler=file_handler,
        app_service=app_service,
    )
