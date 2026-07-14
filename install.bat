@echo off
chcp 65001 >nul
setlocal

set "APP_DIR=%~dp0"
cd /d "%APP_DIR%"

echo.
echo YTDL Downloader installer
echo =========================
echo.

echo [1/3] Checking portable app files...
if not exist "%APP_DIR%python\python.exe" (
    echo Missing bundled Python: %APP_DIR%python\python.exe
    echo Please unzip the full ZIP package again before installing.
    pause
    exit /b 1
)
if not exist "%APP_DIR%python\pythonw.exe" (
    echo Missing bundled Python launcher: %APP_DIR%python\pythonw.exe
    echo Please unzip the full ZIP package again before installing.
    pause
    exit /b 1
)
if not exist "%APP_DIR%src\ytdl_gui.py" (
    echo Missing app source files.
    echo Please unzip the full ZIP package again before installing.
    pause
    exit /b 1
)

echo [2/3] Checking bundled Python packages...
"%APP_DIR%python\python.exe" -c "import flet, yt_dlp, imageio_ffmpeg"
if errorlevel 1 (
    echo Bundled Python packages are incomplete.
    echo Please unzip the full ZIP package again before installing.
    pause
    exit /b 1
)

echo [3/3] Creating desktop shortcut...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $app=(Resolve-Path '%APP_DIR%').Path; $shell=New-Object -ComObject WScript.Shell; $desktop=[Environment]::GetFolderPath('Desktop'); $shortcut=$shell.CreateShortcut([IO.Path]::Combine($desktop,'YTDL Downloader.lnk')); $shortcut.TargetPath=(Join-Path $env:SystemRoot 'System32\wscript.exe'); $shortcut.Arguments='\"' + (Join-Path $app 'run.vbs') + '\"'; $shortcut.WorkingDirectory=$app; $icon=(Join-Path $app 'pic\YTDL_LOGO.ico'); if (Test-Path $icon) { $shortcut.IconLocation=$icon + ',0' } else { $shortcut.IconLocation=(Join-Path $env:SystemRoot 'System32\shell32.dll') + ',220' }; $shortcut.Save()"
if errorlevel 1 (
    echo Desktop shortcut could not be created. You can still use 02.RUN.bat.
    pause
    exit /b 1
)

echo.
echo Install complete. You can launch YTDL Downloader from the desktop shortcut or 02.RUN.bat.
echo.
pause
