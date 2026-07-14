#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"

echo
echo "YTDL macOS installer"
echo "================================"
echo

if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="$(command -v python3)"
else
    echo "Python 3 was not found. Please install Python 3.10 or newer first:"
    echo "https://www.python.org/downloads/macos/"
    exit 1
fi

"$PYTHON_CMD" - <<'PY'
import sys

if sys.version_info < (3, 10):
    raise SystemExit("Python 3.10 or newer is required.")
PY

echo "[1/5] Creating local Python environment..."
"$PYTHON_CMD" -m venv "$APP_DIR/.venv"

PYTHON="$APP_DIR/.venv/bin/python"

echo "[2/5] Updating installer tools..."
"$PYTHON" -m pip install --upgrade pip

echo "[3/5] Installing yt-dlp, Flet and media tools..."
"$PYTHON" -m pip install --upgrade -r "$APP_DIR/requirements.txt"

echo "[4/5] Preparing Deno JavaScript runtime..."
if [ -f "$APP_DIR/tools/install_deno_macos.sh" ]; then
    bash "$APP_DIR/tools/install_deno_macos.sh" || {
        echo "Warning: Deno could not be prepared. YouTube may require sign-in verification."
    }
fi

echo "[5/5] Preparing launch scripts..."
chmod +x "$APP_DIR/run.command" "$APP_DIR/install.command" 2>/dev/null || true
if [ -f "$APP_DIR/build_macos_app.command" ]; then
    chmod +x "$APP_DIR/build_macos_app.command" 2>/dev/null || true
fi
if [ -f "$APP_DIR/tools/install_deno_macos.sh" ]; then
    chmod +x "$APP_DIR/tools/install_deno_macos.sh" 2>/dev/null || true
fi

echo
echo "Install complete. You can launch YTDL with run.command."
echo

if [ "${YTDL_SKIP_PAUSE:-0}" != "1" ] && [ -t 0 ]; then
    read -r -p "Press Return to close this window. " _
fi
