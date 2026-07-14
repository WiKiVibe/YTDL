# YTDL for macOS (experimental)

This is **not** the same as the Windows Release ZIP. There is no one-click Mac download for end users yet.

You need a Mac, Terminal comfort, and Python installed yourself.

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

Requires Xcode Command Line Tools. On the Mac:

```sh
chmod +x build_macos_app.command tools/install_deno_macos.sh
./build_macos_app.command
```

Output is typically under `dist/macos`.

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
