import os
import shutil
from datetime import datetime
from typing import Dict, List, Any

from core.file_handler import FileHandler

class BackupManager:
    """备份管理器"""
    
    def __init__(self):
        self.backup_extension = ".bak"
    
    def get_backup_files(self, directory: str) -> List[Dict[str, Any]]:
        """
        获取指定目录下的所有备份文件
        
        Args:
            directory: 要搜索的目录
        
        Returns:
            备份文件列表，每个元素包含文件信息
        """
        backup_files = []
        
        if not os.path.exists(directory):
            return backup_files
        
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith(self.backup_extension):
                    file_path = os.path.join(root, file)
                    original_file = file_path[:-len(self.backup_extension)]
                    
                    # 获取文件信息
                    file_info = {
                        "backup_path": file_path,
                        "original_path": original_file,
                        "backup_name": file,
                        "original_name": os.path.basename(original_file),
                        "size": os.path.getsize(file_path),
                        "modified_time": os.path.getmtime(file_path),
                        "modified_str": datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%Y-%m-%d %H:%M:%S")
                    }
                    backup_files.append(file_info)
        
        # 按修改时间排序，最新的在前
        backup_files.sort(key=lambda x: x["modified_time"], reverse=True)
        return backup_files
    
    def restore_backup(self, backup_path: str, original_path: str) -> bool:
        if not os.path.exists(backup_path):
            return False

        temp_backup = f"{original_path}.temp_bak"
        try:
            if os.path.exists(original_path):
                shutil.copy2(original_path, temp_backup)

            shutil.copy2(backup_path, original_path)
            return True
        except Exception as e:
            print(f"恢复备份失败 [{backup_path} -> {original_path}]: {e}")
            return False
        finally:
            if os.path.exists(temp_backup):
                try:
                    os.remove(temp_backup)
                except Exception:
                    pass
    
    def delete_backup(self, backup_path: str) -> bool:
        """
        删除备份文件
        
        Args:
            backup_path: 备份文件路径
        
        Returns:
            是否删除成功
        """
        try:
            if os.path.exists(backup_path):
                os.remove(backup_path)
                return True
            return False
        except Exception:
            return False
    
    def clean_old_backups(self, directory: str, keep_days: int = 7) -> int:
        """
        清理指定天数之前的备份文件
        
        Args:
            directory: 要清理的目录
            keep_days: 保留的天数
        
        Returns:
            删除的备份文件数量
        """
        deleted_count = 0
        cutoff_time = datetime.now().timestamp() - (keep_days * 24 * 3600)
        
        backup_files = self.get_backup_files(directory)
        for backup in backup_files:
            if backup["modified_time"] < cutoff_time:
                if self.delete_backup(backup["backup_path"]):
                    deleted_count += 1
        
        return deleted_count

class BackupManagementUseCase:
    """备份管理用例"""
    
    def __init__(self, file_handler: FileHandler):
        """
        初始化备份管理用例
        
        Args:
            file_handler: 文件处理器实例
        """
        self.file_handler = file_handler
        self.backup_manager = BackupManager()
    
    def get_backups(self, directory: str) -> Dict[str, Any]:
        """
        获取备份文件列表
        
        Args:
            directory: 要搜索的目录
        
        Returns:
            包含备份文件列表的结果
        """
        try:
            backup_files = self.backup_manager.get_backup_files(directory)
            return {
                "success": True,
                "backups": backup_files,
                "count": len(backup_files)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def restore_backup(self, backup_path: str, original_path: str) -> Dict[str, Any]:
        """
        恢复备份文件
        
        Args:
            backup_path: 备份文件路径
            original_path: 原始文件路径
        
        Returns:
            恢复结果
        """
        try:
            success = self.backup_manager.restore_backup(backup_path, original_path)
            if success:
                return {
                    "success": True,
                    "message": f"已成功恢复备份到: {original_path}"
                }
            else:
                return {
                    "success": False,
                    "error": "恢复备份失败"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def delete_backup(self, backup_path: str) -> Dict[str, Any]:
        """
        删除备份文件
        
        Args:
            backup_path: 备份文件路径
        
        Returns:
            删除结果
        """
        try:
            success = self.backup_manager.delete_backup(backup_path)
            if success:
                return {
                    "success": True,
                    "message": f"已成功删除备份: {backup_path}"
                }
            else:
                return {
                    "success": False,
                    "error": "删除备份失败"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def clean_old_backups(self, directory: str, keep_days: int = 7) -> Dict[str, Any]:
        """
        清理旧备份文件
        
        Args:
            directory: 要清理的目录
            keep_days: 保留的天数
        
        Returns:
            清理结果
        """
        try:
            deleted_count = self.backup_manager.clean_old_backups(directory, keep_days)
            return {
                "success": True,
                "message": f"已清理 {deleted_count} 个旧备份文件",
                "deleted_count": deleted_count
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
