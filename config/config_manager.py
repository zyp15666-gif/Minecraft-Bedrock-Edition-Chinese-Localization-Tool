#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块

支持 API Key 安全存储（Windows DPAPI 加密）：
- API Key 存储在单独的加密文件中，不在 config.yml 明文保存
- 加密后的数据只能由当前 Windows 用户解密
"""

import logging
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from api.api_defaults import SUPPORTED_PROVIDER_KEYS
from config.config_schema import validate_config as schema_validate
from core.app_paths import APP_FOLDER_NAME, get_documents_base
from core.secure_storage import get_secure_storage, retrieve_api_key, store_api_key

logger = logging.getLogger(__name__)

CONFIG_VERSION = "2.2"
CONFIG_VERSION_KEY = "_config_version"


class ConfigManager:
    """配置管理器"""

    def __init__(self):
        """初始化配置管理器"""
        self.config_path = self._get_config_path()
        self.config = self._load_default_config()

    def _get_config_path(self) -> Path:
        """获取配置文件路径

        处理PyInstaller打包后的路径问题：
        - 开发环境：使用当前文件所在目录
        - 打包环境：使用用户的Documents文件夹（兼容旧版Windows）
        """
        if getattr(sys, 'frozen', False):
            documents_dir = get_documents_base()
            app_config_dir = documents_dir / APP_FOLDER_NAME
            app_config_dir.mkdir(parents=True, exist_ok=True)
            config_path = app_config_dir / "config.yml"
            logger.info(f"打包环境 - 配置文件路径: {config_path}")
            return config_path
        else:
            config_path = Path(__file__).parent / "config.yml"
            logger.info(f"开发环境 - 配置文件路径: {config_path}")
            return config_path

    def _find_valid_documents_path(self) -> Path:
        """查找有效的 Documents 文件夹路径（兼容测试与旧代码）。"""
        return get_documents_base()

    def _apply_performance_preset(self, config: Dict[str, Any]) -> None:
        """根据 basic.performance_preset 覆盖并发与批大小（small / balanced / large）。"""
        basic = config.get("basic") or {}
        preset = (basic.get("performance_preset") or "").strip().lower()
        if not preset:
            return
        from config.performance_presets import PRESETS
        if preset not in PRESETS:
            logger.warning("[ConfigManager] 未知 performance_preset=%s，忽略", preset)
            return
        merged = dict(PRESETS[preset])
        config.setdefault("basic", {}).update(merged)
        logger.info("[ConfigManager] 已应用性能预设 %s: %s", preset, merged)

    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        return {
            "basic": {
                "namespace": "sgs_farm",
                "indent": 4,
                "use_multithreading": True,
                "max_workers": 20,
                "max_retries": 2,
                "batch_size": 100,
                "cache_max_size": 2000,
                "max_threads_per_api": 3,
                "update_interval": 0.3,
                "update_batch_size": 10,
                "ast_cache_maxsize": 128,
                "base_delay": 1.0,
                "log_level": "INFO",  # DEBUG, INFO, WARNING, ERROR
                "local_model_use_prompt": True,
                "use_multi_api_validation": False, # 默认关闭多重验证
                "local_first_fallback": True,   # 是否启用本地优先 + 质量降级
                "performance_preset": "",  # 空=不应用；可选 small | balanced | large
            },
            "rate_limit": {
                "default": 0.15,
                "local_ollama": 0.0
            },
            "terminology": {
                "dict_path": "resources/api/minecraft_terms.json",
                "enabled": True,
                "mode": "aggressive",
                "min_term_length": 3,
                "auto_update": False,
                "update_check_interval_days": 30,
                "update_url": "",
                "backup_before_update": True
            },
            "update": {
                "check_on_startup": False,  # 启动时检查更新（关闭以避免网络问题）
                "check_interval_hours": 24,  # 检查间隔（小时）
                "repo_owner": "",  # GitHub 仓库所有者（留空则使用默认）
                "repo_name": ""    # GitHub 仓库名（留空则使用默认）
            },
            "author": {
                "name": "Minecraft基岩版汉化工具",
                "description": "由 Minecraft基岩版汉化工具 自动生成"
            },
            "local_ollama": [],
            "deepseek": [],
            "qwen": [],
            "zhipu": [],
            "doubao": [],
            "ui": {
                "dark_mode": True,
                "language": "zh_CN",
                "window_size": [800, 600],
                "startup_animation_duration": 0.8
            }
        }

    CONFIG_VERSION = "2.0"

    CONFIG_SCHEMA = {
        "basic": {
            "required_keys": ["namespace", "max_workers", "cache_max_size"],
            "types": {
                "namespace": str,
                "max_workers": int,
                "cache_max_size": int,
                "indent": int,
                "use_multithreading": bool,
            },
            "ranges": {
                "max_workers": (1, 100),
                "cache_max_size": (100, 100000),
                "indent": (2, 8),
            }
        },
        "rate_limit": {
            "required_keys": ["default"],
            "types": {
                "default": (int, float),
                "local_ollama": (int, float),
            },
            "ranges": {
                "default": (0.0, 10.0),
                "local_ollama": (0.0, 10.0),
            }
        },
        "terminology": {
            "required_keys": [],
            "types": {
                "enabled": bool,
                "min_term_length": int,
            },
            "ranges": {
                "min_term_length": (1, 50),
            }
        }
    }

    _URL_PATTERN = re.compile(
        r'^https?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    def validate_config(self, config: Dict[str, Any] = None) -> Dict[str, Any]:
        if config is None:
            config = self.config

        errors = []
        warnings = []
        fixed_config = dict(config)

        self._validate_sections(fixed_config, errors, warnings)
        self._validate_api_providers(fixed_config, errors, warnings)

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "fixed_config": fixed_config,
        }

    def _validate_sections(self, fixed_config: dict, errors: list, warnings: list):
        for section_name, schema in self.CONFIG_SCHEMA.items():
            if section_name not in fixed_config:
                if section_name in ("basic", "rate_limit"):
                    errors.append(f"缺少必需的配置节: [{section_name}]")
                else:
                    warnings.append(f"缺少可选配置节: [{section_name}]")
                continue

            section = fixed_config[section_name]
            if not isinstance(section, dict):
                errors.append(f"配置节 [{section_name}] 格式错误，应为字典")
                continue

            for key in schema.get("required_keys", []):
                if key not in section:
                    errors.append(f"配置节 [{section_name}] 缺少必需键: {key}")

            for key, expected_type in schema.get("types", {}).items():
                if key in section and not isinstance(section[key], expected_type):
                    type_name = expected_type.__name__ if isinstance(expected_type, type) else str(expected_type)
                    warnings.append(
                        f"配置节 [{section_name}].{key} 类型错误: "
                        f"期望 {type_name}，实际 {type(section[key]).__name__}")

            for key, (min_val, max_val) in schema.get("ranges", {}).items():
                if key in section:
                    val = section[key]
                    if isinstance(val, (int, float)):
                        if val < min_val or val > max_val:
                            clamped = max(min_val, min(max_val, val))
                            warnings.append(
                                f"配置节 [{section_name}].{key} 值 {val} 超出范围 "
                                f"[{min_val}, {max_val}]，已修正为 {clamped}")
                            section[key] = clamped

    def _validate_api_providers(self, fixed_config: dict, errors: list, warnings: list):
        for provider in SUPPORTED_PROVIDER_KEYS:
            apis = fixed_config.get(provider, [])
            if not isinstance(apis, list):
                warnings.append(f"配置项 [{provider}] 应为列表格式")
                continue
            for i, api in enumerate(apis):
                if not isinstance(api, dict):
                    errors.append(f"配置项 [{provider}][{i}] 格式错误，应为字典")
                    continue
                if "name" not in api:
                    errors.append(f"配置项 [{provider}][{i}] 缺少 'name' 字段")
                api_url = api.get("api_url", "")
                if api_url:
                    if not self._URL_PATTERN.match(api_url):
                        warnings.append(f"配置项 [{provider}][{i}] 的 api_url 格式可能无效: {api_url[:50]}")

    def load_config(self, raise_on_error: bool = False) -> Dict[str, Any]:
        """加载配置文件

        Args:
            raise_on_error: 是否在验证失败时抛出异常，默认False（仅记录错误）
        """
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                self._merge_configs(self.config, config)
                self._strip_runtime_paths(self.config)
                self._resolve_env_variables(self.config)
                self._apply_performance_preset(self.config)

                self._load_api_keys_from_secure_storage()

                self._migrate_config_version()

                result = self.validate_config(self.config)
                if result["warnings"]:
                    for warning in result["warnings"]:
                        logger.warning(f"[ConfigManager] 配置警告: {warning}")
                if result["errors"]:
                    error_msg = "\n".join(result["errors"])
                    logger.error(f"[ConfigManager] 配置错误:\n{error_msg}")
                    if raise_on_error:
                        from core.exceptions import ConfigValidationError
                        raise ConfigValidationError(f"配置验证失败，共 {len(result['errors'])} 个错误:\n{error_msg}")
                if result["warnings"] or result["errors"]:
                    self.config = result["fixed_config"]

                schema_errors = schema_validate(self.config)
                if schema_errors:
                    from config.config_schema import format_validation_errors
                    msg = format_validation_errors(schema_errors)
                    logger.info(f"[ConfigManager] Schema 验证:\n{msg}")

                return self.config
            except Exception as e:
                if raise_on_error and not isinstance(e, ConfigValidationError):
                    from core.exceptions import ConfigError
                    raise ConfigError(f"加载配置文件失败: {e}") from e
                logger.error(f"加载配置文件失败: {e}")
                return self.config
        else:
            return self.config

    def _load_api_keys_from_secure_storage(self):
        """从安全存储加载 API Key 到配置中"""
        try:
            get_secure_storage()
            api_providers = SUPPORTED_PROVIDER_KEYS

            for provider in api_providers:
                if provider not in self.config or not isinstance(self.config[provider], list):
                    continue

                for api_entry in self.config[provider]:
                    if not isinstance(api_entry, dict):
                        continue

                    api_name = api_entry.get('name', '')
                    if not api_name:
                        continue

                    stored_key = retrieve_api_key(provider, api_name)
                    if stored_key:
                        api_entry['api_key'] = stored_key
                        logger.debug(f"[ConfigManager] 从安全存储加载 API Key: {provider}/{api_name}")

        except Exception as e:
            logger.warning(f"[ConfigManager] 从安全存储加载 API Key 失败: {e}")

    def _migrate_config_version(self):
        """迁移配置版本"""
        current_version = self.config.get(CONFIG_VERSION_KEY, "1.0")

        if current_version == CONFIG_VERSION:
            return

        logger.info(f"[ConfigManager] 配置版本迁移: {current_version} -> {CONFIG_VERSION}")

        if current_version < "2.0":
            self._migrate_v1_to_v2()

        if current_version < "2.1":
            self._migrate_v2_to_v2_1()

        if current_version < "2.2":
            self._migrate_v2_1_to_v2_2()

        self.config[CONFIG_VERSION_KEY] = CONFIG_VERSION
        logger.info(f"[ConfigManager] 配置迁移完成，当前版本: {CONFIG_VERSION}")

    def _migrate_v1_to_v2(self):
        """从 v1.x 迁移到 v2.0"""
        pass

    def _migrate_v2_to_v2_1(self):
        """从 v2.0 迁移到 v2.1 - 迁移 API Key 到安全存储"""
        try:
            secure_storage = get_secure_storage()
            migrated = secure_storage.migrate_from_config(self.config)

            if migrated > 0:
                self._remove_api_keys_from_config()
                logger.info(f"[ConfigManager] 已迁移 {migrated} 个 API Key 到安全存储")
        except Exception as e:
            logger.warning(f"[ConfigManager] API Key 迁移失败: {e}")

    def _migrate_v2_1_to_v2_2(self):
        """从 v2.1 迁移到 v2.2 - 添加更新检查配置节"""
        if 'update' not in self.config:
            self.config['update'] = {
                'check_on_startup': False,
                'check_interval_hours': 24,
                'repo_owner': '',
                'repo_name': ''
            }
            logger.info("[ConfigManager] 已添加更新检查配置节")

    def _remove_api_keys_from_config(self):
        """从配置中移除 API Key（已迁移到安全存储）"""
        api_providers = SUPPORTED_PROVIDER_KEYS
        placeholder_patterns = [
            '你的', 'your_', 'your-key', 'your_key', 'placeholder',
            'xxx', 'XXXX', '***', 'api_key_here', 'key_here',
            'sk-test', 'test-key', 'test_key', 'fake_', 'mock_'
        ]

        for provider in api_providers:
            if provider not in self.config or not isinstance(self.config[provider], list):
                continue

            for api_entry in self.config[provider]:
                if not isinstance(api_entry, dict):
                    continue

                api_key = api_entry.get('api_key', '')
                if api_key:
                    is_placeholder = any(p.lower() in str(api_key).lower() for p in placeholder_patterns)
                    if not is_placeholder:
                        api_entry['api_key'] = f"<SECURE:{provider}>"

    def _resolve_env_variables(self, config: Dict[str, Any]):
        """递归解析配置中的环境变量引用

        支持 ${ENV_VAR} 和 ${ENV_VAR:default} 语法。
        当 api_key 值为空或包含占位符时，自动从环境变量读取。

        Args:
            config: 配置字典
        """
        api_providers = SUPPORTED_PROVIDER_KEYS
        placeholder_patterns = [
            '你的', 'your_', 'your-key', 'your_key', 'placeholder',
            'xxx', 'XXXX', '***', 'api_key_here', 'key_here',
            'sk-test', 'test-key', 'test_key', 'fake_', 'mock_'
        ]

        for provider in api_providers:
            if provider not in config or not isinstance(config[provider], list):
                continue
            for api_entry in config[provider]:
                if not isinstance(api_entry, dict):
                    continue
                api_key = api_entry.get('api_key', '')
                api_entry.get('name', provider)

                is_placeholder = (
                    not api_key or
                    any(p.lower() in str(api_key).lower() for p in placeholder_patterns)
                )

                if is_placeholder:
                    env_name = f"{provider.upper()}_API_KEY"
                    env_value = os.environ.get(env_name, '')
                    if env_value:
                        if self._validate_env_value(env_value, env_name):
                            api_entry['api_key'] = env_value
                        else:
                            pass
                    else:
                        pass

    def _validate_env_value(self, value: str, var_name: str) -> bool:
        """验证环境变量的安全性

        Args:
            value: 环境变量值
            var_name: 环境变量名

        Returns:
            bool: 值安全返回True，否则返回False
        """
        if not value:
            return False
        dangerous_patterns = [
            r'[\'"`];',  # 可能的命令注入
            r'[\'"`]\s*rm\s',  # rm 命令注入
            r'[\'"`]\s*cat\s',  # cat 命令注入
            r'[\'"`]\s*echo\s',  # echo 命令注入
            r'[\'"`]\s*wget\s',  # wget 命令注入
            r'[\'"`]\s*curl\s',  # curl 命令注入
            r'[\'"`]\s*python\s',  # python 命令注入
            r'[\'"`]\s*bash\s',  # bash 命令注入
            r'[\'"`]\s*sh\s',  # sh 命令注入
        ]
        if '\n' in value or '\r' in value:
            return False
        for pattern in dangerous_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                return False
        if len(value) > 500:
            return False
        return True

    def _merge_configs(self, default: Dict[str, Any], user: Dict[str, Any]):
        """合并配置"""
        for key, value in user.items():
            if key in default and isinstance(default[key], dict) and isinstance(value, dict):
                self._merge_configs(default[key], value)
            else:
                default[key] = value

    def save_config(self, config: Dict[str, Any] = None, create_backup: bool = True) -> bool:
        """保存配置文件（原子写入）

        API Key 会自动存储到安全存储中，配置文件中只保留占位符。

        Args:
            config: 要保存的配置字典，如果为None则保存当前配置
            create_backup: 是否在保存前创建备份

        Returns:
            bool: 保存成功返回True，失败返回False
        """
        if config is not None:
            self.config = config

        config_to_save = self._prepare_config_for_save()

        temp_fd = None

        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            if create_backup and self.config_path.exists():
                backup_path = self._create_backup()
                if not backup_path:
                    logger.warning("[ConfigManager] 警告：无法创建配置备份")

            temp_fd, temp_path_str = tempfile.mkstemp(
                suffix='.yml.tmp',
                prefix='config_',
                dir=self.config_path.parent
            )

            with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                yaml.dump(config_to_save, f, default_flow_style=False, allow_unicode=True)
                f.flush()
                os.fsync(f.fileno())

            temp_fd = None

            try:
                with open(temp_path_str, 'r', encoding='utf-8') as f:
                    yaml.safe_load(f)
            except yaml.YAMLError as e:
                logger.error(f"[ConfigManager] 临时文件验证失败，中止保存: {e}")
                if os.path.exists(temp_path_str):
                    os.unlink(temp_path_str)
                return False

            os.replace(temp_path_str, self.config_path)

            if self.config_path.exists():
                file_size = self.config_path.stat().st_size
                logger.info(f"[ConfigManager] 配置已保存 ({file_size} 字节)")
                return True
            else:
                logger.error("[ConfigManager] 保存配置失败：文件不存在")
                return False

        except PermissionError as e:
            logger.error(f"[ConfigManager] 保存配置文件失败 - 权限错误: {e}")
            import traceback
            traceback.print_exc()
            return False
        except Exception as e:
            logger.error(f"[ConfigManager] 保存配置文件失败: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            if temp_fd is not None:
                try:
                    os.close(temp_fd)
                except OSError:
                    pass
            if temp_path_str and os.path.exists(temp_path_str):
                try:
                    os.unlink(temp_path_str)
                except OSError:
                    pass

    def _prepare_config_for_save(self) -> Dict[str, Any]:
        """准备配置用于保存，将 API Key 存储到安全存储并替换为占位符"""
        import copy
        config_copy = copy.deepcopy(self.config)

        config_copy[CONFIG_VERSION_KEY] = CONFIG_VERSION

        self._save_api_keys_to_secure_storage(config_copy)

        self._mask_api_keys_in_config(config_copy)

        return config_copy

    def _save_api_keys_to_secure_storage(self, config: Dict[str, Any]):
        """将 API Key 保存到安全存储"""
        api_providers = SUPPORTED_PROVIDER_KEYS
        placeholder_patterns = [
            '你的', 'your_', 'your-key', 'your_key', 'placeholder',
            'xxx', 'XXXX', '***', 'api_key_here', 'key_here',
            'sk-test', 'test-key', 'test_key', 'fake_', 'mock_'
        ]

        for provider in api_providers:
            if provider not in config or not isinstance(config[provider], list):
                continue

            for api_entry in config[provider]:
                if not isinstance(api_entry, dict):
                    continue

                api_name = api_entry.get('name', '')
                api_key = api_entry.get('api_key', '')

                if not api_name or not api_key:
                    continue

                is_placeholder = any(p.lower() in str(api_key).lower() for p in placeholder_patterns)
                is_secure_placeholder = api_key.startswith('<SECURE:')

                if not is_placeholder and not is_secure_placeholder:
                    if store_api_key(provider, api_name, api_key):
                        logger.debug(f"[ConfigManager] API Key 已保存到安全存储: {provider}/{api_name}")

    def _mask_api_keys_in_config(self, config: Dict[str, Any]):
        """在配置中用占位符替换 API Key"""
        api_providers = SUPPORTED_PROVIDER_KEYS
        placeholder_patterns = [
            '你的', 'your_', 'your-key', 'your_key', 'placeholder',
            'xxx', 'XXXX', '***', 'api_key_here', 'key_here',
            'sk-test', 'test-key', 'test_key', 'fake_', 'mock_'
        ]

        for provider in api_providers:
            if provider not in config or not isinstance(config[provider], list):
                continue

            for api_entry in config[provider]:
                if not isinstance(api_entry, dict):
                    continue

                api_key = api_entry.get('api_key', '')
                if api_key:
                    is_placeholder = any(p.lower() in str(api_key).lower() for p in placeholder_patterns)
                    is_secure_placeholder = api_key.startswith('<SECURE:')

                    if not is_placeholder and not is_secure_placeholder:
                        api_entry['api_key'] = f"<SECURE:{provider}>"

    def _create_backup(self) -> Optional[str]:
        """创建配置文件备份

        Returns:
            备份文件路径，失败返回None
        """
        try:
            if not self.config_path.exists():
                return None

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = self.config_path.parent / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)

            backup_path = backup_dir / f"config_backup_{timestamp}.yml"

            import shutil
            shutil.copy2(self.config_path, backup_path)

            self._cleanup_old_backups(backup_dir)

            logger.info(f"[ConfigManager] 配置已备份: {backup_path.name}")
            return str(backup_path)

        except Exception as e:
            logger.error(f"[ConfigManager] 创建配置备份失败: {e}")
            return None

    def _cleanup_old_backups(self, backup_dir: Path, max_backups: int = 5):
        """清理旧备份文件，保留最近的N个

        Args:
            backup_dir: 备份目录路径
            max_backups: 最大保留备份数量
        """
        try:
            backup_files = sorted(
                backup_dir.glob("config_backup_*.yml"),
                key=lambda f: f.stat().st_mtime,
                reverse=True
            )

            for old_backup in backup_files[max_backups:]:
                old_backup.unlink()
                logger.info(f"[ConfigManager] 已删除旧备份: {old_backup.name}")

        except Exception as e:
            logger.error(f"[ConfigManager] 清理旧备份失败: {e}")

    def restore_from_backup(self, backup_name: Optional[str] = None) -> bool:
        """从备份恢复配置

        Args:
            backup_name: 备份文件名，如果为None则恢复最近的备份

        Returns:
            是否成功恢复
        """
        try:
            backup_dir = self.config_path.parent / "backups"

            if not backup_dir.exists():
                logger.warning("[ConfigManager] 备份目录不存在")
                return False

            if backup_name:
                backup_path = backup_dir / backup_name
            else:
                backup_files = sorted(
                    backup_dir.glob("config_backup_*.yml"),
                    key=lambda f: f.stat().st_mtime,
                    reverse=True
                )
                if not backup_files:
                    logger.warning("[ConfigManager] 没有找到备份文件")
                    return False
                backup_path = backup_files[0]

            if not backup_path.exists():
                logger.error(f"[ConfigManager] 备份文件不存在: {backup_path}")
                return False

            with open(backup_path, 'r', encoding='utf-8') as f:
                restored_config = yaml.safe_load(f)

            if restored_config:
                self._merge_configs(self.config, restored_config)
                logger.info(f"[ConfigManager] 已从备份恢复配置: {backup_path.name}")
                return True
            else:
                logger.error("[ConfigManager] 备份文件内容无效")
                return False

        except Exception as e:
            logger.error(f"[ConfigManager] 从备份恢复配置失败: {e}")
            return False

    def list_backups(self) -> List[str]:
        """列出所有可用的备份文件

        Returns:
            备份文件名列表（按时间倒序）
        """
        try:
            backup_dir = self.config_path.parent / "backups"
            if not backup_dir.exists():
                return []

            backup_files = sorted(
                backup_dir.glob("config_backup_*.yml"),
                key=lambda f: f.stat().st_mtime,
                reverse=True
            )

            return [f.name for f in backup_files]

        except Exception as e:
            logger.error(f"[ConfigManager] 列出备份文件失败: {e}")
            return []

    def export_config(self, filepath: str) -> bool:
        """导出配置到指定文件

        Args:
            filepath: 导出文件路径

        Returns:
            是否成功
        """
        try:
            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)

            with open(filepath, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True)

            logger.info(f"[ConfigManager] 配置已导出到: {filepath}")
            return True
        except Exception as e:
            logger.error(f"[ConfigManager] 导出配置失败: {e}")
            return False

    def import_config(self, filepath: str, merge: bool = True) -> bool:
        """从指定文件导入配置

        Args:
            filepath: 导入文件路径
            merge: 是否合并到当前配置（True）或替换当前配置（False）

        Returns:
            是否成功
        """
        try:
            if not os.path.exists(filepath):
                logger.error(f"[ConfigManager] 导入文件不存在: {filepath}")
                return False

            with open(filepath, 'r', encoding='utf-8') as f:
                imported_config = yaml.safe_load(f)

            if merge:
                # 合并配置
                self._merge_configs(self.config, imported_config)
            else:
                self.config = imported_config

            logger.info(f"[ConfigManager] 配置已从文件导入: {filepath}")
            return True
        except Exception as e:
            logger.error(f"[ConfigManager] 导入配置失败: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        keys = key.split('.')
        value = self.config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any):
        """设置配置值"""
        keys = key.split('.')
        config = self.config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    DEFAULT_FUNCTION_BUTTONS = [
        {'id': 'extract_only', 'label': '📋 [1] 仅提取汉化 key', 'icon': 'CONTENT_COPY', 'enabled': True, 'order': 1},
        {'id': 'extract_and_translate', 'label': '🌐 [2] 提取+AI 翻译', 'icon': 'LANGUAGE', 'enabled': True, 'order': 2},
        {'id': 'replace_display_names', 'label': '🔄 [3] 全 BP 替换 display_name', 'icon': 'SYNC', 'enabled': True, 'order': 3},
        {'id': 'batch_delete_value', 'label': '🗑️ [4] 批量删除 value', 'icon': 'DELETE', 'enabled': True, 'order': 4},
        {'id': 'batch_restore_value', 'label': '♻️ [5] 批量还原 value', 'icon': 'RECYCLING', 'enabled': True, 'order': 5},
        {'id': 'translate_lang_file', 'label': '📄 [6] 翻译独立的.lang 文件', 'icon': 'DESCRIPTION', 'enabled': True, 'order': 6},
        {'id': 'one_click_service', 'label': '🚀 [7] 一条龙服务', 'icon': 'ROCKET_LAUNCH', 'enabled': True, 'order': 7},
        {'id': 'adapt_entity_display_names', 'label': '✨ [8] 高亮实体信息显示名称', 'icon': 'STAR', 'enabled': True, 'order': 8},
        {'id': 'translate_single_js_file', 'label': '📖 [9] 翻译单个 JS 文件', 'icon': 'CODE', 'enabled': True, 'order': 9},
        {'id': 'script_hardcode_translation', 'label': '🔧 [10] 脚本硬编码汉化(慎用)', 'icon': 'CONSTRUCTION', 'enabled': True, 'order': 10},
        {'id': 'backup_management', 'label': '💾 [11] 备份文件管理', 'icon': 'BACKUP', 'enabled': True, 'order': 11},
        {'id': 'translate_mcstructure', 'label': '📚 [12] mcstructure汉化', 'icon': 'MENU_BOOK', 'enabled': True, 'order': 12},
    ]

    def get_function_buttons_config(self) -> List[Dict[str, Any]]:
        """获取功能按钮配置列表（按 order 排序）

        Returns:
            按钮配置列表，每项包含 id, label, icon, enabled, order
        """
        buttons = self.config.get('ui', {}).get('function_buttons', [])
        if not buttons:
            return self.DEFAULT_FUNCTION_BUTTONS.copy()
        validated_buttons = [self._validate_button_config(btn) for btn in buttons]
        validated_buttons = [btn for btn in validated_buttons if btn is not None]
        sorted_buttons = sorted(validated_buttons, key=lambda x: x.get('order', 999))
        return sorted_buttons

    def _validate_button_config(self, button: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """校验按钮配置结构的有效性

        Args:
            button: 按钮配置字典

        Returns:
            校验通过返回原始配置，否则返回 None
        """
        required_fields = {'id', 'label', 'icon', 'enabled', 'order'}
        if not isinstance(button, dict):
            logger.error("[ConfigManager] 按钮配置无效：不是字典类型")
            return None
        missing_fields = required_fields - set(button.keys())
        if missing_fields:
            logger.error(f"[ConfigManager] 按钮配置缺少字段: {missing_fields}")
            return None
        if not isinstance(button.get('id'), str) or not button['id']:
            logger.error("[ConfigManager] 按钮配置 id 无效")
            return None
        if not isinstance(button.get('label'), str) or not button['label']:
            logger.error("[ConfigManager] 按钮配置 label 无效")
            return None
        if not isinstance(button.get('icon'), str):
            logger.error("[ConfigManager] 按钮配置 icon 无效")
            return None
        if not isinstance(button.get('enabled'), bool):
            logger.warning("[ConfigManager] 按钮配置 enabled 无效，使用默认值 True")
            button['enabled'] = True
        if not isinstance(button.get('order'), (int, float)):
            logger.warning("[ConfigManager] 按钮配置 order 无效，使用默认值 999")
            button['order'] = 999
        return button

    def update_function_buttons_config(self, buttons_config: List[Dict[str, Any]]) -> bool:
        """更新功能按钮配置

        Args:
            buttons_config: 按钮配置列表

        Returns:
            是否成功
        """
        try:
            if 'ui' not in self.config:
                self.config['ui'] = {}
            self.config['ui']['function_buttons'] = buttons_config
            return True
        except Exception as e:
            logger.error(f"[ConfigManager] 更新按钮配置失败: {e}")
            return False

    def get_function_button_by_id(self, button_id: str) -> Optional[Dict[str, Any]]:
        """根据 ID 获取单个按钮配置

        Args:
            button_id: 按钮 ID

        Returns:
            按钮配置字典，如果不存在返回 None
        """
        buttons = self.get_function_buttons_config()
        for btn in buttons:
            if btn.get('id') == button_id:
                return btn
        return None

    def _strip_runtime_paths(self, config: Dict[str, Any]):
        """清除配置中不应持久化的运行时路径（bp_folder, rp_folder 等）"""
        runtime_keys = {'bp_folder', 'rp_folder', 'bp_path', 'rp_path', 'last_folder'}
        for key in runtime_keys:
            config.pop(key, None)
        for section_name in ('basic', 'ui'):
            section = config.get(section_name)
            if isinstance(section, dict):
                for key in runtime_keys:
                    section.pop(key, None)

    def restore_default_config(self, keep_api_keys: bool = True) -> Dict[str, Any]:
        """恢复默认配置（可选保留 API 密钥）"""
        api_sections = ('deepseek', 'doubao', 'local_ollama', 'qwen', 'openai',
                        'azure_openai', 'baidu_ernie', 'iflytek_spark', 'google_gemini', 'zhipu')
        saved_apis = {}
        if keep_api_keys:
            for section in api_sections:
                if section in self.config and self.config[section]:
                    saved_apis[section] = self.config[section]

        default = self._load_default_config()
        self.config = default

        if keep_api_keys and saved_apis:
            for section, apis in saved_apis.items():
                self.config[section] = apis

        self.save_config(self.config)
        return self.config

    def reload(self) -> Dict[str, Any]:
        """重新加载配置文件，无需重启应用"""
        if not self.config_path.exists():
            return self.config

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                new_config = yaml.safe_load(f)
            self._merge_configs(self.config, new_config)
            self._resolve_env_variables(self.config)
            result = self.validate_config(self.config)
            if result["warnings"]:
                for warning in result["warnings"]:
                    logger.warning(f"[ConfigManager] 配置警告: {warning}")
            if result["errors"]:
                for error in result["errors"]:
                    logger.error(f"[ConfigManager] 配置错误: {error}")
            if result["warnings"] or result["errors"]:
                self.config = result["fixed_config"]
            logger.info("[ConfigManager] 配置已重新加载")
            return self.config
        except Exception as e:
            logger.error(f"[ConfigManager] 重新加载配置失败: {e}")
            return self.config
