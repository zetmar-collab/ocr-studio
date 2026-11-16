from __future__ import annotations

import io
import math
import os
import re
import shutil
import subprocess
import sys
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageOps

from .config import (
    BUNDLED_TESSDATA_DIR,
    BUNDLED_TESSERACT_EXE,
    IMAGE_EXTENSIONS,
    LOW_CONFIDENCE_THRESHOLD,
    OCR_RENDER_DPI,
    PDF_EXTENSION,
    TESSDATA_DIR,
)
from .jobs import JobCancelled
from .pathsafe import ansi_safe_dir
from .textutil import strip_control_chars

ProgressCallback = Callable[[int, int, str], None]

_LANG_RE = re.compile(r"^[A-Za-z_]{3,12}$")
_SYSTEM_TESSDATA_DIRS = (
    Path(r"C:\Program Files\Tesseract-OCR\tessdata"),
    Path(r"C:\Program Files (x86)\Tesseract-OCR\tessdata"),
)
# Strona PDF z co najmniej tylu znakami (bez spacji) ma warstwe tekstowa
# i nie wymaga OCR.
_MIN_TEXT_LAYER_CHARS = 25
_MAX_RENDER_PIXELS = 50_000_000


class OCRLanguageMissingError(FileNotFoundError):
    """Brak pliku traineddata dla `lang_code`."""

    def __init__(self, lang_code: str) -> None:
        self.lang_code = lang_code
        super().__init__(lang_code)


class OCRError(RuntimeError):
    """Tesseract zakonczyl sie bledem. `details` to jego komunikat."""

    def __init__(self, details: str) -> None:
        self.details = details
        super().__init__(details)


class OCRDocumentError(RuntimeError):
    """Nie udalo sie otworzyc dokumentu wejsciowego (uszkodzony, zaszyfrowany)."""

    def __init__(self, path: Path, details: str) -> None:
        self.path = path
        self.details = details
        super().__init__(details)


class OCRCancelled(JobCancelled):
    """OCR przerwany przez uzytkownika."""


@dataclass
class OCRResult:
    text: str = ""
    # zakresy (start, koniec) w `text` slow rozpoznanych z mala pewnoscia
    low_confidence: list[tuple[int, int]] = field(default_factory=list)
    pages: int = 0
    text_layer_pages: int = 0

    def append(self, other: OCRResult, separator: str = "\n\n") -> None:
        if self.text and other.text:
            self.text += separator
        offset = len(self.text)
        self.text += other.text
        self.low_confidence.extend((s + offset, e + offset) for s, e in other.low_confidence)
        self.pages += other.pages
        self.text_layer_pages += other.text_layer_pages


def parse_languages(spec: str) -> list[str]:
    """'pol+eng' -> ['pol', 'eng'] z walidacja (kody trafiaja do wiersza polecen)."""
    langs = spec.split("+")
    if any(not _LANG_RE.match(lang) for lang in langs):
        raise ValueError(f"Niepoprawny kod jezyka OCR: {spec!r}")
    return langs


def parse_tsv(tsv: str, threshold: float = LOW_CONFIDENCE_THRESHOLD) -> OCRResult:
    """Sklada tekst ze slow w formacie TSV Tesseract i zapamietuje slowa o niskiej pewnosci.

    Uklad: slowa w linii oddzielone spacja, linie '\\n', akapity i bloki pusta linia.
    """
    pieces: list[str] = []
    spans: list[tuple[int, int]] = []
    length = 0
    previous: tuple[str, str, str] | None = None

    for raw in tsv.splitlines():
        parts = raw.split("\t", 11)
        if len(parts) < 12 or parts[0] != "5":
            continue
        word = parts[11].strip()
        if not word:
            continue
        block, paragraph, line = parts[2], parts[3], parts[4]

        if previous is not None:
            if (block, paragraph) != previous[:2]:
                separator = "\n\n"
            elif line != previous[2]:
                separator = "\n"
            else:
                separator = " "
            pieces.append(separator)
            length += len(separator)
        previous = (block, paragraph, line)

        try:
            confidence = float(parts[10])
        except ValueError:
            confidence = 100.0
        if 0 <= confidence < threshold:
            spans.append((length, length + len(word)))
        pieces.append(word)
        length += len(word)

    return OCRResult(text="".join(pieces), low_confidence=spans, pages=1)


