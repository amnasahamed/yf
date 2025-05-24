# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['/Users/amnasahamed/Documents/Personal/trading/yfinance/stock_analyzer.py'],
    pathex=[],
    binaries=[],
    datas=[],
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
    name='StockAnalyzer',
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
    icon=['/Users/amnasahamed/Documents/Personal/trading/yfinance/5b3152ff8ceaa9c3785b95cc460d7826_vks7YnXDRo.icns'],
)
app = BUNDLE(
    exe,
    name='StockAnalyzer.app',
    icon='/Users/amnasahamed/Documents/Personal/trading/yfinance/5b3152ff8ceaa9c3785b95cc460d7826_vks7YnXDRo.icns',
    bundle_identifier=None,
)
