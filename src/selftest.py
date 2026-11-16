"""Nieinteraktywny test dymny: `OCR Studio.exe --selftest wynik.json`.

Sprawdza to, co bylo przyczyna odrzucenia wersji 0.2.0 w Microsoft Store:
czy aplikacja dziala na czystym komputerze, bez Tesseract w systemie i bez
internetu. Uruchamiany z pakietu (zamrozonego) potwierdza, ze wbudowany silnik,
jezyki i slowniki sa na miejscu i dzialaja.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


def _font(size: int) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    for name in ("arial.ttf", "segoeui.ttf", "calibri.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _sample_image(path: Path, lines: list[str]) -> Path:
    image = Image.new("RGB", (1500, 120 + 80 * len(lines)), "white")
    draw = ImageDraw.Draw(image)
    for index, line in enumerate(lines):
        draw.text((60, 50 + index * 80), line, fill="black", font=_font(48))
    image.save(path, dpi=(200, 200))
    return path


def run_selftest() -> dict[str, Any]:
    from .config import APP_VERSION, BUNDLED_DICTS_DIR, DATA_DIR
    from .export_service import ExportService
    from .ocr_service import OCRService
    from .spellcheck_service import SpellcheckService

    checks: list[dict[str, Any]] = []

    def check(name: str, function: Callable[[], str]) -> None:
        try:
            checks.append({"name": name, "ok": True, "detail": function()})
        except Exception as exc:  # noqa: BLE001 - raport ma pokazac kazdy rodzaj awarii
            checks.append({"name": name, "ok": False, "detail": f"{type(exc).__name__}: {exc}"})

    service = OCRService()
    workdir = Path(tempfile.mkdtemp(prefix="studio_ocr_selftest_"))

    def engine() -> str:
        if not service.uses_bundled_engine:
            raise RuntimeError(f"uzywa silnika spoza pakietu: {service._tesseract_cmd}")
        result = subprocess.run(
            [service._tesseract_cmd, "--version"],
            capture_output=True,
            text=True,
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return (result.stdout or result.stderr).splitlines()[0].strip()

    def languages() -> str:
        service.ensure_lang_installed("pol+eng")
        return "pol, eng"

    def ocr_polish() -> str:
        image = _sample_image(workdir / "pl.png", ["Zażółć gęślą jaźń", "Studio OCR działa"])
        text = service.ocr_document(image, "pol").text
        if "Zażółć" not in text or "działa" not in text:
            raise RuntimeError(f"niepoprawny wynik: {text!r}")
        return text.splitlines()[0]

    def searchable_pdf() -> str:
        image = _sample_image(workdir / "pdf.png", ["Przeszukiwalny dokument alpha bravo"])
        pdf = workdir / "out.pdf"
        service.export_searchable_pdf(image, pdf, "pol")
        again = service.ocr_document(pdf, "pol")
        if again.text_layer_pages != 1 or "alpha" not in again.text:
            raise RuntimeError("warstwa tekstowa PDF nie zostala odczytana")
        return "PDF z warstwa tekstowa OK"

    def spelling() -> str:
        parts = []
        for code, bad in (("pl_PL", "To jest dokumnet"), ("en_US", "This is a dokument")):
            if not (BUNDLED_DICTS_DIR / code / f"{code}.dic").exists():
                raise RuntimeError(f"brak wbudowanego slownika {code}")
            errors = SpellcheckService(code).find_errors(bad)
            if not errors:
                raise RuntimeError(f"slownik {code} nie wykryl bledu w {bad!r}")
            parts.append(f"{code}: {errors[0].word}")
        return ", ".join(parts)

    def docx_export() -> str:
        target = workdir / "out.docx"
        ExportService.export_docx("Linia pierwsza\x0c\nLinia druga\x00", target)
        return f"{target.stat().st_size} B"

    def data_dir() -> str:
        probe = DATA_DIR / ".selftest"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return str(DATA_DIR)

    def drag_and_drop() -> str:
        # Informacyjnie: brak tkdnd nie blokuje aplikacji (przeciaganie plikow jest dodatkiem),
        # ale w pakiecie ma byc - ten test wylapie jej zgubienie przez PyInstaller.
        import tkinter

        from tkinterdnd2 import TkinterDnD

        root = tkinter.Tk()
        root.withdraw()
        try:
            return f"tkdnd {TkinterDnD._require(root)}"
        finally:
            root.destroy()

    check("engine", engine)
    check("languages", languages)
    check("ocr_polish", ocr_polish)
    check("searchable_pdf", searchable_pdf)
    check("spelling", spelling)
    check("docx_export", docx_export)
    check("data_dir_writable", data_dir)
    check("drag_and_drop", drag_and_drop)

    return {
        "version": APP_VERSION,
        "frozen": bool(getattr(sys, "frozen", False)),
        "ok": all(item["ok"] for item in checks),
        "checks": checks,
    }


def main(argv: list[str]) -> int:
    """`--selftest [plik.json]`: zapisuje raport (lub drukuje) i zwraca 0 tylko gdy wszystko dziala."""
    report = run_selftest()
    text = json.dumps(report, ensure_ascii=False, indent=2)
    index = argv.index("--selftest")
    if index + 1 < len(argv) and not argv[index + 1].startswith("-"):
        Path(argv[index + 1]).write_text(text, encoding="utf-8")
    else:
        print(text)
    return 0 if report["ok"] else 1
