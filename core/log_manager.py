#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志管理模块
功能：
1. 按日期创建日志文件
2. 自动清理7天前的日志
3. 提供统一的日志记录接口
4. 支持上下文管理器协议
"""

import os
import logging
from logging.handlers import RotatingFileHandler
import datetime
import shutil
from pathlib import Path
from typing import Dict, Any, Optional

from .utils import sanitize_log_message


class StructuredLogFormatter(logging.Formatter):
    """JSON 结构化日志格式化器"""

    def format(self, record: logging.LogRecord) -> str:
        import json
        log_entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = str(record.exc_info[1])
        return json.dumps(log_entry, ensure_ascii=False)


class LogManager:
    """日志管理器 - 支持上下文管理器和依赖注入"""

    def __init__(self, base_dir: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        """初始化日志管理器
        
        Args:
            base_dir: 基础目录路径，如果为None则使用用户文档目录
            config: 配置字典，如果为None则尝试从ConfigManager获取或使用默认值
        """
        self.config = config or self._load_config()
        
        if base_dir:
            self.log_dir = os.path.join(base_dir, "logs")
        else:
            documents_dir = os.path.expanduser(r"~\Documents")
            self.log_dir = os.path.join(
                documents_dir, "Minecraft基岩版汉化工具", "logs")

        self._create_log_dir()
        self._clean_old_logs()
        self._setup_logging()

        self.crashed = False
        self._initialized = True
    
    def __enter__(self) -> 'LogManager':
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """上下文管理器退出"""
        self.cleanup()
    
    class SanitizedLogFormatter(logging.Formatter):
        """脱敏日志格式化器，自动隐藏敏感信息"""
        
        def format(self, record):
            formatted = super().format(record)
            sanitized = sanitize_log_message(formatted, hide_api_keys=True, max_visible_length=50)
            return sanitized
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置
        
        尝试从ConfigManager获取配置，如果失败则返回默认配置
        """
        try:
            from config.config_manager import ConfigManager
            config_manager = ConfigManager()
            return config_manager.config
        except ImportError as e:
            print(f"无法导入ConfigManager: {e}，使用默认配置")
            return {"basic": {"log_level": "INFO"}}
        except Exception as e:
            print(f"加载配置失败: {e}，使用默认配置")
            return {"basic": {"log_level": "INFO"}}

    def _create_log_dir(self):
        """创建日志目录"""
        try:
            os.makedirs(self.log_dir, exist_ok=True)
            print(f"日志目录已创建: {self.log_dir}")
        except Exception as e:
            print(f"创建日志目录失败: {str(e)}")

    def _clean_old_logs(self, keep_count: int = 10):
        """清理旧日志（7天前 + 超过keep_count个的旧文件）"""
        try:
            today = datetime.datetime.now().date()
            seven_days_ago = today - datetime.timedelta(days=7)

            log_files = []
            for filename in os.listdir(self.log_dir):
                if filename.endswith((".log", ".jsonl")):
                    filepath = os.path.join(self.log_dir, filename)
                    if not os.path.isfile(filepath):
                        continue
                    try:
                        date_str = filename.split("_")[1].split(".")[0]
                        log_date = datetime.datetime.strptime(date_str, "%Y%m%d").date()
                    except (IndexError, ValueError):
                        log_date = datetime.datetime.fromtimestamp(os.path.getmtime(filepath)).date()
                    log_files.append((filepath, log_date, os.path.getmtime(filepath)))

            for filepath, log_date, _ in log_files:
                if log_date < seven_days_ago:
                    try:
                        os.remove(filepath)
                        print(f"已删除过期日志: {os.path.basename(filepath)}")
                    except OSError:
                        pass

            remaining = [(fp, mt) for fp, ld, mt in log_files
                         if os.path.exists(fp) and ld >= seven_days_ago]
            remaining.sort(key=lambda x: x[1], reverse=True)

            if len(remaining) > keep_count:
                for filepath, _ in remaining[keep_count:]:
                    try:
                        os.remove(filepath)
                        print(f"已删除超出数量限制的日志: {os.path.basename(filepath)}")
                    except OSError:
                        pass
        except Exception as e:
            print(f"清理旧日志失败: {str(e)}")

    def _setup_logging(self):
        """配置日志"""
        today = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"minecraft_translator_{today}.log"
        self.log_path = os.path.join(self.log_dir, log_filename)
        
        log_level_str = self.config.get("basic", {}).get("log_level", "INFO")
        log_level = self._parse_log_level(log_level_str)
        print(f"📝 日志级别配置: {log_level_str} -> {logging.getLevelName(log_level)}")

        logger = logging.getLogger()
        logger.setLevel(log_level)

        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        self.file_handler = RotatingFileHandler(
            self.log_path,
            maxBytes=10*1024*1024,
            backupCount=5,
            encoding='utf-8'
        )
        self.file_handler.setLevel(log_level)

        self.console_handler = logging.StreamHandler()
        self.console_handler.setLevel(log_level)

        formatter = self.SanitizedLogFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.file_handler.setFormatter(formatter)
        self.console_handler.setFormatter(formatter)

        logger.addHandler(self.file_handler)
        logger.addHandler(self.console_handler)

        log_format = self.config.get("basic", {}).get("log_format", "text")
        if log_format == "json":
            json_path = self.log_path.replace(".log", ".jsonl")
            self.json_handler = logging.FileHandler(json_path, encoding='utf-8')
            self.json_handler.setLevel(log_level)
            self.json_handler.setFormatter(StructuredLogFormatter())
            logger.addHandler(self.json_handler)

        logger.info(f"日志系统初始化完成，日志文件: {self.log_path}")
        print(f"🎮 日志系统已初始化，日志文件保存位置: {self.log_path}")
    
    def _parse_log_level(self, level_str: str) -> int:
        """将字符串日志级别转换为logging常量"""
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        return level_map.get(level_str.upper(), logging.INFO)

    def mark_crash(self):
        """标记应用崩溃"""
        self.crashed = True
        print("已标记应用崩溃")

    def mark_user_interaction(self, action_type: str = None, details: str = None):
        """标记用户交互"""
        logger = logging.getLogger()
        
        if action_type and details:
            log_message = f"👤 用户交互: {action_type} - {details}"
        elif action_type:
            log_message = f"👤 用户交互: {action_type}"
        else:
            log_message = "👤 用户交互事件记录"
            
        logger.debug(log_message)
        print(log_message)

    def cleanup(self):
        """清理日志文件（Windows安全关闭+重试机制）"""
        try:
            if hasattr(self, 'file_handler'):
                self.file_handler.close()
            if hasattr(self, 'console_handler'):
                self.console_handler.close()
            if hasattr(self, 'json_handler'):
                self.json_handler.close()

            logger = logging.getLogger()
            for handler in logger.handlers[:]:
                logger.removeHandler(handler)

            import time as _time
            _time.sleep(0.1)

            if hasattr(self, 'log_path') and os.path.exists(self.log_path):
                if self.crashed:
                    file_size = os.path.getsize(self.log_path)
                    print(f"⚠️ 应用崩溃，保留日志文件: {self.log_path} (大小: {file_size} bytes)")
                else:
                    archive_dir = os.path.join(self.log_dir, "archive")
                    os.makedirs(archive_dir, exist_ok=True)

                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

                    for _ in range(3):
                        try:
                            archive_path = os.path.join(archive_dir, f"archive_{timestamp}.log")
                            shutil.move(self.log_path, archive_path)
                            print(f"📁 正常退出，日志已归档: {archive_path}")
                            break
                        except OSError:
                            _time.sleep(0.3)
                    else:
                        print(f"⚠️ 归档日志失败（文件被占用），保留当前日志")

                    json_log = self.log_path.replace(".log", ".jsonl")
                    if os.path.exists(json_log):
                        for _ in range(3):
                            try:
                                json_archive = os.path.join(archive_dir, f"archive_{timestamp}.jsonl")
                                shutil.move(json_log, json_archive)
                                break
                            except OSError:
                                _time.sleep(0.3)

                    self._cleanup_rotate_backups()
                    self._cleanup_archive(archive_dir, keep_count=10)
        except Exception as e:
            print(f"清理日志文件失败: {str(e)}")

    def _cleanup_rotate_backups(self):
        """清理 RotatingFileHandler 产生的轮转备份文件（.log.1, .log.2 等）"""
        try:
            if not hasattr(self, 'log_dir') or not os.path.isdir(self.log_dir):
                return
            for filename in os.listdir(self.log_dir):
                if filename.endswith((".log.1", ".log.2", ".log.3", ".log.4", ".log.5",
                                       ".log.6", ".log.7", ".log.8", ".log.9",
                                       ".jsonl.1", ".jsonl.2", ".jsonl.3", ".jsonl.4", ".jsonl.5")):
                    filepath = os.path.join(self.log_dir, filename)
                    if os.path.isfile(filepath):
                        try:
                            os.remove(filepath)
                        except OSError:
                            pass
        except Exception:
            pass

    def _cleanup_archive(self, archive_dir, keep_count=10):
        """清理归档目录，保留最近指定数量的日志文件"""
        try:
            if not os.path.exists(archive_dir):
                return

            log_files = []
            for filename in os.listdir(archive_dir):
                if filename.endswith(".log") and filename.startswith("archive_"):
                    filepath = os.path.join(archive_dir, filename)
                    if os.path.isfile(filepath):
                        log_files.append((filepath, os.path.getmtime(filepath)))

            log_files.sort(key=lambda x: x[1])

            if len(log_files) > keep_count:
                files_to_delete = log_files[:len(log_files) - keep_count]
                for filepath, _ in files_to_delete:
                    try:
                        os.remove(filepath)
                        print(f"🗑️  已清理旧归档日志: {os.path.basename(filepath)}")
                    except Exception as e:
                        print(f"删除归档日志失败 {filepath}: {e}")

            seven_days_ago = datetime.datetime.now() - datetime.timedelta(days=7)
            for filepath, mtime in log_files:
                mtime_dt = datetime.datetime.fromtimestamp(mtime)
                if mtime_dt < seven_days_ago:
                    try:
                        os.remove(filepath)
                        print(f"🗑️  已清理7天前归档日志: {os.path.basename(filepath)}")
                    except Exception as e:
                        print(f"删除旧归档日志失败 {filepath}: {e}")

        except Exception as e:
            print(f"清理归档目录失败: {str(e)}")

    def get_logger(self, name: str) -> logging.Logger:
        """获取指定名称的logger
        
        Args:
            name: logger名称
            
        Returns:
            logging.Logger实例
        """
        return logging.getLogger(name)
    
    @staticmethod
    def create_with_defaults(base_dir: Optional[str] = None, try_load: bool = True) -> 'LogManager':
        """使用默认配置创建LogManager实例
        
        Args:
            base_dir: 基础目录路径
            try_load: 是否尝试从ConfigManager加载配置
            
        Returns:
            LogManager实例
        """
        config = None
        if try_load:
            try:
                from config.config_manager import ConfigManager
                config = ConfigManager().config
            except Exception:
                pass
        
        return LogManager(base_dir, config)


