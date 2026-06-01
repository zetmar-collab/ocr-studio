from __future__ import annotations

from pathlib import Path

import requests

from .config import CUSTOM_DICTS_DIR, DICTS_DIR, OCR_LANG_MAP, TESSDATA_DIR

TESSDATA_BASE_URL = "https://github.com/tesseract-ocr/tessdata_best/raw/main"
HUNSPELL_BASE_URL = "https://raw.githubusercontent.com/wooorm/dictionaries/main/dictionaries"


class LanguageManager:
    def list_installed_ocr(self) -> list[str]:
        installed = []
        for trained in TESSDATA_DIR.glob("*.traineddata"):
            installed.append(trained.stem)
        return sorted(installed)

    def install_ocr_language(self, lang_code: str) -> Path:
        target = TESSDATA_DIR / f"{lang_code}.traineddata"
        if target.exists():
            return target
        url = f"{TESSDATA_BASE_URL}/{lang_code}.traineddata"
        response = requests.get(url, timeout=90)
        response.raise_for_status()
        target.write_bytes(response.content)
        return target

    def available_ocr_choices(self) -> dict[str, str]:
        return OCR_LANG_MAP.copy()

    def install_spell_dictionary(self, dict_code: str) -> tuple[Path, Path]:
        lang_dir = DICTS_DIR / dict_code
        lang_dir.mkdir(parents=True, exist_ok=True)

        aff_path = lang_dir / f"{dict_code}.aff"
        dic_path = lang_dir / f"{dict_code}.dic"

        repo_code = self._resolve_spell_repo_code(dict_code)

        if not aff_path.exists():
            aff_url = f"{HUNSPELL_BASE_URL}/{repo_code}/index.aff"
            response = requests.get(aff_url, timeout=90)
            response.raise_for_status()
            aff_path.write_bytes(response.content)

        if not dic_path.exists():
            dic_url = f"{HUNSPELL_BASE_URL}/{repo_code}/index.dic"
            response = requests.get(dic_url, timeout=90)
            response.raise_for_status()
            dic_path.write_bytes(response.content)

        custom_path = CUSTOM_DICTS_DIR / f"{dict_code}.txt"
        if not custom_path.exists():
            custom_path.write_text("", encoding="utf-8")

        return aff_path, dic_path

    def _resolve_spell_repo_code(self, dict_code: str) -> str:
        candidates: list[str] = []
        lower = dict_code.lower()
        candidates.extend([dict_code, lower, lower.replace("_", "-")])
        if "_" in dict_code:
            base = dict_code.split("_", 1)[0]
            candidates.extend([base, base.lower()])
        if "-" in dict_code:
            base = dict_code.split("-", 1)[0]
            candidates.extend([base, base.lower()])

        seen: set[str] = set()
        ordered_candidates = [c for c in candidates if c and not (c in seen or seen.add(c))]

        for candidate in ordered_candidates:
            test_url = f"{HUNSPELL_BASE_URL}/{candidate}/index.aff"
            response = requests.get(test_url, timeout=30)
            if response.ok:
                return candidate

        raise RuntimeError(
            f"Brak slownika dla kodu '{dict_code}'. Sprobuj innego jezyka lub sprawdz polaczenie internetowe."
        )

    def list_installed_spell(self) -> list[str]:
        installed = []
        for folder in DICTS_DIR.iterdir():
            if not folder.is_dir():
                continue
            code = folder.name
            aff = folder / f"{code}.aff"
            dic = folder / f"{code}.dic"
            if aff.exists() and dic.exists():
                installed.append(code)
        return sorted(installed)
