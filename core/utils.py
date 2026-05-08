#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用工具函数模块

集中管理项目中重复使用的辅助函数，避免代码重复。
"""

import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

LANG_KEY_PATTERN = re.compile(
    r'^[a-z_]+(\.[a-z_]+)*:[a-z_\.]+\.(name|description|title|text)$',
    re.IGNORECASE
)


def is_lang_key_format(text: str) -> bool:
    """判断文本是否符合 Minecraft 语言键的格式

    典型格式：
    - item.sgs_farm:breadcrumbs.name
    - tile.minecraft:stone.name
    - entity.zombie:zombie.name
    - sgs_farm:itemGroup.name.kegs

    Returns:
        True 表示符合格式，False 表示不符合
    """
    if not text:
        return False
    return bool(LANG_KEY_PATTERN.match(text))


def get_project_root() -> Path:
    """获取项目根目录的绝对路径

    兼容开发环境和 PyInstaller 打包环境。

    Returns:
        项目根目录的 Path 对象
    """
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent


def resolve_resource_path(relative_path: str) -> Path:
    """将相对路径解析为绝对路径

    兼容开发环境和 PyInstaller 打包环境。
    开发环境：相对于项目根目录
    打包环境：相对于可执行文件目录

    Args:
        relative_path: 相对路径（如 "resources/api/minecraft_terms.json"）

    Returns:
        解析后的绝对路径
    """
    root = get_project_root()
    abs_path = root / relative_path

    if abs_path.exists():
        return abs_path

    if getattr(sys, 'frozen', False):
        base = Path(sys._MEIPASS)
        alt_path = base / relative_path
        if alt_path.exists():
            return alt_path

    return abs_path


def validate_required_files(file_list: List[str]) -> Dict[str, bool]:
    """验证必要的文件是否存在

    Args:
        file_list: 必要文件的相对路径列表

    Returns:
        文件存在状态字典 {relative_path: exists}
    """
    results = {}
    for file_path in file_list:
        abs_path = resolve_resource_path(file_path)
        results[file_path] = abs_path.exists()
        if not abs_path.exists():
            print(f"[路径验证] 文件不存在: {file_path} (解析为: {abs_path})")
    return results


def split_by_color_codes(text: str) -> List[Tuple[str, str]]:
    """
    将文本按颜色代码分割成 (代码, 内容) 片段列表。
    例如: "§aHello §rworld" -> [('§a', 'Hello '), ('§r', 'world')]
    支持所有 §a 到 §z 和 §0 到 §9 格式的颜色符号。
    也支持 \\xA7 转义形式（如 JS 文件中的 \\xA7a）。

    Args:
        text: 包含Minecraft颜色代码的文本

    Returns:
        分割后的片段列表，每个元素为(颜色代码, 文本内容)
    """
    parts = []
    last_pos = 0
    last_code = ''

    i = 0
    while i < len(text):
        code = ''
        code_len = 0

        if text[i] == '§' and i + 1 < len(text):
            next_char = text[i + 1].lower()
            if next_char in '0123456789abcdefklmnor':
                code = text[i:i+2]
                code_len = 2
        elif text[i:i+2] == '\\x' and i + 4 <= len(text):
            hex_part = text[i+2:i+4].lower()
            if len(hex_part) == 2:
                try:
                    char_val = int(hex_part, 16)
                    if char_val == 0xA7 and i + 4 < len(text):
                        next_char = text[i + 4].lower()
                        if next_char in '0123456789abcdefklmnor':
                            code = text[i:i+5]
                            code_len = 5
                except ValueError:
                    pass

        if code_len > 0:
            if i > last_pos:
                content = text[last_pos:i]
                parts.append((last_code, content))
            last_code = code
            last_pos = i + code_len
            i += code_len
        else:
            i += 1

    if last_pos < len(text):
        content = text[last_pos:]
        parts.append((last_code, content))
    elif last_pos == len(text) and last_code:
        parts.append((last_code, ''))

    if not parts:
        parts = [('', text)]

    return parts


def create_log_progress_wrappers(
    progress_callback: Optional[Callable[[float], None]] = None,
    log_callback: Optional[Callable[[str], None]] = None
) -> Tuple[Callable[[str], None], Callable[[float, int, int], None]]:
    """
    创建统一的日志和进度包装函数，减少重复代码。

    Args:
        progress_callback: 原始进度回调函数
        log_callback: 原始日志回调函数

    Returns:
        (log_func, progress_func) 包装后的函数
    """
    def log_func(msg: str) -> None:
        """包装的日志函数"""
        if log_callback:
            log_callback(msg)

    def progress_func(value: float, remaining_count: int = 0, remaining_time: int = 0) -> None:
        """包装的进度函数"""
        if progress_callback:
            progress_callback(value, remaining_count, remaining_time)

    return log_func, progress_func


class CallbackWrapper:
    """
    回调函数包装器，统一处理进度和日志回调逻辑。

    标准进度回调签名: def progress(percent: float, remaining: int, eta: float)
    - percent: 完成百分比 (0.0 - 1.0)
    - remaining: 剩余条目数
    - eta: 预计剩余时间（秒）

    使用示例:
        wrapper = CallbackWrapper(progress_callback, log_callback)
        wrapper.log("开始处理...")
        wrapper.progress(0.5, 10, 5.0)
    """

    def __init__(
        self,
        progress_callback: Optional[Callable[[float, int, float], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ):
        self.progress_callback = self._normalize_progress_callback(progress_callback)
        self.log_callback = log_callback

    @staticmethod
    def _normalize_progress_callback(
        callback: Optional[Callable]
    ) -> Optional[Callable[[float, int, float], None]]:
        """标准化进度回调为三参数签名

        兼容旧版单参数回调:
        - 单参数 callback(percent) -> 包装为 callback(percent, 0, 0.0)
        - 三参数 callback(percent, remaining, eta) -> 直接使用

        Args:
            callback: 原始回调函数

        Returns:
            标准化后的三参数回调函数
        """
        if callback is None:
            return None

        try:
            import inspect
            sig = inspect.signature(callback)
            params = list(sig.parameters.values())
            has_var_positional = any(
                p.kind == inspect.Parameter.VAR_POSITIONAL for p in params
            )
            if has_var_positional:
                return callback
            param_count = len(params)
        except Exception:
            param_count = 3

        if param_count == 1:
            def wrapper(value: float, remaining: int = 0, eta: float = 0.0):
                callback(value)
            return wrapper
        elif param_count == 3:
            return callback
        else:
            def wrapper(value: float, remaining: int = 0, eta: float = 0.0):
                try:
                    callback(value, remaining, eta)
                except TypeError:
                    callback(value)
            return wrapper

    def log(self, message: str) -> None:
        """记录日志"""
        if self.log_callback:
            self.log_callback(message)

    def progress(
        self,
        value: float,
        remaining_count: int = 0,
        remaining_time: float = 0.0
    ) -> None:
        """更新进度（标准三参数签名）"""
        if self.progress_callback:
            self.progress_callback(value, remaining_count, remaining_time)

    def __call__(
        self,
        progress_value: Optional[float] = None,
        log_message: Optional[str] = None
    ) -> None:
        """同时更新进度和日志（可选）"""
        if progress_value is not None:
            self.progress(progress_value)
        if log_message is not None:
            self.log(log_message)


def normalize_text_for_cache(text: str) -> str:
    """
    规范化文本用于缓存键，提高缓存命中率。

    规范化规则：
    1. Unicode 标准化为 NFC 形式，合并组合字符
    2. 移除不可见控制字符（零宽空格、方向标记等）
    3. 统一各种空格为普通空格（不间断空格、全角空格等）
    4. 仅去除首尾空白，保留内部格式不变
    5. 保留颜色代码（§前缀）和占位符（[[]]格式）不变
    6. 不改变大小写（Minecraft中大小写可能有意义）

    Args:
        text: 原始文本

    Returns:
        规范化后的文本
    """
    if not text:
        return text

    # Unicode 标准化为 NFC 形式，合并组合字符
    text = unicodedata.normalize('NFC', text)

    # 移除控制字符（保留常见空白），如零宽空格、不换行空格等
    # 这些字符可能导致相同内容被缓存为不同键
    text = re.sub(r'[\u200b\u200c\u200d\u200e\u200f\u202a-\u202e]', '', text)

    # 统一不间断空格为普通空格
    text = text.replace('\u00a0', ' ')  # NBSP
    text = text.replace('\u202f', ' ')  # NNBSP
    text = text.replace('\u3000', ' ')  # 全角空格

    # 仅去除首尾空白字符，保留内部空白不变
    return text.strip()


def contains_color_codes(text: str) -> bool:
    """
    检查文本是否包含Minecraft颜色代码。
    委托给 has_color_codes()，该函数有更完整的检测逻辑。

    Args:
        text: 待检查文本

    Returns:
        是否包含颜色代码
    """
    return has_color_codes(text)


def contains_known_terms(text: str, term_service) -> bool:
    """
    检查文本是否包含已知术语（需要术语预处理）。

    Args:
        text: 待检查文本
        term_service: 术语服务实例

    Returns:
        是否包含已知术语
    """
    if not text or not term_service or not term_service.terms:
        return False

    # 直接调用术语服务的快速检测方法
    return term_service.has_any_term(text)




def sanitize_log_message(message: str, hide_api_keys: bool = True, max_visible_length: int = 50) -> str:
    """
    对日志消息进行脱敏处理，隐藏敏感信息。

    Args:
        message: 原始日志消息
        hide_api_keys: 是否隐藏API密钥
        max_visible_length: 最大可见长度，超过部分用...代替

    Returns:
        脱敏后的日志消息
    """
    if not message:
        return message

    result = message

    # 1. 隐藏API密钥（常见的API密钥模式）
    if hide_api_keys:
        result = re.sub(r'sk-[a-zA-Z0-9]{20,70}', 'sk-***REDACTED***', result)
        result = re.sub(r'Bearer\s+[a-zA-Z0-9._-]{20,}', 'Bearer ***REDACTED***', result)
        result = re.sub(r'(api[_-]?key|secret|token|apikey|access[_-]?key)\s*[:=]\s*["\']?[a-zA-Z0-9._-]{10,}["\']?',
                       r'\1="***REDACTED***"', result)
        result = re.sub(r'["\']?api[_-]?key["\']?\s*:\s*["\'][a-zA-Z0-9._-]{10,}["\']',
                       '"api_key": "***REDACTED***"', result)
        result = re.sub(r'Authorization["\']?\s*:\s*["\']?Bearer\s+[a-zA-Z0-9._-]{10,}',
                       'Authorization: Bearer ***REDACTED***', result)

    # 2. 限制敏感文本的显示长度（如API响应中的长内容字段）
    # 匹配各种API响应JSON字段中的长文本
    for prefix in ['content', 'message', 'result', 'text']:
        pattern = rf'"{prefix}"\s*:\s*"([^"]{{50,}})"'
        matches = re.findall(pattern, result)
        for match in matches:
            if len(match) > max_visible_length:
                truncated = match[:max_visible_length] + "..."
                result = result.replace(match, truncated)

    # 3. 对翻译结果进行特殊处理，确保不超过最大长度
    for prefix in ['翻译结果', '翻译完成', '译文']:
        pattern = rf'{prefix}[:：]\s*["\']?([^"\']{{50,}})["\']?'
        matches = re.findall(pattern, result)
        for match in matches:
            if len(match) > max_visible_length:
                truncated = match[:max_visible_length] + "..."
                result = result.replace(match, truncated)

    # 4. 移除可能的JSON中的敏感字段
    sensitive_json_fields = ['api_key', 'secret', 'password', 'token', 'auth', 'credential']
    for field in sensitive_json_fields:
        pattern = rf'"{field}"\s*:\s*"[^"]+"'
        result = re.sub(pattern, f'"{field}": "***REDACTED***"', result)

    return result


def has_color_codes(text: str) -> bool:
    """检查文本是否包含Minecraft颜色代码（统一版本）

    支持 § 符号、\\xA7 转义和 \\xA7 字节三种形式。
    \\xA7 必须后跟一个字母或数字才是有效的颜色代码。

    Args:
        text: 待检查文本

    Returns:
        是否包含颜色代码
    """
    if not text:
        return False
    if re.search(r'§[0-9a-fklmnor]', text):
        return True
    if re.search(r'\\xA7[0-9a-zA-Z]', text):
        return True
    if re.search(r'\xA7[0-9a-zA-Z]', text):
        return True
    return False


def normalize_game_text(text: str) -> Tuple[str, str]:
    """统一的游戏文本清洗函数

    将 api_manager.py 和 terminology_service.py 中重复的文本清洗逻辑
    合并到此函数，确保清洗规则一致。

    清洗步骤：
    1. 还原转义字符（\\n → 换行，\\t → 制表符）
    2. 分离注释后缀（# 之后的部分）
    3. 删除制表符，合并多余空格
    4. 去除首尾空白

    Args:
        text: 原始游戏文本

    Returns:
        (core_text, suffix) 二元组：
        - core_text: 清洗后的核心文本
        - suffix: 注释后缀（含#号），无注释时为空字符串
    """
    if not text:
        return text, ''

    if '\\n' in text:
        text = text.replace('\\n', '\n')
    if '\\t' in text:
        text = text.replace('\\t', '\t')

    hash_pos = text.find('#')
    if hash_pos != -1:
        core_part = text[:hash_pos]
        suffix = text[hash_pos:]
    else:
        core_part = text
        suffix = ''

    core_part = core_part.replace('\t', ' ')
    core_text = re.sub(r'[ \t]+', ' ', core_part)
    core_text = re.sub(r'\n+', '\n', core_text)
    core_text = core_text.strip()

    return core_text, suffix


def sanitize_api_response(response_text: str, max_length: int = 100) -> str:
    """
    脱敏API响应文本，避免记录完整响应内容。

    Args:
        response_text: API响应文本
        max_length: 最大显示长度

    Returns:
        脱敏后的响应文本摘要
    """
    if not response_text:
        return ""

    # 如果响应是JSON，尝试提取非敏感部分
    if response_text.strip().startswith('{') or response_text.strip().startswith('['):
        try:
            import json
            data = json.loads(response_text)
            # 创建脱敏副本
            sanitized = {}
            for key, value in data.items():
                if isinstance(key, str) and any(sensitive in key.lower() for sensitive in
                                               ['key', 'secret', 'token', 'password', 'auth']):
                    sanitized[key] = '***REDACTED***'
                elif isinstance(value, str) and len(value) > 20:
                    sanitized[key] = value[:20] + '...'
                else:
                    sanitized[key] = value
            return json.dumps(sanitized, ensure_ascii=False)[:max_length]
        except Exception:
            pass

    # 非JSON文本，简单截断
    if len(response_text) > max_length:
        return response_text[:max_length] + "..."
    return response_text


_PROTECTED_WINDOWS_PATHS: List[str] = []


def _get_protected_paths() -> List[str]:
    """获取受保护的系统目录列表（Windows 10/11）"""
    global _PROTECTED_WINDOWS_PATHS
    if _PROTECTED_WINDOWS_PATHS:
        return _PROTECTED_WINDOWS_PATHS

    windir = os.environ.get('WINDIR', r'C:\Windows').lower()
    _PROTECTED_WINDOWS_PATHS = [
        windir,
        os.path.join(windir, 'system32'),
        os.path.join(windir, 'syswow64'),
        os.path.join(windir, 'system'),
        r'c:\program files',
        r'c:\program files (x86)',
        r'c:\programdata',
    ]

    for env_var in ['ProgramFiles', 'ProgramFiles(x86)', 'ProgramData']:
        val = os.environ.get(env_var)
        if val:
            _PROTECTED_WINDOWS_PATHS.append(val.lower())

    return _PROTECTED_WINDOWS_PATHS


def is_protected_system_path(path: str) -> bool:
    """检查路径是否位于受保护的系统目录中

    防止用户误操作选择 C:\\Windows 等系统目录作为翻译目标，
    避免文件写入操作造成系统破坏。

    Args:
        path: 待检查的路径

    Returns:
        True 表示路径受保护（禁止写入），False 表示安全
    """
    if not path:
        return False

    try:
        normalized = os.path.normpath(path).lower()
    except (ValueError, OSError):
        return True

    for protected in _get_protected_paths():
        try:
            prot_normalized = os.path.normpath(protected).lower()
        except (ValueError, OSError):
            continue
        if normalized == prot_normalized or normalized.startswith(prot_normalized + os.sep):
            return True

    return False
