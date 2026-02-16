# -*- mode: python ; coding: utf-8 -*-
import os
import sys

# Paths relative to project root (spec lives in pyinstaller/)
ROOT = os.path.normpath(os.path.join(SPECPATH, '..'))

# Use vcruntime DLLs from the Python installation (not System32) so the
# bundled versions match exactly what python313.dll was built against.
_python_dir = os.path.dirname(sys.executable)
_vc_binaries = []
for _dll in ('vcruntime140.dll', 'vcruntime140_1.dll'):
    _path = os.path.join(_python_dir, _dll)
    if os.path.isfile(_path):
        _vc_binaries.append((_path, '.'))

a = Analysis(
    [os.path.join(ROOT, 'src', 'realms_launcher', '__main__.py')],
    pathex=[os.path.join(ROOT, 'src')],
    binaries=_vc_binaries,
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
    runtime_tmpdir=None,  # extract to user %TEMP% (always writable, even after elevated update relaunch)
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[os.path.join(ROOT, 'assets', 'icons', 'aotr_fs.ico')],
)
