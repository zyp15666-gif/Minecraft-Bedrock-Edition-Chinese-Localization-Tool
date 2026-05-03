#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
翻译管道模块 - 整合翻译初始化、文件翻译和批量处理功能

从临时脚本 translate_en_us.py 重构而来，提供标准化的翻译管道接口
"""

from config.config_manager import ConfigManager
from core.application_service import ApplicationService
from core.container import build_app_container
from core.file_handler import FileHandler
from core.translator import Translator
from api.api_manager import APIManager
import os
import sys
import time
from typing import Dict, Any, Optional, Callable, Tuple


class TranslationPipeline:
    """翻译管道类 - 统一管理翻译组件和流程"""

    def __init__(self, config_path: str = None):
        """
        初始化翻译管道

        Args:
            config_path: 配置文件路径（已弃用，保留用于兼容性）
        """
        self.config_path = config_path  # 保留用于兼容性
        self.config = None
        self.api_manager = None
        self.translator = None
        self.file_handler = None
        self.app_service = None
        self.initialized = False

    def initialize(self) -> bool:
        """
        初始化翻译管道组件

        Returns:
            是否初始化成功
        """
        try:
            container = build_app_container()
            self.config = container.config
            self.api_manager = container.api_manager
            self.translator = container.translator
            self.file_handler = container.file_handler
            self.app_service = container.app_service

            apis = self.api_manager.detect_available_apis()
            if not apis:
                raise RuntimeError("未检测到可用API，请检查网络和配置")

            print(f"✅ 检测到 {len(apis)} 个可用API")
            self.initialized = True
            return True

        except Exception as e:
            print(f"❌ 翻译管道初始化失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_components(self) -> Tuple[APIManager, Translator, FileHandler, ApplicationService]:
        """
        获取翻译管道组件

        Returns:
            (api_manager, translator, file_handler, app_service) 元组
        """
        if not self.initialized:
            raise RuntimeError("翻译管道未初始化，请先调用initialize()")

        return self.api_manager, self.translator, self.file_handler, self.app_service

    def translate_lang_file(
        self,
        input_file: str,
        output_file: str,
        progress_callback: Optional[Callable[[
            float, int, float], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> bool:
        """
        翻译.lang文件并保存到指定输出文件

        Args:
            input_file: 输入文件路径
            output_file: 输出文件路径
            progress_callback: 进度回调函数 (百分比, 剩余条数, 剩余时间)
            log_callback: 日志回调函数

        Returns:
            是否翻译成功
        """
        if not self.initialized:
            if not self.initialize():
                return False

        try:
            if not os.path.exists(input_file):
                if log_callback:
                    log_callback(f"❌ 输入文件不存在: {input_file}")
                return False

            entries = self.file_handler.parse_lang_file(input_file)

            if not entries:
                if log_callback:
                    log_callback("❌ 未从文件中提取到任何条目")
                return False

            if log_callback:
                log_callback(f"📊 解析到 {len(entries)} 个条目")

            if log_callback:
                log_callback("🌐 开始翻译...")

            start_time = time.time()

            translated = self.translator.translate_entries(
                entries,
                progress_callback=progress_callback,
                log_callback=log_callback
            )

            elapsed = time.time() - start_time
            if log_callback:
                log_callback(f"⏱️  翻译完成，耗时: {elapsed:.2f} 秒")

            if not translated:
                if log_callback:
                    log_callback("❌ 翻译失败，未生成翻译结果")
                return False

            if log_callback:
                log_callback(f"💾 写入输出文件: {output_file}")

            output_dir = os.path.dirname(output_file)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)

            with open(output_file, 'w', encoding='utf-8', newline='\n') as f:
                with open(input_file, 'r', encoding='utf-8') as inf:
                    for line in inf:
                        line_stripped = line.strip()
                        if not line_stripped or line_stripped.startswith('#'):
                            f.write(line)
                        elif '=' in line_stripped:
                            break
                        else:
                            f.write(line)

                for key, value in entries.items():
                    translated_value = translated.get(
                        key, value)
                    translated_value = translated_value.replace('\n', '\\n')
                    f.write(f"{key}={translated_value}\n")

            success_count = len(
                [key for key in entries if translated.get(key, '') != entries[key]])

            if log_callback:
                log_callback(f"✅ 翻译完成！输出文件: {output_file}")
                log_callback(
                    f"📊 统计: 总共 {len(entries)} 条, 成功翻译 {success_count} 条")

            return True

        except Exception as e:
            if log_callback:
                log_callback(f"❌ 翻译过程中出错: {e}")
            import traceback
            traceback.print_exc()
            return False

    def batch_translate_files(
        self,
        file_pairs: list[tuple[str, str]],
        progress_callback: Optional[Callable[[float, int, int], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, bool]:
        """
        批量翻译多个文件

        Args:
            file_pairs: 文件对列表 [(输入文件, 输出文件), ...]
            progress_callback: 进度回调函数 (进度值0-1, 剩余文件数, 剩余时间)
            log_callback: 日志回调函数

        Returns:
            字典 {文件路径: 是否成功}
        """
        results = {}
        total_files = len(file_pairs)

        if log_callback:
            log_callback(f"📁 开始批量翻译 {total_files} 个文件")

        for i, (input_file, output_file) in enumerate(file_pairs):
            if progress_callback:
                progress_callback(i / total_files, total_files - i, 0)

            if log_callback:
                log_callback(f"\n📄 处理文件 {i+1}/{total_files}: {input_file}")

            file_start = i / total_files
            file_end = (i + 1) / total_files

            def make_inner_progress(start, end):
                def inner_progress(p, remaining, time_left):
                    if progress_callback:
                        mapped = start + p * (end - start)
                        progress_callback(mapped, remaining, time_left)
                return inner_progress

            success = self.translate_lang_file(
                input_file,
                output_file,
                progress_callback=make_inner_progress(file_start, file_end),
                log_callback=lambda msg, cb=log_callback: cb(
                    f"  {msg}") if cb else None
            )

            results[input_file] = success

            if progress_callback:
                progress_callback((i + 1) / total_files, total_files - i - 1, 0)

        success_count = sum(1 for result in results.values() if result)

        if log_callback:
            log_callback(f"\n📊 批量翻译完成: 成功 {success_count}/{total_files} 个文件")

        return results


def create_pipeline(config_path: str = "config/config.yml") -> TranslationPipeline:
    """
    创建翻译管道的便捷函数

    Args:
        config_path: 配置文件路径

    Returns:
        TranslationPipeline实例
    """
    return TranslationPipeline(config_path)


def setup_translation_pipeline(config_path: str = "config/config.yml") -> Optional[Tuple[ApplicationService, Dict[str, Any]]]:
    """
    设置翻译管道（兼容旧接口）

    Args:
        config_path: 配置文件路径

    Returns:
        (app_service, config) 元组 或 None（失败时）
    """
    try:
        pipeline = TranslationPipeline(config_path)
        if pipeline.initialize():
            _, _, _, app_service = pipeline.get_components()
            return app_service, pipeline.config
        return None
    except Exception as e:
        print(f"❌ 翻译管道设置失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def translate_lang_file_direct(
    input_file: str,
    output_file: str,
    config_path: str = None,
    progress_callback: Optional[Callable[[float, int, float], None]] = None,
    log_callback: Optional[Callable[[str], None]] = None
) -> bool:
    """
    直接翻译.lang文件（兼容旧接口）

    Args:
        input_file: 输入文件路径
        output_file: 输出文件路径
        config_path: 配置文件路径（已弃用，保留用于兼容性）
        progress_callback: 进度回调函数
        log_callback: 日志回调函数

    Returns:
        是否翻译成功
    """
    pipeline = TranslationPipeline(config_path)
    return pipeline.translate_lang_file(input_file, output_file, progress_callback, log_callback)


if __name__ == "__main__":
    """
    命令行入口点 - 用于测试
    """
    print("=" * 60)
    print("翻译管道测试")
    print("=" * 60)

    pipeline = create_pipeline()
    if pipeline.initialize():
        print("✅ 翻译管道初始化成功")

        api_manager, translator, file_handler, app_service = pipeline.get_components()
        print(
            f"📊 可用API数量: {len(api_manager.available_apis) if api_manager.available_apis else 0}")
        print(f"📊 术语数量: {len(api_manager.term_service.terms)}")

        test_input = "en_US.lang"
        test_output = "test_zh_cn.lang"

        if os.path.exists(test_input):
            print(f"\n🔍 测试翻译文件: {test_input}")

            def test_progress(p, remaining, time_left):
                print(f"  进度: {p:.1f}% - 剩余 {remaining} 条")

            def test_log(msg):
                print(f"  日志: {msg}")

            success = pipeline.translate_lang_file(
                test_input, test_output,
                progress_callback=test_progress,
                log_callback=test_log
            )

            if success:
                print(f"✅ 测试成功！输出文件: {test_output}")
            else:
                print("❌ 测试失败")
        else:
            print(f"\n⚠️  测试文件 {test_input} 不存在，跳过翻译测试")
    else:
        print("❌ 翻译管道初始化失败")
