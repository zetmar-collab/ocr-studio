"""Sciezki bezpieczne dla Tesseract.

tesseract.exe dostaje argumenty w stronie kodowej ANSI systemu. Znaki spoza niej
(np. cyrylica w nazwie konta na polskim Windows) sa zamieniane na '?', wiec plik
nie zostaje otwarty ("Error opening data file"). Polskie litery sa bezpieczne
tylko dlatego, ze wchodza w cp1250.
"""

from __future__ import annotations

import ctypes
import hashlib
import os
import shutil
import sys
from pathlib import Path


class UnsafePathError(RuntimeError):
    """Nie udalo sie wskazac Tesseract katalogu o ASCII-bezpiecznej sciezce."""

    def __init__(self, path: Path) -> None:
        self.path = path
        super().__init__(str(path))


def is_ansi_safe(path: str | os.PathLike[str]) -> bool:
    """Czy sciezka przetrwa konwersje do ANSI (i z powrotem) bez zmian."""
    text = str(path)
    if not sys.platform.startswith("win"):
        return True
    try:
        return text.encode("mbcs").decode("mbcs") == text
    except UnicodeError:
        return False


def short_path(path: Path) -> Path | None:
    """Zwraca skrocona nazwe 8.3 (zwykle ASCII) lub None, gdy niedostepna."""
    if not sys.platform.startswith("win"):
        return None
    try:
        buffer = ctypes.create_unicode_buffer(32768)
        length = ctypes.windll.kernel32.GetShortPathNameW(str(path), buffer, len(buffer))  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        return None
    if not length:
        return None
    return Path(buffer.value)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _current_user_sid():
    import win32api
    import win32con
    import win32security

    token = win32security.OpenProcessToken(win32api.GetCurrentProcess(), win32con.TOKEN_QUERY)
    return win32security.GetTokenInformation(token, win32security.TokenUser)[0]


def _owned_by_current_user(path: Path) -> bool:
    """Czy wlascicielem `path` jest biezacy uzytkownik (lub jego domyslny wlasciciel obiektow)."""
    import win32api
    import win32con
    import win32security

    descriptor = win32security.GetFileSecurity(str(path), win32security.OWNER_SECURITY_INFORMATION)
    owner = win32security.ConvertSidToStringSid(descriptor.GetSecurityDescriptorOwner())
    token = win32security.OpenProcessToken(win32api.GetCurrentProcess(), win32con.TOKEN_QUERY)
    # Obiekty PySID nie maja hasha opartego na wartosci - porownujemy SID-y jako napisy.
    allowed = {
        win32security.ConvertSidToStringSid(win32security.GetTokenInformation(token, win32security.TokenUser)[0]),
        # administrator z podniesionym tokenem tworzy obiekty z wlascicielem "Administratorzy"
        win32security.ConvertSidToStringSid(win32security.GetTokenInformation(token, win32security.TokenOwner)),
    }
    return owner in allowed


def _restrict_to_current_user(path: Path) -> None:
    """Nadaje pelny dostep wylacznie biezacemu uzytkownikowi i systemowi, bez dziedziczenia."""
    import ntsecuritycon
    import win32security

    user = _current_user_sid()
    system = win32security.CreateWellKnownSid(win32security.WinLocalSystemSid)
    acl = win32security.ACL()
    inherit = ntsecuritycon.CONTAINER_INHERIT_ACE | ntsecuritycon.OBJECT_INHERIT_ACE
    for sid in (user, system):
        acl.AddAccessAllowedAceEx(win32security.ACL_REVISION, inherit, ntsecuritycon.FILE_ALL_ACCESS, sid)
    win32security.SetNamedSecurityInfo(
        str(path),
        win32security.SE_FILE_OBJECT,
        win32security.DACL_SECURITY_INFORMATION | win32security.PROTECTED_DACL_SECURITY_INFORMATION,
        None,
        None,
        acl,
        None,
    )


def _private_staging_dir(program_data: str, staging_name: str, leaf: str) -> Path:
    r"""Prywatny katalog roboczy per uzytkownik: ProgramData\<nazwa>\<SID>\<leaf>.

    SID jest zawsze ASCII i unikalny dla konta. Katalog nadrzedny jest wspolny,
    wiec inny uzytkownik moglby go wczesniej utworzyc i podstawic pliki - dlatego
    istniejacy katalog uzywamy tylko wtedy, gdy nalezy do nas, a nowy zabezpieczamy
    DACL tylko dla wlasciciela. Rzuca OSError, gdy to sie nie uda.
    """
    import win32security

    sid = win32security.ConvertSidToStringSid(_current_user_sid())
    user_dir = Path(program_data) / staging_name / sid
    user_dir.parent.mkdir(parents=True, exist_ok=True)
    existed = user_dir.exists()
    user_dir.mkdir(exist_ok=True)
    if existed:
        if not _owned_by_current_user(user_dir):
            raise OSError("katalog roboczy nalezy do innego uzytkownika")
    else:
        _restrict_to_current_user(user_dir)
    staging = user_dir / leaf
    staging.mkdir(exist_ok=True)
    return staging


def ansi_safe_dir(path: Path, *, staging_name: str = "StudioOCR", copy_files: list[str] | None = None) -> Path:
    """Zwraca katalog o sciezce bezpiecznej dla Tesseract, z zawartoscia `path`.

    Kolejnosc prob: sciezka oryginalna -> skrocona nazwa 8.3 -> prywatna kopia
    w ProgramData (ASCII na kazdym systemie). Gdy zadna nie zadziala, rzuca
    UnsafePathError.
    """
    if is_ansi_safe(path):
        return path

    shortened = short_path(path)
    if shortened is not None and is_ansi_safe(shortened):
        return shortened

    program_data = os.environ.get("ProgramData")
    if program_data:
        try:
            staging = _private_staging_dir(program_data, staging_name, path.name)
            if not is_ansi_safe(staging):
                raise OSError("sciezka robocza nie jest ASCII")
            for source in path.iterdir():
                if copy_files is not None and source.name not in copy_files:
                    continue
                if not source.is_file():
                    continue
                target = staging / source.name
                # Zawsze porownujemy SHA-256 (nie rozmiar): plik podstawiony lub
                # uszkodzony zostaje nadpisany kopia zrodla.
                if not target.exists() or _sha256(target) != _sha256(source):
                    temporary = target.with_name(target.name + ".part")
                    shutil.copy2(source, temporary)
                    os.replace(temporary, target)
            return staging
        except Exception:  # noqa: BLE001 - kazdy blad (OSError, win32, brak modulu) = brak bezpiecznej kopii
            pass

    raise UnsafePathError(path)
