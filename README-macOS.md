# YTDL Downloader for macOS

This package can run as a Python/Flet app on macOS, or be built into a native
`.app` bundle on a Mac.

## Run on macOS

1. Install Python 3.10 or newer.
2. Open Terminal in this folder.
3. Run:

```sh
chmod +x install.command run.command tools/install_deno_macos.sh
./install.command
./run.command
```

The installer creates a local `.venv`, installs `yt-dlp`, Flet and FFmpeg
support, and downloads a matching macOS Deno runtime into `bin/deno`.

## Build a native `.app`

Native macOS app bundles must be built on macOS with Xcode Command Line Tools.
On the Mac, run:

```sh
chmod +x build_macos_app.command tools/install_deno_macos.sh
./build_macos_app.command
```

The app bundle will be written under `dist/macos`.

## Notes

- The app stores macOS settings and yt-dlp cache under
  `~/Library/Application Support/YTDL Downloader`.
- A `cookies.txt` file can still be placed next to the app folder if YouTube
  asks for sign-in verification.
- For distribution outside your own Mac, Apple signing/notarization may still
  be required.
