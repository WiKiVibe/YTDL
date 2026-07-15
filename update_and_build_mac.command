#!/usr/bin/env bash
# One-shot: sync from GitHub + rebuild macOS .app
# Usage:
#   double-click this file, or:
#   ./update_and_build_mac.command
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"

echo
echo "YTDL macOS - update + build"
echo "==========================="
echo "Folder: $APP_DIR"
echo

if [ -d "$APP_DIR/.git" ]; then
  if ! command -v git >/dev/null 2>&1; then
    echo "git not found. Install Xcode Command Line Tools first."
    read -r -p "Press Return to close. " _
    exit 1
  fi

  echo "[1/5] Fetch GitHub..."
  git fetch origin

  echo "[2/5] Reset to origin/main (discards local uncommitted changes)..."
  git reset --hard origin/main
else
  if ! command -v curl >/dev/null 2>&1 || ! command -v ditto >/dev/null 2>&1; then
    echo "curl and ditto are required to update this source ZIP folder."
    read -r -p "Press Return to close. " _
    exit 1
  fi

  TEMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/ytdl-update.XXXXXX")"
  trap 'rm -rf "$TEMP_DIR"' EXIT

  echo "[1/5] Download GitHub main branch..."
  curl -fL "https://github.com/WiKiVibe/YTDL/archive/refs/heads/main.zip" \
    -o "$TEMP_DIR/main.zip"
  mkdir -p "$TEMP_DIR/unpacked"
  ditto -x -k "$TEMP_DIR/main.zip" "$TEMP_DIR/unpacked"
  SOURCE_DIR="$TEMP_DIR/unpacked/YTDL-main"
  if [ ! -d "$SOURCE_DIR" ]; then
    echo "Downloaded archive did not contain YTDL-main."
    exit 1
  fi

  echo "[2/5] Install latest source while preserving local environments..."
  for ITEM in \
    .gitignore \
    README-macOS.md \
    build_macos_app.command \
    diagnose_macos_app.command \
    install.command \
    main.py \
    package_macos.ps1 \
    package_macos.sh \
    pic \
    pyproject.toml \
    requirements.txt \
    run.command \
    src \
    tools; do
    if [ -e "$SOURCE_DIR/$ITEM" ]; then
      rm -rf "$APP_DIR/$ITEM"
      ditto "$SOURCE_DIR/$ITEM" "$APP_DIR/$ITEM"
    fi
  done

  # Replace the running updater by renaming a new inode over it.
  ditto "$SOURCE_DIR/update_and_build_mac.command" \
    "$APP_DIR/.update_and_build_mac.command.new"
  chmod +x "$APP_DIR/.update_and_build_mac.command.new"
  mv -f "$APP_DIR/.update_and_build_mac.command.new" \
    "$APP_DIR/update_and_build_mac.command"
fi

echo "[3/5] chmod scripts..."
chmod +x \
  build_macos_app.command \
  diagnose_macos_app.command \
  run.command \
  install.command \
  update_and_build_mac.command \
  tools/install_deno_macos.sh 2>/dev/null || true

echo "[4/5] Clear obsolete Flet extract cache..."
rm -rf "${HOME}/Library/Application Support/app.local.ytdl" 2>/dev/null || true
rm -f "${HOME}/Library/Application Support/YTDL/startup.log" 2>/dev/null || true

echo "[5/5] Build macOS app (this can take several minutes)..."
echo "Packaging the single Flet Desktop window with PyInstaller."
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
