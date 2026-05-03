#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
功能按钮组件模块

提供功能按钮区域的构建函数。

使用方式：
    from ui.tabs.function_buttons import create_function_buttons

    container, button_dict, function_buttons = create_function_buttons(context, callbacks)
"""

import flet as ft
from typing import TYPE_CHECKING, Dict, Callable, List, Tuple

if TYPE_CHECKING:
    from ui.tabs.context import UIContext


BUTTON_CALLBACK_MAP = {
    'extract_only': 'on_extract_only',
    'extract_and_translate': 'on_extract_and_translate',
    'replace_display_names': 'replace_display_names',
    'one_click_service': 'one_click_service',
    'batch_delete_value': 'remove_value_for_specified_folder',
    'batch_restore_value': 'restore_value_for_specified_folder',
    'translate_lang_file': 'translate_lang_file',
    'translate_single_js_file': 'process_guidebook_js',
    'adapt_entity_display_names': 'extract_entity_display_names',
    'script_hardcode_translation': 'script_hardcode_translation',
    'backup_management': 'on_backup_management',
    'translate_mcstructure': 'translate_mcstructure',
}

BUTTON_TOOLTIPS = {
    'extract_only': "仅提取汉化key，不进行翻译。需要先选择BP文件夹。",
    'extract_and_translate': "提取汉化key并使用AI翻译。需要先选择BP文件夹。",
    'replace_display_names': "替换BP文件夹中所有display_name字段。需要先选择BP文件夹。",
    'batch_delete_value': "批量删除指定文件夹中JSON文件的value字段（转为字符串格式）。需要先选择文件夹。",
    'batch_restore_value': "批量还原指定文件夹中JSON文件的value字段（恢复为对象格式）。需要先选择文件夹。",
    'translate_lang_file': "翻译独立的.lang语言文件。需要先选择.lang文件。",
    'adapt_entity_display_names': "提取实体信息并适配显示名称。需要先选择BP文件夹。",
    'translate_single_js_file': "使用 AST+AI 智能翻译单个 JavaScript 文件（支持硬编码文本）。",
    'script_hardcode_translation': "脚本文件夹硬编码汉化测试版，可能会修改源代码。请慎用！",
    'backup_management': "管理BP文件夹中的备份文件（.bak文件），支持预览、恢复和删除操作。需要先选择BP文件夹。",
    'one_click_service': "一键完成提取、翻译、替换等全套操作。需要先选择BP文件夹。",
    'translate_mcstructure': "汉化BP文件夹中structures目录下的所有mcstructure文件（书本和告示牌）。需要先选择BP文件夹。",
}


def create_function_buttons(
    context: 'UIContext',
    callbacks: Dict[str, Callable]
) -> Tuple[ft.Control, Dict[str, ft.ElevatedButton], List[ft.ElevatedButton]]:
    """
    创建功能按钮区域（使用动态缩放 + 2K下1.2倍放大 + 文件夹检查）

    按钮从配置文件 ui.function_buttons 读取，支持动态显示/隐藏和排序。

    Args:
        context: UI上下文对象
        callbacks: 回调函数字典

    Returns:
        元组(container, button_dict, function_buttons):
            container: 功能按钮区域容器
            button_dict: 按钮引用字典，键为按钮ID
            function_buttons: 按钮列表（按配置排序）
    """
    s = context.ui_scale

    button_config_list = context.get_function_buttons_config()

    enabled_buttons = [btn for btn in button_config_list if btn.get('enabled', True)]
    enabled_buttons = sorted(enabled_buttons, key=lambda x: x.get('order', 999))

    button_dict = {}
    function_buttons = []

    for btn_cfg in enabled_buttons:
        btn_id = btn_cfg.get('id', '')
        callback_key = BUTTON_CALLBACK_MAP.get(btn_id)
        callback_fn = callbacks.get(callback_key) if callback_key else None
        label = btn_cfg.get('label', f'[{btn_id}]')
        icon_name = btn_cfg.get('icon', 'BUG_REPORT')
        tooltip = BUTTON_TOOLTIPS.get(btn_id, '')

        # DEBUG: print all buttons being created
        #print(f"[DEBUG create_buttons] btn_id={btn_id}, callback_key={callback_key}, callback_fn={'SET' if callback_fn else 'None'}")

        try:
            icon = getattr(ft.Icons, icon_name, ft.Icons.BUG_REPORT)
        except Exception:
            icon = ft.Icons.BUG_REPORT

        btn = ft.ElevatedButton(
            label,
            icon=icon,
            on_click=callback_fn,
            expand=True,
            height=s['button_height'],
            disabled=True,
            tooltip=tooltip,
            style=ft.ButtonStyle(
                text_style=ft.TextStyle(size=s['button_text_size'])
            ),
        )

        button_dict[btn_id] = btn
        function_buttons.append(btn)

    row_controls = []
    for btn in function_buttons:
        row_controls.append(ft.Column([btn], col=6))

    container = ft.Container(
        content=ft.Column([
            ft.Text("⚙️ 功能", size=s['section_title_size'],
                    weight=ft.FontWeight.BOLD, color=context.get_color('text_primary')),
            ft.ResponsiveRow(
                row_controls,
                spacing=int(10 * context.scale),
            ),
        ]),
        padding=s['padding'],
        bgcolor=context.get_color('primary_bg'),
        border_radius=s['border_radius'],
    )

    return container, button_dict, function_buttons
