# build_windows.ps1 — Build Roulette for Windows and package as a ZIP
# Usage: powershell -ExecutionPolicy Bypass -File build_windows.ps1
#
# Output: dist\Roulette-Windows.zip
#         (contains the Roulette\ directory bundle — run Roulette\Roulette.exe)
#
# Requirements:
#   - Python 3.9+ on PATH
#   - pip install -r requirements.txt -r requirements-build.txt

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$AppName    = "Roulette"
$DistDir    = "dist"
$BundleDir  = "$DistDir\$AppName"
$ZipPath    = "$DistDir\$AppName-Windows.zip"

Write-Host "-> Installing build dependencies..."
pip install --quiet pyinstaller

# Ensure icon exists
if (-not (Test-Path "app\assets\icon.png")) {
    Write-Host "-> Generating icon..."
    python app\assets\generate_icon.py
}

Write-Host "-> Building $AppName with PyInstaller..."
pyinstaller roulette.spec --noconfirm

Write-Host "-> Packaging $AppName-Windows.zip..."
if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }

Compress-Archive -Path $BundleDir -DestinationPath $ZipPath

Write-Host ""
Write-Host "Done: $ZipPath"
Write-Host "To run: unzip, then run $AppName\$AppName.exe"
Write-Host ""
Write-Host "Note: mpv will be installed automatically via winget on first launch"
Write-Host "if it is not already present on the system."
