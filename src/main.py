from __future__ import annotations

import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from .config import (
    APP_AUTHOR,
    APP_NAME,
    APP_VERSION,
    OCR_LANG_MAP,
    SPELL_LANG_MAP,
)
from .export_service import ExportService
from .i18n import I18n
from .language_manager import LanguageManager
from .icon_utils import ensure_app_icon
from .ocr_service import OCRLanguageMissingError, OCRService
from .preview_dialog import ScanPreviewDialog
from .scanner_service import ScannerService, ScannerUnavailableError
from .settings import load_settings, save_settings
from .spellcheck_service import SpellcheckService, SpellDictionaryMissingError

THEME_MODES = ["System", "Light", "Dark"]
LANGUAGE_CODES = ["pl", "en"]


class OCRStudioApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        settings = load_settings()
        self.i18n = I18n(settings.get("language", "pl"))
        self._theme_mode = settings.get("theme", "System")
        if self._theme_mode not in THEME_MODES:
            self._theme_mode = "System"
        ctk.set_appearance_mode(self._theme_mode)

        self.geometry("1200x760")

        self.language_manager = LanguageManager()
        self.ocr_service = OCRService()
        self.current_input_file: Path | None = None
        self.spell_errors: list[dict[str, object]] = []

        # Owned by the app (not by any widget) so they survive UI rebuilds
        # triggered by a language change.
        self.status_var = ctk.StringVar(value=self.i18n.t("status.ready"))
        self.path_var = ctk.StringVar(value=self.i18n.t("lbl.no_file"))
        self.ocr_lang_var = ctk.StringVar(value="Polski")
        self.spell_lang_var = ctk.StringVar(value="Polski (pl_PL)")

        icon_path = ensure_app_icon()
        try:
            self.iconbitmap(str(icon_path))
        except Exception:
            # Na niektorych konfiguracjach Windows fallback jest ignorowany.
            pass

        self._build_ui()
        self._refresh_installed_languages()

    def _save_settings(self) -> None:
        save_settings({"theme": self._theme_mode, "language": self.i18n.language})

    def _build_ui(self) -> None:
        self.title(f"{APP_NAME} - {APP_VERSION}")
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        t = self.i18n.t

        title = ctk.CTkLabel(
            self,
            text=f"{APP_NAME}  |  {t('app.author')}: {APP_AUTHOR}  |  ver. {APP_VERSION}",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title.grid(row=0, column=0, columnspan=2, padx=16, pady=(12, 8), sticky="w")

        sidebar = ctk.CTkScrollableFrame(self, width=340)
        sidebar.grid(row=1, column=0, padx=(12, 8), pady=12, sticky="nswe")
        sidebar.grid_columnconfigure(0, weight=1)

        content = ctk.CTkFrame(self)
        content.grid(row=1, column=1, padx=(8, 12), pady=12, sticky="nswe")
        content.grid_rowconfigure(1, weight=1)
        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(1, weight=0)

        ctk.CTkLabel(sidebar, text=t("sec.source"), font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, padx=10, pady=(10, 6), sticky="w"
        )
        ctk.CTkButton(sidebar, text=t("btn.load_file"), command=self._pick_file).grid(
            row=1, column=0, padx=10, pady=4, sticky="ew"
        )
        ctk.CTkButton(sidebar, text=t("btn.scan_png"), command=lambda: self._scan("png")).grid(
            row=2, column=0, padx=10, pady=4, sticky="ew"
        )
        ctk.CTkButton(sidebar, text=t("btn.scan_jpeg"), command=lambda: self._scan("jpeg")).grid(
            row=3, column=0, padx=10, pady=4, sticky="ew"
        )
        ctk.CTkButton(sidebar, text=t("btn.scan_pdf"), command=lambda: self._scan("pdf")).grid(
            row=4, column=0, padx=10, pady=(4, 10), sticky="ew"
        )
        ctk.CTkLabel(sidebar, textvariable=self.path_var, wraplength=300).grid(
            row=5, column=0, padx=10, pady=(0, 10), sticky="w"
        )

        ctk.CTkLabel(sidebar, text=t("sec.ocr_lang"), font=ctk.CTkFont(weight="bold")).grid(
            row=6, column=0, padx=10, pady=(10, 4), sticky="w"
        )
        self.ocr_lang_menu = ctk.CTkOptionMenu(sidebar, values=list(OCR_LANG_MAP.keys()), variable=self.ocr_lang_var)
        self.ocr_lang_menu.grid(row=7, column=0, padx=10, pady=4, sticky="ew")
        ctk.CTkButton(sidebar, text=t("btn.install_ocr_lang"), command=self._install_ocr_language).grid(
            row=8, column=0, padx=10, pady=4, sticky="ew"
        )

        ctk.CTkLabel(sidebar, text=t("sec.spelling"), font=ctk.CTkFont(weight="bold")).grid(
            row=9, column=0, padx=10, pady=(12, 4), sticky="w"
        )
        self.spell_lang_menu = ctk.CTkOptionMenu(sidebar, values=list(SPELL_LANG_MAP.keys()), variable=self.spell_lang_var)
        self.spell_lang_menu.grid(row=10, column=0, padx=10, pady=4, sticky="ew")
        ctk.CTkButton(sidebar, text=t("btn.install_spell_dict"), command=self._install_spell_language).grid(
            row=11, column=0, padx=10, pady=4, sticky="ew"
        )
        ctk.CTkButton(sidebar, text=t("btn.spellcheck"), command=self._run_spellcheck).grid(
            row=12, column=0, padx=10, pady=4, sticky="ew"
        )
        ctk.CTkButton(sidebar, text=t("btn.add_word"), command=self._add_selected_word).grid(
            row=13, column=0, padx=10, pady=4, sticky="ew"
        )

        ctk.CTkLabel(sidebar, text=t("sec.export"), font=ctk.CTkFont(weight="bold")).grid(
            row=14, column=0, padx=10, pady=(12, 4), sticky="w"
        )
        ctk.CTkButton(sidebar, text=t("btn.export_txt"), command=self._export_txt).grid(
            row=15, column=0, padx=10, pady=4, sticky="ew"
        )
        ctk.CTkButton(sidebar, text=t("btn.export_docx"), command=self._export_docx).grid(
            row=16, column=0, padx=10, pady=4, sticky="ew"
        )

        ctk.CTkLabel(sidebar, text=t("sec.appearance"), font=ctk.CTkFont(weight="bold")).grid(
            row=17, column=0, padx=10, pady=(12, 4), sticky="w"
        )
        theme_labels = {
            "System": t("theme.system"),
            "Light": t("theme.light"),
            "Dark": t("theme.dark"),
        }
        self._theme_label_to_mode = {label: mode for mode, label in theme_labels.items()}
        self.theme_display_var = ctk.StringVar(value=theme_labels[self._theme_mode])
        theme_seg = ctk.CTkSegmentedButton(
            sidebar,
            values=[theme_labels[mode] for mode in THEME_MODES],
            command=self._on_theme_changed,
            variable=self.theme_display_var,
        )
        theme_seg.grid(row=18, column=0, padx=10, pady=(4, 10), sticky="ew")

        ctk.CTkLabel(sidebar, text=t("sec.app_language"), font=ctk.CTkFont(weight="bold")).grid(
            row=19, column=0, padx=10, pady=(4, 4), sticky="w"
        )
        lang_labels = {"pl": "PL", "en": "EN"}
        self._lang_label_to_code = {label: code for code, label in lang_labels.items()}
        self.lang_display_var = ctk.StringVar(value=lang_labels[self.i18n.language])
        lang_seg = ctk.CTkSegmentedButton(
            sidebar,
            values=[lang_labels[code] for code in LANGUAGE_CODES],
            command=self._on_language_changed,
            variable=self.lang_display_var,
        )
        lang_seg.grid(row=20, column=0, padx=10, pady=(4, 10), sticky="ew")

        ctk.CTkButton(sidebar, text=t("btn.run_ocr"), fg_color="#2f9e44", hover_color="#237a35", command=self._run_ocr).grid(
            row=21, column=0, padx=10, pady=(8, 10), sticky="ew"
        )

        ocr_header = ctk.CTkFrame(content, fg_color="transparent")
        ocr_header.grid(row=0, column=0, columnspan=2, padx=12, pady=(10, 4), sticky="ew")
        ocr_header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(ocr_header, text=t("lbl.result_header"), font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, sticky="w"
        )
        ocr_actions = ctk.CTkFrame(ocr_header, fg_color="transparent")
        ocr_actions.grid(row=0, column=1, sticky="e")
        ctk.CTkButton(
            ocr_actions,
            text=t("btn.copy_clipboard"),
            command=self._copy_ocr_to_clipboard,
            width=150,
        ).pack(side="right", padx=(6, 0))
        ctk.CTkButton(
            ocr_actions,
            text=t("btn.new_document"),
            command=self._new_document,
            width=130,
            fg_color="#b45309",
            hover_color="#92400e",
        ).pack(side="right", padx=(6, 0))
        ctk.CTkButton(
            ocr_actions,
            text=t("btn.run_ocr"),
            fg_color="#2f9e44",
            hover_color="#237a35",
            command=self._run_ocr,
            width=150,
        ).pack(side="right")

        self.textbox = ctk.CTkTextbox(content, wrap="word")
        self.textbox.grid(row=1, column=0, columnspan=2, padx=12, pady=(0, 8), sticky="nswe")

        spell_header = ctk.CTkFrame(content, fg_color="transparent")
        spell_header.grid(row=2, column=0, columnspan=2, padx=12, pady=(8, 4), sticky="ew")
        spell_header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(spell_header, text=t("lbl.errors_header"), font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, sticky="w"
        )
        spell_actions = ctk.CTkFrame(spell_header, fg_color="transparent")
        spell_actions.grid(row=0, column=1, sticky="e")
        ctk.CTkButton(
            spell_actions,
            text=t("btn.ignore"),
            command=self._ignore_spelling,
            width=110,
            fg_color="#6b7280",
            hover_color="#4b5563",
        ).pack(side="right", padx=(6, 0))
        ctk.CTkButton(
            spell_actions,
            text=t("btn.fix_spelling"),
            command=self._fix_spelling,
            width=140,
            fg_color="#2563eb",
            hover_color="#1d4ed8",
        ).pack(side="right")

        self.errors_box = ctk.CTkTextbox(content, height=160)
        self.errors_box.grid(row=3, column=0, columnspan=2, padx=12, pady=(0, 10), sticky="ew")

        status = ctk.CTkLabel(self, textvariable=self.status_var)
        status.grid(row=2, column=0, columnspan=2, padx=12, pady=(0, 10), sticky="w")

    def _rebuild_ui(self) -> None:
        ocr_text = self.textbox.get("1.0", "end-1c")
        errors_text = self.errors_box.get("1.0", "end-1c")

        for child in list(self.winfo_children()):
            child.destroy()

        self._build_ui()

        if ocr_text:
            self.textbox.insert("1.0", ocr_text)
        if errors_text:
            self.errors_box.insert("1.0", errors_text)

        self._refresh_installed_languages()

    def _set_status(self, message: str) -> None:
        self.status_var.set(message)

    def _refresh_installed_languages(self) -> None:
        t = self.i18n.t
        installed_ocr = ", ".join(self.language_manager.list_installed_ocr()) or t("status.none")
        installed_spell = ", ".join(self.language_manager.list_installed_spell()) or t("status.none")
        self._set_status(t("status.langs", ocr=installed_ocr, spell=installed_spell))

    def _pick_file(self) -> None:
        file_path = filedialog.askopenfilename(
            title=self.i18n.t("btn.load_file"),
            filetypes=[
                ("Dokumenty OCR", "*.pdf *.png *.jpg *.jpeg *.bmp *.tiff"),
                ("Wszystkie pliki", "*.*"),
            ],
        )
        if not file_path:
            return
        self.current_input_file = Path(file_path)
        self.path_var.set(str(self.current_input_file))

    def _scan(self, fmt: str) -> None:
        t = self.i18n.t
        ext = ".pdf" if fmt == "pdf" else (".jpg" if fmt == "jpeg" else ".png")
        filetypes = {
            ".png": [("Obraz PNG", "*.png")],
            ".jpg": [("Obraz JPEG", "*.jpg;*.jpeg")],
            ".pdf": [("Dokument PDF", "*.pdf")],
        }
        save_path = filedialog.asksaveasfilename(
            title=t("dlg.scan"),
            defaultextension=ext,
            filetypes=filetypes[ext] + [("Wszystkie pliki", "*.*")],
            initialfile=f"skan{ext}",
        )
        if not save_path:
            return

        target = Path(save_path)
        try:
            scanner = ScannerService()
            scanned = scanner.scan_to_file(target, fmt=fmt)
            self.current_input_file = scanned
            self.path_var.set(str(scanned))
            self._set_status(t("status.scan_done", name=scanned.name))
            self._show_scan_preview(scanned)
        except ScannerUnavailableError as exc:
            messagebox.showerror(t("dlg.scan"), t(f"err.scanner.{exc.key}"))
        except Exception as exc:
            messagebox.showerror(t("dlg.scan"), t("msg.scan_failed", error=str(exc)))

    def _show_scan_preview(self, file_path: Path) -> None:
        ScanPreviewDialog(self, file_path, on_ocr=self._run_ocr, i18n=self.i18n)

    def _run_ocr(self) -> None:
        t = self.i18n.t
        if not self.ocr_service.is_available():
            messagebox.showwarning(t("dlg.ocr"), t("msg.no_tesseract"))
            return
        if not self.current_input_file:
            messagebox.showwarning(t("dlg.ocr"), t("msg.no_file_selected"))
            return
        language_name = self.ocr_lang_var.get()
        lang_code = OCR_LANG_MAP[language_name]
        try:
            self.ocr_service.ensure_lang_installed(lang_code)
        except OCRLanguageMissingError as exc:
            messagebox.showwarning(t("dlg.ocr"), t("msg.lang_missing", lang=exc.lang_code))
            return
        self._set_status(t("status.ocr_running"))

        def worker() -> None:
            try:
                suffix = self.current_input_file.suffix.lower()
                if suffix == ".pdf":
                    text = self.ocr_service.pdf_to_text(self.current_input_file, lang_code)
                else:
                    text = self.ocr_service.image_to_text(self.current_input_file, lang_code)
                self.after(0, lambda: self._set_ocr_text(text))
                self.after(0, lambda: self._set_status(t("status.ocr_done")))
            except Exception as exc:
                error_message = str(exc)
                self.after(0, lambda: messagebox.showerror(t("dlg.ocr"), t("msg.ocr_error", error=error_message)))
                self.after(0, lambda: self._set_status(t("status.ocr_error")))

        threading.Thread(target=worker, daemon=True).start()

    def _set_ocr_text(self, text: str) -> None:
        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", text)

    def _install_ocr_language(self) -> None:
        t = self.i18n.t
        language_name = self.ocr_lang_var.get()
        lang_code = OCR_LANG_MAP[language_name]
        try:
            self.language_manager.install_ocr_language(lang_code)
            self._refresh_installed_languages()
            messagebox.showinfo(t("dlg.ocr_lang"), t("msg.ocr_lang_installed", lang=lang_code))
        except Exception as exc:
            messagebox.showerror(t("dlg.ocr_lang"), t("msg.ocr_lang_failed", error=str(exc)))

    def _install_spell_language(self) -> None:
        t = self.i18n.t
        dict_label = self.spell_lang_var.get()
        dict_code = SPELL_LANG_MAP[dict_label]
        try:
            self.language_manager.install_spell_dictionary(dict_code)
            self._refresh_installed_languages()
            messagebox.showinfo(t("dlg.spelling"), t("msg.spell_dict_installed", dict=dict_code))
        except Exception as exc:
            messagebox.showerror(t("dlg.spelling"), t("msg.spell_dict_failed", error=str(exc)))

    def _run_spellcheck(self) -> None:
        t = self.i18n.t
        text = self.textbox.get("1.0", "end").strip()
        if not text:
            messagebox.showwarning(t("dlg.spelling"), t("msg.no_text_to_check"))
            return

        dict_code = SPELL_LANG_MAP[self.spell_lang_var.get()]
        try:
            checker = SpellcheckService(dict_code)
            self.spell_errors = checker.check_text(text)
        except SpellDictionaryMissingError as exc:
            messagebox.showwarning(t("dlg.spelling"), t("msg.spell_dict_missing", dict=exc.dict_code))
            return
        except Exception as exc:
            messagebox.showerror(t("dlg.spelling"), t("msg.spellcheck_error", error=str(exc)))
            return

        self.errors_box.delete("1.0", "end")
        if not self.spell_errors:
            self.errors_box.insert("1.0", t("msg.no_errors"))
        else:
            lines = []
            for index, error in enumerate(self.spell_errors, start=1):
                word = error["word"]
                sugg = ", ".join(error["suggestions"]) if error["suggestions"] else "(brak podpowiedzi)"
                lines.append(f"{index}. {word} -> {sugg}")
            self.errors_box.insert("1.0", "\n".join(lines))
        self._set_status(t("status.spellcheck_done", count=len(self.spell_errors)))

    def _new_document(self) -> None:
        t = self.i18n.t
        text = self.textbox.get("1.0", "end").strip()
        if text and not messagebox.askyesno(t("dlg.new_document"), t("msg.confirm_new_document")):
            return

        self.current_input_file = None
        self.path_var.set(t("lbl.no_file"))
        self.spell_errors = []
        self.textbox.delete("1.0", "end")
        self.errors_box.delete("1.0", "end")
        self._set_status(t("status.new_document"))

    def _copy_ocr_to_clipboard(self) -> None:
        t = self.i18n.t
        text = self.textbox.get("1.0", "end").strip()
        if not text:
            messagebox.showwarning(t("dlg.clipboard"), t("msg.no_text_to_copy"))
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self._set_status(t("status.copied"))

    def _fix_spelling(self) -> None:
        t = self.i18n.t
        text = self.textbox.get("1.0", "end").strip()
        if not text:
            messagebox.showwarning(t("dlg.spelling"), t("msg.no_text_to_fix"))
            return
        if not self.spell_errors:
            self._run_spellcheck()
            if not self.spell_errors:
                messagebox.showinfo(t("dlg.spelling"), t("msg.no_errors_to_fix"))
                return

        dict_code = SPELL_LANG_MAP[self.spell_lang_var.get()]
        try:
            checker = SpellcheckService(dict_code)
            corrected = checker.apply_corrections(text, self.spell_errors)
        except Exception as exc:
            messagebox.showerror(t("dlg.spelling"), t("msg.fix_failed", error=str(exc)))
            return

        self._set_ocr_text(corrected)
        self._run_spellcheck()
        self._set_status(t("status.spelling_fixed"))

    def _ignore_spelling(self) -> None:
        t = self.i18n.t
        self.spell_errors = []
        self.errors_box.delete("1.0", "end")
        self.errors_box.insert("1.0", t("msg.ignored_note"))
        self._set_status(t("status.spelling_ignored"))

    def _add_selected_word(self) -> None:
        t = self.i18n.t
        dict_code = SPELL_LANG_MAP[self.spell_lang_var.get()]
        selected_text = self.textbox.selection_get().strip() if self.textbox.tag_ranges("sel") else ""
        if not selected_text:
            messagebox.showwarning(t("dlg.dictionary"), t("msg.select_word"))
            return
        try:
            checker = SpellcheckService(dict_code)
            checker.add_to_custom_dictionary(selected_text)
            self._set_status(t("status.word_added", word=selected_text))
        except Exception as exc:
            messagebox.showerror(t("dlg.dictionary"), t("msg.word_add_failed", error=str(exc)))

    def _export_txt(self) -> None:
        self._export("txt")

    def _export_docx(self) -> None:
        self._export("docx")

    def _export(self, kind: str) -> None:
        t = self.i18n.t
        text = self.textbox.get("1.0", "end").strip()
        if not text:
            messagebox.showwarning(t("dlg.export"), t("msg.no_text_to_export"))
            return
        if self.spell_errors:
            if not messagebox.askyesno(t("dlg.export"), t("msg.confirm_export_with_errors")):
                return
        extension = ".txt" if kind == "txt" else ".docx"
        path = filedialog.asksaveasfilename(
            title=t("dlg.export"),
            defaultextension=extension,
            filetypes=[("Plik", f"*{extension}")],
        )
        if not path:
            return
        output_path = Path(path)
        try:
            if kind == "txt":
                ExportService.export_txt(text, output_path)
            else:
                ExportService.export_docx(text, output_path)
            self._set_status(t("status.saved", path=output_path))
        except Exception as exc:
            messagebox.showerror(t("dlg.export"), t("msg.export_failed", error=str(exc)))

    def _on_theme_changed(self, display_value: str) -> None:
        mode = self._theme_label_to_mode.get(display_value, "System")
        self._theme_mode = mode
        ctk.set_appearance_mode(mode)
        self._save_settings()

    def _on_language_changed(self, display_value: str) -> None:
        lang_code = self._lang_label_to_code.get(display_value, "pl")
        if lang_code == self.i18n.language:
            return
        self.i18n.set_language(lang_code)
        self._save_settings()
        self._rebuild_ui()


def run() -> None:
    ctk.set_default_color_theme("blue")
    app = OCRStudioApp()
    app.mainloop()


if __name__ == "__main__":
    run()
