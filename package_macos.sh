#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIST="$APP_DIR/dist"
STAGING="$DIST/YTDL-macOS"
ZIP="$DIST/YTDL-macOS-source.zip"

mkdir -p "$DIST"
rm -rf "$STAGING" "$ZIP"
mkdir -p "$STAGING"

copy_item() {
    local item="$1"
    if [ -e "$APP_DIR/$item" ]; then
        cp -R "$APP_DIR/$item" "$STAGING/$item"
    fi
}

copy_item "src"
copy_item "tools"
copy_item "pic"
copy_item "requirements.txt"
copy_item "main.py"
copy_item "install.command"
copy_item "run.command"
copy_item "build_macos_app.command"
copy_item "README-macOS.md"

chmod +x "$STAGING/install.command" "$STAGING/run.command" "$STAGING/build_macos_app.command" 2>/dev/null || true
chmod +x "$STAGING/tools/install_deno_macos.sh" 2>/dev/null || true

find "$STAGING" -type d -name "__pycache__" -prune -exec rm -rf {} +
find "$STAGING" -type f -name "*.pyc" -delete

(
    cd "$DIST"
    zip -r -q "$(basename "$ZIP")" "$(basename "$STAGING")"
)

rm -rf "$STAGING"
echo "Created $ZIP"
