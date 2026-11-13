# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

encodings_datas, encodings_binaries, encodings_hidden = collect_all('encodings')
rapidocr_datas, rapidocr_binaries, rapidocr_hidden = collect_all('rapidocr_onnxruntime')
onnx_datas, onnx_binaries, onnx_hidden = collect_all('onnxruntime')
pdfium_datas, pdfium_binaries, pdfium_hidden = collect_all('pypdfium2')
pdfium_raw_datas, pdfium_raw_binaries, pdfium_raw_hidden = collect_all('pypdfium2_raw')
ctk_datas, ctk_binaries, ctk_hidden = collect_all('customtkinter')

all_datas = [
    ('TaxClean.ico', '.'),
    ('TaxClean_User_Manual.html', '.'),
] + rapidocr_datas + onnx_datas + pdfium_datas + pdfium_raw_datas + ctk_datas + encodings_datas

all_binaries = rapidocr_binaries + onnx_binaries + pdfium_binaries + pdfium_raw_binaries + ctk_binaries + encodings_binaries

all_hidden = list(set([
    'encodings',
    'encodings.utf_8',
    'encodings.cp1252',
    'encodings.latin_1',
    'encodings.ascii',
    'customtkinter',
    'darkdetect',
    'compliance',
    'audit_tools',
    'exporters',
    'licensing',
    'sa_bank_checker',
    'openpyxl',
    'pypdf',
    'pypdfium2',
    'pypdfium2_raw',
    'rapidocr_onnxruntime',
    'onnxruntime',
    'numpy',
    'PIL',
] + rapidocr_hidden + onnx_hidden + pdfium_hidden + pdfium_raw_hidden + ctk_hidden + encodings_hidden))

a = Analysis(
    ['TaxCleanDesktop.pyw'],
    pathex=[],
    binaries=all_binaries,
    datas=all_datas,
    hiddenimports=all_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['torch', 'tensorflow', 'matplotlib', 'scipy'],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TaxCleanZA',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='TaxClean.ico'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='TaxCleanZA'
)
