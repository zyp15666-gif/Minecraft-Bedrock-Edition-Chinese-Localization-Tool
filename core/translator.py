#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
翻译核心模块（仅使用多线程模式）
"""

import asyncio
import math
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional, Tuple

from tqdm import tqdm

from core.log_manager import get_logger
from core.utils import has_color_codes, is_lang_key_format

logger = get_logger(__name__)


class Translator:
    """翻译器"""

    _CACHED_IDENTIFIER_PATTERNS = None
    _CACHED_FORMAT_PATTERNS = None
    _CACHED_ENGLISH_RE = re.compile(r'[a-zA-Z]')
    _CACHED_CHINESE_RE = re.compile(r'[\u4e00-\u9fff]')

    @classmethod
    def _get_identifier_patterns(cls):
        """获取缓存的标识符正则模式"""
        if cls._CACHED_IDENTIFIER_PATTERNS is None:
            cls._CACHED_IDENTIFIER_PATTERNS = [
                re.compile(p) for p in cls._identifier_patterns()
            ]
        return cls._CACHED_IDENTIFIER_PATTERNS

    @classmethod
    def _get_format_patterns(cls):
        """获取缓存的格式正则模式"""
        if cls._CACHED_FORMAT_PATTERNS is None:
            cls._CACHED_FORMAT_PATTERNS = cls._compile_format_patterns()
        return cls._CACHED_FORMAT_PATTERNS

    def __init__(self, api_manager, config: Dict[str, Any]):
        """初始化翻译器

        Args:
            api_manager: API管理器实例
            config: 配置字典
        """
        self.api_manager = api_manager
        self.config = config
        self.use_multithreading = config.get(
            "basic", {}).get("use_multithreading", True)
        available_api_count = len(getattr(api_manager, 'available_apis', []))
        max_threads_per_api = config.get('basic', {}).get('max_threads_per_api', 3)
        self.max_workers_config = available_api_count * max_threads_per_api
        self.max_retries = config.get("basic", {}).get("max_retries", 2)
        self.batch_size = config.get("basic", {}).get(
            "batch_size", 100)
        self.batch_delay = config.get("rate_limit", {}).get(
            "default", 0.15)
        self._translate_lock = threading.Lock()
        self._local_api_trust_count = 0
        self._local_api_trust_threshold = config.get('basic', {}).get('local_trust_threshold', 20)
        self._local_api_consecutive_good = 0

    # ──────────── 统一日志与进度辅助方法 ────────────

    def _log_message(self, log_callback: Optional[Callable[[str], None]], message: str):
        """统一日志输出 — 有回调走回调，无回调走 print"""
        if log_callback:
            log_callback(message)
        else:
            print(message)

    def _report_progress(
        self,
        progress_callback: Optional[Callable],
        completed: int,
        total: int,
        start: float,
    ) -> None:
        """统一进度上报，中心化进度计算逻辑。

        Args:
            progress_callback: 进度回调函数
            completed: 已完成条目数
            total: 总条目数
            start: 开始时间戳
        """
        if not progress_callback:
            return
        progress = min(0.2 + (completed / total) * 0.8, 1.0) if total > 0 else 1.0
        elapsed_time = time.time() - start
        if completed > 0:
            avg_time = elapsed_time / completed
            remaining_items = total - completed
            estimated_remaining = int(avg_time * remaining_items)
        else:
            remaining_items = total
            estimated_remaining = 0
        progress_callback(progress, remaining_items, estimated_remaining)

    def _report_completion(self, progress_callback: Optional[Callable], total: int, start: float):
        """翻译完成时的进度与耗时输出"""
        if progress_callback:
            progress_callback(1.0, 0, 0)
        elapsed = time.time() - start
        if elapsed > 0:
            print(f"耗时: {elapsed:.2f} 秒 | 平均速度: {total/elapsed:.2f} 条/秒")
        else:
            print(f"耗时: {elapsed:.2f} 秒 | 平均速度: N/A")

    def _fix_escape_sequences(self, text: str) -> str:
        """修复文本中的转义序列"""
        if '\\n' in text:
            text = text.replace('\\n', '\n')
        if '\\t' in text:
            text = text.replace('\\t', '\t')
        return text

    def _check_term_match(self, text: str) -> Optional[str]:
        """检查术语匹配（原始和清洗两种方式）

        Args:
            text: 待检查文本

        Returns:
            匹配到的术语翻译，无匹配返回None
        """
        if not self.api_manager or not self.api_manager.term_service:
            return None

        term_translation = self.api_manager.term_service.get_translation_original(text)
        if term_translation:
            logger.debug(f"术语命中-原始: '{text[:30]}...' -> '{term_translation[:30]}...'")
            return term_translation

        term_translation = self.api_manager.term_service.get_translation_clean(text)
        if term_translation:
            logger.debug(f"术语命中-清洗: '{text[:30]}...' -> '{term_translation[:30]}...'")
            return term_translation

        return None

    def _translate_with_local_api(self, local_api, original_fixed, cloud_apis):
        """使用本地API翻译，质量不合格时降级到云端

        Args:
            local_api: 本地API配置
            original_fixed: 待翻译文本
            cloud_apis: 云端API列表

        Returns:
            翻译结果
        """
        if self._local_api_consecutive_good >= self._local_api_trust_threshold:
            try:
                translated = self.api_manager.translate_with_api(local_api, original_fixed)
            except Exception as e:
                logger.warning(f"本地API翻译失败: {str(e)[:50]}")
                translated = None
                self._local_api_consecutive_good = 0
            if translated:
                return translated
            return original_fixed

        try:
            translated = self.api_manager.translate_with_api(local_api, original_fixed)
        except Exception as e:
            logger.warning(f"本地API翻译失败: {str(e)[:50]}")
            translated = None

        if translated and self._is_poor_quality(original_fixed, translated):
            logger.info("[降级] 本地模型翻译质量不合格，启用云端多重验证")
            self._local_api_consecutive_good = 0
            if cloud_apis:
                translated = self.api_manager.multi_api_translate(original_fixed)
        elif translated:
            self._local_api_consecutive_good += 1
        return translated if translated else original_fixed

    def _translate_with_multi_api(self, original_fixed):
        """使用多重API验证翻译

        Args:
            original_fixed: 待翻译文本

        Returns:
            翻译结果
        """
        try:
            translated = self.api_manager.multi_api_translate(original_fixed)
        except Exception as e:
            logger.warning(f"多重验证翻译失败: {str(e)[:50]}")
            translated = None
        return translated if translated else original_fixed

    def _translate_with_single_api(self, original_fixed):
        """使用单一API翻译

        Args:
            original_fixed: 待翻译文本

        Returns:
            翻译结果
        """
        try:
            translated = self.api_manager.translate_text(original_fixed)
            return translated if translated else original_fixed
        except Exception as e:
            logger.warning(f"API翻译失败: {str(e)[:50]}")
            return original_fixed

    # ──────────── 单条翻译 ────────────

    def translate_single_item(self, key_original_tuple: tuple) -> tuple:
        key, original, retry_count, keys_set = key_original_tuple

        original_fixed = self._fix_escape_sequences(original)

        if original_fixed in keys_set and is_lang_key_format(original_fixed):
            return key, original_fixed

        term_translation = self._check_term_match(original_fixed)
        if term_translation:
            return key, term_translation

        available_apis = self.api_manager.get_available_apis()
        if not available_apis:
            return key, original_fixed

        local_apis = [api for api in available_apis if api.get('type') == 'local_ollama']
        cloud_apis = [api for api in available_apis if api.get('type') != 'local_ollama']

        use_multi = self.config.get('basic', {}).get('use_multi_api_validation', False)
        fallback_enabled = self.config.get('basic', {}).get('local_first_fallback', True)

        if local_apis and fallback_enabled:
            translated = self._translate_with_local_api(local_apis[0], original_fixed, cloud_apis)
            return key, translated
        elif use_multi and len(available_apis) >= 2:
            translated = self._translate_with_multi_api(original_fixed)
            return key, translated
        else:
            translated = self._translate_with_single_api(original_fixed)
            return key, translated

    # ──────────── 多线程翻译 ────────────

    def translate_dict_parallel(self, entries: Dict[str, str], progress_callback=None, log_callback=None) -> Dict[str, str]:
        """多线程翻译 - 支持分批处理避免API速率限制"""
        available_api_count = len(self.api_manager.get_available_apis())
        max_threads_per_api = self.config.get('basic', {}).get('max_threads_per_api', 3)
        max_workers = available_api_count * max_threads_per_api

        self._log_message(log_callback, "\n启动多线程翻译")
        self._log_message(log_callback, f"   线程数: {max_workers}")
        self._log_message(log_callback, f"   可用API: {available_api_count}")
        self._log_message(log_callback, f"   待翻译条目: {len(entries)}")
        self._log_message(log_callback, f"   批次大小: {self.batch_size}")
        self._log_message(log_callback, f"   批次间延迟: {self.batch_delay}秒")

        translated = {}
        start = time.time()
        total = len(entries)

        if progress_callback:
            progress_callback(0.0, total, 0)

        items = list(entries.items())
        num_batches = math.ceil(total / self.batch_size)
        self._log_message(log_callback, f"   总批次: {num_batches}")

        if progress_callback:
            progress_callback(0.1, total, 0)

        keys_set = set(entries.keys())
        update_interval = self.config.get("basic", {}).get("update_interval", 0.3)
        update_batch_size = self.config.get("basic", {}).get("update_batch_size", 10)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            if progress_callback:
                progress_callback(0.2, total, 0)

            for batch_idx in range(num_batches):
                batch_start = batch_idx * self.batch_size
                batch_end = min(batch_start + self.batch_size, total)
                batch_items = items[batch_start:batch_end]

                self._log_message(log_callback,
                    f"\n处理批次 {batch_idx + 1}/{num_batches} (条目 {batch_start + 1}-{batch_end})")

                failed_keys = self._process_single_batch(
                    executor, batch_items, keys_set, translated,
                    total, progress_callback, log_callback,
                    update_interval, update_batch_size, start
                )

                if failed_keys and log_callback:
                    log_callback(f"批次 {batch_idx + 1} 完成，失败 {len(failed_keys)} 条: {failed_keys[:5]}{'...' if len(failed_keys) > 5 else ''}")

                if batch_idx < num_batches - 1 and self.batch_delay > 0:
                    self._log_message(log_callback,
                        f"批次 {batch_idx + 1} 完成，等待 {self.batch_delay} 秒后继续下一批次...")
                    time.sleep(self.batch_delay)

        self._report_completion(progress_callback, len(entries), start)
        return translated

    def _process_single_batch(
        self, executor, batch_items, keys_set, translated,
        total, progress_callback, log_callback,
        update_interval, update_batch_size, start
    ) -> list:
        """处理单个批次的翻译任务"""
        tasks = [(key, value, self.max_retries, keys_set) for key, value in batch_items]
        future_to_key = {executor.submit(self.translate_single_item, task): task[0] for task in tasks}
        failed_keys = []
        last_update_time = time.time()

        batch_iterator = as_completed(future_to_key)
        if not log_callback:
            batch_iterator = tqdm(batch_iterator, total=len(batch_items),
                                  desc=f"批次 {0}", unit="条", ncols=80)

        for future in batch_iterator:
            key = future_to_key[future]
            try:
                result_key, result_text = future.result()
                with self._translate_lock:
                    translated[result_key] = result_text
            except Exception as e:
                error_msg = f"翻译失败 [{key}]: {str(e)}"
                self._log_message(log_callback, error_msg)
                original_value = None
                for item_key, item_value in batch_items:
                    if item_key == key:
                        original_value = item_value
                        break
                if original_value is not None:
                    with self._translate_lock:
                        translated[key] = original_value
                failed_keys.append(key)

            if not log_callback and hasattr(batch_iterator, 'update'):
                batch_iterator.update(1)

            # 进度上报
            completed = len(translated)
            if progress_callback:
                current_time = time.time()
                is_last_item = (completed == total)
                if is_last_item or completed % update_batch_size == 0 or current_time - last_update_time >= update_interval:
                    self._report_progress(progress_callback, completed, total, start)
                    last_update_time = current_time

        del future_to_key
        del tasks
        return failed_keys

    # ──────────── 单线程翻译 ────────────

    def translate_dict_single(self, entries: Dict[str, str], progress_callback=None, log_callback=None) -> Dict[str, str]:
        """单线程翻译 - 支持分批处理避免API速率限制"""
        self._log_message(log_callback, "\n开始单线程翻译")
        self._log_message(log_callback, f"   可用API: {len(self.api_manager.get_available_apis())}")
        self._log_message(log_callback, f"   待翻译条目: {len(entries)}")
        self._log_message(log_callback, f"   批次大小: {self.batch_size}")
        self._log_message(log_callback, f"   批次间延迟: {self.batch_delay}秒")

        translated = {}
        start = time.time()
        completed = 0
        total = len(entries)

        num_batches = math.ceil(total / self.batch_size)
        self._log_message(log_callback, f"   总批次: {num_batches}")

        if progress_callback:
            progress_callback(0.0, total, 0)
            progress_callback(0.2, total, 0)

        items = list(entries.items())
        keys_set = set(entries.keys())
        use_tqdm = not log_callback  # GUI模式不用tqdm

        for batch_idx in range(num_batches):
            batch_start = batch_idx * self.batch_size
            batch_end = min(batch_start + self.batch_size, total)
            batch_items = items[batch_start:batch_end]

            self._log_message(log_callback,
                f"\n处理批次 {batch_idx + 1}/{num_batches} (条目 {batch_start + 1}-{batch_end})")

            iterator = batch_items
            if use_tqdm:
                iterator = tqdm(batch_items, desc=f"批次 {batch_idx + 1}", unit="条", ncols=80)

            for key, original in iterator:
                has_color_code = has_color_codes(original)
                translated_text = original
                if not has_color_code and original in keys_set and is_lang_key_format(original):
                    pass  # 语言键格式，跳过翻译
                else:
                    for attempt in range(self.max_retries):
                        translated_text = self.api_manager.translate_text(original)
                        if translated_text != original:
                            break

                translated[key] = translated_text
                completed += 1

                # 进度上报
                if progress_callback:
                    self._report_progress(progress_callback, completed, total, start)

            # 批次完成后延迟
            if batch_idx < num_batches - 1 and self.batch_delay > 0:
                self._log_message(log_callback,
                    f"批次 {batch_idx + 1} 完成，等待 {self.batch_delay} 秒后继续下一批次...")
                time.sleep(self.batch_delay)

        self._report_completion(progress_callback, len(entries), start)
        return translated

    # ──────────── 入口方法 ────────────

    def translate_entries(self, entries: Dict[str, str], progress_callback=None, log_callback=None) -> Dict[str, str]:
        """根据配置选择翻译模式"""
        if not entries:
            return {}

        len(self.api_manager.available_apis)
        entry_count = len(entries)

        # 根据条目数量动态选择翻译模式
        if self.use_multithreading and entry_count >= 20:
            self._log_message(log_callback, f"\n📊 检测到 {entry_count} 条条目，使用多线程翻译")
            translated = self.translate_dict_parallel(entries, progress_callback, log_callback)
        else:
            self._log_message(log_callback, f"\n📊 检测到 {entry_count} 条条目，使用单线程翻译")
            translated = self.translate_dict_single(entries, progress_callback, log_callback)

        # 翻译完成后进行质量检查
        if log_callback and translated:
            quality_report = self._check_translation_quality(entries, translated, log_callback)
            if not quality_report.get('quality_passed', True):
                log_callback(f"⚠️ 翻译质量检测未通过：完整性 {quality_report['completeness']:.1f}%, "
                            f"标识符保护 {quality_report['identifier_protection']:.1f}%, "
                            f"格式保留 {quality_report['format_preservation']:.1f}%")
                if quality_report.get('problematic_entries'):
                    log_callback(f"  问题条目: {quality_report['problematic_entries'][:5]}{'...' if len(quality_report['problematic_entries']) > 5 else ''}")
            else:
                log_callback(f"✅ 翻译质量检测通过 (总分: {quality_report['overall_score']:.1f})")

        return translated

    def translate_entries_batch(self, entries: Dict[str, str], progress_callback=None, log_callback=None) -> Dict[str, str]:
        """使用传统的多线程翻译方法"""
        if not entries:
            return {}

        self._log_message(log_callback, "\n🚀 启动传统多线程翻译")
        self._log_message(log_callback, f"   待翻译条目: {len(entries)}")

        translated = self.translate_dict_parallel(entries, progress_callback, log_callback)
        return translated

    async def _translate_single_async(self, key: str, original: str, keys_set: set) -> Tuple[str, str]:
        """异步翻译单个条目

        Args:
            key: 条目键
            original: 原始文本
            keys_set: 键集合（用于语言键格式检测）

        Returns:
            (key, translated_text) 元组
        """
        original_fixed = self._fix_escape_sequences(original)

        if original_fixed in keys_set and is_lang_key_format(original_fixed):
            return key, original_fixed

        term_translation = self._check_term_match(original_fixed)
        if term_translation:
            return key, term_translation

        available_apis = self.api_manager.get_available_apis()
        if not available_apis:
            return key, original_fixed

        api_config = available_apis[0]
        try:
            translated_text = await self.api_manager.async_api_client.translate(
                api_config, original_fixed
            )
            return key, translated_text if translated_text else original_fixed
        except Exception as e:
            logger.error(f"异步翻译失败 [{key}]: {e}")
            return key, original_fixed

    async def translate_entries_async(self, entries: Dict[str, str], progress_callback=None, log_callback=None) -> Dict[str, str]:
        """异步批量翻译（使用asyncio.gather替代ThreadPoolExecutor）

        性能优势：
        - 单线程处理多个并发请求
        - 避免线程池阻塞
        - 降低内存占用
        - 提高吞吐量

        Args:
            entries: 待翻译的键值对字典
            progress_callback: 进度回调函数
            log_callback: 日志回调函数

        Returns:
            翻译后的键值对字典
        """
        if not entries:
            return {}

        if not hasattr(self.api_manager, 'async_api_client') or not self.api_manager.async_api_client:
            self._log_message(log_callback, "⚠️ 异步API客户端不可用，回退到同步模式")
            return self.translate_entries(entries, progress_callback, log_callback)

        self._log_message(log_callback, "\n🚀 启动异步并发翻译")
        self._log_message(log_callback, f"   待翻译条目: {len(entries)}")

        start = time.time()
        total = len(entries)
        translated = {}
        keys_set = set(entries.keys())

        if progress_callback:
            progress_callback(0.0, total, 0)

        tasks = [self._translate_single_async(key, value, keys_set) for key, value in entries.items()]

        completed = 0
        update_interval = self.config.get("basic", {}).get("update_interval", 0.3)
        last_update_time = time.time()

        for coro in asyncio.as_completed(tasks):
            try:
                result_key, result_text = await coro
                translated[result_key] = result_text
                completed += 1

                if progress_callback:
                    current_time = time.time()
                    if completed % 10 == 0 or current_time - last_update_time >= update_interval:
                        self._report_progress(progress_callback, completed, total, start)
                        last_update_time = current_time
            except Exception as e:
                logger.error(f"异步任务执行失败: {e}")

        self._report_completion(progress_callback, len(entries), start)
        return translated

    # ──────────── 质量相关 ────────────

    def _is_poor_quality(self, original: str, translated: str) -> bool:
        """判断翻译结果是否质量不合格（需要降级）。

        使用缓存的预编译正则，避免每次调用时重新编译。
        """
        if not translated:
            return True

        total_chars = len(translated)
        if total_chars == 0:
            return True

        english_chars = len(self._CACHED_ENGLISH_RE.findall(translated))
        english_ratio = english_chars / total_chars

        if english_ratio > 0.8:
            return True

        chinese_chars = len(self._CACHED_CHINESE_RE.findall(translated))
        if chinese_chars == 0 and english_ratio > 0.3:
            return True

        return False

    def _check_translation_quality(self, original_entries: Dict[str, str],
                                   translated_entries: Dict[str, str],
                                   log_callback=None) -> Dict[str, Any]:
        """
        检查批量翻译结果的质量

        返回质量报告：
        {
            'overall_score': float,
            'completeness': float,
            'identifier_protection': float,
            'format_preservation': float,
            'problematic_entries': List[str],
            'quality_passed': bool
        }
        """
        if not translated_entries:
            return {
                'overall_score': 0,
                'completeness': 0,
                'identifier_protection': 0,
                'format_preservation': 0,
                'problematic_entries': list(original_entries.keys()),
                'quality_passed': False
            }

        total = len(original_entries)
        translated_count = len(translated_entries)

        # 各维度评分
        completeness = self._calc_completeness(translated_count, total)
        identifier_protection = self._calc_identifier_protection(original_entries, translated_entries)
        format_preservation = self._calc_format_preservation(original_entries, translated_entries)
        problematic_entries = self._collect_problematic_entries(original_entries, translated_entries)

        # 综合评分（加权平均）
        overall_score = (completeness * 0.4 +
                        identifier_protection * 0.3 +
                        format_preservation * 0.3)

        quality_passed = (overall_score >= 85 and
                         completeness >= 90 and
                         identifier_protection >= 95)

        return {
            'overall_score': overall_score,
            'completeness': completeness,
            'identifier_protection': identifier_protection,
            'format_preservation': format_preservation,
            'problematic_entries': problematic_entries,
            'quality_passed': quality_passed
        }

    # ──────────── 质量检查子方法 ────────────

    @staticmethod
    def _calc_completeness(translated_count: int, total: int) -> float:
        """计算翻译完整性百分比"""
        return (translated_count / total) * 100 if total > 0 else 0

    @staticmethod
    def _identifier_patterns():
        """返回 Minecraft 技术标识符的模式列表"""
        return [
            r'^[a-z]+\.[a-z_]+:[a-z_\.]+$',  # entity.minecraft:zombie
            r'^[a-z]+\.[a-z_]+\.[a-z_]+$',    # item.iron_sword.name
            r'^/[a-z]+',                       # /tp, /give 等指令
            r'^[a-z_]+:[a-z_]+$',              # minecraft:stone
        ]

    @staticmethod
    def _format_patterns():
        """返回需要保留的格式代码模式"""
        return [r'§[0-9a-fk-or]', r'%[sd]', r'%\d+\$[sd]', r'\{[^}]+\}']

    @staticmethod
    def _compile_format_patterns():
        """预编译格式模式正则表达式，提高匹配效率"""
        return [re.compile(p) for p in Translator._format_patterns()]

    @staticmethod
    def _calc_identifier_protection(
        original_entries: Dict[str, str],
        translated_entries: Dict[str, str],
    ) -> float:
        """计算标识符保护评分（技术标识符是否被误翻译）"""
        compiled_patterns = Translator._get_identifier_patterns()
        protected_count = 0
        violated_count = 0

        for key, original in original_entries.items():
            if key in translated_entries:
                translated = translated_entries[key]
                is_identifier = any(p.match(original) for p in compiled_patterns)
                if is_identifier:
                    protected_count += 1
                    if translated != original:
                        violated_count += 1

        return ((protected_count - violated_count) / protected_count * 100) if protected_count > 0 else 100

    @staticmethod
    def _calc_format_preservation(
        original_entries: Dict[str, str],
        translated_entries: Dict[str, str],
    ) -> float:
        """计算格式保留评分（颜色代码、占位符是否保留）

        使用缓存的预编译正则表达式和集合运算优化匹配性能。
        """
        compiled_patterns = Translator._get_format_patterns()
        format_preserved = 0
        format_total = 0

        for key, original in original_entries.items():
            if key in translated_entries:
                translated = translated_entries[key]
                for compiled_pattern in compiled_patterns:
                    original_formats = set(compiled_pattern.findall(original))
                    if original_formats:
                        format_total += len(original_formats)
                        translated_formats = set(compiled_pattern.findall(translated))
                        format_preserved += len(original_formats & translated_formats)

        return (format_preserved / format_total * 100) if format_total > 0 else 100

    @staticmethod
    def _collect_problematic_entries(
        original_entries: Dict[str, str],
        translated_entries: Dict[str, str],
    ) -> List[str]:
        """收集有质量问题的条目 key 列表

        使用缓存的预编译正则表达式优化匹配性能。
        """
        identifier_patterns = Translator._get_identifier_patterns()
        compiled_format_patterns = Translator._get_format_patterns()
        problematic = set()

        for key, original in original_entries.items():
            if key not in translated_entries:
                problematic.add(key)
                continue

            translated = translated_entries[key]

            is_identifier = any(p.match(original) for p in identifier_patterns)
            if is_identifier and translated != original:
                problematic.add(key)
                continue

            for compiled_pattern in compiled_format_patterns:
                original_formats = set(compiled_pattern.findall(original))
                if original_formats:
                    translated_formats = set(compiled_pattern.findall(translated))
                    if not original_formats.issubset(translated_formats):
                        problematic.add(key)
                        break

        return list(problematic)
