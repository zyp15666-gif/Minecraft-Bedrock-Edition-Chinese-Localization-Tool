#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
操作撤销/重做模块

实现 Command 模式，支持操作的撤销和重做。

使用方式：
    from core.commands import (
        CommandManager,
        FileOperationCommand,
        TranslationCommand
    )

    cmd_manager = CommandManager(max_history=50)

    # 执行命令
    cmd = FileOperationCommand(...)
    cmd_manager.execute(cmd)

    # 撤销
    cmd_manager.undo()

    # 重做
    cmd_manager.redo()
"""

import os
import shutil
import json
import copy
import threading
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional, List, Dict
from dataclasses import dataclass, field
from datetime import datetime

from core.log_manager import get_logger

logger = get_logger(__name__)


class Command(ABC):
    """命令基类"""

    @abstractmethod
    def execute(self) -> Any:
        """执行命令"""
        pass

    @abstractmethod
    def undo(self) -> bool:
        """撤销命令"""
        pass

    @abstractmethod
    def get_description(self) -> str:
        """获取命令描述"""
        pass


@dataclass
class FileBackup:
    """文件备份信息"""
    original_path: str
    backup_path: str
    backup_time: datetime = field(default_factory=datetime.now)


class FileOperationCommand(Command):
    """
    文件操作命令

    支持的文件操作：
    - 复制文件
    - 移动文件
    - 删除文件
    - 修改文件内容
    """

    def __init__(
        self,
        operation: str,
        file_path: str,
        backup_dir: str,
        new_path: Optional[str] = None,
        new_content: Optional[bytes] = None
    ):
        """
        初始化文件操作命令

        Args:
            operation: 操作类型 ('copy', 'move', 'delete', 'modify')
            file_path: 文件路径
            backup_dir: 备份目录
            new_path: 新路径（用于移动操作）
            new_content: 新内容（用于修改操作）
        """
        self.operation = operation
        self.file_path = file_path
        self.backup_dir = backup_dir
        self.new_path = new_path
        self.new_content = new_content

        self._backup: Optional[FileBackup] = None
        self._result: Any = None

    def execute(self) -> Any:
        """执行文件操作"""
        os.makedirs(self.backup_dir, exist_ok=True)

        if self.operation == 'copy':
            if os.path.exists(self.file_path):
                shutil.copy2(self.file_path, self.new_path)
                self._result = self.new_path
            else:
                raise FileNotFoundError(f"文件不存在: {self.file_path}")

        elif self.operation == 'move':
            if os.path.exists(self.file_path):
                shutil.move(self.file_path, self.new_path)
                self._result = self.new_path
            else:
                raise FileNotFoundError(f"文件不存在: {self.file_path}")

        elif self.operation == 'delete':
            if os.path.exists(self.file_path):
                backup_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.path.basename(self.file_path)}"
                backup_path = os.path.join(self.backup_dir, backup_name)
                shutil.copy2(self.file_path, backup_path)
                self._backup = FileBackup(self.file_path, backup_path)
                os.remove(self.file_path)
                self._result = True
            else:
                logger.warning(f"文件不存在，跳过删除: {self.file_path}")
                self._result = False

        elif self.operation == 'modify':
            if os.path.exists(self.file_path):
                backup_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.path.basename(self.file_path)}"
                backup_path = os.path.join(self.backup_dir, backup_name)
                shutil.copy2(self.file_path, backup_path)
                self._backup = FileBackup(self.file_path, backup_path)

                with open(self.file_path, 'wb') as f:
                    f.write(self.new_content)
                self._result = True
            else:
                raise FileNotFoundError(f"文件不存在: {self.file_path}")

        logger.info(f"[Command] 执行文件操作: {self.operation} {self.file_path}")
        return self._result

    def undo(self) -> bool:
        """撤销文件操作"""
        if self.operation == 'copy' and self.new_path:
            if os.path.exists(self.new_path):
                os.remove(self.new_path)
                logger.info(f"[Command] 撤销复制操作: {self.new_path}")
                return True

        elif self.operation == 'move' and self.new_path:
            if os.path.exists(self.new_path):
                shutil.move(self.new_path, self.file_path)
                logger.info(f"[Command] 撤销移动操作: {self.file_path}")
                return True

        elif self.operation == 'delete' and self._backup:
            if os.path.exists(self._backup.backup_path):
                os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
                shutil.copy2(self._backup.backup_path, self.file_path)
                logger.info(f"[Command] 撤销删除操作: {self.file_path}")
                return True

        elif self.operation == 'modify' and self._backup:
            if os.path.exists(self._backup.backup_path):
                shutil.copy2(self._backup.backup_path, self.file_path)
                logger.info(f"[Command] 撤销修改操作: {self.file_path}")
                return True

        return False

    def get_description(self) -> str:
        """获取命令描述"""
        descriptions = {
            'copy': f'复制文件到 {self.new_path}',
            'move': f'移动文件到 {self.new_path}',
            'delete': f'删除文件 {self.file_path}',
            'modify': f'修改文件 {self.file_path}'
        }
        return descriptions.get(self.operation, f'未知操作: {self.operation}')


class BatchCommand(Command):
    """批量命令（将多个命令组合为一个）"""

    def __init__(self, commands: List[Command], description: str = ""):
        """
        初始化批量命令

        Args:
            commands: 子命令列表
            description: 批量命令描述
        """
        self.commands = commands
        self._description = description
        self._executed: List[int] = []

    def execute(self) -> Any:
        """执行所有子命令"""
        self._executed = []
        results = []

        for i, cmd in enumerate(self.commands):
            try:
                result = cmd.execute()
                self._executed.append(i)
                results.append(result)
            except Exception as e:
                logger.error(f"[BatchCommand] 第 {i+1} 个命令执行失败: {e}")
                raise

        return results

    def undo(self) -> bool:
        """撤销所有已执行的子命令（逆序）"""
        success = True

        for i in reversed(self._executed):
            try:
                if not self.commands[i].undo():
                    success = False
            except Exception as e:
                logger.error(f"[BatchCommand] 撤销第 {i+1} 个命令失败: {e}")
                success = False

        return success

    def get_description(self) -> str:
        """获取命令描述"""
        if self._description:
            return self._description
        return f"批量操作 ({len(self.commands)} 个命令)"


class TranslationCommand(Command):
    """翻译操作命令"""

    def __init__(
        self,
        file_path: str,
        original_data: Dict,
        translated_data: Dict,
        backup_dir: str
    ):
        """
        初始化翻译命令

        Args:
            file_path: 文件路径
            original_data: 原始数据
            translated_data: 翻译后数据
            backup_dir: 备份目录
        """
        self.file_path = file_path
        self.original_data = original_data
        self.translated_data = translated_data
        self.backup_dir = backup_dir

        self._backup_path: Optional[str] = None

    def execute(self) -> Any:
        """执行翻译"""
        backup_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.path.basename(self.file_path)}"
        self._backup_path = os.path.join(self.backup_dir, backup_name)

        os.makedirs(self.backup_dir, exist_ok=True)
        shutil.copy2(self.file_path, self._backup_path)

        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(self.translated_data, f, ensure_ascii=False, indent=2)

        logger.info(f"[Command] 执行翻译: {self.file_path}")
        return True

    def undo(self) -> bool:
        """撤销翻译"""
        if self._backup_path and os.path.exists(self._backup_path):
            shutil.copy2(self._backup_path, self.file_path)
            logger.info(f"[Command] 撤销翻译: {self.file_path}")
            return True
        return False

    def get_description(self) -> str:
        """获取命令描述"""
        return f"翻译文件 {self.file_path}"


class CommandManager:
    """
    命令管理器

    负责命令的执行、撤销、重做和历史记录管理。
    """

    def __init__(self, max_history: int = 50):
        """
        初始化命令管理器

        Args:
            max_history: 最大历史记录数
        """
        self.max_history = max_history
        self._history: List[Command] = []
        self._index: int = 0
        self._lock = threading.RLock()

        self._on_execute: Optional[Callable[[Command], None]] = None
        self._on_undo: Optional[Callable[[Command], None]] = None
        self._on_redo: Optional[Callable[[Command], None]] = None

    def set_callbacks(
        self,
        on_execute: Optional[Callable[[Command], None]] = None,
        on_undo: Optional[Callable[[Command], None]] = None,
        on_redo: Optional[Callable[[Command], None]] = None
    ):
        """设置回调函数"""
        self._on_execute = on_execute
        self._on_undo = on_undo
        self._on_redo = on_redo

    def execute(self, command: Command) -> Any:
        """
        执行命令

        Args:
            command: 要执行的命令

        Returns:
            命令执行结果
        """
        with self._lock:
            self._history = self._history[:self._index]

            result = command.execute()

            self._history.append(command)
            self._index += 1

            if len(self._history) > self.max_history:
                self._history.pop(0)
                self._index -= 1

            if self._on_execute:
                self._on_execute(command)

            logger.info(f"[CommandManager] 执行命令: {command.get_description()}")
            return result

    def undo(self) -> bool:
        """
        撤销上一个命令

        Returns:
            是否撤销成功
        """
        with self._lock:
            if not self.can_undo():
                return False

            self._index -= 1
            command = self._history[self._index]

            if command.undo():
                if self._on_undo:
                    self._on_undo(command)
                logger.info(f"[CommandManager] 撤销命令: {command.get_description()}")
                return True

            return False

    def redo(self) -> bool:
        """
        重做上一个撤销的命令

        Returns:
            是否重做成功
        """
        with self._lock:
            if not self.can_redo():
                return False

            command = self._history[self._index]

            if command.execute():
                self._index += 1
                if self._on_redo:
                    self._on_redo(command)
                logger.info(f"[CommandManager] 重做命令: {command.get_description()}")
                return True

            return False

    def can_undo(self) -> bool:
        """检查是否可以撤销"""
        return self._index > 0

    def can_redo(self) -> bool:
        """检查是否可以重做"""
        return self._index < len(self._history)

    def get_history(self) -> List[str]:
        """
        获取命令历史描述

        Returns:
            命令描述列表
        """
        return [cmd.get_description() for cmd in self._history]

    def get_undo_description(self) -> Optional[str]:
        """获取下一个可撤销命令的描述"""
        if self.can_undo():
            return self._history[self._index - 1].get_description()
        return None

    def get_redo_description(self) -> Optional[str]:
        """获取下一个可重做命令的描述"""
        if self.can_redo():
            return self._history[self._index].get_description()
        return None

    def clear(self):
        """清空历史记录"""
        with self._lock:
            self._history.clear()
            self._index = 0
            logger.info("[CommandManager] 历史记录已清空")

    def get_stats(self) -> Dict[str, Any]:
        """获取命令统计信息"""
        return {
            'total_commands': len(self._history),
            'current_index': self._index,
            'can_undo': self.can_undo(),
            'can_redo': self.can_redo(),
            'max_history': self.max_history
        }


if __name__ == "__main__":
    print("=" * 60)
    print("Command 模式测试")
    print("=" * 60)

    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        backup_dir = os.path.join(tmpdir, "backups")
        test_file = os.path.join(tmpdir, "test.txt")

        print("\n1. 测试文件操作命令")
        with open(test_file, "w") as f:
            f.write("Hello World")

        print(f"   创建测试文件: {test_file}")

        cmd_manager = CommandManager(max_history=10)

        cmd = FileOperationCommand(
            operation='modify',
            file_path=test_file,
            backup_dir=backup_dir,
            new_content=b"Hello Translated"
        )

        cmd_manager.execute(cmd)

        with open(test_file) as f:
            content = f.read()
        print(f"   修改后内容: {content}")
        assert content == "Hello Translated"

        print("\n2. 测试撤销")
        cmd_manager.undo()

        with open(test_file) as f:
            content = f.read()
        print(f"   撤销后内容: {content}")
        assert content == "Hello World"

        print("\n3. 测试重做")
        cmd_manager.redo()

        with open(test_file) as f:
            content = f.read()
        print(f"   重做后内容: {content}")
        assert content == "Hello Translated"

        print("\n4. 测试统计信息")
        stats = cmd_manager.get_stats()
        print(f"   统计: {stats}")

        print("\n5. 测试批量命令")
        batch = BatchCommand([
            FileOperationCommand('modify', test_file, backup_dir, new_content=b"Batch 1"),
            FileOperationCommand('modify', test_file, backup_dir, new_content=b"Batch 2"),
        ], description="批量修改")

        cmd_manager.execute(batch)

        with open(test_file) as f:
            content = f.read()
        print(f"   批量执行后内容: {content}")

        cmd_manager.undo()

        with open(test_file) as f:
            content = f.read()
        print(f"   批量撤销后内容: {content}")

        print("\n" + "=" * 60)
        print("所有测试通过!")
        print("=" * 60)