def _prepare_image(image: Image.Image) -> Image.Image:
    """Normalizuje obraz do postaci akceptowanej przez Tesseract."""
    image = ImageOps.exif_transpose(image)  # zdjecia z telefonu bywaja obrocone w EXIF
    if image.mode in ("RGBA", "LA", "PA") or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        flattened = Image.new("RGB", rgba.size, "white")
        flattened.paste(rgba, mask=rgba.getchannel("A"))
        return flattened
    if image.mode.startswith("I") or image.mode == "F":
        return image.point(lambda value: value * (1 / 256)).convert("L")
    if image.mode not in ("1", "L", "RGB"):
        return image.convert("RGB")
    return image


def _png_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    # Bez informacji o DPI Tesseract zgaduje rozdzielczosc ("Estimating resolution").
    dpi = image.info.get("dpi")
    if not (isinstance(dpi, tuple) and len(dpi) == 2 and min(dpi) >= 70):
        dpi = (OCR_RENDER_DPI, OCR_RENDER_DPI)
    image.save(buffer, format="PNG", dpi=(int(dpi[0]), int(dpi[1])))
    return buffer.getvalue()


def _page_text_layer(page) -> str:
    """Tekst osadzony w stronie PDF, z akapitami rozpoznanymi po dlugosci linii."""
    textpage = page.get_textpage()
    try:
        raw = textpage.get_text_bounded()
    finally:
        textpage.close()
    raw = strip_control_chars(raw.replace("\r\n", "\n").replace("\r", "\n"))
    lines = [line.rstrip() for line in raw.split("\n")]
    lengths = sorted(len(line) for line in lines if line.strip())
    if not lengths:
        return ""
    typical = lengths[int(len(lengths) * 0.9) - 1 if len(lengths) > 1 else 0]
    result: list[str] = []
    for index, line in enumerate(lines):
        result.append(line)
        is_last = index == len(lines) - 1
        # linia wyraznie krotsza od typowej konczy akapit
        if line.strip() and not is_last and lines[index + 1].strip() and len(line) < typical * 0.7:
            result.append("")
    return "\n".join(result).strip()


