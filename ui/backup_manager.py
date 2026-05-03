#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
备份管理器 - 统一处理所有备份相关的UI操作

从main_window.py中提取，负责：
- 备份文件列表展示
- 备份创建、恢复、删除
- 备份预览
"""

import flet as ft
from typing import List, Dict, Any, Callable, Optional
from pathlib import Path


class BackupManager:
    """备份管理器"""

    def __init__(
        self,
        config_manager,
        dialog_manager,
        log_callback: Callable[[str], None],
        show_preview_callback: Callable[[Dict[str, Any]], None],
        on_restore_callback: Callable[[str], None],
    ):
        """初始化备份管理器

        Args:
            config_manager: 配置管理器
            dialog_manager: 对话框管理器
            log_callback: 日志回调
            show_preview_callback: 显示预览回调
            on_restore_callback: 恢复备份回调
        """
        self.config_manager = config_manager
        self.dialog_manager = dialog_manager
        self.log = log_callback
        self.show_preview = show_preview_callback
        self.on_restore = on_restore_callback

    def on_show_backup_management(self, e):
        """显示备份管理界面"""
        backups = self.config_manager.list_backups()
        if not backups:
            self.dialog_manager.show_info_dialog("备份管理", "当前没有任何备份文件")
            return

        self._show_backup_list_dialog(backups)

    def _show_backup_list_dialog(self, backups: List[str]):
        """显示备份列表对话框"""
        def on_select_backup(index: int):
            if 0 <= index < len(backups):
                backup_name = backups[index]
                self._show_backup_options(backup_name)

        options = [{'label': name, 'description': f'备份文件: {name}'} for name in backups]
        self.dialog_manager.show_mode_selection_dialog(
            title="备份管理 - 选择备份",
            options=options,
            on_select=on_select_backup
        )

    def _show_backup_options(self, backup_name: str):
        """显示备份操作选项"""
        backup_info = self._get_backup_info(backup_name)

        content = ft.Column([
            ft.Text(f"备份文件: {backup_name}", size=14, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            ft.Text(f"创建时间: {backup_info.get('created_time', '未知')}", size=12),
            ft.Text(f"文件大小: {backup_info.get('size', '未知')}", size=12),
            ft.Divider(),
        ], tight=True)

        def on_preview(e):
            self.show_preview(backup_info)

        def on_restore(e):
            self.dialog_manager.show_backup_restore_confirm_dialog(
                backup_info,
                lambda: self.on_restore(backup_name)
            )

        def on_delete(e):
            self.dialog_manager.show_backup_delete_confirm_dialog(
                backup_info,
                lambda: self._delete_backup(backup_name)
            )

        preview_btn = ft.ElevatedButton("👁️ 预览", on_click=on_preview)
        restore_btn = ft.ElevatedButton("🔄 恢复", on_click=on_restore, style=ft.ButtonStyle(color=ft.Colors.GREEN))
        delete_btn = ft.ElevatedButton("🗑️ 删除", on_click=on_delete, style=ft.ButtonStyle(color=ft.Colors.RED))

        dialog = ft.AlertDialog(
            title=ft.Text("📋 备份操作"),
            content=content,
            actions=[
                ft.TextButton("取消", on_click=lambda e: self.dialog_manager.page.pop_dialog()),
                preview_btn,
                restore_btn,
                delete_btn,
            ],
        )
        self.dialog_manager.page.show_dialog(dialog)

    def _get_backup_info(self, backup_name: str) -> Dict[str, Any]:
        """获取备份文件信息"""
        backup_dir = self.config_manager.config_path.parent / "backups"
        backup_path = backup_dir / backup_name

        info = {
            'filename': backup_name,
            'path': str(backup_path),
            'content': '',
        }

        if backup_path.exists():
            stat = backup_path.stat()
            info['size'] = self._format_size(stat.st_size)
            info['created_time'] = self._format_time(stat.st_mtime)

            try:
                with open(backup_path, 'r', encoding='utf-8') as f:
                    info['content'] = f.read()
            except Exception:
                pass

        return info

    def _delete_backup(self, backup_name: str):
        """删除备份"""
        try:
            backup_dir = self.config_manager.config_path.parent / "backups"
            backup_path = backup_dir / backup_name

            if backup_path.exists():
                backup_path.unlink()
                self.log(f"✅ 已删除备份: {backup_name}")
        except Exception as e:
            self.dialog_manager.show_error_dialog("删除失败", str(e))

    def _format_size(self, size: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def _format_time(self, timestamp: float) -> str:
        """格式化时间戳"""
        from datetime import datetime
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
