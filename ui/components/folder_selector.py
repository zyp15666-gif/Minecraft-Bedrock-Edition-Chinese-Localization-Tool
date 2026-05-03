#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件夹选择组件模块

提供 BP/RP 文件夹选择功能。
支持 ft.FilePicker 和 tkinter 两种模式。

使用方式：
    from ui.components.folder_selector import FolderSelector

    folder_selector = FolderSelector(ui_scale, log_func)
    folder_section = folder_selector.create()
"""

import flet as ft
from typing import Callable, Dict, Any, Optional, Tuple
import os


class FolderSelector:
    """
    文件夹选择器

    提供：
    - BP 文件夹选择
    - RP 文件夹选择
    - 文件夹有效性验证
    """

    def __init__(self, ui_scale: Dict[str, Any], log_func: Optional[Callable] = None):
        """
        初始化文件夹选择器

        Args:
            ui_scale: UI 缩放配置
            log_func: 日志回调函数
        """
        self.ui_scale = ui_scale
        self.log_func = log_func or (lambda x: None)

        self.bp_folder: Optional[str] = None
        self.rp_folder: Optional[str] = None

        self.bp_path_label = ft.Text("未选择", color=ft.Colors.GREY)
        self.rp_path_label = ft.Text("未选择", color=ft.Colors.GREY)

        self._file_picker: Optional[ft.FilePicker] = None

    def log(self, message: str):
        """记录日志"""
        self.log_func(message)

    def set_file_picker(self, file_picker: ft.FilePicker):
        """设置文件选择器实例"""
        self._file_picker = file_picker

    def create(self) -> ft.Container:
        """
        创建文件夹选择区域

        Returns:
            文件夹选择容器
        """
        bp_row = self._create_folder_row("BP", self.bp_path_label, self._on_bp_select)
        rp_row = self._create_folder_row("RP", self.rp_path_label, self._on_rp_select)

        folder_section = ft.Container(
            content=ft.Column([
                ft.Text("📁 文件夹选择", size=self.ui_scale['section_title_size'], weight=ft.FontWeight.BOLD),
                ft.Container(height=5),
                bp_row,
                ft.Container(height=8),
                rp_row,
            ]),
            padding=15,
            bgcolor=ft.Colors.with_opacity(0.3, ft.Colors.BLUE_100),
            border_radius=10,
        )

        return folder_section

    def _create_folder_row(self, label: str, text_field: ft.Text, on_select) -> ft.Row:
        """创建文件夹选择行"""
        return ft.Row([
            ft.Text(f"{label} 文件夹:", size=self.ui_scale['body_size'], width=80),
            ft.Container(
                content=text_field,
                expand=True,
                bgcolor=ft.Colors.GREY_200,
                border_radius=5,
                padding=5,
            ),
            ft.ElevatedButton(
                "选择",
                icon="folder_open",
                on_click=on_select,
                style=ft.ButtonStyle(
                    bgcolor=ft.Colors.BLUE_500,
                    color=ft.Colors.WHITE,
                ),
            ),
        ], alignment=ft.MainAxisAlignment.START)

    async def _on_bp_select(self, e: ft.FilePickerResultEvent):
        """BP 文件夹选择处理"""
        if self._file_picker:
            path = await self._file_picker.get_directory_path()
            if path:
                self.bp_folder = path
                folder_name = os.path.basename(path) or path
                self.bp_path_label.value = folder_name
                self.bp_path_label.color = ft.Colors.GREEN
                self.bp_path_label.update()
                self.log(f"已选择 BP 文件夹: {path}")

    async def _on_rp_select(self, e: ft.FilePickerResultEvent):
        """RP 文件夹选择处理"""
        if self._file_picker:
            path = await self._file_picker.get_directory_path()
            if path:
                self.rp_folder = path
                folder_name = os.path.basename(path) or path
                self.rp_path_label.value = folder_name
                self.rp_path_label.color = ft.Colors.GREEN
                self.rp_path_label.update()
                self.log(f"已选择 RP 文件夹: {path}")

    def validate_folders(self) -> Tuple[bool, str]:
        """
        验证文件夹选择是否有效

        Returns:
            (是否有效, 错误消息)
        """
        if not self.bp_folder:
            return False, "请选择 BP 文件夹"
        if not self.rp_folder:
            return False, "请选择 RP 文件夹"
        if not self._is_valid_bedrock_folder(self.bp_folder):
            return False, "BP 文件夹无效，必须包含 'behavior pack' 目录"
        if not self._is_valid_bedrock_folder(self.rp_folder):
            return False, "RP 文件夹无效，必须包含 'resource pack' 目录"
        return True, ""

    def _is_valid_bedrock_folder(self, folder: str) -> bool:
        """检查是否为有效的基岩版文件夹"""
        folder_lower = folder.lower()
        return 'behavior pack' in folder_lower or 'behavior_pack' in folder_lower or \
               'resource pack' in folder_lower or 'resource_pack' in folder_lower

    def get_folders(self) -> Tuple[Optional[str], Optional[str]]:
        """
        获取选择的文件夹

        Returns:
            (bp_folder, rp_folder)
        """
        return self.bp_folder, self.rp_folder

    def set_folders(self, bp_folder: Optional[str], rp_folder: Optional[str]):
        """
        设置文件夹

        Args:
            bp_folder: BP 文件夹路径
            rp_folder: RP 文件夹路径
        """
        if bp_folder:
            self.bp_folder = bp_folder
            folder_name = os.path.basename(bp_folder) or bp_folder
            self.bp_path_label.value = folder_name
            self.bp_path_label.color = ft.Colors.GREEN
            self.bp_path_label.update()

        if rp_folder:
            self.rp_folder = rp_folder
            folder_name = os.path.basename(rp_folder) or rp_folder
            self.rp_path_label.value = folder_name
            self.rp_path_label.color = ft.Colors.GREEN
            self.rp_path_label.update()

    def clear(self):
        """清空选择"""
        self.bp_folder = None
        self.rp_folder = None
        self.bp_path_label.value = "未选择"
        self.bp_path_label.color = ft.Colors.GREY
        self.rp_path_label.value = "未选择"
        self.rp_path_label.color = ft.Colors.GREY
        self.bp_path_label.update()
        self.rp_path_label.update()
