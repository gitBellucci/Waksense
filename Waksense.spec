# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

import sys
import os
from pathlib import Path

# Get the directory where this spec file is located (use current working directory)
spec_file_dir = Path.cwd()

# Data files to include
datas = [
    # Main launcher icon
    (str(spec_file_dir / 'Waksense.ico'), '.'),
    
    # Log deduplicator module (needed at runtime)
    (str(spec_file_dir / 'log_deduplicator.py'), '.'),
    
    # Tracker modules (needed for --iop and --cra arguments)
    (str(spec_file_dir / 'Iop' / 'wakfu_iop_resource_tracker.py'), 'Iop'),
    (str(spec_file_dir / 'Cra' / 'wakfu_resource_tracker_fullscreen.py'), 'Cra'),
    
    # Breed icons
    (str(spec_file_dir / 'img' / 'breedsicons'), 'img/breedsicons'),
    
    # Iop images
    (str(spec_file_dir / 'Iop' / 'img'), 'Iop/img'),
    
    # Cra images
    (str(spec_file_dir / 'Cra' / 'img'), 'Cra/img'),
]

# Hidden imports
hiddenimports = [
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'win32gui',
    'win32process',
    'psutil',
    'log_deduplicator',
    'Iop.wakfu_iop_resource_tracker',
    'Cra.wakfu_resource_tracker_fullscreen',
]

a = Analysis(
    [str(spec_file_dir / 'wakfu_class_launcher.py')],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Waksense',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # Disable UPX to avoid compression issues
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(spec_file_dir / 'Waksense.ico'),  # Application icon
    onefile=True,  # Single executable file
)

