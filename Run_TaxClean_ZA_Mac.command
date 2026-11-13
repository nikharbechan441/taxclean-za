#!/usr/bin/env bash
# ==============================================================================
# TaxClean ZA - macOS Double-Click Finder Launcher (.command)
# Double-click this file from macOS Finder to launch TaxClean ZA locally.
# ==============================================================================
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "=========================================================="
echo " Starting TaxClean ZA - Offline SARS Bank Statement Engine"
echo " Platform: macOS"
echo "=========================================================="

if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    osascript -e 'display alert "Python 3 Required" message "Please install Python 3 from https://python.org to run TaxClean ZA on macOS."'
    exit 1
fi

$PYTHON_CMD -m pip install -q customtkinter darkdetect openpyxl pypdf pypdfium2 rapidocr_onnxruntime onnxruntime numpy Pillow 2>/dev/null || true

exec $PYTHON_CMD TaxCleanDesktop.pyw