class OCRService:
    def __init__(self) -> None:
        self._tesseract_cmd = self._resolve_tesseract_command()

    # ---------- silnik i jezyki ----------

    def _resolve_tesseract_command(self) -> str:
        # Silnik dolaczony do pakietu ma pierwszenstwo: dziala od razu po
        # instalacji i nie zalezy od tego, co uzytkownik ma w systemie.
        if BUNDLED_TESSERACT_EXE.exists():
            return str(BUNDLED_TESSERACT_EXE)

        # Zapasowo: instalacja systemowa (uruchomienie ze zrodel bez
        # wczesniejszego `python scripts/vendor_tesseract.py`).
        from_path = shutil.which("tesseract")
        if from_path:
            return from_path
        for candidate in (
            Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
            Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
            Path.home() / r"AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
        ):
            if candidate.exists():
                return str(candidate)
        return "tesseract"

    @property
    def uses_bundled_engine(self) -> bool:
        return Path(self._tesseract_cmd) == BUNDLED_TESSERACT_EXE

    def is_available(self) -> bool:
        """Czy silnik OCR jest gotowy do uzycia."""
        return Path(self._tesseract_cmd).exists() or shutil.which(self._tesseract_cmd) is not None

    @staticmethod
    def _find_traineddata(lang: str) -> Path | None:
        """Gdzie lezy plik jezyka: katalog uzytkownika, pakiet lub instalacja systemowa."""
        for directory in (TESSDATA_DIR, BUNDLED_TESSDATA_DIR, *_SYSTEM_TESSDATA_DIRS):
            candidate = directory / f"{lang}.traineddata"
            if candidate.exists():
                return candidate
        return None

    def ensure_lang_installed(self, lang_spec: str) -> Path:
        """Sprawdza, czy kazdy jezyk z `lang_spec` ('pol' lub 'pol+eng') jest dostepny."""
        found: Path | None = None
        for lang in parse_languages(lang_spec):
            found = self._find_traineddata(lang)
            if found is None:
                raise OCRLanguageMissingError(lang)
        assert found is not None
        return found

    def prepare_languages(self, lang_spec: str) -> Path:
        """Zwraca katalog tessdata z wszystkimi jezykami i sciezka bezpieczna dla Tesseract."""
        langs = parse_languages(lang_spec)
        sources = {}
        for lang in langs:
            source = self._find_traineddata(lang)
            if source is None:
                raise OCRLanguageMissingError(lang)
            sources[lang] = source

        # Wszystkie jezyki w pakiecie: uzywamy katalogu pakietu bezposrednio
        # (sciezka ASCII, bez kopiowania do profilu uzytkownika).
        if all(src.parent == BUNDLED_TESSDATA_DIR for src in sources.values()):
            return BUNDLED_TESSDATA_DIR

        # Mieszanka: wszystkie pliki musza lezec w jednym katalogu.
        TESSDATA_DIR.mkdir(parents=True, exist_ok=True)
        for lang, source in sources.items():
            target = TESSDATA_DIR / f"{lang}.traineddata"
            if source != target and not target.exists():
                shutil.copy2(source, target)
        # czcionka warstwy tekstowej PDF musi lezec obok plikow jezykowych
        font = BUNDLED_TESSDATA_DIR / "pdf.ttf"
        if font.exists() and not (TESSDATA_DIR / "pdf.ttf").exists():
            shutil.copy2(font, TESSDATA_DIR / "pdf.ttf")

        wanted = [f"{lang}.traineddata" for lang in langs] + ["pdf.ttf"]
        return ansi_safe_dir(TESSDATA_DIR, copy_files=wanted)

    # ---------- uruchamianie Tesseract ----------

    def _run_tesseract(
        self,
        args: list[str],
        data: bytes,
        tessdata_dir: Path,
        cancel: threading.Event | None,
    ) -> bytes:
        env = os.environ.copy()
        env["TESSDATA_PREFIX"] = str(tessdata_dir)

        kwargs: dict = {}
        if sys.platform.startswith("win"):
            # Aplikacja okienkowa: bez tego kazde wywolanie otwieralo okno konsoli.
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            startup = subprocess.STARTUPINFO()
            startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startup.wShowWindow = subprocess.SW_HIDE
            kwargs["startupinfo"] = startup

        process = subprocess.Popen(
            [self._tesseract_cmd, *args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            **kwargs,
        )

        pending: bytes | None = data
        while True:
            try:
                stdout, stderr = process.communicate(input=pending, timeout=0.2)
                break
            except subprocess.TimeoutExpired:
                pending = None
                if cancel is not None and cancel.is_set():
                    process.kill()
                    process.communicate()
                    raise OCRCancelled() from None

        if process.returncode != 0:
            details = stderr.decode("utf-8", errors="replace").strip()
            raise OCRError(details or f"Tesseract zakonczyl sie kodem {process.returncode}.")
        return stdout

    def _ocr_image(
        self,
        image: Image.Image,
        lang_spec: str,
        tessdata_dir: Path,
        cancel: threading.Event | None,
        threshold: float,
    ) -> OCRResult:
        prepared = _prepare_image(image)
        output = self._run_tesseract(
            ["stdin", "stdout", "-l", lang_spec, "--tessdata-dir", str(tessdata_dir), "-c", "tessedit_create_tsv=1"],
            _png_bytes(prepared),
            tessdata_dir,
            cancel,
        )
        return parse_tsv(output.decode("utf-8", errors="replace"), threshold)

    def _image_to_pdf_bytes(
        self,
        image: Image.Image,
        lang_spec: str,
        tessdata_dir: Path,
        cancel: threading.Event | None,
    ) -> bytes:
        return self._run_tesseract(
            ["stdin", "stdout", "-l", lang_spec, "--tessdata-dir", str(tessdata_dir), "-c", "tessedit_create_pdf=1"],
            _png_bytes(_prepare_image(image)),
            tessdata_dir,
            cancel,
        )

    # ---------- dokumenty ----------

    @staticmethod
    def _check_cancel(cancel: threading.Event | None) -> None:
        if cancel is not None and cancel.is_set():
            raise OCRCancelled()

    @staticmethod
    def _open_pdf(path: Path):
        import pypdfium2 as pdfium

        try:
            return pdfium.PdfDocument(str(path))
        except pdfium.PdfiumError as exc:
            raise OCRDocumentError(path, str(exc)) from exc

    @staticmethod
    def _render_page(page, *, grayscale: bool) -> Image.Image:
        scale = OCR_RENDER_DPI / 72
        width, height = page.get_size()
        pixels = (width * scale) * (height * scale)
        if pixels > _MAX_RENDER_PIXELS:
            scale *= math.sqrt(_MAX_RENDER_PIXELS / pixels)
        return page.render(scale=scale, grayscale=grayscale).to_pil()

    def ocr_document(
        self,
        path: Path,
        lang_spec: str,
        *,
        progress: ProgressCallback | None = None,
        cancel: threading.Event | None = None,
        force_ocr: bool = False,
        threshold: float = LOW_CONFIDENCE_THRESHOLD,
    ) -> OCRResult:
        """OCR obrazu (wszystkie ramki TIFF) lub PDF (z uzyciem warstwy tekstowej, gdy jest)."""
        tessdata_dir = self.prepare_languages(lang_spec)
        if path.suffix.lower() == PDF_EXTENSION:
            return self._ocr_pdf(path, lang_spec, tessdata_dir, progress, cancel, force_ocr, threshold)
        return self._ocr_image_file(path, lang_spec, tessdata_dir, progress, cancel, threshold)

    def _ocr_image_file(self, path, lang_spec, tessdata_dir, progress, cancel, threshold) -> OCRResult:
        result = OCRResult()
        with Image.open(path) as image:
            total = max(1, getattr(image, "n_frames", 1))
            for index in range(total):
                self._check_cancel(cancel)
                if progress:
                    progress(index, total, path.name)
                image.seek(index)
                result.append(self._ocr_image(image, lang_spec, tessdata_dir, cancel, threshold))
            if progress:
                progress(total, total, path.name)
        return result

    def _ocr_pdf(self, path, lang_spec, tessdata_dir, progress, cancel, force_ocr, threshold) -> OCRResult:
        result = OCRResult()
        pdf = self._open_pdf(path)
        try:
            total = len(pdf)
            for index in range(total):
                self._check_cancel(cancel)
                if progress:
                    progress(index, total, path.name)
                page = pdf[index]

                layer = "" if force_ocr else _page_text_layer(page)
                if len(re.sub(r"\s", "", layer)) >= _MIN_TEXT_LAYER_CHARS:
                    result.append(OCRResult(text=layer, pages=1, text_layer_pages=1))
                    continue

                image = self._render_page(page, grayscale=True)
                result.append(self._ocr_image(image, lang_spec, tessdata_dir, cancel, threshold))
            if progress:
                progress(total, total, path.name)
        finally:
            pdf.close()
        return result

    def export_searchable_pdf(
        self,
        path: Path,
        output_path: Path,
        lang_spec: str,
        *,
        progress: ProgressCallback | None = None,
        cancel: threading.Event | None = None,
        force_ocr: bool = False,
    ) -> int:
        """Zapisuje PDF z niewidoczna warstwa tekstowa. Zwraca liczbe stron.

        Strony PDF, ktore juz maja tekst, sa przepisywane bez zmian (zachowuja
        jakosc wektorowa); pozostale sa rozpoznawane i skladane w jeden plik.
        """
        import pypdfium2 as pdfium

        tessdata_dir = self.prepare_languages(lang_spec)
        merged = pdfium.PdfDocument.new()
        keepalive: list = []
        try:
            if path.suffix.lower() == PDF_EXTENSION:
                source = self._open_pdf(path)
                keepalive.append(source)
                total = len(source)
                for index in range(total):
                    self._check_cancel(cancel)
                    if progress:
                        progress(index, total, path.name)
                    page = source[index]
                    layer = "" if force_ocr else _page_text_layer(page)
                    if len(re.sub(r"\s", "", layer)) >= _MIN_TEXT_LAYER_CHARS:
                        merged.import_pages(source, [index])
                    else:
                        image = self._render_page(page, grayscale=False)
                        data = self._image_to_pdf_bytes(image, lang_spec, tessdata_dir, cancel)
                        part = pdfium.PdfDocument(data)
                        keepalive.append(part)
                        merged.import_pages(part)
            else:
                with Image.open(path) as image:
                    total = max(1, getattr(image, "n_frames", 1))
                    for index in range(total):
                        self._check_cancel(cancel)
                        if progress:
                            progress(index, total, path.name)
                        image.seek(index)
                        data = self._image_to_pdf_bytes(image, lang_spec, tessdata_dir, cancel)
                        part = pdfium.PdfDocument(data)
                        keepalive.append(part)
                        merged.import_pages(part)

            if progress:
                progress(total, total, path.name)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            merged.save(str(output_path))
            return total
        finally:
            for doc in keepalive:
                doc.close()
            merged.close()


def is_supported_input(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_EXTENSIONS or path.suffix.lower() == PDF_EXTENSION
