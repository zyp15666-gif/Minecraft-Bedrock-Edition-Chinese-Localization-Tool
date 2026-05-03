#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
api/translation_cache.py 单元测试
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import time
import tempfile
from pathlib import Path
from api.translation_cache import TranslationCache


class TestTranslationCache:
    def setup_method(self):
        self.cache = TranslationCache(max_size=100)

    def teardown_method(self):
        if self.cache:
            self.cache.close()

    def test_set_and_get(self):
        self.cache.set("hello", "你好")
        result = self.cache.get("hello")
        assert result == "你好"

    def test_get_nonexistent(self):
        result = self.cache.get("nonexistent_key")
        assert result is None

    def test_cache_overwrite(self):
        self.cache.set("hello", "你好")
        self.cache.set("hello", "您好")
        result = self.cache.get("hello")
        assert result == "您好"

    def test_max_size_eviction(self):
        cache = TranslationCache(max_size=3)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        cache.set("key4", "value4")
        assert cache.size() <= 3

    def test_stats(self):
        self.cache.set("hello", "你好")
        self.cache.get("hello")
        self.cache.get("nonexistent")
        stats = self.cache.get_stats()
        assert stats['hits'] >= 1
        assert stats['sets'] >= 1
        assert stats['size'] >= 1

    def test_clear(self):
        self.cache.set("hello", "你好")
        self.cache.clear()
        assert self.cache.size() == 0
        assert self.cache.get("hello") is None

    def test_contains(self):
        self.cache.set("hello", "你好")
        assert self.cache.contains("hello") is True
        assert self.cache.contains("nonexistent") is False

    def test_normalize_key(self):
        self.cache.set("  hello  ", "你好")
        result = self.cache.get("hello")
        assert result == "你好"


class TestTranslationCacheWithDB:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_cache.db")
        self.cache = TranslationCache(max_size=100, db_path=self.db_path)

    def teardown_method(self):
        if self.cache:
            self.cache.close()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_persistence(self):
        self.cache.set("hello", "你好")
        self.cache.close()
        new_cache = TranslationCache(max_size=100, db_path=self.db_path)
        result = new_cache.get("hello")
        assert result == "你好"
        new_cache.close()

    def test_async_writer_creates_thread(self):
        assert self.cache._writer_thread is not None
        assert self.cache._writer_thread.is_alive()

    def test_batch_write_queue(self):
        for i in range(10):
            self.cache.set(f"key_{i}", f"value_{i}")
        time.sleep(2)
        assert self.cache.size() >= 10

    def test_close_stops_writer(self):
        self.cache.set("hello", "你好")
        self.cache.close()
        assert not self.cache._writer_running

    def test_save_and_load_from_file(self, tmp_path):
        self.cache.set("hello", "你好")
        filepath = tmp_path / "cache_export.json"
        result = self.cache.save_to_file(str(filepath))
        assert result is True
        assert filepath.exists()

        new_cache = TranslationCache(max_size=100)
        load_result = new_cache.load_from_file(str(filepath))
        assert load_result is True
        assert new_cache.get("hello") == "你好"


class TestTranslationCacheEdgeCases:
    def test_empty_key(self):
        cache = TranslationCache(max_size=10)
        cache.set("", "empty_key_value")
        assert cache.get("") == "empty_key_value"

    def test_unicode_key(self):
        cache = TranslationCache(max_size=10)
        cache.set("键", "值")
        assert cache.get("键") == "值"

    def test_very_long_value(self):
        cache = TranslationCache(max_size=10)
        long_value = "x" * 10000
        cache.set("long", long_value)
        assert cache.get("long") == long_value

    def test_special_characters(self):
        cache = TranslationCache(max_size=10)
        special = "Hello §aWorld\n\t\r"
        cache.set("special", special)
        assert cache.get("special") == special

    def test_concurrent_access(self):
        import threading
        cache = TranslationCache(max_size=1000)
        errors = []

        def writer(n):
            try:
                for i in range(50):
                    cache.set(f"key_{n}_{i}", f"value_{n}_{i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert cache.size() <= 1000
