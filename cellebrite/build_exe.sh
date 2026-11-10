#!/usr/bin/env bash
# ------------------------------------------------------------------------------
# AUTHOR:         kalink0
# MAIL:           kalinko@be-binary.de
# CREATION DATE:  2026-11-10
#
# LICENSE:        CC0-1.0
#
# SOURCE:         https://github.com/kalink0/useful_scripts
#
# TITLE:          build_exe.sh
#
# DESCRIPTION:    Build a Linux executable of sauce.py - pyinstaller
#                   dist/sauce  (GUI without arguments, CLI with arguments)
#
# KNOWN RESTRICTIONS:
#                 Python 3.8+ with tkinter (Debian/Ubuntu: apt install python3-tk python3-venv)
#                 The binary needs a glibc >= the one of the build system:
#                 build on the oldest distribution it has to run on.
#
# USAGE EXAMPLE:  ./build_exe.sh
# ------------------------------------------------------------------------------
set -euo pipefail
cd "$(dirname "$0")"
VENV_DIR=".venv-build"

python3 -c "import tkinter" || { echo "[ERROR] tkinter missing (e.g. apt install python3-tk)"; exit 1; }

if [ ! -x "$VENV_DIR/bin/python" ]; then
    echo "[1/3] Creating build venv..."
    python3 -m venv "$VENV_DIR"
fi

echo "[2/3] Installing / checking PyInstaller..."
"$VENV_DIR/bin/python" -m pip install --quiet --upgrade pyinstaller -r requirements.txt

echo "[3/3] Building executable..."
"$VENV_DIR/bin/pyinstaller" --noconfirm --clean --onefile --collect-all tkinterdnd2 --name sauce sauce.py

echo
echo "[OK] Done: $(pwd)/dist/sauce"
