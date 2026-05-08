#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scripts通用工具模块
提供路径处理、编码管理、错误处理等通用功能
"""

import logging
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Union

# ============================================================================
# 路径处理统一化
# ============================================================================

class PathManager:
    """项目路径管理器"""

    _instance: Optional['PathManager'] = None
    _project_root: Optional[Path] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_project_root(cls) -> Path:
        """获取项目根目录（scripts的父目录）"""
        if cls._project_root is None:
            # scripts/__file__ -> scripts/ -> project_root/
            cls._project_root = Path(__file__).resolve().parent.parent
        return cls._project_root

    @classmethod
    def get_scripts_dir(cls) -> Path:
        """获取scripts目录"""
        return cls.get_project_root() / "scripts"

    @classmethod
    def get_resources_dir(cls) -> Path:
        """获取resources目录"""
        return cls.get_project_root() / "resources"

    @classmethod
    def get_data_dir(cls) -> Path:
        """获取data目录"""
        return cls.get_project_root() / "data"

    @classmethod
    def get_dist_dir(cls) -> Path:
        """获取dist目录（PyInstaller输出）"""
        return cls.get_project_root() / "dist" / "MinecraftBedrockLocalizer"

    @classmethod
    def get_internal_dir(cls) -> Path:
        """获取_internal目录"""
        return cls.get_dist_dir() / "_internal"

    @classmethod
    def resolve_path(cls, relative_path: Union[str, Path]) -> Path:
        """解析相对路径为绝对路径（相对于项目根目录）"""
        path = Path(relative_path)
        if path.is_absolute():
            return path
        return cls.get_project_root() / path

    @classmethod
    def ensure_dir_exists(cls, dir_path: Union[str, Path]) -> Path:
        """确保目录存在，不存在则创建"""
        path = cls.resolve_path(dir_path) if not Path(dir_path).is_absolute() else Path(dir_path)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def is_within_project(cls, path: Union[str, Path]) -> bool:
        """检查路径是否在项目目录内（安全检查）"""
        try:
            resolved = Path(path).resolve()
            project_root = cls.get_project_root().resolve()
            return str(resolved).startswith(str(project_root))
        except Exception:
            return False


# ============================================================================
# 编码处理统一化
# ============================================================================

class EncodingManager:
    """文件编码管理器"""

    DEFAULT_ENCODING = 'utf-8'
    FALLBACK_ENCODINGS = ['utf-8', 'utf-8-sig', 'gbk', 'gb2312']

    @classmethod
    def read_file(cls, file_path: Union[str, Path], encoding: Optional[str] = None) -> str:
        """安全读取文件，尝试多种编码

        Args:
            file_path: 文件路径
            encoding: 指定编码，None则自动检测

        Returns:
            文件内容字符串

        Raises:
            FileNotFoundError: 文件不存在
            UnicodeDecodeError: 所有编码都失败
        """
        file_path = Path(file_path)

        if encoding:
            return file_path.read_text(encoding=encoding)

        # 尝试多种编码
        for enc in cls.FALLBACK_ENCODINGS:
            try:
                return file_path.read_text(encoding=enc)
            except UnicodeDecodeError:
                continue
            except LookupError:
                # 未知编码名称，跳过
                continue

        raise UnicodeDecodeError(
            'utf-8',
            b'',
            0,
            1,
            f"无法使用以下编码读取文件 {file_path}: {cls.FALLBACK_ENCODINGS}"
        )

    @classmethod
    def write_file(cls, file_path: Union[str, Path], content: str,
                   encoding: Optional[str] = None,
                   add_bom: bool = False) -> None:
        """安全写入文件

        Args:
            file_path: 文件路径
            content: 文件内容
            encoding: 编码，默认为utf-8
            add_bom: 是否添加BOM标记
        """
        file_path = Path(file_path)
        encoding = encoding or cls.DEFAULT_ENCODING

        # 确保父目录存在
        file_path.parent.mkdir(parents=True, exist_ok=True)

        if add_bom:
            # 对于需要BOM的情况（如Windows某些工具）
            if encoding == 'utf-8':
                encoding = 'utf-8-sig'

        with open(file_path, 'w', encoding=encoding) as f:
            f.write(content)

    @classmethod
    def normalize_line_endings(cls, content: str, style: str = 'unix') -> str:
        """规范化行结束符

        Args:
            content: 文本内容
            style: 'unix' (\\n) 或 'windows' (\\r\\n)
        """
        # 先统一为\n
        content = content.replace('\r\n', '\n').replace('\r', '\n')

        if style == 'windows':
            content = content.replace('\n', '\r\n')

        return content


# ============================================================================
# 错误处理统一化
# ============================================================================

class ScriptError(Exception):
    """脚本专用异常基类"""
    pass


class FileNotFoundError(ScriptError):
    """文件不存在错误"""
    pass


class ValidationError(ScriptError):
    """验证错误"""
    pass


class DependencyError(ScriptError):
    """依赖错误"""
    pass


class ErrorHandler:
    """统一错误处理器"""

    @staticmethod
    def handle_error(error: Exception, context: str = "",
                     exit_on_error: bool = False) -> int:
        """处理错误并输出友好信息

        Args:
            error: 异常对象
            context: 错误上下文描述
            exit_on_error: 是否以错误码退出

        Returns:
            错误码（0表示成功）
        """
        error_type = type(error).__name__

        if context:
            print(f"\n❌ [{error_type}] {context}")
        else:
            print(f"\n❌ [{error_type}] {error}")

        # 根据错误类型提供建议
        if isinstance(error, FileNotFoundError):
            print("   建议：检查文件路径是否正确")
        elif isinstance(error, ValidationError):
            print("   建议：检查输入参数是否合法")
        elif isinstance(error, DependencyError):
            print("   建议：确保已安装所需依赖")

        if exit_on_error:
            sys.exit(1)
            return 1

        return 1

    @staticmethod
    @contextmanager
    def error_context(context: str, exit_on_error: bool = False):
        """错误处理上下文管理器

        Usage:
            with ErrorHandler.error_context("读取配置文件"):
                config = load_config()
        """
        try:
            yield
        except Exception as e:
            ErrorHandler.handle_error(e, context, exit_on_error)
            if exit_on_error:
                sys.exit(1)


# ============================================================================
# 日志处理统一化
# ============================================================================

class LogManager:
    """统一日志管理器"""

    _configured = False

    @classmethod
    def setup_script_logging(cls, name: str = "scripts",
                            level: int = logging.INFO) -> logging.Logger:
        """设置脚本日志

        Args:
            name: 日志记录器名称
            level: 日志级别

        Returns:
            配置好的logger对象
        """
        logger = logging.getLogger(name)
        logger.setLevel(level)

        if not logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(level)

            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)

            logger.addHandler(handler)

        return logger

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """获取日志记录器"""
        return logging.getLogger(name)


# ============================================================================
# 依赖检查
# ============================================================================

class DependencyChecker:
    """脚本依赖检查器"""

    @staticmethod
    def check_python_version(min_version: tuple = (3, 8)) -> bool:
        """检查Python版本"""
        current = sys.version_info[:2]
        if current < min_version:
            print(f"❌ Python版本过低: {'.'.join(map(str, current))}")
            print(f"   需要 Python {'.'.join(map(str, min_version))}+")
            return False
        return True

    @staticmethod
    def check_module(module_name: str) -> bool:
        """检查模块是否可用"""
        try:
            __import__(module_name)
            return True
        except ImportError:
            print(f"❌ 缺少必需模块: {module_name}")
            print(f"   请运行: pip install {module_name}")
            return False

    @staticmethod
    def check_file(file_path: Union[str, Path],
                   description: str = "必需文件") -> bool:
        """检查文件是否存在"""
        path = Path(file_path)
        if not path.exists():
            print(f"❌ {description}不存在: {path}")
            return False
        return True

    @staticmethod
    def check_directory(dir_path: Union[str, Path],
                       description: str = "必需目录") -> bool:
        """检查目录是否存在"""
        path = Path(dir_path)
        if not path.exists():
            print(f"❌ {description}不存在: {path}")
            return False
        if not path.is_dir():
            print(f"❌ 路径不是目录: {path}")
            return False
        return True


# ============================================================================
# 进度显示
# ============================================================================

class ProgressDisplay:
    """统一进度显示"""

    @staticmethod
    def show_progress(current: int, total: int, prefix: str = "进度",
                     bar_length: int = 30) -> None:
        """显示进度条

        Args:
            current: 当前进度
            total: 总数
            prefix: 前缀文本
            bar_length: 进度条长度
        """
        if total <= 0:
            return

        percent = current / total
        filled = int(bar_length * percent)
        bar = '█' * filled + '░' * (bar_length - filled)

        print(f"\r{prefix}: |{bar}| {percent*100:.1f}% ({current}/{total})", end='')

        if current >= total:
            print()  # 完成后换行

    @staticmethod
    def print_step(step: int, total: int, message: str) -> None:
        """打印步骤信息"""
        print(f"\n[{step}/{total}] {message}")


# ============================================================================
# 主函数入口装饰器
# ============================================================================

def script_entry(point: str = "main"):
    """脚本主入口装饰器

    Usage:
        @script_entry()
        def main():
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 检查Python版本
            if not DependencyChecker.check_python_version():
                return 1

            try:
                return func(*args, **kwargs)
            except KeyboardInterrupt:
                print("\n\n⚠️ 用户中断操作")
                return 130
            except Exception as e:
                ErrorHandler.handle_error(e, f"执行 {func.__name__} 时出错", exit_on_error=True)
                return 1

        # 设置函数属性
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__

        return wrapper

    return decorator


# ============================================================================
# 便捷函数
# ============================================================================

def get_resource_path(relative_path: str) -> Path:
    """获取资源文件的绝对路径"""
    return PathManager.get_project_root() / "resources" / relative_path


def ensure_utf8_file_read(file_path: Union[str, Path]) -> str:
    """确保以UTF-8编码读取文件（失败则提示）"""
    try:
        return EncodingManager.read_file(file_path, 'utf-8')
    except UnicodeDecodeError as e:
        raise FileNotFoundError(
            f"无法读取文件 {file_path}，编码错误。"
            f"请确保文件是有效的UTF-8编码。"
        ) from e


if __name__ == "__main__":
    # 测试代码
    print("项目根目录:", PathManager.get_project_root())
    print("Scripts目录:", PathManager.get_scripts_dir())
    print("Resources目录:", PathManager.get_resources_dir())
