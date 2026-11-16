from pathlib import Path

import pytest

from src import pathsafe
from src.pathsafe import UnsafePathError, ansi_safe_dir, is_ansi_safe

UNSAFE_MARKER = "Юзер"


@pytest.fixture
def fake_ansi(monkeypatch):
    """Deterministyczne: sciezka z cyrylica jest 'niebezpieczna' niezaleznie od strony kodowej systemu."""
    monkeypatch.setattr(pathsafe, "is_ansi_safe", lambda p: UNSAFE_MARKER not in str(p))


def test_ascii_path_is_safe():
    assert is_ansi_safe(r"C:\Users\Marek\AppData\Local\OCR Studio\data")


def test_unencodable_characters_are_unsafe_on_non_utf8_codepage():
    import ctypes

    if ctypes.windll.kernel32.GetACP() == 65001:  # UTF-8 jako strona kodowa systemu - wszystko bezpieczne
        pytest.skip("system uzywa UTF-8 jako ANSI")
    assert not is_ansi_safe("C:\\Users\\\U0001f600\\data")


def test_safe_directory_is_returned_unchanged(tmp_path):
    assert ansi_safe_dir(tmp_path) == tmp_path


def test_unsafe_directory_uses_short_path_when_available(tmp_path, monkeypatch, fake_ansi):
    unsafe = tmp_path / UNSAFE_MARKER
    unsafe.mkdir()
    monkeypatch.setattr(pathsafe, "short_path", lambda p: tmp_path / "SHORT~1")
    assert ansi_safe_dir(unsafe) == tmp_path / "SHORT~1"


def test_unsafe_directory_falls_back_to_staging_copy(tmp_path, monkeypatch, fake_ansi):
    unsafe = tmp_path / UNSAFE_MARKER / "tessdata"
    unsafe.mkdir(parents=True)
    (unsafe / "deu.traineddata").write_bytes(b"x" * 10)
    (unsafe / "inny.plik").write_bytes(b"y")
    program_data = tmp_path / "ProgramData"
    program_data.mkdir()
    monkeypatch.setenv("ProgramData", str(program_data))
    monkeypatch.setattr(pathsafe, "short_path", lambda p: None)

    result = ansi_safe_dir(unsafe, copy_files=["deu.traineddata"])

    assert result.parent.parent == program_data / "StudioOCR"  # StudioOCR\<SID>\tessdata
    assert result.parent.name.startswith("S-1-5-")
    assert (result / "deu.traineddata").read_bytes() == b"x" * 10
    assert not (result / "inny.plik").exists()  # kopiujemy tylko potrzebne pliki


def test_staging_copy_is_refreshed_when_source_changes(tmp_path, monkeypatch, fake_ansi):
    unsafe = tmp_path / UNSAFE_MARKER / "tessdata"
    unsafe.mkdir(parents=True)
    source = unsafe / "deu.traineddata"
    source.write_bytes(b"stare")
    (tmp_path / "pd").mkdir()
    monkeypatch.setenv("ProgramData", str(tmp_path / "pd"))
    monkeypatch.setattr(pathsafe, "short_path", lambda p: None)

    ansi_safe_dir(unsafe)
    source.write_bytes(b"nowa dluzsza zawartosc")
    result = ansi_safe_dir(unsafe)

    assert (result / "deu.traineddata").read_bytes() == b"nowa dluzsza zawartosc"


def test_raises_when_no_safe_location_exists(tmp_path, monkeypatch, fake_ansi):
    unsafe = tmp_path / UNSAFE_MARKER
    unsafe.mkdir()
    monkeypatch.delenv("ProgramData", raising=False)
    monkeypatch.setattr(pathsafe, "short_path", lambda p: None)
    with pytest.raises(UnsafePathError) as info:
        ansi_safe_dir(unsafe)
    assert info.value.path == Path(unsafe)


def staging_setup(tmp_path, monkeypatch):
    unsafe = tmp_path / UNSAFE_MARKER / "tessdata"
    unsafe.mkdir(parents=True)
    program_data = tmp_path / "pd"
    program_data.mkdir()
    monkeypatch.setenv("ProgramData", str(program_data))
    monkeypatch.setattr(pathsafe, "short_path", lambda p: None)
    monkeypatch.setattr(pathsafe, "is_ansi_safe", lambda p: UNSAFE_MARKER not in str(p))
    return unsafe


def test_tampered_staged_file_of_same_size_is_overwritten(tmp_path, monkeypatch):
    # regresja z przegladu bezpieczenstwa: porownanie po rozmiarze nie wykrywalo podmiany pliku
    unsafe = staging_setup(tmp_path, monkeypatch)
    source = unsafe / "deu.traineddata"
    source.write_bytes(b"A" * 64)
    staged = pathsafe.ansi_safe_dir(unsafe) / "deu.traineddata"
    staged.write_bytes(b"B" * 64)  # ten sam rozmiar, inna zawartosc - podmiana przez innego procesu
    pathsafe.ansi_safe_dir(unsafe)
    assert staged.read_bytes() == b"A" * 64


def test_staging_directory_owned_by_someone_else_is_refused(tmp_path, monkeypatch):
    unsafe = staging_setup(tmp_path, monkeypatch)
    (unsafe / "deu.traineddata").write_bytes(b"x")
    pathsafe.ansi_safe_dir(unsafe)  # pierwsze uzycie tworzy katalog uzytkownika
    monkeypatch.setattr(pathsafe, "_owned_by_current_user", lambda p: False)
    with pytest.raises(UnsafePathError):
        pathsafe.ansi_safe_dir(unsafe)  # katalog istnieje i "nalezy do kogos innego" - nie wolno go uzyc


def test_staging_directory_is_restricted_to_current_user(tmp_path, monkeypatch):
    import win32security

    unsafe = staging_setup(tmp_path, monkeypatch)
    (unsafe / "deu.traineddata").write_bytes(b"x")
    user_dir = pathsafe.ansi_safe_dir(unsafe).parent

    assert pathsafe._owned_by_current_user(user_dir)
    dacl = win32security.GetFileSecurity(str(user_dir), win32security.DACL_SECURITY_INFORMATION).GetSecurityDescriptorDacl()
    to_text = win32security.ConvertSidToStringSid
    trustees = {to_text(dacl.GetAce(i)[2]) for i in range(dacl.GetAceCount())}
    assert trustees == {to_text(pathsafe._current_user_sid()), to_text(win32security.CreateWellKnownSid(win32security.WinLocalSystemSid))}
    assert user_dir.stat().st_mode  # katalog nadal dostepny dla wlasciciela


def test_staging_is_ascii_and_stable_between_calls(tmp_path, monkeypatch):
    unsafe = staging_setup(tmp_path, monkeypatch)
    (unsafe / "deu.traineddata").write_bytes(b"x")
    first = pathsafe.ansi_safe_dir(unsafe)
    assert str(first).isascii() and pathsafe.ansi_safe_dir(unsafe) == first
