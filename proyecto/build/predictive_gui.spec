# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis([
    'c:\\Users\\elpro\\Documents\\Github\\Proyecto-Starwing\\proyecto\\v2.1\\6_Predictive_Maintenance.py',
],
    pathex=['.'],
    binaries=[],
    datas=[
        ('c:\\Users\\elpro\\Documents\\Github\\Proyecto-Starwing\\proyecto\\logs_tiempo_real.csv', 'proyecto'),
        ('c:\\Users\\elpro\\Documents\\Github\\Proyecto-Starwing\\proyecto\\v2.1\\bitacora_mantenimiento.csv', 'proyecto'),
    ],
    hiddenimports=['tkcalendar'],
    hookspath=[],
    hooksconfig={},
)

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='PredictiveMaintenance',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False )

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='PredictiveMaintenance')
