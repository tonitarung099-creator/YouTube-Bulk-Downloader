$ErrorActionPreference = "Stop"
$root = Resolve-Path "$PSScriptRoot\.."
Set-Location $root

$distDir = Join-Path $root "dist"
$buildDir = Join-Path $root "build"
$releaseDir = Join-Path $root "release"
$zipPath = Join-Path $releaseDir "Pengunduh-YouTube-Massal-Windows-portable.zip"

# Bersihkan semua lokasi build yang mungkin dipakai PyInstaller agar pencarian kandidat tidak pernah mengambil hasil lama.
$legacyBuild = Join-Path $root "packaging\build"
$legacyDist = Join-Path $root "packaging\dist"
Remove-Item $buildDir,$distDir,$releaseDir,$legacyBuild,$legacyDist -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $distDir,$buildDir,$releaseDir | Out-Null

python -m PyInstaller --noconfirm --clean --distpath $distDir --workpath $buildDir packaging\youtube_bulk_downloader.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller gagal dengan kode $LASTEXITCODE." }

# Jangan berasumsi lokasi folder hasil. Cari EXE yang baru saja dibuat lalu jadikan foldernya root portable.
$exeCandidates = @(Get-ChildItem $root -Recurse -Filter "Pengunduh YouTube Massal.exe" -File -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notmatch "\\release\\" } |
    Sort-Object LastWriteTimeUtc -Descending)
if ($exeCandidates.Count -eq 0) {
    $tree = @(Get-ChildItem $root -Recurse -Depth 4 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)
    throw "EXE hasil PyInstaller tidak ditemukan. Pohon build: $($tree -join '; ')"
}
$appExe = $exeCandidates[0].FullName
$appDir = $exeCandidates[0].Directory.FullName
$runtimeDir = Join-Path $appDir "_internal"
Write-Host "PyInstaller app root: $appDir"
Write-Host "PyInstaller exe: $appExe"
if (-not (Test-Path $runtimeDir -PathType Container)) {
    $children = @(Get-ChildItem $appDir -Force -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Name)
    throw "Runtime _internal tidak ditemukan di '$appDir'. Isi: $($children -join ', ')"
}

$tools = Join-Path $appDir "tools"
New-Item -ItemType Directory -Force -Path $tools | Out-Null

# FFmpeg/ffprobe untuk merge video+audio dan konversi audio.
$ffZip = Join-Path $env:TEMP "ffmpeg-essentials.zip"; $ffDir = Join-Path $env:TEMP "ffmpeg-essentials"
Invoke-WebRequest "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" -OutFile $ffZip
Remove-Item $ffDir -Recurse -Force -ErrorAction SilentlyContinue; Expand-Archive $ffZip $ffDir -Force
$bin = Get-ChildItem $ffDir -Recurse -Filter ffmpeg.exe | Select-Object -First 1
$probe = Get-ChildItem $ffDir -Recurse -Filter ffprobe.exe | Select-Object -First 1
if (-not $bin -or -not $probe) { throw "FFmpeg/ffprobe tidak ditemukan di arsip build." }
Copy-Item $bin.FullName (Join-Path $tools "ffmpeg.exe"); Copy-Item $probe.FullName (Join-Path $tools "ffprobe.exe")

# Deno sebagai JS runtime yt-dlp untuk dukungan YouTube modern.
$denoZip = Join-Path $env:TEMP "deno-windows.zip"; $denoDir = Join-Path $env:TEMP "deno-windows"
Invoke-WebRequest "https://github.com/denoland/deno/releases/latest/download/deno-x86_64-pc-windows-msvc.zip" -OutFile $denoZip
Remove-Item $denoDir -Recurse -Force -ErrorAction SilentlyContinue; New-Item -ItemType Directory -Force -Path $denoDir | Out-Null
Expand-Archive $denoZip $denoDir -Force
$deno = Get-ChildItem $denoDir -Recurse -Filter deno.exe | Select-Object -First 1
if (-not $deno) { throw "deno.exe tidak ditemukan di arsip build." }
Copy-Item $deno.FullName (Join-Path $tools "deno.exe")

