#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
翻译质量检查模块

提供翻译质量检查功能，包括：
1. AI提示信息检测
2. 长度比例检查
3. 颜色代码保留检查
4. 占位符保留检查
5. 英文比例检查
6. 未处理占位符检查

重构自 api_manager.py 中的 _check_translation_quality 方法
"""

import re
import threading
from typing import Dict, List, Tuple

from core.log_manager import get_logger

logger = get_logger(__name__)


class TranslationQualityChecker:
    """翻译质量检查器"""

    def __init__(self, term_service=None, cache_enabled: bool = True, cache_max_size: int = 1000,
                 min_length_ratio: float = 0.15, max_length_ratio: float = 3.0,
                 english_max_ratio: float = 0.3):
        """
        初始化翻译质量检查器

        Args:
            term_service: 术语服务实例（可选），用于术语一致性检查
            cache_enabled: 是否启用质量检查结果缓存，默认启用
            cache_max_size: 质量检查缓存最大大小，默认1000
            min_length_ratio: 翻译结果最小长度比例，默认0.15
            max_length_ratio: 翻译结果最大长度比例，默认3.0
            english_max_ratio: 翻译结果最大英文比例，默认0.3
        """
        self.term_service = term_service
        self.cache_enabled = cache_enabled
        self.cache_max_size = cache_max_size

        # 质量阈值配置
        self.min_length_ratio = min_length_ratio
        self.max_length_ratio = max_length_ratio
        self.english_max_ratio = english_max_ratio

        # 质量检查结果缓存 {(original, translated): bool}
        self._quality_cache = {}
        self._quality_cache_keys = []  # 用于实现LRU缓存
        self._cache_lock = threading.Lock()

        # AI提示信息列表（分级管理，降低误报率）
        self.ai_prompts_critical = [
            "请提供", "无法进行翻译", "没有提供", "空消息", "空白的消息",
            "Please provide", "cannot translate", "no text", "empty message",
        ]
        self.ai_prompts_warning = [
            "看起来您", "如果您需要", "具体文本", "英文文本", "进行汉化",
            "很抱歉", "不足以", "只提供了一个", "破折号", "句号", "感叹号",
            "looks like", "If you need", "specific text", "English text",
            "I'm sorry", "not enough", "only provided", "dash", "period", "exclamation mark",
        ]
        self.ai_prompts_context = [
            "在 Minecraft 中", "通常用于", "以下几种情况", "命令提示", "游戏内功能",
            "对应的中文翻译", "请注意", "具体含义", "根据上下文", "有所不同",
            "in Minecraft", "usually used for", "following cases", "command prompt",
            "in-game function", "corresponding Chinese translation", "Please note",
            "specific meaning", "depending on context", "may vary"
        ]

        # 白名单 - 游戏内容中可能正常出现的短语
        # 格式: key: 单个字符串(直接匹配) 或 列表(任一匹配即返回True)
        self.ai_prompts_whitelist = {
            "以下": "以下",
            "以上": "以上",
            "请注意": "请注意",
            "具体含义": "具体含义",
            "根据上下文": "根据上下文",
            "command": "command",
            "prompt": "prompt",
            "chat": "chat",
            "in-game": "in-game",
            "games": "games",
            "block": "block",
            "item": "item",
            "entity": "entity",
            "player": "player",
            "gameplay": "gameplay",
            "chat message": "chat message",
            "game chat": "game chat",
            "请提供": ["请提供物品名称", "请提供坐标", "请提供名称"],
            "Minecraft": ["Minecraft", "我的世界"],
        }

        # 未处理占位符模式
        self.placeholder_patterns = [
            r'\[术语_\d+\]',  # [术语_0]
            r'\[TERM_\d+\]',  # [TERM_0]
            r'\[\[TERM_\d+\]\]',  # [[TERM_0]]
            r'\[\[术语_\d+\]\]',  # [[术语_0]]
        ]

    def check_quality(self, original: str, translated: str, detailed_report: bool = False) -> bool:
        """
        检查翻译质量

        Args:
            original: 原文
            translated: 翻译结果
            detailed_report: 是否返回详细报告

        Returns:
            bool: 翻译质量是否合格（如果detailed_report=True，返回元组(bool, Dict)）
        """
        # 检查缓存（如果启用）
        if self.cache_enabled and not detailed_report:
            cache_key = (original, translated)
            with self._cache_lock:
                if cache_key in self._quality_cache:
                    # 更新缓存访问顺序（LRU）
                    self._quality_cache_keys.remove(cache_key)
                    self._quality_cache_keys.append(cache_key)
                    return self._quality_cache[cache_key]

        issues = []

        # 1. 检查AI提示信息
        if self._has_ai_prompts(translated):
            issues.append("包含AI提示信息")

        # 2. 检查长度比例
        length_ok, length_msg = self._check_length_ratio(original, translated)
        if not length_ok:
            issues.append(length_msg)

        # 3. 检查颜色代码保留
        color_ok, color_msg = self._check_color_codes(original, translated)
        if not color_ok:
            issues.append(color_msg)

        # 4. 检查占位符保留
        placeholder_ok, placeholder_msg = self._check_placeholders(
            original, translated)
        if not placeholder_ok:
            issues.append(placeholder_msg)

        # 5. 检查英文比例
        english_ok, english_msg = self._check_english_ratio(
            original, translated)
        if not english_ok:
            issues.append(english_msg)

        # 6. 检查未处理占位符
        unprocessed_ok, unprocessed_msg = self._check_unprocessed_placeholders(
            translated)
        if not unprocessed_ok:
            issues.append(unprocessed_msg)

        # 7. 检查术语一致性（如果有术语服务）
        if self.term_service:
            term_ok, term_msg = self._check_term_consistency(
                original, translated)
            if not term_ok:
                issues.append(term_msg)

        quality_ok = len(issues) == 0

        # 存储到缓存（如果启用且不是详细报告）
        if self.cache_enabled and not detailed_report:
            self._store_in_cache(original, translated, quality_ok)

        if detailed_report:
            report = {
                'quality_ok': quality_ok,
                'issues': issues,
                'original_length': len(original),
                'translated_length': len(translated),
                'length_ratio': len(translated) / len(original) if len(original) > 0 else 0,
                'original_color_codes': len(re.findall(r'§[0-9a-fklmnor]', original)),
                'translated_color_codes': len(re.findall(r'§[0-9a-fklmnor]', translated)),
                'original_placeholders': len(re.findall(r'%[0-9]*[sd]', original)),
                'translated_placeholders': len(re.findall(r'%[0-9]*[sd]', translated)),
            }
            return quality_ok, report
        else:
            return quality_ok

    def _has_ai_prompts(self, translated: str) -> bool:
        """检查是否包含AI提示信息（分级判断，降低误报率）

        Returns:
            True如果检测到明确AI提示（critical级别）
        """
        translated.lower()

        for prompt in self.ai_prompts_critical:
            if prompt in translated:
                if not self._is_in_whitelist(prompt, translated):
                    logger.warning(f"[翻译质量检查] 检测到 AI 提示信息（critical）：'{prompt}'")
                    return True

        for prompt in self.ai_prompts_warning:
            if prompt in translated:
                if not self._is_in_whitelist(prompt, translated):
                    logger.warning(f"[翻译质量检查] 检测到 AI 提示信息（warning）：'{prompt}'")
                    return True

        return False

    def _is_in_whitelist(self, prompt: str, translated: str) -> bool:
        """检查AI提示是否在白名单中（降低误报率）

        Args:
            prompt: 检测到的AI提示词
            translated: 完整翻译文本

        Returns:
            True如果在白名单中
        """
        translated_lower = translated.lower()

        for whitelist_key, whitelist_values in self.ai_prompts_whitelist.items():
            if isinstance(whitelist_values, list):
                if whitelist_key in prompt or any(val in translated for val in whitelist_values):
                    return True
            elif whitelist_values in translated_lower:
                return True

        return False

    def _check_length_ratio(self, original: str, translated: str) -> Tuple[bool, str]:
        """检查翻译结果长度比例"""
        min_ratio = self.min_length_ratio
        max_ratio = self.max_length_ratio

        # 对于超短文本（<=5字符），使用更宽松的检查
        if len(original) <= 5:
            min_ratio = 0.1  # 允许更短的比例

        ratio = len(translated) / len(original) if len(original) > 0 else 0

        # 检查基本长度比例
        if len(translated) < len(original) * min_ratio or len(translated) > len(original) * max_ratio:
            # 尝试使用中文分词进行更智能的判断
            try:
                import jieba
                # 分词后计算词汇数量
                original_words = len(list(jieba.cut(original)))
                translated_words = len(list(jieba.cut(translated)))

                # 对于中文翻译，词汇数量比例应该更接近1
                if translated_words >= original_words * 0.5 and translated_words <= original_words * 1.5:
                    # 词汇数量合理，即使字符长度比例不太合理，也认为通过
                    return True, f"长度比例基本合理 (字符比例: {ratio:.2f}, 词汇比例: {translated_words/original_words:.2f} 词汇数: {translated_words}/{original_words})"
            except ImportError:
                # jieba库不存在，使用原有的检查逻辑
                pass

            msg = f"翻译结果长度不合理：{len(translated)} vs {len(original)} (比例: {ratio:.2f}, 阈值: [{min_ratio}, {max_ratio}])"
            logger.warning(f"[翻译质量检查] {msg}")
            return False, msg

        return True, f"长度比例正常 (比例: {ratio:.2f})"

    def _check_color_codes(self, original: str, translated: str) -> Tuple[bool, str]:
        """检查颜色代码保留"""
        original_color_codes = len(re.findall(r'§[0-9a-fklmnor]', original))
        translated_color_codes = len(
            re.findall(r'§[0-9a-fklmnor]', translated))

        if original_color_codes > 0 and translated_color_codes != original_color_codes:
            msg = f"颜色代码数量不匹配：{translated_color_codes} vs {original_color_codes}"
            logger.warning(f"[翻译质量检查] {msg}")
            return False, msg

        return True, f"颜色代码保留正常 (原文: {original_color_codes}, 翻译: {translated_color_codes})"

    def _check_placeholders(self, original: str, translated: str) -> Tuple[bool, str]:
        """检查占位符保留（%s, %d 等）"""
        original_placeholders = len(re.findall(r'%[0-9]*[sd]', original))
        translated_placeholders = len(re.findall(r'%[0-9]*[sd]', translated))

        if original_placeholders > 0 and translated_placeholders != original_placeholders:
            msg = f"占位符数量不匹配：{translated_placeholders} vs {original_placeholders}"
            logger.warning(f"[翻译质量检查] {msg}")
            return False, msg

        return True, f"占位符保留正常 (原文: {original_placeholders}, 翻译: {translated_placeholders})"

    def _check_english_ratio(self, original: str, translated: str) -> Tuple[bool, str]:
        """检查英文比例"""
        if len(translated) <= 10:  # 只对较长的文本进行检查
            return True, "文本过短，跳过英文比例检查"

        english_ratio = len(re.findall(
            r'[a-zA-Z]', translated)) / len(translated)

        if english_ratio > self.english_max_ratio:
            msg = f"翻译结果包含过多英文：{english_ratio:.2%} (阈值: {self.english_max_ratio:.2%})"
            logger.warning(f"[翻译质量检查] {msg}")
            return False, msg

        return True, f"英文比例正常 ({english_ratio:.2%})"

    def _check_unprocessed_placeholders(self, translated: str) -> Tuple[bool, str]:
        """检查未处理的占位符（术语替换失败）"""
        for pattern in self.placeholder_patterns:
            if re.search(pattern, translated):
                msg = f"翻译结果包含未处理的占位符：匹配模式 {pattern}"
                logger.warning(f"[翻译质量检查] {msg}")
                return False, msg

        return True, "无未处理占位符"

    def _check_term_consistency(self, original: str, translated: str) -> Tuple[bool, str]:
        """检查术语一致性（如果原文包含已知术语，翻译结果应包含对应的中文）"""
        if not self.term_service:
            return True, "无术语服务，跳过术语一致性检查"

        issues = []
        for term, chinese_translation in self.term_service.terms.items():
            if term in original and term in translated:
                # 跳过技术标识符（如 minecraft:stone 中的 stone）
                # 检查term是否出现在namespace:term或module:term等模式中
                if self._is_part_of_technical_identifier(original, term):
                    continue
                # 英文术语出现在原文和翻译结果中，可能未翻译
                issues.append(f"术语可能未翻译：'{term}'")

        if issues:
            msg = f"术语一致性检查发现 {len(issues)} 个问题: {', '.join(issues[:3])}"
            if len(issues) > 3:
                msg += f" 等 {len(issues)} 个问题"
            logger.warning(f"[翻译质量检查] {msg}")
            return False, msg

        return True, "术语一致性正常"

    @staticmethod
    def _is_part_of_technical_identifier(text: str, term: str) -> bool:
        """检查术语是否作为技术标识符的一部分出现"""
        import re
        # 匹配 namespace:term 或 module:term 模式
        pattern = rf'[a-zA-Z_][a-zA-Z0-9_]*:{re.escape(term)}\b'
        if re.search(pattern, text):
            return True
        # 匹配 snake_case 或 camelCase 中的子串
        # 如 "tcon_stone_block" 包含 "stone"
        if re.search(rf'\b[a-z_]*{re.escape(term)}[a-z_]*\b', text):
            return True
        return False

    def analyze_batch(self, pairs: List[Tuple[str, str]]) -> Dict[str, any]:
        """
        批量分析翻译质量

        Args:
            pairs: 原文-翻译对列表 [(original, translated), ...]

        Returns:
            分析结果字典
        """

        total = len(pairs)
        passed = 0
        issues_summary = {}
        detailed_results = []

        for i, (original, translated) in enumerate(pairs):
            quality_ok, report = self.check_quality(
                original, translated, detailed_report=True)

            if quality_ok:
                passed += 1

            # 汇总问题
            for issue in report.get('issues', []):
                issues_summary[issue] = issues_summary.get(issue, 0) + 1

            detailed_results.append({
                'index': i,
                'quality_ok': quality_ok,
                'original': original[:100] + ('...' if len(original) > 100 else ''),
                'translated': translated[:100] + ('...' if len(translated) > 100 else ''),
                'issues': report.get('issues', []),
                'length_ratio': report.get('length_ratio', 0),
            })

        pass_rate = passed / total if total > 0 else 0

        return {
            'total': total,
            'passed': passed,
            'failed': total - passed,
            'pass_rate': pass_rate,
            'issues_summary': issues_summary,
            'sample_results': detailed_results[:10],  # 只返回前10个详细结果
        }

    def _store_in_cache(self, original: str, translated: str, quality_ok: bool) -> None:
        """将质量检查结果存储到缓存"""
        cache_key = (original, translated)
        with self._cache_lock:
            # 如果缓存已满，执行LRU清理
            if len(self._quality_cache) >= self.cache_max_size:
                # 移除最久未使用的项（列表中的第一个）
                lru_key = self._quality_cache_keys.pop(0)
                del self._quality_cache[lru_key]

            # 存储新项
            self._quality_cache[cache_key] = quality_ok
            self._quality_cache_keys.append(cache_key)

    def clear_quality_cache(self) -> None:
        """清除质量检查缓存"""
        with self._cache_lock:
            self._quality_cache.clear()
            self._quality_cache_keys.clear()
        logger.debug("质量检查缓存已清除")

    def get_quality_cache_stats(self) -> Dict[str, any]:
        """获取质量检查缓存统计信息"""
        with self._cache_lock:
            return {
                'cache_size': len(self._quality_cache),
                'cache_max_size': self.cache_max_size,
                'cache_enabled': self.cache_enabled,
                'lru_keys_count': len(self._quality_cache_keys)
            }


def create_quality_checker(term_service=None) -> TranslationQualityChecker:
    """
    创建翻译质量检查器的便捷函数

    Args:
        term_service: 术语服务实例（可选）

    Returns:
        TranslationQualityChecker实例
    """
    return TranslationQualityChecker(term_service)


if __name__ == "__main__":
    """
    测试翻译质量检查器
    """
    checker = TranslationQualityChecker()

    # 测试用例
    test_cases = [
        # (原文, 翻译, 预期结果)
        ("Hello World", "你好世界", True),  # 正常翻译
        ("§6Example Tower Defense Base§f", "§6示例塔防基地§f", True),  # 包含颜色代码
        ("Item %s not found", "物品 %s 未找到", True),  # 包含占位符
        ("Hello World", "Please provide the English text for translation", False),  # 包含AI提示
        ("Short", "非常非常长的翻译文本", False),  # 长度比例不合理
        ("§6Test§f", "测试", False),  # 颜色代码丢失
        ("Item %s", "物品", False),  # 占位符丢失
        ("Hello World", "Hello World 你好", False),  # 英文比例过高
    ]

    print("=" * 60)
    print("翻译质量检查器测试")
    print("=" * 60)

    for i, (original, translated, expected) in enumerate(test_cases, 1):
        result = checker.check_quality(original, translated)
        status = "✅" if result == expected else "❌"
        print(f"{i}. {status} 原文: '{original}'")
        print(f"   翻译: '{translated}'")
        print(f"   预期: {expected}, 实际: {result}")
        if result != expected:
            print("   ⚠️  测试失败!")
        print()

    # 批量分析测试
    print("=" * 60)
    print("批量分析测试")
    print("=" * 60)

    pairs = [(original, translated) for original, translated, _ in test_cases]
    analysis = checker.analyze_batch(pairs)

    print(f"总共测试: {analysis['total']}")
    print(f"通过: {analysis['passed']}")
    print(f"失败: {analysis['failed']}")
    print(f"通过率: {analysis['pass_rate']:.2%}")
    print(f"问题汇总: {analysis['issues_summary']}")
