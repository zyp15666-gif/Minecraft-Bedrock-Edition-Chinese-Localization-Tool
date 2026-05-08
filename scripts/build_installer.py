#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 NSIS 安装脚本

自动扫描 dist/MinecraftBedrockLocalizer/_internal/ 目录并生成 NSIS 文件列表，
消除硬编码路径问题。

使用方法:
    方式一（分步执行）:
        1. 先运行 PyInstaller 构建: pyinstaller MinecraftBedrockLocalizer.spec
        2. 运行本脚本: python scripts/build_installer.py
        3. 编译 NSIS 脚本: makensis installer_auto.nsi

    方式二（一键构建）:
        python scripts/build_installer.py --compile

    方式三（完整构建，包含 PyInstaller）:
        python scripts/build_installer.py --full

增强特性:
    - 依赖检查（PyInstaller、makensis）
    - 构建验证
    - 详细的错误诊断
    - 支持一键编译和完整构建
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


class BuildInstallerError(Exception):
    """构建安装脚本错误"""
    pass


def _check_pyinstaller_installed() -> bool:
    """检查 PyInstaller 是否已安装"""
    try:
        subprocess.run(
            ['pyinstaller', '--version'],
            capture_output=True,
            check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _check_makensis_installed() -> bool:
    """检查 makensis 是否已安装"""
    try:
        subprocess.run(
            ['makensis', '/VERSION'],
            capture_output=True,
            check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _find_pyinstaller_output(project_root: Path) -> tuple:
    """查找PyInstaller输出目录

    Returns:
        (dist_dir, internal_dir, exe_file) 元组
    """
    dist_dir = project_root / "dist" / "MinecraftBedrockLocalizer"
    internal_dir = dist_dir / "_internal"
    exe_file = dist_dir / "MinecraftBedrockLocalizer.exe"

    return dist_dir, internal_dir, exe_file


def _verify_build_output(dist_dir: Path, exe_file: Path) -> None:
    """验证PyInstaller构建输出

    Raises:
        BuildInstallerError: 构建输出不完整
    """
    if not dist_dir.exists():
        raise BuildInstallerError(
            f"构建输出目录不存在: {dist_dir}\n"
            f"请先运行 PyInstaller 构建: pyinstaller MinecraftBedrockLocalizer.spec"
        )

    if not exe_file.exists():
        raise BuildInstallerError(
            f"主程序文件不存在: {exe_file}\n"
            f"PyInstaller 构建可能未成功完成"
        )

    # 检查文件大小（小于100KB可能是占位符）
    exe_size = exe_file.stat().st_size
    if exe_size < 100 * 1024:
        raise BuildInstallerError(
            f"主程序文件大小异常 ({exe_size / 1024:.1f} KB)\n"
            f"构建可能未成功完成"
        )


def _read_version(project_root: Path) -> str:
    """获取版本号（从多个来源尝试读取）"""
    # 方法1：从 pyproject.toml 读取
    try:
        pyproject = project_root / "pyproject.toml"
        if pyproject.exists():
            import re
            content = pyproject.read_text(encoding='utf-8')
            m = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
            if m:
                version = m.group(1)
                print(f"   从 pyproject.toml 获取版本: {version}")
                return version
    except Exception as e:
        print(f"   警告：从 pyproject.toml 读取版本失败: {e}")

    # 方法2：从 config.yml 读取
    try:
        cfg = project_root / "config" / "config.yml"
        if cfg.exists():
            import yaml
            with open(cfg, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            if data and 'version' in data:
                version = str(data['version'])
                print(f"   从 config.yml 获取版本: {version}")
                return version
    except Exception as e:
        print(f"   警告：从 config.yml 读取版本失败: {e}")

    # 默认版本
    print("   使用默认版本: 1.0.0")
    return "1.0.0"


def _collect_files_for_installer(internal_dir: Path, dist_dir: Path) -> list:
    """收集需要打包的文件

    Args:
        internal_dir: _internal 目录
        dist_dir: dist 根目录

    Returns:
        文件列表
    """
    files = []

    # 收集 _internal 目录下的所有文件
    if internal_dir.exists():
        for root, _, filenames in os.walk(internal_dir):
            for filename in filenames:
                full_path = Path(root) / filename
                rel_path = full_path.relative_to(dist_dir)
                # 转换为NSIS路径格式（反斜杠）
                nsis_path = str(rel_path).replace('/', '\\')
                files.append(f'  File "${{DIST_DIR}}\\{nsis_path}"')

    return files


def _generate_nsis_script(project_root: Path, dist_dir: Path,
                          internal_dir: Path, exe_file: Path,
                          version: str) -> str:
    """生成NSIS安装脚本内容

    Args:
        project_root: 项目根目录
        dist_dir: dist 目录
        internal_dir: _internal 目录
        exe_file: 主程序文件
        version: 版本号

    Returns:
        NSIS脚本字符串
    """
    files = []

    if exe_file.exists():
        files.append('  File "${DIST_DIR}\\MinecraftBedrockLocalizer.exe"')
    else:
        print(f"警告：主程序 {exe_file} 不存在，跳过")

    internal_files = _collect_files_for_installer(internal_dir, dist_dir)
    files.extend(internal_files)

    print(f"\n📦 共收集到 {len(files)} 个文件")

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    output_exe = f"MinecraftBedrockLocalizerSetup_v{version}.exe"

    template = f'''!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "x64.nsh"

; 自动生成的 NSIS 脚本
; 生成时间: {timestamp}
; 由 scripts/build_installer.py 自动生成，请勿手动修改
; 版本: {version}

; 项目配置
!define PRODUCT_NAME "Minecraft Bedrock Localizer"
!define PRODUCT_VERSION "{version}"
!define PRODUCT_PUBLISHER "Minecraft Bedrock Localizer Team"
!define PRODUCT_UNINST_KEY "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{PRODUCT_NAME}}"
!define PRODUCT_REG_KEY "Software\\MinecraftBedrockLocalizer"

; 安装程序配置
Name "${{PRODUCT_NAME}}"
OutFile "dist\\{output_exe}"
RequestExecutionLevel user
Unicode true
SetCompressor /SOLID lzma

; 安装目录使用 LocalAppData（避免 Program Files 权限问题）
InstallDir "$LOCALAPPDATA\\MinecraftBedrockLocalizer"

!define DIST_DIR "dist\\MinecraftBedrockLocalizer"

; 现代界面
!define MUI_ABORTWARNING
!define MUI_FINISHPAGE_RUN "$INSTDIR\\MinecraftBedrockLocalizer.exe"

; 页面
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

!insertmacro MUI_LANGUAGE "SimpChinese"
!insertmacro MUI_LANGUAGE "English"

; 静默安装支持
SilentInstall silent
SilentUninstall silent

Function .onInit
  ; 检查 WebView2 运行时
  ${{If}} ${{Silent}}
    SetSilent silent
  ${{Else}}
    SetSilent normal
  ${{EndIf}}

  ; WebView2 注册表检测
  ClearErrors
  ReadRegStr $0 HKLM "SOFTWARE\\WOW6432Node\\Microsoft\\EdgeUpdate\\Clients\\{{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}}" "pv"
  ${{If}} ${{Errors}}
    ClearErrors
    ReadRegStr $0 HKLM "SOFTWARE\\Microsoft\\EdgeUpdate\\Clients\\{{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}}" "pv"
  ${{EndIf}}

  ${{If}} ${{Errors}}
    ; WebView2 未安装，提示用户
    MessageBox MB_YESNO|MB_ICONEXCLAMATION \
      "此应用需要 Microsoft Edge WebView2 运行时。$\n$\n\
      检测到系统未安装 WebView2。$\n$\n\
      点击「是」在安装完成后自动打开 WebView2 下载页面，$\n\
      点击「否」继续安装（应用可能无法正常启动）。$\n$\n\
      WebView2 is required. Click Yes to open download page after installation." \
      /SD IDYES IDYES ContinueInstall IDNO SkipWebView2

    ContinueInstall:
      ; 设置标记，安装完成后打开下载页面
      SetRegView 64
      WriteRegStr HKCU "${{PRODUCT_REG_KEY}}" "NeedWebView2" "1"
      SetRegView default
      Goto DoneWebView2Check

    SkipWebView2:
      SetRegView 64
      WriteRegStr HKCU "${{PRODUCT_REG_KEY}}" "NeedWebView2" "0"
      SetRegView default

    DoneWebView2Check:
  ${{Else}}
    ; WebView2 已安装
    DetailPrint "WebView2 Runtime detected: $0"
  ${{EndIf}}
FunctionEnd

; 安装段
Section "Install"
  SetOutPath "$INSTDIR"

  ; 主程序文件
{chr(10).join(files)}

  ; 创建快捷方式
  CreateShortcut "$DESKTOP\\${{PRODUCT_NAME}}.lnk" "$INSTDIR\\MinecraftBedrockLocalizer.exe"
  CreateShortcut "$SMPROGRAMS\\${{PRODUCT_NAME}}.lnk" "$INSTDIR\\MinecraftBedrockLocalizer.exe"

  ; 写入卸载程序
  WriteUninstaller "$INSTDIR\\uninstall.exe"

  ; 注册表信息（用于"添加/删除程序"）
  WriteRegStr HKCU "${{PRODUCT_UNINST_KEY}}" "DisplayName" "${{PRODUCT_NAME}}"
  WriteRegStr HKCU "${{PRODUCT_UNINST_KEY}}" "DisplayVersion" "${{PRODUCT_VERSION}}"
  WriteRegStr HKCU "${{PRODUCT_UNINST_KEY}}" "Publisher" "${{PRODUCT_PUBLISHER}}"
  WriteRegStr HKCU "${{PRODUCT_UNINST_KEY}}" "UninstallString" "$INSTDIR\\uninstall.exe"
  WriteRegStr HKCU "${{PRODUCT_UNINST_KEY}}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${{PRODUCT_UNINST_KEY}}" "QuietUninstallString" "$INSTDIR\\uninstall.exe /S"
  WriteRegDWORD HKCU "${{PRODUCT_UNINST_KEY}}" "NoModify" 1
  WriteRegDWORD HKCU "${{PRODUCT_UNINST_KEY}}" "NoRepair" 1

  ; 保存安装信息
  WriteRegStr HKCU "${{PRODUCT_REG_KEY}}" "InstallPath" "$INSTDIR"
  WriteRegStr HKCU "${{PRODUCT_REG_KEY}}" "Version" "${{PRODUCT_VERSION}}"

  ; 检查是否需要打开 WebView2 下载页面
  SetRegView 64
  ReadRegStr $1 HKCU "${{PRODUCT_REG_KEY}}" "NeedWebView2"
  SetRegView default
  ${{If}} $1 == "1"
    DetailPrint "Opening WebView2 download page..."
    ExecShell "open" "https://go.microsoft.com/fwlink/p/?LinkId=2124703"
    ; 清理标记
    SetRegView 64
    DeleteRegValue HKCU "${{PRODUCT_REG_KEY}}" "NeedWebView2"
    SetRegView default
  ${{EndIf}}
SectionEnd

; 卸载段
Section "Uninstall"
  ; 删除安装目录中的文件
  Delete "$INSTDIR\\MinecraftBedrockLocalizer.exe"
  RMDir /r "$INSTDIR\\_internal"
  Delete "$INSTDIR\\uninstall.exe"

  ; 删除快捷方式
  Delete "$DESKTOP\\${{PRODUCT_NAME}}.lnk"
  Delete "$SMPROGRAMS\\${{PRODUCT_NAME}}.lnk"

  ; 删除注册表
  DeleteRegKey HKCU "${{PRODUCT_UNINST_KEY}}"
  DeleteRegKey HKCU "${{PRODUCT_REG_KEY}}"

  ; 删除安装目录
  RMDir "$INSTDIR"

  ; 询问是否删除用户数据
  MessageBox MB_YESNO "是否删除用户配置和缓存数据？$\n$\n包含：翻译缓存、配置文件、备份等。$\n$\n选择"否"将保留这些数据，下次安装时可继续使用。$\n$\nDelete user data? Select No to keep for next install." IDYES DeleteUserData IDNO KeepUserData

DeleteUserData:
  ; 删除 Documents 下的配置目录
  RMDir /r "$DOCUMENTS\\Minecraft基岩版汉化工具"
  ; 删除 LocalAppData 下的缓存
  RMDir /r "$LOCALAPPDATA\\MinecraftBedrockLocalizer\\Cache"
  ; 删除安全存储文件
  Delete "$DOCUMENTS\\Minecraft基岩版汉化工具\\.secure_storage"
  Goto DoneUninstall

KeepUserData:
  ; 保留用户数据
  DetailPrint "用户数据已保留"

DoneUninstall:
SectionEnd
'''

    return template


def _save_nsis_script(output_file: Path, content: str) -> None:
    """保存NSIS脚本

    Args:
        output_file: 输出文件路径
        content: 脚本内容
    """
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"\n✅ 已生成 NSIS 脚本: {output_file}")


def _run_pyinstaller(project_root: Path) -> int:
    """运行 PyInstaller 构建

    Args:
        project_root: 项目根目录

    Returns:
        0表示成功，非0表示失败
    """
    spec_file = project_root / "MinecraftBedrockLocalizer.spec"
    if not spec_file.exists():
        print(f"❌ 找不到 spec 文件: {spec_file}")
        return 1

    print("\n🔨 运行 PyInstaller 构建...")
    print(f"   spec 文件: {spec_file}")

    try:
        result = subprocess.run(
            ['pyinstaller', str(spec_file), '--noconfirm'],
            cwd=project_root,
            check=False
        )
        if result.returncode != 0:
            print(f"❌ PyInstaller 构建失败 (退出码: {result.returncode})")
            return result.returncode

        print("   ✅ PyInstaller 构建成功")
        return 0
    except FileNotFoundError:
        print("❌ 找不到 pyinstaller 命令")
        print("   请运行: pip install pyinstaller")
        return 1


def _compile_nsis_script(nsi_file: Path, project_root: Path) -> int:
    """编译 NSIS 脚本生成安装程序

    Args:
        nsi_file: NSIS 脚本文件路径
        project_root: 项目根目录

    Returns:
        0表示成功，非0表示失败
    """
    if not nsi_file.exists():
        print(f"❌ NSIS 脚本不存在: {nsi_file}")
        return 1

    print("\n🔨 编译 NSIS 脚本...")
    print(f"   脚本文件: {nsi_file}")

    try:
        result = subprocess.run(
            ['makensis', str(nsi_file)],
            cwd=project_root,
            check=False
        )
        if result.returncode != 0:
            print(f"❌ NSIS 编译失败 (退出码: {result.returncode})")
            return result.returncode

        print("   ✅ NSIS 编译成功")
        return 0
    except FileNotFoundError:
        print("❌ 找不到 makensis 命令")
        print("   请安装 NSIS: https://nsis.sourceforge.io/Download")
        print("   或通过 Chocolatey: choco install nsis")
        return 1


def generate_nsis_script() -> int:
    """生成NSIS安装脚本主函数

    Returns:
        0表示成功，非0表示失败
    """
    print("=" * 60)
    print("NSIS 安装脚本生成工具")
    print("=" * 60)

    # 获取项目根目录
    project_root = Path(__file__).parent.parent
    print(f"\n📁 项目根目录: {project_root}")

    # 检查PyInstaller是否安装
    print("\n🔍 检查构建环境...")
    if not _check_pyinstaller_installed():
        print("❌ PyInstaller 未安装")
        print("   请运行: pip install pyinstaller")
        return 1
    print("   ✅ PyInstaller 已安装")

    # 查找PyInstaller输出
    dist_dir, internal_dir, exe_file = _find_pyinstaller_output(project_root)
    print("\n📂 检查构建输出...")
    print(f"   dist目录: {dist_dir}")
    print(f"   主程序: {exe_file}")

    # 验证构建输出
    try:
        _verify_build_output(dist_dir, exe_file)
        print("   ✅ 构建输出验证通过")
    except BuildInstallerError as e:
        print(f"\n❌ {e}")
        return 1

    # 读取版本号
    print("\n📄 读取版本信息...")
    version = _read_version(project_root)

    # 生成NSIS脚本
    print("\n🔧 生成NSIS脚本...")
    nsis_content = _generate_nsis_script(
        project_root, dist_dir, internal_dir, exe_file, version
    )

    # 保存脚本
    output_file = project_root / "installer_auto.nsi"
    _save_nsis_script(output_file, nsis_content)

    # 检查makensis
    print("\n" + "=" * 60)
    print("构建完成！")
    print("=" * 60)

    print("\n📋 下一步操作:")
    print("   1. 如果需要编译安装程序，请安装 NSIS")
    print(f"   2. 运行: makensis {output_file}")
    print(f"   3. 安装程序将输出到: dist\\MinecraftBedrockLocalizerSetup_v{version}.exe")

    # 检查makensis
    if _check_makensis_installed():
        print("\n✅ 检测到 NSIS，是否现在编译？")
        print(f"   运行: makensis {output_file}")
    else:
        print("\n⚠️  未检测到 NSIS，请手动安装 NSIS 后运行编译命令")

    return 0


def main() -> int:
    """主入口"""
    parser = argparse.ArgumentParser(
        description='NSIS 安装脚本生成工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  python scripts/build_installer.py           # 仅生成 NSIS 脚本
  python scripts/build_installer.py --compile # 生成脚本并编译
  python scripts/build_installer.py --full    # 完整构建（PyInstaller + NSIS）
        '''
    )
    parser.add_argument(
        '--compile', '-c',
        action='store_true',
        help='生成脚本后自动编译 NSIS'
    )
    parser.add_argument(
        '--full', '-f',
        action='store_true',
        help='完整构建：先运行 PyInstaller，再生成并编译 NSIS'
    )
    args = parser.parse_args()

    try:
        project_root = Path(__file__).parent.parent

        # 完整构建模式
        if args.full:
            print("=" * 60)
            print("完整构建模式")
            print("=" * 60)

            # 检查 PyInstaller
            if not _check_pyinstaller_installed():
                print("❌ PyInstaller 未安装")
                print("   请运行: pip install pyinstaller")
                return 1

            # 检查 NSIS
            if not _check_makensis_installed():
                print("❌ NSIS 未安装")
                print("   请安装 NSIS: https://nsis.sourceforge.io/Download")
                print("   或通过 Chocolatey: choco install nsis")
                return 1

            # 运行 PyInstaller
            result = _run_pyinstaller(project_root)
            if result != 0:
                return result

            # 生成 NSIS 脚本
            result = generate_nsis_script()
            if result != 0:
                return result

            # 编译 NSIS
            nsi_file = project_root / "installer_auto.nsi"
            result = _compile_nsis_script(nsi_file, project_root)
            if result != 0:
                return result

            print("\n" + "=" * 60)
            print("🎉 完整构建成功！")
            print("=" * 60)
            return 0

        # 仅编译模式
        if args.compile:
            result = generate_nsis_script()
            if result != 0:
                return result

            nsi_file = project_root / "installer_auto.nsi"
            result = _compile_nsis_script(nsi_file, project_root)
            if result != 0:
                return result

            print("\n" + "=" * 60)
            print("🎉 构建成功！")
            print("=" * 60)
            return 0

        # 默认：仅生成脚本
        return generate_nsis_script()

    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断操作")
        return 130
    except Exception as e:
        print(f"\n❌ 未知错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
