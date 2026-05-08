#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置标签页组件

提供配置管理功能。

使用方式：
    from ui.tabs.config_tab import create_config_tab

    config_container = create_config_tab(context, config, callbacks)
"""

import threading
from typing import TYPE_CHECKING, Any, Callable, Dict

import flet as ft

if TYPE_CHECKING:
    from ui.tabs.context import UIContext


def create_config_tab(
    context: 'UIContext',
    config: Dict[str, Any],
    callbacks: Dict[str, Callable]
) -> ft.Control:
    """
    创建配置标签页（使用动态缩放）

    由于配置标签页代码较长，这里提供简化版本。
    完整实现请参考 ui/tabs/__init__.py 中的原始代码。

    Args:
        context: UI上下文对象
        config: 配置字典（将被修改）
        callbacks: 回调函数字典

    Returns:
        配置标签页容器
    """
    s = context.ui_scale
    scale = context.scale

    save_config = callbacks.get('save_config')
    show_add_api_dialog = callbacks.get('show_add_api_dialog')
    get_api_list = callbacks.get('get_api_list')
    show_import_export_dialog = callbacks.get('show_import_export_dialog')

    # 获取按钮配置
    button_config_list = context.get_function_buttons_config()

    # ========== 自动保存回调 ==========
    def _create_switch_change_handler(key_path: list, save_callback):
        """创建 Switch 的 on_change 回调"""
        def handler(e):
            def do_save():
                config_ref = config
                for key in key_path[:-1]:
                    if key not in config_ref:
                        config_ref[key] = {}
                    config_ref = config_ref[key]
                config_ref[key_path[-1]] = e.control.value
                if save_callback:
                    save_callback()
            threading.Timer(0.3, do_save).start()
        return handler

    def _create_text_change_handler(key_path: list, save_callback, value_type=str):
        """创建 TextField 的 on_change 回调"""
        def handler(e):
            def do_save():
                config_ref = config
                for key in key_path[:-1]:
                    if key not in config_ref:
                        config_ref[key] = {}
                    config_ref = config_ref[key]
                raw_value = e.control.value.strip() if e.control.value else ''
                if value_type == int:
                    try:
                        config_ref[key_path[-1]] = int(raw_value) if raw_value else 0
                    except ValueError:
                        config_ref[key_path[-1]] = 0
                else:
                    config_ref[key_path[-1]] = raw_value
                if save_callback:
                    save_callback()
            threading.Timer(0.5, do_save).start()
        return handler

    # ========== 基本配置控件 ==========
    multithreading_switch = ft.Switch(
        label="使用多线程",
        value=config.get('basic', {}).get('use_multithreading', True),
        tooltip="开启后使用多线程并行翻译，大幅提升翻译速度",
        on_change=_create_switch_change_handler(['basic', 'use_multithreading'], save_config)
    )
    terminology_switch = ft.Switch(
        label="启用术语替换",
        value=config.get('terminology', {}).get('enabled', True),
        on_change=_create_switch_change_handler(['terminology', 'enabled'], save_config)
    )
    local_first_fallback_switch = ft.Switch(
        label="本地优先 (质量差时启用云端)",
        value=config.get('basic', {}).get('local_first_fallback', True),
        tooltip="开启后，优先使用本地模型翻译；若结果全英文或质量极差，自动调用云端多重验证兜底。",
        on_change=_create_switch_change_handler(['basic', 'local_first_fallback'], save_config)
    )
    local_prompt_switch = ft.Switch(
        label="本地模型使用提示词",
        value=config.get('basic', {}).get('local_model_use_prompt', True),
        tooltip="关闭后，本地模型将不发送任何系统提示词，直接翻译原文",
        on_change=_create_switch_change_handler(['basic', 'local_model_use_prompt'], save_config)
    )
    multi_api_switch = ft.Switch(
        label="启用多重API验证（消耗更多Token）",
        value=config.get('basic', {}).get('use_multi_api_validation', False),
        tooltip="开启后，每条文本会调用多个API并选择最佳翻译，显著提升质量但增加Token消耗",
        on_change=_create_switch_change_handler(['basic', 'use_multi_api_validation'], save_config)
    )
    namespace_field = ft.TextField(
        label="命名空间 (namespace)",
        width=int(300 * scale),
        value=config.get('basic', {}).get('namespace', 'minecraft'),
        on_change=_create_text_change_handler(['basic', 'namespace'], save_config, str)
    )
    max_retries_field = ft.TextField(
        label="最大重试次数 (max_retries)",
        width=int(300 * scale),
        value=str(config.get('basic', {}).get('max_retries', 2)),
        keyboard_type=ft.KeyboardType.NUMBER,
        on_change=_create_text_change_handler(['basic', 'max_retries'], save_config, int)
    )
    max_workers_field = ft.TextField(
        label="最大线程数 (max_workers)",
        width=int(300 * scale),
        value=str(config.get('basic', {}).get('max_workers', 18)),
        keyboard_type=ft.KeyboardType.NUMBER,
        on_change=_create_text_change_handler(['basic', 'max_workers'], save_config, int)
    )
    cache_max_size_field = ft.TextField(
        label="缓存最大容量 (cache_max_size)",
        width=int(300 * scale),
        value=str(config.get('basic', {}).get('cache_max_size', 2000)),
        keyboard_type=ft.KeyboardType.NUMBER,
        on_change=_create_text_change_handler(['basic', 'cache_max_size'], save_config, int)
    )

    # ========== 基本配置区域 ==========
    basic_section = ft.Container(
        content=ft.Column([
            ft.Text("⚙️ 基本配置", size=s['section_title_size'],
                    weight=ft.FontWeight.BOLD, color=context.get_color('text_primary')),
            ft.Divider(height=int(10 * scale)),

            ft.Row([
                ft.Column([
                    multithreading_switch,
                    terminology_switch,
                    local_prompt_switch,
                    multi_api_switch,
                    local_first_fallback_switch,
                ], expand=True, spacing=int(10 * scale)),

                ft.Column([
                    namespace_field,
                    max_retries_field,
                    max_workers_field,
                    cache_max_size_field,
                ], expand=True, spacing=int(10 * scale)),
            ], spacing=int(20 * scale)),
        ]),
        padding=s['padding'],
        bgcolor=context.get_color('primary_bg'),
        border_radius=s['border_radius'],
    )

    # ========== 数据管理区域 ==========
    data_management_section = ft.Container(
        content=ft.Column([
            ft.Text("💾 数据管理", size=s['section_title_size'],
                    weight=ft.FontWeight.BOLD, color=context.get_color('text_primary')),
            ft.Divider(height=int(10 * scale)),
            ft.Text("导入/导出配置、术语库和翻译记忆库", size=s['body_size'],
                    color=context.get_color('text_secondary')),
            ft.Divider(height=int(5 * scale)),

            ft.Row([
                ft.ElevatedButton(
                    "📥📤 导入/导出管理",
                    icon=ft.Icons.IMPORT_EXPORT,
                    on_click=show_import_export_dialog if show_import_export_dialog else None,
                    style=ft.ButtonStyle(
                        text_style=ft.TextStyle(size=s['body_size'])
                    ),
                    tooltip="管理配置、术语库和翻译记忆库的导入导出",
                ),
            ], alignment=ft.MainAxisAlignment.START, spacing=int(10 * scale)),
        ]),
        padding=15,
        bgcolor=context.get_color('primary_bg'),
        border_radius=10,
    )

    # ========== API 管理区域 ==========
    api_section = ft.Container(
        content=ft.Column([
            ft.Text("🔌 API 管理", size=s['section_title_size'],
                    weight=ft.FontWeight.BOLD, color=context.get_color('text_primary')),
            ft.Divider(height=int(10 * scale)),

            ft.Row([
                ft.ElevatedButton(
                    "➕ 添加 API",
                    icon=ft.Icons.ADD,
                    on_click=show_add_api_dialog if show_add_api_dialog else None,
                    style=ft.ButtonStyle(text_style=ft.TextStyle(size=s['body_size'])),
                ),
                ft.ElevatedButton(
                    "✅ 全部启用",
                    icon=ft.Icons.CHECK_CIRCLE,
                    on_click=callbacks.get('enable_all_apis'),
                    style=ft.ButtonStyle(text_style=ft.TextStyle(size=s['body_size'])),
                    tooltip="一键启用所有已配置的API"
                ),
                ft.ElevatedButton(
                    "❌ 全部禁用",
                    icon=ft.Icons.CANCEL,
                    on_click=callbacks.get('disable_all_apis'),
                    style=ft.ButtonStyle(text_style=ft.TextStyle(size=s['body_size'])),
                    tooltip="一键禁用所有已配置的API"
                ),
            ], alignment=ft.MainAxisAlignment.START, spacing=int(10 * scale)),
            ft.Divider(height=int(10 * scale)),

            ft.Row([
                ft.Column([
                    ft.Text("已配置的 API:", size=s['body_size'], weight=ft.FontWeight.BOLD, color=context.get_color(
                        'text_primary')),
                    get_api_list() if get_api_list else ft.Text("无API配置", color=context.get_color('text_secondary')),
                ], expand=1, spacing=int(10 * scale)),
            ], spacing=int(20 * scale)),
        ]),
        padding=15,
        bgcolor=context.get_color('primary_bg'),
        border_radius=10,
    )

    # ========== 按钮管理区域 ==========
    button_mgmt_section = _create_button_management_section(context, button_config_list, callbacks)

    return ft.Column([
        basic_section,
        ft.Divider(height=10),
        data_management_section,
        ft.Divider(height=10),
        button_mgmt_section,
        ft.Divider(height=10),
        api_section,
    ], scroll=ft.ScrollMode.AUTO, spacing=10)


def _create_button_row(btn_cfg, context, button_switches, button_order_fields, _on_btn_switch_change, _on_order_change):
    """创建单个按钮配置行

    Args:
        btn_cfg: 按钮配置字典
        context: UI上下文对象
        button_switches: 按钮开关字典
        button_order_fields: 按钮顺序字段字典
        _on_btn_switch_change: 开关变更回调
        _on_order_change: 顺序变更回调

    Returns:
        Flet Column 控件
    """
    btn_id = btn_cfg.get('id', '')
    btn_label = btn_cfg.get('label', btn_id)
    btn_icon = btn_cfg.get('icon', 'BUG_REPORT')
    btn_order = btn_cfg.get('order', 0)
    btn_enabled = btn_cfg.get('enabled', True)

    try:
        icon = getattr(ft.Icons, btn_icon, ft.Icons.BUG_REPORT)
    except Exception:
        icon = ft.Icons.BUG_REPORT

    sw = ft.Switch(
        label=btn_label,
        value=btn_enabled,
        on_change=_on_btn_switch_change,
        tooltip=f"ID: {btn_id}",
    )
    button_switches[btn_id] = sw

    order_field = ft.TextField(
        value=str(btn_order),
        width=60,
        text_size=12,
        tooltip="排序序号",
        on_change=_on_order_change,
    )
    button_order_fields[btn_id] = order_field

    return ft.Column(
        [
            ft.Container(
                content=ft.Row([
                    ft.Icon(icon, size=14),
                    ft.Container(sw, expand=True),
                    ft.Text("顺序:", size=10),
                    order_field,
                ], spacing=5),
                padding=5,
                bgcolor=context.get_color('secondary_bg'),
                border_radius=5,
            )
        ],
        col=6,
    )


def _save_button_switches(button_config_list, button_switches, btn_mgmt_update_config, btn_mgmt_save_config):
    for btn_id, switch in button_switches.items():
        for cfg in button_config_list:
            if cfg.get('id') == btn_id:
                cfg['enabled'] = switch.value
                break
    if btn_mgmt_update_config:
        btn_mgmt_update_config(button_config_list)
    if btn_mgmt_save_config:
        btn_mgmt_save_config()


def _save_button_orders(button_config_list, button_order_fields, btn_mgmt_update_config, btn_mgmt_save_config, context):
    for btn_id, order_field in button_order_fields.items():
        try:
            order = int(order_field.value)
        except ValueError:
            order = 999
        for cfg in button_config_list:
            if cfg.get('id') == btn_id:
                cfg['order'] = order
                break
    button_config_list.sort(key=lambda x: x.get('order', 999))
    if btn_mgmt_update_config:
        btn_mgmt_update_config(button_config_list)
    if btn_mgmt_save_config:
        btn_mgmt_save_config()
    context.page.snack_bar = ft.SnackBar(
        content=ft.Text("✅ 按钮顺序已自动保存"),
        duration=2000,
    )
    context.page.snack_bar.open = True
    context.page.update()


def _create_button_management_section(
    context,
    button_config_list: list,
    callbacks: Dict[str, Callable]
) -> ft.Container:
    s = context.ui_scale
    scale = context.scale

    btn_mgmt_update_config = callbacks.get('update_function_buttons_config')
    btn_mgmt_save_config = callbacks.get('save_config')

    button_switches: Dict[str, ft.Switch] = {}
    button_order_fields: Dict[str, ft.TextField] = {}

    def _on_btn_switch_change(e):
        threading.Timer(0.5, lambda: _save_button_switches(
            button_config_list, button_switches, btn_mgmt_update_config, btn_mgmt_save_config
        )).start()

    def _on_order_change(e):
        threading.Timer(0.5, lambda: _save_button_orders(
            button_config_list, button_order_fields, btn_mgmt_update_config, btn_mgmt_save_config, context
        )).start()

    button_rows = [
        _create_button_row(btn_cfg, context, button_switches, button_order_fields, _on_btn_switch_change, _on_order_change)
        for btn_cfg in button_config_list
    ]

    button_grid = ft.ResponsiveRow(
        button_rows,
        spacing=10,
        run_spacing=10,
    )

    return ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Text("🔧 按钮管理", size=s['section_title_size'],
                        weight=ft.FontWeight.BOLD, color=context.get_color('text_primary')),
                ft.Text("（控制功能按钮的显示/隐藏和顺序）\n修改后自动保存，重启应用后生效",
                        size=s['small_size'], color=context.get_color('text_secondary')),
            ]),
            button_grid,
        ], spacing=int(10 * scale)),
        padding=15,
        bgcolor=context.get_color('primary_bg'),
        border_radius=10,
    )
