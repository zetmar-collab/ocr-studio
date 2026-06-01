# OCR Studio

Desktopowa aplikacja OCR dla Windows — autor **Marek Zettel**.

Wersja: **0.1.8**

## Funkcje

- OCR obrazów (PNG, JPEG, BMP, TIFF) i PDF
- Skanowanie dokumentów (WIA) do PNG / JPEG / PDF
- Wybór miejsca zapisu skanu + podgląd przed OCR
- Wielojęzyczny OCR (instalacja języków z poziomu aplikacji)
- Sprawdzanie pisowni (Hunspell) z poprawą lub ignorowaniem błędów
- Eksport do TXT i DOCX
- Motyw jasny / ciemny / systemowy
- Instalacja silników Tesseract i Ghostscript z poziomu GUI

## Pobieranie (użytkownik końcowy)

1. Pobierz `OCR_Studio_Setup_x.x.x.exe` z [Releases](https://github.com/zetmar-collab/ocr-studio/releases).
2. Uruchom instalator i postępuj według kreatora.
3. Po pierwszym uruchomieniu: **Zainstaluj Tesseract** (i opcjonalnie język OCR, np. Polski).

## Budowanie ze źródeł (deweloper)

### Wymagania

- Windows 10/11
- Python 3.11+
- [Inno Setup 6](https://jrsoftware.org/isdl.php) (do instalatora `.exe`)

### Szybki build (EXE + Setup)

```powershell
cd "C:\Users\Marek\Desktop\OCR Studio"
.\scripts\build_installer.ps1
```

Wynik:

- `dist\OCR Studio.exe` — aplikacja przenośna
- `installer\output\OCR_Studio_Setup_0.1.8.exe` — instalator

### Tylko EXE

```powershell
pip install -r requirements.txt -r requirements-build.txt
python build_exe.py
```

### Uruchomienie z kodu (dev)

```powershell
pip install -r requirements.txt
python run.py
```

## Struktura projektu

```
OCR Studio/
├── src/                 # kod aplikacji
├── installer/           # skrypt Inno Setup
├── scripts/             # build_installer.ps1
├── data/                # ikona, katalogi danych runtime
├── build_exe.py
├── run.py
└── requirements.txt
```

## GitHub Releases

Tag w formacie `v0.1.8` uruchamia workflow budujący artefakty (EXE + Setup).

```powershell
git tag v0.1.8
git push origin v0.1.8
```

## Licencja

MIT — zobacz [LICENSE](LICENSE).
