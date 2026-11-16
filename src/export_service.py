from __future__ import annotations

import re
from pathlib import Path

from docx import Document

from .textutil import reflow_paragraphs, strip_control_chars


class ExportService:
    @staticmethod
    def prepare_text(text: str, reflow: bool = False) -> str:
        """Tekst do zapisu: bez znakow sterujacych, opcjonalnie z zlaczonymi liniami akapitow."""
        text = strip_control_chars(text)
        return reflow_paragraphs(text) if reflow else text.strip()

    @staticmethod
    def export_txt(text: str, output_path: Path, reflow: bool = False) -> Path:
        output_path.write_text(ExportService.prepare_text(text, reflow) + "\n", encoding="utf-8")
        return output_path

    @staticmethod
    def export_docx(text: str, output_path: Path, reflow: bool = False) -> Path:
        prepared = ExportService.prepare_text(text, reflow)
        document = Document()
        if reflow:
            # akapity rozdzielone pusta linia -> jeden akapit DOCX na blok
            for block in re.split(r"\n\s*\n", prepared):
                if block.strip():
                    document.add_paragraph(block.strip())
        else:
            for line in prepared.split("\n"):
                document.add_paragraph(line)
        document.save(str(output_path))
        return output_path
