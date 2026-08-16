param(
    [string]$Version = "2.0.0"
)

# MaskBox 便携版打包脚本（Windows PowerShell）
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "==> Build frontend"
Push-Location frontend
npm ci
npm run typecheck
npm run build
Pop-Location

Write-Host "==> Install runtime dependencies"
python -m pip install -r requirements.txt pyinstaller

Write-Host "==> Run tests"
python -m pytest

Write-Host "==> PyInstaller build"
python -m PyInstaller --noconfirm --clean MaskBox.spec

$DistDir = Join-Path $Root "dist"
$AppDir = Join-Path $DistDir "MaskBox"
$ZipName = "MaskBox-v$Version-windows-portable.zip"
$ZipPath = Join-Path $DistDir $ZipName

if (-not (Test-Path $AppDir)) {
    throw "Build output not found: $AppDir"
}

Write-Host "==> Create $ZipName"
if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
Compress-Archive -Path (Join-Path $AppDir "*") -DestinationPath $ZipPath

$Hash = (Get-FileHash $ZipPath -Algorithm SHA256).Hash.ToLowerInvariant()
"$Hash  $ZipName" | Out-File -Encoding ascii (Join-Path $DistDir "sha256.txt")
Write-Host "SHA256: $Hash"
Write-Host "Artifact: $ZipPath"
