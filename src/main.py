from __future__ import annotations

import tkinter as tk
from collections import Counter
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any

import customtkinter as ctk

from .config import (
    APP_AUTHOR,
    APP_DISPLAY_NAME,
    APP_VERSION,
    OCR_LANG_MAP,
    SPELL_LANG_MAP,
    SUPPORTED_EXTENSIONS,
)
from .export_service import ExportService
from .i18n import I18n
from .icon_utils import ensure_app_icon
from .jobs import JobRunner
from .language_manager import DownloadError, LanguageManager
from .ocr_service import (
    OCRDocumentError,
    OCRError,
    OCRLanguageMissingError,
    OCRResult,
    OCRService,
    is_supported_input,
)
from .pathsafe import UnsafePathError
from .preview_dialog import ScanPreviewDialog
from .scanner_service import ScannerService, ScannerUnavailableError
from .settings import THEME_MODES, load_settings, save_settings
from .spellcheck_service import SpellcheckService, SpellDictionaryMissingError, add_custom_word

try:  # przeciaganie plikow na okno jest dodatkiem - brak biblioteki nie moze zablokowac aplikacji
    from tkinterdnd2 import DND_FILES, TkinterDnD

    _WINDOW_BASES: tuple[type, ...] = (ctk.CTk, TkinterDnD.DnDWrapper)
except Exception:  # noqa: BLE001
    DND_FILES = "DND_Files"
    _WINDOW_BASES = (ctk.CTk,)

UI_LANGUAGE_LABELS = {"pl": "PL", "en": "EN"}
SIDEBAR_WIDTH = 370


def fit_window_size(screen_width: int, screen_height: int, scale: float) -> tuple[int, int]:
    """Rozmiar okna (w jednostkach CustomTkinter, czyli przed skalowaniem DPI) mieszczacy sie na ekranie.

    CustomTkinter mnozy geometrie przez skale DPI, wiec stale 1200x760 przy
    skalowaniu 150% dawalo okno 1800x1140 px - wyzsze niz ekran 1080p.
    Zostawiamy zapas na pasek tytulu i pasek zadan.
    """
    scale = scale if scale > 0 else 1.0
    width = int(min(1200, max(720, screen_width * 0.92 / scale)))
    height = int(min(760, max(420, (screen_height - 120) / scale)))
    return width, height


