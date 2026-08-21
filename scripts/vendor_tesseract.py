"""Kompletuje minimalny runtime Tesseract do wbudowania w pakiet aplikacji.

Kopiuje tesseract.exe wraz z bibliotekami, od ktorych faktycznie zalezy
(wyznaczonymi z tablicy importow PE, a nie na oko), oraz pobiera pliki
jezykowe. Efekt trafia do vendor/tesseract/ i jest dolaczany przez
build_exe.py.

Binaria nie sa trzymane w repozytorium - ten skrypt odtwarza je przed buildem.

Uzycie:
    python scripts/vendor_tesseract.py
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VENDOR_DIR = PROJECT_ROOT / "vendor" / "tesseract"
VENDOR_TESSDATA = VENDOR_DIR / "tessdata"

SOURCE_CANDIDATES = [
    Path(r"C:\Program Files\Tesseract-OCR"),
    Path(r"C:\Program Files (x86)\Tesseract-OCR"),
    Path.home() / r"AppData\Local\Programs\Tesseract-OCR",
]

# Te same zrodla, z ktorych aplikacja dociaga kolejne jezyki w runtime,
# zeby jakosc wbudowanych i doinstalowanych plikow byla identyczna.
TESSDATA_BASE_URL = "https://github.com/tesseract-ocr/tessdata_best/raw/main"
BUNDLED_LANGUAGES = ["eng", "pol"]


def find_tesseract_source() -> Path:
    for candidate in SOURCE_CANDIDATES:
        if (candidate / "tesseract.exe").exists():
            return candidate
    raise SystemExit(
        "Nie znaleziono instalacji Tesseract.\n"
        "Zainstaluj Tesseract (https://github.com/UB-Mannheim/tesseract/wiki), "
        "a potem uruchom ten skrypt ponownie."
    )


def required_dlls(source: Path) -> set[str]:
    """Zwraca nazwy DLL, od ktorych tesseract.exe zalezy posrednio lub bezposrednio."""
    try:
        import pefile
    except ImportError as exc:
        raise SystemExit(
            "Brak modulu pefile. Zainstaluj: pip install -r requirements-build.txt"
        ) from exc

    available = {p.name.lower(): p.name for p in source.glob("*.dll")}
    needed: set[str] = set()
    visited: set[str] = set()

    def walk(pe_path: Path) -> None:
        try:
            pe = pefile.PE(str(pe_path), fast_load=True)
            pe.parse_data_directories([pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"]])
        except Exception:
            return
        try:
            for entry in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []):
                name = entry.dll.decode(errors="ignore").lower()
                if name in available and name not in visited:
                    visited.add(name)
                    real_name = available[name]
                    needed.add(real_name)
                    walk(source / real_name)
        finally:
            pe.close()

    walk(source / "tesseract.exe")
    return needed


def download_languages() -> None:
    VENDOR_TESSDATA.mkdir(parents=True, exist_ok=True)
    for lang in BUNDLED_LANGUAGES:
        target = VENDOR_TESSDATA / f"{lang}.traineddata"
        if target.exists():
            print(f"OK (jest juz): tessdata/{lang}.traineddata")
            continue
        url = f"{TESSDATA_BASE_URL}/{lang}.traineddata"
        print(f"Pobieram {lang}.traineddata ...")
        response = requests.get(url, timeout=180)
        response.raise_for_status()
        target.write_bytes(response.content)
        print(f"OK: tessdata/{lang}.traineddata ({len(response.content) / 1024 / 1024:.1f} MB)")


def main() -> int:
    if not sys.platform.startswith("win"):
        raise SystemExit("Skrypt dziala tylko na Windows.")

    source = find_tesseract_source()
    print(f"Zrodlo Tesseract: {source}")

    if VENDOR_DIR.exists():
        shutil.rmtree(VENDOR_DIR)
    VENDOR_DIR.mkdir(parents=True)

    shutil.copy2(source / "tesseract.exe", VENDOR_DIR / "tesseract.exe")

    dlls = required_dlls(source)
    for dll in sorted(dlls):
        shutil.copy2(source / dll, VENDOR_DIR / dll)
    print(f"Skopiowano tesseract.exe + {len(dlls)} DLL")

    download_languages()

    total = sum(f.stat().st_size for f in VENDOR_DIR.rglob("*") if f.is_file())
    print(f"\nGOTOWE: {VENDOR_DIR} ({total / 1024 / 1024:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
