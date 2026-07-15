#!/usr/bin/env bash
set -uo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_BUNDLE="$APP_DIR/dist/macos/YTDL.app"
EXECUTABLE="$APP_BUNDLE/Contents/MacOS/YTDL"
LOG_DIR="$HOME/Library/Application Support/YTDL"
STARTUP_LOG="$LOG_DIR/startup.log"
CONSOLE_LOG="$LOG_DIR/bundle-console.log"

mkdir -p "$LOG_DIR"
rm -f "$STARTUP_LOG" "$CONSOLE_LOG"

echo
echo "YTDL macOS diagnostic launch"
echo "============================"
echo

if [ ! -x "$EXECUTABLE" ]; then
    echo "The packaged executable was not found:"
    echo "  $EXECUTABLE"
    echo
    echo "Build it first with: ./build_macos_app.command"
    read -r -p "Press Return to close. " _
    exit 1
fi

echo "App: $APP_BUNDLE"
echo "macOS: $(sw_vers -productVersion)"
echo "CPU: $(uname -m)"
echo
echo "Bundle signature:"
codesign --verify --deep --strict --verbose=2 "$APP_BUNDLE" 2>&1 || true
echo
echo "Bundle entitlements:"
codesign -d --entitlements :- "$APP_BUNDLE" 2>&1 || true
echo
echo "Launching the real bundle executable. Close the YTDL window to finish."
echo

set +e
"$EXECUTABLE" 2>&1 | tee "$CONSOLE_LOG"
APP_EXIT_CODE=${PIPESTATUS[0]}
set -e

echo
echo "YTDL exit code: $APP_EXIT_CODE"
echo
echo "Python startup log:"
if [ -f "$STARTUP_LOG" ]; then
    cat "$STARTUP_LOG"
else
    echo "(startup.log was not created; Python entrypoint did not run)"
fi
echo
echo "Recent Flet console logs:"
find "$HOME/Library/Application Support" -type f -name "console.log" -mmin -10 -print 2>/dev/null || true
echo
echo "Logs saved in: $LOG_DIR"
read -r -p "Press Return to close. " _
exit "$APP_EXIT_CODE"
