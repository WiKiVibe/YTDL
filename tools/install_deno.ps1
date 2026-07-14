$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$bin = Join-Path $root "bin"
$deno = Join-Path $bin "deno.exe"
$zip = Join-Path $bin "deno.zip"
$tmp = Join-Path $bin "deno.zip.tmp"
$url = "https://github.com/denoland/deno/releases/latest/download/deno-x86_64-pc-windows-msvc.zip"

New-Item -ItemType Directory -Force -Path $bin | Out-Null

function Test-Deno($path) {
    if (-not (Test-Path $path)) {
        return $false
    }
    try {
        & $path --version | Out-Null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

if (Test-Deno $deno) {
    Write-Host "Deno already available: $deno"
    exit 0
}

if (Test-Path $tmp) {
    Remove-Item -LiteralPath $tmp -Force
}
if (Test-Path $zip) {
    Remove-Item -LiteralPath $zip -Force
}

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
Write-Host "Downloading Deno JavaScript runtime..."
$downloaded = $false
try {
    Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $tmp
    $downloaded = $true
} catch {
    Write-Host "PowerShell download failed; retrying with curl..."
    $curl = Get-Command curl.exe -ErrorAction SilentlyContinue
    if ($curl) {
        & $curl.Source -L --fail --retry 3 --connect-timeout 20 --ssl-no-revoke -o $tmp $url
        $downloaded = ($LASTEXITCODE -eq 0)
    }
    if (-not $downloaded) {
        Write-Host "curl download failed; retrying with Python..."
        $python = Join-Path $root ".venv\Scripts\python.exe"
        if (-not (Test-Path $python)) {
            $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
            if ($pythonCommand) {
                $python = $pythonCommand.Source
            }
        }
        if (-not (Test-Path $python)) {
            throw "No Python executable available to download Deno."
        }
        $code = @"
import ssl
import sys
import urllib.request

url, output = sys.argv[1], sys.argv[2]
context = ssl._create_unverified_context()
with urllib.request.urlopen(url, timeout=120, context=context) as response:
    with open(output, 'wb') as file:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            file.write(chunk)
"@
        & $python -c $code $url $tmp
        $downloaded = ($LASTEXITCODE -eq 0)
    }
}

if (-not $downloaded) {
    throw "Could not download Deno."
}

$download = Get-Item -LiteralPath $tmp
if ($download.Length -lt 1000000) {
    Remove-Item -LiteralPath $tmp -Force
    throw "Downloaded Deno archive is too small. The network may have returned an error page."
}

Move-Item -LiteralPath $tmp -Destination $zip -Force
Expand-Archive -Path $zip -DestinationPath $bin -Force
Remove-Item -LiteralPath $zip -Force

if (-not (Test-Deno $deno)) {
    throw "Deno was downloaded but did not start correctly."
}

Write-Host "Deno ready: $deno"
