"""Testy interfejsu na prawdziwym oknie Tk (ukrytym). Jedna instancja na modul."""

import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image, ImageDraw

from src import main as main_module
from src.main import fit_window_size

pytestmark = pytest.mark.gui


class Dialogs:
    """Podstawia okna dialogowe i zapisuje, o co zapytano."""

    def __init__(self):
        self.calls = []
        self.answers = {"askyesno": True}
        self.save_path = None
        self.open_paths = ()
        self.directory = ""

    def record(self, name, answer=None):
        def handler(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            return self.answers.get(name, answer)

        return handler

    def names(self):
        return [name for name, _a, _k in self.calls]


@pytest.fixture(scope="module")
def app(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("gui")
    with pytest.MonkeyPatch.context() as mp:
        saved = []
        from src.settings import default_settings

        mp.setattr(main_module, "load_settings", lambda: default_settings("pl"))
        mp.setattr(main_module, "save_settings", saved.append)
        custom = tmp / "custom"
        custom.mkdir()
        mp.setattr("src.spellcheck_service.CUSTOM_DICTS_DIR", custom)
        window = main_module.OCRStudioApp()
        window.withdraw()
        window.update()
        window.saved_settings = saved
        window.tmp = tmp
        yield window
        try:
            window.destroy()
        except Exception:  # noqa: BLE001
            pass


@pytest.fixture
def dialogs(monkeypatch):
    d = Dialogs()
    for name in ("showinfo", "showwarning", "showerror", "askyesno"):
        monkeypatch.setattr(f"tkinter.messagebox.{name}", d.record(name))
    monkeypatch.setattr("tkinter.filedialog.asksaveasfilename", lambda **k: d.save_path or "")
    monkeypatch.setattr("tkinter.filedialog.askopenfilenames", lambda **k: d.open_paths)
    monkeypatch.setattr("tkinter.filedialog.askdirectory", lambda **k: d.directory)
    return d


@pytest.fixture(autouse=True)
def reset(app):
    wait(app)
    app._ignored_words.clear()
    app.input_files = []
    app._refresh_path_label()
    app._replace_all_text("")
    app._tb.edit_reset()
    app._clear_spell_marks()
    app._tb.tag_remove("low_conf", "1.0", "end")
    app.ocr_lang_var.set("Polski")
    app._ocr_lang2 = ""
    app.spell_lang_var.set("English (en_US)")
    app.mark_var.set(True)
    app.force_var.set(False)
    app.reflow_var.set(True)
    app.i18n.set_language("pl")
    app._relabel()
    app.saved_settings.clear()
    app.update()
    yield


def wait(app, timeout=60):
    end = time.time() + timeout
    while app.runner.busy and time.time() < end:
        app.update()
        time.sleep(0.01)
    app.update()
    time.sleep(0.02)
    app.update()


def set_text(app, text):
    app._replace_all_text(text)
    app.update()


def spell_words(app):
    return [app._tb.get(s, e) for s, e in app._spell_ranges()]


# --------------------------------------------------------------- okno i jezyk


def test_window_fits_typical_screens():
    for width, height, scale in [(1920, 1080, 1.5), (1920, 1080, 1.25), (1366, 768, 1.0), (1366, 768, 1.25), (1280, 720, 1.5)]:
        w, h = fit_window_size(width, height, scale)
        assert w * scale <= width and h * scale + 88 <= height, (width, height, scale, w, h)
    assert fit_window_size(2560, 1080, 1.0) == (1200, 760)
    assert fit_window_size(1920, 1080, 0)[0] > 0  # skala zero nie moze dzielic przez zero


def test_startup_state(app):
    assert app.title().startswith("Studio OCR")
    assert app._dnd_ready is True, app._dnd_error
    assert len(app._lockable) > 10
    assert app.path_var.get().startswith("Brak wybranego pliku")
    assert app._tb.cget("undo") == 1


def test_language_switch_relabels_in_place_without_rebuilding(app):
    widget_ids = {id(w) for w in app.winfo_children()}
    app._tb.insert("end", "tekst uzytkownika")
    app._on_language_changed("EN")
    app.update()
    assert app._lockable[0].cget("text") == "Load files (PDF/image)"
    assert "author" in app.title_label.cget("text")
    assert app.path_var.get().startswith("No file selected")
    assert app.theme_seg.get() == "System"
    assert {id(w) for w in app.winfo_children()} == widget_ids, "okno zostalo przebudowane"
    assert app._text_value() == "tekst uzytkownika", "tekst uzytkownika nie moze zginac przy zmianie jezyka"
    app._on_language_changed("PL")
    assert app._lockable[0].cget("text") == "Wczytaj pliki (PDF/obraz)"


def test_language_switch_keeps_undo_history_and_marks(app):
    set_text(app, "alfa beta")
    app._tb.tag_add("low_conf", "1.0", "1.4")
    app._on_language_changed("EN")
    app.update()
    assert app._tb.tag_ranges("low_conf"), "znaczniki powinny przetrwac zmiane jezyka"
    app._tb.edit_undo()
    assert app._text_value() == ""


def test_settings_are_saved_on_change(app):
    app._on_theme_changed(app.i18n.t("theme.dark"))
    assert app.saved_settings[-1]["theme"] == "Dark"
    app._on_language_changed("EN")
    assert app.saved_settings[-1]["language"] == "en"
    app.ocr_lang_var.set("Deutsch")
    app._on_lang_choice_changed("Deutsch")
    app._on_second_lang_changed("English")
    last = app.saved_settings[-1]
    assert (last["ocr_lang"], last["ocr_lang2"]) == ("Deutsch", "English")
    app._on_theme_changed(app.i18n.t("theme.system"))


def test_second_language_none_label_follows_ui_language(app):
    app._on_second_lang_changed(app.i18n.t("lbl.none"))
    assert app._ocr_lang2 == ""
    app._on_language_changed("EN")
    assert app.ocr_lang2_var.get() == "(none)"
    app._ocr_lang2 = "English"
    app._relabel()
    assert app.ocr_lang2_var.get() == "English"
    assert app._lang_spec() == "pol+eng"
    app.ocr_lang_var.set("English")
    assert app._lang_spec() == "eng", "ten sam jezyk dwa razy nie moze trafic do Tesseract"


# ----------------------------------------------------------------- pliki i DnD


def test_drop_event_parses_braced_paths_and_filters_unsupported(app, tmp_path, dialogs):
    good = tmp_path / "dokument ze spacja.png"
    other = tmp_path / "b.pdf"
    bad = tmp_path / "c.txt"
    for f in (good, other, bad):
        f.write_bytes(b"x")
    # tkdnd zwraca liste Tcl: sciezki ze spacjami w nawiasach klamrowych, pozostale z ukosnikami "/"
    event = SimpleNamespace(data=f"{{{good}}} {other.as_posix()} {bad.as_posix()}", action="copy")
    assert app._on_drop(event) == "copy"
    assert app.input_files == [good, other]
    assert "1" in app.status_var.get()  # pominieto 1 nieobslugiwany plik
    assert "Wybrane pliki: 2" in app.path_var.get()


def test_drop_of_a_folder_expands_to_supported_files(app, tmp_path):
    (tmp_path / "x.png").write_bytes(b"x")
    (tmp_path / "y.TIFF").write_bytes(b"x")
    (tmp_path / "z.docx").write_bytes(b"x")
    app._set_input_files([tmp_path])
    assert [p.name for p in app.input_files] == ["x.png", "y.TIFF"]


def test_drop_is_ignored_while_busy(app, tmp_path, dialogs):
    started = app._start_job(lambda ctx: time.sleep(0.3))
    assert started
    app._on_drop(SimpleNamespace(data=str(tmp_path / "a.png"), action="copy"))
    assert app.input_files == []
    wait(app)


def test_tif_extension_is_accepted(app, tmp_path):
    # regresja: filtr dialogu nie zawieral *.tif
    path = tmp_path / "scan.tif"
    path.write_bytes(b"x")
    app._set_input_files([path])
    assert app.input_files == [path]


def test_pick_files_dialog_filter_lists_tif(app, monkeypatch):
    captured = {}
    monkeypatch.setattr("tkinter.filedialog.askopenfilenames", lambda **k: captured.update(k) or ())
    app._pick_files()
    patterns = captured["filetypes"][0][1]
    assert "*.tif" in patterns.split() and "*.tiff" in patterns.split() and "*.pdf" in patterns.split()


# ------------------------------------------------------------------------- OCR


def make_sample(app, lines=("Zażółć gęślą jaźń", "Studio OCR działa"), name="g.png"):
    image = Image.new("RGB", (1500, 120 + 80 * len(lines)), "white")
    draw = ImageDraw.Draw(image)
    from tests.conftest import _font

    for index, line in enumerate(lines):
        draw.text((60, 50 + index * 80), line, fill="black", font=_font(48))
    path = app.tmp / name
    image.save(path, dpi=(200, 200))
    return path


def test_ocr_runs_in_background_and_locks_the_interface(app, dialogs):
    app._set_input_files([make_sample(app)])
    app._run_ocr()
    assert app.runner.busy
    assert all(w.cget("state") == "disabled" for w in app._lockable)
    assert app.cancel_button.winfo_manager() == "grid"
    wait(app)
    assert not app.runner.busy
    assert all(w.cget("state") == "normal" for w in app._lockable)
    assert app.cancel_button.winfo_manager() == ""
    assert "Zażółć gęślą jaźń" in app._text_value()
    assert "OCR zakończony" in app.status_var.get()
    assert dialogs.names() == []


def test_ocr_result_is_one_undo_step(app, dialogs):
    set_text(app, "poprzednia tresc")
    app._tb.edit_reset()
    app._set_input_files([make_sample(app)])
    app._run_ocr()
    wait(app)
    assert "Zażółć" in app._text_value()
    app._tb.edit_undo()
    assert app._text_value() == "poprzednia tresc"
    app._tb.edit_redo()
    assert "Zażółć" in app._text_value()


def test_manual_edits_are_not_overwritten_without_confirmation(app, dialogs):
    app._set_input_files([make_sample(app)])
    app._run_ocr()
    wait(app)
    app._tb.insert("end", " MOJA POPRAWKA")
    app.update()
    assert app._text_dirty

    dialogs.answers["askyesno"] = False
    app._run_ocr()
    wait(app)
    assert "askyesno" in dialogs.names()
    assert "MOJA POPRAWKA" in app._text_value(), "odmowa musi zostawic tekst nietkniety"

    dialogs.answers["askyesno"] = True
    app._run_ocr()
    wait(app)
    assert "MOJA POPRAWKA" not in app._text_value()
    app._tb.edit_undo()
    assert "MOJA POPRAWKA" in app._text_value(), "zastapienie musi dac sie cofnac"


def test_ocr_without_manual_edits_does_not_ask(app, dialogs):
    app._set_input_files([make_sample(app)])
    app._run_ocr()
    wait(app)
    app._run_ocr()
    wait(app)
    assert "askyesno" not in dialogs.names()


def test_new_document_during_ocr_is_ignored_no_crash(app, dialogs):
    # regresja: watek czytal self.current_input_file, a "Nowy dokument" ustawial go na None -> AttributeError
    app._set_input_files([make_sample(app)])
    app._run_ocr()
    app._new_document()
    assert app.input_files, "Nowy dokument w trakcie OCR nie moze zmieniac stanu"
    wait(app)
    assert "showerror" not in dialogs.names()
    assert "Zażółć" in app._text_value()


def test_second_ocr_click_does_not_start_second_thread(app, dialogs):
    app._set_input_files([make_sample(app)])
    app._run_ocr()
    first = app.runner.current
    app._run_ocr()
    assert app.runner.current is first
    assert "showinfo" in dialogs.names()
    wait(app)


def test_file_change_during_ocr_does_not_affect_running_job(app, dialogs, tmp_path):
    sample = make_sample(app, ("Pierwszy plik alpha",), name="first.png")
    other = make_sample(app, ("Drugi plik bravo",), name="second.png")
    app._set_input_files([sample])
    app._run_ocr()
    app.input_files = [other]  # uzytkownik "wybiera" inny plik w trakcie pracy
    wait(app)
    assert "alpha" in app._text_value() and "bravo" not in app._text_value()


def test_worker_thread_never_reads_window_state(app, dialogs):
    """Zasada: wszystko, czego potrzebuje watek, jest kopiowane PRZED startem.

    Regresja z audytu: watek czytal self.current_input_file, a "Nowy dokument"
    zerowal go w trakcie pracy. Lista plikow zapisuje, z jakiego watku ja czytano.
    """
    import threading

    readers = []

    class SpyList(list):
        def __iter__(self):
            readers.append(threading.get_ident())
            return super().__iter__()

        def __getitem__(self, item):
            readers.append(threading.get_ident())
            return super().__getitem__(item)

    app._set_input_files([make_sample(app)])
    app.input_files = SpyList(app.input_files)
    readers.clear()
    app._run_ocr()
    wait(app)
    assert "Zażółć" in app._text_value()
    assert readers and set(readers) == {threading.get_ident()}, "watek roboczy czytal stan okna"


def test_ocr_missing_engine_shows_warning(app, dialogs, monkeypatch):
    app._set_input_files([make_sample(app)])
    monkeypatch.setattr(app.ocr_service, "is_available", lambda: False)
    app._run_ocr()
    assert "showwarning" in dialogs.names() and not app.runner.busy


def test_ocr_without_file_warns(app, dialogs):
    app._run_ocr()
    assert dialogs.names() == ["showwarning"]


def test_ocr_missing_language_warns_before_starting(app, dialogs):
    app._set_input_files([make_sample(app)])
    app.ocr_lang_var.set("Deutsch")
    app._run_ocr()
    assert dialogs.names() == ["showwarning"] and not app.runner.busy
    assert "deu" in dialogs.calls[0][1][1]


def test_ocr_error_is_reported_with_dialog_not_exception(app, dialogs):
    bad = app.tmp / "bad.pdf"
    bad.write_bytes(b"nie pdf")
    app._set_input_files([bad])
    app._run_ocr()
    wait(app)
    assert dialogs.names() == ["showerror"]
    assert "bad.pdf" in dialogs.calls[0][1][1]
    assert "Błąd OCR" in app.status_var.get()
    assert all(w.cget("state") == "normal" for w in app._lockable)


def test_batch_ocr_adds_file_headers_and_shifts_marks(app, dialogs):
    first = make_sample(app, ("Alfa jeden",), name="a1.png")
    second = make_sample(app, ("Bravo dwa",), name="a2.png")
    app._set_input_files([first, second])
    app._run_ocr()
    wait(app)
    text = app._text_value()
    assert "=== a1.png ===" in text and "=== a2.png ===" in text
    assert text.index("Alfa") < text.index("=== a2.png ===") < text.index("Bravo")


def test_uncertain_words_are_highlighted_and_toggle_clears_them(app, dialogs, monkeypatch):
    from src.ocr_service import OCRResult

    app._set_result(OCRResult(text="dobre watpliwe ok", low_confidence=[(6, 14)], pages=1), mark_uncertain=True)
    ranges = app._tb.tag_ranges("low_conf")
    assert app._tb.get(ranges[0], ranges[1]) == "watpliwe"
    app.mark_var.set(False)
    app._on_mark_toggled()
    assert not app._tb.tag_ranges("low_conf")


def test_cancel_stops_job_and_restores_interface(app, dialogs, tmp_path):
    from tests.conftest import _font

    frames = []
    for index in range(30):
        frame = Image.new("RGB", (1500, 300), "white")
        ImageDraw.Draw(frame).text((50, 80), f"Strona {index} alpha bravo", fill="black", font=_font(48))
        frames.append(frame)
    tiff = tmp_path / "long.tif"
    frames[0].save(tiff, save_all=True, append_images=frames[1:], dpi=(200, 200))
    app._set_input_files([tiff])
    app.ocr_lang_var.set("English")
    app._run_ocr()
    time.sleep(0.6)
    app.update()
    app._cancel_job()
    wait(app, 15)
    assert not app.runner.busy
    assert "anulowana" in app.status_var.get()
    assert app._text_value() == "", "anulowany OCR nie powinien zapisac czesciowego wyniku"
    assert dialogs.names() == []


def test_closing_window_during_ocr_cancels_the_job(app, dialogs, tmp_path, monkeypatch):
    from tests.conftest import _font

    image = Image.new("RGB", (4000, 7300), "white")
    draw = ImageDraw.Draw(image)
    for index in range(80):
        draw.text((60, 50 + index * 90), f"Linia {index} Lorem ipsum dolor sit amet consectetur", fill="black", font=_font(44))
    path = tmp_path / "heavy.png"
    image.save(path, dpi=(300, 300))
    app._set_input_files([path])
    app.ocr_lang_var.set("English")
    app._run_ocr()
    time.sleep(0.5)
    monkeypatch.setattr(app, "destroy", lambda: None)  # nie niszczymy wspolnego okna testowego
    started = time.perf_counter()
    app._on_close()
    assert time.perf_counter() - started < 3.0
    assert app.runner.current.finished or not app.runner.current._thread.is_alive()
    app.update()
    wait(app, 10)


# -------------------------------------------------------------------- pisownia


def test_spellcheck_marks_errors_with_tags_and_lists_them(app, dialogs):
    set_text(app, "Ths is a tset of the sistem. Ths again.")
    app._run_spellcheck()
    wait(app)
    assert spell_words(app) == ["Ths", "tset", "sistem", "Ths"]
    listing = app.errors_box.get("1.0", "end")
    assert "Ths (×2)" in listing and "tset" in listing
    assert "Błędy: 4" in app.status_var.get()


def test_error_marks_follow_the_text_when_user_edits(app, dialogs):
    # regresja: pozycje znakow z chwili sprawdzenia przesuwaly sie po edycji i psuly dokument
    set_text(app, "Ths is a tset")
    app._run_spellcheck()
    wait(app)
    app._tb.insert("1.0", "NOWY AKAPIT NA POCZATKU. ")
    app.update()
    assert spell_words(app) == ["Ths", "tset"], "znaczniki musza przesunac sie razem z tekstem"


def test_fix_all_is_confirmed_applied_and_undone_in_one_step(app, dialogs):
    original = "Ths is a tset of the sistem."
    set_text(app, original)
    app._tb.edit_reset()
    app._run_spellcheck()
    wait(app)
    app._fix_all_spelling()
    wait(app)
    fixed = app._text_value()
    assert "askyesno" in dialogs.names()
    assert "Ths" not in fixed and "tset" not in fixed and "sistem" not in fixed
    assert fixed.endswith(".") and " is a " in fixed
    app._tb.edit_undo()
    assert app._text_value() == original, "jedno Ctrl+Z ma cofnac wszystkie zamiany"


def test_fix_all_declined_changes_nothing(app, dialogs):
    set_text(app, "Ths is a tset")
    app._run_spellcheck()
    wait(app)
    dialogs.answers["askyesno"] = False
    app._fix_all_spelling()
    wait(app)
    assert app._text_value() == "Ths is a tset"


def test_fix_all_survives_edit_while_suggestions_are_computed(app, dialogs):
    set_text(app, "Ths is a tset")
    app._run_spellcheck()
    wait(app)
    app._fix_all_spelling()
    app._tb.insert("1.0", "PREFIX ")  # uzytkownik pisze, gdy trwa liczenie podpowiedzi
    wait(app)
    text = app._text_value()
    assert text.startswith("PREFIX ") and "Ths" not in text and "tset" not in text


def test_replace_word_refuses_when_text_changed_under_menu(app):
    set_text(app, "Ths is")
    app._tb.tag_add("spell_error", "1.0", "1.3")
    start, end = app._spell_ranges()[0]
    app._replace_word(start, end, "Thx", "This")  # slowo pod zakresem to juz nie "Thx"
    assert app._text_value() == "Ths is"
    app._replace_word(start, end, "Ths", "This")
    assert app._text_value() == "This is"


def test_ignore_all_marks_words_ignored_for_next_check(app, dialogs):
    set_text(app, "Ths is a tset")
    app._run_spellcheck()
    wait(app)
    app._ignore_spelling()
    assert not app._tb.tag_ranges("spell_error")
    app._run_spellcheck()
    wait(app)
    assert spell_words(app) == []


def test_add_word_to_dictionary_removes_all_its_marks(app, dialogs):
    set_text(app, "Zettel is Zettel")
    app._run_spellcheck()
    wait(app)
    assert spell_words(app) == ["Zettel", "Zettel"]
    app._tb.tag_add("sel", "1.0", "1.6")
    app._add_selected_word()
    assert spell_words(app) == []
    assert "Zettel" in app.status_var.get()
    app._run_spellcheck()
    wait(app)
    assert spell_words(app) == []


def test_add_word_without_selection_warns(app, dialogs):
    app._add_selected_word()
    assert dialogs.names() == ["showwarning"]


def test_spellcheck_empty_text_warns(app, dialogs):
    app._run_spellcheck()
    assert dialogs.names() == ["showwarning"] and not app.runner.busy


def test_spellcheck_with_missing_dictionary_warns(app, dialogs):
    set_text(app, "tekst")
    app.spell_lang_var.set("Deutsch (de_DE)")
    app._run_spellcheck()
    wait(app)
    assert dialogs.names() == ["showwarning"]
    assert "de_DE" in dialogs.calls[0][1][1]
    assert all(w.cget("state") == "normal" for w in app._lockable)


def test_text_changed_during_spellcheck_discards_stale_result(app, dialogs):
    set_text(app, "Ths is a tset")
    app._run_spellcheck()
    app._tb.insert("1.0", "XX ")  # zmiana zanim wynik wroci
    wait(app)
    assert spell_words(app) == [], "wynik policzony na starym tekscie nie moze byc naniesiony"


def test_context_menu_offers_suggestions_ignore_and_add(app, dialogs, monkeypatch):
    labels = []

    class RecordingMenu(main_module.tk.Menu):
        def add_command(self, **kwargs):
            labels.append((kwargs.get("label"), kwargs.get("state", "normal")))
            return super().add_command(**kwargs)

        def tk_popup(self, *args, **kwargs):  # bez blokujacego menu w tescie
            return None

    monkeypatch.setattr(main_module.tk, "Menu", RecordingMenu)
    set_text(app, "This is a systemm")
    app._run_spellcheck()
    wait(app)
    start, end = app._spell_ranges()[0]
    event = SimpleNamespace(x=0, y=0, x_root=0, y_root=0)
    app._show_text_menu(event, (start, end, "systemm"), ["system", "systems"])
    names = [label for label, _state in labels]
    assert names[:2] == ["system", "systems"]
    assert "Ignoruj to słowo" in names and "Dodaj do słownika" in names
    assert names[-4:] == ["Wytnij", "Kopiuj", "Wklej", "Zaznacz wszystko"]
    assert dict(labels)["Wytnij"] == "disabled"  # brak zaznaczenia


def test_context_menu_without_suggestions_says_so(app, monkeypatch):
    labels = []

    class RecordingMenu(main_module.tk.Menu):
        def add_command(self, **kwargs):
            labels.append(kwargs.get("label"))
            return super().add_command(**kwargs)

        def tk_popup(self, *a, **k):
            return None

    monkeypatch.setattr(main_module.tk, "Menu", RecordingMenu)
    set_text(app, "xqzv")
    app._tb.tag_add("spell_error", "1.0", "1.4")
    start, end = app._spell_ranges()[0]
    app._show_text_menu(SimpleNamespace(x=0, y=0, x_root=0, y_root=0), (start, end, "xqzv"), [])
    assert "(brak podpowiedzi)" in labels


# ------------------------------------------------------------------------ zapis


def test_export_txt_uses_reflow_setting(app, dialogs, tmp_path):
    set_text(app, "Pierwszy\nakapit\n\nDrugi")
    target = tmp_path / "wynik.txt"
    dialogs.save_path = str(target)
    app._export("txt")
    assert target.read_text(encoding="utf-8") == "Pierwszy akapit\n\nDrugi\n"
    app.reflow_var.set(False)
    app._export("txt")
    assert target.read_text(encoding="utf-8") == "Pierwszy\nakapit\n\nDrugi\n"
    assert "Zapisano" in app.status_var.get()


def test_export_docx_with_form_feed_does_not_crash(app, dialogs, tmp_path):
    from docx import Document

    set_text(app, "tekst\x0c z koncem strony")
    target = tmp_path / "wynik.docx"
    dialogs.save_path = str(target)
    app._export("docx")
    assert "showerror" not in dialogs.names()
    assert "tekst" in Document(str(target)).paragraphs[0].text


def test_export_asks_when_spelling_errors_remain(app, dialogs, tmp_path):
    set_text(app, "Ths is a tset")
    app._run_spellcheck()
    wait(app)
    dialogs.answers["askyesno"] = False
    dialogs.save_path = str(tmp_path / "x.txt")
    app._export("txt")
    assert "askyesno" in dialogs.names() and not (tmp_path / "x.txt").exists()


def test_export_empty_text_warns(app, dialogs):
    app._export("txt")
    assert dialogs.names() == ["showwarning"]


def test_export_write_failure_is_reported(app, dialogs, tmp_path):
    set_text(app, "tekst")
    dialogs.save_path = str(tmp_path / "brak_katalogu" / "x.txt")
    app._export("txt")
    assert dialogs.names() == ["showerror"]


def test_export_searchable_pdf_single_file(app, dialogs, tmp_path):
    app._set_input_files([make_sample(app, ("Przeszukiwalny dokument alpha bravo charlie",), name="pdf_in.png")])
    target = tmp_path / "wynik.pdf"
    dialogs.save_path = str(target)
    app._export_pdf()
    wait(app)
    assert target.exists() and dialogs.names() == []
    again = app.ocr_service.ocr_document(target, "pol")
    assert again.text_layer_pages == 1 and "alpha" in again.text


def test_export_searchable_pdf_batch_never_overwrites(app, dialogs, tmp_path):
    first = make_sample(app, ("Pierwszy alpha",), name="b1.png")
    second = make_sample(app, ("Drugi bravo",), name="b2.png")
    out = tmp_path / "out"
    out.mkdir()
    (out / "b1_ocr.pdf").write_bytes(b"istniejacy plik")
    dialogs.directory = str(out)
    app._set_input_files([first, second])
    app._export_pdf()
    wait(app)
    assert (out / "b1_ocr.pdf").read_bytes() == b"istniejacy plik"
    assert (out / "b1_ocr (1).pdf").exists() and (out / "b2_ocr.pdf").exists()


def test_export_pdf_without_source_warns(app, dialogs):
    app._export_pdf()
    assert dialogs.names() == ["showwarning"]


# ----------------------------------------------------------- jezyki i slowniki


def test_install_available_language_shows_info_without_network(app, dialogs):
    app.ocr_lang_var.set("Polski")
    app._install_ocr_language()
    assert dialogs.names() == ["showinfo"] and not app.runner.busy
    app.spell_lang_var.set("English (en_US)")
    app._install_spell_language()
    assert dialogs.names() == ["showinfo", "showinfo"] and not app.runner.busy


def test_install_language_failure_is_reported(app, dialogs, monkeypatch):
    from src.language_manager import DownloadError

    def boom(*args, **kwargs):
        raise DownloadError("deu.traineddata", "brak internetu")

    monkeypatch.setattr(app.language_manager, "install_ocr_language", boom)
    app.ocr_lang_var.set("Deutsch")
    app._install_ocr_language()
    wait(app)
    assert dialogs.names() == ["showerror"]
    assert "brak internetu" in dialogs.calls[0][1][1]
    assert all(w.cget("state") == "normal" for w in app._lockable)


def test_status_shows_bundled_languages_on_fresh_profile(app):
    app._refresh_installed_languages()
    status = app.status_var.get()
    assert "eng" in status and "pol" in status and "pl_PL" in status and "en_US" in status


def test_new_document_clears_everything_after_confirmation(app, dialogs):
    set_text(app, "do usuniecia")
    app.input_files = [Path("x.png")]
    app._ignored_words.add("x")
    dialogs.answers["askyesno"] = False
    app._new_document()
    assert app._text_value() == "do usuniecia"
    dialogs.answers["askyesno"] = True
    app._new_document()
    assert app._text_value() == "" and app.input_files == [] and not app._ignored_words


def test_copy_to_clipboard(app, dialogs):
    set_text(app, "  skopiuj mnie  ")
    app._copy_ocr_to_clipboard()
    assert app.clipboard_get() == "skopiuj mnie"
    set_text(app, "")
    app._copy_ocr_to_clipboard()
    assert dialogs.names()[-1] == "showwarning"


def test_dirty_flag_is_set_only_by_user_edits(app):
    set_text(app, "programowo")
    assert app._text_dirty is False
    app._tb.insert("end", " reczna zmiana")
    app.update()
    assert app._text_dirty is True
    set_text(app, "znowu programowo")
    assert app._text_dirty is False


def test_busy_start_while_busy_does_not_spawn(app, dialogs):
    assert app._start_job(lambda ctx: time.sleep(0.2))
    assert app._start_job(lambda ctx: None) is False
    assert "showinfo" in dialogs.names()
    wait(app)
