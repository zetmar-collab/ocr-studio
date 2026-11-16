# Studio OCR

Desktopowa aplikacja OCR dla Windows — autor **Marek Zettel**.

Wersja: **0.2.2**

[**Pobierz ze Sklepu Windows**](https://apps.microsoft.com/store/detail/9P5G09GWN16N)

## Funkcje

- OCR obrazów (PNG, JPEG, BMP, TIFF — także wielostronicowy, WebP) i PDF
- **Silnik OCR wbudowany w aplikację** — działa od razu po instalacji, offline, bez uprawnień administratora
- Języki polski i angielski dołączone; kolejne doinstalujesz z poziomu aplikacji (z weryfikacją sumy kontrolnej)
- **Dwa języki naraz** (np. polski + angielski) dla dokumentów mieszanych
- **PDF z warstwą tekstową** — tekst jest czytany bezpośrednio, bez OCR (szybciej i dokładniej); skany są rozpoznawane
- **Zapis przeszukiwalnego PDF** z niewidoczną warstwą tekstową
- **Przeciągnij i upuść** pliki lub foldery na okno; **OCR wsadowy** wielu plików naraz
- Pasek postępu i **przycisk Anuluj** (Esc) — długie dokumenty nie blokują okna
- Słowa rozpoznane z małą pewnością są **podświetlane** do sprawdzenia
- Skanowanie dokumentów (WIA) do PNG / JPEG / PDF z podglądem przed OCR
- Sprawdzanie pisowni (Hunspell): słowniki polski i angielski wbudowane. Błędy są podkreślone w tekście;
  **prawy przycisk myszy** daje podpowiedzi, „Ignoruj" i „Dodaj do słownika"; „Popraw wszystko" działa
  w jednym kroku, który cofniesz **Ctrl+Z**
- Zapis do TXT i DOCX, z opcją scalania linii w akapity
- Motyw jasny / ciemny / systemowy
- Język interfejsu: polski / angielski (domyślnie wg języka Windows), zmiana bez restartu
- Skróty: **F5** uruchom OCR, **Ctrl+O** wczytaj pliki, **Esc** anuluj

## Pobieranie (użytkownik końcowy)

Najprościej ze **Sklepu Windows**: <https://apps.microsoft.com/store/detail/9P5G09GWN16N>

Alternatywnie z [Releases](https://github.com/zetmar-collab/ocr-studio/releases):

- `OCR_Studio_Setup_x.x.x.exe` — instalator (domyślnie dla bieżącego użytkownika, bez UAC),
- `StudioOCR_x.x.x_portable.zip` — wersja przenośna (rozpakuj i uruchom `OCR Studio.exe`).

## Budowanie ze źródeł (deweloper)

### Wymagania

- Windows 10/11, Python **3.12**
- [Tesseract 5.3.1](https://github.com/UB-Mannheim/tesseract/wiki) zainstalowany jako **źródło** wbudowanego
  silnika (`choco install tesseract --version=5.3.1.20230401`). Wersja jest przypięta —
  `scripts/vendor_tesseract.py` przerwie build, jeśli się nie zgadza.
- [Inno Setup 6](https://jrsoftware.org/isdl.php) (opcjonalnie, do instalatora `.exe`)

### Uruchomienie z kodu

```powershell
pip install -r requirements.txt
python scripts/vendor_tesseract.py        # silnik OCR + polski/angielski -> vendor/tesseract
python scripts/vendor_dictionaries.py     # słowniki pl_PL/en_US -> vendor/dictionaries
python run.py
```

`vendor/` nie jest w repozytorium (jest w `.gitignore`) — skrypty odtwarzają go i weryfikują sumami SHA-256.

### Testy i lint

```powershell
pip install -r requirements-dev.txt
python -m ruff check .
python -m pytest -rs          # ~170 testów: serwisy, silnik OCR, interfejs
python -m pip_audit -r requirements.txt --no-deps --disable-pip
```

Testy silnika (`-m engine`) i interfejsu (`-m gui`) wymagają `vendor/` i ekranu; bez nich są pomijane.

### Test dymny (czysty komputer)

```powershell
python run.py --selftest wynik.json     # lub: "OCR Studio.exe" --selftest wynik.json
```

Sprawdza, że aplikacja działa **bez Tesseract w systemie i bez internetu**: wbudowany silnik, języki,
słowniki, OCR po polsku, przeszukiwalny PDF i zapis DOCX. Kod wyjścia 0 = wszystko działa.
To dokładnie scenariusz, na którym wersja 0.2.0 została odrzucona przez certyfikację Sklepu.

### Instalator i wersja przenośna

```powershell
.\scripts\build_installer.ps1
```

Skrypt odtwarza `vendor/`, buduje aplikację (PyInstaller `--onedir`), uruchamia `--selftest` przy `PATH`
bez Tesseract, pakuje `dist\StudioOCR_<wersja>_portable.zip` i buduje instalator
`installer\output\OCR_Studio_Setup_<wersja>.exe`.

### Pakiet MSIX (Microsoft Store)

Wymaga dodatkowo [Windows 10 SDK](https://developer.microsoft.com/windows/downloads/windows-sdk/) (`makeappx.exe`, `signtool.exe`).

```powershell
.\scripts\build_msix.ps1            # buduje .msix gotowy do wgrania w Partner Center
.\scripts\build_msix.ps1 -Sign      # dodatkowo tworzy OSOBNĄ podpisaną kopię do lokalnego sideload
```

| Plik | Podpis | Przeznaczenie |
| --- | --- | --- |
| `installer\msix\output\StudioOCR_<wersja>.msix` | brak | **wgranie do Partner Center** |
| `installer\msix\output\StudioOCR_<wersja>_signed_local_test.msix` | certyfikat testowy | wyłącznie lokalna instalacja (sideload) |

Plik do Partner Center **nigdy** nie jest podpisywany — nawet przy `-Sign`, który tworzy osobną kopię.

Tożsamość pakietu (`installer\msix\AppxManifest.xml`) odpowiada rejestracji w Partner Center:

- Nazwa pakietu: `MarekZettel-zetmar.StudioOCR`
- Wydawca: `CN=15A53D32-C868-48EE-B700-5DBB5449CA1B`
- Nazwa wyświetlana wydawcy: `Marek Zettel - zetmar`
- Nazwa wyświetlana aplikacji: `Studio OCR`

Jeśli w magazynie certyfikatów istnieje już certyfikat wydawcy `CN=15A53D32-...` (wspólny dla wszystkich
aplikacji tego konta), skrypt **użyje go ponownie** — wyeksportuje do `StudioOCR_test.pfx`.

> **Uwaga:** `StudioOCR_test.pfx` zawiera klucz prywatny. Jest wykluczony z gita — nie commituj go ani nie udostępniaj.

## Aktualizacja listy pobieranych plików

Języki OCR i słowniki pobierane na żądanie są przypięte do konkretnych commitów i sum SHA-256
(`src/downloads_manifest.py`, generowany). Po zmianie SHA w `scripts/update_data_manifest.py` lub list
języków w `src/config.py`:

```powershell
python scripts/update_data_manifest.py
```

## Struktura projektu

```
Studio OCR/
├── src/                 # kod aplikacji (main, ocr_service, spellcheck_service, jobs, ...)
├── tests/               # testy (pytest)
├── installer/           # skrypt Inno Setup + pakiet MSIX (installer/msix)
├── scripts/             # build_installer.ps1, build_msix.ps1, vendor_*.py, update_data_manifest.py
├── vendor/              # wbudowany silnik OCR i słowniki (poza repozytorium)
├── data/                # ikona, katalogi danych runtime
├── docs/                # polityka prywatności (GitHub Pages)
├── build_exe.py
└── run.py
```

## GitHub Releases

Tag w formacie `v0.2.2` uruchamia workflow: testy, lint, audyt zależności, build, test dymny
zbudowanej aplikacji, a dopiero potem publikację (osobny job z uprawnieniem do zapisu).

```powershell
git tag v0.2.2
git push origin v0.2.2
```

## Licencje

Aplikacja: MIT — zobacz [LICENSE](LICENSE). Komponenty innych producentów (Tesseract, Leptonica,
słowniki Hunspell, PDFium i in.): [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).