# =============================================================================
# 全局日志管理器实例（向后兼容，逐步废弃）
# =============================================================================
log_manager: Optional[LogManager] = None


def init_logger(base_dir: Optional[str] = None, config: Optional[Dict[str, Any]] = None) -> LogManager:
    """初始化日志系统（向后兼容，逐步废弃）
    
    Args:
        base_dir: 基础目录路径
        config: 配置字典
        
    Returns:
        LogManager实例
    """
    global log_manager
    if log_manager is None:
        log_manager = LogManager(base_dir, config)
    return log_manager


def get_logger(name: str) -> logging.Logger:
    """获取logger（向后兼容，逐步废弃）
    
    推荐使用依赖注入方式：
    
    ```python
    # 旧方式（逐步废弃）
    from core.log_manager import get_logger
    logger = get_logger(__name__)
    
    # 新方式（推荐）
    from core.log_manager import LogManager
    with LogManager.create_with_defaults() as log_mgr:
        logger = log_mgr.get_logger(__name__)
        # 或者在类中注入
        class MyClass:
            def __init__(self, logger=None):
                self.logger = logger or logging.getLogger(__name__)
    ```
    
    Args:
        name: logger名称
        
    Returns:
        logging.Logger实例
    """
    global log_manager
    if log_manager is None:
        log_manager = LogManager()
    return log_manager.get_logger(name)


def get_log_manager() -> LogManager:
    """获取全局LogManager实例（向后兼容，逐步废弃）
    
    Returns:
        LogManager实例
    """
    global log_manager
    if log_manager is None:
        log_manager = LogManager()
    return log_manager
