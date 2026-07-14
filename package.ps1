$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

try {
    [Net.ServicePointManager]::SecurityProtocol =
        [Net.SecurityProtocolType]::Tls12 -bor [Net.SecurityProtocolType]::Tls13
} catch {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
}

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$dist = Join-Path $root "dist"
$zip = Join-Path $dist "YTDL-GUI.zip"
$staging = Join-Path $dist "YTDL"
$appStaging = Join-Path $staging "app"
$cacheDir = Join-Path $root "cache"
$pythonVersion = "3.14.6"
$pythonEmbedName = "python-$pythonVersion-embed-amd64.zip"
$pythonEmbedUrl = "https://www.python.org/ftp/python/$pythonVersion/$pythonEmbedName"
$pythonEmbedCache = Join-Path $cacheDir $pythonEmbedName
$venvSitePackages = Join-Path $root ".venv\Lib\site-packages"
$portableSitePackages = Join-Path $root "python\Lib\site-packages"
$venvPython = Join-Path $root ".venv\Scripts\python.exe"
$sourceSitePackages = $null
# Prefer a working portable tree, then a working venv.
if (Test-Path $portableSitePackages) {
    $sourceSitePackages = $portableSitePackages
    Write-Host "Using portable python site-packages: $sourceSitePackages"
} elseif ((Test-Path $venvSitePackages) -and (Test-Path $venvPython)) {
    $sourceSitePackages = $venvSitePackages
    Write-Host "Using venv site-packages: $sourceSitePackages"
} elseif (Test-Path $venvSitePackages) {
    $sourceSitePackages = $venvSitePackages
    Write-Host "Using venv site-packages (python may be broken): $sourceSitePackages"
}

