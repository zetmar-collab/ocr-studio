from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import customtkinter as ctk
from PIL import Image, ImageOps

from .i18n import I18n


class ScanPreviewDialog(ctk.CTkToplevel):
    """Podglad zeskanowanego dokumentu z opcja uruchomienia OCR."""

    def __init__(
        self,
        master: ctk.CTk,
        file_path: Path,
        on_ocr: Callable[[], None],
        i18n: I18n | None = None,
    ) -> None:
        super().__init__(master)
        self.file_path = file_path
        self.on_ocr = on_ocr
        self.i18n = i18n or I18n()
        t = self.i18n.t

        self.title(t("preview.title"))
        self.geometry("820x640")
        self.transient(master)
        # grab_set() na jeszcze niewidocznym oknie bywa odrzucane przez Tk
        # ("window not viewable"), wiec czekamy az okno sie pojawi.
        self.after(100, self._safe_grab)

        header = ctk.CTkLabel(
            self,
            text=t("preview.scanned", name=file_path.name),
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        header.pack(padx=16, pady=(14, 8), anchor="w")

        self.preview_frame = ctk.CTkScrollableFrame(self, width=760, height=480)
        self.preview_frame.pack(padx=16, pady=8, fill="both", expand=True)

        self._image_ref: ctk.CTkImage | None = None
        self._render_preview()

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(padx=16, pady=(8, 16), fill="x")

        ctk.CTkButton(
            buttons,
            text=t("btn.do_ocr"),
            fg_color="#2f9e44",
            hover_color="#237a35",
            command=self._start_ocr,
            width=180,
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(buttons, text=t("btn.close"), command=self.destroy, width=120).pack(side="right")

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
                text=self.i18n.t("preview.render_error", error=str(exc)),
                wraplength=700,
            ).pack(padx=12, pady=12)

    def _safe_grab(self) -> None:
        try:
            if self.winfo_exists():
                self.grab_set()
        except Exception:
            # podglad dziala tez bez blokowania glownego okna
            pass

    def _show_image(self, image: Image.Image) -> None:
        display = self._fit_image(image)
        self._image_ref = ctk.CTkImage(light_image=display, dark_image=display, size=display.size)
        ctk.CTkLabel(self.preview_frame, text="", image=self._image_ref).pack(padx=8, pady=8)

    def _render_image_preview(self) -> None:
        with Image.open(self.file_path) as img:
            # pierwsza ramka (TIFF wielostronicowy), z uwzglednieniem obrotu z EXIF
            self._show_image(ImageOps.exif_transpose(img).convert("RGB"))

    def _render_pdf_preview(self) -> None:
        import pypdfium2 as pdfium

        pdf = pdfium.PdfDocument(str(self.file_path))
        try:
            page_count = len(pdf)
            ctk.CTkLabel(
                self.preview_frame,
                text=self.i18n.t("preview.pdf_info", pages=page_count),
                font=ctk.CTkFont(weight="bold"),
            ).pack(padx=8, pady=(8, 4), anchor="w")
            if page_count == 0:
                return
            pil_image = pdf[0].render(scale=1.5).to_pil()
        finally:
            pdf.close()
        self._show_image(pil_image)

    def _fit_image(self, image: Image.Image, max_w: int = 720, max_h: int = 420) -> Image.Image:
        image.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
        return image

    def _start_ocr(self) -> None:
        self.destroy()
        self.on_ocr()
