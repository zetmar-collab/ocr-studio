from __future__ import annotations

import itertools
import re
import threading
from dataclasses import dataclass

from spylls.hunspell import Dictionary

from .config import CUSTOM_DICTS_DIR
from .language_manager import LanguageManager

_LETTERS = "A-Za-zÀ-ÖØ-öø-ɏ"
# slowo, opcjonalnie z lacznikami i apostrofami wewnatrz (np. "bio-medyczny", "don't")
WORD_RE = re.compile(rf"[{_LETTERS}]+(?:['’\-][{_LETTERS}]+)*")

_dictionary_cache: dict[str, Dictionary] = {}
# podpowiedzi kosztuja sekundy, wiec cache zyje tak dlugo jak proces: (slownik, slowo, tryb)
_suggestion_cache: dict[tuple[str, str, bool], list[str]] = {}
_dictionary_lock = threading.RLock()


def add_custom_word(dict_code: str, word: str) -> bool:
    """Dopisuje slowo do wlasnego slownika bez wczytywania slownika Hunspell. True, gdy dodano."""
    word = word.strip()
    if not word:
        return False
    path = CUSTOM_DICTS_DIR / f"{dict_code}.txt"
    existing: set[str] = set()
    if path.exists():
        try:
            existing = {line.strip().lower() for line in path.read_text(encoding="utf-8").splitlines()}
        except OSError:
            existing = set()
    if word.lower() in existing:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{word}" + chr(10))
    return True


class SpellDictionaryMissingError(FileNotFoundError):
    """Slownik Hunspell dla `dict_code` nie jest zainstalowany ani wbudowany."""

    def __init__(self, dict_code: str) -> None:
        self.dict_code = dict_code
        super().__init__(dict_code)


@dataclass(frozen=True)
class SpellError:
    word: str
    start: int
    end: int


def _load_dictionary(dict_code: str) -> Dictionary:
    """Wczytuje slownik raz na proces (polski trwa kilka sekund) i trzyma w pamieci."""
    with _dictionary_lock:
        cached = _dictionary_cache.get(dict_code)
        if cached is not None:
            return cached
        stem = LanguageManager().find_spell_dictionary(dict_code)
        if stem is None:
            raise SpellDictionaryMissingError(dict_code)
        dictionary = Dictionary.from_files(str(stem))
        _dictionary_cache[dict_code] = dictionary
        return dictionary


def _normalize(word: str) -> str:
    return word.replace("’", "'")


class SpellcheckService:
    def __init__(self, dict_code: str) -> None:
        self.dict_code = dict_code
        self.dictionary = _load_dictionary(dict_code)
        self.custom_words = self._load_custom_words(dict_code)

    def _load_custom_words(self, dict_code: str) -> set[str]:
        path = CUSTOM_DICTS_DIR / f"{dict_code}.txt"
        if not path.exists():
            return set()
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return set()
        return {line.strip().lower() for line in lines if line.strip()}

    def add_to_custom_dictionary(self, word: str) -> None:
        word = word.strip()
        if not word or word.lower() in self.custom_words:
            return
        self.custom_words.add(word.lower())
        self._custom_path.parent.mkdir(parents=True, exist_ok=True)
        with self._custom_path.open("a", encoding="utf-8") as handle:
            handle.write(f"{word}\n")

    def is_correct(self, word: str) -> bool:
        normalized = _normalize(word)
        if normalized.lower() in self.custom_words:
            return True
        with _dictionary_lock:
            return bool(self.dictionary.lookup(normalized))

    def find_errors(self, text: str, ignored: frozenset[str] | set[str] = frozenset()) -> list[SpellError]:
        """Znajduje bledne slowa. Szybkie: nie liczy podpowiedzi (to kosztuje sekundy)."""
        errors: list[SpellError] = []
        checked: dict[str, bool] = {}
        for match in WORD_RE.finditer(text):
            word = match.group(0)
            key = word.lower()
            if key in ignored:
                continue
            if key not in checked:
                checked[key] = self.is_correct(word) if len(word) > 1 else True
            if not checked[key]:
                errors.append(SpellError(word, match.start(), match.end()))
        return errors

    def suggest(self, word: str, limit: int = 5, *, fast: bool = False) -> list[str]:
        """Podpowiedzi dla slowa (w spylls kosztuja ~1-10 s na slowo - wolac z watku roboczego).

        `fast=True` pomija wyszukiwanie n-gramowe: szybsze i ostrozniejsze, dobre
        do automatycznej zamiany pierwsza podpowiedzia.
        """
        key = (self.dict_code, word, fast)
        if key not in _suggestion_cache:
            with _dictionary_lock:
                aff = self.dictionary.aff
                original = aff.MAXNGRAMSUGS
                if fast:
                    aff.MAXNGRAMSUGS = 0
                try:
                    found = list(itertools.islice(self.dictionary.suggest(_normalize(word)), limit))
                finally:
                    aff.MAXNGRAMSUGS = original
            _suggestion_cache[key] = found
        return _suggestion_cache[key][:limit]

    def prewarm(self) -> None:
        """Wczytuje slownik do pamieci (cache procesu); wywolywane w tle przy starcie."""
        self.is_correct("test")

    # ---------- zgodnosc wsteczna ----------

    def check_text(self, text: str) -> list[dict[str, object]]:
        return [
            {"word": e.word, "start": e.start, "end": e.end, "suggestions": self.suggest(e.word)}
            for e in self.find_errors(text)
        ]

    def apply_corrections(self, text: str, errors: list[dict[str, object]]) -> str:
        """Podmienia bledne slowa pierwsza podpowiedzia, od konca (indeksy sie nie przesuwaja).

        Zamienia tylko tam, gdzie tekst pod zakresem nadal jest tym slowem -
        przestarzale przesuniecia (po edycji tekstu) nie moga uszkodzic dokumentu.
        """
        corrected = text
        for error in sorted(errors, key=lambda item: int(item["start"]), reverse=True):  # type: ignore[arg-type]
            suggestions = error.get("suggestions") or []
            if not suggestions:
                continue
            start, end = int(error["start"]), int(error["end"])  # type: ignore[arg-type]
            if corrected[start:end] != error["word"]:
                continue
            corrected = corrected[:start] + str(suggestions[0]) + corrected[end:]
        return corrected
