"""Dolacza do pakietu slowniki pisowni (polski i angielski), zeby sprawdzanie
pisowni dzialalo od razu po instalacji - bez pobierania.

Pliki pochodza z przypietego commita wooorm/dictionaries, sa weryfikowane
sumami SHA-256 z src/downloads_manifest.py i trafiaja do vendor/dictionaries/
razem z tekstem licencji kazdego slownika.

Uzycie:
    python scripts/vendor_dictionaries.py
"""

from __future__ import annotations

import hashlib
import shutil
import sys
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.downloads_manifest import DICT_BASE_URL, DICT_FILES, SPELL_REPO_CODES  # noqa: E402

VENDOR_DIR = PROJECT_ROOT / "vendor" / "dictionaries"
BUNDLED = ["pl_PL", "en_US"]


def main() -> int:
    if VENDOR_DIR.exists():
        shutil.rmtree(VENDOR_DIR)

    for code in BUNDLED:
        repo_code = SPELL_REPO_CODES[code]
        target_dir = VENDOR_DIR / code
        target_dir.mkdir(parents=True)

        for ext in ("aff", "dic"):
            expected_sha, expected_size = DICT_FILES[(code, ext)]
            response = requests.get(f"{DICT_BASE_URL}/{repo_code}/index.{ext}", timeout=120)
            response.raise_for_status()
            data = response.content
            if len(data) != expected_size or hashlib.sha256(data).hexdigest() != expected_sha:
                raise SystemExit(f"Suma kontrolna {code}.{ext} nie zgadza sie z manifestem.")
            (target_dir / f"{code}.{ext}").write_bytes(data)

        response = requests.get(f"{DICT_BASE_URL}/{repo_code}/license", timeout=120)
        response.raise_for_status()
        (target_dir / f"LICENSE-{code}.txt").write_bytes(response.content)
        print(f"OK: {code} (aff + dic + licencja)")

    total = sum(f.stat().st_size for f in VENDOR_DIR.rglob("*") if f.is_file())
    print(f"\nGOTOWE: {VENDOR_DIR} ({total / 1024 / 1024:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
