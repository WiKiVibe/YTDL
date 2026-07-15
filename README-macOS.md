# YTDL for macOS

The Release package is `YTDL-MAC.zip` for Apple Silicon. Unzip it, move
`YTDL.app` to Applications, then Control-click the app and choose **Open** on
first launch. The app is ad-hoc signed but not Apple-notarized.

The instructions below are for running or rebuilding YTDL from source.

## Run from source

1. Install Python 3.10 or newer (from [python.org](https://www.python.org/downloads/macos/) or Homebrew).
2. Open Terminal in this repo folder.
3. Run:

```sh
chmod +x install.command run.command tools/install_deno_macos.sh
./install.command
./run.command
```

The installer creates a local `.venv`, installs dependencies from `requirements.txt`, and downloads a macOS Deno runtime into `bin/deno`.

## Build a native `.app` (on a Mac)

Requires Python 3.10 or newer and at least 5 GB of free space. This project
uses `flet pack` / PyInstaller for macOS because it packages the working Flet
Desktop window directly and does not create a second serious_python/Flutter
host window. Xcode, Flutter and CocoaPods are not used by this build route.

On the Mac:

```sh
chmod +x build_macos_app.command diagnose_macos_app.command tools/install_deno_macos.sh
./build_macos_app.command
```

The build creates:

```text
dist/macos/YTDL.app
dist/YTDL-MAC.zip
```

For later updates from a Git clone, run `update_and_build_mac.command`. It
fetches `origin/main`, replaces the local tracked files, and rebuilds the app.

Flet is pinned to 0.85.3 so source runs and packaged builds use the same API.

The installer includes Flet Desktop and PyInstaller. The finished `.app`
contains one Flet Desktop window and no separate embedded Flutter host.

## Diagnose an empty or black window

Do not launch the app from Finder while diagnosing. Run:

```sh
./diagnose_macos_app.command
```

This launches the executable inside the bundle, captures its console output,
checks the signature and entitlements, and prints the Python startup log after
the app closes. Logs are saved in:

```text
~/Library/Application Support/YTDL/
```

### Gatekeeper / “unidentified developer”

If you open an unsigned `.app` downloaded from the internet, macOS may block it.

**Workaround (per user, not ideal for public distribution):**

1. Right-click (or Control-click) the app → **Open** → confirm **Open**, or  
2. System Settings → Privacy & Security → allow the blocked app, or  
3. Remove quarantine after download (advanced):  
   `xattr -dr com.apple.quarantine /path/to/YTDL.app`

Better long-term options (for real distribution):

| Approach | Notes |
|----------|--------|
| **Unsigned + “Open” workaround** | OK for friends / self-test; bad for strangers |
| **Apple Developer ID + notarize** | Best UX; paid Apple Developer Program (~US$99/year) |
| **Source-only (this folder)** | No `.app` Gatekeeper issue; users run via Terminal |

## Notes

- Settings and yt-dlp cache: `~/Library/Application Support/YTDL`
- YouTube may still require login/cookies on some networks
- Windows portable ZIP **cannot** be used on Mac
