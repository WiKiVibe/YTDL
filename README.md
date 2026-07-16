# YTDL

Desktop GUI for [yt-dlp](https://github.com/yt-dlp/yt-dlp). Paste a YouTube URL or playlist, choose video/audio options, and download.
以 [yt-dlp](https://github.com/yt-dlp/yt-dlp) 為核心的桌面圖形介面。貼上 YouTube 網址或播放清單，選擇影音格式後即可下載。

Optional channel-owner CC subtitles are supported. YouTube auto-generated captions are never downloaded by this option.
可選擇下載頻道主提供的 CC 字幕；此選項不會下載 YouTube 自動產生的字幕。

> Please only download content you have the right to save or use. You are responsible for how you use this software.
> 請只下載您有權儲存或使用的內容。您必須自行負責本軟體的使用方式。

---

## Download for Windows
## Windows 下載方式

1. Open [Releases](https://github.com/WiKiVibe/YTDL/releases) and download **YTDL-WIN.zip**.<br>
   開啟 [Releases](https://github.com/WiKiVibe/YTDL/releases)，下載 **YTDL-WIN.zip**。
2. Unzip the entire folder. Do not run files directly inside the ZIP preview window.<br>
   完整解壓縮資料夾，請勿直接在 ZIP 預覽視窗內執行檔案。
3. Run `01.Install.bat` once to create a desktop shortcut.<br>
   第一次使用時執行一次 `01.Install.bat`，建立桌面捷徑。
4. Later, launch YTDL from the desktop shortcut or `02.RUN.bat`.<br>
   之後可從桌面捷徑或 `02.RUN.bat` 啟動 YTDL。

**Requirements:** Windows 10/11 (64-bit). The Release ZIP includes its own Python runtime.
**系統需求：** Windows 10/11（64 位元）。Release ZIP 已包含獨立的 Python 執行環境。

---

## Download for macOS Apple Silicon
## macOS Apple Silicon 下載方式

1. Open [Releases](https://github.com/WiKiVibe/YTDL/releases) and download **YTDL-MAC.zip**.<br>
   開啟 [Releases](https://github.com/WiKiVibe/YTDL/releases)，下載 **YTDL-MAC.zip**。
2. Unzip it and move `YTDL.app` to Applications.<br>
   解壓縮後，將 `YTDL.app` 移到「應用程式」資料夾。
3. On first launch, Control-click `YTDL.app`, choose **Open**, and confirm **Open**.<br>
   第一次啟動時，按住 Control 點擊 `YTDL.app`，選擇「打開」，再確認「打開」。

The current macOS build is ad-hoc signed but not Apple-notarized.
目前 macOS 版本採用臨時簽署，尚未通過 Apple 公證。

Advanced source-build and troubleshooting instructions are available in [`README-macOS.md`](README-macOS.md).
進階的原始碼建置與疑難排解說明請參閱 [`README-macOS.md`](README-macOS.md)。

---

## Features
## 功能

- Video downloads: AUTO / 4K / HD, with optional H.264 or AV1.<br>
  影片下載：AUTO／4K／HD，可選擇 H.264 或 AV1。
- Audio downloads: WAV / MP3 / AAC.<br>
  音訊下載：WAV／MP3／AAC。
- Optional uploader/official CC subtitles in SRT format, without YouTube auto-captions.<br>
  可選擇下載上傳者／官方提供的 SRT CC 字幕，不含 YouTube 自動字幕。
- Optional update checks through GitHub Releases.<br>
  可選擇透過 GitHub Releases 檢查新版程式。

---

## Support this project
## 贊助這個專案

If YTDL saves you time, you can support WiKiVibe through the Sponsor button near the top-right area of this repository.
如果 YTDL 幫你節省了時間，可以使用本儲存庫右上方附近的 Sponsor 按鈕贊助 WiKiVibe。

You can also scan the QR code or open the [WiKiVibe support page](https://portaly.cc/WiKiVibe).
也可以掃描下方 QR Code，或直接開啟 [WiKiVibe 贊助頁面](https://portaly.cc/WiKiVibe)。

[![Support WiKiVibe QR code](pic/portaly_wikivibe.png)](https://portaly.cc/WiKiVibe)

---

## Run from source
## 從原始碼執行

Install Python 3.10 to 3.13, clone this repository, and run the installer for your operating system.
安裝 Python 3.10 至 3.13，複製本儲存庫後，執行對應作業系統的安裝程式。

```powershell
# Windows
.\install.bat
.\run.bat
```

```sh
# macOS
chmod +x install.command run.command
./install.command
./run.command
```

---

## License
## 授權

YTDL is released under the MIT License. See [`LICENSE`](LICENSE).
YTDL 採用 MIT 授權，詳情請參閱 [`LICENSE`](LICENSE)。

Third-party components such as yt-dlp, Flet, imageio-ffmpeg, FFmpeg, and Deno retain their own licenses.
yt-dlp、Flet、imageio-ffmpeg、FFmpeg 與 Deno 等第三方元件，仍適用各自的授權條款。

---

## Disclaimer
## 免責聲明

This software is provided as-is. Website changes may temporarily break extractors or downloads.
本軟體依現況提供。網站改版可能暫時導致解析或下載功能失效。

The authors are not responsible for misuse or violations of platform terms by end users.
作者不對使用者的不當使用或違反平台服務條款之行為負責。
