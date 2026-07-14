$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$dist = Join-Path $root "dist"
$zip = Join-Path $dist "YTDL-macOS-source.zip"
$staging = Join-Path $dist "YTDL-macOS"

New-Item -ItemType Directory -Force -Path $dist | Out-Null
$distPath = (Resolve-Path $dist).Path
$stagingPath = [IO.Path]::GetFullPath($staging)
$expectedPrefix = $distPath.TrimEnd("\") + "\"
if (-not $stagingPath.StartsWith($expectedPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to use staging path outside dist: $stagingPath"
}

if (Test-Path $zip) {
    Remove-Item -LiteralPath $zip -Force
}
if (Test-Path $staging) {
    Remove-Item -LiteralPath $staging -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $staging | Out-Null

function Copy-ProjectItem($name) {
    $source = Join-Path $root $name
    if (Test-Path $source) {
        Copy-Item -Path $source -Destination (Join-Path $staging $name) -Recurse
    }
}

@(
    "src",
    "tools",
    "pic",
    "requirements.txt",
    "main.py",
    "install.command",
    "run.command",
    "build_macos_app.command",
    "package_macos.sh",
    "README-macOS.md"
) | ForEach-Object {
    Copy-ProjectItem $_
}

Get-ChildItem -Path $staging -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem -Path $staging -Recurse -File -Filter "*.pyc" | Remove-Item -Force

Compress-Archive -Path $staging -DestinationPath $zip -Force
Remove-Item $staging -Recurse -Force
Write-Host "Created $zip"
