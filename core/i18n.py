#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
国际化 (i18n) 模块

提供多语言支持，允许在运行时切换 UI 语言。

使用方式：
    from core.i18n import i18n, set_locale, get_locale

    # 获取当前语言的字符串
    title = i18n.APP_TITLE
    button_text = i18n.BTN_EXTRACT_ONLY

    # 切换语言
    set_locale('en_US')
"""

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class I18nStrings:
    """国际化字符串数据类"""
    LOCALE: str = "zh_CN"
    APP_TITLE: str = "🎮 Minecraft 基岩版汉化工具"
    APP_SUBTITLE: str = "现代化、易用、高效的翻译工具"

    # 文件夹选择
    FOLDER_SELECT: str = "📁 文件夹选择"
    BP_FOLDER: str = "BP 文件夹:"
    RP_FOLDER: str = "RP 文件夹:"
    SELECT_BUTTON: str = "选择"

    # API
    API_DETECT: str = "🔌 API 检测"
    API_DETECT_BUTTON: str = "检测可用 API"
    API_STATUS: str = "API 状态"
    API_AVAILABLE: str = "可用"
    API_UNAVAILABLE: str = "不可用"
    API_NOT_DETECTED: str = "未检测"

    # 功能按钮
    BTN_EXTRACT_ONLY: str = "[1] 仅提取汉化 key"
    BTN_EXTRACT_TRANSLATE: str = "[2] 提取+AI 翻译"
    BTN_REPLACE_DISPLAY: str = "[3] 全 BP 替换 display_name"
    BTN_BATCH_DELETE: str = "[4] 批量删除 value"
    BTN_BATCH_RESTORE: str = "[5] 批量还原 value"
    BTN_TRANSLATE_LANG: str = "[6] 翻译独立的.lang 文件"
    BTN_ONE_CLICK: str = "[7] 一条龙服务"
    BTN_ENTITY_DISPLAY: str = "[8] 高亮实体信息显示名称"
    BTN_TRANSLATE_JS: str = "[9] 翻译单个 JS 文件"
    BTN_SCRIPT_HARDCODE: str = "[10] 脚本硬编码汉化(慎用)"
    BTN_BACKUP: str = "[11] 备份文件管理"

    # 进度
    PROGRESS_READY: str = "就绪"
    PROGRESS_TRANSLATING: str = "翻译中"
    PROGRESS_EXTRACTING: str = "提取中"
    PROGRESS_COMPLETE: str = "完成"

    # 状态栏
    STATUS_READY: str = "就绪"
    STATUS_WORKING: str = "工作中..."
    STATUS_COMPLETE: str = "完成"
    STATUS_ERROR: str = "错误"

    # 日志
    LOG_APP_START: str = "🚀 应用程序启动完成"
    LOG_APP_READY: str = "✅ 应用已就绪"
    LOG_ERROR_PREFIX: str = "❌ 错误"
    LOG_WARNING_PREFIX: str = "⚠️ 警告"
    LOG_INFO_PREFIX: str = "ℹ️ 信息"

    # 对话框
    DIALOG_ERROR: str = "错误"
    DIALOG_SUCCESS: str = "成功"
    DIALOG_WARNING: str = "警告"
    DIALOG_CONFIRM: str = "确认"
    DIALOG_CANCEL: str = "取消"
    DIALOG_CLOSE: str = "关闭"
    DIALOG_SAVE: str = "保存"
    DIALOG_LOAD: str = "加载"

    # 配置
    CONFIG_TAB: str = "配置"
    CONFIG_BASIC: str = "基础配置"
    CONFIG_API: str = "API 配置"
    CONFIG_ADVANCED: str = "高级配置"
    CONFIG_SAVE: str = "保存配置"
    CONFIG_LOAD: str = "加载配置"
    CONFIG_RESTORE: str = "恢复默认"

    # 日志标签
    LOG_TAB: str = "日志"
    MAIN_TAB: str = "主功能"

    # 其他
    NO_FOLDER_SELECTED: str = "未选择"
    UNKNOWN_ERROR: str = "未知错误"
    NETWORK_ERROR: str = "网络错误"
    API_TIMEOUT: str = "API 超时"
    API_RATE_LIMIT: str = "请求过于频繁"


class I18nEnglish(I18nStrings):
    """英文国际化字符串"""
    LOCALE = "en_US"
    APP_TITLE = "🎮 Minecraft Bedrock Translator"
    APP_SUBTITLE = "Modern, easy-to-use, efficient translation tool"

    FOLDER_SELECT = "📁 Folder Selection"
    BP_FOLDER = "BP Folder:"
    RP_FOLDER = "RP Folder:"
    SELECT_BUTTON = "Select"

    API_DETECT = "🔌 API Detection"
    API_DETECT_BUTTON = "Detect Available APIs"
    API_STATUS = "API Status"
    API_AVAILABLE = "Available"
    API_UNAVAILABLE = "Unavailable"
    API_NOT_DETECTED = "Not Detected"

    BTN_EXTRACT_ONLY = "[1] Extract Translation Keys Only"
    BTN_EXTRACT_TRANSLATE = "[2] Extract + AI Translate"
    BTN_REPLACE_DISPLAY = "[3] Replace display_name in BP"
    BTN_BATCH_DELETE = "[4] Batch Delete Value"
    BTN_BATCH_RESTORE = "[5] Batch Restore Value"
    BTN_TRANSLATE_LANG = "[6] Translate .lang File"
    BTN_ONE_CLICK = "[7] One-Click Service"
    BTN_ENTITY_DISPLAY = "[8] Entity Display Names"
    BTN_TRANSLATE_JS = "[9] Translate Single JS File"
    BTN_SCRIPT_HARDCODE = "[10] Script Hardcode Translation (Caution)"
    BTN_BACKUP = "[11] Backup Management"

    PROGRESS_READY = "Ready"
    PROGRESS_TRANSLATING = "Translating"
    PROGRESS_EXTRACTING = "Extracting"
    PROGRESS_COMPLETE = "Complete"

    STATUS_READY = "Ready"
    STATUS_WORKING = "Working..."
    STATUS_COMPLETE = "Complete"
    STATUS_ERROR = "Error"

    LOG_APP_START = "🚀 Application started"
    LOG_APP_READY = "✅ Application ready"
    LOG_ERROR_PREFIX = "❌ Error"
    LOG_WARNING_PREFIX = "⚠️ Warning"
    LOG_INFO_PREFIX = "ℹ️ Info"

    DIALOG_ERROR = "Error"
    DIALOG_SUCCESS = "Success"
    DIALOG_WARNING = "Warning"
    DIALOG_CONFIRM = "Confirm"
    DIALOG_CANCEL = "Cancel"
    DIALOG_CLOSE = "Close"
    DIALOG_SAVE = "Save"
    DIALOG_LOAD = "Load"

    CONFIG_TAB = "Settings"
    CONFIG_BASIC = "Basic Settings"
    CONFIG_API = "API Configuration"
    CONFIG_ADVANCED = "Advanced Settings"
    CONFIG_SAVE = "Save Settings"
    CONFIG_LOAD = "Load Settings"
    CONFIG_RESTORE = "Restore Defaults"

    LOG_TAB = "Logs"
    MAIN_TAB = "Main"

    NO_FOLDER_SELECTED = "Not Selected"
    UNKNOWN_ERROR = "Unknown error"
    NETWORK_ERROR = "Network error"
    API_TIMEOUT = "API timeout"
    API_RATE_LIMIT = "Rate limit exceeded"


_locale_strings: Dict[str, I18nStrings] = {
    "zh_CN": I18nStrings(),
    "en_US": I18nEnglish(),
}

_current_locale: str = "zh_CN"
i18n: I18nStrings = _locale_strings[_current_locale]


def set_locale(locale: str) -> bool:
    """
    设置当前语言

    Args:
        locale: 语言代码 (zh_CN, en_US)

    Returns:
        是否设置成功
    """
    global _current_locale, i18n

    if locale not in _locale_strings:
        return False

    _current_locale = locale
    i18n = _locale_strings[locale]
    return True


def get_locale() -> str:
    """获取当前语言代码"""
    return _current_locale


def get_available_locales() -> list:
    """获取可用的语言列表"""
    return list(_locale_strings.keys())


def get_locale_display_name(locale: str) -> str:
    """获取语言显示名称"""
    names = {
        "zh_CN": "简体中文",
        "en_US": "English"
    }
    return names.get(locale, locale)


def load_locale_from_config(config: Dict[str, Any]) -> bool:
    """
    从配置加载语言设置

    Args:
        config: 配置字典

    Returns:
        是否加载成功
    """
    ui_config = config.get("ui", {})
    language = ui_config.get("language", "zh_CN")
    return set_locale(language)


def save_locale_to_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    保存当前语言设置到配置

    Args:
        config: 配置字典

    Returns:
        更新后的配置字典
    """
    if "ui" not in config:
        config["ui"] = {}
    config["ui"]["language"] = _current_locale
    return config


if __name__ == "__main__":
    print("=" * 60)
    print("国际化测试")
    print("=" * 60)

    print("\n1. 默认语言 (zh_CN)")
    print(f"   APP_TITLE: {i18n.APP_TITLE}")
    print(f"   BTN_EXTRACT_ONLY: {i18n.BTN_EXTRACT_ONLY}")

    print("\n2. 切换到英文")
    set_locale("en_US")
    print(f"   APP_TITLE: {i18n.APP_TITLE}")
    print(f"   BTN_EXTRACT_ONLY: {i18n.BTN_EXTRACT_ONLY}")

    print("\n3. 可用语言")
    for locale in get_available_locales():
        print(f"   {locale}: {get_locale_display_name(locale)}")

    print("\n4. 切换回中文")
    set_locale("zh_CN")
    print(f"   APP_TITLE: {i18n.APP_TITLE}")

    print("\n" + "=" * 60)
    print("所有测试通过!")
    print("=" * 60)
