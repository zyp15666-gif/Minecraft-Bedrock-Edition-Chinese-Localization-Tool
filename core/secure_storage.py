#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全存储模块 - 使用 Windows DPAPI 加密敏感数据

仅适用于 Windows 平台，使用 DPAPI (Data Protection API) 加密：
- 加密后的数据只能由当前 Windows 用户账户解密
- 即使数据被复制到其他机器也无法解密
- 加密密钥由 Windows 系统管理，无需用户记忆

使用场景：
- API Key 加密存储
- 敏感配置项保护
"""

import os
import sys
import json
import base64
import hashlib
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

_IS_WINDOWS = sys.platform == 'win32'

if _IS_WINDOWS:
    try:
        import ctypes
        from ctypes import wintypes
        _CRYPT32_AVAILABLE = True
    except ImportError:
        _CRYPT32_AVAILABLE = False
else:
    _CRYPT32_AVAILABLE = False


CRYPTPROTECT_UI_FORBIDDEN = 0x01


class SecureStorageError(Exception):
    """安全存储错误"""
    pass


class SecureStorage:
    """安全存储 - 使用 Windows DPAPI 加密敏感数据"""

    _instance = None
    _lock = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, storage_path: Optional[Path] = None):
        """初始化安全存储

        Args:
            storage_path: 加密存储文件路径，默认为用户配置目录下的 .secure_storage
        """
        if hasattr(self, '_initialized') and self._initialized:
            return

        if storage_path is None:
            if getattr(sys, 'frozen', False):
                base_dir = Path(os.environ.get('USERPROFILE', '~')) / "Documents" / "Minecraft基岩版汉化工具"
            else:
                base_dir = Path(__file__).parent.parent

            self._storage_path = base_dir / ".secure_storage"
        else:
            self._storage_path = Path(storage_path)

        self._storage_path.parent.mkdir(parents=True, exist_ok=True)

        self._data: Dict[str, Any] = {}
        self._modified = False

        self._load()

        self._initialized = True

    def _load(self):
        """加载加密存储"""
        if not self._storage_path.exists():
            logger.debug("安全存储文件不存在，将创建新文件")
            return

        try:
            with open(self._storage_path, 'rb') as f:
                encrypted_data = f.read()

            if not encrypted_data:
                return

            decrypted = self._decrypt_data(encrypted_data)
            if decrypted:
                self._data = json.loads(decrypted)
                logger.debug(f"安全存储已加载，包含 {len(self._data)} 个条目")
        except json.JSONDecodeError as e:
            logger.error(f"安全存储数据格式错误: {e}")
            self._backup_corrupted()
        except SecureStorageError as e:
            logger.error(f"安全存储解密失败: {e}")
            self._backup_corrupted()
        except Exception as e:
            logger.error(f"加载安全存储失败: {e}")

    def _backup_corrupted(self):
        """备份损坏的存储文件"""
        if self._storage_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self._storage_path.with_suffix(f".corrupted_{timestamp}")
            try:
                import shutil
                shutil.copy2(self._storage_path, backup_path)
                logger.warning(f"损坏的存储文件已备份到: {backup_path}")
            except Exception as e:
                logger.error(f"备份损坏文件失败: {e}")

            self._data = {}
            self._modified = True

    def _save(self):
        """保存加密存储"""
        if not self._modified:
            return

        try:
            json_data = json.dumps(self._data, ensure_ascii=False, indent=2)
            encrypted_data = self._encrypt_data(json_data)

            temp_path = self._storage_path.with_suffix('.tmp')
            with open(temp_path, 'wb') as f:
                f.write(encrypted_data)
                f.flush()
                os.fsync(f.fileno())

            if self._storage_path.exists():
                os.replace(temp_path, self._storage_path)
            else:
                temp_path.rename(self._storage_path)

            self._modified = False
            logger.debug("安全存储已保存")
        except Exception as e:
            logger.error(f"保存安全存储失败: {e}")
            raise SecureStorageError(f"保存失败: {e}")

    def _encrypt_data(self, data: str) -> bytes:
        """使用 DPAPI 加密数据

        Args:
            data: 待加密的字符串

        Returns:
            加密后的字节数据
        """
        if not _CRYPT32_AVAILABLE:
            logger.warning("DPAPI 不可用，使用 base64 混淆存储（不推荐）")
            return self._obfuscate_data(data)

        try:
            data_bytes = data.encode('utf-8')

            blob_in = ctypes.create_string_buffer(data_bytes, len(data_bytes))

            blob_out = wintypes.DATA_BLOB()
            blob_in_struct = wintypes.DATA_BLOB()
            blob_in_struct.cbData = len(data_bytes)
            blob_in_struct.pbData = ctypes.cast(blob_in, ctypes.POINTER(wintypes.BYTE))

            if not ctypes.windll.crypt32.CryptProtectData(
                ctypes.byref(blob_in_struct),
                None,
                None,
                None,
                None,
                CRYPTPROTECT_UI_FORBIDDEN,
                ctypes.byref(blob_out)
            ):
                raise SecureStorageError("CryptProtectData 失败")

            result = ctypes.string_at(blob_out.pbData, blob_out.cbData)

            ctypes.windll.kernel32.LocalFree(blob_out.pbData)

            return result

        except Exception as e:
            logger.error(f"DPAPI 加密失败: {e}")
            return self._obfuscate_data(data)

    def _decrypt_data(self, data: bytes) -> Optional[str]:
        """使用 DPAPI 解密数据

        Args:
            data: 加密的字节数据

        Returns:
            解密后的字符串
        """
        if not _CRYPT32_AVAILABLE:
            return self._deobfuscate_data(data)

        try:
            blob_in = wintypes.DATA_BLOB()
            blob_in.cbData = len(data)
            blob_in.pbData = ctypes.cast(
                ctypes.create_string_buffer(data, len(data)),
                ctypes.POINTER(wintypes.BYTE)
            )

            blob_out = wintypes.DATA_BLOB()

            if not ctypes.windll.crypt32.CryptUnprotectData(
                ctypes.byref(blob_in),
                None,
                None,
                None,
                None,
                CRYPTPROTECT_UI_FORBIDDEN,
                ctypes.byref(blob_out)
            ):
                raise SecureStorageError("CryptUnprotectData 失败")

            result = ctypes.string_at(blob_out.pbData, blob_out.cbData).decode('utf-8')

            ctypes.windll.kernel32.LocalFree(blob_out.pbData)

            return result

        except Exception as e:
            logger.error(f"DPAPI 解密失败: {e}")
            return self._deobfuscate_data(data)

    def _obfuscate_data(self, data: str) -> bytes:
        """简单混淆（非加密，仅用于不支持 DPAPI 的环境）"""
        key = hashlib.sha256(b"MinecraftBedrockLocalizer_ObfuscationKey").digest()
        data_bytes = data.encode('utf-8')
        result = bytearray()
        for i, byte in enumerate(data_bytes):
            result.append(byte ^ key[i % len(key)])
        return base64.b64encode(bytes(result))

    def _deobfuscate_data(self, data: bytes) -> Optional[str]:
        """解除混淆"""
        try:
            key = hashlib.sha256(b"MinecraftBedrockLocalizer_ObfuscationKey").digest()
            decoded = base64.b64decode(data)
            result = bytearray()
            for i, byte in enumerate(decoded):
                result.append(byte ^ key[i % len(key)])
            return bytes(result).decode('utf-8')
        except Exception as e:
            logger.error(f"解除混淆失败: {e}")
            return None

    def store_api_key(self, provider: str, api_name: str, api_key: str) -> bool:
        """存储 API Key

        Args:
            provider: 提供商名称（如 'deepseek', 'doubao'）
            api_name: API 配置名称
            api_key: API 密钥

        Returns:
            是否成功存储
        """
        if not api_key:
            return False

        key = f"api_keys.{provider}.{api_name}"

        if 'api_keys' not in self._data:
            self._data['api_keys'] = {}
        if provider not in self._data['api_keys']:
            self._data['api_keys'][provider] = {}

        self._data['api_keys'][provider][api_name] = {
            'key': api_key,
            'updated_at': datetime.now().isoformat()
        }
        self._modified = True

        try:
            self._save()
            logger.debug(f"API Key 已安全存储: {provider}/{api_name}")
            return True
        except Exception as e:
            logger.error(f"存储 API Key 失败: {e}")
            return False

    def retrieve_api_key(self, provider: str, api_name: str) -> Optional[str]:
        """获取 API Key

        Args:
            provider: 提供商名称
            api_name: API 配置名称

        Returns:
            API 密钥，不存在则返回 None
        """
        try:
            return self._data.get('api_keys', {}).get(provider, {}).get(api_name, {}).get('key')
        except Exception:
            return None

    def delete_api_key(self, provider: str, api_name: str) -> bool:
        """删除 API Key

        Args:
            provider: 提供商名称
            api_name: API 配置名称

        Returns:
            是否成功删除
        """
        try:
            if provider in self._data.get('api_keys', {}):
                self._data['api_keys'][provider].pop(api_name, None)
                self._modified = True
                self._save()
            return True
        except Exception as e:
            logger.error(f"删除 API Key 失败: {e}")
            return False

    def list_stored_providers(self) -> Dict[str, list]:
        """列出所有已存储密钥的提供商和配置名称

        Returns:
            {provider: [api_name1, api_name2, ...]}
        """
        result = {}
        for provider, apis in self._data.get('api_keys', {}).items():
            if isinstance(apis, dict):
                result[provider] = list(apis.keys())
        return result

    def migrate_from_config(self, config: Dict[str, Any]) -> int:
        """从配置文件迁移 API Key 到安全存储

        Args:
            config: 配置字典

        Returns:
            迁移的密钥数量
        """
        migrated = 0
        api_providers = [
            'deepseek', 'doubao', 'local_ollama', 'qwen', 'openai',
            'azure_openai', 'baidu_ernie', 'iflytek_spark', 'google_gemini', 'zhipu'
        ]

        for provider in api_providers:
            apis = config.get(provider, [])
            if not isinstance(apis, list):
                continue

            for api_config in apis:
                if not isinstance(api_config, dict):
                    continue

                api_name = api_config.get('name', '')
                api_key = api_config.get('api_key', '')

                if api_name and api_key:
                    placeholder_patterns = [
                        'your', 'your_', 'your-key', 'your_key', 'placeholder',
                        'xxx', 'XXXX', '***', 'api_key_here', 'key_here',
                        'sk-test', 'test-key', 'test_key', 'fake_', 'mock_'
                    ]
                    is_placeholder = any(p.lower() in str(api_key).lower() for p in placeholder_patterns)

                    if not is_placeholder:
                        if self.store_api_key(provider, api_name, api_key):
                            migrated += 1

        if migrated > 0:
            logger.info(f"已迁移 {migrated} 个 API Key 到安全存储")

        return migrated

    def clear_all(self):
        """清空所有存储的敏感数据"""
        self._data = {}
        self._modified = True
        self._save()
        logger.info("安全存储已清空")

    def is_dpapi_available(self) -> bool:
        """检查 DPAPI 是否可用"""
        return _CRYPT32_AVAILABLE


_secure_storage_instance: Optional[SecureStorage] = None


def get_secure_storage() -> SecureStorage:
    """获取安全存储单例"""
    global _secure_storage_instance
    if _secure_storage_instance is None:
        _secure_storage_instance = SecureStorage()
    return _secure_storage_instance


def store_api_key(provider: str, api_name: str, api_key: str) -> bool:
    """便捷函数：存储 API Key"""
    return get_secure_storage().store_api_key(provider, api_name, api_key)


def retrieve_api_key(provider: str, api_name: str) -> Optional[str]:
    """便捷函数：获取 API Key"""
    return get_secure_storage().retrieve_api_key(provider, api_name)


def delete_api_key(provider: str, api_name: str) -> bool:
    """便捷函数：删除 API Key"""
    return get_secure_storage().delete_api_key(provider, api_name)
