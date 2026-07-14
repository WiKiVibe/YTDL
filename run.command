#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"

PYTHON="$APP_DIR/.venv/bin/python"

if [ ! -x "$PYTHON" ] || ! "$PYTHON" -c "import flet" >/dev/null 2>&1; then
    echo "First run setup is required."
    bash "$APP_DIR/install.command"
fi

if [ ! -x "$APP_DIR/bin/deno" ] && ! command -v deno >/dev/null 2>&1; then
    if [ -f "$APP_DIR/tools/install_deno_macos.sh" ]; then
        bash "$APP_DIR/tools/install_deno_macos.sh" || true
    fi
fi

"$PYTHON" "$APP_DIR/main.py"
