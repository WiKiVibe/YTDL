#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"

if [ "$(uname -s)" != "Darwin" ]; then
    echo "This build script must be run on macOS."
    exit 1
fi

if ! command -v xcodebuild >/dev/null 2>&1; then
    echo "Xcode Command Line Tools are required. Run: xcode-select --install"
    exit 1
fi

PYTHON="$APP_DIR/.venv/bin/python"
if [ ! -x "$PYTHON" ] || ! "$PYTHON" -c "import flet, yt_dlp, imageio_ffmpeg" >/dev/null 2>&1; then
    YTDL_SKIP_PAUSE=1 bash "$APP_DIR/install.command"
fi

if [ ! -x "$APP_DIR/bin/deno" ] && [ -f "$APP_DIR/tools/install_deno_macos.sh" ]; then
    bash "$APP_DIR/tools/install_deno_macos.sh" || true
fi

mkdir -p "$APP_DIR/assets"
cp -f "$APP_DIR/pic/YTDL_LOGO.png" "$APP_DIR/assets/icon.png"
cp -f "$APP_DIR/pic/YTDL_LOGO.png" "$APP_DIR/assets/icon_macos.png"

FLET_CMD="$APP_DIR/.venv/bin/flet"
if [ ! -x "$FLET_CMD" ]; then
    if command -v flet >/dev/null 2>&1; then
        FLET_CMD="$(command -v flet)"
    else
        echo "Flet CLI was not found after installation."
        exit 1
    fi
fi

mkdir -p "$APP_DIR/dist"

"$FLET_CMD" build macos "$APP_DIR" \
    --module-name main \
    --project ytdl_downloader \
    --artifact "YTDL Downloader" \
    --product "YTDL Downloader" \
    --description "YouTube downloader GUI" \
    --org "app.local" \
    --company "YTDL Downloader" \
    --copyright "YTDL Downloader" \
    --build-version "1.0.0" \
    --build-number "1" \
    --arch arm64 x64 \
    --output "$APP_DIR/dist/macos" \
    --exclude ".venv" \
    --exclude "dist" \
    --exclude "build" \
    --exclude "runtime" \
    --exclude "cache" \
    --exclude "downloads" \
    --exclude ".git" \
    --exclude ".agents" \
    --exclude ".codex" \
    --exclude "__pycache__" \
    --exclude "*.pyc" \
    --macos-entitlements "com.apple.security.app-sandbox=false" \
    --macos-entitlements "com.apple.security.network.client=true" \
    --macos-entitlements "com.apple.security.files.user-selected.read-write=true" \
    --macos-entitlements "com.apple.security.files.downloads.read-write=true" \
    --clear-cache \
    --yes

echo
echo "macOS app build complete: $APP_DIR/dist/macos"
