#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"

if [ "$(uname -s)" != "Darwin" ]; then
    echo "This build script must be run on macOS."
    exit 1
fi

AVAILABLE_KB="$(df -Pk "$APP_DIR" | awk 'NR==2 {print $4}')"
MIN_FREE_KB=$((5 * 1024 * 1024))
if [ -n "$AVAILABLE_KB" ] && [ "$AVAILABLE_KB" -lt "$MIN_FREE_KB" ]; then
    AVAILABLE_GB=$((AVAILABLE_KB / 1024 / 1024))
    echo "Not enough free disk space."
    echo "Available: about ${AVAILABLE_GB} GB; required: at least 5 GB."
    exit 1
fi

PYTHON="$APP_DIR/.venv/bin/python"
if [ ! -x "$PYTHON" ] || ! "$PYTHON" -c "import importlib.metadata as m, yt_dlp, imageio_ffmpeg, PyInstaller; assert m.version('flet') == '0.85.3'" >/dev/null 2>&1; then
    YTDL_SKIP_PAUSE=1 bash "$APP_DIR/install.command"
fi

if [ ! -x "$APP_DIR/bin/deno" ] && [ -f "$APP_DIR/tools/install_deno_macos.sh" ]; then
    bash "$APP_DIR/tools/install_deno_macos.sh"
fi

FLET_CMD="$APP_DIR/.venv/bin/flet"
if [ ! -x "$FLET_CMD" ]; then
    echo "Flet CLI was not found after installation."
    exit 1
fi

mkdir -p "$APP_DIR/assets" "$APP_DIR/dist"
cp -f "$APP_DIR/pic/YTDL_LOGO.png" "$APP_DIR/assets/icon.png"

ICONSET="$APP_DIR/assets/YTDL.iconset"
ICON_ICNS="$APP_DIR/assets/YTDL.icns"
rm -rf "$ICONSET"
mkdir -p "$ICONSET"
for SIZE in 16 32 128 256 512; do
    DOUBLE=$((SIZE * 2))
    sips -z "$SIZE" "$SIZE" "$APP_DIR/pic/YTDL_LOGO.png" --out "$ICONSET/icon_${SIZE}x${SIZE}.png" >/dev/null
    sips -z "$DOUBLE" "$DOUBLE" "$APP_DIR/pic/YTDL_LOGO.png" --out "$ICONSET/icon_${SIZE}x${SIZE}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o "$ICON_ICNS"
rm -rf "$ICONSET"

echo
echo "Building a single-window macOS app with Flet Pack..."
echo "This route packages the working Flet Desktop window directly."
echo

rm -rf "$APP_DIR/dist/macos" "$APP_DIR/build/YTDL"
rm -f "$APP_DIR/YTDL.spec"
mkdir -p "$APP_DIR/dist/macos"

PACK_ARGS=(
    pack
    "$APP_DIR/main.py"
    --name "YTDL"
    --icon "$ICON_ICNS"
    --distpath "$APP_DIR/dist/macos"
    --add-data "$APP_DIR/pic:pic"
    --add-data "$APP_DIR/assets:assets"
    --hidden-import "yt_dlp" "yt_dlp.extractor" "yt_dlp.postprocessor" "imageio_ffmpeg"
    --product-name "YTDL"
    --product-version "1.0.0"
    --bundle-id "app.local.ytdl"
    --copyright "YTDL"
    --yes
    --verbose
)

if [ -x "$APP_DIR/bin/deno" ]; then
    PACK_ARGS+=(--add-binary "$APP_DIR/bin/deno:bin")
fi

"$FLET_CMD" "${PACK_ARGS[@]}"

APP_BUNDLE="$APP_DIR/dist/macos/YTDL.app"
EXECUTABLE="$APP_BUNDLE/Contents/MacOS/YTDL"
if [ ! -x "$EXECUTABLE" ]; then
    echo "Packaging finished but YTDL.app was not created correctly."
    exit 1
fi

plutil -lint "$APP_BUNDLE/Contents/Info.plist"
codesign --force --deep --sign - --timestamp=none "$APP_BUNDLE"
codesign --verify --deep --strict --verbose=2 "$APP_BUNDLE"

echo
echo "Single-window macOS app complete:"
echo "  $APP_BUNDLE"
echo
echo "Open it with:"
echo "  open \"$APP_BUNDLE\""
