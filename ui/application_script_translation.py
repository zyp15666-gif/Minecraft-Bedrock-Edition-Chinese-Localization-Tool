"""脚本硬编码翻译与预览执行（MinecraftTranslatorApp 混入）。"""

from __future__ import annotations

import os
import threading

import flet as ft

from ui.user_interaction import mark_interaction


class ApplicationScriptTranslationMixin:
    def script_hardcode_translation(self, e):
        """[10] 脚本文件夹硬编码汉化测试版 - 增强版（支持三种汉化模式）"""
        # 标记用户交互
        mark_interaction("button_click", "功能10: 脚本文件夹硬编码汉化")

        if not self.bp_path:
            self.show_error_dialog("错误", "请先选择 BP 文件夹")
            return

        # 检查是否有可用的API
        if not self._require_api("功能10"):
            return

        self.log("🚀 [功能10] 开始脚本文件夹硬编码汉化测试...")

        # 先快速扫描JS文件
        import os
        script_folder = os.path.join(self.bp_path, "scripts")
        if not os.path.exists(script_folder):
            self.show_error_dialog("错误", f"未找到脚本文件夹: {script_folder}")
            return

        # 扫描JS文件
        js_files = []
        for root, _, files in os.walk(script_folder):
            for file in files:
                if file.lower().endswith('.js'):
                    js_files.append(os.path.join(root, file))

        if not js_files:
            self.show_error_dialog("提示", "在脚本文件夹中未找到任何JS文件")
            return

        self.log(f"📁 找到 {len(js_files)} 个JS脚本文件")

        # 创建选项对话框
        def option1_selected(e):
            """选项1: 只汉化包含§颜色/格式代码的脚本"""
            self.page.pop_dialog()
            self.log("🔧 选择模式1: 只汉化包含§颜色/格式代码的脚本")
            self.show_js_translation_preview_dialog(js_files, mode=1, bp_path=self.bp_path)

        def option2_selected(e):
            """选项2: 汉化通过了三重API验证机制的脚本"""
            self.page.pop_dialog()
            self.log("🔧 选择模式2: 汉化通过了三重API验证机制的脚本")
            self.show_js_translation_preview_dialog(js_files, mode=2, bp_path=self.bp_path)

        def option3_selected(e):
            """选项3: 取消"""
            self.page.pop_dialog()
            self.log("🔧 选择模式3: 取消操作")

        # 创建对话框
        dialog = ft.AlertDialog(
            title=ft.Text("🔧 脚本文件夹硬编码汉化选项"),
            content=ft.Column([
                ft.Text(f"在脚本文件夹中找到 {len(js_files)} 个JS文件", size=14, weight=ft.FontWeight.BOLD),
                ft.Text("请选择汉化模式:", size=14),
                ft.Divider(height=10),
                ft.Text("选项1: 只汉化包含§颜色/格式代码的脚本", size=12),
                ft.Text("  • 仅处理包含Minecraft颜色代码(§)的文件", size=12, color=ft.Colors.GREY),
                ft.Text("  • 最安全的模式，基本不会误判", size=12, color=ft.Colors.GREY),
                ft.Divider(height=10),
                ft.Text("选项2: 汉化通过了三重API验证机制的脚本", size=12),
                ft.Text("  • 使用AI三重验证判断是否需要汉化", size=12, color=ft.Colors.GREY),
                ft.Text("  • 更全面，但需要API支持", size=12, color=ft.Colors.GREY),
                ft.Divider(height=10),
                ft.Text("📝 注意: 选择后将先显示预览对话框，确认后再执行翻译", size=11, color=ft.Colors.GREEN),
                ft.Divider(height=10),
                ft.Text("选项3: 取消操作", size=12, color=ft.Colors.GREY),
            ], tight=True, spacing=5),
            actions=[
                ft.TextButton("选项1", on_click=option1_selected),
                ft.TextButton("选项2", on_click=option2_selected),
                ft.TextButton("取消", on_click=option3_selected),
            ],
        )

        # 显示对话框
        self.page.show_dialog(dialog)

    def show_js_translation_preview_dialog(self, js_files, mode, bp_path=None):
        """
        显示JS翻译预览对话框

        参数:
            js_files: JS文件列表
            mode: 翻译模式 (1: 颜色代码模式, 2: AI智能模式)
            bp_path: BP文件夹路径
        """
        # 首先分析文件获取预览数据
        self.log(f"🔍 开始分析 {len(js_files)} 个JS文件用于预览...")

        # 禁用所有按钮
        self.disable_all_buttons()

        def analyze_task():
            try:
                def progress_callback(value, remaining=0, time_left=0):
                    async def update():
                        text = f"分析中... {int(value*100)}%" if value < 1 else "分析完成"
                        self.update_progress(value, text, remaining, time_left)
                    self.page.run_task(update)

                def log_callback(msg):
                    async def update():
                        self.log(msg)
                    self.page.run_task(update)

                # 创建ScriptTranslation实例
                from core.script_translation import create_script_translation
                script_translator = create_script_translation(self.translator)

                # 分析文件获取预览数据
                analysis_result = script_translator.analyze_js_files_for_preview(
                    js_files=js_files,
                    mode=mode,
                    progress_callback=progress_callback,
                    log_callback=log_callback
                )
                # ... 后续代码保持不变

                async def show_preview_dialog():
                    # 启用所有按钮
                    self.enable_all_buttons()

                    if not analysis_result.get('success'):
                        self.show_error_dialog("分析失败", analysis_result.get('message', '未知错误'))
                        return

                    # 获取分析数据
                    file_analyses = analysis_result.get('file_analyses', [])
                    summary = analysis_result.get('summary', {})

                    if not file_analyses:
                        self.show_error_dialog("提示", "没有找到可翻译的字符串")
                        return

                    # 创建预览内容
                    preview_content = []

                    # 添加摘要信息
                    preview_content.append(ft.Text(
                        f"📊 分析摘要: {summary.get('total_files', 0)} 个文件, "
                        f"{summary.get('total_strings', 0)} 个字符串, "
                        f"{summary.get('needs_translation_count', 0)} 个需要翻译",
                        size=14,
                        weight=ft.FontWeight.BOLD
                    ))

                    # 添加预估时间
                    estimated_time = summary.get('estimated_translation_time', 0)
                    preview_content.append(ft.Text(
                        f"⏱️ 预估翻译时间: {estimated_time:.1f} 秒",
                        size=12,
                        color=ft.Colors.GREY
                    ))

                    preview_content.append(ft.Divider(height=10))

                    # 创建文件列表
                    file_list = []

                    for file_analysis in file_analyses:
                        file_path = file_analysis['file_path']
                        file_name = os.path.basename(file_path)
                        needs_count = file_analysis.get('needs_translation_count', 0)
                        total_count = file_analysis.get('total_strings', 0)
                        error = file_analysis.get('error')

                        if error:
                            file_info_row = ft.Row([
                                ft.Text(file_name, size=12, expand=True),
                                ft.Text(f"错误: {error[:30]}", size=12, color=ft.Colors.RED)
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                        else:
                            file_info_row = ft.Row([
                                ft.Text(file_name, size=12, expand=True),
                                ft.Text(f"{needs_count}/{total_count}", size=12, color=ft.Colors.GREEN if needs_count > 0 else ft.Colors.GREY)
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

                        file_list.append(file_info_row)

                    # 添加到预览内容
                    preview_content.append(ft.Text("📁 文件列表:", size=13, weight=ft.FontWeight.BOLD))
                    preview_content.extend(file_list)
                    preview_content.append(ft.Divider(height=10))

                    # 添加提示信息
                    preview_content.append(ft.Text(
                        "⚠️ 注意: 翻译将创建备份文件 (.bak)，如有问题可手动恢复",
                        size=11,
                        color=ft.Colors.ORANGE
                    ))

                    # 创建确认翻译的函数
                    def confirm_translation(e):
                        self.page.pop_dialog()
                        self._execute_script_translation(js_files, mode, bp_path)

                    def cancel_preview(e):
                        self.page.pop_dialog()
                        self.log("预览取消")

                    # 创建对话框
                    dialog = ft.AlertDialog(
                        title=ft.Text(f"🔍 JS翻译预览 (模式{mode})"),
                        content=ft.Column(preview_content, tight=True, spacing=8, scroll=ft.ScrollMode.AUTO),
                        actions=[
                            ft.TextButton("取消", on_click=cancel_preview),
                            ft.TextButton("确认翻译", on_click=confirm_translation, style=ft.ButtonStyle(color=ft.Colors.GREEN))
                        ],
                    )

                    # 显示对话框
                    self.page.show_dialog(dialog)

                # 显示预览对话框
                self.page.run_task(show_preview_dialog)

            except Exception as ex:
                async def show_error(error=ex):
                    self.enable_all_buttons()
                    self.show_error_dialog("分析错误", str(error))
                self.page.run_task(show_error)

        # 启动分析任务线程
        thread = threading.Thread(target=analyze_task, daemon=True)
        thread.start()




    def _execute_script_translation(self, js_files, mode, bp_path=None):
        """执行脚本翻译：支持单文件和多文件两种场景"""
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

                # 根据文件数量选择翻译方式
                if len(js_files) == 1:
                    # 单文件翻译
                    js_file = js_files[0]
                    log_callback(f"🚀 开始翻译单个 JS 文件: {os.path.basename(js_file)}")
                    result = self.functions.translate_single_js_file(
                        js_file_path=js_file,
                        mode=mode,
                        progress_callback=progress_callback,
                        log_callback=log_callback
                    )
                else:
                    # 多文件批量翻译
                    log_callback(f"🚀 开始批量翻译 {len(js_files)} 个 JS 文件")
                    from core.script_translation import ScriptTranslation
                    script_trans = ScriptTranslation(self.translator)
                    result = script_trans.translate_js_files_with_ast(
                        js_files=js_files,
                        mode=mode,
                        progress_callback=progress_callback,
                        log_callback=log_callback
                    )

                if result.get('success'):
                    translated_count = len(result.get('translated_files', []))
                    if translated_count == 0:
                        msg = "所有文件中均未找到需要翻译的字符串"
                    else:
                        msg = f"成功翻译 {translated_count} 个文件，共处理 {len(js_files)} 个文件"
                    async def show_success():
                        self.show_success_dialog("翻译完成", msg)
                    self.page.run_task(show_success)
                else:
                    async def show_error():
                        self.show_error_dialog("翻译失败", result.get('message', '未知错误'))
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
