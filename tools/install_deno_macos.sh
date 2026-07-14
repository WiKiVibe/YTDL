#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="$ROOT/bin"
DENO="$BIN/deno"
ZIP="$BIN/deno.zip"

mkdir -p "$BIN"

test_deno() {
    local deno_path="$1"
    [ -x "$deno_path" ] && "$deno_path" --version >/dev/null 2>&1
}

if test_deno "$DENO"; then
    echo "Deno already available: $DENO"
    exit 0
fi

ARCH="$(uname -m)"
case "$ARCH" in
    arm64)
        TARGET="aarch64-apple-darwin"
        ;;
    x86_64)
        TARGET="x86_64-apple-darwin"
        ;;
    *)
        echo "Unsupported macOS architecture: $ARCH" >&2
        exit 1
        ;;
esac

URL="https://github.com/denoland/deno/releases/latest/download/deno-${TARGET}.zip"
TMP="$(mktemp "$BIN/deno.zip.tmp.XXXXXX")"
trap 'rm -f "$TMP" "$ZIP"' EXIT

echo "Downloading Deno JavaScript runtime for $ARCH..."
if command -v curl >/dev/null 2>&1; then
    curl -L --fail --retry 3 --connect-timeout 20 -o "$TMP" "$URL"
elif command -v python3 >/dev/null 2>&1; then
    python3 - "$URL" "$TMP" <<'PY'
import sys
import urllib.request

url, output = sys.argv[1], sys.argv[2]
with urllib.request.urlopen(url, timeout=120) as response:
    with open(output, "wb") as file:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            file.write(chunk)
PY
else
    echo "Neither curl nor python3 is available to download Deno." >&2
    exit 1
fi

SIZE="$(wc -c < "$TMP" | tr -d ' ')"
if [ "${SIZE:-0}" -lt 1000000 ]; then
    echo "Downloaded Deno archive is too small. The network may have returned an error page." >&2
    exit 1
fi

mv "$TMP" "$ZIP"
unzip -o -q "$ZIP" -d "$BIN"
chmod +x "$DENO"
rm -f "$ZIP"

if ! test_deno "$DENO"; then
    echo "Deno was downloaded but did not start correctly." >&2
    exit 1
fi

echo "Deno ready: $DENO"
