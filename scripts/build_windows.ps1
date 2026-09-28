$ErrorActionPreference = "Stop"
$root = Resolve-Path "$PSScriptRoot\.."
Set-Location $root
Remove-Item build,dist,release -Recurse -Force -ErrorAction SilentlyContinue
python -m PyInstaller --noconfirm packaging\youtube_bulk_downloader.spec
$appDir = Join-Path $root "dist\Pengunduh YouTube Massal"
$tools = Join-Path $appDir "tools"; New-Item -ItemType Directory -Force -Path $tools | Out-Null
$ffZip = Join-Path $env:TEMP "ffmpeg-essentials.zip"; $ffDir = Join-Path $env:TEMP "ffmpeg-essentials"
Invoke-WebRequest "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" -OutFile $ffZip
Remove-Item $ffDir -Recurse -Force -ErrorAction SilentlyContinue; Expand-Archive $ffZip $ffDir -Force
$bin = Get-ChildItem $ffDir -Recurse -Filter ffmpeg.exe | Select-Object -First 1
$probe = Get-ChildItem $ffDir -Recurse -Filter ffprobe.exe | Select-Object -First 1
Copy-Item $bin.FullName (Join-Path $tools "ffmpeg.exe"); Copy-Item $probe.FullName (Join-Path $tools "ffprobe.exe")
New-Item -ItemType Directory -Force -Path (Join-Path $appDir "downloads"),(Join-Path $appDir "data") | Out-Null
Copy-Item README.md (Join-Path $appDir "README.md")
$manifest = @{ app="Pengunduh YouTube Massal"; version="0.2.0"; python=(python --version); built=(Get-Date).ToUniversalTime().ToString("o"); ffmpeg="bundled essentials" } | ConvertTo-Json
Set-Content -Encoding UTF8 (Join-Path $appDir "VERSIONS.json") $manifest
New-Item -ItemType Directory -Force release | Out-Null
Compress-Archive -Path "$appDir\*" -DestinationPath "release\Pengunduh-YouTube-Massal-Windows-portable.zip" -CompressionLevel Optimal
Write-Host "Portable ZIP: $root\release\Pengunduh-YouTube-Massal-Windows-portable.zip"
