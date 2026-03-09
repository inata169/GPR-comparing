# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Excludes: remove 'tkinter' stuff here because viewer needs it!
excludes = [
    'PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'wx',
    'mkl', 'libopenblas', 
    'pytest', 'IPython', 'notebook', 'jedi', 'docutils',
    # 'scipy.sparse', 'scipy.stats', 'scipy.optimize', 'scipy.integrate',
    # 'scipy.fft', 'scipy.spatial', 'scipy.cluster', 'scipy.signal',
    # 'scipy.io',
    'matplotlib.backends.backend_qt5agg', 'matplotlib.backends.backend_qt5',
    'matplotlib.backends.backend_qt6agg', 'matplotlib.backends.backend_qt6',
    'matplotlib.backends.backend_pyside2', 'matplotlib.backends.backend_pyside6',
    'matplotlib.backends.backend_wxagg', 'matplotlib.backends.backend_wx',
    'matplotlib.backends.backend_gtk3agg', 'matplotlib.backends.backend_gtk3',
    'matplotlib.backends.backend_gtk4agg', 'matplotlib.backends.backend_gtk4',
    'pandas', 'notebook', 'nbformat', 'nbconvert'
]

# Selective SciPy inclusion to keep size down
hidden_scipy = [
    'scipy.ndimage',
    'scipy.special',
    'scipy.special._cdflib',
    'scipy.linalg',
    'scipy._lib',
    'scipy._lib.array_api_compat.numpy',
    'scipy._lib.array_api_compat.common',
]
data_scipy = []

a = Analysis(
    ['scripts\\gamma_viewer.py'],
    pathex=[],
    binaries=[],
    datas=data_scipy,
    hiddenimports=[
        'matplotlib', 
        'matplotlib.pyplot',
        'matplotlib.backends.backend_tkagg', 
        'matplotlib.backends.backend_agg',
        'tkinter',
        'numba', 
        'pydicom', 
        'sqlite3',
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
        'PIL._imaging',
        'rtgamma.gamma', 
        'rtgamma.io_dicom', 
        'rtgamma.mask', 
        'rtgamma.optimize', 
        'rtgamma.report', 
        'rtgamma.resample',
        'rtgamma.pdf_report',
        'reportlab'
    ] + hidden_scipy,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
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
    name='gamma_viewer',
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
    name='gamma_viewer',
)
