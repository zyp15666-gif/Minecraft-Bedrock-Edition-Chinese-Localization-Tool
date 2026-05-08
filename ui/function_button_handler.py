#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
功能按钮事件处理器 - 统一管理所有功能按钮的事件处理

从main_window.py中提取，负责：
- 11个功能按钮的事件处理
- 通用后台任务执行模式
- 统一的进度和日志回调处理
"""

from typing import Any, Callable, Dict, Optional

import flet as ft


class FunctionButtonHandler:
    """功能按钮事件处理器"""

    def __init__(
        self,
        page: ft.Page,
        functions,
        config_manager,
        task_service,
        update_progress: Callable,
        disable_buttons: Callable,
        enable_buttons: Callable,
        log_callback: Callable,
        show_error: Callable,
        show_success: Callable,
    ):
        """初始化功能按钮处理器

        Args:
            page: Flet页面对象
            functions: ApplicationService实例
            config_manager: 配置管理器
            task_service: 后台任务服务
            update_progress: 更新进度回调
            disable_buttons: 禁用按钮回调
            enable_buttons: 启用按钮回调
            log_callback: 日志回调
            show_error: 显示错误对话框回调
            show_success: 显示成功对话框回调
        """
        self.page = page
        self.functions = functions
        self.config_manager = config_manager
        self.task_service = task_service
        self.update_progress = update_progress
        self.disable_buttons = disable_buttons
        self.enable_buttons = enable_buttons
        self.log = log_callback
        self.show_error = show_error
        self.show_success = show_success
        self.function_buttons: list = []

    def register_buttons(self, buttons: list):
        """注册功能按钮列表"""
        self.function_buttons = buttons

    def _create_progress_callback(self, operation_name: str) -> Callable:
        """创建进度回调"""
        def progress_callback(value: float, remaining_count: int = 0, remaining_time: int = 0):
            if value < 1:
                text = f"{operation_name}中... {int(value * 100)}%"
            else:
                text = f"{operation_name}完成"
            self.update_progress(value, text, remaining_count, remaining_time)
        return progress_callback

    def _create_log_callback(self) -> Callable:
        """创建日志回调"""
        def log_callback(msg: str):
            self.log(msg)
        return log_callback

    def _run_feature_task(
        self,
        method_name: str,
        operation_name: str,
        log_prefix: str,
        bp_path: Optional[str] = None,
        rp_path: Optional[str] = None,
        folder_path: Optional[str] = None,
        lang_file_path: Optional[str] = None,
        js_file_path: Optional[str] = None,
        mode: Optional[int] = None,
        **extra_kwargs
    ):
        """通用后台任务执行方法"""
        self.log(f"🚀 {log_prefix}")
        self.disable_buttons()

        def task_fn():
            try:
                method = getattr(self.functions, method_name)
                kwargs = {
                    'progress_callback': self._create_progress_callback(operation_name),
                    'log_callback': self._create_log_callback(),
                }

                if bp_path is not None:
                    kwargs['bp_path'] = bp_path
                if rp_path is not None:
                    kwargs['rp_path'] = rp_path
                if folder_path is not None:
                    kwargs['folder_path'] = folder_path
                if lang_file_path is not None:
                    kwargs['lang_file_path'] = lang_file_path
                if js_file_path is not None:
                    kwargs['js_file_path'] = js_file_path
                if mode is not None:
                    kwargs['mode'] = mode

                kwargs.update(extra_kwargs)
                return method(**kwargs)
            except Exception as ex:
                return {'success': False, 'message': f"{operation_name}出错: {str(ex)}"}

        def on_result(result: Dict[str, Any]):
            if result.get('success'):
                self.update_progress(1.0, f"{operation_name}完成", 0, 0)
                self.show_success(operation_name, result.get('message', ''))
                self.log(f"✅ {result.get('message', '')}")
            else:
                self.show_error(operation_name, result.get('message', ''))
                self.log(f"❌ {result.get('message', '')}")

        def on_error(error: Exception):
            self.show_error(operation_name, str(error))
            self.log(f"❌ {operation_name}失败: {error}")

        self.task_service.run_with_button_state(
            task_fn,
            disabled_controls=self.function_buttons,
            on_progress=lambda v, r, t: self.update_progress(v, f"{log_prefix} {int(v*100)}%" if v < 1 else "完成", r, t),
            on_log=self.log,
            on_result=on_result,
            on_error=on_error,
        )

    def on_extract_only(self, bp_path: str, rp_path: Optional[str] = None):
        """[1] 仅提取汉化key"""
        self._run_feature_task(
            method_name='extract_only',
            operation_name='提取',
            log_prefix='[功能1] 开始提取汉化key...',
            bp_path=bp_path,
            rp_path=rp_path,
        )

    def on_extract_and_translate(self, bp_path: str, rp_path: Optional[str] = None):
        """[2] 提取+AI翻译"""
        self._run_feature_task(
            method_name='extract_and_translate',
            operation_name='翻译',
            log_prefix='[功能2] 开始提取并翻译...',
            bp_path=bp_path,
            rp_path=rp_path,
        )

    def on_replace_display_names(self, bp_path: str):
        """[3] 全BP替换display_name"""
        self._run_feature_task(
            method_name='replace_display_names',
            operation_name='替换',
            log_prefix='[功能3] 开始替换display_name...',
            bp_path=bp_path,
        )

    def on_batch_delete_value(self, folder_path: str):
        """[4] 批量删除value"""
        self._run_feature_task(
            method_name='batch_delete_value',
            operation_name='删除',
            log_prefix='[功能4] 开始批量删除value...',
            folder_path=folder_path,
        )

    def on_batch_restore_value(self, folder_path: str):
        """[5] 批量还原value"""
        self._run_feature_task(
            method_name='batch_restore_value',
            operation_name='还原',
            log_prefix='[功能5] 开始批量还原value...',
            folder_path=folder_path,
        )

    def on_translate_lang_file(self, lang_file_path: str, bp_path: Optional[str] = None, rp_path: Optional[str] = None):
        """[6] 翻译独立的.lang文件"""
        self._run_feature_task(
            method_name='translate_lang_file',
            operation_name='翻译',
            log_prefix='[功能6] 开始翻译lang文件...',
            lang_file_path=lang_file_path,
            bp_path=bp_path,
            rp_path=rp_path,
        )

    def on_one_click_service(self, bp_path: str, rp_path: Optional[str] = None):
        """[7] 一条龙服务"""
        self._run_feature_task(
            method_name='one_click_service',
            operation_name='一条龙',
            log_prefix='[功能7] 开始一条龙服务...',
            bp_path=bp_path,
            rp_path=rp_path,
        )

    def on_adapt_entity_display_names(self, bp_path: str, rp_path: Optional[str] = None):
        """[8] 高亮实体信息显示名称适配"""
        self._run_feature_task(
            method_name='adapt_entity_display_names',
            operation_name='适配',
            log_prefix='[功能8] 开始提取实体显示名称...',
            bp_path=bp_path,
            rp_path=rp_path,
        )

    def on_translate_single_js_file(self, js_file_path: str, mode: int):
        """[9] 翻译单个JS文件"""
        self._run_feature_task(
            method_name='translate_single_js_file',
            operation_name='翻译',
            log_prefix='[功能9] 开始翻译JS文件...',
            js_file_path=js_file_path,
            mode=mode,
        )

    def on_script_hardcode_translation(self, bp_path: str, mode: int):
        """[10] 脚本硬编码汉化"""
        self._run_feature_task(
            method_name='script_hardcode_translation',
            operation_name='脚本汉化',
            log_prefix='[功能10] 开始脚本文件夹硬编码汉化...',
            bp_path=bp_path,
            mode=mode,
        )

    def on_translate_mcstructure(self, bp_path: str, rp_path: Optional[str] = None):
        """[12] mcstructure汉化"""
        self._run_feature_task(
            method_name='translate_mcstructure',
            operation_name='mcstructure汉化',
            log_prefix='[功能12] 开始汉化mcstructure文件...',
            bp_path=bp_path,
            rp_path=rp_path,
        )
