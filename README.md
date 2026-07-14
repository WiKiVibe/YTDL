# YTDL

Paste a YouTube URL (or playlist), pick video/audio options, and download. Optional **channel owner CC subtitles** (never YouTube auto-captions).

> Please only download content you have the right to save or use. This project is a front-end for yt-dlp; you are responsible for how you use it.

---

## Two ways to get the app

| Audience | What to use |
|----------|-------------|
| **Most users** | Download the portable **ZIP** from [Releases](https://github.com/WiKiVibe/YTDL/releases) — no Python install needed |
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

## License

MIT — see [`LICENSE`](LICENSE).

Third-party components (yt-dlp, Flet, FFmpeg via imageio-ffmpeg, Deno, etc.) keep their own licenses.

---

## Disclaimer

This software is provided as-is. Site extractors break when platforms change; keep yt-dlp updated. The authors are not responsible for misuse or ToS violations by end users.
