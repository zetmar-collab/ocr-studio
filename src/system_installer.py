from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import requests

from .config import TMP_DIR

# Publiczne instalatory (Windows x64)
TESSERACT_INSTALLER_URL = (
    "https://github.com/UB-Mannheim/tesseract/wiki/"
)
TESSERACT_FALLBACK_EXE = (
    "https://digi.bib.uni-mannheim.de/tesseract/"
    "tesseract-ocr-w64-setup-5.3.1.20230401.exe"
)
GHOSTSCRIPT_EXE_URL = (
    "https://github.com/ArtifexSoftware/ghostpdl-downloads/releases/download/gs10060/"
    "gs10060w64.exe"
)


class SystemInstaller:
    def find_tesseract_executable(self) -> Path | None:
        from_path = shutil.which("tesseract")
        if from_path:
            return Path(from_path)

        candidates = [
            Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
            Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
            Path.home() / r"AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    def find_ghostscript_executable(self) -> Path | None:
        for binary in ("gswin64c", "gswin32c"):
            from_path = shutil.which(binary)
            if from_path:
                return Path(from_path)

        gs_roots = [
            Path(r"C:\Program Files\gs"),
            Path(r"C:\Program Files (x86)\gs"),
        ]
        for root in gs_roots:
            if not root.exists():
                continue
            versions = sorted([p for p in root.iterdir() if p.is_dir()], reverse=True)
            for version in versions:
                for exe_name in ("gswin64c.exe", "gswin32c.exe"):
                    candidate = version / "bin" / exe_name
                    if candidate.exists():
                        return candidate
        return None

    def is_tesseract_installed(self) -> bool:
        return self.find_tesseract_executable() is not None

    def is_ghostscript_installed(self) -> bool:
        return self.find_ghostscript_executable() is not None

    def get_engine_status(self) -> dict[str, bool]:
        return {
            "tesseract": self.is_tesseract_installed(),
            "ghostscript": self.is_ghostscript_installed(),
        }

    def _download_file(self, url: str, target: Path) -> Path:
        response = requests.get(url, timeout=180, stream=True)
        response.raise_for_status()
        with target.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)
        return target

    def _run_installer_elevated(self, installer_path: Path, silent_args: str) -> None:
        # Elevation via UAC prompt to avoid WinError 740 on standard user context.
        ps_command = (
            "Start-Process "
            f"-FilePath '{installer_path}' "
            f"-ArgumentList '{silent_args}' "
            "-Verb RunAs -Wait"
        )
        process = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_command],
            capture_output=True,
            text=True,
        )
        if process.returncode != 0:
            message = process.stderr.strip() or process.stdout.strip()
            raise RuntimeError(
                message
                or "Instalacja anulowana lub nie powiodla sie (sprawdz UAC/Uprawnienia administratora)."
            )

    def install_tesseract(self) -> str:
        installer = TMP_DIR / "tesseract-installer.exe"
        self._download_file(TESSERACT_FALLBACK_EXE, installer)
        self._run_installer_elevated(installer, "/S")
        return "Tesseract zainstalowany."

    def install_ghostscript(self) -> str:
        installer = TMP_DIR / "ghostscript-installer.exe"
        self._download_file(GHOSTSCRIPT_EXE_URL, installer)
        self._run_installer_elevated(installer, "/S")
        return "Ghostscript zainstalowany."
