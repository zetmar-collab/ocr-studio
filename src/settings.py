from __future__ import annotations

import ctypes
import json
import os
import sys
from typing import Any

from .config import DATA_DIR, OCR_LANG_MAP, SPELL_LANG_MAP

SETTINGS_PATH = DATA_DIR / "settings.json"

THEME_MODES = ("System", "Light", "Dark")
UI_LANGUAGES = ("pl", "en")

_POLISH_LANG_ID = 0x15  # LANG_POLISH


def detect_system_language() -> str:
    """Jezyk interfejsu Windows -> 'pl' lub 'en' (domyslnie przy pierwszym uruchomieniu)."""
    if not sys.platform.startswith("win"):
        return "en"
    try:
        ui_language = ctypes.windll.kernel32.GetUserDefaultUILanguage()  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        return "en"
    return "pl" if (ui_language & 0x3FF) == _POLISH_LANG_ID else "en"


def default_settings(language: str | None = None) -> dict[str, Any]:
    language = language if language in UI_LANGUAGES else detect_system_language()
    polish = language == "pl"
    return {
        "theme": "System",
        "language": language,
        # jezyk OCR i slownik pisowni zgodne z jezykiem interfejsu
        "ocr_lang": "Polski" if polish else "English",
        "ocr_lang2": "",
        "spell_lang": "Polski (pl_PL)" if polish else "English (en_US)",
        "reflow": True,
        "mark_uncertain": True,
        "force_ocr": False,
    }


def _validate(settings: dict[str, Any]) -> dict[str, Any]:
    """Odrzuca wartosci spoza dozwolonych zbiorow (uszkodzony lub reczny plik)."""
    defaults = default_settings(settings.get("language") if settings.get("language") in UI_LANGUAGES else None)
    clean = dict(defaults)

    if settings.get("theme") in THEME_MODES:
        clean["theme"] = settings["theme"]
    if settings.get("language") in UI_LANGUAGES:
        clean["language"] = settings["language"]
    if settings.get("ocr_lang") in OCR_LANG_MAP:
        clean["ocr_lang"] = settings["ocr_lang"]
    if settings.get("ocr_lang2") in OCR_LANG_MAP and settings.get("ocr_lang2") != clean["ocr_lang"]:
        clean["ocr_lang2"] = settings["ocr_lang2"]
    if settings.get("spell_lang") in SPELL_LANG_MAP:
        clean["spell_lang"] = settings["spell_lang"]
    for key in ("reflow", "mark_uncertain", "force_ocr"):
        if isinstance(settings.get(key), bool):
            clean[key] = settings[key]
    return clean


def load_settings() -> dict[str, Any]:
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default_settings()
    if not isinstance(data, dict):
        return default_settings()
    return _validate(data)


def save_settings(settings: dict[str, Any]) -> None:
    """Zapis atomowy: przerwany zapis nie zostawia uszkodzonego pliku ustawien."""
    temporary = SETTINGS_PATH.with_name(SETTINGS_PATH.name + ".tmp")
    try:
        temporary.write_text(json.dumps(_validate(settings), ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporary, SETTINGS_PATH)
    except OSError:
        temporary.unlink(missing_ok=True)
