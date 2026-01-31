# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Pulse PyInstaller specification file
#
# This file defines how the Pulse application is bundled into a
# standalone executable and macOS .app bundle.
#
# Overview of build steps:
#   1. Analysis  (Analysis):  Scan the entry-point script and its imports to
#      determine all Python modules, binaries, and data files required.
#   2. PYZ       (PYZ):       Create a compressed archive of pure Python
#      modules that will be embedded in the executable.
#   3. EXE       (EXE):       Build the platform-specific executable from the
#      archived Python code, collected binaries, and data.
#   4. COLLECT   (COLLECT):   Collect all binaries and dependencies into a
#      directory structure (onedir mode).
#   5. BUNDLE    (BUNDLE):    For macOS, wrap the collected directory into a
#      .app application bundle with the appropriate metadata.
# ---------------------------------------------------------------------------

block_cipher = None

# Get the project root directory
project_root = Path(SPECPATH).resolve()
src_path = project_root / 'src'

# Read version from environment or default
version = os.environ.get('VERSION', '1.0.13')

a = Analysis(
    ['src/pulse/menu_bar.py'],
    pathex=[str(src_path)],
    binaries=[],
    datas=[],
    hiddenimports=[
        # PyObjC frameworks and bridge modules that may be loaded dynamically
        'objc',
        'Foundation',
        'AppKit',
        'Cocoa',
        'Quartz',
        'CoreFoundation',
        # Pulse internal package (for dynamically imported submodules)
        'pulse',
        # Third-party dependencies that may not be detected via static analysis
        'psutil',
        'requests',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude heavy libraries not used by this project to save space
        'tkinter', 'matplotlib', 'numpy', 'scipy', 'pandas', 'PIL', 'cv2',
        'PyQt5', 'PySide2', 'wx',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Pulse',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Pulse',
)

app = BUNDLE(
    coll,
    name='Pulse.app',
    icon=None,
    bundle_identifier='com.wtznc.pulse',
    info_plist={
        'LSUIElement': True,  # Menu bar only app (hidden from Dock)
        'CFBundleShortVersionString': version,
        'CFBundleVersion': version,
        'NSAppleEventsUsageDescription': 'Pulse requires access to Apple Events to monitor and track application usage.',
        'NSSystemAdministrationUsageDescription': 'Pulse requires system administration privileges to access and track system activity.',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.13.0',
        'NSHumanReadableCopyright': 'Copyright © 2024 Wojciech Tyziniec. All rights reserved.',
    },
)