#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"

PYTHON="$APP_DIR/.venv/bin/python"

echo
echo "YTDL (macOS)"
echo "============"
echo "App dir: $APP_DIR"
echo

if [ ! -x "$PYTHON" ]; then
    echo "Missing .venv. Running install.command first..."
    YTDL_SKIP_PAUSE=1 bash "$APP_DIR/install.command"
fi

if ! "$PYTHON" -c "import flet" >/dev/null 2>&1; then
    echo "Flet not installed in .venv. Running install.command..."
    YTDL_SKIP_PAUSE=1 bash "$APP_DIR/install.command"
fi

if [ ! -x "$APP_DIR/bin/deno" ] && ! command -v deno >/dev/null 2>&1; then
    if [ -f "$APP_DIR/tools/install_deno_macos.sh" ]; then
        echo "Preparing Deno..."
        bash "$APP_DIR/tools/install_deno_macos.sh" || true
    fi
fi

echo "Python: $("$PYTHON" -c 'import sys; print(sys.version.split()[0])')"
echo "Flet:   $("$PYTHON" -c 'import flet; print(getattr(flet, "__version__", "?"))' 2>/dev/null || echo '?')"
echo
echo "Starting GUI..."
echo

set +e
"$PYTHON" "$APP_DIR/main.py"
CODE=$?
set -e

echo
if [ "$CODE" -ne 0 ]; then
    echo "YTDL exited with error code $CODE."
    echo
    echo "Common fixes:"
    echo "  1) Re-run:  ./install.command"
    echo "  2) Paste the FULL terminal output above when asking for help."
    echo "  3) Try:     $PYTHON -c \"import flet; print(flet.__version__)\""
else
    echo "YTDL closed normally."
fi

if [ "${YTDL_SKIP_PAUSE:-0}" != "1" ] && [ -t 0 ]; then
    echo
    read -r -p "Press Return to close this window. " _
fi

exit "$CODE"
