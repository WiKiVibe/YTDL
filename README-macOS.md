# YTDL for macOS
# YTDL macOS 版

The Release package is `YTDL-MAC.zip` for Apple Silicon.
Release 提供的 Apple Silicon 安裝包為 `YTDL-MAC.zip`。

Unzip it, move `YTDL.app` to Applications, then Control-click the app and choose **Open** on first launch.
解壓縮後將 `YTDL.app` 移到「應用程式」，第一次啟動時按住 Control 點擊程式，並選擇「打開」。

The app is ad-hoc signed but not Apple-notarized.
此程式採用臨時簽署，尚未通過 Apple 公證。

The instructions below are for running or rebuilding YTDL from source.
以下內容適用於從原始碼執行或重新建置 YTDL。

## Run from source
## 從原始碼執行

1. Install Python 3.10 to 3.13 from [python.org](https://www.python.org/downloads/macos/) or Homebrew.<br>
   從 [python.org](https://www.python.org/downloads/macos/) 或 Homebrew 安裝 Python 3.10 至 3.13。
2. Open Terminal in this repository folder.<br>
   在本儲存庫資料夾中開啟終端機。
3. Run the following commands.<br>
   執行以下指令。

```sh
chmod +x install.command run.command tools/install_deno_macos.sh
./install.command
./run.command
```

The installer creates a local `.venv`, installs dependencies from `requirements.txt`, and downloads the macOS Deno runtime into `bin/deno`.
安裝程式會建立本機 `.venv`、從 `requirements.txt` 安裝相依套件，並將 macOS 版 Deno 下載至 `bin/deno`。

## Build a native app on a Mac
## 在 Mac 上建置原生 App

Python 3.10 to 3.13 and at least 5 GB of free space are required.
需要 Python 3.10 至 3.13，以及至少 5 GB 的可用空間。

This project uses `flet pack` and PyInstaller for the macOS build.
本專案使用 `flet pack` 與 PyInstaller 建置 macOS 版本。

Xcode, Flutter, and CocoaPods are not required for this build route.
此建置流程不需要 Xcode、Flutter 或 CocoaPods。

```sh
chmod +x build_macos_app.command diagnose_macos_app.command tools/install_deno_macos.sh
./build_macos_app.command
```

The build creates the following files.
建置完成後會產生以下檔案。

```text
dist/macos/YTDL.app
dist/YTDL-MAC.zip
```

For later updates from a Git clone, run `update_and_build_mac.command`.
之後若要從 Git 複本更新，請執行 `update_and_build_mac.command`。

It downloads the latest `origin/main`, preserves local environments, replaces project files, and rebuilds the app.
此程式會下載最新的 `origin/main`、保留本機執行環境、更新專案檔案並重新建置 App。

Flet is pinned to version 0.85.3 so source runs and packaged builds use the same API.
Flet 固定使用 0.85.3，確保原始碼執行與封裝版本使用相同 API。

## Diagnose an empty or black window
## 排查空白或黑畫面

Do not launch the app from Finder while diagnosing.
進行排查時，請勿從 Finder 啟動程式。

Run the diagnostic script instead.
請改為執行診斷腳本。

```sh
./diagnose_macos_app.command
```

The script launches the executable inside the bundle, captures console output, checks signatures and entitlements, and prints the Python startup log after the app closes.
此腳本會啟動 App 內的執行檔、擷取主控台輸出、檢查簽章與權限，並在程式關閉後顯示 Python 啟動紀錄。

Logs are saved in the following location.
紀錄檔會儲存在以下位置。

```text
~/Library/Application Support/YTDL/
```

## Gatekeeper and unidentified developer warnings
## Gatekeeper 與無法識別開發者警告

macOS may block an app downloaded from the internet when it is not Apple-notarized.
未經 Apple 公證的 App 從網路下載後，可能會被 macOS 阻擋。

Use one of the following methods.
可使用以下任一方式處理。

1. Control-click the app, choose **Open**, and confirm **Open**.<br>
   按住 Control 點擊程式，選擇「打開」，再確認「打開」。
2. Open System Settings, go to Privacy & Security, and allow the blocked app.<br>
   開啟「系統設定」的「隱私權與安全性」，允許被阻擋的 App。
3. Advanced users can remove the quarantine attribute.<br>
   進階使用者可移除隔離屬性。

```sh
xattr -dr com.apple.quarantine /path/to/YTDL.app
```

Apple Developer ID signing and notarization provide the best public-distribution experience.
若要提供最佳的公開發佈體驗，建議使用 Apple Developer ID 簽署與公證。

## Notes
## 注意事項

- Settings and yt-dlp cache are stored in `~/Library/Application Support/YTDL`.<br>
  設定與 yt-dlp 快取儲存在 `~/Library/Application Support/YTDL`。
- Some networks or videos may still require YouTube login cookies.<br>
  某些網路環境或影片仍可能需要 YouTube 登入 Cookie。
- The Windows portable ZIP cannot be used on macOS.<br>
  Windows 可攜式 ZIP 無法在 macOS 使用。
