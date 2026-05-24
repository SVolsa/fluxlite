# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['fluxlite\\__main__.py'],
    pathex=[],
    binaries=[],
    datas=[('fluxlite', 'fluxlite')],
    hiddenimports=['fluxlite', 'fluxlite.main', 'fluxlite.app', 'fluxlite.commands', 'fluxlite.console', 'fluxlite.config', 'fluxlite.context', 'fluxlite.i18n', 'fluxlite.startup', 'fluxlite.styles', 'fluxlite.wizard', 'fluxlite.plugin_api', 'fluxlite.plugin_manager', 'fluxlite.profile', 'fluxlite.memory', 'fluxlite.mcp_client', 'fluxlite.tools', 'fluxlite.provider'],
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
    name='fluxlite',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['logo_256x256.ico'],
)
