# Buduje pakiet MSIX (Studio OCR) do przeslania w Partner Center.
# Wymaga: Python 3.11+, Windows 10 SDK (makeappx.exe, makepri.exe).
#
# Uzycie:
#   .\scripts\build_msix.ps1            # buduje .msix (bez podpisu — do wgrania w Partner Center)
#   .\scripts\build_msix.ps1 -Sign      # dodatkowo podpisuje certyfikatem testowym (do lokalnego sideload)

param(
    [switch]$Sign
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "=== Studio OCR - build MSIX ===" -ForegroundColor Cyan

$Version = python -c "from src.config import APP_VERSION; print(APP_VERSION)"
$PackageVersion = "$Version.0"
Write-Host "Wersja aplikacji: $Version (pakiet: $PackageVersion)"

Write-Host "`n[1/4] Instalacja zaleznosci..." -ForegroundColor Yellow
python -m pip install -r requirements.txt -q
python -m pip install -r requirements-build.txt -q

Write-Host "`n[2/4] Budowanie aplikacji (PyInstaller --onedir)..." -ForegroundColor Yellow
python build_exe.py --onedir
if ($LASTEXITCODE -ne 0) { throw "Blad budowania aplikacji." }

$AppDir = Join-Path $Root "dist\OCR Studio"
$AppExe = Join-Path $AppDir "OCR Studio.exe"
if (-not (Test-Path $AppExe)) {
    throw "Brak pliku: $AppExe"
}

Write-Host "`n[3/4] Przygotowanie PackageRoot..." -ForegroundColor Yellow
python scripts\generate_msix_assets.py
if ($LASTEXITCODE -ne 0) { throw "Blad generowania obrazow MSIX." }

$MsixDir = Join-Path $Root "installer\msix"
$PackageRoot = Join-Path $MsixDir "PackageRoot"
if (Test-Path $PackageRoot) {
    Remove-Item $PackageRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $PackageRoot | Out-Null

# Cala zawartosc onedir builda (exe + zaleznosci) trafia do korzenia pakietu.
Copy-Item -Path (Join-Path $AppDir "*") -Destination $PackageRoot -Recurse

# python-docx bundluje (przez hook PyInstallera) surowy, rozpakowany szablon
# .docx obok gotowego templates\default.docx. python-docx w runtime czyta
# wylacznie ten drugi (zip) — docx\api.py:_default_docx_path(). Rozpakowany
# folder zawiera pliki OPC "[Content_Types].xml" i ".rels", ktorych nazwy
# koliduja z zarezerwowanym formatem pakietu MSIX (blad makeappx 0x8007007b),
# wiec usuwamy go jako martwy balast przed pakowaniem.
$DeadDocxTemplate = Join-Path $PackageRoot "_internal\docx\templates\default-docx-template"
if (Test-Path $DeadDocxTemplate) {
    Remove-Item $DeadDocxTemplate -Recurse -Force
}

# Porzadkowe pliki systemowe (np. z paczek pip na macOS) niepotrzebne w
# pakiecie i niedozwolone przez MSIX (nazwy zaczynajace sie od kropki).
Get-ChildItem -Path $PackageRoot -Recurse -Force -Include ".DS_Store", ".gitkeep" |
    Remove-Item -Force

Copy-Item -Path (Join-Path $MsixDir "Images") -Destination $PackageRoot -Recurse

$ManifestSource = Join-Path $MsixDir "AppxManifest.xml"
$ManifestTarget = Join-Path $PackageRoot "AppxManifest.xml"
(Get-Content $ManifestSource -Raw) -replace "__VERSION__", $Version |
    Set-Content -Path $ManifestTarget -Encoding UTF8

Write-Host "OK: $PackageRoot" -ForegroundColor Green

Write-Host "`n[4/4] Pakowanie MSIX (makeappx)..." -ForegroundColor Yellow
$SdkRoots = @(
    "${env:ProgramFiles(x86)}\Windows Kits\10\bin"
)
$MakeAppx = $SdkRoots |
    Where-Object { Test-Path $_ } |
    ForEach-Object { Get-ChildItem $_ -Directory | Sort-Object Name -Descending } |
    ForEach-Object { Join-Path $_.FullName "x64\makeappx.exe" } |
    Where-Object { Test-Path $_ } |
    Select-Object -First 1

if (-not $MakeAppx) {
    Write-Host "UWAGA: Nie znaleziono makeappx.exe (Windows 10 SDK)." -ForegroundColor Red
    Write-Host "Zainstaluj: https://developer.microsoft.com/windows/downloads/windows-sdk/" -ForegroundColor Yellow
    Write-Host "PackageRoot jest gotowy w: $PackageRoot — spakuj go recznie po instalacji SDK." -ForegroundColor Yellow
    exit 0
}

$OutputDir = Join-Path $MsixDir "output"
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
$MsixPath = Join-Path $OutputDir "StudioOCR_$Version.msix"

& $MakeAppx pack /d $PackageRoot /p $MsixPath /overwrite
if ($LASTEXITCODE -ne 0) { throw "Blad pakowania MSIX." }

Write-Host "`nGOTOWE (niepodpisany, do Partner Center): $MsixPath" -ForegroundColor Green

if ($Sign) {
    # Kopia do podpisu — plik do Partner Center ($MsixPath) ma zostac
    # niepodpisany niezaleznie od tej galezi, zeby przypadkowo nie wgrac
    # wersji z osobistym certyfikatem testowym zamiast czystego pakietu.
    $SignedMsixPath = Join-Path $OutputDir "StudioOCR_${Version}_signed_local_test.msix"
    Copy-Item -Path $MsixPath -Destination $SignedMsixPath -Force

    Write-Host "`n[opcjonalnie] Podpisywanie certyfikatem testowym (tylko do lokalnego sideload)..." -ForegroundColor Yellow
    $SignTool = $SdkRoots |
        Where-Object { Test-Path $_ } |
        ForEach-Object { Get-ChildItem $_ -Directory | Sort-Object Name -Descending } |
        ForEach-Object { Join-Path $_.FullName "x64\signtool.exe" } |
        Where-Object { Test-Path $_ } |
        Select-Object -First 1

    if (-not $SignTool) {
        Write-Host "UWAGA: Nie znaleziono signtool.exe — pomijam podpisywanie." -ForegroundColor Red
    } else {
        $CertPath = Join-Path $OutputDir "StudioOCR_test.pfx"
        $PfxPassword = ConvertTo-SecureString -String "StudioOCR!Test" -Force -AsPlainText

        if (-not (Test-Path $CertPath)) {
            # Publisher CN=15A53D32-... to tozsamosc wydawcy z Partner Center,
            # wspolna dla wszystkich aplikacji tego konta — jesli certyfikat z
            # tym Subject juz istnieje w magazynie (np. z innego projektu),
            # UZYWAMY GO PONOWNIE (eksport do wlasnego pliku .pfx dla Studio
            # OCR) zamiast generowac nowa, niepowiazana pare kluczy. Nowy
            # self-signed cert z tym samym Subject ale innym kluczem prywatnym
            # nie zadzialalby do sideloadu (Windows waliduje klucz, nie tylko
            # napis Subject).
            $ExistingCert = Get-ChildItem -Path "Cert:\CurrentUser\My" |
                Where-Object { $_.Subject -eq "CN=15A53D32-C868-48EE-B700-5DBB5449CA1B" -and $_.HasPrivateKey } |
                Sort-Object NotAfter -Descending |
                Select-Object -First 1

            if ($ExistingCert) {
                Write-Host "Znaleziono istniejacy certyfikat wydawcy w magazynie (thumbprint: $($ExistingCert.Thumbprint))." -ForegroundColor Yellow
                Write-Host "Eksportuje go do osobnego pliku testowego dla Studio OCR (bez tworzenia nowego certyfikatu)." -ForegroundColor Yellow
                Export-PfxCertificate -Cert $ExistingCert -FilePath $CertPath -Password $PfxPassword | Out-Null
            } else {
                $Cert = New-SelfSignedCertificate `
                    -Type Custom `
                    -Subject "CN=15A53D32-C868-48EE-B700-5DBB5449CA1B" `
                    -KeyUsage DigitalSignature `
                    -FriendlyName "Studio OCR test cert" `
                    -CertStoreLocation "Cert:\CurrentUser\My" `
                    -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.3", "2.5.29.19={text}")
                Export-PfxCertificate -Cert $Cert -FilePath $CertPath -Password $PfxPassword | Out-Null
                Write-Host "Utworzono nowy certyfikat testowy: $CertPath (haslo: StudioOCR!Test)" -ForegroundColor Yellow
            }
            Write-Host "Aby zainstalowac lokalnie, zaimportuj $CertPath do 'Zaufane osoby' (Trusted People) na tym komputerze." -ForegroundColor Yellow
        }

        & $SignTool sign /fd SHA256 /a /f $CertPath /p "StudioOCR!Test" $SignedMsixPath
        if ($LASTEXITCODE -ne 0) { throw "Blad podpisywania MSIX." }
        Write-Host "Podpisano (kopia do lokalnych testow): $SignedMsixPath" -ForegroundColor Green
        Write-Host "Plik do Partner Center pozostaje niepodpisany: $MsixPath" -ForegroundColor Green
    }
} else {
    Write-Host "`nPakiet NIE jest podpisany — to oczekiwany stan pliku do Partner Center." -ForegroundColor Yellow
    Write-Host "Do wgrania w Partner Center (Studio OCR, submission) podpis nie jest wymagany — Microsoft podpisuje pakiet ponownie." -ForegroundColor Yellow
    Write-Host "Do lokalnego testu (sideload) uruchom ten skrypt z parametrem -Sign (utworzy OSOBNA podpisana kopie)." -ForegroundColor Yellow
}
