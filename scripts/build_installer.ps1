# Buduje EXE + instalator Windows (Inno Setup)
# Wymaga: Python 3.11+, Inno Setup 6 (ISCC.exe)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "=== OCR Studio — build release ===" -ForegroundColor Cyan

# Wersja z config.py
$Version = python -c "from src.config import APP_VERSION; print(APP_VERSION)"
Write-Host "Wersja: $Version"

Write-Host "`n[1/2] Budowanie EXE (PyInstaller)..." -ForegroundColor Yellow
python -m pip install -r requirements.txt -q
python -m pip install -r requirements-build.txt -q
python build_exe.py
if ($LASTEXITCODE -ne 0) { throw "Blad budowania EXE." }

$ExePath = Join-Path $Root "dist\OCR Studio.exe"
if (-not (Test-Path $ExePath)) {
    throw "Brak pliku: $ExePath"
}
Write-Host "OK: $ExePath" -ForegroundColor Green

Write-Host "`n[2/2] Budowanie instalatora (Inno Setup)..." -ForegroundColor Yellow
$IsccCandidates = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
)
$Iscc = $IsccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $Iscc) {
    Write-Host "UWAGA: Nie znaleziono Inno Setup 6." -ForegroundColor Red
    Write-Host "Pobierz: https://jrsoftware.org/isdl.php" -ForegroundColor Yellow
    Write-Host "EXE jest gotowe w dist\ — instalator zbudujesz po instalacji Inno Setup." -ForegroundColor Yellow
    exit 0
}

& $Iscc "installer\OCR_Studio_Setup.iss" "/DMyAppVersion=$Version"
if ($LASTEXITCODE -ne 0) { throw "Blad budowania instalatora." }

$SetupPath = Join-Path $Root "installer\output\OCR_Studio_Setup_$Version.exe"
Write-Host "`nGOTOWE:" -ForegroundColor Green
Write-Host "  EXE:      dist\OCR Studio.exe"
Write-Host "  Setup:    $SetupPath"
