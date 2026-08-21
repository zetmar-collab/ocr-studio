from __future__ import annotations

import json

from .config import DATA_DIR

SETTINGS_PATH = DATA_DIR / "settings.json"

DEFAULT_SETTINGS: dict[str, str] = {
    "theme": "System",
    "language": "pl",
}


def load_settings() -> dict[str, str]:
    settings = DEFAULT_SETTINGS.copy()
    if not SETTINGS_PATH.exists():
        return settings
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return settings
    if isinstance(data, dict):
        for key in DEFAULT_SETTINGS:
            value = data.get(key)
            if isinstance(value, str) and value:
                settings[key] = value
    return settings


def save_settings(settings: dict[str, str]) -> None:
    try:
        SETTINGS_PATH.write_text(
            json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError:
        pass
