#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能基准测试 — 翻译速度与文件解析速度

运行方式：
    python -m benchmarks.benchmark_translator
    python -m pytest benchmarks/ -v

输出的基准结果可提交到仓库，用于检测性能回归。
"""

import time
import json
import os
import sys
import tempfile
import shutil

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def create_test_bp_folder(count: int = 10) -> str:
    """创建包含 count 个测试方块文件的临时 BP 文件夹"""
    tmp_dir = tempfile.mkdtemp()
    texts_dir = os.path.join(tmp_dir, "texts")
    os.makedirs(texts_dir, exist_ok=True)

    manifest = {
        "format_version": 2,
        "header": {"name": "bench", "description": "bench", "uuid": "0" * 36, "version": [1, 0, 0]},
        "modules": [{"type": "data", "uuid": "1" * 36, "version": [1, 0, 0]}],
    }
    with open(os.path.join(tmp_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f)

    for i in range(count):
        block = {
            "format_version": "1.20.0",
            "minecraft:block": {
                "description": {"identifier": f"test_ns:block_{i}", "register_to_creative_menu": True},
                "components": {"minecraft:display_name": {"value": f"Block {i} Display Name for Testing"}}
            }
        }
        blocks_dir = os.path.join(tmp_dir, "blocks")
        os.makedirs(blocks_dir, exist_ok=True)
        with open(os.path.join(blocks_dir, f"block_{i}.json"), "w") as f:
            json.dump(block, f)

    return tmp_dir


def benchmark_file_extraction():
    """文件解析速度基准测试"""
    from core.file_handler import FileHandler

    config = {"basic": {"namespace": "test_ns", "indent": 4}}
    handler = FileHandler(config)

    results = {}

    for file_count in [1, 5, 10, 20]:
        bp_folder = create_test_bp_folder(file_count)

        # 预热
        _ = handler.extract_entries(bp_folder)

        # 正式测试（取 3 次平均）
        times = []
        for _ in range(3):
            start = time.perf_counter()
            entries = handler.extract_entries(bp_folder)
            elapsed = time.perf_counter() - start
            times.append(elapsed)

        avg_time = sum(times) / len(times)
        results[file_count] = {
            "files": file_count,
            "entries": len(entries),
            "avg_time_s": round(avg_time, 4),
            "entries_per_sec": round(len(entries) / avg_time, 2) if avg_time > 0 else 0,
        }

        shutil.rmtree(bp_folder, ignore_errors=True)

    return results


def benchmark_lang_file_generation():
    """Lang 文件生成速度基准测试"""
    from core.file_handler import FileHandler

    config = {"basic": {"namespace": "test_ns", "indent": 4}}
    handler = FileHandler(config)

    results = {}

    for entry_count in [10, 100, 500]:
        bp_folder = tempfile.mkdtemp()
        texts_dir = os.path.join(bp_folder, "texts")
        os.makedirs(texts_dir, exist_ok=True)

        entries = {f"tile.test_ns:block_{i}.name": f"Block {i}" for i in range(entry_count)}

        times = []
        for _ in range(3):
            start = time.perf_counter()
            handler.merge_and_write_lang(bp_folder, entries, is_translated=False)
            elapsed = time.perf_counter() - start
            times.append(elapsed)

        avg_time = sum(times) / len(times)
        results[entry_count] = {
            "entry_count": entry_count,
            "avg_time_s": round(avg_time, 4),
            "entries_per_sec": round(entry_count / avg_time, 2) if avg_time > 0 else 0,
        }

        shutil.rmtree(bp_folder, ignore_errors=True)

    return results


def benchmark_color_code_operations():
    """颜色代码处理速度基准测试"""
    from core.utils import split_by_color_codes, has_color_codes, normalize_game_text

    texts = [
        "§6Hello §aWorld§f",
        "Normal text without color codes",
        "§c§l§nMultiple §4§l§nformats applied§r",
        "§6[§eServer§6] §bPlayer §7joined the game",
        "Plain string for comparison",
    ] * 200  # 1000 条

    results = {}

    # split_by_color_codes
    start = time.perf_counter()
    for text in texts:
        split_by_color_codes(text)
    elapsed = time.perf_counter() - start
    results["split_by_color_codes"] = {
        "count": len(texts),
        "total_time_s": round(elapsed, 4),
        "ops_per_sec": round(len(texts) / elapsed, 2) if elapsed > 0 else 0,
    }

    # has_color_codes
    start = time.perf_counter()
    for text in texts:
        has_color_codes(text)
    elapsed = time.perf_counter() - start
    results["has_color_codes"] = {
        "count": len(texts),
        "total_time_s": round(elapsed, 4),
        "ops_per_sec": round(len(texts) / elapsed, 2) if elapsed > 0 else 0,
    }

    # normalize_game_text
    start = time.perf_counter()
    for text in texts:
        normalize_game_text(text)
    elapsed = time.perf_counter() - start
    results["normalize_game_text"] = {
        "count": len(texts),
        "total_time_s": round(elapsed, 4),
        "ops_per_sec": round(len(texts) / elapsed, 2) if elapsed > 0 else 0,
    }

    return results


def run_all_benchmarks():
    """运行所有基准测试并输出结果"""
    print("=" * 60)
    print("Minecraft 基岩版汉化工具 — 性能基准测试")
    print("=" * 60)

    print("\n[1/3] 文件解析速度基准测试...")
    extraction_results = benchmark_file_extraction()
    for count, data in extraction_results.items():
        print(f"  {count} 个文件: {data['avg_time_s']}s, "
              f"共 {data['entries']} 条, "
              f"{data['entries_per_sec']} 条/秒")

    print("\n[2/3] Lang 文件生成速度基准测试...")
    lang_results = benchmark_lang_file_generation()
    for count, data in lang_results.items():
        print(f"  {count} 条: {data['avg_time_s']}s, "
              f"{data['entries_per_sec']} 条/秒")

    print("\n[3/3] 颜色代码处理速度基准测试...")
    color_results = benchmark_color_code_operations()
    for name, data in color_results.items():
        print(f"  {name}: {data['total_time_s']}s, "
              f"{data['ops_per_sec']} 次/秒")

    # 汇总结果
    summary = {
        "file_extraction": extraction_results,
        "lang_generation": lang_results,
        "color_operations": color_results,
    }

    # 写入结果文件
    output_path = os.path.join(
        os.path.dirname(__file__),
        "benchmark_results.json"
    )
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 基准测试结果已保存: {output_path}")

    return summary


if __name__ == "__main__":
    run_all_benchmarks()
