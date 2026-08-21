from __future__ import annotations

import re
from pathlib import Path

from spylls.hunspell import Dictionary

from .config import CUSTOM_DICTS_DIR, DICTS_DIR

WORD_RE = re.compile(r"[A-Za-zÀ-ÿĄąĆćĘęŁłŃńÓóŚśŹźŻż]+(?:['-][A-Za-zÀ-ÿĄąĆćĘęŁłŃńÓóŚśŹźŻż]+)?")


class SpellDictionaryMissingError(FileNotFoundError):
    """Raised when the Hunspell dictionary for `dict_code` is not installed."""

    def __init__(self, dict_code: str) -> None:
        self.dict_code = dict_code
        super().__init__(dict_code)


class SpellcheckService:
    def __init__(self, dict_code: str) -> None:
        self.dict_code = dict_code
        self.dictionary = self._load_dictionary(dict_code)
        self.custom_words = self._load_custom_words(dict_code)

    def _load_dictionary(self, dict_code: str) -> Dictionary:
        aff = DICTS_DIR / dict_code / f"{dict_code}.aff"
        dic = DICTS_DIR / dict_code / f"{dict_code}.dic"
        if not aff.exists() or not dic.exists():
            raise SpellDictionaryMissingError(dict_code)
        # spylls expects a dictionary stem path, e.g. ".../pl_PL"
        stem_path = DICTS_DIR / dict_code / dict_code
        return Dictionary.from_files(str(stem_path))

    def _load_custom_words(self, dict_code: str) -> set[str]:
        custom = CUSTOM_DICTS_DIR / f"{dict_code}.txt"
        if not custom.exists():
            custom.write_text("", encoding="utf-8")
            return set()
        return {line.strip() for line in custom.read_text(encoding="utf-8").splitlines() if line.strip()}

    def add_to_custom_dictionary(self, word: str) -> None:
        word = word.strip()
        if not word:
            return
        if word in self.custom_words:
            return
        self.custom_words.add(word)
        custom = CUSTOM_DICTS_DIR / f"{self.dict_code}.txt"
        existing = custom.read_text(encoding="utf-8")
        custom.write_text(existing + ("" if existing.endswith("\n") or existing == "" else "\n") + f"{word}\n", encoding="utf-8")

    def check_text(self, text: str) -> list[dict[str, object]]:
        errors: list[dict[str, object]] = []
        for match in WORD_RE.finditer(text):
            word = match.group(0)
            if word in self.custom_words:
                continue
            if self.dictionary.lookup(word):
                continue
            suggestions = list(self.dictionary.suggest(word))[:5]
            errors.append(
                {
                    "word": word,
                    "start": match.start(),
                    "end": match.end(),
                    "suggestions": suggestions,
                }
            )
        return errors

    def apply_corrections(self, text: str, errors: list[dict[str, object]]) -> str:
        """Podmienia bledne slowa pierwsza sugestia (od konca, bez przesuwania indeksow)."""
        corrected = text
        for error in sorted(errors, key=lambda item: int(item["start"]), reverse=True):
            suggestions = error.get("suggestions") or []
            if not suggestions:
                continue
            start = int(error["start"])
            end = int(error["end"])
            corrected = corrected[:start] + str(suggestions[0]) + corrected[end:]
        return corrected
