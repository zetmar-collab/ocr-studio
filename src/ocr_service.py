from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytesseract
from PIL import Image

from .config import TESSDATA_DIR


class OCRService:
    def __init__(self) -> None:
        self._tesseract_cmd = self._resolve_tesseract_command()

    def _resolve_tesseract_command(self) -> str:
        if shutil.which("tesseract"):
            return shutil.which("tesseract") or "tesseract"

        candidates = [
            Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
            Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
            Path.home() / r"AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
        ]
        for candidate in candidates:
            if candidate.exists():
                pytesseract.pytesseract.tesseract_cmd = str(candidate)
                return str(candidate)

        return "tesseract"

    def _ensure_lang_installed(self, lang_code: str) -> Path:
        trained = TESSDATA_DIR / f"{lang_code}.traineddata"
        if trained.exists():
            return trained

        system_tessdata_dirs = [
            Path(r"C:\Program Files\Tesseract-OCR\tessdata"),
            Path(r"C:\Program Files (x86)\Tesseract-OCR\tessdata"),
        ]
        for system_dir in system_tessdata_dirs:
            source = system_dir / f"{lang_code}.traineddata"
            if source.exists():
                shutil.copy2(source, trained)
                return trained

        raise FileNotFoundError(
            f"Brak pliku jezyka OCR: {lang_code}.traineddata. "
            f"Kliknij 'Doinstaluj jezyk OCR' w aplikacji."
        )

    def _run_ocr(self, image: Image.Image, lang_code: str) -> str:
        tessdata_dir = str(TESSDATA_DIR.resolve())
        env = os.environ.copy()
        env["TESSDATA_PREFIX"] = tessdata_dir

        tmp_path = Path(tempfile.mktemp(suffix=".png"))
        try:
            image.save(tmp_path)
            command = [
                self._tesseract_cmd,
                str(tmp_path),
                "stdout",
                "-l",
                lang_code,
                "--tessdata-dir",
                tessdata_dir,
            ]
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
            )
            if process.returncode != 0:
                details = process.stderr.strip() or process.stdout.strip()
                raise RuntimeError(details or "Tesseract OCR nie powiodl sie.")
            return process.stdout
        finally:
            tmp_path.unlink(missing_ok=True)

    def image_to_text(self, image_path: Path, lang_code: str) -> str:
        self._ensure_lang_installed(lang_code)
        with Image.open(image_path) as image:
            return self._run_ocr(image, lang_code)

    def pdf_to_text(self, pdf_path: Path, lang_code: str) -> str:
        """OCR PDF przez render stron (stabilne w .exe, bez OCRmyPDF/hocr)."""
        self._ensure_lang_installed(lang_code)
        try:
            import pypdfium2 as pdfium
        except ImportError as exc:
            raise RuntimeError(
                "Brak modulu pypdfium2 do OCR PDF. Zainstaluj ponownie aplikacje."
            ) from exc

        texts: list[str] = []
        pdf = pdfium.PdfDocument(str(pdf_path))
        try:
            for page_index in range(len(pdf)):
                page = pdf[page_index]
                bitmap = page.render(scale=2.0)
                pil_image = bitmap.to_pil()
                page_text = self._run_ocr(pil_image, lang_code).strip()
                if page_text:
                    texts.append(page_text)
        finally:
            pdf.close()

        if not texts:
            return ""
        return "\n\n".join(texts)
