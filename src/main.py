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
from .language_manager import LanguageManager
from .icon_utils import ensure_app_icon
from .ocr_service import OCRService
from .preview_dialog import ScanPreviewDialog
from .scanner_service import ScannerService, ScannerUnavailableError
from .spellcheck_service import SpellcheckService
from .system_installer import SystemInstaller


class OCRStudioApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_NAME} - {APP_VERSION}")
        self.geometry("1200x760")

        self.language_manager = LanguageManager()
        self.ocr_service = OCRService()
        self.system_installer = SystemInstaller()
        self.current_input_file: Path | None = None
        self.spell_errors: list[dict[str, object]] = []
        self.engine_status_var = ctk.StringVar(value="Silniki OCR: sprawdzanie...")

        icon_path = ensure_app_icon()
        try:
            self.iconbitmap(str(icon_path))
        except Exception:
            # Na niektorych konfiguracjach Windows fallback jest ignorowany.
            pass

        self._build_ui()
        self._refresh_installed_languages()
        self._refresh_engine_status()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        title = ctk.CTkLabel(
            self,
            text=f"{APP_NAME}  |  autor: {APP_AUTHOR}  |  ver. {APP_VERSION}",
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

        self.status_var = ctk.StringVar(value="Gotowe.")
        self.path_var = ctk.StringVar(value="Brak wybranego pliku.")

        ctk.CTkLabel(sidebar, text="1) Instalacja silnikow", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, padx=10, pady=(10, 6), sticky="w"
        )
        ctk.CTkLabel(sidebar, textvariable=self.engine_status_var, wraplength=300).grid(
            row=1, column=0, padx=10, pady=(0, 6), sticky="w"
        )
        ctk.CTkButton(sidebar, text="Zainstaluj Tesseract", command=self._install_tesseract).grid(
            row=2, column=0, padx=10, pady=4, sticky="ew"
        )
        ctk.CTkButton(sidebar, text="Zainstaluj Ghostscript", command=self._install_ghostscript).grid(
            row=3, column=0, padx=10, pady=4, sticky="ew"
        )
        ctk.CTkButton(sidebar, text="Zainstaluj wszystko (OCR)", command=self._install_all_engines).grid(
            row=4, column=0, padx=10, pady=(4, 10), sticky="ew"
        )

        ctk.CTkLabel(sidebar, text="2) Zrodlo dokumentu", font=ctk.CTkFont(weight="bold")).grid(
            row=5, column=0, padx=10, pady=(10, 6), sticky="w"
        )
        ctk.CTkButton(sidebar, text="Wczytaj PDF/obraz", command=self._pick_file).grid(
            row=6, column=0, padx=10, pady=4, sticky="ew"
        )
        ctk.CTkButton(sidebar, text="Skanuj do PNG", command=lambda: self._scan("png")).grid(
            row=7, column=0, padx=10, pady=4, sticky="ew"
        )
        ctk.CTkButton(sidebar, text="Skanuj do JPEG", command=lambda: self._scan("jpeg")).grid(
            row=8, column=0, padx=10, pady=4, sticky="ew"
        )
        ctk.CTkButton(sidebar, text="Skanuj do PDF", command=lambda: self._scan("pdf")).grid(
            row=9, column=0, padx=10, pady=(4, 10), sticky="ew"
        )
        ctk.CTkLabel(sidebar, textvariable=self.path_var, wraplength=300).grid(
            row=10, column=0, padx=10, pady=(0, 10), sticky="w"
        )

        ctk.CTkLabel(sidebar, text="3) Jezyk OCR", font=ctk.CTkFont(weight="bold")).grid(
            row=11, column=0, padx=10, pady=(10, 4), sticky="w"
        )
        self.ocr_lang_var = ctk.StringVar(value="Polski")
        self.ocr_lang_menu = ctk.CTkOptionMenu(sidebar, values=list(OCR_LANG_MAP.keys()), variable=self.ocr_lang_var)
        self.ocr_lang_menu.grid(row=12, column=0, padx=10, pady=4, sticky="ew")
        ctk.CTkButton(sidebar, text="Doinstaluj jezyk OCR", command=self._install_ocr_language).grid(
            row=13, column=0, padx=10, pady=4, sticky="ew"
        )

        ctk.CTkLabel(sidebar, text="4) Pisownia", font=ctk.CTkFont(weight="bold")).grid(
            row=14, column=0, padx=10, pady=(12, 4), sticky="w"
        )
        self.spell_lang_var = ctk.StringVar(value="Polski (pl_PL)")
        self.spell_lang_menu = ctk.CTkOptionMenu(sidebar, values=list(SPELL_LANG_MAP.keys()), variable=self.spell_lang_var)
        self.spell_lang_menu.grid(row=15, column=0, padx=10, pady=4, sticky="ew")
        ctk.CTkButton(sidebar, text="Doinstaluj slownik pisowni", command=self._install_spell_language).grid(
            row=16, column=0, padx=10, pady=4, sticky="ew"
        )
        ctk.CTkButton(sidebar, text="Sprawdź pisownię", command=self._run_spellcheck).grid(
            row=17, column=0, padx=10, pady=4, sticky="ew"
        )
        ctk.CTkButton(sidebar, text="Dodaj zaznaczone slowo do slownika", command=self._add_selected_word).grid(
            row=18, column=0, padx=10, pady=4, sticky="ew"
        )

        ctk.CTkLabel(sidebar, text="5) Eksport", font=ctk.CTkFont(weight="bold")).grid(
            row=19, column=0, padx=10, pady=(12, 4), sticky="w"
        )
        ctk.CTkButton(sidebar, text="Eksportuj do TXT", command=self._export_txt).grid(
            row=20, column=0, padx=10, pady=4, sticky="ew"
        )
        ctk.CTkButton(sidebar, text="Eksportuj do DOCX", command=self._export_docx).grid(
            row=21, column=0, padx=10, pady=4, sticky="ew"
        )

        ctk.CTkLabel(sidebar, text="6) Wyglad", font=ctk.CTkFont(weight="bold")).grid(
            row=22, column=0, padx=10, pady=(12, 4), sticky="w"
        )
        self.theme_var = ctk.StringVar(value="System")
        theme = ctk.CTkSegmentedButton(
            sidebar,
            values=["Light", "Dark", "System"],
            command=self._change_theme,
            variable=self.theme_var,
        )
        theme.grid(row=23, column=0, padx=10, pady=(4, 10), sticky="ew")

        ctk.CTkButton(sidebar, text="Uruchom OCR", fg_color="#2f9e44", hover_color="#237a35", command=self._run_ocr).grid(
            row=24, column=0, padx=10, pady=(8, 10), sticky="ew"
        )

        ocr_header = ctk.CTkFrame(content, fg_color="transparent")
        ocr_header.grid(row=0, column=0, columnspan=2, padx=12, pady=(10, 4), sticky="ew")
        ocr_header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(ocr_header, text="Wynik OCR", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, sticky="w"
        )
        ocr_actions = ctk.CTkFrame(ocr_header, fg_color="transparent")
        ocr_actions.grid(row=0, column=1, sticky="e")
        ctk.CTkButton(
            ocr_actions,
            text="Kopiuj do schowka",
            command=self._copy_ocr_to_clipboard,
            width=150,
        ).pack(side="right", padx=(6, 0))
        ctk.CTkButton(
            ocr_actions,
            text="Nowy dokument",
            command=self._new_document,
            width=130,
            fg_color="#b45309",
            hover_color="#92400e",
        ).pack(side="right", padx=(6, 0))
        ctk.CTkButton(
            ocr_actions,
            text="Uruchom OCR",
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

        ctk.CTkLabel(spell_header, text="Błędy pisowni", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, sticky="w"
        )
        spell_actions = ctk.CTkFrame(spell_header, fg_color="transparent")
        spell_actions.grid(row=0, column=1, sticky="e")
        ctk.CTkButton(
            spell_actions,
            text="Ignoruj",
            command=self._ignore_spelling,
            width=110,
            fg_color="#6b7280",
            hover_color="#4b5563",
        ).pack(side="right", padx=(6, 0))
        ctk.CTkButton(
            spell_actions,
            text="Popraw pisownię",
            command=self._fix_spelling,
            width=140,
            fg_color="#2563eb",
            hover_color="#1d4ed8",
        ).pack(side="right")

        self.errors_box = ctk.CTkTextbox(content, height=160)
        self.errors_box.grid(row=3, column=0, columnspan=2, padx=12, pady=(0, 10), sticky="ew")

        status = ctk.CTkLabel(self, textvariable=self.status_var)
        status.grid(row=2, column=0, columnspan=2, padx=12, pady=(0, 10), sticky="w")

    def _set_status(self, message: str) -> None:
        self.status_var.set(message)

    def _refresh_installed_languages(self) -> None:
        installed_ocr = ", ".join(self.language_manager.list_installed_ocr()) or "brak"
        installed_spell = ", ".join(self.language_manager.list_installed_spell()) or "brak"
        self._set_status(f"Jezyki OCR: {installed_ocr} | Slowniki pisowni: {installed_spell}")

    def _refresh_engine_status(self) -> None:
        status = self.system_installer.get_engine_status()
        tesseract = "OK" if status["tesseract"] else "BRAK"
        ghostscript = "OK" if status["ghostscript"] else "BRAK"
        self.engine_status_var.set(f"Tesseract: {tesseract} | Ghostscript: {ghostscript}")

    def _run_async_task(self, task, start_message: str, ok_message: str) -> None:
        self._set_status(start_message)

        def worker() -> None:
            try:
                task()
                self.after(0, self._refresh_engine_status)
                self.after(0, lambda: self._set_status(ok_message))
            except Exception as exc:
                self.after(0, lambda: messagebox.showerror("Instalacja", str(exc)))
                self.after(0, lambda: self._set_status("Instalacja nie powiodla sie."))

        threading.Thread(target=worker, daemon=True).start()

    def _install_tesseract(self) -> None:
        self._run_async_task(
            task=self.system_installer.install_tesseract,
            start_message="Instalacja Tesseract...",
            ok_message="Tesseract zainstalowany.",
        )

    def _install_ghostscript(self) -> None:
        self._run_async_task(
            task=self.system_installer.install_ghostscript,
            start_message="Instalacja Ghostscript...",
            ok_message="Ghostscript zainstalowany.",
        )

    def _install_all_engines(self) -> None:
        def all_task() -> None:
            if not self.system_installer.is_tesseract_installed():
                self.system_installer.install_tesseract()
            if not self.system_installer.is_ghostscript_installed():
                self.system_installer.install_ghostscript()

        self._run_async_task(
            task=all_task,
            start_message="Instalacja kompletnego OCR (Tesseract + Ghostscript)...",
            ok_message="Silniki OCR gotowe.",
        )

    def _pick_file(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Wybierz dokument",
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
        ext = ".pdf" if fmt == "pdf" else (".jpg" if fmt == "jpeg" else ".png")
        filetypes = {
            ".png": [("Obraz PNG", "*.png")],
            ".jpg": [("Obraz JPEG", "*.jpg;*.jpeg")],
            ".pdf": [("Dokument PDF", "*.pdf")],
        }
        save_path = filedialog.asksaveasfilename(
            title="Zapisz zeskanowany dokument",
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
            self._set_status(f"Zeskanowano dokument: {scanned.name}")
            self._show_scan_preview(scanned)
        except ScannerUnavailableError as exc:
            messagebox.showerror("Skanowanie", str(exc))
        except Exception as exc:
            messagebox.showerror("Skanowanie", f"Nie udalo sie zeskanowac: {exc}")

    def _show_scan_preview(self, file_path: Path) -> None:
        ScanPreviewDialog(self, file_path, on_ocr=self._run_ocr)

    def _run_ocr(self) -> None:
        engine_status = self.system_installer.get_engine_status()
        if not engine_status["tesseract"]:
            messagebox.showwarning("OCR", "Brak Tesseract. Uzyj przycisku 'Zainstaluj Tesseract'.")
            return
        if not self.current_input_file:
            messagebox.showwarning("OCR", "Najpierw wybierz plik lub zeskanuj dokument.")
            return
        language_name = self.ocr_lang_var.get()
        lang_code = OCR_LANG_MAP[language_name]
        try:
            self.ocr_service._ensure_lang_installed(lang_code)
        except FileNotFoundError as exc:
            messagebox.showwarning("OCR", str(exc))
            return
        self._set_status("Trwa OCR...")

        def worker() -> None:
            try:
                suffix = self.current_input_file.suffix.lower()
                if suffix == ".pdf":
                    text = self.ocr_service.pdf_to_text(self.current_input_file, lang_code)
                else:
                    text = self.ocr_service.image_to_text(self.current_input_file, lang_code)
                self.after(0, lambda: self._set_ocr_text(text))
                self.after(0, lambda: self._set_status("OCR zakonczony."))
            except Exception as exc:
                self.after(0, lambda: messagebox.showerror("OCR", f"Blad OCR: {exc}"))
                self.after(0, lambda: self._set_status("Blad OCR."))

        threading.Thread(target=worker, daemon=True).start()

    def _set_ocr_text(self, text: str) -> None:
        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", text)

    def _install_ocr_language(self) -> None:
        language_name = self.ocr_lang_var.get()
        lang_code = OCR_LANG_MAP[language_name]
        try:
            self.language_manager.install_ocr_language(lang_code)
            self._refresh_installed_languages()
            messagebox.showinfo("Jezyk OCR", f"Zainstalowano jezyk OCR: {lang_code}")
        except Exception as exc:
            messagebox.showerror("Jezyk OCR", f"Nie udalo sie zainstalowac: {exc}")

    def _install_spell_language(self) -> None:
        dict_label = self.spell_lang_var.get()
        dict_code = SPELL_LANG_MAP[dict_label]
        try:
            self.language_manager.install_spell_dictionary(dict_code)
            self._refresh_installed_languages()
            messagebox.showinfo("Pisownia", f"Zainstalowano slownik: {dict_code}")
        except Exception as exc:
            messagebox.showerror("Pisownia", f"Nie udalo sie zainstalowac slownika: {exc}")

    def _run_spellcheck(self) -> None:
        text = self.textbox.get("1.0", "end").strip()
        if not text:
            messagebox.showwarning("Pisownia", "Brak tekstu do sprawdzenia.")
            return

        dict_code = SPELL_LANG_MAP[self.spell_lang_var.get()]
        try:
            checker = SpellcheckService(dict_code)
            self.spell_errors = checker.check_text(text)
        except FileNotFoundError as exc:
            messagebox.showwarning("Pisownia", str(exc))
            return
        except Exception as exc:
            messagebox.showerror("Pisownia", f"Blad sprawdzania pisowni: {exc}")
            return

        self.errors_box.delete("1.0", "end")
        if not self.spell_errors:
            self.errors_box.insert("1.0", "Brak błędów pisowni.")
        else:
            lines = []
            for index, error in enumerate(self.spell_errors, start=1):
                word = error["word"]
                sugg = ", ".join(error["suggestions"]) if error["suggestions"] else "(brak podpowiedzi)"
                lines.append(f"{index}. {word} -> {sugg}")
            self.errors_box.insert("1.0", "\n".join(lines))
        self._set_status(f"Sprawdzanie pisowni zakończone. Błędy: {len(self.spell_errors)}")

    def _new_document(self) -> None:
        text = self.textbox.get("1.0", "end").strip()
        if text and not messagebox.askyesno(
            "Nowy dokument",
            "Wyczyścić wynik OCR i rozpocząć OCR nowego dokumentu lub obrazu?",
        ):
            return

        self.current_input_file = None
        self.path_var.set("Brak wybranego pliku.")
        self.spell_errors = []
        self.textbox.delete("1.0", "end")
        self.errors_box.delete("1.0", "end")
        self._set_status("Gotowe. Wczytaj plik lub zeskanuj nowy dokument.")

    def _copy_ocr_to_clipboard(self) -> None:
        text = self.textbox.get("1.0", "end").strip()
        if not text:
            messagebox.showwarning("Schowek", "Brak tekstu OCR do skopiowania.")
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self._set_status("Skopiowano tekst OCR do schowka.")

    def _fix_spelling(self) -> None:
        text = self.textbox.get("1.0", "end").strip()
        if not text:
            messagebox.showwarning("Pisownia", "Brak tekstu OCR do poprawy.")
            return
        if not self.spell_errors:
            self._run_spellcheck()
            if not self.spell_errors:
                messagebox.showinfo("Pisownia", "Nie znaleziono błędów do poprawy.")
                return

        dict_code = SPELL_LANG_MAP[self.spell_lang_var.get()]
        try:
            checker = SpellcheckService(dict_code)
            corrected = checker.apply_corrections(text, self.spell_errors)
        except Exception as exc:
            messagebox.showerror("Pisownia", f"Nie udało się poprawić tekstu: {exc}")
            return

        self._set_ocr_text(corrected)
        self._run_spellcheck()
        self._set_status("Zastosowano poprawki pisowni w tekście OCR.")

    def _ignore_spelling(self) -> None:
        self.spell_errors = []
        self.errors_box.delete("1.0", "end")
        self.errors_box.insert("1.0", "Pisownia zignorowana — możesz eksportować tekst bez ostrzeżenia.")
        self._set_status("Pisownia zignorowana.")

    def _add_selected_word(self) -> None:
        dict_code = SPELL_LANG_MAP[self.spell_lang_var.get()]
        selected_text = self.textbox.selection_get().strip() if self.textbox.tag_ranges("sel") else ""
        if not selected_text:
            messagebox.showwarning("Slownik", "Zaznacz slowo w polu tekstu OCR.")
            return
        try:
            checker = SpellcheckService(dict_code)
            checker.add_to_custom_dictionary(selected_text)
            self._set_status(f"Dodano do slownika: {selected_text}")
        except Exception as exc:
            messagebox.showerror("Slownik", f"Nie udalo sie dodac slowa: {exc}")

    def _export_txt(self) -> None:
        self._export("txt")

    def _export_docx(self) -> None:
        self._export("docx")

    def _export(self, kind: str) -> None:
        text = self.textbox.get("1.0", "end").strip()
        if not text:
            messagebox.showwarning("Eksport", "Brak tekstu OCR do zapisania.")
            return
        if self.spell_errors:
            if not messagebox.askyesno(
                "Eksport",
                "Wykryto bledy pisowni. Czy chcesz kontynuowac zapis?",
            ):
                return
        extension = ".txt" if kind == "txt" else ".docx"
        path = filedialog.asksaveasfilename(
            title="Zapisz wynik OCR",
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
            self._set_status(f"Zapisano: {output_path}")
        except Exception as exc:
            messagebox.showerror("Eksport", f"Nie udalo sie zapisac pliku: {exc}")

    def _change_theme(self, value: str) -> None:
        ctk.set_appearance_mode(value)


def run() -> None:
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    app = OCRStudioApp()
    app.mainloop()


if __name__ == "__main__":
    run()
