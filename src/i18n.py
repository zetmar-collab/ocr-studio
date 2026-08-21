from __future__ import annotations

TRANSLATIONS: dict[str, dict[str, str]] = {
    "pl": {
        "app.author": "autor",
        "sec.source": "1) Zrodlo dokumentu",
        "sec.ocr_lang": "2) Jezyk OCR",
        "sec.spelling": "3) Pisownia",
        "sec.export": "4) Eksport",
        "sec.appearance": "5) Wyglad",
        "sec.app_language": "6) Jezyk aplikacji",
        "btn.load_file": "Wczytaj PDF/obraz",
        "btn.scan_png": "Skanuj do PNG",
        "btn.scan_jpeg": "Skanuj do JPEG",
        "btn.scan_pdf": "Skanuj do PDF",
        "btn.install_ocr_lang": "Doinstaluj jezyk OCR",
        "btn.install_spell_dict": "Doinstaluj slownik pisowni",
        "btn.spellcheck": "Sprawdź pisownię",
        "btn.add_word": "Dodaj zaznaczone slowo do slownika",
        "btn.export_txt": "Eksportuj do TXT",
        "btn.export_docx": "Eksportuj do DOCX",
        "btn.run_ocr": "Uruchom OCR",
        "btn.copy_clipboard": "Kopiuj do schowka",
        "btn.new_document": "Nowy dokument",
        "btn.ignore": "Ignoruj",
        "btn.fix_spelling": "Popraw pisownię",
        "btn.do_ocr": "Dokonaj OCR",
        "btn.close": "Zamknij",
        "lbl.no_file": "Brak wybranego pliku.",
        "lbl.result_header": "Wynik OCR",
        "lbl.errors_header": "Błędy pisowni",
        "theme.system": "Systemowy",
        "theme.light": "Jasny",
        "theme.dark": "Ciemny",
        "status.ready": "Gotowe.",
        "status.langs": "Jezyki OCR: {ocr} | Slowniki pisowni: {spell}",
        "status.none": "brak",
        "status.scan_done": "Zeskanowano dokument: {name}",
        "status.ocr_running": "Trwa OCR...",
        "status.ocr_done": "OCR zakonczony.",
        "status.ocr_error": "Blad OCR.",
        "status.spellcheck_done": "Sprawdzanie pisowni zakończone. Błędy: {count}",
        "status.new_document": "Gotowe. Wczytaj plik lub zeskanuj nowy dokument.",
        "status.copied": "Skopiowano tekst OCR do schowka.",
        "status.spelling_fixed": "Zastosowano poprawki pisowni w tekście OCR.",
        "status.spelling_ignored": "Pisownia zignorowana.",
        "status.word_added": "Dodano do slownika: {word}",
        "status.saved": "Zapisano: {path}",
        "dlg.ocr": "OCR",
        "dlg.scan": "Skanowanie",
        "dlg.ocr_lang": "Jezyk OCR",
        "dlg.spelling": "Pisownia",
        "dlg.new_document": "Nowy dokument",
        "dlg.clipboard": "Schowek",
        "dlg.dictionary": "Slownik",
        "dlg.export": "Eksport",
        "msg.no_tesseract": (
            "Nie znaleziono silnika OCR dolaczonego do aplikacji. "
            "Zainstaluj aplikacje ponownie."
        ),
        "msg.no_file_selected": "Najpierw wybierz plik lub zeskanuj dokument.",
        "msg.lang_missing": (
            "Brak pliku jezyka OCR: {lang}.traineddata. "
            "Kliknij 'Doinstaluj jezyk OCR' w aplikacji."
        ),
        "msg.ocr_lang_installed": "Zainstalowano jezyk OCR: {lang}",
        "msg.ocr_lang_failed": "Nie udalo sie zainstalowac: {error}",
        "msg.spell_dict_installed": "Zainstalowano slownik: {dict}",
        "msg.spell_dict_failed": "Nie udalo sie zainstalowac slownika: {error}",
        "msg.spell_dict_missing": (
            "Brak slownika {dict}. Zainstaluj jezyk pisowni przed sprawdzeniem."
        ),
        "msg.no_text_to_check": "Brak tekstu do sprawdzenia.",
        "msg.spellcheck_error": "Blad sprawdzania pisowni: {error}",
        "msg.no_errors": "Brak błędów pisowni.",
        "msg.confirm_new_document": (
            "Wyczyścić wynik OCR i rozpocząć OCR nowego dokumentu lub obrazu?"
        ),
        "msg.no_text_to_copy": "Brak tekstu OCR do skopiowania.",
        "msg.no_text_to_fix": "Brak tekstu OCR do poprawy.",
        "msg.no_errors_to_fix": "Nie znaleziono błędów do poprawy.",
        "msg.fix_failed": "Nie udało się poprawić tekstu: {error}",
        "msg.ignored_note": "Pisownia zignorowana — możesz eksportować tekst bez ostrzeżenia.",
        "msg.select_word": "Zaznacz slowo w polu tekstu OCR.",
        "msg.word_add_failed": "Nie udalo sie dodac slowa: {error}",
        "msg.no_text_to_export": "Brak tekstu OCR do zapisania.",
        "msg.confirm_export_with_errors": (
            "Wykryto bledy pisowni. Czy chcesz kontynuowac zapis?"
        ),
        "msg.export_failed": "Nie udalo sie zapisac pliku: {error}",
        "msg.scan_failed": "Nie udalo sie zeskanowac: {error}",
        "msg.ocr_error": "Blad OCR: {error}",
        "err.scanner.win_only": "Skanowanie WIA jest dostepne tylko na Windows.",
        "err.scanner.no_pywin32": "Brak pywin32. Zainstaluj: pip install pywin32",
        "err.scanner.bad_format": "Obslugiwane formaty skanu: png, jpeg, pdf.",
        "err.scanner.no_device": "Nie wybrano urzadzenia skanujacego.",
        "err.scanner.cancelled": "Skanowanie anulowane.",
        "preview.title": "Podglad skanu",
        "preview.scanned": "Zeskanowano: {name}",
        "preview.pdf_info": "PDF — {pages} stron(y). Ponizej podglad pierwszej strony.",
        "preview.render_error": "Nie udalo sie wyswietlic podgladu: {error}",
    },
    "en": {
        "app.author": "author",
        "sec.source": "1) Document source",
        "sec.ocr_lang": "2) OCR language",
        "sec.spelling": "3) Spelling",
        "sec.export": "4) Export",
        "sec.appearance": "5) Appearance",
        "sec.app_language": "6) App language",
        "btn.load_file": "Load PDF/image",
        "btn.scan_png": "Scan to PNG",
        "btn.scan_jpeg": "Scan to JPEG",
        "btn.scan_pdf": "Scan to PDF",
        "btn.install_ocr_lang": "Install OCR language",
        "btn.install_spell_dict": "Install spelling dictionary",
        "btn.spellcheck": "Check spelling",
        "btn.add_word": "Add selected word to dictionary",
        "btn.export_txt": "Export to TXT",
        "btn.export_docx": "Export to DOCX",
        "btn.run_ocr": "Run OCR",
        "btn.copy_clipboard": "Copy to clipboard",
        "btn.new_document": "New document",
        "btn.ignore": "Ignore",
        "btn.fix_spelling": "Fix spelling",
        "btn.do_ocr": "Run OCR",
        "btn.close": "Close",
        "lbl.no_file": "No file selected.",
        "lbl.result_header": "OCR result",
        "lbl.errors_header": "Spelling errors",
        "theme.system": "System",
        "theme.light": "Light",
        "theme.dark": "Dark",
        "status.ready": "Ready.",
        "status.langs": "OCR languages: {ocr} | Spelling dictionaries: {spell}",
        "status.none": "none",
        "status.scan_done": "Document scanned: {name}",
        "status.ocr_running": "OCR running...",
        "status.ocr_done": "OCR finished.",
        "status.ocr_error": "OCR error.",
        "status.spellcheck_done": "Spell check finished. Errors: {count}",
        "status.new_document": "Ready. Load a file or scan a new document.",
        "status.copied": "Copied OCR text to clipboard.",
        "status.spelling_fixed": "Applied spelling corrections to the OCR text.",
        "status.spelling_ignored": "Spelling ignored.",
        "status.word_added": "Added to dictionary: {word}",
        "status.saved": "Saved: {path}",
        "dlg.ocr": "OCR",
        "dlg.scan": "Scanning",
        "dlg.ocr_lang": "OCR language",
        "dlg.spelling": "Spelling",
        "dlg.new_document": "New document",
        "dlg.clipboard": "Clipboard",
        "dlg.dictionary": "Dictionary",
        "dlg.export": "Export",
        "msg.no_tesseract": (
            "The OCR engine bundled with the app could not be found. "
            "Please reinstall the app."
        ),
        "msg.no_file_selected": "First select a file or scan a document.",
        "msg.lang_missing": (
            "OCR language file missing: {lang}.traineddata. "
            "Click 'Install OCR language' in the app."
        ),
        "msg.ocr_lang_installed": "Installed OCR language: {lang}",
        "msg.ocr_lang_failed": "Failed to install: {error}",
        "msg.spell_dict_installed": "Installed dictionary: {dict}",
        "msg.spell_dict_failed": "Failed to install dictionary: {error}",
        "msg.spell_dict_missing": (
            "Dictionary {dict} is missing. Install the spelling language before checking."
        ),
        "msg.no_text_to_check": "No text to check.",
        "msg.spellcheck_error": "Spell check error: {error}",
        "msg.no_errors": "No spelling errors.",
        "msg.confirm_new_document": (
            "Clear the OCR result and start OCR on a new document or image?"
        ),
        "msg.no_text_to_copy": "No OCR text to copy.",
        "msg.no_text_to_fix": "No OCR text to fix.",
        "msg.no_errors_to_fix": "No errors found to fix.",
        "msg.fix_failed": "Failed to fix the text: {error}",
        "msg.ignored_note": "Spelling ignored — you can export the text without a warning.",
        "msg.select_word": "Select a word in the OCR text field.",
        "msg.word_add_failed": "Failed to add the word: {error}",
        "msg.no_text_to_export": "No OCR text to save.",
        "msg.confirm_export_with_errors": (
            "Spelling errors detected. Do you want to continue saving?"
        ),
        "msg.export_failed": "Failed to save the file: {error}",
        "msg.scan_failed": "Failed to scan: {error}",
        "msg.ocr_error": "OCR error: {error}",
        "err.scanner.win_only": "WIA scanning is only available on Windows.",
        "err.scanner.no_pywin32": "pywin32 is missing. Install with: pip install pywin32",
        "err.scanner.bad_format": "Supported scan formats: png, jpeg, pdf.",
        "err.scanner.no_device": "No scanning device selected.",
        "err.scanner.cancelled": "Scan cancelled.",
        "preview.title": "Scan preview",
        "preview.scanned": "Scanned: {name}",
        "preview.pdf_info": "PDF — {pages} page(s). Preview of the first page below.",
        "preview.render_error": "Failed to display preview: {error}",
    },
}

DEFAULT_LANGUAGE = "pl"


class I18n:
    def __init__(self, language: str = DEFAULT_LANGUAGE) -> None:
        self.language = language if language in TRANSLATIONS else DEFAULT_LANGUAGE

    def set_language(self, language: str) -> None:
        self.language = language if language in TRANSLATIONS else DEFAULT_LANGUAGE

    def t(self, key: str, **kwargs: object) -> str:
        table = TRANSLATIONS.get(self.language, TRANSLATIONS[DEFAULT_LANGUAGE])
        text = table.get(key) or TRANSLATIONS[DEFAULT_LANGUAGE].get(key, key)
        return text.format(**kwargs) if kwargs else text
