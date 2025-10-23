# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path

# Get the current directory
current_dir = Path.cwd()

# Define data files to include
datas = [
    # Main application icon
    ('Waksense.ico', '.'),
    
    # Iop tracker files
    ('Iop/wakfu_iop_resource_tracker.py', 'Iop'),
    ('Iop/positions_config.json', 'Iop'),
    ('Iop/img', 'Iop/img'),
    
    # Cra tracker files  
    ('Cra/wakfu_resource_tracker_fullscreen.py', 'Cra'),
    ('Cra/positions_config.json', 'Cra'),
    ('Cra/img', 'Cra/img'),
    
    # Shared image files
    ('img', 'img'),
]

# Hidden imports for PyQt6 and other dependencies
hiddenimports = [
    'PyQt6.QtCore',
    'PyQt6.QtGui', 
    'PyQt6.QtWidgets',
    'PyQt6.sip',
    'pathlib',
    'json',
    'threading',
    'subprocess',
    're',
    'math',
    'time',
    # Include the tracker modules explicitly
    'Iop.wakfu_iop_resource_tracker',
    'Cra.wakfu_resource_tracker_fullscreen',
]

a = Analysis(
    ['wakfu_class_launcher.py'],
    pathex=[str(current_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'cv2',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Waksense',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='Waksense.ico',
)
