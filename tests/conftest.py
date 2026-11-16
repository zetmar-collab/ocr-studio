"""Wspolne narzedzia testow.

Testy nie moga dotykac prawdziwych danych uzytkownika (jezyki, ustawienia,
wlasne slowniki), wiec fixture `sandbox` przekierowuje wszystkie katalogi danych
do katalogu tymczasowego. Silnik Tesseract i slowniki pochodza z vendor/.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import config  # noqa: E402

ENGINE_AVAILABLE = config.BUNDLED_TESSERACT_EXE.exists()


def _tk_available() -> bool:
    try:
        import tkinter

        root = tkinter.Tk()
        root.destroy()
        return True
    except Exception:  # noqa: BLE001
        return False


TK_AVAILABLE = _tk_available()


def pytest_collection_modifyitems(config, items):  # noqa: ARG001
    skip_engine = pytest.mark.skip(reason="brak vendor/tesseract - uruchom scripts/vendor_tesseract.py")
    skip_gui = pytest.mark.skip(reason="brak dostepnego Tk/ekranu")
    for item in items:
        if "engine" in item.keywords and not ENGINE_AVAILABLE:
            item.add_marker(skip_engine)
        if "gui" in item.keywords and not (TK_AVAILABLE and ENGINE_AVAILABLE):
            item.add_marker(skip_gui)


@pytest.fixture
def sandbox(monkeypatch, tmp_path):
    """Izoluje katalogi danych aplikacji w katalogu tymczasowym."""
    data = tmp_path / "data"
    dirs = {
        "tessdata": data / "tessdata",
        "dicts": data / "dictionaries",
        "custom": data / "custom_dictionaries",
    }
    for directory in dirs.values():
        directory.mkdir(parents=True)

    for module, name, value in (
        ("src.ocr_service", "TESSDATA_DIR", dirs["tessdata"]),
        ("src.language_manager", "TESSDATA_DIR", dirs["tessdata"]),
        ("src.language_manager", "DICTS_DIR", dirs["dicts"]),
        ("src.language_manager", "CUSTOM_DICTS_DIR", dirs["custom"]),
        ("src.spellcheck_service", "CUSTOM_DICTS_DIR", dirs["custom"]),
        ("src.settings", "SETTINGS_PATH", data / "settings.json"),
    ):
        monkeypatch.setattr(f"{module}.{name}", value)
    return type("Sandbox", (), {"root": data, **dirs})


def _font(size: int):
    for name in ("arial.ttf", "segoeui.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


@pytest.fixture
def make_image(tmp_path):
    """Fabryka obrazow z tekstem: make_image(["linia 1", "linia 2"], name="a.png")."""

    def factory(lines, name="sample.png", size=(1500, None), font_size=48, **save_kwargs):
        height = size[1] or 120 + 80 * len(lines)
        image = Image.new("RGB", (size[0], height), "white")
        draw = ImageDraw.Draw(image)
        for index, line in enumerate(lines):
            draw.text((60, 50 + index * 80), line, fill="black", font=_font(font_size))
        path = tmp_path / name
        image.save(path, dpi=(200, 200), **save_kwargs)
        return path

    return factory
