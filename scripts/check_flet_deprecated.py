#!/usr/bin/env python3
"""检查 Flet 弃用 API 使用情况。

在 Flet 0.85+ 中，以下模块级辅助函数已被移除，必须使用类构造函数代替。

规则来源:
  - https://github.com/flet-dev/flet/pull/6425
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple

FORBIDDEN_PATTERNS: List[Tuple[str, str, str]] = [
    (r'\bft\.border\.',         'ft.border.* → 已移除 (0.85+)', 'ft.Border(...)'),
    (r'\bft\.padding\.',        'ft.padding.* → 已移除 (0.85+)', 'ft.Padding(...)'),
    (r'\bft\.margin\.',         'ft.margin.* → 已移除 (0.85+)', 'ft.Margin(...)'),
    (r'\bft\.border_radius\.',  'ft.border_radius.* → 已移除 (0.85+)', 'ft.BorderRadius(...)'),

    (r'page\.dialog\s*=\s*\w',  'page.dialog = ... → 旧对话框API', 'page.open(dialog)'),
    (r'page\.dialog\.open\s*=', 'page.dialog.open = True → 旧对话框API', 'page.open(dialog)'),
    (r'page\.close_dialog\(',   'page.close_dialog() → 已弃用', 'page.pop_dialog()'),

    (r'^\s*ft\.app\(',          'ft.app() → 已弃用 (0.80+)', 'ft.run()'),
    (r'^\s*ft\.app_flet\(',     'ft.app_flet() → 已弃用', 'ft.run()'),
    (r'^\s*ft\.app_web\(',      'ft.app_web() → 已弃用', 'ft.run()'),
]


def _is_fallback_compat(content: str, lineno: int) -> bool:
    """检查 ft.app() 是否位于版本兼容回退分支中"""
    lines = content.split('\n')
    for i in range(max(0, lineno - 5), lineno):
        prev = lines[i].strip()
        if 'hasattr' in prev and 'run' in prev and 'ft' in prev:
            return True
        if prev == 'else:' and i > 0 and 'hasattr' in lines[i - 1]:
            return True
    return False


def check_file(filepath: Path) -> List[Tuple[int, str, str, str]]:
    violations = []
    try:
        content = filepath.read_text(encoding='utf-8')
    except Exception:
        return violations

    for lineno, line in enumerate(content.split('\n'), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith(('#', '//', '"""', "'''")):
            continue
        for pattern, description, replacement in FORBIDDEN_PATTERNS:
            if not re.search(pattern, stripped):
                continue
            if pattern.startswith(r'^\s*ft\.app\('):
                if _is_fallback_compat(content, lineno):
                    continue
            violations.append((lineno, stripped, description, replacement))

    return violations


def main() -> int:
    project_root = Path(__file__).resolve().parent.parent
    source_dirs = ['api', 'core', 'config', 'ui', 'scripts', 'tests']

    exclude_names = {
        'check_flet_deprecated.py',
        '__pycache__',
    }

    total = 0
    for dir_name in source_dirs:
        dir_path = project_root / dir_name
        if not dir_path.is_dir():
            continue

        for filepath in sorted(dir_path.rglob('*.py')):
            if any(e in filepath.parts for e in ['.venv', 'venv', '.git', '.pytest_cache', '__pycache__']):
                continue
            if filepath.name in exclude_names:
                continue

            violations = check_file(filepath)
            if violations:
                print(f"\n{'=' * 70}")
                print(f"  {filepath.relative_to(project_root)}")
                print(f"{'=' * 70}")
                for lineno, line_text, problem, fix in violations:
                    print(f"  L{lineno:>4}: {problem}")
                    print(f"          → {line_text[:80]}")
                    print(f"          → 替代: {fix}")
                    print()
                total += len(violations)

    if total > 0:
        print(f"\n{'=' * 70}")
        print(f"  ❌ 发现 {total} 处使用 Flet 弃用 API")
        print(f"{'=' * 70}\n")
        return 1
    else:
        print("\n  ✅ 未发现 Flet 弃用 API 使用\n")
        return 0


if __name__ == '__main__':
    sys.exit(main())
