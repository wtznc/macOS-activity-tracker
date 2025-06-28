# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Activity Tracker macOS app bundle.
"""

import sys
from pathlib import Path

# Get the project root directory
project_root = Path(SPECPATH).resolve()
src_path = project_root / 'src'

block_cipher = None

a = Analysis(
    ['src/activity_tracker/__main__.py'],
    pathex=[str(src_path)],
    binaries=[],
    datas=[
        # Include any data files if needed
        # ('src/activity_tracker/data', 'activity_tracker/data'),
    ],
    hiddenimports=[
        # PyObjC frameworks that might not be auto-detected
        'objc',
        'Foundation',
        'AppKit',
        'Cocoa',
        'Quartz',
        'CoreFoundation',
        # Activity tracker modules
        'activity_tracker.menu_bar',
        'activity_tracker.core',
        'activity_tracker.daemon',
        'activity_tracker.sync',
        'activity_tracker.activity_monitor',
        'activity_tracker.config',
        'activity_tracker.data_aggregator',
        'activity_tracker.detection',
        'activity_tracker.http_sync',
        'activity_tracker.storage',
        'activity_tracker.utils',
        # Required system modules
        'psutil',
        'requests',
        'json',
        'sqlite3',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary modules to reduce bundle size
        'tkinter',
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
        'PIL',
        'cv2',
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
    name='ActivityTracker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window for GUI app
    disable_windowed_traceback=False,
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
    name='ActivityTracker',
)

app = BUNDLE(
    coll,
    name='Activity Tracker.app',
    icon=None,  # Add icon path here if you have one: 'path/to/icon.icns'
    bundle_identifier='com.wtznc.activity-tracker',
    version='1.0.2',
    info_plist={
        'CFBundleName': 'Activity Tracker',
        'CFBundleDisplayName': 'Activity Tracker',
        'CFBundleGetInfoString': 'Activity Tracker - macOS Usage Tracking',
        'CFBundleIdentifier': 'com.wtznc.activity-tracker',
        'CFBundleVersion': '1.0.2',
        'CFBundleShortVersionString': '1.0.2',
        'CFBundlePackageType': 'APPL',
        'CFBundleSignature': '????',
        'LSUIElement': True,  # Hide from dock (menu bar app)
        'LSMinimumSystemVersion': '10.14',
        'NSHighResolutionCapable': True,
        'NSHumanReadableCopyright': 'Copyright © 2025 Wojciech Tyziniec. MIT License.',
        'NSAppleEventsUsageDescription': 'Activity Tracker needs to access application information to track your usage.',
        'NSSystemAdministrationUsageDescription': 'Activity Tracker needs system access to monitor application usage.',
        'NSAppleScriptEnabled': False,
        'LSBackgroundOnly': False,
    },
)