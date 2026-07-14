@echo off
chcp 65001 >nul
setlocal
set "APP_DIR=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$app=(Resolve-Path '%APP_DIR%').Path; $icon=(Join-Path $app 'pic\YTDL_LOGO.ico'); if (-not (Test-Path $icon)) { Write-Host 'Icon not found: ' $icon; exit 1 }; $desktop=[Environment]::GetFolderPath('Desktop'); $lnk=[IO.Path]::Combine($desktop,'YTDL Downloader.lnk'); if (-not (Test-Path $lnk)) { Write-Host 'Shortcut not found: ' $lnk; exit 1 }; $shell=New-Object -ComObject WScript.Shell; $sc=$shell.CreateShortcut($lnk); $sc.IconLocation=$icon + ',0'; $sc.Save(); Write-Host 'Shortcut icon updated.'"
echo.
pause
