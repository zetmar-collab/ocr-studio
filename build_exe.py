"""Buduje aplikacje (PyInstaller --onedir) do dist/OCR Studio/.

Jeden wariant dla wszystkich kanalow (instalator Inno Setup, archiwum przenosne,
pakiet MSIX). Wariant --onefile zostal usuniety: rozpakowywal ~140 MB do %TEMP%
przy kazdym uruchomieniu, co spowalnialo start i drazylo antywirusy.

Przed budowaniem trzeba odtworzyc zasoby wbudowane w pakiet:
    python scripts/vendor_tesseract.py
    python scripts/vendor_dictionaries.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from src.icon_utils import ensure_app_icon

PROJECT_ROOT = Path(__file__).resolve().parent
EXE_NAME = "OCR Studio"  # stala nazwa: odwoluje sie do niej AppxManifest.xml i instalator

REQUIRED_VENDOR_FILES = (
    "vendor/tesseract/tesseract.exe",
    "vendor/tesseract/tessdata/pol.traineddata",
    "vendor/tesseract/tessdata/eng.traineddata",
    "vendor/tesseract/tessdata/pdf.ttf",
    "vendor/tesseract/LICENSE-tesseract-apache-2.0.txt",
    "vendor/dictionaries/pl_PL/pl_PL.dic",
    "vendor/dictionaries/pl_PL/LICENSE-pl_PL.txt",
    "vendor/dictionaries/en_US/en_US.dic",
    "vendor/dictionaries/en_US/LICENSE-en_US.txt",
)


def check_vendor() -> bool:
    missing = [name for name in REQUIRED_VENDOR_FILES if not (PROJECT_ROOT / name).exists()]
    if missing:
        print("BLAD: brakuje wbudowanych zasobow:", file=sys.stderr)
        for name in missing:
            print(f"  - {name}", file=sys.stderr)
        print(
            "Uruchom: python scripts/vendor_tesseract.py && python scripts/vendor_dictionaries.py",
            file=sys.stderr,
        )
        return False
    return True


def main() -> int:
    if not check_vendor():
        return 1

    icon_path = ensure_app_icon()
    data = [
        (PROJECT_ROOT / "data", "data"),
        (PROJECT_ROOT / "vendor" / "tesseract", "tesseract"),
        (PROJECT_ROOT / "vendor" / "dictionaries", "dictionaries"),
        (PROJECT_ROOT / "THIRD-PARTY-NOTICES.md", "."),
        (PROJECT_ROOT / "LICENSE", "."),
    ]

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--windowed",
        "--name",
        EXE_NAME,
        "--icon",
        str(icon_path),
        "--hidden-import",
        "customtkinter",
        "--collect-all",
        "customtkinter",
        "--collect-all",
        "darkdetect",
        "--collect-all",
        "packaging",
        "--collect-all",
        "pypdfium2",
        "--collect-all",
        "tkinterdnd2",
    ]
    for source, target in data:
        command += ["--add-data", f"{source};{target}"]
    command.append(str(PROJECT_ROOT / "run.py"))

    process = subprocess.run(command, cwd=PROJECT_ROOT)
    return process.returncode


if __name__ == "__main__":
    raise SystemExit(main())
