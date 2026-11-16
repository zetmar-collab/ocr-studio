# Buduje aplikacje (onedir), sprawdza ja testem dymnym, pakuje wersje przenosna (.zip)
# i instalator Windows (Inno Setup).
# Wymaga: Python 3.12, zainstalowanego Tesseract 5.3.1 (zrodlo wbudowanego silnika),
#         Inno Setup 6 (ISCC.exe) - opcjonalnie, bez niego powstaje tylko .zip.

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "=== Studio OCR - build release ===" -ForegroundColor Cyan

$Version = python -c "from src.config import APP_VERSION; print(APP_VERSION)"
Write-Host "Wersja: $Version"

Write-Host "`n[1/5] Zaleznosci i zasoby wbudowane..." -ForegroundColor Yellow
python -m pip install -r requirements.txt -r requirements-build.txt -q
python scripts\vendor_tesseract.py
if ($LASTEXITCODE -ne 0) { throw "Blad przygotowania silnika OCR." }
python scripts\vendor_dictionaries.py
if ($LASTEXITCODE -ne 0) { throw "Blad przygotowania slownikow." }

Write-Host "`n[2/5] Budowanie aplikacji (PyInstaller --onedir)..." -ForegroundColor Yellow
python build_exe.py
if ($LASTEXITCODE -ne 0) { throw "Blad budowania aplikacji." }

$AppDir = Join-Path $Root "dist\OCR Studio"
$ExePath = Join-Path $AppDir "OCR Studio.exe"
if (-not (Test-Path $ExePath)) { throw "Brak pliku: $ExePath" }

Write-Host "`n[3/5] Test dymny zbudowanej aplikacji (--selftest)..." -ForegroundColor Yellow
$Report = Join-Path $Root "dist\selftest.json"
# PATH bez katalogow Tesseract: aplikacja musi uzyc WBUDOWANEGO silnika.
$OriginalPath = $env:PATH
$env:PATH = ($env:PATH -split ";" | Where-Object { $_ -notmatch "Tesseract" }) -join ";"
try {
    $Process = Start-Process -FilePath $ExePath -ArgumentList "--selftest", "`"$Report`"" -Wait -PassThru
} finally {
    $env:PATH = $OriginalPath
}
if ($Process.ExitCode -ne 0) {
    Get-Content $Report -ErrorAction SilentlyContinue | Write-Host
    throw "Test dymny nie przeszedl (kod $($Process.ExitCode))."
}
Write-Host "OK: aplikacja dziala bez Tesseract w systemie" -ForegroundColor Green

Write-Host "`n[4/5] Wersja przenosna (.zip)..." -ForegroundColor Yellow
$ZipPath = Join-Path $Root "dist\StudioOCR_${Version}_portable.zip"
if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
Compress-Archive -Path $AppDir -DestinationPath $ZipPath -CompressionLevel Optimal
Write-Host "OK: $ZipPath" -ForegroundColor Green

Write-Host "`n[5/5] Budowanie instalatora (Inno Setup)..." -ForegroundColor Yellow
$Iscc = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $Iscc) {
    Write-Host "UWAGA: Nie znaleziono Inno Setup 6 (https://jrsoftware.org/isdl.php)." -ForegroundColor Red
    Write-Host "Wersja przenosna jest gotowa: $ZipPath" -ForegroundColor Yellow
    exit 0
}

& $Iscc "installer\OCR_Studio_Setup.iss" "/DMyAppVersion=$Version"
if ($LASTEXITCODE -ne 0) { throw "Blad budowania instalatora." }

Write-Host "`nGOTOWE:" -ForegroundColor Green
Write-Host "  Przenosna: $ZipPath"
Write-Host "  Instalator: installer\output\OCR_Studio_Setup_$Version.exe"
