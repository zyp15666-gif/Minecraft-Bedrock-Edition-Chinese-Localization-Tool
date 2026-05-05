"""
Minecraft 基岩版汉化工具 — 功能事件处理器

从 main_window_flet.py 拆出的功能回调处理模块。
每个功能对应一个事件处理方法。
"""

import os
import time
from typing import Dict, Any, Optional, Callable

from core.log_manager import get_logger

logger = get_logger(__name__)


def _default_progress_callback(value, remaining_count=0, remaining_time=0):
    pass


def _default_log_callback(msg):
    pass


class FunctionHandlers:
    """功能事件处理器 - 封装 11 个核心功能的回调逻辑

    通过 app_ref 引用 MinecraftTranslatorApp 实例进行操作。
    """

    def __init__(self, app_ref):
        self.app = app_ref

    # ──────────── 通用辅助 ────────────

    def _run_feature(
        self,
        method_name: str,
        log_prefix: str,
        feature_tag: str,
        **extra_kwargs
    ):
        """通用功能执行入口

        Args:
            method_name: ApplicationService 中的方法名
            log_prefix: 日志前缀
            feature_tag: 功能标识（用于统计）
            extra_kwargs: 传给功能方法的额外参数
        """
        app = self.app
        app.log(f"▶️ 开始{log_prefix}...")
        if not app.bp_path:
            app.show_error_dialog("错误", "请先选择 BP 文件夹")
            return

        def task_fn(progress_callback, log_callback):
            app.functions.log_callback = log_callback
            if not hasattr(app.functions, 'log_callback'):
                setattr(app.functions, 'log_callback', log_callback)

            method_params = {
                'extract_only': {'bp_path': app.bp_path, 'rp_path': app.rp_path},
                'extract_and_translate': {'bp_path': app.bp_path, 'rp_path': app.rp_path},
                'replace_display_names': {'bp_path': app.bp_path},
                'batch_delete_value': {'folder_path': app.bp_path},
                'batch_restore_value': {'folder_path': app.bp_path},
                'translate_lang_file': {'lang_file_path': app.bp_path, 'bp_path': app.bp_path, 'rp_path': app.rp_path},
                'one_click_service': {'bp_path': app.bp_path, 'rp_path': app.rp_path},
                'adapt_entity_display_names': {'bp_path': app.bp_path, 'rp_path': app.rp_path},
                'translate_single_js_file': {'js_file_path': app.bp_path, 'mode': 2},
                'script_hardcode_translation': {'bp_path': app.bp_path, 'mode': 2},
                'translate_mcstructure': {'bp_path': app.bp_path},
            }
            
            params = method_params.get(method_name, {'bp_path': app.bp_path, 'rp_path': app.rp_path}).copy()
            for k, v in extra_kwargs.items():
                if k not in ['bp_path', 'rp_path', 'folder_path']:
                    params[k] = v
            params['progress_callback'] = progress_callback
            params['log_callback'] = log_callback

            result = getattr(app.functions, method_name)(**params)
            return result

        def on_progress(value, remaining_count=0, remaining_time=0):
            text = f"{log_prefix}... {int(value*100)}%" if value < 1 else f"{log_prefix}完成"
            app.update_progress(value, text, remaining_count, remaining_time)

        app.run_background_task(
            task_fn,
            on_progress=on_progress,
            on_result=self._handle_result,
            on_error=self._handle_error,
        )

    def _handle_result(self, result: Dict[str, Any]):
        app = self.app
        app.log(f"✅ 操作完成")
        if result:
            if result.get("success"):
                app.show_success_dialog(
                    "操作完成",
                    result.get("message", "操作成功完成")
                )
            elif result.get("message"):
                app.show_error_dialog("操作结果", result["message"])

    def _handle_error(self, error: Exception):
        app = self.app
        error_msg = str(error)
        app.log(f"❌ 操作失败: {error_msg[:200]}")
        app.show_error_dialog("操作失败", f"操作执行时发生错误：\n{error_msg[:500]}")

    # ──────────── 功能 1: 仅提取汉化 key ────────────

    def on_extract_only(self, e=None):
        self._run_feature("extract_only", "仅提取汉化 Key", "extract_only")

    # ──────────── 功能 2: 提取 + AI 翻译 ────────────

    def on_extract_and_translate(self, e=None):
        self._run_feature(
            "extract_and_translate", "提取+AI翻译", "extract_and_translate"
        )

    # ──────────── 功能 3: 替换 display_name ────────────

    def replace_display_names(self, e=None):
        self._run_feature(
            "replace_display_names", "替换 display_name", "replace_display_names"
        )

    # ──────────── 功能 4: 批量删除 value ────────────

    def on_batch_delete_value(self, e=None):
        self._run_feature(
            "batch_delete_value", "批量删除 value", "batch_delete_value"
        )

    # ──────────── 功能 5: 批量还原 value ────────────

    def on_batch_restore_value(self, e=None):
        self._run_feature(
            "batch_restore_value", "批量还原 value", "batch_restore_value"
        )

    # ──────────── 功能 6: 翻译 .lang 文件 ────────────

    def on_translate_lang_file(self, e=None):
        self._run_feature(
            "translate_lang_file", "翻译 .lang 文件", "translate_lang_file"
        )

    # ──────────── 功能 7: 一条龙服务 ────────────

    def on_one_click_service(self, e=None):
        self._run_feature(
            "one_click_service", "一条龙服务", "one_click_service"
        )

    # ──────────── 功能 8: 实体显示名称适配 ────────────

    def on_adapt_entity_display_names(self, e=None):
        self._run_feature(
            "adapt_entity_display_names",
            "实体显示名称适配",
            "adapt_entity_display_names"
        )

    # ──────────── 功能 9: 翻译单个 JS 文件 ────────────

    def on_translate_single_js_file(self, e=None):
        self._run_feature(
            "translate_single_js_file",
            "翻译单个 JS 文件",
            "translate_single_js_file"
        )

    # ──────────── 功能 10: 脚本硬编码汉化 ────────────

    def on_script_hardcode_translation(self, e=None):
        self._run_feature(
            "script_hardcode_translation",
            "脚本硬编码汉化",
            "script_hardcode_translation"
        )

    # ──────────── 功能 11: 备份管理 ────────────

    def on_backup_management(self, e=None):
        """备份管理直接打开对话框"""
        self.app.show_backup_management_dialog()

    def on_translate_mcstructure(self, e=None):
        """mcstructure汉化"""
        self._run_feature(
            "translate_mcstructure",
            "mcstructure汉化",
            "translate_mcstructure"
        )
