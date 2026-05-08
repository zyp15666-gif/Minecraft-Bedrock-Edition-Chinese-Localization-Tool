#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
翻译脚本 - 翻译 en_US.lang 到 zh_cn.lang
使用内置的 DeepSeek API 配置

重构为使用核心翻译管道模块
"""

import os
import sys
from typing import Any, Dict

# 添加项目路径
sys.path.insert(0, '.')

def setup_translation_pipeline():
    """设置翻译管道"""
    try:
        from core.pipeline import setup_translation_pipeline as core_setup_pipeline
        result = core_setup_pipeline()

        if result:
            functions, config = result
            print("✅ 翻译管道初始化成功")
            print(f"🔑 可用 DeepSeek API: {len(config.get('deepseek', []))}")
            return functions, config
        else:
            print("❌ 翻译管道初始化失败")
            return None

    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def translate_lang_file_direct(input_file: str, output_file: str, functions, config: Dict[str, Any]):
    """直接翻译.lang文件并保存到指定输出文件"""
    try:
        from core.pipeline import translate_lang_file_direct as core_translate_file

        # 进度回调
        def progress_callback(p, remaining_count=0, remaining_time=0):
            if p == 100:
                print(f"  进度: {p}% - 完成")
            else:
                if remaining_time > 0:
                    print(f"  进度: {p}% - 剩余 {remaining_count} 条, 约 {remaining_time} 秒")
                else:
                    print(f"  进度: {p}%")

        # 日志回调
        def log_callback(msg):
            print(f"  日志: {msg}")

        print(f"\n📄 开始翻译文件: {input_file}")
        success = core_translate_file(
            input_file=input_file,
            output_file=output_file,
            config_path=None,  # 使用ConfigManager自动检测
            progress_callback=progress_callback,
            log_callback=log_callback
        )

        return success

    except Exception as e:
        print(f"❌ 翻译过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("Minecraft 基岩版汉化工具 - 临时翻译脚本")
    print("=" * 60)

    # 输入输出文件
    input_file = "en_US.lang"
    output_file = "zh_cn.lang"

    # 检查输入文件
    if not os.path.exists(input_file):
        print(f"❌ 输入文件 '{input_file}' 不存在")
        print("请确保 en_US.lang 文件在当前目录")
        return 1

    print(f"📥 输入文件: {input_file}")
    print(f"📤 输出文件: {output_file}")

    # 设置翻译管道
    result = setup_translation_pipeline()
    if not result:
        return 1

    functions, config = result

    # 执行翻译
    success = translate_lang_file_direct(input_file, output_file, functions, config)

    if success:
        print("\n🎉 翻译任务完成！")
        # 显示输出文件的前几行
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                lines = [next(f) for _ in range(5)]
                print("\n📄 输出文件前5行预览:")
                for line in lines:
                    print(f"   {line.rstrip()}")
        except:
            pass
        return 0
    else:
        print("\n❌ 翻译任务失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
