# -*- mode: python ; coding: utf-8 -*-
import os

# Paths relative to project root (spec lives in pyinstaller/)
ROOT = os.path.normpath(os.path.join(SPECPATH, '..'))

a = Analysis(
    [os.path.join(ROOT, 'src', 'realms_launcher', '__main__.py')],
    pathex=[os.path.join(ROOT, 'src')],
    binaries=[('C:\\Windows\\System32\\vcruntime140.dll', '.'), ('C:\\Windows\\System32\\vcruntime140_1.dll', '.'), ('C:\\Windows\\System32\\msvcp140.dll', '.')],
    datas=[(os.path.join(ROOT, 'assets'), 'assets')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='realms_launcher',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir='.',  # extract next to the exe to avoid Temp/AV issues
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[os.path.join(ROOT, 'assets', 'icons', 'aotr_fs.ico')],
)
