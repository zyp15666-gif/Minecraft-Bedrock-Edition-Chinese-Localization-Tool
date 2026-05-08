"""
应用服务层 — 从主窗口抽离的业务逻辑

职责：
- API检测、配置保存/加载
- 备份管理、文件操作协调
- 直接调用UseCase，移除冗余适配层
- 将 UI 专属操作通过回调传递给调用者
"""

import os
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from core.log_manager import get_logger
from core.utils import CallbackWrapper

logger = get_logger(__name__)


class ApplicationService:
    """应用服务 — 主窗口委托的业务逻辑"""

    def __init__(
        self,
        api_manager,
        config_manager,
        file_handler,
        translator,
        log_callback: Optional[Callable[[str], None]] = None,
        show_error: Optional[Callable[[str, str], None]] = None,
        show_success: Optional[Callable[[str, str], None]] = None,
    ):
        self.api_manager = api_manager
        self.config_manager = config_manager
        self.file_handler = file_handler
        self.translator = translator
        self.log = log_callback or print
        self.show_error = show_error or (lambda t, m: print(f"[{t}] {m}"))
        self.show_success = show_success or (lambda t, m: print(f"[{t}] {m}"))

        self._init_use_cases()

    def _init_use_cases(self):
        """初始化所有UseCase实例"""
        from core.use_cases import (
            AdaptEntityDisplayNamesUseCase,
            BatchDeleteValueUseCase,
            BatchRestoreValueUseCase,
            ExtractAndTranslateUseCase,
            ExtractOnlyUseCase,
            OneClickServiceUseCase,
            ReplaceDisplayNamesUseCase,
            ScriptHardcodeTranslationUseCase,
            TranslateLangFileUseCase,
            TranslateSingleJsFileUseCase,
        )
        from core.use_cases.backup_management import BackupManagementUseCase
        from core.use_cases.translate_mcstructure import McstructureTranslationUseCase

        self._extract_only_uc = ExtractOnlyUseCase(self.file_handler)
        self._extract_translate_uc = ExtractAndTranslateUseCase(self.file_handler, self.translator)
        self._replace_display_uc = ReplaceDisplayNamesUseCase(self.file_handler)
        self._one_click_uc = OneClickServiceUseCase(self.file_handler, self.translator)
        self._batch_delete_uc = BatchDeleteValueUseCase(self.file_handler, self.config_manager.config)
        self._batch_restore_uc = BatchRestoreValueUseCase(self.file_handler, self.config_manager.config)
        self._translate_lang_uc = TranslateLangFileUseCase(self.file_handler, self.translator)
        self._translate_js_uc = TranslateSingleJsFileUseCase(self.translator)
        self._adapt_entity_uc = AdaptEntityDisplayNamesUseCase(self.file_handler, self.translator)
        self._script_hardcode_uc = ScriptHardcodeTranslationUseCase(self.translator)
        self._backup_uc = BackupManagementUseCase(self.file_handler)
        self._mcstructure_uc = McstructureTranslationUseCase(self.translator.api_manager)

    def _wrap_progress_callback(self, callback: Optional[Callable]) -> Optional[Callable]:
        """包装进度回调，委托给 CallbackWrapper._normalize_progress_callback"""
        return CallbackWrapper._normalize_progress_callback(callback)

    # ── API 管理 ──

    def detect_apis(self, progress_callback=None) -> List[Dict[str, Any]]:
        """检测可用 API"""
        if progress_callback:
            progress_callback(0.6, "正在检测API...", 0, 0)
        available = self.api_manager.detect_available_apis()
        if progress_callback:
            progress_callback(1.0, "API 检测完成" if available else "未检测到可用API", 0, 0)
        return available

    def build_api_list(self) -> List[Dict[str, Any]]:
        return self.api_manager.build_api_list()

    # ── 配置管理 ──

    def save_config(self, config: Dict[str, Any] = None) -> bool:
        try:
            target = config or self.api_manager.config
            self.config_manager.save_config(target)
            self.log("💾 配置已保存")
            return True
        except Exception as e:
            self.log(f"❌ 保存配置失败: {e}")
            return False

    def reload_config(self) -> Dict[str, Any]:
        return self.config_manager.reload()

    # ── 备份管理 ──

    def get_backup_files(self, bp_path: str) -> List[Dict[str, Any]]:
        if not bp_path or not os.path.exists(bp_path):
            return []
        backups = []
        for root, _, files in os.walk(bp_path):
            for f in files:
                if f.endswith(".bak"):
                    fp = os.path.join(root, f)
                    backups.append({
                        "filename": f,
                        "path": fp,
                        "folder": root,
                        "original_exists": os.path.exists(fp[:-4]),
                        "size": os.path.getsize(fp),
                        "modified": datetime.fromtimestamp(os.path.getmtime(fp)).strftime("%Y-%m-%d %H:%M:%S"),
                    })
        backups.sort(key=lambda b: os.path.getmtime(b["path"]), reverse=True)
        return backups

    def restore_backup(self, backup_path: str) -> bool:
        from core.use_cases.backup_management import BackupManager
        return BackupManager().restore_backup(backup_path, backup_path[:-4])

    def delete_backup_file(self, backup_path: str) -> bool:
        from core.use_cases.backup_management import BackupManager
        return BackupManager().delete_backup(backup_path)

    # ── 文件夹选择 ──

    def select_bp_folder(self, path: str) -> Dict[str, Any]:
        if not path or not os.path.isdir(path):
            return {"success": False, "error": "无效的BP文件夹路径"}
        return {"success": True, "path": path, "name": os.path.basename(path)}

    def select_rp_folder(self, path: str) -> Dict[str, Any]:
        if not path or not os.path.isdir(path):
            return {"success": False, "error": "无效的RP文件夹路径"}
        return {"success": True, "path": path, "name": os.path.basename(path)}

    # ── 脚本预览 ──

    def analyze_js_for_preview(self, bp_path: str, mode: int = 2,
                                progress_callback=None, log_callback=None) -> Dict[str, Any]:
        from core.script_translation import create_script_translation
        js_files = create_script_translation(self.api_manager).scan_js_files(bp_path, log_callback)
        if not js_files:
            return {"file_analyses": [], "summary": {"total_files": 0}, "js_files": []}
        analysis = create_script_translation(self.api_manager).analyze_js_files_for_preview(
            js_files, mode=mode, progress_callback=progress_callback, log_callback=log_callback)
        analysis["js_files"] = js_files
        return analysis

    # ── 统计 ──

    def collect_performance_stats(self) -> Dict[str, Any]:
        stats = {}
        try:
            from core.script_translation import JSASTExtractor
            stats["ast_cache"] = JSASTExtractor.get_cache_stats()
        except Exception:
            stats["ast_cache"] = {}

        try:
            cs = self.api_manager.cache.get_cache_stats()
            stats["translation_cache"] = cs
        except Exception:
            stats["translation_cache"] = {}

        try:
            stats["api"] = self.api_manager.get_api_stats()
        except Exception:
            stats["api"] = {}

        try:
            from core.metrics_collector import get_metrics_collector
            get_metrics_collector().record_memory()
            stats["realtime"] = get_metrics_collector().get_snapshot()
        except Exception:
            stats["realtime"] = {}

        return stats

    # ── UseCase 直接调用方法 ──

    def extract_only(self, bp_path: str, rp_path: Optional[str] = None,
                     progress_callback: Optional[Callable] = None,
                     log_callback: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
        """功能1: 仅提取汉化key"""
        wrapped_progress = self._wrap_progress_callback(progress_callback)
        return self._extract_only_uc.execute(
            bp_path=bp_path, rp_path=rp_path,
            progress_callback=wrapped_progress, log_callback=log_callback
        )

    def extract_and_translate(self, bp_path: str, rp_path: Optional[str] = None,
                              progress_callback: Optional[Callable] = None,
                              log_callback: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
        """功能2: 提取+AI翻译"""
        wrapped_progress = self._wrap_progress_callback(progress_callback)
        return self._extract_translate_uc.execute(
            bp_path=bp_path, rp_path=rp_path,
            progress_callback=wrapped_progress, log_callback=log_callback
        )

    def replace_display_names(self, bp_path: str,
                               progress_callback: Optional[Callable] = None,
                               log_callback: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
        """功能3: 替换display_name"""
        wrapped_progress = self._wrap_progress_callback(progress_callback)
        return self._replace_display_uc.execute(
            bp_path=bp_path,
            progress_callback=wrapped_progress, log_callback=log_callback
        )

    def one_click_service(self, bp_path: str, rp_path: Optional[str] = None,
                          progress_callback: Optional[Callable] = None,
                          log_callback: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
        """功能7: 一条龙服务"""
        wrapped_progress = self._wrap_progress_callback(progress_callback)
        return self._one_click_uc.execute(
            bp_path=bp_path, rp_path=rp_path,
            progress_callback=wrapped_progress, log_callback=log_callback
        )

    def batch_delete_value(self, folder_path: str,
                           progress_callback: Optional[Callable] = None,
                           log_callback: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
        """功能4: 批量删除value"""
        wrapped_progress = self._wrap_progress_callback(progress_callback)
        return self._batch_delete_uc.execute(
            folder_path=folder_path,
            progress_callback=wrapped_progress, log_callback=log_callback
        )

    def batch_restore_value(self, folder_path: str,
                            progress_callback: Optional[Callable] = None,
                            log_callback: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
        """功能5: 批量还原value"""
        wrapped_progress = self._wrap_progress_callback(progress_callback)
        return self._batch_restore_uc.execute(
            folder_path=folder_path,
            progress_callback=wrapped_progress, log_callback=log_callback
        )

    def translate_lang_file(self, lang_file_path: str, bp_path: Optional[str] = None,
                            rp_path: Optional[str] = None,
                            progress_callback: Optional[Callable] = None,
                            log_callback: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
        """功能6: 翻译独立的.lang文件"""
        wrapped_progress = self._wrap_progress_callback(progress_callback)
        return self._translate_lang_uc.execute(
            lang_file_path=lang_file_path, bp_path=bp_path, rp_path=rp_path,
            progress_callback=wrapped_progress, log_callback=log_callback
        )

    def translate_single_js_file(self, js_file_path: str, mode: int = 2,
                                  progress_callback: Optional[Callable] = None,
                                  log_callback: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
        """功能9: 翻译单个JS文件"""
        wrapped_progress = self._wrap_progress_callback(progress_callback)
        return self._translate_js_uc.execute(
            js_file_path=js_file_path, mode=mode,
            progress_callback=wrapped_progress, log_callback=log_callback
        )

    def adapt_entity_display_names(self, bp_path: str, rp_path: Optional[str] = None,
                                    progress_callback: Optional[Callable] = None,
                                    log_callback: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
        """功能8: 高亮实体信息显示名称适配"""
        wrapped_progress = self._wrap_progress_callback(progress_callback)
        return self._adapt_entity_uc.execute(
            bp_path=bp_path, rp_path=rp_path,
            progress_callback=wrapped_progress, log_callback=log_callback
        )

    def script_hardcode_translation(self, bp_path: str, mode: int = 2,
                                     progress_callback: Optional[Callable] = None,
                                     log_callback: Optional[Callable[[str], None]] = None,
                                     ui_keywords: Optional[List[str]] = None) -> Dict[str, Any]:
        """功能10: 脚本文件夹硬编码汉化"""
        wrapped_progress = self._wrap_progress_callback(progress_callback)
        return self._script_hardcode_uc.execute(
            bp_path=bp_path, mode=mode,
            progress_callback=wrapped_progress, log_callback=log_callback,
            ui_keywords=ui_keywords
        )

    def get_backups(self, directory: str) -> Dict[str, Any]:
        """功能11: 获取备份列表"""
        return self._backup_uc.get_backups(directory)

    def restore_backup_uc(self, backup_path: str, original_path: str) -> Dict[str, Any]:
        """功能11: 恢复备份"""
        return self._backup_uc.restore_backup(backup_path, original_path)

    def delete_backup_uc(self, backup_path: str) -> Dict[str, Any]:
        """功能11: 删除备份"""
        return self._backup_uc.delete_backup(backup_path)

    def translate_mcstructure(self, bp_path: str, rp_path: Optional[str] = None,
                              progress_callback: Optional[Callable] = None,
                              log_callback: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
        """功能12: mcstructure汉化"""
        wrapped_progress = self._wrap_progress_callback(progress_callback)
        return self._mcstructure_uc.execute(
            bp_folder_path=bp_path,
            progress_callback=wrapped_progress, log_callback=log_callback
        )

    # ── 通用UseCase调用方法（向后兼容） ──

    def run_use_case(self, method_name: str, **kwargs) -> Dict[str, Any]:
        """通用UseCase调用方法

        Args:
            method_name: 方法名称（如 'extract_only', 'extract_and_translate' 等）
            **kwargs: 传递给方法的参数

        Returns:
            执行结果字典
        """
        method = getattr(self, method_name, None)
        if method is None:
            return {"success": False, "message": f"未知功能: {method_name}"}
        return method(**kwargs)