# Folder writable portable tetap hadir setelah extract.
$downloadsDir = Join-Path $appDir "downloads"; $dataDir = Join-Path $appDir "data"
New-Item -ItemType Directory -Force -Path $downloadsDir,$dataDir | Out-Null
Set-Content -Encoding UTF8 (Join-Path $downloadsDir ".keep") "Folder hasil unduhan portable."
Set-Content -Encoding UTF8 (Join-Path $dataDir ".keep") "Folder data aplikasi portable."

Copy-Item README.md (Join-Path $appDir "README.md") -Force
$denoVersion = (& (Join-Path $tools "deno.exe") --version | Select-Object -First 1)
$manifest = @{ app="Pengunduh YouTube Massal"; version="0.2.0"; python=(python --version); built=(Get-Date).ToUniversalTime().ToString("o"); ffmpeg="bundled essentials"; deno=$denoVersion; yt_dlp=(python -c "import yt_dlp; print(yt_dlp.version.__version__)") } | ConvertTo-Json
Set-Content -Encoding UTF8 (Join-Path $appDir "VERSIONS.json") $manifest

Compress-Archive -Path "$appDir\*" -DestinationPath $zipPath -CompressionLevel Optimal
if (-not (Test-Path $zipPath -PathType Leaf)) { throw "ZIP portable gagal dibuat." }

# Verifikasi arsip final yang benar-benar diterima pengguna.
$verifyDir = Join-Path $env:TEMP "youtube-bulk-portable-verify"
Remove-Item $verifyDir -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive $zipPath $verifyDir -Force
$required = @(
    "Pengunduh YouTube Massal.exe",
    "_internal",
    "tools\ffmpeg.exe",
    "tools\ffprobe.exe",
    "tools\deno.exe",
    "downloads\.keep",
    "data\.keep",
    "README.md",
    "VERSIONS.json"
)
foreach ($relative in $required) {
    $target = Join-Path $verifyDir $relative
    if (-not (Test-Path $target)) { throw "Portable ZIP tidak lengkap: '$relative' tidak ditemukan." }
}
$exeSize = (Get-Item (Join-Path $verifyDir "Pengunduh YouTube Massal.exe")).Length
$runtimeFiles = @(Get-ChildItem (Join-Path $verifyDir "_internal") -Recurse -File).Count
if ($exeSize -lt 100000) { throw "EXE portable terlalu kecil/tidak valid: $exeSize byte." }
if ($runtimeFiles -lt 10) { throw "Runtime portable tampak tidak lengkap: hanya $runtimeFiles file." }

# Jalankan tool yang dibundel dari hasil ekstrak, bukan dari PATH runner.
$verifiedTools = Join-Path $verifyDir "tools"
& (Join-Path $verifiedTools "ffmpeg.exe") -version | Select-Object -First 1 | Write-Host
if ($LASTEXITCODE -ne 0) { throw "ffmpeg.exe bundled gagal dijalankan." }
& (Join-Path $verifiedTools "ffprobe.exe") -version | Select-Object -First 1 | Write-Host
if ($LASTEXITCODE -ne 0) { throw "ffprobe.exe bundled gagal dijalankan." }
& (Join-Path $verifiedTools "deno.exe") --version | Select-Object -First 1 | Write-Host
if ($LASTEXITCODE -ne 0) { throw "deno.exe bundled gagal dijalankan." }

# Smoke-test EXE hasil ZIP: aplikasi GUI harus berhasil start dan tetap hidup beberapa detik.
$verifiedExe = Join-Path $verifyDir "Pengunduh YouTube Massal.exe"
$smoke = Start-Process -FilePath $verifiedExe -PassThru
Start-Sleep -Seconds 4
$smoke.Refresh()
if ($smoke.HasExited) { throw "EXE portable keluar terlalu cepat saat smoke test. ExitCode=$($smoke.ExitCode)" }
Stop-Process -Id $smoke.Id -Force
$smoke.WaitForExit()

# Uji end-to-end nyata: metadata YouTube -> download <=360p -> FFmpeg/Deno portable -> file media.
python scripts\e2e_youtube_test.py --tools-dir $verifiedTools
if ($LASTEXITCODE -ne 0) { throw "Uji end-to-end YouTube gagal dengan kode $LASTEXITCODE." }

Write-Host "Portable tervalidasi: EXE=$exeSize byte, runtime files=$runtimeFiles, GUI smoke test=OK, YouTube E2E=OK"
Write-Host "Portable ZIP: $zipPath"
