"""
UI对话框模块 - 从main_window_flet.py分离出的对话框组件

本模块包含所有独立的对话框函数，不再依赖于MinecraftTranslatorApp类。
所有函数接收ft.Page对象作为第一个参数。
"""
import asyncio
import os
import threading
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import flet as ft

from api.api_defaults import (
    API_MODEL_PRESETS,
    API_TYPE_MAP,
    API_TYPE_OPTIONS,
    API_URL_DEFAULTS,
)

_TKINTER_AVAILABLE = False
try:
    from tkinter import Tk, filedialog
    _TKINTER_AVAILABLE = True
except ImportError:
    pass


def _tkinter_select_folder(title: str) -> str:
    """使用 tkinter 选择文件夹（安全包装）

    Returns:
        选择的文件夹路径，取消或不可用时返回空字符串
    """
    if not _TKINTER_AVAILABLE:
        return ""
    try:
        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        folder = filedialog.askdirectory(title=title)
        root.destroy()
        return folder
    except Exception:
        return ""


def _tkinter_select_file(title: str, filetypes: list = None) -> str:
    """使用 tkinter 选择文件（安全包装）

    Returns:
        选择的文件路径，取消或不可用时返回空字符串
    """
    if not _TKINTER_AVAILABLE:
        return ""
    try:
        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        file_path = filedialog.askopenfilename(title=title, filetypes=filetypes or [])
        root.destroy()
        return file_path
    except Exception:
        return ""


def _check_tkinter(page: ft.Page) -> bool:
    """检查 tkinter 是否可用，不可用时弹出错误对话框"""
    if not _TKINTER_AVAILABLE:
        show_error_dialog(page, "功能不可用", "文件选择器依赖 tkinter，当前环境不可用")
        return False
    return True


