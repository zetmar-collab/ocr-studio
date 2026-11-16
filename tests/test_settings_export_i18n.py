import json
import re

import pytest
from docx import Document

from src import settings as settings_module
from src.export_service import ExportService
from src.i18n import TRANSLATIONS, I18n
from src.settings import default_settings, load_settings, save_settings

# ---------------------------------------------------------------- ustawienia


def test_defaults_follow_system_language(monkeypatch):
    monkeypatch.setattr(settings_module, "detect_system_language", lambda: "en")
    english = default_settings()
    assert (english["language"], english["ocr_lang"], english["spell_lang"]) == ("en", "English", "English (en_US)")
    monkeypatch.setattr(settings_module, "detect_system_language", lambda: "pl")
    polish = default_settings()
    assert (polish["language"], polish["ocr_lang"], polish["spell_lang"]) == ("pl", "Polski", "Polski (pl_PL)")


def test_load_without_file_uses_defaults(sandbox):
    assert load_settings() == default_settings()


def test_roundtrip(sandbox):
    saved = dict(default_settings("en"), theme="Dark", ocr_lang="Deutsch", ocr_lang2="English", reflow=False)
    save_settings(saved)
    assert load_settings() == saved


def test_load_rejects_unknown_values_and_keeps_valid_ones(sandbox):
    sandbox.root.joinpath("settings.json").write_text(
        json.dumps({"theme": "Neon", "language": "en", "ocr_lang": "Klingon", "reflow": "tak", "mark_uncertain": False}),
        encoding="utf-8",
    )
    result = load_settings()
    assert result["theme"] == "System"  # nieznany motyw
    assert result["language"] == "en"  # poprawny zostaje
    assert result["ocr_lang"] == "English"  # nieznany jezyk -> domyslny dla jezyka interfejsu
    assert result["reflow"] is True  # nie-bool odrzucony
    assert result["mark_uncertain"] is False  # poprawny bool zostaje


@pytest.mark.parametrize("content", ["", "nie json", "[1, 2]", "null", '{"theme": '])
def test_load_survives_corrupt_file(sandbox, content):
    sandbox.root.joinpath("settings.json").write_text(content, encoding="utf-8")
    assert load_settings() == default_settings()


def test_second_ocr_language_cannot_equal_first(sandbox):
    sandbox.root.joinpath("settings.json").write_text(
        json.dumps({"ocr_lang": "Polski", "ocr_lang2": "Polski"}), encoding="utf-8"
    )
    assert load_settings()["ocr_lang2"] == ""


def test_save_is_atomic_and_leaves_no_temp_file(sandbox):
    save_settings(default_settings("pl"))
    assert sorted(p.name for p in sandbox.root.iterdir() if p.is_file()) == ["settings.json"]


def test_existing_0_2_x_settings_file_still_loads(sandbox):
    # format z wersji 0.2.1: tylko theme i language
    sandbox.root.joinpath("settings.json").write_text(json.dumps({"theme": "Dark", "language": "pl"}), encoding="utf-8")
    result = load_settings()
    assert (result["theme"], result["language"], result["ocr_lang"]) == ("Dark", "pl", "Polski")


# -------------------------------------------------------------------- eksport


def test_txt_export_strips_form_feed(tmp_path):
    target = tmp_path / "a.txt"
    ExportService.export_txt("linia\x0c\n", target)
    assert target.read_text(encoding="utf-8") == "linia\n"


def test_docx_export_survives_control_characters(tmp_path):
    # python-docx rzuca ValueError na znaki sterujace; Tesseract dopisuje \f na koncu strony
    target = tmp_path / "a.docx"
    ExportService.export_docx("pierwsza\x0c\ndruga\x00\nTrzecia\x0b", target)
    paragraphs = [p.text for p in Document(str(target)).paragraphs]
    assert paragraphs == ["pierwsza", "druga", "Trzecia"]


def test_docx_without_reflow_keeps_one_paragraph_per_line(tmp_path):
    target = tmp_path / "a.docx"
    ExportService.export_docx("linia 1\nlinia 2\n\nlinia 3", target, reflow=False)
    assert [p.text for p in Document(str(target)).paragraphs] == ["linia 1", "linia 2", "", "linia 3"]


def test_docx_with_reflow_builds_real_paragraphs(tmp_path):
    target = tmp_path / "a.docx"
    ExportService.export_docx("Pierwszy akapit\nw trzech\nliniach.\n\nDrugi akapit.", target, reflow=True)
    assert [p.text for p in Document(str(target)).paragraphs] == ["Pierwszy akapit w trzech liniach.", "Drugi akapit."]


def test_txt_with_reflow(tmp_path):
    target = tmp_path / "a.txt"
    ExportService.export_txt("a\nb\n\nc", target, reflow=True)
    assert target.read_text(encoding="utf-8") == "a b\n\nc\n"


def test_export_keeps_polish_characters(tmp_path):
    target = tmp_path / "a.txt"
    ExportService.export_txt("Zażółć gęślą jaźń", target)
    assert target.read_text(encoding="utf-8").strip() == "Zażółć gęślą jaźń"


# ----------------------------------------------------------------------- i18n


def placeholders(text):
    return set(re.findall(r"\{(\w+)\}", text))


def test_both_languages_have_identical_keys():
    pl, en = TRANSLATIONS["pl"], TRANSLATIONS["en"]
    assert set(pl) - set(en) == set(), "brak tlumaczen EN"
    assert set(en) - set(pl) == set(), "brak tlumaczen PL"


def test_placeholders_match_between_languages():
    for key, text in TRANSLATIONS["pl"].items():
        assert placeholders(text) == placeholders(TRANSLATIONS["en"][key]), f"rozne placeholdery w {key}"


def test_no_empty_translations():
    for language, table in TRANSLATIONS.items():
        empty = [key for key, text in table.items() if not text.strip()]
        assert not empty, f"{language}: puste tlumaczenia {empty}"


def test_every_translation_formats_with_its_placeholders():
    for table in TRANSLATIONS.values():
        for text in table.values():
            text.format(**dict.fromkeys(placeholders(text), "x"))


def test_unknown_key_returns_key_and_unknown_language_falls_back():
    assert I18n("en").t("no.such.key") == "no.such.key"
    assert I18n("xx").language == "pl"


def test_polish_ui_uses_diacritics():
    # w wersji 0.2.x wiele napisow bylo bez polskich znakow ("Zrodlo", "Jezyk")
    for key in ("sec.source", "sec.ocr_lang", "btn.install_ocr_lang", "msg.lang_missing"):
        assert re.search(r"[ąćęłńóśźż]", TRANSLATIONS["pl"][key], re.IGNORECASE), key


def test_every_key_used_in_code_exists():
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent / "src"
    used = set()
    for path in root.glob("*.py"):
        if path.name == "i18n.py":
            continue
        used |= set(re.findall(r"""\bt\(\s*["']([a-z_]+\.[a-z_.]+)["']""", path.read_text(encoding="utf-8")))
        used |= set(re.findall(r"""_text\([^,]+,\s*["']([a-z_]+\.[a-z_.]+)["']""", path.read_text(encoding="utf-8")))
        used |= set(re.findall(r"""_button\([^,]+,\s*["']([a-z_]+\.[a-z_.]+)["']""", path.read_text(encoding="utf-8")))
    assert len(used) > 40, f"test nie znajduje kluczy (znaleziono {len(used)}) - sprawdz wyrazenia regularne"
    missing = {key for key in used if key not in TRANSLATIONS["pl"]}
    assert not missing, f"klucze uzyte w kodzie, a nieistniejace w i18n: {sorted(missing)}"
