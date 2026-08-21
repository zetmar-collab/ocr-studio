from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytesseract
from PIL import Image

from .config import (
    BUNDLED_TESSDATA_DIR,
    BUNDLED_TESSERACT_EXE,
    TESSDATA_DIR,
)


class OCRLanguageMissingError(FileNotFoundError):
    """Raised when a Tesseract traineddata file for `lang_code` is not installed."""

    def __init__(self, lang_code: str) -> None:
        self.lang_code = lang_code
        super().__init__(lang_code)


class OCRService:
    def __init__(self) -> None:
        self._tesseract_cmd = self._resolve_tesseract_command()

    def _resolve_tesseract_command(self) -> str:
        # Silnik dolaczony do pakietu ma pierwszenstwo: dziala od razu po
        # instalacji i nie zalezy od tego, co uzytkownik ma w systemie.
        if BUNDLED_TESSERACT_EXE.exists():
            pytesseract.pytesseract.tesseract_cmd = str(BUNDLED_TESSERACT_EXE)
            return str(BUNDLED_TESSERACT_EXE)

        # Zapasowo: instalacja systemowa (np. przy uruchomieniu ze zrodel
        # bez wczesniejszego `python scripts/vendor_tesseract.py`).
        from_path = shutil.which("tesseract")
        if from_path:
            return from_path

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

    def is_available(self) -> bool:
        """Czy silnik OCR jest gotowy do uzycia."""
        if BUNDLED_TESSERACT_EXE.exists():
            return True
        return shutil.which(self._tesseract_cmd) is not None or Path(self._tesseract_cmd).exists()

    def ensure_lang_installed(self, lang_code: str) -> Path:
        trained = TESSDATA_DIR / f"{lang_code}.traineddata"
        if trained.exists():
            return trained

        # Jezyki dolaczone do pakietu (pol, eng) oraz ewentualna instalacja
        # systemowa. Kopiujemy do TESSDATA_DIR, zeby wszystkie pliki jezykowe
        # - wbudowane i doinstalowane - lezaly w jednym miejscu.
        fallback_tessdata_dirs = [
            BUNDLED_TESSDATA_DIR,
            Path(r"C:\Program Files\Tesseract-OCR\tessdata"),
            Path(r"C:\Program Files (x86)\Tesseract-OCR\tessdata"),
        ]
        for source_dir in fallback_tessdata_dirs:
            source = source_dir / f"{lang_code}.traineddata"
            if source.exists():
                shutil.copy2(source, trained)
                return trained

        raise OCRLanguageMissingError(lang_code)

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
        self.ensure_lang_installed(lang_code)
        with Image.open(image_path) as image:
            return self._run_ocr(image, lang_code)

    def pdf_to_text(self, pdf_path: Path, lang_code: str) -> str:
        """OCR PDF przez render stron (stabilne w .exe, bez OCRmyPDF/hocr)."""
        self.ensure_lang_installed(lang_code)
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
