# YTDL

Windows GUI for [yt-dlp](https://github.com/yt-dlp/yt-dlp). Paste a YouTube URL (or playlist), pick video/audio options, and download. Optional **channel owner CC subtitles** (never YouTube auto-captions).

> Please only download content you have the right to save or use. This project is a front-end for yt-dlp; you are responsible for how you use it.

---

## Download (Windows)

1. Open [Releases](https://github.com/WiKiVibe/YTDL/releases) and download **YTDL-GUI.zip**.
2. Unzip the whole folder (do not run files from inside the ZIP window).
3. Run `01.Install.bat` once (creates a desktop shortcut).
4. Later use the desktop shortcut or `02.RUN.bat`.

More detail is in the ZIP as `README.txt`.

**Requirements:** Windows 10/11 (64-bit). No separate Python install needed for the Release ZIP.

---

## macOS

There is **no portable Mac download** in Releases yet (no `.app` / `.dmg`).

- End users on Mac: **not supported** as a one-click install today.
- Developers who already use Terminal may try the experimental scripts in the repo (`install.command` / `run.command`; see [`README-macOS.md`](README-macOS.md)). This requires installing Python yourself and is not the same experience as the Windows ZIP.

A dedicated Mac build / distribution path is under consideration; it is not ready for general download.

---

## Features

- Video: AUTO / 4K / HD, optional H.264 or AV1
- Audio: WAV / MP3 / AAC
- Optional uploader/official CC subtitles (SRT), never YouTube auto-captions
- Optional check for newer app versions via GitHub Releases

---

## License

MIT — see [`LICENSE`](LICENSE).

Third-party components (yt-dlp, Flet, FFmpeg via imageio-ffmpeg, Deno, etc.) keep their own licenses.

---

## Disclaimer

This software is provided as-is. Site extractors break when platforms change. The authors are not responsible for misuse or ToS violations by end users.
