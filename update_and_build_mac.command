#!/usr/bin/env bash
# One-shot: sync from GitHub + rebuild macOS .app
# Usage:
#   double-click this file, or:
#   ./update_and_build_mac.command
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"

echo
echo "YTDL macOS — update + build"
echo "==========================="
echo "Folder: $APP_DIR"
echo

if ! command -v git >/dev/null 2>&1; then
  echo "git not found. Install Xcode Command Line Tools first."
  read -r -p "Press Return to close. " _
  exit 1
fi

echo "[1/4] Fetch GitHub..."
git fetch origin

echo "[2/4] Reset to origin/main (discards local uncommitted changes)..."
git reset --hard origin/main

echo "[3/5] chmod scripts..."
chmod +x \
  build_macos_app.command \
  run.command \
  install.command \
  update_and_build_mac.command \
  tools/install_deno_macos.sh 2>/dev/null || true

echo "[4/5] Clear Flet extract cache (prevents stale black-screen builds)..."
# Flet runs code from here, NOT only from this git folder:
#   ~/Library/Application Support/app.local.ytdl/flet/app/main.pyc
rm -rf "${HOME}/Library/Application Support/app.local.ytdl" 2>/dev/null || true
rm -f "${HOME}/Library/Application Support/YTDL/startup.log" 2>/dev/null || true
echo "    cleared app.local.ytdl (if it existed)"

echo "[5/5] Build macOS app (this can take several minutes)..."
echo "Keep external SSD mounted if Xcode lives there."
echo
./build_macos_app.command

echo
echo "Done."
if [ -d "$APP_DIR/dist/macos" ]; then
  echo "Output:"
  ls -la "$APP_DIR/dist/macos" || true
  echo
  echo "Open with:"
  echo "  open \"$APP_DIR/dist/macos\"/*.app"
fi
echo
read -r -p "Press Return to close. " _
