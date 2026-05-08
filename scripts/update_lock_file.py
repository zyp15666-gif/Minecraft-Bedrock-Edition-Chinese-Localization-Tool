#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新依赖锁定文件

此脚本用于更新requirements.lock文件，确保所有环境使用相同的依赖版本。
"""

import subprocess
import sys
from pathlib import Path


def update_lock_file():
    """更新依赖锁定文件"""
    print("=" * 60)
    print("更新依赖锁定文件")
    print("=" * 60)

    project_root = Path(__file__).parent.parent
    lock_file = project_root / "requirements.lock"

    print(f"\n📝 生成锁定文件: {lock_file}")

    try:
        # 运行pip freeze
        result = subprocess.run(
            [sys.executable, "-m", "pip", "freeze"],
            capture_output=True,
            text=True,
            check=True
        )

        # 写入锁定文件
        with open(lock_file, 'w', encoding='utf-8') as f:
            f.write("# 依赖锁定文件 - 由pip freeze生成\n")
            f.write("# 此文件确保所有环境使用相同的依赖版本\n")
            f.write("# 不要手动修改此文件，使用 python scripts/update_lock_file.py 重新生成\n\n")
            f.write(result.stdout)

        print(f"✅ 锁定文件已更新: {lock_file}")
        print(f"   依赖数量: {len(result.stdout.strip().split(chr(10)))}")

    except subprocess.CalledProcessError as e:
        print(f"❌ 更新失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    update_lock_file()
