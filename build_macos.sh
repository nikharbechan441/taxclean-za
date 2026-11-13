#!/usr/bin/env bash
# ==============================================================================
# TaxClean ZA - Automated macOS Native .app & .dmg Packaging Script
# Target: macOS 11.0+ (Universal / Apple Silicon M1-M4 & Intel x86_64)
# ==============================================================================
set -e

echo "=== [1/4] Checking Environment & Python Dependencies ==="
python3 -m pip install --upgrade pip
python3 -m pip install pyinstaller customtkinter darkdetect openpyxl pypdf pypdfium2 pdfplumber rapidocr_onnxruntime onnxruntime numpy Pillow

echo "=== [2/4] Compiling Native macOS Bundle with PyInstaller ==="
rm -rf build "dist/TaxClean ZA.app" dist/TaxCleanZA-Mac.dmg dist/TaxCleanZA-macOS.zip
pyinstaller --clean TaxCleanZA_mac.spec

echo "=== [3/4] Creating macOS DMG & ZIP Archives ==="
mkdir -p dist
if command -v hdiutil &> /dev/null; then
    echo "Creating compressed disk image (UDZO)..."
    hdiutil create -volname "TaxClean ZA" -srcfolder "dist/TaxClean ZA.app" -ov -format UDZO "dist/TaxCleanZA-Mac.dmg"
    echo "Generated dist/TaxCleanZA-Mac.dmg"
else
    echo "hdiutil not found (non-macOS environment). Skipping DMG generation."
fi

cd dist
zip -r -q "TaxCleanZA-macOS.zip" "TaxClean ZA.app"
cd ..
echo "Generated dist/TaxCleanZA-macOS.zip"

echo "=== [4/4] macOS Build Complete! ==="
ls -lh dist/TaxCleanZA-Mac* || true
