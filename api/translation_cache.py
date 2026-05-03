#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
翻译缓存管理 - 负责翻译结果的缓存读写
优化版：惰性加载 + LRU缓存 + SQLite持久化

优化点：
1. 惰性加载：启动时不预加载，仅记录条目数
2. LRU缓存：使用cachetools.LRUCache管理内存缓存（最大2000条）
3. SQLite持久化：长期存储，重启后不丢失
4. 异步批量写入：避免阻塞翻译流程
"""

import threading
import time
import os
import sqlite3
import queue
from typing import Optional, Dict, Any, List, Tuple
from core.log_manager import get_logger
from core.utils import normalize_text_for_cache

logger = get_logger(__name__)

try:
    from cachetools import LRUCache
    CACHETOOLS_AVAILABLE = True
except ImportError:
    CACHETOOLS_AVAILABLE = False
    logger.warning("cachetools未安装，使用内置LRU实现。建议运行: pip install cachetools")


class TranslationCache:
    """翻译缓存管理 - 惰性加载 + LRU缓存 + SQLite持久化"""

    def __init__(self, max_size: int = 2000, db_path: Optional[str] = None):
        """初始化翻译缓存

        Args:
            max_size: 内存缓存最大容量，默认为2000（惰性加载优化）
            db_path: SQLite数据库文件路径，为None时使用内存缓存
        """
        if CACHETOOLS_AVAILABLE:
            self._cache = LRUCache(maxsize=max_size)
        else:
            self._cache = {}
            self._access_order = []
        
        self._lock = threading.RLock()
        self._max_size = max_size
        self._db_path = db_path
        self._db_connection = None
        
        self._total_db_count = 0

        self._hits = 0
        self._misses = 0
        self._sets = 0

        self._write_queue = queue.Queue()
        self._batch_size = 50
        self._flush_interval = 1.0
        self._writer_running = True
        self._writer_thread = None

        if self._db_path:
            self._init_database()
            self._count_database_records()
            self._start_async_writer()

    def _init_database(self):
        """初始化SQLite数据库（启用WAL模式提升并发性能）"""
        try:
            db_dir = os.path.dirname(os.path.abspath(self._db_path))
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)

            if not self._check_database_integrity():
                self._handle_corrupted_database()

            self._db_connection = sqlite3.connect(
                self._db_path, 
                check_same_thread=False,
                timeout=10
            )
            self._db_connection.execute("PRAGMA journal_mode=WAL")
            self._db_connection.execute("PRAGMA synchronous=NORMAL")
            self._db_connection.execute("PRAGMA cache_size=-64000")
            self._db_connection.execute("PRAGMA temp_store=MEMORY")

            cursor = self._db_connection.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS translations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT NOT NULL UNIQUE,
                    value TEXT NOT NULL,
                    access_count INTEGER DEFAULT 0,
                    timestamp REAL DEFAULT 0,
                    created_at REAL DEFAULT 0
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_translations_key ON translations(key)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_translations_timestamp ON translations(timestamp)')
            self._db_connection.commit()
            logger.info(f"SQLite数据库已初始化: {self._db_path}")
        except Exception as e:
            logger.error(f"初始化数据库失败: {e}")
            self._db_connection = None

    def _check_database_integrity(self) -> bool:
        """检查数据库完整性

        Returns:
            True 表示数据库完好，False 表示损坏
        """
        if not os.path.exists(self._db_path):
            return True

        try:
            conn = sqlite3.connect(self._db_path, timeout=5)
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            conn.close()

            if result and result[0] == 'ok':
                logger.debug("数据库完整性检查通过")
                return True
            else:
                logger.warning(f"数据库完整性检查失败: {result}")
                return False

        except sqlite3.DatabaseError as e:
            logger.error(f"数据库损坏: {e}")
            return False
        except Exception as e:
            logger.error(f"数据库检查异常: {e}")
            return False

    def _handle_corrupted_database(self):
        """处理损坏的数据库"""
        import shutil
        from datetime import datetime

        try:
            if os.path.exists(self._db_path):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"{self._db_path}.corrupted_{timestamp}"
                shutil.copy2(self._db_path, backup_path)
                logger.warning(f"损坏的数据库已备份到: {backup_path}")

                for ext in ['-wal', '-shm']:
                    wal_path = self._db_path + ext
                    if os.path.exists(wal_path):
                        os.remove(wal_path)

                os.remove(self._db_path)
                logger.info("已删除损坏的数据库，将创建新数据库")

        except Exception as e:
            logger.error(f"处理损坏数据库失败: {e}")

    def _count_database_records(self):
        """统计数据库中的缓存条目数（惰性加载：不预加载数据）"""
        if not self._db_connection:
            return
            
        try:
            cursor = self._db_connection.cursor()
            cursor.execute('SELECT COUNT(*) FROM translations')
            count = cursor.fetchone()[0]
            self._total_db_count = count
            logger.info(f"数据库中共有 {count} 条缓存记录（惰性加载模式，未预加载到内存）")
        except Exception as e:
            logger.error(f"统计数据库记录失败: {e}")

    def _save_to_database(self, key: str, value: str, access_count: int = 0, timestamp: float = 0):
        """保存缓存到数据库（通过写入队列异步执行）"""
        if not self._db_connection:
            return
        self._write_queue.put((key, value, access_count, timestamp))

    def _start_async_writer(self):
        """启动异步写入线程"""
        if self._writer_thread is None or not self._writer_thread.is_alive():
            self._writer_running = True
            self._writer_thread = threading.Thread(target=self._async_write_worker, daemon=True)
            self._writer_thread.start()
            logger.debug("异步写入线程已启动")

    def _async_write_worker(self):
        """异步写入工作线程，批量处理写入队列"""
        batch = []
        last_flush_time = time.time()

        while self._writer_running:
            try:
                try:
                    item = self._write_queue.get(timeout=0.1)
                    batch.append(item)

                    should_flush = (
                        len(batch) >= self._batch_size or
                        (batch and time.time() - last_flush_time >= self._flush_interval)
                    )

                    if should_flush:
                        self._batch_write(batch)
                        batch = []
                        last_flush_time = time.time()
                except queue.Empty:
                    if batch and time.time() - last_flush_time >= self._flush_interval:
                        self._batch_write(batch)
                        batch = []
                        last_flush_time = time.time()
            except Exception as e:
                logger.error(f"异步写入线程异常: {e}")

        if batch:
            self._batch_write(batch)

    def _batch_write(self, batch: List[Tuple[str, str, int, float]]):
        """批量写入数据库"""
        if not self._db_connection or not batch:
            return
        try:
            cursor = self._db_connection.cursor()
            cursor.executemany('''
                INSERT OR REPLACE INTO translations
                (key, value, access_count, timestamp, created_at)
                VALUES (?, ?, ?, ?, COALESCE((SELECT created_at FROM translations WHERE key=?), ?))
            ''', [(key, value, access_count, timestamp, key, time.time()) for key, value, access_count, timestamp in batch])
            self._db_connection.commit()
            logger.debug(f"批量写入 {len(batch)} 条记录到数据库")
        except Exception as e:
            logger.error(f"批量写入数据库失败: {e}")

    def _delete_from_database(self, key: str):
        """从数据库删除缓存"""
        if not self._db_connection:
            return
            
        try:
            cursor = self._db_connection.cursor()
            cursor.execute('DELETE FROM translations WHERE key=?', (key,))
            self._db_connection.commit()
        except Exception as e:
            logger.error(f"从数据库删除失败: {e}")

    def _safe_db_write(self, key: str, value: str, access_count: int = 0, timestamp: float = 0):
        """线程安全的数据库写入（带异常处理）"""
        try:
            self._save_to_database(key, value, access_count, timestamp)
        except Exception as e:
            logger.error(f"异步数据库写入失败 [{key[:50]}...]: {e}")

    def get(self, key: str) -> Optional[str]:
        """获取缓存（惰性加载：先查LRU，未命中则查SQLite）

        Args:
            key: 缓存键（原文）

        Returns:
            缓存的翻译结果，如果不存在则返回None
        """
        normalized_key = normalize_text_for_cache(key)
        
        with self._lock:
            if CACHETOOLS_AVAILABLE:
                if normalized_key in self._cache:
                    self._hits += 1
                    value = self._cache[normalized_key]
                    logger.debug(f"LRU缓存命中: {normalized_key[:50]}...")
                    return value
            else:
                if normalized_key in self._cache:
                    if normalized_key in self._access_order:
                        self._access_order.remove(normalized_key)
                    self._access_order.append(normalized_key)
                    self._hits += 1
                    value = self._cache[normalized_key]
                    logger.debug(f"内存缓存命中: {normalized_key[:50]}...")
                    return value
            
            if self._db_connection:
                try:
                    cursor = self._db_connection.cursor()
                    cursor.execute('SELECT value, access_count, timestamp FROM translations WHERE key=?', (normalized_key,))
                    row = cursor.fetchone()
                    if row:
                        value, access_count, timestamp = row
                        
                        if CACHETOOLS_AVAILABLE:
                            self._cache[normalized_key] = value
                        else:
                            self._cache[normalized_key] = value
                            if normalized_key in self._access_order:
                                self._access_order.remove(normalized_key)
                            self._access_order.append(normalized_key)
                        
                        self._hits += 1

                        self._safe_db_write(normalized_key, value, access_count + 1, time.time())

                        logger.debug(f"数据库命中并加载到LRU: {normalized_key[:50]}...")
                        return value
                except Exception as e:
                    logger.error(f"从数据库读取失败: {e}")
            
            self._misses += 1
            logger.debug(f"缓存未命中: {normalized_key[:50]}...")
            return None

    def set(self, key: str, value: str):
        """设置缓存

        Args:
            key: 缓存键（原文）
            value: 缓存值（翻译结果）
        """
        normalized_key = normalize_text_for_cache(key)
        
        with self._lock:
            if CACHETOOLS_AVAILABLE:
                self._cache[normalized_key] = value
            else:
                if len(self._cache) >= self._max_size and normalized_key not in self._cache:
                    self._smart_evict()
                
                self._cache[normalized_key] = value
                if normalized_key in self._access_order:
                    self._access_order.remove(normalized_key)
                self._access_order.append(normalized_key)
            
            self._sets += 1

            if self._db_connection:
                self._safe_db_write(normalized_key, value, 0, time.time())

            logger.debug(f"缓存设置: {normalized_key[:50]}... -> {value[:50]}...")

    def _smart_evict(self):
        """智能清理缓存：移除访问次数最低且最久未使用的项（仅用于内置LRU）"""
        if CACHETOOLS_AVAILABLE:
            return
        
        with self._lock:
            if not self._cache:
                return

            min_access_count = float('inf')
            candidates = []

            for key in self._cache:
                access_count = 0
                if access_count < min_access_count:
                    min_access_count = access_count
                    candidates = [key]
                elif access_count == min_access_count:
                    candidates.append(key)

            if len(candidates) == 1:
                evict_key = candidates[0]
            else:
                seen = set(candidates)
                evict_key = candidates[0]
                for key in reversed(self._access_order):
                    if key in seen:
                        evict_key = key
                        break

            if evict_key in self._access_order:
                self._access_order.remove(evict_key)
            if evict_key in self._cache:
                del self._cache[evict_key]
                logger.debug(f"智能清理缓存: 移除键 '{evict_key[:50]}...'")

    def clear(self):
        """清空缓存"""
        with self._lock:
            if CACHETOOLS_AVAILABLE:
                self._cache.clear()
            else:
                self._cache.clear()
                self._access_order.clear()
            
            if self._db_connection:
                try:
                    cursor = self._db_connection.cursor()
                    cursor.execute('DELETE FROM translations')
                    self._db_connection.commit()
                    self._total_db_count = 0
                except Exception as e:
                    logger.error(f"清空数据库失败: {e}")
            
            logger.info("缓存已清空")

    def size(self) -> int:
        """获取内存缓存大小"""
        with self._lock:
            return len(self._cache)

    def total_size(self) -> int:
        """获取总缓存大小（内存 + 数据库）"""
        with self._lock:
            return self._total_db_count if self._db_connection else len(self._cache)

    def contains(self, key: str) -> bool:
        """检查缓存是否包含指定键"""
        normalized_key = normalize_text_for_cache(key)
        with self._lock:
            if normalized_key in self._cache:
                return True
            
            if self._db_connection:
                try:
                    cursor = self._db_connection.cursor()
                    cursor.execute('SELECT 1 FROM translations WHERE key=?', (normalized_key,))
                    return cursor.fetchone() is not None
                except Exception as e:
                    logger.error(f"检查数据库失败: {e}")
        
        return False

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'memory_cache_size': len(self._cache),
                'max_size': self._max_size,
                'db_cache_size': self._total_db_count,
                'hits': self._hits,
                'misses': self._misses,
                'sets': self._sets,
                'hit_rate': f"{hit_rate:.2f}%",
                'using_cachetools': CACHETOOLS_AVAILABLE
            }

    def close(self):
        """关闭缓存（停止异步写入线程）"""
        self._writer_running = False
        if self._writer_thread and self._writer_thread.is_alive():
            self._writer_thread.join(timeout=2.0)
        
        if self._db_connection:
            try:
                self._db_connection.close()
                logger.info("数据库连接已关闭")
            except Exception as e:
                logger.error(f"关闭数据库连接失败: {e}")

    def __del__(self):
        """析构函数：确保资源正确释放"""
        self.close()
