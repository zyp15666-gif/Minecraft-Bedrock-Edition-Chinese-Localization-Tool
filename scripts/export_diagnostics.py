#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""导出诊断 zip（配合崩溃日志中的 ERR- ID 反馈问题）。"""

import argparse
import sys
from pathlib import Path

script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))


def main():
    parser = argparse.ArgumentParser(description="导出诊断包")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=project_root / "diagnostics_export.zip",
        help="输出 zip 路径",
    )
    args = parser.parse_args()

    version = ""
    pyproject = project_root / "pyproject.toml"
    if pyproject.is_file():
        text = pyproject.read_text(encoding="utf-8")
        m = __import__("re").search(r'^version\s*=\s*["\']([^"\']+)["\']', text, __import__("re").MULTILINE)
        if m:
            version = m.group(1)

    from core.diagnostics import export_diagnostic_zip

    path = export_diagnostic_zip(args.output, project_version=version or None)
    print(f"已写入: {path}")


if __name__ == "__main__":
    main()
