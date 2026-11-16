from __future__ import annotations

import os
import sys
from pathlib import Path

# Nazwa widoczna dla uzytkownika - taka sama jak w Microsoft Store.
APP_DISPLAY_NAME = "Studio OCR"
# Nazwa katalogu danych i pliku .exe. Pozostaje "OCR Studio", zeby nie osierocic
# danych uzytkownikow (jezyki, slowniki, ustawienia) zapisanych przez 0.1.x/0.2.x.
APP_NAME = "OCR Studio"
APP_AUTHOR = "Marek Zettel"
APP_VERSION = "0.2.2"

BASE_DIR = Path(__file__).resolve().parent.parent


def _resolve_runtime_data_dir() -> Path:
    # In onefile .exe, files inside _MEIPASS are temporary/read-only.
    # Keep OCR languages and dictionaries in a persistent user location.
    if getattr(sys, "frozen", False):
        local_app_data = os.getenv("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / APP_NAME / "data"
    return BASE_DIR / "data"


def _resolve_bundle_dir(name: str) -> Path:
    """Zasoby dolaczone do pakietu (silnik OCR, slowniki) - dzieki nim aplikacja
    dziala natychmiast po instalacji, bez pobierania i bez praw administratora."""
    if getattr(sys, "frozen", False):
        # PyInstaller rozpakowuje dodane dane do _MEIPASS (w buildzie onedir
        # jest to katalog _internal obok pliku .exe).
        bundle_root = Path(getattr(sys, "_MEIPASS", BASE_DIR))
        return bundle_root / name
    return BASE_DIR / "vendor" / name


DATA_DIR = _resolve_runtime_data_dir()
TMP_DIR = DATA_DIR / "tmp"
TESSDATA_DIR = DATA_DIR / "tessdata"
DICTS_DIR = DATA_DIR / "dictionaries"
CUSTOM_DICTS_DIR = DATA_DIR / "custom_dictionaries"

BUNDLED_TESSERACT_DIR = _resolve_bundle_dir("tesseract")
BUNDLED_TESSERACT_EXE = BUNDLED_TESSERACT_DIR / "tesseract.exe"
BUNDLED_TESSDATA_DIR = BUNDLED_TESSERACT_DIR / "tessdata"
BUNDLED_DICTS_DIR = _resolve_bundle_dir("dictionaries")

# Obslugiwane rozszerzenia plikow wejsciowych (male litery).
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp")
PDF_EXTENSION = ".pdf"
SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS + (PDF_EXTENSION,)

# Rozdzielczosc renderowania stron PDF przed OCR (Tesseract zaleca ~300 DPI).
OCR_RENDER_DPI = 300
# Slowa rozpoznane z pewnoscia ponizej progu (0-100) sa oznaczane w tekscie.
LOW_CONFIDENCE_THRESHOLD = 60

for path in [DATA_DIR, TMP_DIR, TESSDATA_DIR, DICTS_DIR, CUSTOM_DICTS_DIR]:
    path.mkdir(parents=True, exist_ok=True)

# Mapowanie najczestszych jezykow OCR na kod traineddata.
OCR_LANG_MAP = {
    "Polski": "pol",
    "English": "eng",
    "Deutsch": "deu",
    "Francais": "fra",
    "Espanol": "spa",
    "Italiano": "ita",
    "Portugues": "por",
    "Nederlands": "nld",
    "Cesky": "ces",
    "Slovencina": "slk",
    "Ukrainska": "ukr",
}

# Hunspell dictionaries (aff/dic) from open-source repo.
SPELL_LANG_MAP = {
    "Polski (pl_PL)": "pl_PL",
    "English (en_US)": "en_US",
    "Deutsch (de_DE)": "de_DE",
    "Francais (fr_FR)": "fr_FR",
    "Espanol (es_ES)": "es_ES",
    "Italiano (it_IT)": "it_IT",
}
