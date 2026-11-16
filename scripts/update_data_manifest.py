"""Generuje src/downloads_manifest.py: przypięte adresy i sumy SHA-256 plików,
które aplikacja pobiera na zadanie uzytkownika (jezyki OCR, slowniki pisowni).

Dlaczego: pobieranie z ruchomej galezi `main` bez weryfikacji pozwalaloby
przejetemu upstreamowi dostarczyc dowolny plik (traineddata jest parsowane
przez natywny Tesseract), a przerwane pobranie zostawialoby uszkodzony plik
uznawany pozniej za zainstalowany.

Uzycie (po zmianie SHA ponizej lub list jezykow w src/config.py):
    python scripts/update_data_manifest.py
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import OCR_LANG_MAP, SPELL_LANG_MAP  # noqa: E402

TESSDATA_REPO = "tesseract-ocr/tessdata_best"
TESSDATA_SHA = "e12c65a915945e4c28e237a9b52bc4a8f39a0cec"
DICT_REPO = "wooorm/dictionaries"
DICT_SHA = "8cfea406b505e4d7df52d5a19bce525df98c54ab"

# kod slownika Hunspell -> katalog w repozytorium wooorm/dictionaries
SPELL_REPO_CODES = {
    "pl_PL": "pl",
    "en_US": "en",
    "de_DE": "de",
    "fr_FR": "fr",
    "es_ES": "es",
    "it_IT": "it",
}

OUTPUT = PROJECT_ROOT / "src" / "downloads_manifest.py"


def _fetch(url: str) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with requests.get(url, stream=True, timeout=180) as response:
        response.raise_for_status()
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def main() -> int:
    missing = set(SPELL_LANG_MAP.values()) - set(SPELL_REPO_CODES)
    if missing:
        raise SystemExit(f"Brak mapowania kodu slownika w SPELL_REPO_CODES: {sorted(missing)}")

    lines = [
        '"""Wygenerowane przez scripts/update_data_manifest.py - nie edytuj recznie."""',
        "",
        "from __future__ import annotations",
        "",
        f'TESSDATA_BASE_URL = "https://github.com/{TESSDATA_REPO}/raw/{TESSDATA_SHA}"',
        f'DICT_BASE_URL = "https://raw.githubusercontent.com/{DICT_REPO}/{DICT_SHA}/dictionaries"',
        "",
        "# kod jezyka OCR -> (sha256, rozmiar w bajtach)",
        "TESSDATA_FILES: dict[str, tuple[str, int]] = {",
    ]
    for code in sorted(OCR_LANG_MAP.values()):
        sha, size = _fetch(f"https://github.com/{TESSDATA_REPO}/raw/{TESSDATA_SHA}/{code}.traineddata")
        print(f"traineddata {code}: {size / 1024 / 1024:5.1f} MB  {sha[:12]}")
        lines.append(f'    "{code}": ("{sha}", {size}),')
    lines += ["}", "", "# kod slownika -> katalog w repozytorium zrodlowym", "SPELL_REPO_CODES: dict[str, str] = {"]
    for dict_code, repo_code in sorted(SPELL_REPO_CODES.items()):
        lines.append(f'    "{dict_code}": "{repo_code}",')
    lines += ["}", "", "# (kod slownika, rozszerzenie) -> (sha256, rozmiar)", "DICT_FILES: dict[tuple[str, str], tuple[str, int]] = {"]
    for dict_code, repo_code in sorted(SPELL_REPO_CODES.items()):
        for ext in ("aff", "dic"):
            sha, size = _fetch(f"https://raw.githubusercontent.com/{DICT_REPO}/{DICT_SHA}/dictionaries/{repo_code}/index.{ext}")
            print(f"slownik {dict_code}.{ext}: {size / 1024:7.0f} KB  {sha[:12]}")
            lines.append(f'    ("{dict_code}", "{ext}"): ("{sha}", {size}),')
    lines += ["}", ""]

    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nZapisano: {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