def _make_export_path(save_dir: str, prefix: str, ext: str) -> str:
    """生成带时间戳的导出文件路径"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_export_{timestamp}.{ext}"
    return os.path.join(save_dir, filename)


def _show_replace_confirm_dialog(
    page: ft.Page,
    item_name: str,
    import_path: str,
    on_confirm: Callable,
    log_callback: Optional[Callable[[str], None]] = None,
):
    """显示替换确认对话框（通用，用于术语库和翻译记忆库导入）"""
    def confirm_import(ev):
        page.pop_dialog()
        on_confirm()

    def cancel_import(ev):
        page.pop_dialog()
        if log_callback:
            log_callback(f"ℹ️ 用户取消了{item_name}导入")

    confirm_dialog = ft.AlertDialog(
        title=ft.Text("⚠️ 确认替换"),
        content=ft.Column([
            ft.Text(f"导入{item_name}将完全替换现有的数据。", size=14),
            ft.Text("此操作不可撤销，是否继续？", size=14, weight=ft.FontWeight.BOLD),
            ft.Text(f"文件: {os.path.basename(import_path)}", size=12, color=ft.Colors.GREY),
        ], tight=True, spacing=10),
        actions=[
            ft.TextButton("取消", on_click=cancel_import),
            ft.TextButton("确认替换", on_click=confirm_import, style=ft.ButtonStyle(color=ft.Colors.RED)),
        ],
    )
    page.show_dialog(confirm_dialog)


# ──────────── 基础对话框 ────────────

def show_success_dialog(page: ft.Page, title: str, message: str):
    """显示成功对话框"""
    dialog = ft.AlertDialog(
        title=ft.Text(f"✅ {title}"),
        content=ft.Text(message),
        actions=[
            ft.TextButton("确定", on_click=lambda e: page.pop_dialog()),
        ],
    )
    page.show_dialog(dialog)


def show_error_dialog(page: ft.Page, title: str, message: str):
    """显示错误对话框（用户友好版）"""
    friendly_message = message
    if "ConnectionError" in message or "连接" in message:
        friendly_message = "网络连接失败，请检查网络设置或API服务是否可用。"
    elif "Timeout" in message or "超时" in message:
        friendly_message = "请求超时，请检查网络连接或稍后重试。"
    elif "API key" in message or "密钥" in message:
        friendly_message = "API密钥无效或已过期，请检查配置文件中的API设置。"
    elif "JSON" in message and ("decode" in message or "格式" in message):
        friendly_message = "服务器返回的数据格式错误，可能是API服务异常。"
    elif "未找到" in message or "不存在" in message:
        friendly_message = f"文件或文件夹不存在：{message}"

    dialog = ft.AlertDialog(
        title=ft.Text(f"❌ {title}"),
        content=ft.Text(friendly_message),
        actions=[
            ft.TextButton("确定", on_click=lambda e: page.pop_dialog()),
        ],
    )
    page.show_dialog(dialog)


def show_info_dialog(page: ft.Page, title: str, message: str):
    """显示信息对话框"""
    dialog = ft.AlertDialog(
        title=ft.Text(f"ℹ️ {title}"),
        content=ft.Text(message),
        actions=[
            ft.TextButton("确定", on_click=lambda e: page.pop_dialog()),
        ],
    )
    page.show_dialog(dialog)


def show_log_dialog(page: ft.Page, log_text: List[str], title: str = "📋 操作日志"):
    """显示日志对话框"""
    log_content = "\n".join(log_text[-100:]) if log_text else "暂无日志"
    dialog = ft.AlertDialog(
        title=ft.Text(title),
        content=ft.Container(
            content=ft.Text(log_content, size=12),
            height=400,
            padding=10,
        ),
        actions=[
            ft.TextButton("关闭", on_click=lambda e: page.pop_dialog()),
        ],
    )
    page.show_dialog(dialog)


# ──────────── 导入/导出子操作 ────────────

async def _do_export_config(page, config_manager, log):
    """导出配置到文件"""
    if not _check_tkinter(page):
        return
    save_dir = await asyncio.to_thread(_tkinter_select_folder, "选择导出文件夹")
    if not save_dir:
        log("❌ 导出配置: 用户取消了文件夹选择")
        return
    export_path = _make_export_path(save_dir, "config", "yml")
    log(f"📤 导出配置: 保存到 {export_path}")
    if config_manager.export_config(export_path):
        show_success_dialog(page, "导出成功", f"配置已导出到：\n{export_path}")
        log(f"✅ 配置已导出到: {export_path}")
    else:
        show_error_dialog(page, "导出失败", "配置导出失败，请查看日志")


async def _do_import_config(page, config_manager, log):
    """从文件导入配置"""
    if not _check_tkinter(page):
        return
    import_path = await asyncio.to_thread(
        _tkinter_select_file, "选择配置文件",
        [("配置文件", "*.yml *.yaml *.json"), ("所有文件", "*.*")]
    )
    if not import_path:
        log("❌ 导入配置: 用户取消了文件选择")
        return
    log(f"📥 导入配置: 选择了文件 {import_path}")
    if config_manager.import_config(import_path):
        show_success_dialog(page, "导入成功", f"配置已从以下文件导入：\n{import_path}")
        log(f"✅ 配置已从文件导入: {import_path}")
    else:
        show_error_dialog(page, "导入失败", "配置导入失败，请检查文件格式或内容")


async def _do_export_terms(page, terminology_service, log):
    """导出术语库到文件"""
    if not _check_tkinter(page):
        return
    save_dir = await asyncio.to_thread(_tkinter_select_folder, "选择导出文件夹")
    if not save_dir:
        log("❌ 导出术语库: 用户取消了文件夹选择")
        return
    export_path = _make_export_path(save_dir, "terms", "json")
    log(f"📤 导出术语库: 保存到 {export_path}")
    if terminology_service.export_terms(export_path, format='json'):
        show_success_dialog(page, "导出成功", f"术语库已导出到：\n{export_path}")
        log(f"✅ 术语库已导出到: {export_path}")
    else:
        show_error_dialog(page, "导出失败", "术语库导出失败，请查看日志")


async def _do_import_terms(page, terminology_service, log):
    """从文件导入术语库（含确认对话框）"""
    if not _check_tkinter(page):
        return
    import_path = await asyncio.to_thread(
        _tkinter_select_file, "选择术语库文件",
        [("术语库文件", "*.json *.csv *.txt"), ("所有文件", "*.*")]
    )
    if not import_path:
        log("❌ 导入术语库: 用户取消了文件选择")
        return
    log(f"📥 导入术语库: 选择了文件 {import_path}")

    def do_replace():
        imported_count = terminology_service.import_terms(import_path, overwrite=True, replace=True)
        if imported_count > 0:
            show_success_dialog(page, "导入成功", f"术语库已完全替换，共导入 {imported_count} 条术语\n文件：\n{import_path}")
            log(f"✅ 术语库已完全替换，共 {imported_count} 条，文件: {import_path}")
        else:
            show_error_dialog(page, "导入失败", "术语库导入失败，请检查文件格式或内容")

    _show_replace_confirm_dialog(page, "术语库", import_path, do_replace, log)


async def _do_export_cache(page, translation_cache, log):
    """导出翻译记忆库到文件"""
    if not _check_tkinter(page):
        return
    save_dir = await asyncio.to_thread(_tkinter_select_folder, "选择导出文件夹")
    if not save_dir:
        log("❌ 导出翻译记忆库: 用户取消了文件夹选择")
        return
    export_path = _make_export_path(save_dir, "cache", "json")
    log(f"📤 导出翻译记忆库: 保存到 {export_path}")
    if translation_cache.save_to_file(export_path):
        show_success_dialog(page, "导出成功", f"翻译记忆库已导出到：\n{export_path}")
        log(f"✅ 翻译记忆库已导出到: {export_path}")
    else:
        show_error_dialog(page, "导出失败", "翻译记忆库导出失败，请查看日志")


async def _do_import_cache(page, translation_cache, log):
    """从文件导入翻译记忆库（含确认对话框）"""
    if not _check_tkinter(page):
        return
    import_path = await asyncio.to_thread(
        _tkinter_select_file, "选择翻译记忆库文件",
        [("翻译记忆库", "*.json"), ("所有文件", "*.*")]
    )
    if not import_path:
        log("❌ 导入翻译记忆库: 用户取消了文件选择")
        return
    log(f"📥 导入翻译记忆库: 选择了文件 {import_path}")

    def do_replace():
        if translation_cache.load_from_file(import_path):
            show_success_dialog(page, "导入成功", f"翻译记忆库已完全替换，文件：\n{import_path}")
            log(f"✅ 翻译记忆库已完全替换，文件: {import_path}")
        else:
            show_error_dialog(page, "导入失败", "翻译记忆库导入失败，请检查文件格式或内容")

    _show_replace_confirm_dialog(page, "翻译记忆库", import_path, do_replace, log)


# ──────────── 导入/导出主对话框 ────────────

def show_import_export_dialog(
    page: ft.Page,
    config_manager,
    terminology_service,
    translation_cache,
    log_callback=None
):
    """显示导入/导出管理对话框

    6个子操作（导出/导入配置、导出/导入术语库、导出/导入缓存）
    各自委托给独立的异步函数，本函数仅负责 UI 布局。
    """
    if not config_manager or not terminology_service or not translation_cache:
        show_error_dialog(page, "错误", "导入/导出服务未初始化，请先检测API并启动翻译管道")
        return

    def log(message):
        if log_callback:
            log_callback(message)

    content = ft.Column([
        ft.Text("📥📤 导入/导出管理", size=18, weight=ft.FontWeight.BOLD),
        ft.Divider(height=10),

        ft.Container(
            content=ft.Column([
                ft.Text("⚙️ 配置管理", size=16, weight=ft.FontWeight.BOLD),
                ft.Text("导入/导出应用程序配置", size=12, color=ft.Colors.GREY),
                ft.Row([
                    ft.ElevatedButton("📤 导出配置", on_click=lambda e: asyncio.ensure_future(_do_export_config(page, config_manager, log))),
                    ft.ElevatedButton("📥 导入配置", on_click=lambda e: asyncio.ensure_future(_do_import_config(page, config_manager, log))),
                ], spacing=10),
            ], spacing=5),
            padding=10,
            border=ft.Border.all(1, ft.Colors.GREY_300),
            border_radius=5,
        ),

        ft.Divider(height=10),

        ft.Container(
            content=ft.Column([
                ft.Text("📚 术语库管理", size=16, weight=ft.FontWeight.BOLD),
                ft.Text("导入/导出术语词典", size=12, color=ft.Colors.GREY),
                ft.Row([
                    ft.ElevatedButton("📤 导出术语库", on_click=lambda e: asyncio.ensure_future(_do_export_terms(page, terminology_service, log))),
                    ft.ElevatedButton("📥 导入术语库", on_click=lambda e: asyncio.ensure_future(_do_import_terms(page, terminology_service, log))),
                ], spacing=10),
            ], spacing=5),
            padding=10,
            border=ft.Border.all(1, ft.Colors.GREY_300),
            border_radius=5,
        ),

        ft.Divider(height=10),

        ft.Container(
            content=ft.Column([
                ft.Text("💾 翻译记忆库管理", size=16, weight=ft.FontWeight.BOLD),
                ft.Text("导入/导出翻译缓存", size=12, color=ft.Colors.GREY),
                ft.Row([
                    ft.ElevatedButton("📤 导出记忆库", on_click=lambda e: asyncio.ensure_future(_do_export_cache(page, translation_cache, log))),
                    ft.ElevatedButton("📥 导入记忆库", on_click=lambda e: asyncio.ensure_future(_do_import_cache(page, translation_cache, log))),
                ], spacing=10),
            ], spacing=5),
            padding=10,
            border=ft.Border.all(1, ft.Colors.GREY_300),
            border_radius=5,
        ),

        ft.Divider(height=10),
        ft.Text("💡 提示：导入功能使用文件选择器，导出功能可自定义保存位置", size=11, color=ft.Colors.GREY, italic=True),
    ], scroll=ft.ScrollMode.AUTO)

    dialog = ft.AlertDialog(
        title=ft.Text("📥📤 导入/导出管理"),
        content=content,
        actions=[
            ft.TextButton("关闭", on_click=lambda e: page.pop_dialog()),
        ],
    )
    page.show_dialog(dialog)


# ──────────── 添加 API 对话框 ────────────

_API_URL_DEFAULTS = API_URL_DEFAULTS
_API_MODEL_PRESETS = API_MODEL_PRESETS
_API_TYPE_MAP = API_TYPE_MAP
_API_TYPE_OPTIONS = API_TYPE_OPTIONS


def _create_api_form_fields(generate_api_name_func: Callable[[str, str], str]):
    """创建添加 API 对话框的表单字段

    模型名称使用下拉框预设，同时允许手动输入自定义模型名。

    Returns:
        (fields_dict, api_type_dropdown) 二元组
    """
    name_field = ft.TextField(label="API 名称", width=300)
    api_key_field = ft.TextField(
        label="API 密钥", password=True, can_reveal_password=True, width=300)

    initial_models = _API_MODEL_PRESETS.get("智谱", [])
    model_dropdown = ft.Dropdown(
        label="模型名称（推荐）",
        width=300,
        options=[ft.dropdown.Option(m) for m in initial_models],
        value=initial_models[0] if initial_models else None,
        hint_text="选择推荐模型或手动输入",
    )
    custom_model_field = ft.TextField(
        label="自定义模型名称（可选，优先于上方选择）",
        width=300,
        value="",
        hint_text="留空则使用上方选择的模型",
    )

    api_url_field = ft.TextField(
        label="API URL",
        width=300,
        value=_API_URL_DEFAULTS.get("智谱", ""),
    )
    priority_field = ft.TextField(
        label="优先级 (可选)", width=300, value="", keyboard_type=ft.KeyboardType.NUMBER)
    enabled_switch = ft.Switch(label="启用", value=True)

    def on_api_type_changed(e):
        type_name = e.control.value
        if type_name in _API_URL_DEFAULTS:
            api_url_field.value = _API_URL_DEFAULTS[type_name]
            name_field.value = generate_api_name_func(type_name, "")

            models = _API_MODEL_PRESETS.get(type_name, [])
            model_dropdown.options = [ft.dropdown.Option(m) for m in models]
            model_dropdown.value = models[0] if models else None
            custom_model_field.value = ""

    api_type_dropdown = ft.Dropdown(
        label="API 类型",
        options=[ft.dropdown.Option(t) for t in _API_TYPE_OPTIONS],
        value="智谱",
        width=300,
        menu_height=150,
        on_select=on_api_type_changed,
    )

    name_field.value = generate_api_name_func("智谱", "")

    fields = {
        'name': name_field,
        'api_key': api_key_field,
        'model_dropdown': model_dropdown,
        'custom_model': custom_model_field,
        'api_url': api_url_field,
        'priority': priority_field,
        'enabled': enabled_switch,
    }
    return fields, api_type_dropdown


def _save_api_config(
    page: ft.Page,
    fields: Dict[str, ft.TextField],
    api_type_dropdown: ft.Dropdown,
    callbacks: Dict[str, Callable],
    config: Dict[str, Any],
    generate_api_name_func: Callable[[str, str], str],
):
    """保存 API 配置到 config 并触发后续操作"""
    log = callbacks.get('log')
    show_error = callbacks.get('show_error_dialog')
    show_success = callbacks.get('show_success_dialog')
    save_config = callbacks.get('save_config')
    refresh_config_tab = callbacks.get('refresh_config_tab')
    detect_apis = callbacks.get('detect_apis')

    name_field = fields['name']
    api_key_field = fields['api_key']
    model_dropdown = fields['model_dropdown']
    custom_model_field = fields['custom_model']
    api_url_field = fields['api_url']
    priority_field = fields['priority']
    enabled_switch = fields['enabled']

    if not api_key_field.value or not api_key_field.value.strip():
        if show_error:
            show_error(page, "错误", "请输入 API 密钥！")
        return

    model_value = (custom_model_field.value and custom_model_field.value.strip()) or model_dropdown.value or ""
    if not model_value:
        if show_error:
            show_error(page, "错误", "请选择或输入模型名称！")
        return

    api_type = _API_TYPE_MAP.get(api_type_dropdown.value, "zhipu")
    api_name = name_field.value or generate_api_name_func(api_type_dropdown.value, model_value)

    api_config = {
        "name": api_name,
        "api_key": api_key_field.value.strip(),
        "model": model_value,
        "api_url": api_url_field.value,
        "priority": int(priority_field.value) if priority_field.value and priority_field.value.isdigit() else 1,
        "enabled": enabled_switch.value,
    }

    if api_type not in config:
        config[api_type] = []
    config[api_type].append(api_config)

    if save_config:
        save_config()

    if log:
        log(f"已添加 API: {api_config['name']}")

    page.pop_dialog()

    if refresh_config_tab:
        refresh_config_tab()

    if show_success:
        show_success(page, "成功", f"API '{api_config['name']}' 添加成功")

    def background_detect():
        try:
            if detect_apis:
                detect_apis()
        except Exception as ex:
            if log:
                log(f"后台API检测失败: {str(ex)}")

    thread = threading.Thread(target=background_detect, daemon=True)
    thread.start()
    page.update()


def show_add_api_dialog(
    page: ft.Page,
    callbacks: Dict[str, Callable],
    config: Dict[str, Any],
    generate_api_name_func: Callable[[str, str], str]
) -> None:
    """显示添加 API 对话框

    Args:
        page: Flet页面对象
        callbacks: 回调函数字典，包含以下键：
            - log: 日志记录函数
            - show_error_dialog: 显示错误对话框函数
            - show_success_dialog: 显示成功对话框函数
            - save_config: 保存配置函数
            - refresh_config_tab: 刷新配置标签页函数
            - detect_apis: 检测API函数
        config: 配置字典（将被修改）
        generate_api_name_func: 生成API名称的函数，接受(api_type, model)参数
    """
    log = callbacks.get('log')
    show_error = callbacks.get('show_error_dialog')

    if log:
        log("点击了添加 API 按钮")

    try:
        fields, api_type_dropdown = _create_api_form_fields(generate_api_name_func)

        dialog = ft.AlertDialog(
            title=ft.Text("➕ 添加 API"),
            content=ft.Column([
                api_type_dropdown,
                fields['name'],
                fields['api_key'],
                fields['model_dropdown'],
                fields['custom_model'],
                fields['api_url'],
                fields['priority'],
                fields['enabled'],
            ], tight=True, spacing=10, scroll=ft.ScrollMode.AUTO),
            actions=[
                ft.TextButton("取消", on_click=lambda e: page.pop_dialog()),
                ft.TextButton("保存", on_click=lambda e: _save_api_config(
                    page, fields, api_type_dropdown, callbacks, config, generate_api_name_func
                )),
            ],
        )
        page.show_dialog(dialog)
    except Exception as ex:
        if log:
            log(f"打开添加 API 对话框失败: {str(ex)}")
        if show_error:
            show_error(page, "错误", str(ex))


# ──────────── 终端对话框 ────────────

def show_terminal_dialog(page: ft.Page, terminal_text: List[str], title: str = "💻 终端输出"):
    """显示终端对话框"""
    terminal_content = "\n".join(terminal_text[-100:]) if terminal_text else "暂无输出"
    dialog = ft.AlertDialog(
        title=ft.Text(title),
        content=ft.Container(
            content=ft.Text(terminal_content, size=12, font_family="Consolas"),
            height=500,
            padding=10,
        ),
        actions=[
            ft.TextButton("关闭", on_click=lambda e: page.pop_dialog()),
        ],
    )
    page.show_dialog(dialog)
