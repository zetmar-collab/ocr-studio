from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from src.config import APP_VERSION
from src.icon_utils import ensure_app_icon


def main() -> int:
    project_root = Path(__file__).resolve().parent
    dist_dir = project_root / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)

    icon_path = ensure_app_icon()
    build_name = f"OCR Studio {APP_VERSION}"

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onefile",
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
        str(project_root / "run.py"),
    ]
    process = subprocess.run(command, cwd=project_root)
    if process.returncode != 0:
        return process.returncode

    versioned_exe = dist_dir / f"{build_name}.exe"
    stable_exe = dist_dir / "OCR Studio.exe"
    if versioned_exe.exists():
        shutil.copy2(versioned_exe, stable_exe)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
