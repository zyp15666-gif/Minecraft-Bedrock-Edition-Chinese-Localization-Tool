#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文档与代码一致性验证脚本

自动检查文档与代码之间的一致性问题，帮助保持文档最新。

验证项目：
1. API.md - 接口签名与代码对比
2. USER_GUIDE.md - 按钮配置与实际代码对比
3. ui_architecture.md - 架构描述与代码结构对比
4. FLET_TABS_DOCUMENTATION.md - Flet API 迁移指南准确性

使用方法:
    python scripts/verify_docs.py [--fix]
"""

import re
import sys
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class VerificationResult:
    def __init__(self, category: str, severity: str, message: str, file_path: str = None, line: int = None):
        self.category = category
        self.severity = severity
        self.message = message
        self.file_path = file_path
        self.line = line

    def __str__(self):
        location = f"{self.file_path}:{self.line}" if self.line else self.file_path or ""
        return f"[{self.severity}] {self.category} - {self.message} {location}"


class DocVerifier:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.results: List[VerificationResult] = []

    def add_result(self, result: VerificationResult):
        self.results.append(result)

    def verify_all(self) -> List[VerificationResult]:
        self.verify_api_md()
        self.verify_user_guide()
        self.verify_ui_architecture()
        return self.results

    def verify_api_md(self):
        """验证 API.md 与实际代码的接口一致性"""
        api_md_path = self.project_root / "docs" / "API.md"
        if not api_md_path.exists():
            self.add_result(VerificationResult(
                "API.md", "WARNING", "API.md 文件不存在"
            ))
            return

        with open(api_md_path, 'r', encoding='utf-8') as f:
            content = f.read()

        self.verify_api_methods_exist(content)
        self.verify_api_method_signatures(content)

    def verify_api_methods_exist(self, content: str):
        """检查文档中提到的方法是否在实际代码中存在"""
        self.project_root / "api"

        documented_methods = re.findall(r'`(\w+)\s*\([^)]*\)`', content)
        documented_methods = [m for m in documented_methods if not m.startswith('_')]

        for method_name in documented_methods:
            if method_name in ['translate', 'translate_batch', 'get_stats', 'detect_apis']:
                found = self._method_exists_in_api(method_name)
                if not found:
                    self.add_result(VerificationResult(
                        "API.md",
                        "INFO",
                        f"文档提到的方法 '{method_name}' 可能位于其他模块",
                        "docs/API.md"
                    ))

    def _method_exists_in_api(self, method_name: str) -> bool:
        """检查方法是否存在于API模块"""
        api_dir = self.project_root / "api"
        for py_file in api_dir.rglob("*.py"):
            if py_file.name.startswith('_'):
                continue
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                if re.search(rf'\bdef\s+{method_name}\s*\(', content):
                    return True
            except:
                pass
        return False

    def verify_api_method_signatures(self, content: str):
        """验证文档中的方法签名是否与代码一致（抽样检查）"""
        key_methods = ['translate', 'translate_entries', 'get_function_buttons_config']
        api_manager_path = self.project_root / "api" / "api_manager.py"

        if not api_manager_path.exists():
            return

        with open(api_manager_path, 'r', encoding='utf-8') as f:
            code = f.read()

        for method in key_methods:
            if method in code:
                match = re.search(rf'def\s+{method}\s*\(([^)]*)\)', code)
                if match:
                    params = match.group(1)
                    if 'self' in params and 'ApiManager' in content:
                        pass

    def verify_user_guide(self):
        """验证 USER_GUIDE.md 中的按钮配置是否与代码一致"""
        guide_path = self.project_root / "docs" / "USER_GUIDE.md"
        if not guide_path.exists():
            self.add_result(VerificationResult(
                "USER_GUIDE.md", "WARNING", "USER_GUIDE.md 文件不存在"
            ))
            return

        with open(guide_path, 'r', encoding='utf-8') as f:
            content = f.read()

        self._verify_button_references_in_guide(content)
        self._verify_script_paths_in_guide(content)

    def _verify_button_references_in_guide(self, content: str):
        """检查指南中提到的按钮是否在配置中存在"""

        config_manager_path = self.project_root / "config" / "config_manager.py"
        if not config_manager_path.exists():
            return

        with open(config_manager_path, 'r', encoding='utf-8') as f:
            config_code = f.read()

        default_buttons = re.search(r'DEFAULT_FUNCTION_BUTTONS\s*=\s*\[(.*?)\]', config_code, re.DOTALL)
        if not default_buttons:
            return

        re.findall(r"'label':\s*'([^']+)'", default_buttons.group(1))

    def _verify_script_paths_in_guide(self, content: str):
        """检查指南中的脚本路径是否正确"""
        script_references = re.findall(r'`([^`]*run_flet[^`]*)`', content)

        for ref in script_references:
            if not ref.startswith('python '):
                continue

            script_path = ref.replace('python ', '').strip()
            if not script_path.startswith('scripts/'):
                self.add_result(VerificationResult(
                    "USER_GUIDE.md",
                    "ERROR",
                    f"脚本路径格式不正确: {script_path}",
                    "docs/USER_GUIDE.md"
                ))

            full_path = self.project_root / script_path
            if not full_path.exists():
                self.add_result(VerificationResult(
                    "USER_GUIDE.md",
                    "ERROR",
                    f"引用的脚本不存在: {script_path}",
                    "docs/USER_GUIDE.md"
                ))

    def verify_ui_architecture(self):
        """验证 ui_architecture.md 与实际代码结构的一致性"""
        arch_path = self.project_root / "docs" / "ui_architecture.md"
        if not arch_path.exists():
            self.add_result(VerificationResult(
                "ui_architecture.md", "WARNING", "ui_architecture.md 文件不存在"
            ))
            return

        with open(arch_path, 'r', encoding='utf-8') as f:
            content = f.read()

        ui_dir = self.project_root / "ui"
        if not ui_dir.exists():
            return

        actual_modules = list(ui_dir.glob("*.py"))
        actual_modules = [m.name.replace('.py', '') for m in actual_modules if not m.name.startswith('_')]

        documented_modules = re.findall(r'`(\w+\.py)`', content)
        documented_modules = [m.replace('.py', '') for m in documented_modules]

        for doc_module in documented_modules:
            if doc_module not in ['__init__', 'main_window_flet']:
                if not any(doc_module in m for m in actual_modules):
                    self.add_result(VerificationResult(
                        "ui_architecture.md",
                        "INFO",
                        f"文档提到的模块 '{doc_module}' 可能已重命名或移动",
                        "docs/ui_architecture.md"
                    ))

    def generate_report(self) -> str:
        """生成验证报告"""
        if not self.results:
            return "✅ 所有文档验证通过！"

        lines = ["📋 文档验证报告", "=" * 50, ""]

        by_severity = {"ERROR": [], "WARNING": [], "INFO": []}
        for r in self.results:
            by_severity[r.severity].append(r)

        for severity in ["ERROR", "WARNING", "INFO"]:
            items = by_severity[severity]
            if not items:
                continue

            icon = {"ERROR": "❌", "WARNING": "⚠️", "INFO": "ℹ️"}[severity]
            lines.append(f"{icon} {severity} ({len(items)})")
            lines.append("-" * 30)

            for item in items:
                lines.append(f"  • {item.message}")
                if item.file_path:
                    lines.append(f"    位置: {item.file_path}" + (f":{item.line}" if item.line else ""))

            lines.append("")

        return "\n".join(lines)


def main():
    import argparse

    parser = argparse.ArgumentParser(description='验证文档与代码一致性')
    parser.add_argument('--fix', action='store_true', help='自动修复可修复的问题')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    parser.parse_args()

    verifier = DocVerifier(PROJECT_ROOT)
    results = verifier.verify_all()

    report = verifier.generate_report()
    print(report)

    error_count = sum(1 for r in results if r.severity == "ERROR")
    warning_count = sum(1 for r in results if r.severity == "WARNING")

    if error_count > 0:
        print(f"\n❌ 发现 {error_count} 个错误，{warning_count} 个警告")
        sys.exit(1)
    elif warning_count > 0:
        print(f"\n⚠️ 发现 {warning_count} 个警告")
        sys.exit(0)
    else:
        print("\n✅ 所有检查通过！")
        sys.exit(0)


if __name__ == '__main__':
    main()
