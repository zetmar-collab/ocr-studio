"""Kompletuje minimalny runtime Tesseract do wbudowania w pakiet aplikacji.

Kopiuje tesseract.exe wraz z bibliotekami, od ktorych faktycznie zalezy
(wyznaczonymi z tablicy importow PE, a nie na oko), pobiera pliki jezykowe
(z weryfikacja SHA-256) i dolacza tekst licencji. Efekt trafia do
vendor/tesseract/ i jest dolaczany przez build_exe.py.

Binaria nie sa trzymane w repozytorium - ten skrypt odtwarza je przed buildem.
Wersja silnika jest przypieta (EXPECTED_VERSION): pakiet Sklepu i wydanie
z GitHuba musza zawierac ten sam, przetestowany silnik.

Uzycie:
    python scripts/vendor_tesseract.py
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.downloads_manifest import TESSDATA_BASE_URL, TESSDATA_FILES  # noqa: E402

VENDOR_DIR = PROJECT_ROOT / "vendor" / "tesseract"
VENDOR_TESSDATA = VENDOR_DIR / "tessdata"

EXPECTED_VERSION = "5.3.1.20230401"
BUNDLED_LANGUAGES = ["eng", "pol"]

SOURCE_CANDIDATES = [
    Path(r"C:\Program Files\Tesseract-OCR"),
    Path(r"C:\Program Files (x86)\Tesseract-OCR"),
    Path.home() / r"AppData\Local\Programs\Tesseract-OCR",
]


def find_tesseract_source() -> Path:
    for candidate in SOURCE_CANDIDATES:
        if (candidate / "tesseract.exe").exists():
            return candidate
    raise SystemExit(
        "Nie znaleziono instalacji Tesseract.\n"
        f"Zainstaluj wersje {EXPECTED_VERSION} (choco install tesseract "
        f"--version {EXPECTED_VERSION}), a potem uruchom ten skrypt ponownie."
    )


def check_version(source: Path) -> None:
    result = subprocess.run(
        [str(source / "tesseract.exe"), "--version"],
        capture_output=True,
        text=True,
        errors="replace",
    )
    first_line = (result.stdout or result.stderr).splitlines()[0].strip()
    if EXPECTED_VERSION not in first_line:
        raise SystemExit(
            f"Zla wersja Tesseract: '{first_line}'.\n"
            f"Oczekiwana: {EXPECTED_VERSION}. Zmiana wersji wymaga swiadomej "
            "aktualizacji EXPECTED_VERSION po przetestowaniu pakietu."
        )
    print(f"Wersja silnika: {first_line}")


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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_languages() -> None:
    VENDOR_TESSDATA.mkdir(parents=True, exist_ok=True)
    for lang in BUNDLED_LANGUAGES:
        expected_sha, expected_size = TESSDATA_FILES[lang]
        target = VENDOR_TESSDATA / f"{lang}.traineddata"
        if not target.exists():
            print(f"Pobieram {lang}.traineddata ...")
            response = requests.get(f"{TESSDATA_BASE_URL}/{lang}.traineddata", timeout=180)
            response.raise_for_status()
            target.write_bytes(response.content)
        if target.stat().st_size != expected_size or _sha256(target) != expected_sha:
            target.unlink(missing_ok=True)
            raise SystemExit(f"Suma kontrolna {lang}.traineddata nie zgadza sie z manifestem.")
        print(f"OK (SHA-256 zgodny): tessdata/{lang}.traineddata ({expected_size / 1024 / 1024:.1f} MB)")


def copy_pdf_font(source: Path) -> None:
    """Czcionka niewidocznej warstwy tekstowej - bez niej `pdf` nie dziala."""
    font = source / "tessdata" / "pdf.ttf"
    if not font.exists():
        raise SystemExit(f"Brak pdf.ttf w instalacji Tesseract: {font}")
    shutil.copy2(font, VENDOR_TESSDATA / "pdf.ttf")
    print("OK: dolaczono pdf.ttf")


def copy_license(source: Path) -> None:
    license_file = source / "doc" / "LICENSE"
    if not license_file.exists():
        raise SystemExit(f"Brak pliku licencji w instalacji Tesseract: {license_file}")
    shutil.copy2(license_file, VENDOR_DIR / "LICENSE-tesseract-apache-2.0.txt")
    print("OK: dolaczono tekst licencji Apache 2.0")


def main() -> int:
    if not sys.platform.startswith("win"):
        raise SystemExit("Skrypt dziala tylko na Windows.")

    source = find_tesseract_source()
    print(f"Zrodlo Tesseract: {source}")
    check_version(source)

    if VENDOR_DIR.exists():
        shutil.rmtree(VENDOR_DIR)
    VENDOR_DIR.mkdir(parents=True)

    shutil.copy2(source / "tesseract.exe", VENDOR_DIR / "tesseract.exe")

    dlls = required_dlls(source)
    for dll in sorted(dlls):
        shutil.copy2(source / dll, VENDOR_DIR / dll)
    print(f"Skopiowano tesseract.exe + {len(dlls)} DLL")

    download_languages()
    copy_pdf_font(source)
    copy_license(source)

    total = sum(f.stat().st_size for f in VENDOR_DIR.rglob("*") if f.is_file())
    print(f"\nGOTOWE: {VENDOR_DIR} ({total / 1024 / 1024:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
