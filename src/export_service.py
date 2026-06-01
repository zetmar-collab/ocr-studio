from __future__ import annotations

from pathlib import Path

from docx import Document


class ExportService:
    @staticmethod
    def export_txt(text: str, output_path: Path) -> Path:
        output_path.write_text(text, encoding="utf-8")
        return output_path

    @staticmethod
    def export_docx(text: str, output_path: Path) -> Path:
        document = Document()
        for paragraph in text.split("\n"):
            document.add_paragraph(paragraph)
        document.save(str(output_path))
        return output_path
