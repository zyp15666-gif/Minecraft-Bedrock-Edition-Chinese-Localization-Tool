"""备份管理、导入导出、性能监控（MinecraftTranslatorApp 混入）。"""

from __future__ import annotations

import os
import re
import time
from datetime import datetime

import flet as ft

from core.log_manager import get_logger
from ui import dialogs
from ui.user_interaction import mark_interaction

logger = get_logger(__name__)

class ApplicationToolsDialogsMixin:
    def show_backup_management_dialog(self, e=None):
        """显示备份文件管理对话框"""
        # 标记用户交互
        mark_interaction("button_click", "功能11: 备份文件管理")

        if not self.bp_path:
            self.show_error_dialog("错误", "请先选择 BP 文件夹")
            return

        # 检查是否有可用的API
        if not self._require_api("功能11"):
            return

        self.log("📂 正在扫描备份文件...")

        # 扫描备份文件
        import os

        backup_files = []

        # 扫描BP文件夹及其子文件夹中的.bak文件
        for root, dirs, files in os.walk(self.bp_path):
            for file in files:
                if file.endswith('.bak'):
                    backup_path = os.path.join(root, file)
                    original_path = backup_path[:-4]  # 移除.bak扩展名

                    # 获取文件信息
                    try:
                        backup_size = os.path.getsize(backup_path)
                        backup_mtime = datetime.fromtimestamp(os.path.getsize(backup_path))
                        backup_mtime_str = backup_mtime.strftime('%Y-%m-%d %H:%M:%S')

                        # 检查原始文件是否存在
                        original_exists = os.path.exists(original_path)

                        backup_files.append({
                            'backup_path': backup_path,
                            'original_path': original_path,
                            'original_exists': original_exists,
                            'size': backup_size,
                            'modified': backup_mtime_str,
                            'filename': os.path.basename(backup_path),
                            'folder': os.path.relpath(root, self.bp_path)
                        })
                    except Exception as ex:
                        logger.debug(f"跳过无效备份文件 {backup_path}: {ex}")
                        continue

        if not backup_files:
            self.show_info_dialog("提示", "在BP文件夹中未找到备份文件 (.bak)")
            return

        self.log(f"📊 找到 {len(backup_files)} 个备份文件")

        # 创建备份文件列表
        backup_list_items = []

        for i, backup in enumerate(backup_files):
            # 创建每行显示的内容
            status_color = ft.Colors.GREEN if backup['original_exists'] else ft.Colors.RED
            status_text = "原始文件存在" if backup['original_exists'] else "原始文件已删除"

            file_row = ft.Row([
                ft.Column([
                    ft.Text(f"{i+1}. {backup['filename']}", size=12, weight=ft.FontWeight.BOLD),
                    ft.Text(f"位置: {backup['folder']}", size=11, color=ft.Colors.GREY),
                    ft.Text(f"状态: {status_text}", size=11, color=status_color),
                    ft.Text(f"大小: {backup['size']:,} bytes, 修改: {backup['modified']}", size=11, color=ft.Colors.GREY),
                ], expand=True),
                ft.Column([
                    ft.ElevatedButton("预览",
                        on_click=lambda e, b=backup: self._preview_backup_file(b),
                        style=ft.ButtonStyle(color=ft.Colors.BLUE, bgcolor=ft.Colors.BLUE_50),
                        width=80
                    ),
                    ft.ElevatedButton("恢复",
                        on_click=lambda e, b=backup: self._restore_backup_file(b),
                        style=ft.ButtonStyle(color=ft.Colors.GREEN, bgcolor=ft.Colors.GREEN_50),
                        width=80
                    ),
                    ft.ElevatedButton("删除",
                        on_click=lambda e, b=backup: self._delete_backup_file(b),
                        style=ft.ButtonStyle(color=ft.Colors.RED, bgcolor=ft.Colors.RED_50),
                        width=80
                    ),
                ], spacing=5)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

            backup_list_items.append(file_row)
            backup_list_items.append(ft.Divider(height=5))

        # 移除最后一个分隔线
        if backup_list_items:
            backup_list_items.pop()

        # 创建对话框内容
        dialog_content = ft.Column([
            ft.Text(f"📂 备份文件管理 ({len(backup_files)} 个文件)", size=16, weight=ft.FontWeight.BOLD),
            ft.Text(f"BP文件夹: {self.bp_path}", size=12, color=ft.Colors.GREY),
            ft.Divider(height=10),
            ft.Container(
                content=ft.Column(backup_list_items, spacing=8, scroll=ft.ScrollMode.AUTO),
                height=400,
                padding=10,
                border=ft.Border.all(1, ft.Colors.GREY_300),
                border_radius=5,
            ),
            ft.Divider(height=10),
            ft.Text("操作说明:", size=12, weight=ft.FontWeight.BOLD),
            ft.Text("• 预览: 查看备份文件内容", size=11, color=ft.Colors.GREY),
            ft.Text("• 恢复: 将备份文件还原为原始文件（覆盖）", size=11, color=ft.Colors.GREY),
            ft.Text("• 删除: 永久删除备份文件", size=11, color=ft.Colors.GREY),
            ft.Text("⚠️ 注意: 恢复操作会覆盖当前文件，请谨慎操作", size=11, color=ft.Colors.ORANGE),
        ], scroll=ft.ScrollMode.AUTO)

        def close_dialog(e):
            self.page.pop_dialog()

        # 创建对话框
        dialog = ft.AlertDialog(
            title=ft.Text("💾 备份文件管理"),
            content=dialog_content,
            actions=[
                ft.TextButton("刷新", on_click=lambda e: self._refresh_backup_dialog()),
                ft.TextButton("关闭", on_click=close_dialog),
            ],
        )

        # 保存对话框引用以便刷新
        self._backup_dialog = dialog

        # 显示对话框
        self.page.show_dialog(dialog)

    def _preview_backup_file(self, backup_info):
        """预览备份文件内容"""
        try:
            with open(backup_info['backup_path'], 'r', encoding='utf-8') as f:
                content = f.read()

            # 限制预览内容长度
            preview_length = min(len(content), 2000)
            preview_content = content[:preview_length]
            if len(content) > preview_length:
                preview_content += f"\n\n... (文件过大，已截断，完整大小: {len(content):,} 字符)"

            # 显示预览对话框
            def close_preview(e):
                self.page.pop_dialog()

            preview_dialog = ft.AlertDialog(
                title=ft.Text(f"👁️ 预览备份文件: {backup_info['filename']}"),
                content=ft.Container(
                    content=ft.Text(preview_content, size=11, font_family="Consolas"),
                    height=400,
                    padding=10,
                    border=ft.Border.all(1, ft.Colors.GREY_300),
                ),
                actions=[
                    ft.TextButton("关闭", on_click=close_preview),
                ],
            )

            self.page.show_dialog(preview_dialog)

        except Exception as ex:
            self.show_error_dialog("预览失败", str(ex))

    def _restore_backup_file(self, backup_info):
        """恢复备份文件"""
        # 确认对话框
        def confirm_restore(e):
            self.page.pop_dialog()
            self._execute_restore_backup(backup_info)

        def cancel_restore(e):
            self.page.pop_dialog()

        confirm_dialog = ft.AlertDialog(
            title=ft.Text("⚠️ 确认恢复"),
            content=ft.Column([
                ft.Text("确定要恢复备份文件吗？", size=14),
                ft.Text(f"备份文件: {backup_info['filename']}", size=12, color=ft.Colors.GREY),
                ft.Text(f"原始文件: {os.path.basename(backup_info['original_path'])}", size=12, color=ft.Colors.GREY),
                ft.Divider(height=10),
                ft.Text("警告: 此操作将覆盖当前原始文件，且不可撤销！", size=12, color=ft.Colors.RED, weight=ft.FontWeight.BOLD),
            ], tight=True, spacing=10),
            actions=[
                ft.TextButton("取消", on_click=cancel_restore),
                ft.TextButton("确认恢复", on_click=confirm_restore, style=ft.ButtonStyle(color=ft.Colors.RED)),
            ],
        )

        self.page.show_dialog(confirm_dialog)

    def _execute_restore_backup(self, backup_info):
        """执行备份恢复操作"""
        try:
            import shutil

            # 备份当前原始文件（如果存在）
            if os.path.exists(backup_info['original_path']):
                temp_backup = backup_info['original_path'] + '.temp.bak'
                shutil.copy2(backup_info['original_path'], temp_backup)

            # 恢复备份文件
            shutil.copy2(backup_info['backup_path'], backup_info['original_path'])

            self.log(f"✅ 已恢复备份文件: {backup_info['filename']} -> {os.path.basename(backup_info['original_path'])}")

            # 显示成功对话框
            def close_success(e):
                self.page.pop_dialog()
                # 刷新备份对话框
                if hasattr(self, '_backup_dialog'):
                    self.page.pop_dialog()
                    self.show_backup_management_dialog()

            success_dialog = ft.AlertDialog(
                title=ft.Text("✅ 恢复成功"),
                content=ft.Text("已成功恢复备份文件\n原始文件已更新"),
                actions=[
                    ft.TextButton("确定", on_click=close_success),
                ],
            )

            self.page.show_dialog(success_dialog)

        except Exception as ex:
            self.show_error_dialog("恢复失败", str(ex))

    def _delete_backup_file(self, backup_info):
        """删除备份文件"""
        # 确认对话框
        def confirm_delete(e):
            self.page.pop_dialog()
            self._execute_delete_backup(backup_info)

        def cancel_delete(e):
            self.page.pop_dialog()

        confirm_dialog = ft.AlertDialog(
            title=ft.Text("⚠️ 确认删除"),
            content=ft.Column([
                ft.Text("确定要永久删除此备份文件吗？", size=14),
                ft.Text(f"文件: {backup_info['filename']}", size=12, color=ft.Colors.GREY),
                ft.Text(f"路径: {backup_info['folder']}", size=12, color=ft.Colors.GREY),
                ft.Divider(height=10),
                ft.Text("警告: 此操作不可撤销！", size=12, color=ft.Colors.RED),
            ], tight=True, spacing=10),
            actions=[
                ft.TextButton("取消", on_click=cancel_delete),
                ft.TextButton("确认删除", on_click=confirm_delete, style=ft.ButtonStyle(color=ft.Colors.RED)),
            ],
        )

        self.page.show_dialog(confirm_dialog)

    def _execute_delete_backup(self, backup_info):
        """执行备份文件删除"""
        try:
            os.remove(backup_info['backup_path'])

            self.log(f"🗑️ 已删除备份文件: {backup_info['filename']}")

            # 显示成功对话框
            def close_success(e):
                self.page.pop_dialog()
                # 刷新备份对话框
                if hasattr(self, '_backup_dialog'):
                    self.page.pop_dialog()
                    self.show_backup_management_dialog()

            success_dialog = ft.AlertDialog(
                title=ft.Text("✅ 删除成功"),
                content=ft.Text("已成功删除备份文件"),
                actions=[
                    ft.TextButton("确定", on_click=close_success),
                ],
            )

            self.page.show_dialog(success_dialog)

        except Exception as ex:
            self.show_error_dialog("删除失败", str(ex))

    def translate_mcstructure(self, e):
        """[12] mcstructure 汉化"""
        if not self.bp_path:
            self.show_error_dialog("错误", "请先选择 BP 文件夹")
            self.log("❌ [功能12] 请先选择 BP 文件夹")
            return

        if not self._require_api("功能12"):
            return

        structures_path = os.path.join(self.bp_path, "structures")
        if not os.path.exists(structures_path):
            self.show_error_dialog("错误", f"structures 文件夹不存在:\n{structures_path}")
            self.log(f"❌ [功能12] structures 文件夹不存在: {structures_path}")
            return

        self._run_feature_task(
            method_name="translate_mcstructure",
            log_prefix="[功能12]",
            feature_tag="功能12: mcstructure 汉化",
        )

    def _refresh_backup_dialog(self):
        """刷新备份对话框"""
        if hasattr(self, '_backup_dialog'):
            self.page.pop_dialog()
            self.show_backup_management_dialog()

    def show_import_export_dialog(self, e=None):
        """显示导入/导出管理对话框"""
        # 标记用户交互
        mark_interaction("button_click", "导入/导出管理")

        # 调用对话框模块中的函数

        # 调试日志
        self.log("📥📤 点击了导入/导出管理按钮")
        self.log(f"配置管理器: {self.config_manager}")
        self.log(f"API管理器: {self.api_manager}")
        if self.api_manager:
            self.log(f"术语服务: {self.api_manager.term_service}")
            self.log(f"翻译缓存: {self.api_manager.cache}")

        try:
            dialogs.show_import_export_dialog(
                page=self.page,
                config_manager=self.config_manager,
                terminology_service=self.api_manager.term_service,
                translation_cache=self.api_manager.cache,
                log_callback=self.log
            )
            self.log("✅ 导入/导出对话框已显示")
        except Exception as ex:
            self.log(f"❌ 显示导入/导出对话框时出错: {ex}")
            import traceback
            self.log(f"详细错误: {traceback.format_exc()}")
            # 显示错误对话框
            from ui import dialogs as ui_dialogs
            ui_dialogs.show_error_dialog(self.page, "对话框错误", f"无法显示导入/导出对话框: {ex}")

    def _collect_performance_stats(self) -> dict:
        """收集所有性能统计信息

        Returns:
            包含各维度统计信息的字典
        """
        stats = {}

        # 1. AST缓存统计
        try:
            from core.script_translation import JSASTExtractor
            ast_cache_stats = JSASTExtractor.get_cache_stats()
            stats['ast_cache'] = ast_cache_stats
        except Exception:
            stats['ast_cache'] = {'cache_size': 0, 'total_cached_strings': 0}

        # 2. 翻译缓存统计
        try:
            translation_cache = self.api_manager.cache
            cache_stats = translation_cache.get_cache_stats()
            stats['translation_cache'] = cache_stats
        except Exception:
            stats['translation_cache'] = {'total_cached': 0, 'hits': 0, 'misses': 0}

        # 3. API调用统计
        try:
            api_stats = self.api_manager.get_api_stats() if hasattr(self.api_manager, 'get_api_stats') else {}
            stats['api'] = api_stats
        except Exception:
            stats['api'] = {'total_calls': 0, 'successful_calls': 0, 'failed_calls': 0}

        # 3.5. 实时指标采集器
        try:
            from core.metrics_collector import get_metrics_collector
            collector = get_metrics_collector()
            collector.record_memory()
            stats['realtime'] = collector.get_snapshot()
        except Exception:
            stats['realtime'] = {}

        # 4. 系统信息
        stats['system'] = self._collect_system_info()

        # 5. 应用统计
        stats['application'] = self._analyze_log_files()

        return stats

    @staticmethod
    def _collect_system_info() -> dict:
        """收集系统信息

        Returns:
            系统信息字典
        """
        try:
            import psutil

            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()

            return {
                'memory_usage_mb': memory_info.rss / 1024 / 1024,
                'cpu_percent': process.cpu_percent(interval=0.1),
                'thread_count': process.num_threads(),
                'create_time': datetime.fromtimestamp(process.create_time()).strftime('%Y-%m-%d %H:%M:%S'),
                'runtime_seconds': time.time() - process.create_time()
            }
        except Exception:
            return {
                'memory_usage_mb': 0,
                'cpu_percent': 0,
                'thread_count': 0,
                'create_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'runtime_seconds': 0
            }

    @staticmethod
    def _build_system_info_section(sys_info: dict) -> list:
        """构建系统信息UI部分

        Args:
            sys_info: 系统信息字典

        Returns:
            Flet控件列表
        """
        return [
            ft.Text("💻 系统信息:", size=14, weight=ft.FontWeight.BOLD),
            ft.Text(f"• 内存使用: {sys_info['memory_usage_mb']:.1f} MB", size=12),
            ft.Text(f"• CPU使用率: {sys_info['cpu_percent']:.1f}%", size=12),
            ft.Text(f"• 线程数: {sys_info['thread_count']}", size=12),
            ft.Text(f"• 运行时间: {sys_info['runtime_seconds']:.0f} 秒", size=12),
            ft.Text(f"• 启动时间: {sys_info['create_time']}", size=12),
            ft.Divider(height=10),
        ]

    @staticmethod
    def _build_ast_cache_section(ast_info: dict) -> list:
        """构建AST缓存统计UI部分

        Args:
            ast_info: AST缓存统计字典

        Returns:
            Flet控件列表
        """
        items = [
            ft.Text("🧠 AST缓存统计:", size=14, weight=ft.FontWeight.BOLD),
            ft.Text(f"• 缓存文件数: {ast_info['cache_size']}", size=12),
            ft.Text(f"• 最大缓存大小: {ast_info.get('maxsize', 128)}", size=12),
        ]

        total_access = ast_info.get('hits', 0) + ast_info.get('misses', 0)
        if total_access > 0:
            hit_rate = ast_info.get('hits', 0) / total_access * 100
            items.append(ft.Text(f"• 命中率: {hit_rate:.1f}%", size=12))
            items.append(ft.Text(f"• 命中数: {ast_info.get('hits', 0)} | 未命中数: {ast_info.get('misses', 0)}", size=12))
        else:
            items.append(ft.Text("• 命中率: 无访问记录", size=12))

        items.append(ft.Divider(height=10))
        return items

    @staticmethod
    def _build_translation_cache_section(trans_info: dict) -> list:
        """构建翻译缓存统计UI部分

        Args:
            trans_info: 翻译缓存统计字典

        Returns:
            Flet控件列表
        """
        total_access = trans_info.get('hits', 0) + trans_info.get('misses', 0)
        hit_rate = trans_info.get('hits', 0) / total_access * 100 if total_access > 0 else 0

        return [
            ft.Text("🔤 翻译缓存统计:", size=14, weight=ft.FontWeight.BOLD),
            ft.Text(f"• 缓存条目数: {trans_info.get('total_cached', 0)}", size=12),
            ft.Text(f"• 缓存命中: {trans_info.get('hits', 0)}", size=12),
            ft.Text(f"• 缓存未命中: {trans_info.get('misses', 0)}", size=12),
            ft.Text(f"• 命中率: {hit_rate:.1f}%", size=12),
            ft.Divider(height=10),
        ]

    @staticmethod
    def _build_api_stats_section(api_info: dict) -> list:
        """构建API统计UI部分

        Args:
            api_info: API统计字典

        Returns:
            Flet控件列表
        """
        success_rate = api_info.get('successful_calls', 0) / api_info.get('total_calls', 1) * 100 if api_info.get('total_calls', 0) > 0 else 0

        return [
            ft.Text("🌐 API调用统计:", size=14, weight=ft.FontWeight.BOLD),
            ft.Text(f"• 总调用次数: {api_info.get('total_calls', 0)}", size=12),
            ft.Text(f"• 成功调用: {api_info.get('successful_calls', 0)}", size=12),
            ft.Text(f"• 失败调用: {api_info.get('failed_calls', 0)}", size=12),
            ft.Text(f"• 成功率: {success_rate:.1f}%", size=12),
            ft.Divider(height=10),
        ]

    @staticmethod
    def _build_app_stats_section(app_info: dict) -> list:
        """构建应用统计UI部分

        Args:
            app_info: 应用统计字典

        Returns:
            Flet控件列表
        """
        items = [
            ft.Text("📈 应用统计:", size=14, weight=ft.FontWeight.BOLD),
        ]

        if app_info:
            items.append(ft.Text(f"• 总翻译文件数: {app_info.get('total_files', 0)}", size=12))
            items.append(ft.Text(f"• 总翻译字符串数: {app_info.get('total_strings', 0)}", size=12))
            items.append(ft.Text(f"• 平均翻译速度: {app_info.get('avg_speed', 0):.1f} 字符串/秒", size=12))
            if app_info.get('last_operation'):
                items.append(ft.Text(f"• 最后操作: {app_info['last_operation']}", size=12))

        items.append(ft.Divider(height=10))
        return items

    @staticmethod
    def _build_realtime_section(realtime: dict) -> list:
        """构建实时采集指标UI部分

        Args:
            realtime: 实时指标字典

        Returns:
            Flet控件列表
        """
        if not realtime:
            return []

        uptime = realtime.get('uptime_seconds', 0)
        m, s = divmod(int(uptime), 60)
        h, m = divmod(m, 60)

        items = [
            ft.Text("⏱️ 实时采集指标:", size=14, weight=ft.FontWeight.BOLD),
            ft.Text(f"• 运行时长: {h}h {m}m {s}s", size=12),
            ft.Text(f"• 累计翻译: {realtime.get('total_translated', 0)} 条", size=12),
            ft.Text(f"• 累计API调用: {realtime.get('total_api_calls', 0)} 次 (错误 {realtime.get('total_api_errors', 0)} 次)", size=12),
            ft.Text(f"• 平均翻译速率: {realtime.get('avg_translation_rate', 0):.1f} 条/秒", size=12),
            ft.Text(f"• 平均API响应: {realtime.get('avg_response_time', 0)*1000:.0f} ms", size=12),
        ]

        mem_history = realtime.get('memory_history_mb', [])
        if mem_history:
            items.append(ft.Text(f"• 当前内存: {mem_history[-1]:.1f} MB (最近{len(mem_history)}个采样点)", size=12))

        items.append(ft.Divider(height=10))
        return items

    @staticmethod
    def _build_suggestions_section(stats: dict) -> list:
        """构建性能优化建议UI部分

        Args:
            stats: 完整统计信息字典

        Returns:
            Flet控件列表
        """
        ast_info = stats['ast_cache']
        trans_info = stats['translation_cache']
        sys_info = stats['system']
        api_info = stats['api']

        total_access = trans_info.get('hits', 0) + trans_info.get('misses', 0)
        hit_rate = trans_info.get('hits', 0) / total_access * 100 if total_access > 0 else 0
        success_rate = api_info.get('successful_calls', 0) / api_info.get('total_calls', 1) * 100 if api_info.get('total_calls', 0) > 0 else 0

        suggestions = []

        if ast_info['cache_size'] < 10:
            suggestions.append("• 考虑处理更多JS文件以提高AST缓存效率")

        if hit_rate < 50 and trans_info.get('total_cached', 0) > 0:
            suggestions.append("• 翻译缓存命中率较低，可能需要调整缓存策略")

        if sys_info['memory_usage_mb'] > 500:
            suggestions.append("• 内存使用较高，建议定期重启应用程序")

        if success_rate < 80 and api_info.get('total_calls', 0) > 10:
            suggestions.append("• API调用成功率较低，请检查网络连接或API配置")

        if not suggestions:
            suggestions.append("• 当前性能表现良好，继续保持！")

        items = [ft.Text("💡 性能优化建议:", size=14, weight=ft.FontWeight.BOLD)]
        for suggestion in suggestions:
            items.append(ft.Text(suggestion, size=12, color=ft.Colors.BLUE))

        items.append(ft.Divider(height=10))
        items.append(ft.Text("🔄 点击'刷新'按钮更新统计信息", size=11, color=ft.Colors.GREY))
        return items

    def show_performance_monitor_dialog(self, e=None):
        """显示性能监控和统计对话框"""
        # 标记用户交互
        mark_interaction("button_click", "性能监控")

        # 收集性能统计信息
        stats = self._collect_performance_stats()

        # 创建对话框内容
        dialog_content = []
        dialog_content.append(ft.Text("📊 性能监控和统计", size=18, weight=ft.FontWeight.BOLD))
        dialog_content.append(ft.Divider(height=10))

        dialog_content.extend(self._build_system_info_section(stats['system']))
        dialog_content.extend(self._build_ast_cache_section(stats['ast_cache']))
        dialog_content.extend(self._build_translation_cache_section(stats['translation_cache']))
        dialog_content.extend(self._build_api_stats_section(stats['api']))
        dialog_content.extend(self._build_app_stats_section(stats['application']))
        dialog_content.extend(self._build_realtime_section(stats.get('realtime', {})))
        dialog_content.extend(self._build_suggestions_section(stats))

        def close_dialog(e):
            self.page.pop_dialog()

        def refresh_dialog(e):
            self.page.pop_dialog()
            self.show_performance_monitor_dialog()

        # 创建对话框
        dialog = ft.AlertDialog(
            title=ft.Text("📊 性能监控和统计"),
            content=ft.Container(
                content=ft.Column(dialog_content, scroll=ft.ScrollMode.AUTO),
                height=500,
                padding=10,
            ),
            actions=[
                ft.TextButton("刷新", on_click=refresh_dialog),
                ft.TextButton("关闭", on_click=close_dialog),
            ],
        )

        self.page.show_dialog(dialog)

    def _analyze_log_files(self):
        """分析日志文件获取应用统计信息"""
        import os

        stats = {
            'total_files': 0,
            'total_strings': 0,
            'avg_speed': 0,
            'last_operation': None
        }

        try:
            log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
            if not os.path.exists(log_dir):
                return stats

            # 查找最新的日志文件
            log_files = []
            for file in os.listdir(log_dir):
                if file.startswith('minecraft_translator_') and file.endswith('.log'):
                    log_files.append(os.path.join(log_dir, file))

            if not log_files:
                return stats

            # 按修改时间排序，获取最新的日志文件
            latest_log = max(log_files, key=os.path.getmtime)

            with open(latest_log, 'r', encoding='utf-8') as f:
                log_content = f.read()

            # 提取翻译相关统计
            file_pattern = r'成功 (\d+) 个，失败 (\d+) 个'
            string_pattern = r'翻译 (\d+) 处|翻译 (\d+) 个字符串'
            speed_pattern = r'速度.*?(\d+\.?\d*) 字符串/秒'

            file_matches = re.findall(file_pattern, log_content)
            string_matches = re.findall(string_pattern, log_content)
            speed_matches = re.findall(speed_pattern, log_content)

            if file_matches:
                stats['total_files'] = sum(int(match[0]) for match in file_matches)

            if string_matches:
                total_strings = 0
                for match in string_matches:
                    # match可能是元组，需要处理两种模式
                    if isinstance(match, tuple):
                        for num in match:
                            if num:
                                total_strings += int(num)
                    else:
                        total_strings += int(match)
                stats['total_strings'] = total_strings

            if speed_matches:
                speeds = [float(speed) for speed in speed_matches]
                stats['avg_speed'] = sum(speeds) / len(speeds) if speeds else 0

            # 提取最后操作时间
            time_pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*?开始.*?功能'
            time_matches = re.findall(time_pattern, log_content)
            if time_matches:
                stats['last_operation'] = time_matches[-1]

        except Exception:
            pass

        return stats

