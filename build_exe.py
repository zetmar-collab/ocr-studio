from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from src.config import APP_VERSION
from src.icon_utils import ensure_app_icon


def main() -> int:
    onedir = "--onedir" in sys.argv
    project_root = Path(__file__).resolve().parent
    dist_dir = project_root / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)

    vendor_tesseract = project_root / "vendor" / "tesseract"
    if not (vendor_tesseract / "tesseract.exe").exists():
        print(
            "BLAD: brak wbudowanego silnika OCR w vendor/tesseract.\n"
            "Uruchom najpierw: python scripts/vendor_tesseract.py",
            file=sys.stderr,
        )
        return 1

    icon_path = ensure_app_icon()
    # A onedir build always uses the stable "OCR Studio" name: MSIX packaging
    # references a fixed folder/exe path, unlike the versioned onefile build.
    build_name = "OCR Studio" if onedir else f"OCR Studio {APP_VERSION}"

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onedir" if onedir else "--onefile",
        "--windowed",
        "--name",
        build_name,
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
        "--hidden-import",
        "pypdfium2",
        "--collect-all",
        "pypdfium2",
        "--add-data",
        f"{project_root / 'data'};data",
        # Silnik OCR wbudowany w pakiet - aplikacja dziala od razu po
        # instalacji, bez pobierania i bez UAC.
        "--add-data",
        f"{vendor_tesseract};tesseract",
        "--add-data",
        f"{project_root / 'THIRD-PARTY-NOTICES.md'};.",
        str(project_root / "run.py"),
    ]
    process = subprocess.run(command, cwd=project_root)
    if process.returncode != 0:
        return process.returncode

    if onedir:
        # dist/OCR Studio/OCR Studio.exe -- consumed directly by build_msix.ps1.
        return 0

    versioned_exe = dist_dir / f"{build_name}.exe"
    stable_exe = dist_dir / "OCR Studio.exe"
    if versioned_exe.exists():
        shutil.copy2(versioned_exe, stable_exe)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
