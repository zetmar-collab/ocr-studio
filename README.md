# Studio OCR

Desktopowa aplikacja OCR dla Windows — autor **Marek Zettel**.

Wersja: **0.2.1**

[**Pobierz ze Sklepu Windows**](https://apps.microsoft.com/store/detail/9P5G09GWN16N)

## Funkcje

- OCR obrazów (PNG, JPEG, BMP, TIFF) i PDF
- Skanowanie dokumentów (WIA) do PNG / JPEG / PDF
- Wybór miejsca zapisu skanu + podgląd przed OCR
- Sprawdzanie pisowni (Hunspell) z poprawą lub ignorowaniem błędów
- Eksport do TXT i DOCX
- Motyw jasny / ciemny / systemowy
- Język interfejsu: polski / angielski (przełącznik w sekcji "Wygląd", zapamiętywany między uruchomieniami)
- **Silnik OCR wbudowany w aplikację** — działa od razu po instalacji, offline, bez uprawnień administratora
- Języki polski i angielski dołączone; kolejne można doinstalować z poziomu aplikacji

## Pobieranie (użytkownik końcowy)

Najprościej ze **Sklepu Windows**: <https://apps.microsoft.com/store/detail/9P5G09GWN16N>

Alternatywnie instalator `.exe`:

1. Pobierz `OCR_Studio_Setup_x.x.x.exe` z [Releases](https://github.com/zetmar-collab/ocr-studio/releases).
2. Uruchom instalator i postępuj według kreatora.

W obu przypadkach OCR działa od razu po instalacji — silnik oraz języki polski
i angielski są wbudowane. Kolejne języki dodasz przyciskiem **Doinstaluj język OCR**.

## Budowanie ze źródeł (deweloper)

### Wymagania

- Windows 10/11
- Python 3.11+
- [Inno Setup 6](https://jrsoftware.org/isdl.php) (do instalatora `.exe`)

### Szybki build (EXE + Setup)

```powershell
.\scripts\build_installer.ps1
```

Wynik:

- `dist\OCR Studio.exe` — aplikacja przenośna
- `installer\output\OCR_Studio_Setup_0.2.1.exe` — instalator

### Tylko EXE

Przed pierwszym buildem trzeba skompletować wbudowany silnik OCR (wymaga
zainstalowanego Tesseract jako źródła; binaria nie są trzymane w repozytorium):

```powershell
pip install -r requirements.txt -r requirements-build.txt
python scripts/vendor_tesseract.py
python build_exe.py
```

### Uruchomienie z kodu (dev)

```powershell
pip install -r requirements.txt
python run.py
```

### Pakiet MSIX (Microsoft Store)

Wymaga dodatkowo [Windows 10 SDK](https://developer.microsoft.com/windows/downloads/windows-sdk/) (`makeappx.exe`, `signtool.exe`).

```powershell
.\scripts\build_msix.ps1            # buduje .msix gotowy do wgrania w Partner Center
.\scripts\build_msix.ps1 -Sign      # dodatkowo tworzy OSOBNA podpisana kopie do lokalnego sideload
```

Wyniki:

| Plik | Podpis | Przeznaczenie |
| --- | --- | --- |
| `installer\msix\output\StudioOCR_<wersja>.msix` | brak | **wgranie do Partner Center** |
| `installer\msix\output\StudioOCR_<wersja>_signed_local_test.msix` | certyfikat testowy | wyłącznie lokalna instalacja (sideload) |

Plik do Partner Center **nigdy** nie jest podpisywany — nawet przy `-Sign`, ktory tworzy osobna kopie. Do sklepu wgrywaj zawsze wersje bez sufiksu `_signed_local_test`.

Tożsamość pakietu (`installer\msix\AppxManifest.xml`) jest ustawiona zgodnie z rejestracją w Partner Center:

- Nazwa pakietu: `MarekZettel-zetmar.StudioOCR`
- Wydawca: `CN=15A53D32-C868-48EE-B700-5DBB5449CA1B`
- Nazwa wyświetlana wydawcy: `Marek Zettel - zetmar`
- Nazwa wyświetlana aplikacji: `Studio OCR`

Do przesłania w Partner Center pakiet **nie może** być podpisany Twoim certyfikatem — Microsoft podpisuje go ponownie przy publikacji. Podpis (`-Sign`) jest potrzebny wyłącznie do lokalnego testu instalacji (sideload) na własnym komputerze.

Jeśli w magazynie certyfikatów istnieje już certyfikat wydawcy `CN=15A53D32-...` (wspólny dla wszystkich aplikacji tego konta Partner Center), skrypt **użyje go ponownie** — wyeksportuje do `StudioOCR_test.pfx` zamiast tworzyć nowy, niepowiązany certyfikat.

> **Uwaga:** `StudioOCR_test.pfx` zawiera klucz prywatny. Jest wykluczony z gita (`.gitignore`) — nie commituj go ani nie udostępniaj.

## Struktura projektu

```
Studio OCR/
├── src/                 # kod aplikacji
├── installer/           # skrypt Inno Setup + pakiet MSIX (installer/msix)
├── scripts/             # build_installer.ps1, build_msix.ps1,
│                        # generate_msix_assets.py, vendor_tesseract.py
├── vendor/              # wbudowany silnik OCR (poza repozytorium)
├── data/                # ikona, katalogi danych runtime
├── build_exe.py
├── run.py
└── requirements.txt
```

## GitHub Releases

Tag w formacie `v0.2.1` uruchamia workflow budujący artefakty (EXE + Setup).

```powershell
git tag v0.2.1
git push origin v0.2.1
```

## Licencja

MIT — zobacz [LICENSE](LICENSE).
