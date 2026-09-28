$ErrorActionPreference = "Stop"
$root = Resolve-Path "$PSScriptRoot\.."
Set-Location $root
Remove-Item build,dist,release -Recurse -Force -ErrorAction SilentlyContinue
python -m PyInstaller --noconfirm packaging\youtube_bulk_downloader.spec
$appDir = Join-Path $root "dist\Pengunduh YouTube Massal"
$tools = Join-Path $appDir "tools"; New-Item -ItemType Directory -Force -Path $tools | Out-Null

# FFmpeg/ffprobe untuk merge video+audio dan konversi audio.
$ffZip = Join-Path $env:TEMP "ffmpeg-essentials.zip"; $ffDir = Join-Path $env:TEMP "ffmpeg-essentials"
Invoke-WebRequest "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" -OutFile $ffZip
Remove-Item $ffDir -Recurse -Force -ErrorAction SilentlyContinue; Expand-Archive $ffZip $ffDir -Force
$bin = Get-ChildItem $ffDir -Recurse -Filter ffmpeg.exe | Select-Object -First 1
$probe = Get-ChildItem $ffDir -Recurse -Filter ffprobe.exe | Select-Object -First 1
if (-not $bin -or -not $probe) { throw "FFmpeg/ffprobe tidak ditemukan di arsip build." }
Copy-Item $bin.FullName (Join-Path $tools "ffmpeg.exe"); Copy-Item $probe.FullName (Join-Path $tools "ffprobe.exe")

# Deno direkomendasikan yt-dlp sebagai JS runtime untuk dukungan YouTube penuh.
$denoZip = Join-Path $env:TEMP "deno-windows.zip"; $denoDir = Join-Path $env:TEMP "deno-windows"
Invoke-WebRequest "https://github.com/denoland/deno/releases/latest/download/deno-x86_64-pc-windows-msvc.zip" -OutFile $denoZip
Remove-Item $denoDir -Recurse -Force -ErrorAction SilentlyContinue; New-Item -ItemType Directory -Force -Path $denoDir | Out-Null
Expand-Archive $denoZip $denoDir -Force
$deno = Get-ChildItem $denoDir -Recurse -Filter deno.exe | Select-Object -First 1
if (-not $deno) { throw "deno.exe tidak ditemukan di arsip build." }
Copy-Item $deno.FullName (Join-Path $tools "deno.exe")

New-Item -ItemType Directory -Force -Path (Join-Path $appDir "downloads"),(Join-Path $appDir "data") | Out-Null
Copy-Item README.md (Join-Path $appDir "README.md")
$denoVersion = (& (Join-Path $tools "deno.exe") --version | Select-Object -First 1)
$manifest = @{ app="Pengunduh YouTube Massal"; version="0.2.0"; python=(python --version); built=(Get-Date).ToUniversalTime().ToString("o"); ffmpeg="bundled essentials"; deno=$denoVersion; yt_dlp=(python -c "import yt_dlp; print(yt_dlp.version.__version__)") } | ConvertTo-Json
Set-Content -Encoding UTF8 (Join-Path $appDir "VERSIONS.json") $manifest
New-Item -ItemType Directory -Force release | Out-Null
Compress-Archive -Path "$appDir\*" -DestinationPath "release\Pengunduh-YouTube-Massal-Windows-portable.zip" -CompressionLevel Optimal
Write-Host "Portable ZIP: $root\release\Pengunduh-YouTube-Massal-Windows-portable.zip"
