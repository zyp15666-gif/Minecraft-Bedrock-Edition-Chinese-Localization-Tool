#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一备份管理器 - 提供一致的备份/恢复接口

消除各UseCase中分散的备份代码，提供统一的备份策略。
"""

import os
import shutil
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path
from dataclasses import dataclass
from enum import Enum


class BackupType(Enum):
    FOLDER_BACKUP = "folder_backup"
    FILE_BACKUP = "file_backup"
    INPLACE_BACKUP = "inplace_backup"


@dataclass
class BackupInfo:
    path: str
    backup_type: BackupType
    original_path: str
    timestamp: str
    size: int = 0


class BackupManager:
    """统一备份管理器"""

    DEFAULT_TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"
    DEFAULT_MAX_BACKUPS = 10

    def __init__(
        self,
        backup_type: BackupType = BackupType.FOLDER_BACKUP,
        timestamp_format: str = None,
        max_backups: int = None,
        backup_suffix: str = ".bak",
        backup_prefix: str = "_BACKUP_"
    ):
        """
        初始化备份管理器

        Args:
            backup_type: 备份类型
            timestamp_format: 时间戳格式
            max_backups: 最大保留备份数量
            backup_suffix: 就地备份后缀
            backup_prefix: 文件夹备份前缀
        """
        self.backup_type = backup_type
        self.timestamp_format = timestamp_format or self.DEFAULT_TIMESTAMP_FORMAT
        self.max_backups = max_backups or self.DEFAULT_MAX_BACKUPS
        self.backup_suffix = backup_suffix
        self.backup_prefix = backup_prefix

    def backup(
        self,
        path: str,
        log_callback: Optional[Callable[[str], None]] = None,
        **kwargs
    ) -> Optional[str]:
        """
        执行备份

        Args:
            path: 要备份的文件或文件夹路径
            log_callback: 日志回调

        Returns:
            备份路径，失败返回None
        """
        if not path or not os.path.exists(path):
            self._log(log_callback, f"备份路径不存在: {path}")
            return None

        timestamp = datetime.now().strftime(self.timestamp_format)

        def log(msg: str):
            if log_callback:
                log_callback(msg)

        try:
            if self.backup_type == BackupType.FOLDER_BACKUP:
                return self._backup_folder(path, timestamp, log)
            elif self.backup_type == BackupType.INPLACE_BACKUP:
                return self._backup_inplace(path, timestamp, log)
            else:
                return self._backup_file(path, timestamp, log)
        except Exception as e:
            self._log(log_callback, f"备份失败: {e}")
            return None

    def _backup_folder(self, folder_path: str, timestamp: str, log: Callable) -> str:
        """备份文件夹"""
        backup_to = f"{folder_path}{self.backup_prefix}{timestamp}"
        shutil.copytree(folder_path, backup_to, dirs_exist_ok=True)
        log(f"✅ 备份完成 → {backup_to}")
        return backup_to

    def _backup_file(self, file_path: str, timestamp: str, log: Callable) -> str:
        """备份单文件"""
        parent_dir = os.path.dirname(file_path)
        backup_dir = f"{parent_dir}{self.backup_prefix}{timestamp}"
        os.makedirs(backup_dir, exist_ok=True)
        backup_to = os.path.join(backup_dir, os.path.basename(file_path))
        shutil.copy2(file_path, backup_to)
        log(f"✅ 文件备份完成 → {backup_to}")
        return backup_to

    def _backup_inplace(self, file_path: str, timestamp: str, log: Callable) -> str:
        """就地备份（添加.bak后缀）"""
        if not os.path.isfile(file_path):
            log(f"就地备份只支持文件: {file_path}")
            return None
        backup_to = f"{file_path}{self.backup_suffix}"
        shutil.copy2(file_path, backup_to)
        log(f"💾 已备份 → {backup_to}")
        return backup_to

    def restore(
        self,
        backup_path: str,
        original_path: str,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> bool:
        """
        恢复备份

        Args:
            backup_path: 备份路径
            original_path: 原始路径
            log_callback: 日志回调

        Returns:
            是否恢复成功
        """
        def log(msg: str):
            if log_callback:
                log_callback(msg)

        if not os.path.exists(backup_path):
            log(f"❌ 备份文件不存在: {backup_path}")
            return False

        temp_backup = f"{original_path}.temp_bak"
        try:
            if os.path.exists(original_path):
                shutil.copy2(original_path, temp_backup)

            if os.path.isdir(backup_path):
                if os.path.isdir(original_path):
                    shutil.rmtree(original_path)
                shutil.copytree(backup_path, original_path)
            else:
                shutil.copy2(backup_path, original_path)

            log(f"✅ 恢复成功: {original_path}")
            return True

        except Exception as e:
            log(f"❌ 恢复失败: {e}")
            if os.path.exists(temp_backup):
                shutil.copy2(temp_backup, original_path)
            return False
        finally:
            if os.path.exists(temp_backup):
                try:
                    os.remove(temp_backup)
                except OSError:
                    pass

    def list_backups(self, directory: str, original_name: str = None) -> List[Dict[str, Any]]:
        """
        列出目录下的备份

        Args:
            directory: 搜索目录
            original_name: 原始文件名（可选，用于过滤）

        Returns:
            备份信息列表
        """
        backups = []

        if not os.path.exists(directory):
            return backups

        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith(self.backup_suffix) or self.backup_prefix in file:
                    file_path = os.path.join(root, file)

                    backups.append({
                        "path": file_path,
                        "name": file,
                        "size": os.path.getsize(file_path),
                        "modified": os.path.getmtime(file_path),
                        "modified_str": datetime.fromtimestamp(
                            os.path.getmtime(file_path)
                        ).strftime("%Y-%m-%d %H:%M:%S")
                    })

        backups.sort(key=lambda x: x["modified"], reverse=True)
        return backups

    def cleanup_old(
        self,
        directory: str,
        keep_count: int = None,
        keep_days: int = None
    ) -> int:
        """
        清理旧备份

        Args:
            directory: 清理目录
            keep_count: 保留最新N个
            keep_days: 保留最近N天

        Returns:
            删除的备份数量
        """
        keep_count = keep_count or self.max_backups
        backups = self.list_backups(directory)

        if not backups:
            return 0

        deleted = 0
        cutoff_time = None
        if keep_days:
            cutoff_time = datetime.now().timestamp() - (keep_days * 24 * 3600)

        for i, backup in enumerate(backups):
            should_delete = False

            if keep_days and backup["modified"] < cutoff_time:
                should_delete = True
            elif i >= keep_count:
                should_delete = True

            if should_delete:
                try:
                    if os.path.isdir(backup["path"]):
                        shutil.rmtree(backup["path"])
                    else:
                        os.remove(backup["path"])
                    deleted += 1
                except Exception:
                    pass

        return deleted

    def _log(self, callback: Optional[Callable], msg: str):
        if callback:
            callback(msg)
