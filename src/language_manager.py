from __future__ import annotations

import hashlib
import os
import threading
from collections.abc import Callable
from pathlib import Path

import requests

from . import downloads_manifest as manifest
from .config import (
    BUNDLED_DICTS_DIR,
    BUNDLED_TESSDATA_DIR,
    CUSTOM_DICTS_DIR,
    DICTS_DIR,
    OCR_LANG_MAP,
    TESSDATA_DIR,
)
from .jobs import JobCancelled

DownloadProgress = Callable[[int, int, str], None]
_CHUNK = 256 * 1024


class DownloadError(RuntimeError):
    """Pobieranie nie powiodlo sie (siec, serwer, niezgodna suma kontrolna)."""

    def __init__(self, what: str, details: str) -> None:
        self.what = what
        self.details = details
        super().__init__(f"{what}: {details}")


def _atomic_download(
    url: str,
    target: Path,
    expected_sha256: str,
    expected_size: int,
    *,
    label: str,
    progress: DownloadProgress | None = None,
    cancel: threading.Event | None = None,
) -> Path:
    """Pobiera plik do `.part`, sprawdza rozmiar i SHA-256 i dopiero wtedy podmienia cel.

    Dzieki temu przerwane lub uszkodzone pobranie nigdy nie zostawia pliku,
    ktory aplikacja uznalaby za zainstalowany.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".part")
    digest = hashlib.sha256()
    received = 0
    try:
        with requests.get(url, stream=True, timeout=(10, 60)) as response:
            response.raise_for_status()
            with partial.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=_CHUNK):
                    if cancel is not None and cancel.is_set():
                        raise JobCancelled()
                    if not chunk:
                        continue
                    handle.write(chunk)
                    digest.update(chunk)
                    received += len(chunk)
                    if progress:
                        progress(received, expected_size, label)
    except JobCancelled:
        partial.unlink(missing_ok=True)
        raise
    except requests.RequestException as exc:
        partial.unlink(missing_ok=True)
        raise DownloadError(label, str(exc)) from exc
    except OSError as exc:
        partial.unlink(missing_ok=True)
        raise DownloadError(label, str(exc)) from exc

    if received != expected_size or digest.hexdigest() != expected_sha256:
        partial.unlink(missing_ok=True)
        raise DownloadError(label, "pobrany plik jest uszkodzony lub zmieniony (niezgodna suma kontrolna)")

    os.replace(partial, target)
    return target


class LanguageManager:
    # ---------- jezyki OCR ----------

    @staticmethod
    def _ocr_candidates(lang_code: str) -> list[Path]:
        return [TESSDATA_DIR / f"{lang_code}.traineddata", BUNDLED_TESSDATA_DIR / f"{lang_code}.traineddata"]

    def is_ocr_language_available(self, lang_code: str) -> bool:
        return any(path.exists() for path in self._ocr_candidates(lang_code))

    def list_installed_ocr(self) -> list[str]:
        """Jezyki dostepne od razu: wbudowane w pakiet oraz doinstalowane."""
        installed = set()
        for directory in (TESSDATA_DIR, BUNDLED_TESSDATA_DIR):
            if directory.exists():
                installed.update(path.name.removesuffix(".traineddata") for path in directory.glob("*.traineddata"))
        return sorted(installed)

    def install_ocr_language(
        self,
        lang_code: str,
        *,
        progress: DownloadProgress | None = None,
        cancel: threading.Event | None = None,
    ) -> Path:
        # Jezyk wbudowany w pakiet lub juz pobrany: zadnego dostepu do sieci.
        for candidate in self._ocr_candidates(lang_code):
            if candidate.exists():
                return candidate

        if lang_code not in manifest.TESSDATA_FILES:
            raise DownloadError(lang_code, "nieznany jezyk OCR")
        sha256, size = manifest.TESSDATA_FILES[lang_code]
        return _atomic_download(
            f"{manifest.TESSDATA_BASE_URL}/{lang_code}.traineddata",
            TESSDATA_DIR / f"{lang_code}.traineddata",
            sha256,
            size,
            label=f"{lang_code}.traineddata",
            progress=progress,
            cancel=cancel,
        )

    def available_ocr_choices(self) -> dict[str, str]:
        return OCR_LANG_MAP.copy()

    # ---------- slowniki pisowni ----------

    @staticmethod
    def _dict_dirs(dict_code: str) -> list[Path]:
        return [DICTS_DIR / dict_code, BUNDLED_DICTS_DIR / dict_code]

    def find_spell_dictionary(self, dict_code: str) -> Path | None:
        """Zwraca sciezke bazowa (bez rozszerzenia) slownika lub None."""
        for directory in self._dict_dirs(dict_code):
            if (directory / f"{dict_code}.aff").exists() and (directory / f"{dict_code}.dic").exists():
                return directory / dict_code
        return None

    def is_spell_dictionary_available(self, dict_code: str) -> bool:
        return self.find_spell_dictionary(dict_code) is not None

    def install_spell_dictionary(
        self,
        dict_code: str,
        *,
        progress: DownloadProgress | None = None,
        cancel: threading.Event | None = None,
    ) -> tuple[Path, Path]:
        existing = self.find_spell_dictionary(dict_code)
        if existing is not None:
            return existing.with_suffix(".aff"), existing.with_suffix(".dic")

        repo_code = manifest.SPELL_REPO_CODES.get(dict_code)
        if repo_code is None:
            raise DownloadError(dict_code, "nieznany slownik")

        lang_dir = DICTS_DIR / dict_code
        paths: dict[str, Path] = {}
        for ext in ("aff", "dic"):
            sha256, size = manifest.DICT_FILES[(dict_code, ext)]
            paths[ext] = _atomic_download(
                f"{manifest.DICT_BASE_URL}/{repo_code}/index.{ext}",
                lang_dir / f"{dict_code}.{ext}",
                sha256,
                size,
                label=f"{dict_code}.{ext}",
                progress=progress,
                cancel=cancel,
            )

        custom_path = CUSTOM_DICTS_DIR / f"{dict_code}.txt"
        if not custom_path.exists():
            custom_path.parent.mkdir(parents=True, exist_ok=True)
            custom_path.write_text("", encoding="utf-8")
        return paths["aff"], paths["dic"]

    def list_installed_spell(self) -> list[str]:
        installed = set()
        for root in (DICTS_DIR, BUNDLED_DICTS_DIR):
            if not root.exists():
                continue
            for folder in root.iterdir():
                if folder.is_dir() and self.find_spell_dictionary(folder.name) is not None:
                    installed.add(folder.name)
        return sorted(installed)
