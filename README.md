# YTDL

Windows-first GUI for [yt-dlp](https://github.com/yt-dlp/yt-dlp), built with [Flet](https://flet.dev/).

Paste a YouTube URL (or playlist), pick video/audio options, and download. Optional **channel owner CC subtitles** (never YouTube auto-captions).

> Please only download content you have the right to save or use. This project is a front-end for yt-dlp; you are responsible for how you use it.

---

## Two ways to get the app

| Audience | What to use |
|----------|-------------|
| **Most users** | Download the portable **ZIP** from [GitHub Releases](../../releases) — no Python install needed |
| **Developers** | Clone this repo and run from source (see below) |

Release ZIPs are built with `package.ps1` and are **not** stored in git history.

---

## For users (Release ZIP)

1. Open the latest **Release** and download `YTDL-GUI.zip`.
2. Unzip the whole folder (do not run files from inside the ZIP window).
3. Run `01.Install.bat` once (creates a desktop shortcut).
4. Later use the desktop shortcut or `02.RUN.bat`.

Details: [`README-share.txt`](README-share.txt) (copied into the ZIP as `README.txt`).

---

## For developers (from source)

### Requirements

- Windows 10/11 (primary)
- Python 3.11+ recommended (3.12–3.14 also fine)
- Network on first setup (packages + optional Deno)

### Setup

```bat
git clone <your-repo-url> YTDL
cd YTDL
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Optional: put Deno at `bin\deno.exe` (or rely on PATH). The app also ships tooling under `tools/`.

### Run

```bat
run.bat
```

Or:

```bat
.venv\Scripts\pythonw.exe src\ytdl_gui.py
```

If you use the **embedded** `python\` folder (from a previous portable install or local copy), `run.vbs` will prefer:

```text
python\pythonw.exe  +  src\ytdl_gui.py
```

### Features (high level)

- Video: AUTO / 4K / HD, optional H.264 or AV1
- Audio: WAV / MP3 / AAC (320k target for MP3/AAC)
- 4K + H.264: download best source then transcode (NVENC when available)
- Optional: download **uploader/official CC** as SRT (`writesubtitles`, never auto-subs)
- Optional: on startup, check GitHub Releases for a newer app version (toast only)
- Settings: output folder, open folder when done, NVENC preference, …

Update check needs `GITHUB_REPO = "owner/repo"` and `APP_VERSION` in `src/ytdl_gui.py` (see `RELEASE.md`).

Default save location: Windows Downloads folder. Filenames get a `_YTDL` suffix.

---

## Building a Release ZIP (Windows)

On a machine that already has a working `.venv` with `requirements.txt` installed, and local `bin\` + `runtime\` for the portable layout:

```powershell
# 1) Dev env ready
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2) Ensure Flet desktop runtime + Deno exist for packaging
#    (runtime\ and bin\ are gitignored; produce them on the build machine)

# 3) Package
.\package.ps1
```

Output:

```text
dist\YTDL-GUI.zip
```

Then on GitHub:

1. **Releases** → **Draft a new release**
2. Tag e.g. `v1.0.0`
3. Upload `dist\YTDL-GUI.zip`
4. Publish

Do **not** commit `dist/`, `python/`, or `runtime/` to the repository.

### What the ZIP contains

```text
YTDL/
  01.Install.bat
  02.RUN.bat
  README.txt
  app/
    python/          # embedded Python + site-packages
    runtime/flet/    # Flet desktop runtime
    bin/             # Deno (YouTube JS challenges)
    src/             # application code
    pic/             # icons & background
    run.vbs / run.bat / install.bat
```

---

## Repository layout

```text
src/ytdl_gui.py      # main GUI + download logic
main.py              # alternate entry (import package style)
requirements.txt
package.ps1          # Windows portable ZIP builder
run.bat / run.vbs    # launch helpers
install.bat          # portable install (shortcut)
pic/                 # branding assets
tools/               # Deno install helpers, Flet branding helper
README-share.txt     # end-user notes for the ZIP
README-macOS.md      # experimental macOS notes
```

Local-only (gitignored): `.venv/`, `python/`, `runtime/`, `bin/`, `dist/`, `cache/`, `settings.json`.

---

## macOS

Experimental / source-based. See [`README-macOS.md`](README-macOS.md).

---

## License

MIT — see [`LICENSE`](LICENSE).

Third-party components (yt-dlp, Flet, FFmpeg via imageio-ffmpeg, Deno, etc.) keep their own licenses.

---

## Disclaimer

This software is provided as-is. Site extractors break when platforms change; keep yt-dlp updated. The authors are not responsible for misuse or ToS violations by end users.
