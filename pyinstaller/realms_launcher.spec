# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['realms_launcher.py'],
    pathex=[],
    binaries=[('C:\\Windows\\System32\\vcruntime140.dll', '.'), ('C:\\Windows\\System32\\vcruntime140_1.dll', '.'), ('C:\\Windows\\System32\\msvcp140.dll', '.')],
    datas=[('aotr_fs.ico', '.'), ('banner.png', '.'), ('background.jpg', '.'), ('icons8-one-ring-96.png', '.'), ('SCCpointer.cur', '.'), ('SCCRepair.ani', '.'), ('SCCAttMagic.ani', '.'), ('magnify.ani', '.'), ('OneRing.ani', '.'), ('ringbearer', 'ringbearer')],
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
    icon=['aotr_fs.ico'],
)
