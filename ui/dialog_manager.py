#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对话框管理器 - 统一管理所有UI对话框

从main_window.py中提取，负责：
- 错误/成功/信息对话框
- 添加API对话框
- 导入/导出对话框
- 性能监控对话框
- JS翻译预览对话框
"""

import flet as ft
from typing import Optional, Callable, Dict, Any, List


class DialogManager:
    """对话框管理器"""

    def __init__(self, page: ft.Page, config_manager, api_manager, log_callback: Callable):
        """初始化对话框管理器

        Args:
            page: Flet页面对象
            config_manager: 配置管理器
            api_manager: API管理器
            log_callback: 日志回调函数
        """
        self.page = page
        self.config_manager = config_manager
        self.api_manager = api_manager
        self.log = log_callback

    def show_error_dialog(self, title: str, message: str):
        """显示错误对话框"""
        def close(e):
            self.page.pop_dialog()

        dialog = ft.AlertDialog(
            title=ft.Text(f"❌ {title}"),
            content=ft.Text(message),
            actions=[ft.TextButton("确定", on_click=close)],
        )
        self.page.show_dialog(dialog)

    def show_success_dialog(self, title: str, message: str):
        """显示成功对话框"""
        def close(e):
            self.page.pop_dialog()

        dialog = ft.AlertDialog(
            title=ft.Text(f"✅ {title}"),
            content=ft.Text(message),
            actions=[ft.TextButton("确定", on_click=close)],
        )
        self.page.show_dialog(dialog)

    def show_info_dialog(self, title: str, message: str):
        """显示信息对话框"""
        def close(e):
            self.page.pop_dialog()

        dialog = ft.AlertDialog(
            title=ft.Text(f"ℹ️ {title}"),
            content=ft.Text(message),
            actions=[ft.TextButton("确定", on_click=close)],
        )
        self.page.show_dialog(dialog)

    def show_confirm_dialog(
        self,
        title: str,
        message: str,
        on_confirm: Callable,
        confirm_text: str = "确定",
        cancel_text: str = "取消",
        is_dangerous: bool = False
    ):
        """显示确认对话框

        Args:
            title: 对话框标题
            message: 对话框消息
            on_confirm: 确认回调函数
            confirm_text: 确认按钮文本
            cancel_text: 取消按钮文本
            is_dangerous: 是否为危险操作（使用红色确认按钮）
        """
        def confirm(e):
            self.page.pop_dialog()
            on_confirm()

        def cancel(e):
            self.page.pop_dialog()

        dialog = ft.AlertDialog(
            title=ft.Text(title),
            content=ft.Text(message),
            actions=[
                ft.TextButton(cancel_text, on_click=cancel),
                ft.TextButton(
                    confirm_text,
                    on_click=confirm,
                    style=ft.ButtonStyle(color=ft.Colors.RED) if is_dangerous else None
                ),
            ],
        )
        self.page.show_dialog(dialog)

    def show_log_dialog(self, log_text: List[str], title: str = "日志"):
        """显示日志对话框"""
        def close(e):
            self.page.pop_dialog()

        log_content = ft.Container(
            content=ft.Column([
                ft.Text(f"📋 {title}", size=16, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Container(
                    content=ft.Column([
                        ft.Text(line, size=11, font_family="Consolas")
                        for line in log_text[-100:]
                    ]),
                    height=400,
                    width=600,
                ),
            ]),
            padding=10,
        )

        dialog = ft.AlertDialog(
            title=ft.Text(f"📋 {title}"),
            content=log_content,
            actions=[ft.TextButton("关闭", on_click=close)],
        )
        self.page.show_dialog(dialog)

    def show_performance_monitor_dialog(self, stats: Dict[str, Any], ui_scale: Dict[str, Any]):
        """显示性能监控对话框"""
        def close(e):
            self.page.pop_dialog()

        def refresh(e):
            self.page.pop_dialog()

        content_items = [
            ft.Text("📊 性能监控和统计", size=18, weight=ft.FontWeight.BOLD),
            ft.Divider(height=10),
        ]

        if 'system' in stats:
            sys_info = stats['system']
            content_items.extend([
                ft.Text("💻 系统信息:", size=14, weight=ft.FontWeight.BOLD),
                ft.Text(f"• 内存使用: {sys_info.get('memory_usage_mb', 0):.1f} MB", size=12),
                ft.Text(f"• CPU使用率: {sys_info.get('cpu_percent', 0):.1f}%", size=12),
                ft.Text(f"• 线程数: {sys_info.get('thread_count', 0)}", size=12),
                ft.Divider(height=10),
            ])

        if 'translation_cache' in stats:
            cache_info = stats['translation_cache']
            total = cache_info.get('hits', 0) + cache_info.get('misses', 0)
            hit_rate = cache_info.get('hits', 0) / total * 100 if total > 0 else 0
            content_items.extend([
                ft.Text("🔤 翻译缓存统计:", size=14, weight=ft.FontWeight.BOLD),
                ft.Text(f"• 缓存条目数: {cache_info.get('total_cached', 0)}", size=12),
                ft.Text(f"• 命中率: {hit_rate:.1f}%", size=12),
                ft.Divider(height=10),
            ])

        if 'api' in stats:
            api_info = stats['api']
            success_rate = 0
            if api_info.get('total_calls', 0) > 0:
                success_rate = api_info.get('successful_calls', 0) / api_info.get('total_calls', 0) * 100
            content_items.extend([
                ft.Text("🌐 API调用统计:", size=14, weight=ft.FontWeight.BOLD),
                ft.Text(f"• 总调用次数: {api_info.get('total_calls', 0)}", size=12),
                ft.Text(f"• 成功率: {success_rate:.1f}%", size=12),
            ])

        dialog_content = ft.Column(content_items, scroll=ft.ScrollMode.AUTO)

        dialog = ft.AlertDialog(
            title=ft.Text("📊 性能监控和统计"),
            content=ft.Container(dialog_content, height=500, padding=10),
            actions=[
                ft.TextButton("刷新", on_click=refresh),
                ft.TextButton("关闭", on_click=close),
            ],
        )
        self.page.show_dialog(dialog)

    def show_backup_preview_dialog(self, backup_info: Dict[str, Any]):
        """显示备份文件预览对话框"""
        def close(e):
            self.page.pop_dialog()

        preview_content = backup_info.get('content', '')[:2000]
        if len(backup_info.get('content', '')) > 2000:
            preview_content += f"\n\n... (已截断，完整大小: {len(backup_info.get('content', '')):,} 字符)"

        dialog = ft.AlertDialog(
            title=ft.Text(f"👁️ 预览备份文件: {backup_info.get('filename', '')}"),
            content=ft.Container(
                content=ft.Text(preview_content, size=11, font_family="Consolas"),
                height=400,
                padding=10,
                border=ft.Border.all(1, ft.Colors.GREY_300),
            ),
            actions=[ft.TextButton("关闭", on_click=close)],
        )
        self.page.show_dialog(dialog)

    def show_backup_restore_confirm_dialog(self, backup_info: Dict[str, Any], on_confirm: Callable):
        """显示备份恢复确认对话框"""
        def confirm(e):
            self.page.pop_dialog()
            on_confirm()

        def cancel(e):
            self.page.pop_dialog()

        dialog = ft.AlertDialog(
            title=ft.Text("⚠️ 确认恢复"),
            content=ft.Column([
                ft.Text("确定要恢复备份文件吗？", size=14),
                ft.Text(f"备份文件: {backup_info.get('filename', '')}", size=12, color=ft.Colors.GREY),
                ft.Text("警告: 此操作将覆盖当前文件，且不可撤销！", size=12, color=ft.Colors.RED, weight=ft.FontWeight.BOLD),
            ], tight=True, spacing=10),
            actions=[
                ft.TextButton("取消", on_click=cancel),
                ft.TextButton("确认恢复", on_click=confirm, style=ft.ButtonStyle(color=ft.Colors.RED)),
            ],
        )
        self.page.show_dialog(dialog)

    def show_backup_delete_confirm_dialog(self, backup_info: Dict[str, Any], on_confirm: Callable):
        """显示备份删除确认对话框"""
        def confirm(e):
            self.page.pop_dialog()
            on_confirm()

        def cancel(e):
            self.page.pop_dialog()

        dialog = ft.AlertDialog(
            title=ft.Text("⚠️ 确认删除"),
            content=ft.Column([
                ft.Text("确定要永久删除此备份文件吗？", size=14),
                ft.Text(f"文件: {backup_info.get('filename', '')}", size=12, color=ft.Colors.GREY),
                ft.Text("警告: 此操作不可撤销！", size=12, color=ft.Colors.RED),
            ], tight=True, spacing=10),
            actions=[
                ft.TextButton("取消", on_click=cancel),
                ft.TextButton("确认删除", on_click=confirm, style=ft.ButtonStyle(color=ft.Colors.RED)),
            ],
        )
        self.page.show_dialog(dialog)

    def show_js_translation_preview_dialog(
        self,
        analysis_result: Dict[str, Any],
        on_confirm: Callable,
        scale: float = 1.0
    ):
        """显示JS翻译预览对话框"""
        def confirm(e):
            self.page.pop_dialog()
            on_confirm()

        def cancel(e):
            self.page.pop_dialog()

        preview_content = [
            ft.Text(
                f"📊 分析摘要: {analysis_result.get('total_files', 0)} 个文件, "
                f"{analysis_result.get('total_strings', 0)} 个字符串",
                size=14,
                weight=ft.FontWeight.BOLD
            ),
            ft.Text(
                f"⏱️ 预估翻译时间: {analysis_result.get('estimated_time', 0):.1f} 秒",
                size=12,
                color=ft.Colors.GREY
            ),
            ft.Divider(height=10),
            ft.Text("📁 文件列表:", size=13, weight=ft.FontWeight.BOLD),
        ]

        for file_info in analysis_result.get('files', [])[:20]:
            preview_content.append(
                ft.Text(
                    f"• {file_info.get('name', 'unknown')}: "
                    f"{file_info.get('needs_translation', 0)}/{file_info.get('total', 0)}",
                    size=12
                )
            )

        preview_content.extend([
            ft.Divider(height=10),
            ft.Text(
                "⚠️ 注意: 翻译将创建备份文件 (.bak)，如有问题可手动恢复",
                size=11,
                color=ft.Colors.ORANGE
            ),
        ])

        dialog = ft.AlertDialog(
            title=ft.Text("🔍 JS翻译预览"),
            content=ft.Column(preview_content, tight=True, spacing=8, scroll=ft.ScrollMode.AUTO),
            actions=[
                ft.TextButton("取消", on_click=cancel),
                ft.TextButton("确认翻译", on_click=confirm, style=ft.ButtonStyle(color=ft.Colors.GREEN)),
            ],
        )
        self.page.show_dialog(dialog)

    def show_mode_selection_dialog(
        self,
        title: str,
        options: List[Dict[str, Any]],
        on_select: Callable[[int], None]
    ):
        """显示模式选择对话框"""
        def make_handler(index: int):
            def handler(e):
                self.page.pop_dialog()
                on_select(index)
            return handler

        def cancel(e):
            self.page.pop_dialog()

        actions = [ft.TextButton("取消", on_click=cancel)]
        for i, option in enumerate(options):
            actions.insert(0, ft.TextButton(option.get('label', f"选项{i+1}"), on_click=make_handler(i)))

        content_parts = [ft.Text(option.get('description', ''), size=12) for option in options]

        dialog = ft.AlertDialog(
            title=ft.Text(f"🔧 {title}"),
            content=ft.Column(content_parts, tight=True, spacing=10),
            actions=actions,
        )
        self.page.show_dialog(dialog)
