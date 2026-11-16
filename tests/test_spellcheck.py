import re

import pytest

from src.spellcheck_service import (
    WORD_RE,
    SpellcheckService,
    SpellDictionaryMissingError,
    add_custom_word,
)


@pytest.fixture(scope="module")
def english():
    return SpellcheckService("en_US")


@pytest.fixture
def clean_custom(sandbox):
    return sandbox.custom


def words(text):
    return WORD_RE.findall(text)


def test_word_regex_handles_hyphens_apostrophes_and_polish_letters():
    assert words("bio-medical-test don't Zażółć gęślą jaźń") == ["bio-medical-test", "don't", "Zażółć", "gęślą", "jaźń"]
    assert words("Żółć’s") == ["Żółć’s"]  # typograficzny apostrof
    assert words("abc123def 42 _x_") == ["abc", "def", "x"]


def test_word_regex_does_not_split_on_cyrillic():
    assert words("słowo привет word") == ["słowo", "word"]


def test_missing_dictionary_raises_typed_error(sandbox):
    with pytest.raises(SpellDictionaryMissingError) as info:
        SpellcheckService("de_DE")
    assert info.value.dict_code == "de_DE"


def test_find_errors_reports_exact_positions(english, clean_custom):
    text = "Ths is a tset of the sistem."
    errors = english.find_errors(text)
    assert [(e.word, text[e.start : e.end]) for e in errors] == [("Ths", "Ths"), ("tset", "tset"), ("sistem", "sistem")]


def test_correct_text_has_no_errors(english, clean_custom):
    assert english.find_errors("This is a test of the system. It's fine, don't worry.") == []


def test_single_letters_are_not_flagged(english, clean_custom):
    assert english.find_errors("a b c x y z") == []


def test_custom_words_are_case_insensitive_and_persistent(clean_custom):
    assert add_custom_word("en_US", "Zettel") is True
    assert add_custom_word("en_US", "zettel") is False  # duplikat niezaleznie od wielkosci liter
    service = SpellcheckService("en_US")
    assert service.find_errors("zettel ZETTEL Zettel") == []
    assert (clean_custom / "en_US.txt").read_text(encoding="utf-8").splitlines() == ["Zettel"]


def test_ignored_words_are_skipped(english, clean_custom):
    assert english.find_errors("tset tset", ignored={"tset"}) == []


def test_add_custom_word_ignores_blank():
    assert add_custom_word("en_US", "   ") is False


def test_suggestions_are_cached_per_dictionary_and_mode(english, monkeypatch):
    calls = []
    real = english.dictionary.suggest

    def counting(word):
        calls.append(word)
        return real(word)

    monkeypatch.setattr(english.dictionary, "suggest", counting)
    first = english.suggest("systemm", fast=True)
    second = english.suggest("systemm", fast=True)
    assert first == second and "system" in first
    assert calls == ["systemm"], "drugie wywolanie powinno wyjsc z cache"
    english.suggest("systemm", fast=False)  # inny tryb = osobny wpis
    assert len(calls) == 2
    assert english.dictionary.aff.MAXNGRAMSUGS == 4  # tryb szybki nie zostawia zmienionych ustawien


def test_fast_mode_restores_ngram_setting_even_on_error(english, monkeypatch):
    original = english.dictionary.aff.MAXNGRAMSUGS

    def boom(_word):
        raise RuntimeError("awaria")

    monkeypatch.setattr(english.dictionary, "suggest", boom)
    with pytest.raises(RuntimeError):
        english.suggest("niecache", fast=True)
    assert english.dictionary.aff.MAXNGRAMSUGS == original


def test_apply_corrections_replaces_from_the_end_without_shifting():
    text = "Ths is a tset"
    errors = [
        {"word": "Ths", "start": 0, "end": 3, "suggestions": ["This"]},
        {"word": "tset", "start": 9, "end": 13, "suggestions": ["test"]},
    ]
    assert SpellcheckService.apply_corrections(None, text, errors) == "This is a test"


def test_apply_corrections_does_not_corrupt_text_edited_after_check():
    # regresja z audytu: offsety z chwili sprawdzenia, tekst juz zmieniony przez uzytkownika
    original = "Ths is a tset of the sistem."
    errors = [
        {"word": "Ths", "start": 0, "end": 3, "suggestions": ["This"]},
        {"word": "tset", "start": 9, "end": 13, "suggestions": ["test"]},
        {"word": "sistem", "start": 21, "end": 27, "suggestions": ["system"]},
    ]
    edited = "NOWY AKAPIT. " + original
    result = SpellcheckService.apply_corrections(None, edited, errors)
    assert result == edited  # zadne przesuniete zakresy nie pasuja do slow -> brak zamian
    assert "NOWY AKAPIT" in result


def test_apply_corrections_skips_errors_without_suggestions():
    errors = [{"word": "xyz", "start": 0, "end": 3, "suggestions": []}]
    assert SpellcheckService.apply_corrections(None, "xyz abc", errors) == "xyz abc"


def test_finding_errors_in_long_text_is_fast(english, clean_custom):
    import time

    text = ("The quick brown fox jumps over the lazy dog and the sistem works. " * 400).strip()
    start = time.perf_counter()
    errors = english.find_errors(text)
    elapsed = time.perf_counter() - start
    assert len(errors) == 400
    assert elapsed < 2.0, f"wykrywanie bledow zbyt wolne: {elapsed:.2f}s"


def test_polish_dictionary_recognises_diacritics(sandbox):
    service = SpellcheckService("pl_PL")
    assert service.find_errors("Zażółć gęślą jaźń, łódź i świnia.") == []
    assert [e.word for e in service.find_errors("To jest dokumnet")] == ["dokumnet"]


def test_dictionary_is_loaded_once_per_process(english):
    from src import spellcheck_service

    assert spellcheck_service._load_dictionary("en_US") is spellcheck_service._load_dictionary("en_US")
    assert SpellcheckService("en_US").dictionary is english.dictionary


def test_word_positions_survive_regex_on_multiline_text(english, clean_custom):
    text = "first line\nsecond tset\n\nthird sistem"
    errors = english.find_errors(text)
    assert [(e.word, re.sub(r"\n", "|", text[e.start : e.end])) for e in errors] == [("tset", "tset"), ("sistem", "sistem")]
