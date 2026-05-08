#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
合并术语词典脚本
将扩展术语词典合并到主术语词典
"""

import json
import os
import sys

# 添加项目根目录到路径
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)


def load_json_file(file_path: str, encoding: str = 'utf-8') -> dict:
    """安全加载JSON文件"""
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ 文件不存在: {file_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析错误: {file_path}")
        print(f"   错误信息: {e}")
        sys.exit(1)


def save_json_file(file_path: str, data: dict, encoding: str = 'utf-8') -> None:
    """安全保存JSON文件"""
    try:
        with open(file_path, 'w', encoding=encoding) as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ 保存文件失败: {file_path}")
        print(f"   错误信息: {e}")
        sys.exit(1)


def merge_terms(existing_file: str, extended_file: str, output_file: str = None) -> None:
    """合并术语词典

    Args:
        existing_file: 现有术语词典路径
        extended_file: 扩展术语词典路径
        output_file: 输出路径，默认覆盖现有词典
    """
    print("=" * 60)
    print("合并术语词典")
    print("=" * 60)

    # 加载现有词典
    print(f"\n📂 加载现有词典: {existing_file}")
    if not os.path.exists(existing_file):
        print(f"❌ 文件不存在: {existing_file}")
        print("   请确保已运行 extract_combined_terms.py 生成扩展词典")
        sys.exit(1)

    existing = load_json_file(existing_file)
    print(f"   现有术语数量: {len(existing)}")

    # 加载扩展词典
    print(f"\n📂 加载扩展词典: {extended_file}")
    if not os.path.exists(extended_file):
        print(f"❌ 文件不存在: {extended_file}")
        print("   请先运行 extract_combined_terms.py 生成扩展词典")
        sys.exit(1)

    extended = load_json_file(extended_file)
    print(f"   扩展术语数量: {len(extended)}")

    # 合并词典
    print("\n🔄 合并词典...")
    existing.update(extended)  # 扩展词典覆盖现有

    # 确定输出路径
    if output_file is None:
        output_file = existing_file

    # 保存结果
    save_json_file(output_file, existing)

    print("\n✅ 合并完成!")
    print(f"   输出文件: {output_file}")
    print(f"   总术语数量: {len(existing)} (+{len(extended)})")


def main():
    """主函数"""
    # 默认路径
    existing_file = "resources/api/minecraft_terms.json"
    extended_file = "resources/api/minecraft_terms_extended.json"

    # 支持命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] in ['-h', '--help']:
            print("""
用法: python merge_terms.py [现有词典] [扩展词典] [输出文件]

参数:
    现有词典    现有术语词典文件路径 (默认: resources/api/minecraft_terms.json)
    扩展词典    扩展术语词典文件路径 (默认: resources/api/minecraft_terms_extended.json)
    输出文件    输出文件路径 (默认: 覆盖现有词典)

示例:
    python merge_terms.py
    python merge_terms.py custom_terms.json extended.json merged.json
            """)
            sys.exit(0)
        else:
            existing_file = sys.argv[1]

    if len(sys.argv) > 2:
        extended_file = sys.argv[2]

    if len(sys.argv) > 3:
        output_file = sys.argv[3]
    else:
        output_file = None

    # 合并术语
    merge_terms(existing_file, extended_file, output_file)

    print("\n" + "=" * 60)
    print("请重启翻译服务以应用新术语")
    print("=" * 60)


if __name__ == "__main__":
    main()