New-Item -ItemType Directory -Force -Path $dist | Out-Null
$distPath = (Resolve-Path $dist).Path
$stagingPath = [IO.Path]::GetFullPath($staging)
$expectedPrefix = $distPath.TrimEnd("\") + "\"
if (-not $stagingPath.StartsWith($expectedPrefix, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to use staging path outside dist: $stagingPath"
}

function Remove-DistChild($name) {
    $target = Join-Path $dist $name
    if (-not (Test-Path $target)) {
        return
    }
    $targetPath = [IO.Path]::GetFullPath($target)
    if (-not $targetPath.StartsWith($expectedPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove path outside dist: $targetPath"
    }
    Remove-Item -LiteralPath $targetPath -Recurse -Force
}

function Write-TextFile($path, $content) {
    $parent = Split-Path -Parent $path
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    Set-Content -LiteralPath $path -Value $content -Encoding UTF8
}

function Save-Download($url, $path) {
    if (Test-Path $path) {
        if ((Get-Item -LiteralPath $path).Length -gt 0) {
            return
        }
        Remove-Item -LiteralPath $path -Force
    }

    $parent = Split-Path -Parent $path
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    Write-Host "Downloading $url"

    try {
        Invoke-WebRequest -Uri $url -OutFile $path
        if ((Get-Item -LiteralPath $path).Length -gt 0) {
            return
        }
    } catch {
        if (Test-Path $path) {
            Remove-Item -LiteralPath $path -Force
        }
        Write-Host "PowerShell download failed; trying Python downloader..."
    }

    $localPython = Join-Path $root ".venv\Scripts\python.exe"
    if (-not (Test-Path $localPython)) {
        throw "Local .venv Python was not found. Run install.bat on this build machine first."
    }

    $downloadCode = "import sys, urllib.request; urllib.request.urlretrieve(sys.argv[1], sys.argv[2])"
    & $localPython -c $downloadCode $url $path
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $path) -or (Get-Item -LiteralPath $path).Length -eq 0) {
        throw "Could not download $url. You can download it manually to $path, then run package.ps1 again."
    }
}

function Enable-EmbeddedPythonSitePackages($pythonDir) {
    $pth = Get-ChildItem -LiteralPath $pythonDir -Filter "python*._pth" -File | Select-Object -First 1
    if (-not $pth) {
        $zip = Get-ChildItem -LiteralPath $pythonDir -Filter "python*.zip" -File | Select-Object -First 1
        if (-not $zip) {
            throw "Embedded Python path file and python zip were not found in $pythonDir"
        }
        $pthPath = Join-Path $pythonDir ([IO.Path]::GetFileNameWithoutExtension($zip.Name) + "._pth")
        Write-TextFile $pthPath (($zip.Name, ".", "Lib\site-packages", "import site") -join [Environment]::NewLine)
        $pth = Get-Item -LiteralPath $pthPath
    }

    $lines = @(Get-Content -LiteralPath $pth.FullName)
    $out = @()
    $hasSitePackages = $false
    $hasImportSite = $false
    foreach ($line in $lines) {
        if ($line -eq "Lib\site-packages") {
            $hasSitePackages = $true
        }
        if ($line -eq "#import site" -or $line -eq "import site") {
            if (-not $hasImportSite) {
                $out += "import site"
            }
            $hasImportSite = $true
        } else {
            $out += $line
        }
    }
    if (-not $hasSitePackages) {
        $out += "Lib\site-packages"
    }
    if (-not $hasImportSite) {
        $out += "import site"
    }
    Set-Content -LiteralPath $pth.FullName -Value $out -Encoding ASCII
}

function New-Zip($sourceDir, $zipPath) {
    Add-Type -AssemblyName System.IO.Compression
    Add-Type -AssemblyName System.IO.Compression.FileSystem

    if (Test-Path $zipPath) {
        Remove-Item -LiteralPath $zipPath -Force
    }

    $sourceFull = [IO.Path]::GetFullPath($sourceDir).TrimEnd("\")
    $baseFull = [IO.Path]::GetFullPath((Split-Path -Parent $sourceFull)).TrimEnd("\")
    $archive = [IO.Compression.ZipFile]::Open($zipPath, [IO.Compression.ZipArchiveMode]::Create)
    try {
        $files = Get-ChildItem -LiteralPath $sourceFull -Recurse -File -Force
        foreach ($file in $files) {
            $rel = $file.FullName.Substring($baseFull.Length).TrimStart("\").Replace("\", "/")
            $entry = $archive.CreateEntry($rel, [IO.Compression.CompressionLevel]::Optimal)
            $entry.LastWriteTime = $file.LastWriteTime
            $input = [IO.File]::OpenRead($file.FullName)
            try {
                $output = $entry.Open()
                try {
                    $input.CopyTo($output)
                } finally {
                    $output.Dispose()
                }
            } finally {
                $input.Dispose()
            }
        }
    } finally {
        $archive.Dispose()
    }
}

if (-not (Test-Path $sourceSitePackages)) {
    throw "Missing $sourceSitePackages. Run install.bat on this build machine first."
}

Save-Download $pythonEmbedUrl $pythonEmbedCache

Remove-DistChild "YTDL"
if (Test-Path $staging) {
    Remove-Item -LiteralPath $staging -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $appStaging | Out-Null

Write-TextFile (Join-Path $staging "01.Install.bat") ((
    "@echo off",
    "chcp 65001 >nul",
    "set ""APP_DIR=%~dp0app\""",
    "if not exist ""%APP_DIR%run.vbs"" (",
    "    echo Missing app files. Please unzip the whole folder again.",
    "    pause",
    "    exit /b 1",
    ")",
    "call ""%APP_DIR%install.bat"""
) -join [Environment]::NewLine)

Write-TextFile (Join-Path $staging "02.RUN.bat") ((
    "@echo off",
    "set ""APP_DIR=%~dp0app\""",
    "if not exist ""%APP_DIR%run.vbs"" (",
    "    echo Missing app files. Please unzip the whole folder again.",
    "    pause",
    "    exit /b 1",
    ")",
    "wscript.exe ""%APP_DIR%run.vbs"""
) -join [Environment]::NewLine)

$shareReadme = Join-Path $root "README-share.txt"
if (Test-Path $shareReadme) {
    Copy-Item -LiteralPath $shareReadme -Destination (Join-Path $staging "README.txt")
}

Copy-Item -LiteralPath (Join-Path $root "src") -Destination (Join-Path $appStaging "src") -Recurse
Copy-Item -LiteralPath (Join-Path $root "pic") -Destination (Join-Path $appStaging "pic") -Recurse
Copy-Item -LiteralPath (Join-Path $root "tools") -Destination (Join-Path $appStaging "tools") -Recurse
Copy-Item -LiteralPath (Join-Path $root "bin") -Destination (Join-Path $appStaging "bin") -Recurse
Copy-Item -LiteralPath (Join-Path $root "runtime") -Destination (Join-Path $appStaging "runtime") -Recurse
Copy-Item -LiteralPath (Join-Path $root "requirements.txt") -Destination (Join-Path $appStaging "requirements.txt")
Copy-Item -LiteralPath (Join-Path $root "install.bat") -Destination (Join-Path $appStaging "install.bat")
Copy-Item -LiteralPath (Join-Path $root "run.bat") -Destination (Join-Path $appStaging "run.bat")
Copy-Item -LiteralPath (Join-Path $root "run.vbs") -Destination (Join-Path $appStaging "run.vbs")

$pythonStaging = Join-Path $appStaging "python"
Expand-Archive -LiteralPath $pythonEmbedCache -DestinationPath $pythonStaging -Force
Enable-EmbeddedPythonSitePackages $pythonStaging

$targetSitePackages = Join-Path $pythonStaging "Lib\site-packages"
New-Item -ItemType Directory -Force -Path $targetSitePackages | Out-Null
Write-Host "Copying installed Python packages..."
Get-ChildItem -LiteralPath $sourceSitePackages -Force | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination $targetSitePackages -Recurse -Force
}

Get-ChildItem -LiteralPath $staging -Recurse -Directory -Filter "__pycache__" -Force | Remove-Item -Recurse -Force
Get-ChildItem -LiteralPath $staging -Recurse -File -Filter "*.pyc" -Force | Remove-Item -Force

New-Zip $staging $zip
Remove-Item -LiteralPath $staging -Recurse -Force
Write-Host "Created $zip"
