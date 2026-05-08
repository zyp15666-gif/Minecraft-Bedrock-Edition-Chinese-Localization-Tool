"""主流程按钮：提取、翻译、一条龙与实体名等（MinecraftTranslatorApp 混入）。"""

from __future__ import annotations

import asyncio
import threading

import flet as ft

from ui.user_interaction import mark_interaction


class ApplicationFeatureOperationsMixin:
    def _require_api(self, feature_name: str) -> bool:
        if not self.api_manager or not self.api_manager.get_available_apis():
            self.show_error_dialog("错误", f"请先配置可用的 API（{feature_name}）")
            return False
        return True

    def _run_feature_task(self, feature_fn, feature_name, progress_text, **kwargs):
        """通用功能执行器：启动后台线程，处理进度/日志/结果。"""

        def progress_callback(value, remaining_count=0, remaining_time=0):
            text = f"{progress_text}... {int(value*100)}%" if value < 1 else f"{progress_text}完成"

            async def update_progress_task():
                self.update_progress(value, text, remaining_count, remaining_time)
            self.page.run_task(update_progress_task)

        def log_callback(msg):
            async def log_task():
                self.log(msg)
            self.page.run_task(log_task)

        def task():
            try:
                try:
                    result = feature_fn(
                        progress_callback=progress_callback,
                        log_callback=log_callback,
                        **kwargs,
                    )
                except Exception as ex:
                    result = {"success": False, "message": f"{progress_text}过程出错: {str(ex)}"}

                if result["success"]:
                    self._handle_success(result, progress_text)
                else:
                    self._handle_failure(result, progress_text)
            finally:
                self.enable_all_buttons()

        self.disable_all_buttons()
        thread = threading.Thread(target=task, daemon=True)
        thread.start()

    def _handle_success(self, result, progress_text):
        msg = result["message"]
        backup = result.get("backup_path")
        if backup:
            msg = f"{msg}\n原文件夹已备份至:\n{backup}"

        async def update_progress_task():
            self.update_progress(1.0, result["message"], 0, 0)
        self.page.run_task(update_progress_task)

        async def show_success_task():
            self.show_success_dialog("成功", msg)
        self.page.run_task(show_success_task)

        async def log_task():
            self.log(f"✅ {result['message']}")
        self.page.run_task(log_task)

    def _handle_failure(self, result, progress_text):
        async def show_error_task():
            self.show_error_dialog("错误", result["message"])
        self.page.run_task(show_error_task)

        async def update_progress_fail_task():
            self.update_progress(0, f"{progress_text}失败", 0, 0)
        self.page.run_task(update_progress_fail_task)

    def on_extract_only(self, e):
        mark_interaction("button_click", "功能1: 仅提取汉化 key")
        if not self.bp_path:
            self.show_error_dialog("错误", "请先选择 BP 文件夹")
            return
        if not self._require_api("功能1"):
            return
        self.log("🚀 [功能1] 开始提取汉化 key...")
        self._run_feature_task(
            self.functions.extract_only, "功能1", "提取",
            bp_path=self.bp_path, rp_path=self.rp_path,
        )

    def on_extract_and_translate(self, e):
        mark_interaction("button_click", "功能2: 提取+AI翻译")
        if not self.bp_path:
            self.show_error_dialog("错误", "请先选择 BP 文件夹")
            return
        if not self._require_api("功能2"):
            return
        self.log("🚀 [功能2] 开始提取并翻译...")
        self._run_feature_task(
            self.functions.extract_and_translate, "功能2", "翻译",
            bp_path=self.bp_path, rp_path=self.rp_path,
        )

    def replace_display_names(self, e):
        mark_interaction("button_click", "功能3: 全BP替换display_name")
        if not self.bp_path:
            self.show_error_dialog("错误", "请先选择 BP 文件夹")
            return
        if not self._require_api("功能3"):
            return
        self.log("🚀 [功能3] 开始替换 display_name...")
        self._run_feature_task(
            self.functions.replace_display_names, "功能3", "替换",
            bp_path=self.bp_path,
        )

    def on_one_click_service(self, e):
        mark_interaction("button_click", "功能7: 一条龙服务")
        if not self.bp_path:
            self.show_error_dialog("错误", "请先选择 BP 文件夹")
            return
        if not self._require_api("功能7"):
            return
        self.log("🚀 [功能7] 开始一条龙服务...")
        self._run_feature_task(
            self.functions.one_click_service, "功能7", "一条龙服务",
            bp_path=self.bp_path, rp_path=self.rp_path,
        )

    async def remove_value_for_specified_folder(self, e):
        mark_interaction("button_click", "功能4: 批量删除value")
        if not self._file_pickers_available:
            self.show_error_dialog("浏览器模式不支持文件选择，请使用桌面模式")
            return
        if not self._require_api("功能4"):
            return

        def _select_folder():
            return self.file_handler.select_folder("选择文件夹")

        path = await asyncio.to_thread(_select_folder)
        if not path:
            return
        self.log(f"🚀 [功能4] 开始批量删除 value: {path}")
        self._run_feature_task(
            self.functions.batch_delete_value, "功能4", "删除",
            folder_path=path,
        )

    async def restore_value_for_specified_folder(self, e):
        mark_interaction("button_click", "功能5: 批量还原value")
        if not self._file_pickers_available:
            self.show_error_dialog("浏览器模式不支持文件选择，请使用桌面模式")
            return
        if not self._require_api("功能5"):
            return

        def _select_folder():
            return self.file_handler.select_folder("选择文件夹")

        path = await asyncio.to_thread(_select_folder)
        if not path:
            return
        self.log(f"🚀 [功能5] 开始批量还原 value: {path}")
        self._run_feature_task(
            self.functions.batch_restore_value, "功能5", "还原",
            folder_path=path,
        )

    async def translate_lang_file(self, e):
        mark_interaction("button_click", "功能6: 翻译独立的.lang文件")
        if not self._file_pickers_available:
            self.show_error_dialog("浏览器模式不支持文件选择，请使用桌面模式")
            return
        if not self._require_api("功能6"):
            return

        def _select_file():
            return self.file_handler.select_file("选择 lang 文件", [("lang文件", "*.lang")])

        lang_file = await asyncio.to_thread(_select_file)
        if not lang_file:
            return
        self.log(f"🚀 [功能6] 开始翻译 lang 文件: {lang_file}")
        self._run_feature_task(
            self.functions.translate_lang_file, "功能6", "翻译",
            lang_file_path=lang_file, bp_path=self.bp_path, rp_path=self.rp_path,
        )

    async def process_guidebook_js(self, e):
        mark_interaction("button_click", "功能9: 翻译单个JS文件")
        if not self._file_pickers_available:
            self.show_error_dialog("浏览器模式不支持文件选择，请使用桌面模式")
            return
        if not self._require_api("功能9"):
            return

        def _select_file():
            return self.file_handler.select_file("选择 JS 文件", [("JS文件", "*.js")])

        js_file = await asyncio.to_thread(_select_file)
        if not js_file:
            return
        self.log(f"🚀 [功能9] 开始翻译 JS 文件: {js_file}")

        def mode1(e):
            self.page.pop_dialog()
            self.show_js_translation_preview_dialog([js_file], mode=1, bp_path=self.bp_path)

        def mode2(e):
            self.page.pop_dialog()
            self.show_js_translation_preview_dialog([js_file], mode=2, bp_path=self.bp_path)

        def cancel(e):
            self.page.pop_dialog()

        dialog = ft.AlertDialog(
            title=ft.Text("🔧 翻译模式选择"),
            content=ft.Column([
                ft.Text("请选择翻译模式:", size=14),
                ft.Divider(height=10),
                ft.Text("模式1: 只翻译包含§颜色代码的字符串（最安全）", size=12),
                ft.Text("模式2: AI 智能判断并翻译所有玩家可见文本", size=12),
                ft.Divider(height=10),
                ft.Text("📝 注意: 现在会先显示预览对话框，确认后再执行翻译", size=11, color=ft.Colors.GREEN),
            ], tight=True, spacing=10),
            actions=[
                ft.TextButton("模式1", on_click=mode1),
                ft.TextButton("模式2", on_click=mode2),
                ft.TextButton("取消", on_click=cancel),
            ],
        )
        self.page.show_dialog(dialog)

    def _execute_single_js_translation(self, js_file, mode):
        def translation_task():
            try:
                def progress_callback(value, remaining_count=0, remaining_time=0):
                    text = f"翻译中... {int(value*100)}%" if value < 1 else "翻译完成"

                    async def update():
                        self.update_progress(value, text, remaining_count, remaining_time)
                    self.page.run_task(update)

                def log_callback(msg):
                    async def update():
                        self.log(msg)
                    self.page.run_task(update)

                self.disable_all_buttons()
                result = self.functions.translate_single_js_file(
                    js_file_path=js_file, mode=mode,
                    progress_callback=progress_callback, log_callback=log_callback,
                )
                if result.get("success"):
                    if result.get("translated_files") and len(result.get("translated_files", [])) == 0:
                        msg = "该文件中没有找到需要翻译的字符串（可能已汉化或无文本）"
                    else:
                        msg = result.get("message", "翻译完成")

                    async def show_success():
                        self.show_success_dialog("翻译完成", msg)
                    self.page.run_task(show_success)
                else:
                    async def show_error():
                        self.show_error_dialog("翻译失败", result.get("message", "未知错误"))
                    self.page.run_task(show_error)
            except Exception as ex:
                error_msg = str(ex)

                async def show_error():
                    self.show_error_dialog("错误", error_msg)
                self.page.run_task(show_error)
            finally:
                self.enable_all_buttons()

        thread = threading.Thread(target=translation_task, daemon=True)
        thread.start()

    def extract_entity_display_names(self, e):
        mark_interaction("button_click", "功能8: 高亮实体信息显示名称适配")
        if not self.bp_path:
            self.show_error_dialog("错误", "请先选择 BP 文件夹")
            return
        if not self._require_api("功能8"):
            return
        self.log("🚀 [功能8] 开始提取实体显示名称...")
        self._run_feature_task(
            self.functions.extract_entity_display_names, "功能8", "适配",
            bp_path=self.bp_path, rp_path=self.rp_path,
        )