class OCRStudioApp(*_WINDOW_BASES):  # type: ignore[misc]
    def __init__(self) -> None:
        super().__init__()
        self._init_drag_and_drop()

        self.settings = load_settings()
        self.i18n = I18n(self.settings["language"])
        self._theme_mode: str = self.settings["theme"]
        ctk.set_appearance_mode(self._theme_mode)

        self._apply_geometry()

        self.language_manager = LanguageManager()
        self.ocr_service = OCRService()
        self.runner = JobRunner(self.after)  # glowne zadanie (OCR, pisownia, pobieranie, zapis)
        self.suggest_runner = JobRunner(self.after)  # podpowiedzi do menu kontekstowego

        self.input_files: list[Path] = []
        self._ignored_words: set[str] = set()
        self._text_dirty = False  # tekst zmieniony recznie po ostatnim wyniku OCR
        self._programmatic_change = False
        self._i18n_items: list[tuple[Any, str, str, dict[str, object]]] = []
        self._lockable: list[Any] = []

        # Zmienne nalezace do aplikacji (nie do widgetow)
        self.status_var = ctk.StringVar(value=self.i18n.t("status.ready"))
        self.path_var = ctk.StringVar()
        self.ocr_lang_var = ctk.StringVar(value=self.settings["ocr_lang"])
        self.ocr_lang2_var = ctk.StringVar()
        self.spell_lang_var = ctk.StringVar(value=self.settings["spell_lang"])
        self.reflow_var = ctk.BooleanVar(value=self.settings["reflow"])
        self.mark_var = ctk.BooleanVar(value=self.settings["mark_uncertain"])
        self.force_var = ctk.BooleanVar(value=self.settings["force_ocr"])
        self._ocr_lang2: str = self.settings["ocr_lang2"]  # "" = brak

        icon_path = ensure_app_icon()
        try:
            self.iconbitmap(str(icon_path))
        except Exception:  # noqa: BLE001 - na czesci konfiguracji Windows ikona bywa ignorowana
            pass

        self.title(f"{APP_DISPLAY_NAME} - {APP_VERSION}")
        self._build_ui()
        self._bind_events()
        self._apply_tag_colors()
        self._relabel()
        self._init_drop_targets()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(400, self._prewarm_dictionary)

    # ------------------------------------------------------------------ start

    def _init_drag_and_drop(self) -> None:
        self._dnd_ready = False
        self._dnd_error = "" if len(_WINDOW_BASES) > 1 else "tkinterdnd2 niedostepne"
        if len(_WINDOW_BASES) > 1:
            try:
                self.TkdndVersion = TkinterDnD._require(self)
                self._dnd_ready = True
            except Exception as exc:  # noqa: BLE001 - bez DnD aplikacja dziala normalnie
                self._dnd_error = f"{type(exc).__name__}: {exc}"

    def _apply_geometry(self) -> None:
        """Rozmiar okna dopasowany do ekranu - CustomTkinter skaluje geometrie przez DPI,
        wiec stale 1200x760 wychodzilo poza ekran 1080p przy skalowaniu 150%."""
        try:
            scale = self._get_window_scaling()
        except Exception:  # noqa: BLE001
            scale = 1.0
        width, height = fit_window_size(self.winfo_screenwidth(), self.winfo_screenheight(), scale)
        self.geometry(f"{width}x{height}")
        self.minsize(min(720, width), min(420, height))

    def _prewarm_dictionary(self) -> None:
        """Wczytuje slownik w tle, zeby pierwsze sprawdzenie pisowni nie czekalo kilku sekund."""
        import threading

        code = SPELL_LANG_MAP[self.spell_lang_var.get()]
        if not self.language_manager.is_spell_dictionary_available(code):
            return

        def warm() -> None:
            try:
                SpellcheckService(code).prewarm()
            except Exception:  # noqa: BLE001 - rozgrzewka jest opcjonalna
                pass

        threading.Thread(target=warm, daemon=True, name="studio-ocr-prewarm").start()

    # --------------------------------------------------------------- widgety

    def _text(self, widget: Any, key: str, attr: str = "text", **fmt: object) -> Any:
        """Rejestruje widget do tlumaczenia w miejscu (bez przebudowy interfejsu)."""
        self._i18n_items.append((widget, key, attr, fmt))
        return widget

    def _button(self, parent: Any, key: str, command: Any, *, lock: bool = True, **kwargs: Any) -> ctk.CTkButton:
        button = ctk.CTkButton(parent, text="", command=command, **kwargs)
        self._text(button, key)
        if lock:
            self._lockable.append(button)
        return button

    def _build_ui(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.title_label = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=18, weight="bold"))
        self.title_label.grid(row=0, column=0, columnspan=2, padx=16, pady=(12, 8), sticky="w")

        self.sidebar = ctk.CTkScrollableFrame(self, width=SIDEBAR_WIDTH)
        self.sidebar.grid(row=1, column=0, padx=(12, 8), pady=(0, 8), sticky="nswe")
        self.sidebar.grid_columnconfigure(0, weight=1)
        self.content = ctk.CTkFrame(self)
        self.content.grid(row=1, column=1, padx=(8, 12), pady=(0, 8), sticky="nswe")
        self.content.grid_rowconfigure(1, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        self._build_sidebar(self.sidebar)
        self._build_content(self.content)
        self._build_status_bar()

    def _section(self, parent: Any, key: str, row: int, top: int = 12) -> None:
        label = ctk.CTkLabel(parent, text="", font=ctk.CTkFont(weight="bold"))
        self._text(label, key)
        label.grid(row=row, column=0, padx=10, pady=(top, 4), sticky="w")

    def _build_sidebar(self, side: Any) -> None:
        row = 0
        self._section(side, "sec.source", row, top=4)
        row += 1
        for key, command in (
            ("btn.load_files", self._pick_files),
            ("btn.scan_png", lambda: self._scan("png")),
            ("btn.scan_jpeg", lambda: self._scan("jpeg")),
            ("btn.scan_pdf", lambda: self._scan("pdf")),
        ):
            self._button(side, key, command).grid(row=row, column=0, padx=10, pady=4, sticky="ew")
            row += 1
        ctk.CTkLabel(side, textvariable=self.path_var, wraplength=SIDEBAR_WIDTH - 40, justify="left").grid(
            row=row, column=0, padx=10, pady=(0, 6), sticky="w"
        )
        row += 1

        self._section(side, "sec.ocr_lang", row)
        row += 1
        self.ocr_lang_menu = ctk.CTkOptionMenu(
            side, values=list(OCR_LANG_MAP), variable=self.ocr_lang_var, command=self._on_lang_choice_changed
        )
        self.ocr_lang_menu.grid(row=row, column=0, padx=10, pady=4, sticky="ew")
        self._lockable.append(self.ocr_lang_menu)
        row += 1
        second_label = ctk.CTkLabel(side, text="", anchor="w")
        self._text(second_label, "lbl.second_lang")
        second_label.grid(row=row, column=0, padx=10, pady=(4, 0), sticky="w")
        row += 1
        self.ocr_lang2_menu = ctk.CTkOptionMenu(
            side, values=[""], variable=self.ocr_lang2_var, command=self._on_second_lang_changed
        )
        self.ocr_lang2_menu.grid(row=row, column=0, padx=10, pady=4, sticky="ew")
        self._lockable.append(self.ocr_lang2_menu)
        row += 1
        self._button(side, "btn.install_ocr_lang", self._install_ocr_language).grid(
            row=row, column=0, padx=10, pady=4, sticky="ew"
        )
        row += 1
        self._option_switch(side, "opt.force_ocr", self.force_var, row)
        row += 1
        self._option_switch(side, "opt.mark_uncertain", self.mark_var, row, command=self._on_mark_toggled)
        row += 1

        self._section(side, "sec.spelling", row)
        row += 1
        self.spell_lang_menu = ctk.CTkOptionMenu(
            side, values=list(SPELL_LANG_MAP), variable=self.spell_lang_var, command=self._on_lang_choice_changed
        )
        self.spell_lang_menu.grid(row=row, column=0, padx=10, pady=4, sticky="ew")
        self._lockable.append(self.spell_lang_menu)
        row += 1
        for key, command in (
            ("btn.install_spell_dict", self._install_spell_language),
            ("btn.spellcheck", self._run_spellcheck),
            ("btn.add_word", self._add_selected_word),
        ):
            self._button(side, key, command).grid(row=row, column=0, padx=10, pady=4, sticky="ew")
            row += 1

        self._section(side, "sec.export", row)
        row += 1
        for key, command in (
            ("btn.export_txt", lambda: self._export("txt")),
            ("btn.export_docx", lambda: self._export("docx")),
            ("btn.export_pdf", self._export_pdf),
        ):
            self._button(side, key, command).grid(row=row, column=0, padx=10, pady=4, sticky="ew")
            row += 1
        self._option_switch(side, "opt.reflow", self.reflow_var, row)
        row += 1

        self._section(side, "sec.appearance", row)
        row += 1
        self.theme_seg = ctk.CTkSegmentedButton(side, values=list(THEME_MODES), command=self._on_theme_changed)
        self.theme_seg.grid(row=row, column=0, padx=10, pady=(4, 6), sticky="ew")
        row += 1

        self._section(side, "sec.app_language", row, top=6)
        row += 1
        self.lang_seg = ctk.CTkSegmentedButton(
            side, values=list(UI_LANGUAGE_LABELS.values()), command=self._on_language_changed
        )
        self.lang_seg.grid(row=row, column=0, padx=10, pady=(4, 6), sticky="ew")
        row += 1

        self._button(side, "btn.run_ocr", self._run_ocr, fg_color="#2f9e44", hover_color="#237a35").grid(
            row=row, column=0, padx=10, pady=(8, 10), sticky="ew"
        )

    def _option_switch(self, parent: Any, key: str, variable: ctk.BooleanVar, row: int, command: Any = None) -> None:
        switch = ctk.CTkCheckBox(parent, text="", variable=variable, command=command or self._save_settings)
        self._text(switch, key)
        switch.grid(row=row, column=0, padx=10, pady=4, sticky="w")
        self._lockable.append(switch)

    def _build_content(self, content: Any) -> None:
        header = ctk.CTkFrame(content, fg_color="transparent")
        header.grid(row=0, column=0, padx=12, pady=(10, 4), sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        title = ctk.CTkLabel(header, text="", font=ctk.CTkFont(size=16, weight="bold"))
        self._text(title, "lbl.result_header")
        title.grid(row=0, column=0, sticky="w")
        actions = ctk.CTkFrame(header, fg_color="transparent")
        actions.grid(row=0, column=1, sticky="e")
        self._button(actions, "btn.copy_clipboard", self._copy_ocr_to_clipboard, lock=False, width=150).pack(
            side="right", padx=(6, 0)
        )
        self._button(
            actions, "btn.new_document", self._new_document, width=130, fg_color="#b45309", hover_color="#92400e"
        ).pack(side="right", padx=(6, 0))
        self._button(
            actions, "btn.run_ocr", self._run_ocr, width=150, fg_color="#2f9e44", hover_color="#237a35"
        ).pack(side="right")

        # undo=True: zamiany zbiorcze (OCR, "Popraw wszystko") mozna cofnac Ctrl+Z
        self.textbox = ctk.CTkTextbox(content, wrap="word", undo=True, autoseparators=True, maxundo=-1)
        self.textbox.grid(row=1, column=0, padx=12, pady=(0, 8), sticky="nswe")
        self._tb: tk.Text = self.textbox._textbox

        spell_header = ctk.CTkFrame(content, fg_color="transparent")
        spell_header.grid(row=2, column=0, padx=12, pady=(8, 4), sticky="ew")
        spell_header.grid_columnconfigure(0, weight=1)
        errors_title = ctk.CTkLabel(spell_header, text="", font=ctk.CTkFont(size=16, weight="bold"))
        self._text(errors_title, "lbl.errors_header")
        errors_title.grid(row=0, column=0, sticky="w")
        spell_actions = ctk.CTkFrame(spell_header, fg_color="transparent")
        spell_actions.grid(row=0, column=1, sticky="e")
        self._button(
            spell_actions, "btn.ignore", self._ignore_spelling, width=140, fg_color="#6b7280", hover_color="#4b5563"
        ).pack(side="right", padx=(6, 0))
        self._button(
            spell_actions, "btn.fix_spelling", self._fix_all_spelling, width=140, fg_color="#2563eb", hover_color="#1d4ed8"
        ).pack(side="right")

        self.errors_box = ctk.CTkTextbox(content, height=150)
        self.errors_box.grid(row=3, column=0, padx=12, pady=(0, 10), sticky="ew")

    def _build_status_bar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=2, column=0, columnspan=2, padx=12, pady=(0, 8), sticky="ew")
        bar.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(bar, textvariable=self.status_var, anchor="w").grid(row=0, column=0, sticky="ew")
        self.progress = ctk.CTkProgressBar(bar, width=260)
        self.progress.set(0)
        self.cancel_button = self._button(bar, "btn.cancel", self._cancel_job, lock=False, width=100)
        self.progress.grid(row=0, column=1, padx=(10, 0))
        self.cancel_button.grid(row=0, column=2, padx=(10, 0))
        self.progress.grid_remove()
        self.cancel_button.grid_remove()

    # -------------------------------------------------------------- zdarzenia

    def _bind_events(self) -> None:
        tb = self._tb
        tb.bind("<<Modified>>", self._on_text_modified, add="+")
        tb.bind("<Button-3>", self._on_text_right_click)
        tb.bind("<Control-o>", lambda _e: (self._pick_files(), "break")[1])
        self.bind("<Control-o>", lambda _e: self._pick_files())
        self.bind("<F5>", lambda _e: self._run_ocr())
        self.bind("<Escape>", lambda _e: self._cancel_job())

    def _init_drop_targets(self) -> None:
        if not self._dnd_ready:
            return
        for widget in (self, self.sidebar, self.content, self.textbox, self._tb):
            try:
                widget.drop_target_register(DND_FILES)
                widget.dnd_bind("<<Drop>>", self._on_drop)
            except Exception:  # noqa: BLE001 - brak DnD na tym widgecie nie jest bledem
                continue

    def _on_drop(self, event: Any) -> Any:
        if self.runner.busy:
            self._set_status(self.i18n.t("msg.busy"))
            return event.action
        self._set_input_files([Path(p) for p in self.tk.splitlist(event.data)])
        return event.action

    def _on_close(self) -> None:
        for runner in (self.runner, self.suggest_runner):
            runner.cancel()
            if runner.current is not None:
                runner.current.wait(1.5)  # zabija tesseract.exe, zeby nie zostal w tle
        self.destroy()

    # ---------------------------------------------------- tlumaczenie w miejscu

    def _relabel(self) -> None:
        t = self.i18n.t
        for widget, key, attr, fmt in self._i18n_items:
            widget.configure(**{attr: t(key, **fmt)})
        self.title_label.configure(text=f"{APP_DISPLAY_NAME}  |  {t('app.author')}: {APP_AUTHOR}  |  ver. {APP_VERSION}")

        theme_labels = {"System": t("theme.system"), "Light": t("theme.light"), "Dark": t("theme.dark")}
        self._theme_label_to_mode = {label: mode for mode, label in theme_labels.items()}
        self.theme_seg.configure(values=[theme_labels[mode] for mode in THEME_MODES])
        self.theme_seg.set(theme_labels[self._theme_mode])
        self.lang_seg.set(UI_LANGUAGE_LABELS[self.i18n.language])

        none_label = t("lbl.none")
        self.ocr_lang2_menu.configure(values=[none_label, *OCR_LANG_MAP])
        self.ocr_lang2_var.set(self._ocr_lang2 or none_label)

        self._refresh_path_label()
        if not self.runner.busy:
            self._refresh_installed_languages()

    def _set_status(self, message: str) -> None:
        self.status_var.set(message)

    def _refresh_path_label(self) -> None:
        t = self.i18n.t
        if not self.input_files:
            self.path_var.set(t("lbl.no_file"))
        elif len(self.input_files) == 1:
            self.path_var.set(str(self.input_files[0]))
        else:
            names = [p.name for p in self.input_files[:5]]
            if len(self.input_files) > 5:
                names.append("…")
            self.path_var.set(t("lbl.files_count", count=len(self.input_files)) + "\n" + "\n".join(names))

    def _refresh_installed_languages(self) -> None:
        t = self.i18n.t
        ocr = ", ".join(self.language_manager.list_installed_ocr()) or t("status.none")
        spell = ", ".join(self.language_manager.list_installed_spell()) or t("status.none")
        self._set_status(t("status.langs", ocr=ocr, spell=spell))

    # ------------------------------------------------------------- ustawienia

    def _save_settings(self) -> None:
        save_settings(
            {
                "theme": self._theme_mode,
                "language": self.i18n.language,
                "ocr_lang": self.ocr_lang_var.get(),
                "ocr_lang2": self._ocr_lang2,
                "spell_lang": self.spell_lang_var.get(),
                "reflow": bool(self.reflow_var.get()),
                "mark_uncertain": bool(self.mark_var.get()),
                "force_ocr": bool(self.force_var.get()),
            }
        )

    def _on_lang_choice_changed(self, _value: str) -> None:
        self._save_settings()

    def _on_second_lang_changed(self, value: str) -> None:
        self._ocr_lang2 = "" if value == self.i18n.t("lbl.none") else value
        self._save_settings()

    def _on_theme_changed(self, display_value: str) -> None:
        self._theme_mode = self._theme_label_to_mode.get(display_value, "System")
        ctk.set_appearance_mode(self._theme_mode)
        self._apply_tag_colors()
        self._save_settings()

    def _on_language_changed(self, display_value: str) -> None:
        code = next((c for c, label in UI_LANGUAGE_LABELS.items() if label == display_value), "pl")
        if code == self.i18n.language:
            return
        self.i18n.set_language(code)
        self._relabel()
        self._save_settings()

    def _on_mark_toggled(self) -> None:
        if not self.mark_var.get():
            self._tb.tag_remove("low_conf", "1.0", "end")
        self._save_settings()

    def _apply_tag_colors(self) -> None:
        dark = ctk.get_appearance_mode() == "Dark"
        self._tb.tag_configure("low_conf", background="#6b5900" if dark else "#fff3bf")
        self._tb.tag_configure("spell_error", foreground="#ff6b6b" if dark else "#c92a2a", underline=True)
        self._tb.tag_raise("sel")

    # ---------------------------------------------------- zadania w tle (blokada)

    def _set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        for widget in self._lockable:
            widget.configure(state=state)
        if busy:
            self.progress.set(0)
            self.progress.grid()
            self.cancel_button.grid()
        else:
            self.progress.grid_remove()
            self.cancel_button.grid_remove()

    def _start_job(self, work: Any, *, on_success: Any = None, on_error: Any = None, on_progress: Any = None) -> bool:
        """Uruchamia zadanie w tle. Zwraca False, gdy inne jest w toku."""
        if self.runner.busy:
            messagebox.showinfo(self.i18n.t("dlg.busy"), self.i18n.t("msg.busy"))
            return False
        self._set_busy(True)

        def finished() -> None:
            self._set_busy(False)

        def cancelled() -> None:
            self._set_status(self.i18n.t("status.cancelled"))

        self.runner.start(
            work,
            on_progress=on_progress or self._on_generic_progress,
            on_success=on_success,
            on_error=on_error or self._on_generic_error,
            on_cancel=cancelled,
            on_finish=finished,
        )
        return True

    def _cancel_job(self) -> None:
        if self.runner.busy:
            self.runner.cancel()

    def _on_generic_progress(self, done: int, total: int, _message: Any) -> None:
        self.progress.set(done / total if total else 0)

    def _on_generic_error(self, exc: BaseException) -> None:
        messagebox.showerror(self.i18n.t("dlg.ocr"), str(exc))

    # ------------------------------------------------------------------ pliki

    def _pick_files(self) -> None:
        if self.runner.busy:
            return
        t = self.i18n.t
        patterns = " ".join(f"*{ext}" for ext in SUPPORTED_EXTENSIONS)
        chosen = filedialog.askopenfilenames(
            title=t("btn.load_files"),
            filetypes=[(t("ft.documents"), patterns), (t("ft.all"), "*.*")],
        )
        if chosen:
            self._set_input_files([Path(p) for p in chosen])

    def _set_input_files(self, paths: list[Path]) -> None:
        expanded: list[Path] = []
        for path in paths:
            if path.is_dir():
                expanded.extend(sorted(child for child in path.iterdir() if child.is_file()))
            else:
                expanded.append(path)
        seen: set[Path] = set()
        supported = []
        for path in expanded:
            if path not in seen and is_supported_input(path):
                seen.add(path)
                supported.append(path)
        skipped = len(expanded) - len(supported)

        if supported:
            self.input_files = supported
            self._refresh_path_label()
        if skipped:
            self._set_status(self.i18n.t("status.files_skipped", count=skipped))

    def _scan(self, fmt: str) -> None:
        if self.runner.busy:
            return
        t = self.i18n.t
        ext = ".pdf" if fmt == "pdf" else (".jpg" if fmt == "jpeg" else ".png")
        filetypes = {
            ".png": [(t("ft.png"), "*.png")],
            ".jpg": [(t("ft.jpeg"), "*.jpg;*.jpeg")],
            ".pdf": [(t("ft.pdf"), "*.pdf")],
        }
        save_path = filedialog.asksaveasfilename(
            title=t("dlg.scan"),
            defaultextension=ext,
            filetypes=[*filetypes[ext], (t("ft.all"), "*.*")],
            initialfile=f"scan{ext}",
        )
        if not save_path:
            return

        try:
            scanned = ScannerService().scan_to_file(Path(save_path), fmt=fmt)
        except ScannerUnavailableError as exc:
            messagebox.showerror(t("dlg.scan"), t(f"err.scanner.{exc.key}"))
            return
        except Exception as exc:  # noqa: BLE001 - blad sterownika/COM pokazujemy uzytkownikowi
            messagebox.showerror(t("dlg.scan"), t("msg.scan_failed", error=str(exc)))
            return

        self.input_files = [scanned]
        self._refresh_path_label()
        self._set_status(t("status.scan_done", name=scanned.name))
        ScanPreviewDialog(self, scanned, on_ocr=self._run_ocr, i18n=self.i18n)

    # -------------------------------------------------------------------- OCR

    def _lang_spec(self) -> str:
        first = OCR_LANG_MAP[self.ocr_lang_var.get()]
        second = OCR_LANG_MAP.get(self._ocr_lang2)
        return f"{first}+{second}" if second and second != first else first

    def _describe_error(self, exc: BaseException, fallback_key: str = "msg.ocr_error") -> str:
        t = self.i18n.t
        if isinstance(exc, OCRLanguageMissingError):
            return t("msg.lang_missing", lang=exc.lang_code)
        if isinstance(exc, UnsafePathError):
            return t("msg.unsafe_path")
        if isinstance(exc, OCRDocumentError):
            return t("msg.pdf_open_error", name=exc.path.name, error=exc.details)
        if isinstance(exc, DownloadError):
            return t("msg.download_failed", what=exc.what, error=exc.details)
        if isinstance(exc, SpellDictionaryMissingError):
            return t("msg.spell_dict_missing", dict=exc.dict_code)
        if isinstance(exc, OCRError):
            return t(fallback_key, error=exc.details)
        return t(fallback_key, error=str(exc))

    def _run_ocr(self) -> None:
        t = self.i18n.t
        if self.runner.busy:
            messagebox.showinfo(t("dlg.busy"), t("msg.busy"))
            return
        if not self.ocr_service.is_available():
            messagebox.showwarning(t("dlg.ocr"), t("msg.no_tesseract"))
            return
        if not self.input_files:
            messagebox.showwarning(t("dlg.ocr"), t("msg.no_file_selected"))
            return
        spec = self._lang_spec()
        try:
            self.ocr_service.ensure_lang_installed(spec)
        except OCRLanguageMissingError as exc:
            messagebox.showwarning(t("dlg.ocr"), t("msg.lang_missing", lang=exc.lang_code))
            return
        # Wynik OCR zastapi caly tekst: pytamy, jesli uzytkownik go edytowal.
        if self._text_dirty and self._tb.get("1.0", "end-1c").strip():
            if not messagebox.askyesno(t("dlg.ocr"), t("msg.confirm_replace_text")):
                return

        # Wszystko, czego potrzebuje watek, przechwytujemy TERAZ - uzytkownik moze
        # w trakcie zmienic plik, jezyk lub kliknac "Nowy dokument".
        files = list(self.input_files)
        force_ocr = bool(self.force_var.get())
        mark = bool(self.mark_var.get())
        ocr = self.ocr_service

        def work(ctx: Any) -> OCRResult:
            combined = OCRResult()
            for index, path in enumerate(files):

                def progress(done: int, total: int, name: str, _i: int = index) -> None:
                    ctx.report(int(((_i + done / max(total, 1)) / len(files)) * 1000), 1000, (name, done, total))

                result = ocr.ocr_document(path, spec, progress=progress, cancel=ctx.cancel_event, force_ocr=force_ocr)
                if len(files) > 1:
                    header = f"=== {path.name} ==="
                    shift = len(header) + 2
                    result = OCRResult(
                        text=f"{header}\n\n{result.text}",
                        low_confidence=[(s + shift, e + shift) for s, e in result.low_confidence],
                        pages=result.pages,
                        text_layer_pages=result.text_layer_pages,
                    )
                combined.append(result)
            return combined

        def on_progress(done: int, total: int, message: Any) -> None:
            self.progress.set(done / total if total else 0)
            if isinstance(message, tuple):
                name, page, pages = message
                self._set_status(t("status.ocr_progress", name=name, done=min(page + 1, pages), total=pages))

        def on_success(result: OCRResult) -> None:
            self._set_result(result, mark_uncertain=mark)
            self._set_status(
                t(
                    "status.ocr_done",
                    pages=result.pages,
                    layer=result.text_layer_pages,
                    uncertain=len(result.low_confidence) if mark else 0,
                )
            )

        def on_error(exc: BaseException) -> None:
            self._set_status(t("status.ocr_error"))
            messagebox.showerror(t("dlg.ocr"), self._describe_error(exc))

        if self._start_job(work, on_success=on_success, on_error=on_error, on_progress=on_progress):
            self._set_status(t("status.ocr_running"))

    # ------------------------------------------------------------ pole tekstowe

    def _on_text_modified(self, _event: Any) -> None:
        tb = self._tb
        if tb.edit_modified():
            tb.edit_modified(False)
            if not self._programmatic_change:
                self._text_dirty = True

    def _replace_all_text(self, text: str) -> None:
        """Podmienia caly tekst jako JEDEN krok cofania (Ctrl+Z przywraca poprzedni)."""
        tb = self._tb
        tb.configure(autoseparators=False)
        tb.edit_separator()
        self._programmatic_change = True
        try:
            tb.delete("1.0", "end")
            tb.insert("1.0", text)
        finally:
            tb.edit_separator()
            tb.configure(autoseparators=True)
            tb.edit_modified(False)
            self._programmatic_change = False
        self._text_dirty = False

    def _set_result(self, result: OCRResult, *, mark_uncertain: bool) -> None:
        self._replace_all_text(result.text)
        self._clear_spell_marks()
        self._tb.tag_remove("low_conf", "1.0", "end")
        if mark_uncertain:
            for start, end in result.low_confidence:
                self._tb.tag_add("low_conf", f"1.0+{start}c", f"1.0+{end}c")

    def _text_value(self) -> str:
        return self._tb.get("1.0", "end-1c")

    def _new_document(self) -> None:
        if self.runner.busy:
            return
        t = self.i18n.t
        if self._text_value().strip() and not messagebox.askyesno(t("dlg.new_document"), t("msg.confirm_new_document")):
            return
        self.input_files = []
        self._refresh_path_label()
        self._replace_all_text("")
        self._tb.edit_reset()
        self._clear_spell_marks()
        self._tb.tag_remove("low_conf", "1.0", "end")
        self._ignored_words.clear()
        self._set_status(t("status.new_document"))

    def _copy_ocr_to_clipboard(self) -> None:
        t = self.i18n.t
        text = self._text_value().strip()
        if not text:
            messagebox.showwarning(t("dlg.clipboard"), t("msg.no_text_to_copy"))
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self._set_status(t("status.copied"))

    # ----------------------------------------------------- jezyki i slowniki

    def _install_ocr_language(self) -> None:
        t = self.i18n.t
        name = self.ocr_lang_var.get()
        code = OCR_LANG_MAP[name]
        if self.language_manager.is_ocr_language_available(code):
            messagebox.showinfo(t("dlg.ocr_lang"), t("msg.ocr_lang_already", lang=code))
            return
        manager = self.language_manager

        def work(ctx: Any) -> None:
            manager.install_ocr_language(
                code, cancel=ctx.cancel_event, progress=lambda done, total, label: ctx.report(done, total, label)
            )

        def on_progress(done: int, total: int, message: Any) -> None:
            self.progress.set(done / total if total else 0)
            self._set_status(t("status.downloading", name=message))

        def on_success(_result: Any) -> None:
            self._refresh_installed_languages()
            messagebox.showinfo(t("dlg.ocr_lang"), t("msg.ocr_lang_installed", lang=code))

        def on_error(exc: BaseException) -> None:
            self._refresh_installed_languages()
            messagebox.showerror(t("dlg.ocr_lang"), t("msg.ocr_lang_failed", error=self._describe_error(exc)))

        self._start_job(work, on_success=on_success, on_error=on_error, on_progress=on_progress)

    def _install_spell_language(self) -> None:
        t = self.i18n.t
        code = SPELL_LANG_MAP[self.spell_lang_var.get()]
        if self.language_manager.is_spell_dictionary_available(code):
            messagebox.showinfo(t("dlg.spelling"), t("msg.spell_dict_already", dict=code))
            return
        manager = self.language_manager

        def work(ctx: Any) -> None:
            manager.install_spell_dictionary(
                code, cancel=ctx.cancel_event, progress=lambda done, total, label: ctx.report(done, total, label)
            )

        def on_progress(done: int, total: int, message: Any) -> None:
            self.progress.set(done / total if total else 0)
            self._set_status(t("status.downloading", name=message))

        def on_success(_result: Any) -> None:
            self._refresh_installed_languages()
            messagebox.showinfo(t("dlg.spelling"), t("msg.spell_dict_installed", dict=code))

        def on_error(exc: BaseException) -> None:
            self._refresh_installed_languages()
            messagebox.showerror(t("dlg.spelling"), t("msg.spell_dict_failed", error=self._describe_error(exc)))

        self._start_job(work, on_success=on_success, on_error=on_error, on_progress=on_progress)

    # --------------------------------------------------------------- pisownia

    def _spell_ranges(self) -> list[tuple[str, str]]:
        ranges = self._tb.tag_ranges("spell_error")
        return [(str(ranges[i]), str(ranges[i + 1])) for i in range(0, len(ranges), 2)]

    def _clear_spell_marks(self) -> None:
        self._tb.tag_remove("spell_error", "1.0", "end")
        self.errors_box.delete("1.0", "end")

    def _refresh_error_box(self) -> None:
        t = self.i18n.t
        self.errors_box.delete("1.0", "end")
        words = Counter(self._tb.get(start, end) for start, end in self._spell_ranges())
        if not words:
            self.errors_box.insert("1.0", t("msg.no_errors"))
            return
        lines = [f"{word} (×{count})" if count > 1 else word for word, count in sorted(words.items(), key=lambda i: i[0].lower())]
        self.errors_box.insert("1.0", "\n".join(lines))

    def _run_spellcheck(self) -> None:
        t = self.i18n.t
        snapshot = self._text_value()
        if not snapshot.strip():
            messagebox.showwarning(t("dlg.spelling"), t("msg.no_text_to_check"))
            return
        code = SPELL_LANG_MAP[self.spell_lang_var.get()]
        ignored = frozenset(self._ignored_words)

        def work(ctx: Any) -> list:
            return SpellcheckService(code).find_errors(snapshot, ignored)

        def on_success(errors: list) -> None:
            if self._text_value() != snapshot:
                # tekst zmienil sie w trakcie sprawdzania - wyniki przesunietych znakow bylyby bledne
                self._set_status(t("status.spellcheck_done", count=0))
                return
            self._tb.tag_remove("spell_error", "1.0", "end")
            for error in errors:
                self._tb.tag_add("spell_error", f"1.0+{error.start}c", f"1.0+{error.end}c")
            self._refresh_error_box()
            self._set_status(t("status.spellcheck_done", count=len(errors)))

        def on_error(exc: BaseException) -> None:
            if isinstance(exc, SpellDictionaryMissingError):
                messagebox.showwarning(t("dlg.spelling"), self._describe_error(exc))
            else:
                messagebox.showerror(t("dlg.spelling"), t("msg.spellcheck_error", error=str(exc)))
            self._refresh_installed_languages()

        if self._start_job(work, on_success=on_success, on_error=on_error):
            self._set_status(t("status.spellcheck_running"))
            self.progress.configure(mode="indeterminate")
            self.progress.start()
            self._indeterminate_until_done()

    def _indeterminate_until_done(self) -> None:
        """Pasek bez znanej dlugosci na czas sprawdzania; wraca do trybu procentowego po zakonczeniu."""

        def restore() -> None:
            if self.runner.busy:
                self.after(150, restore)
                return
            self.progress.stop()
            self.progress.configure(mode="determinate")
            self.progress.set(0)

        self.after(150, restore)

    def _fix_all_spelling(self) -> None:
        t = self.i18n.t
        ranges = self._spell_ranges()
        if not self._text_value().strip():
            messagebox.showwarning(t("dlg.spelling"), t("msg.no_text_to_fix"))
            return
        if not ranges:
            messagebox.showinfo(t("dlg.spelling"), t("msg.no_errors_to_fix"))
            return
        words = sorted({self._tb.get(start, end) for start, end in ranges}, key=str.lower)
        if not messagebox.askyesno(t("dlg.spelling"), t("msg.confirm_fix_all", count=len(ranges))):
            return
        code = SPELL_LANG_MAP[self.spell_lang_var.get()]

        def work(ctx: Any) -> dict[str, str]:
            service = SpellcheckService(code)
            replacements: dict[str, str] = {}
            for index, word in enumerate(words):
                ctx.raise_if_cancelled()
                ctx.report(index, len(words), word)
                found = service.suggest(word, 1, fast=True)
                if found:
                    replacements[word] = found[0]
            ctx.report(len(words), len(words), "")
            return replacements

        def on_progress(done: int, total: int, _message: Any) -> None:
            self.progress.set(done / total if total else 0)
            self._set_status(t("status.fixing", done=done, total=total))

        def on_success(replacements: dict[str, str]) -> None:
            applied = self._apply_replacements(replacements)
            self._refresh_error_box()
            self._set_status(t("status.spelling_fixed", count=applied))

        def on_error(exc: BaseException) -> None:
            messagebox.showerror(t("dlg.spelling"), t("msg.fix_failed", error=self._describe_error(exc, "msg.fix_failed")))

        self._start_job(work, on_success=on_success, on_error=on_error, on_progress=on_progress)

    def _apply_replacements(self, replacements: dict[str, str]) -> int:
        """Zamienia oznaczone slowa jednym krokiem cofania. Zwraca liczbe zamian."""
        tb = self._tb
        applied = 0
        tb.configure(autoseparators=False)
        tb.edit_separator()
        try:
            for start, end in reversed(self._spell_ranges()):
                word = tb.get(start, end)
                new = replacements.get(word)
                if new is None:
                    continue
                tb.delete(start, end)
                tb.insert(start, new)
                applied += 1
        finally:
            tb.edit_separator()
            tb.configure(autoseparators=True)
        return applied

    def _ignore_spelling(self) -> None:
        t = self.i18n.t
        for start, end in self._spell_ranges():
            self._ignored_words.add(self._tb.get(start, end).lower())
        self._tb.tag_remove("spell_error", "1.0", "end")
        self.errors_box.delete("1.0", "end")
        self.errors_box.insert("1.0", t("msg.ignored_note"))
        self._set_status(t("status.spelling_ignored"))

    def _add_selected_word(self) -> None:
        t = self.i18n.t
        tb = self._tb
        selected = tb.get("sel.first", "sel.last").strip() if tb.tag_ranges("sel") else ""
        if not selected:
            messagebox.showwarning(t("dlg.dictionary"), t("msg.select_word"))
            return
        self._add_word_to_dictionary(selected)

    def _add_word_to_dictionary(self, word: str) -> None:
        t = self.i18n.t
        code = SPELL_LANG_MAP[self.spell_lang_var.get()]
        try:
            add_custom_word(code, word)
        except OSError as exc:
            messagebox.showerror(t("dlg.dictionary"), t("msg.word_add_failed", error=str(exc)))
            return
        self._remove_marks_for(word)
        self._refresh_error_box()
        self._set_status(t("status.word_added", word=word))

    def _remove_marks_for(self, word: str) -> None:
        key = word.lower()
        for start, end in self._spell_ranges():
            if self._tb.get(start, end).lower() == key:
                self._tb.tag_remove("spell_error", start, end)

    # ---------------------------------------------------- menu kontekstowe

    def _spell_range_at(self, index: str) -> tuple[str, str] | None:
        for start, end in self._spell_ranges():
            if self._tb.compare(start, "<=", index) and self._tb.compare(index, "<", end):
                return start, end
        return None

    def _on_text_right_click(self, event: Any) -> str:
        tb = self._tb
        tb.focus_set()
        index = tb.index(f"@{event.x},{event.y}")
        located = self._spell_range_at(index)
        if located is None or self.suggest_runner.busy:
            self._show_text_menu(event, None, [])
            return "break"

        start, end = located
        word = tb.get(start, end)
        code = SPELL_LANG_MAP[self.spell_lang_var.get()]
        t = self.i18n.t
        self._set_status(t("status.suggesting", word=word))

        def work(_ctx: Any) -> list[str]:
            return SpellcheckService(code).suggest(word)

        def on_success(suggestions: list[str]) -> None:
            self._set_status(t("status.ready"))
            self._show_text_menu(event, (start, end, word), suggestions)

        def on_error(_exc: BaseException) -> None:
            self._show_text_menu(event, (start, end, word), [])

        self.suggest_runner.start(work, on_success=on_success, on_error=on_error)
        return "break"

    def _show_text_menu(self, event: Any, target: tuple[str, str, str] | None, suggestions: list[str]) -> None:
        t = self.i18n.t
        tb = self._tb
        menu = tk.Menu(self, tearoff=0)

        if target is not None:
            start, end, word = target
            if suggestions:
                for suggestion in suggestions:
                    menu.add_command(
                        label=suggestion,
                        font=("Segoe UI", 10, "bold"),
                        command=lambda s=suggestion: self._replace_word(start, end, word, s),
                    )
            else:
                menu.add_command(label=t("ctx.no_suggestions"), state="disabled")
            menu.add_separator()
            menu.add_command(label=t("ctx.ignore_word"), command=lambda: self._ignore_word(word))
            menu.add_command(label=t("ctx.add_word"), command=lambda: self._add_word_to_dictionary(word))
            menu.add_separator()

        has_selection = bool(tb.tag_ranges("sel"))
        menu.add_command(label=t("ctx.cut"), command=lambda: tb.event_generate("<<Cut>>"), state="normal" if has_selection else "disabled")
        menu.add_command(label=t("ctx.copy"), command=lambda: tb.event_generate("<<Copy>>"), state="normal" if has_selection else "disabled")
        menu.add_command(label=t("ctx.paste"), command=lambda: tb.event_generate("<<Paste>>"))
        menu.add_separator()
        menu.add_command(label=t("ctx.select_all"), command=lambda: tb.tag_add("sel", "1.0", "end-1c"))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _replace_word(self, start: str, end: str, word: str, replacement: str) -> None:
        tb = self._tb
        if tb.get(start, end) != word:
            return  # tekst zmienil sie, zanim wybrano podpowiedz
        tb.delete(start, end)
        tb.insert(start, replacement)
        self._refresh_error_box()

    def _ignore_word(self, word: str) -> None:
        self._ignored_words.add(word.lower())
        self._remove_marks_for(word)
        self._refresh_error_box()

    # ------------------------------------------------------------------ zapis

    def _export(self, kind: str) -> None:
        t = self.i18n.t
        if self.runner.busy:
            return
        text = self._text_value().strip()
        if not text:
            messagebox.showwarning(t("dlg.export"), t("msg.no_text_to_export"))
            return
        if self._spell_ranges() and not messagebox.askyesno(t("dlg.export"), t("msg.confirm_export_with_errors")):
            return
        extension = ".txt" if kind == "txt" else ".docx"
        label = t("ft.txt") if kind == "txt" else t("ft.docx")
        path = filedialog.asksaveasfilename(
            title=t("dlg.export"), defaultextension=extension, filetypes=[(label, f"*{extension}")]
        )
        if not path:
            return
        output = Path(path)
        try:
            if kind == "txt":
                ExportService.export_txt(text, output, reflow=bool(self.reflow_var.get()))
            else:
                ExportService.export_docx(text, output, reflow=bool(self.reflow_var.get()))
        except Exception as exc:  # noqa: BLE001 - blad zapisu (uprawnienia, plik otwarty) pokazujemy uzytkownikowi
            messagebox.showerror(t("dlg.export"), t("msg.export_failed", error=str(exc)))
            return
        self._set_status(t("status.saved", path=output))

    def _export_pdf(self) -> None:
        t = self.i18n.t
        if self.runner.busy:
            return
        if not self.input_files:
            messagebox.showwarning(t("dlg.export"), t("msg.no_source_for_pdf"))
            return
        if not self.ocr_service.is_available():
            messagebox.showwarning(t("dlg.ocr"), t("msg.no_tesseract"))
            return
        spec = self._lang_spec()
        try:
            self.ocr_service.ensure_lang_installed(spec)
        except OCRLanguageMissingError as exc:
            messagebox.showwarning(t("dlg.ocr"), t("msg.lang_missing", lang=exc.lang_code))
            return

        files = list(self.input_files)
        if len(files) == 1:
            chosen = filedialog.asksaveasfilename(
                title=t("dlg.export"),
                defaultextension=".pdf",
                initialfile=f"{files[0].stem}_ocr.pdf",
                filetypes=[(t("ft.pdf"), "*.pdf")],
            )
            if not chosen:
                return
            targets = [Path(chosen)]
        else:
            folder = filedialog.askdirectory(title=t("dlg.export"))
            if not folder:
                return
            targets = [self._unique_path(Path(folder) / f"{p.stem}_ocr.pdf") for p in files]

        force_ocr = bool(self.force_var.get())
        ocr = self.ocr_service

        def work(ctx: Any) -> list[Path]:
            written = []
            for index, (source, target) in enumerate(zip(files, targets, strict=True)):

                def progress(done: int, total: int, name: str, _i: int = index) -> None:
                    ctx.report(int(((_i + done / max(total, 1)) / len(files)) * 1000), 1000, (name, done, total))

                ocr.export_searchable_pdf(source, target, spec, progress=progress, cancel=ctx.cancel_event, force_ocr=force_ocr)
                written.append(target)
            return written

        def on_progress(done: int, total: int, message: Any) -> None:
            self.progress.set(done / total if total else 0)
            if isinstance(message, tuple):
                _name, page, pages = message
                self._set_status(t("status.pdf_page", done=min(page + 1, pages), total=pages))

        def on_success(written: list[Path]) -> None:
            self._set_status(t("status.saved", path=written[-1] if len(written) == 1 else written[0].parent))

        def on_error(exc: BaseException) -> None:
            messagebox.showerror(t("dlg.export"), self._describe_error(exc, "msg.export_failed"))

        self._start_job(work, on_success=on_success, on_error=on_error, on_progress=on_progress)

    @staticmethod
    def _unique_path(path: Path) -> Path:
        candidate, counter = path, 1
        while candidate.exists():
            candidate = path.with_name(f"{path.stem} ({counter}){path.suffix}")
            counter += 1
        return candidate


def run() -> None:
    ctk.set_default_color_theme("blue")
    app = OCRStudioApp()
    app.mainloop()


if __name__ == "__main__":
    run()
