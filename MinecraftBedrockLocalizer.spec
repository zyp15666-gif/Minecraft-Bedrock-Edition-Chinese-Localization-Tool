# -*- mode: python ; coding: utf-8 -*-

import os
import importlib.util

def get_flet_icons_path():
    """动态获取 flet icons.json 路径"""
    try:
        spec = importlib.util.find_spec('flet')
        if spec and spec.origin:
            flet_dir = os.path.dirname(spec.origin)
            return os.path.join(flet_dir, 'controls', 'material', 'icons.json')
    except Exception:
        pass
    return None

block_cipher = None

flet_icons_path = get_flet_icons_path()

a = Analysis(['scripts/run_flet_desktop.py'],
             pathex=['.'],
             binaries=[
                 ('resources/api/minecraft_terms.json', 'resources/api/')
             ],
             datas=[
                 ('docs/', 'docs/'),
                 ('config/config.example.yml', 'config/'),
             ] + ([(flet_icons_path, 'flet/controls/material/')] if flet_icons_path else []),
             hiddenimports=[
                 'flet',
                 'flet_core',
                 'flet_desktop',
                 'requests',
                 'httpx',
                 'yaml',
                 'json',
                 'threading',
                 'time',
                 'os',
                 'sys',
                 're',
                 'typing',
                 'collections',
                 'itertools',
                 'functools',
                 'hashlib',
                 'base64',
                 'uuid',
                 'random',
                 'string',
                 'datetime',
                 'pathlib',
                 'shutil',
                 'subprocess',
                 'argparse',
                 'inspect',
                 'warnings',
                 'importlib',
                 'tempfile',
                 'logging',
                 'tqdm'
             ],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='MinecraftBedrockLocalizer',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False,
          icon='icon_new.ico')

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='MinecraftBedrockLocalizer')