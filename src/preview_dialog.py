from __future__ import annotations

from pathlib import Path
from typing import Callable

import customtkinter as ctk
from PIL import Image, ImageTk


class ScanPreviewDialog(ctk.CTkToplevel):
    """Podglad zeskanowanego dokumentu z opcja uruchomienia OCR."""

    def __init__(
        self,
        master: ctk.CTk,
        file_path: Path,
        on_ocr: Callable[[], None],
    ) -> None:
        super().__init__(master)
        self.file_path = file_path
        self.on_ocr = on_ocr

        self.title("Podglad skanu")
        self.geometry("820x640")
        self.transient(master)
        self.grab_set()

        header = ctk.CTkLabel(
            self,
            text=f"Zeskanowano: {file_path.name}",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        header.pack(padx=16, pady=(14, 8), anchor="w")

        self.preview_frame = ctk.CTkScrollableFrame(self, width=760, height=480)
        self.preview_frame.pack(padx=16, pady=8, fill="both", expand=True)

        self._photo_ref: ImageTk.PhotoImage | None = None
        self._render_preview()

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(padx=16, pady=(8, 16), fill="x")

        ctk.CTkButton(
            buttons,
            text="Dokonaj OCR",
            fg_color="#2f9e44",
            hover_color="#237a35",
            command=self._start_ocr,
            width=180,
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(buttons, text="Zamknij", command=self.destroy, width=120).pack(side="right")

    def _render_preview(self) -> None:
        suffix = self.file_path.suffix.lower()
        try:
            if suffix == ".pdf":
                self._render_pdf_preview()
            else:
                self._render_image_preview()
        except Exception as exc:
            ctk.CTkLabel(
                self.preview_frame,
                text=f"Nie udalo sie wyswietlic podgladu: {exc}",
                wraplength=700,
            ).pack(padx=12, pady=12)

    def _render_image_preview(self) -> None:
        with Image.open(self.file_path) as img:
            display = self._fit_image(img.copy())
        self._photo_ref = ImageTk.PhotoImage(display)
        label = ctk.CTkLabel(self.preview_frame, text="", image=self._photo_ref)
        label.pack(padx=8, pady=8)

    def _render_pdf_preview(self) -> None:
        import pypdfium2 as pdfium

        pdf = pdfium.PdfDocument(str(self.file_path))
        page_count = len(pdf)
        ctk.CTkLabel(
            self.preview_frame,
            text=f"PDF — {page_count} stron(y). Ponizej podglad pierwszej strony.",
            font=ctk.CTkFont(weight="bold"),
        ).pack(padx=8, pady=(8, 4), anchor="w")

        page = pdf[0]
        bitmap = page.render(scale=1.5)
        pil_image = bitmap.to_pil()
        pdf.close()

        display = self._fit_image(pil_image)
        self._photo_ref = ImageTk.PhotoImage(display)
        label = ctk.CTkLabel(self.preview_frame, text="", image=self._photo_ref)
        label.pack(padx=8, pady=8)

    def _fit_image(self, image: Image.Image, max_w: int = 720, max_h: int = 420) -> Image.Image:
        image.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
        return image

    def _start_ocr(self) -> None:
        self.destroy()
        self.on_ocr()
