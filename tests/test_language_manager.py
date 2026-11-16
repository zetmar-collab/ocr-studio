import hashlib
import threading

import pytest

from src import downloads_manifest as manifest
from src import language_manager as lm
from src.config import BUNDLED_TESSDATA_DIR
from src.jobs import JobCancelled
from src.language_manager import DownloadError, LanguageManager, _atomic_download


class FakeResponse:
    def __init__(self, payload: bytes, status_ok: bool = True, fail_after: int | None = None):
        self.payload, self.status_ok, self.fail_after = payload, status_ok, fail_after

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def raise_for_status(self):
        if not self.status_ok:
            raise lm.requests.HTTPError("404")

    def iter_content(self, chunk_size):
        for offset in range(0, len(self.payload), 4):
            if self.fail_after is not None and offset >= self.fail_after:
                raise lm.requests.ConnectionError("zerwane polaczenie")
            yield self.payload[offset : offset + 4]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_bundled_language_never_touches_the_network(sandbox, monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("polski jest w pakiecie - nie wolno laczyc sie z siecia")

    monkeypatch.setattr(lm.requests, "get", boom)
    path = LanguageManager().install_ocr_language("pol")
    assert path == BUNDLED_TESSDATA_DIR / "pol.traineddata"


def test_list_installed_includes_bundled_languages_on_fresh_profile(sandbox):
    installed = LanguageManager().list_installed_ocr()
    assert {"pol", "eng"} <= set(installed)


def test_available_checks(sandbox):
    manager = LanguageManager()
    assert manager.is_ocr_language_available("pol")
    assert not manager.is_ocr_language_available("deu")
    assert manager.is_spell_dictionary_available("pl_PL") and manager.is_spell_dictionary_available("en_US")
    assert not manager.is_spell_dictionary_available("de_DE")


def test_download_success_is_atomic_and_verified(tmp_path, monkeypatch):
    data = b"zawartosc pliku jezykowego"
    monkeypatch.setattr(lm.requests, "get", lambda *a, **k: FakeResponse(data))
    target = tmp_path / "x.traineddata"
    progress = []
    _atomic_download("http://x", target, sha(data), len(data), label="x", progress=lambda *a: progress.append(a))
    assert target.read_bytes() == data
    assert not (tmp_path / "x.traineddata.part").exists()
    assert progress and progress[-1][0] == len(data)


def test_download_rejects_wrong_checksum_and_leaves_nothing(tmp_path, monkeypatch):
    data = b"podmieniony plik"
    monkeypatch.setattr(lm.requests, "get", lambda *a, **k: FakeResponse(data))
    target = tmp_path / "x.traineddata"
    with pytest.raises(DownloadError, match="suma kontrolna"):
        _atomic_download("http://x", target, sha(b"oryginal"), len(data), label="x")
    assert not target.exists() and not (tmp_path / "x.traineddata.part").exists()


def test_download_rejects_truncated_file(tmp_path, monkeypatch):
    data = b"0123456789"
    monkeypatch.setattr(lm.requests, "get", lambda *a, **k: FakeResponse(data[:5]))
    with pytest.raises(DownloadError):
        _atomic_download("http://x", tmp_path / "x", sha(data), len(data), label="x")
    assert not (tmp_path / "x").exists()


def test_interrupted_download_does_not_leave_a_file_treated_as_installed(sandbox, monkeypatch):
    # regresja: przerwany zapis zostawial uszkodzony .traineddata, ktory kod uznawal za zainstalowany
    data = b"A" * 40
    monkeypatch.setitem(manifest.TESSDATA_FILES, "deu", (sha(data), len(data)))
    monkeypatch.setattr(lm.requests, "get", lambda *a, **k: FakeResponse(data, fail_after=12))
    manager = LanguageManager()
    with pytest.raises(DownloadError):
        manager.install_ocr_language("deu")
    assert not manager.is_ocr_language_available("deu")
    assert list(sandbox.tessdata.iterdir()) == []


def test_http_error_becomes_download_error(tmp_path, monkeypatch):
    monkeypatch.setattr(lm.requests, "get", lambda *a, **k: FakeResponse(b"", status_ok=False))
    with pytest.raises(DownloadError):
        _atomic_download("http://x", tmp_path / "x", sha(b""), 0, label="x")


def test_cancel_removes_partial_file(tmp_path, monkeypatch):
    event = threading.Event()
    event.set()
    monkeypatch.setattr(lm.requests, "get", lambda *a, **k: FakeResponse(b"abcdefgh"))
    with pytest.raises(JobCancelled):
        _atomic_download("http://x", tmp_path / "x", sha(b"abcdefgh"), 8, label="x", cancel=event)
    assert list(tmp_path.iterdir()) == []


def test_spell_dictionary_download_writes_both_files(sandbox, monkeypatch):
    aff, dic = b"SET UTF-8\n", b"1\nslowo\n"
    monkeypatch.setitem(manifest.DICT_FILES, ("de_DE", "aff"), (sha(aff), len(aff)))
    monkeypatch.setitem(manifest.DICT_FILES, ("de_DE", "dic"), (sha(dic), len(dic)))
    payloads = {"index.aff": aff, "index.dic": dic}
    monkeypatch.setattr(lm.requests, "get", lambda url, **k: FakeResponse(payloads[url.rsplit("/", 1)[1]]))
    LanguageManager().install_spell_dictionary("de_DE")
    assert (sandbox.dicts / "de_DE" / "de_DE.aff").read_bytes() == aff
    assert (sandbox.dicts / "de_DE" / "de_DE.dic").read_bytes() == dic


def test_manifest_covers_every_selectable_language():
    from src.config import OCR_LANG_MAP, SPELL_LANG_MAP

    assert set(OCR_LANG_MAP.values()) <= set(manifest.TESSDATA_FILES)
    assert set(SPELL_LANG_MAP.values()) <= set(manifest.SPELL_REPO_CODES)
    for code in SPELL_LANG_MAP.values():
        assert (code, "aff") in manifest.DICT_FILES and (code, "dic") in manifest.DICT_FILES


def test_manifest_urls_are_pinned_to_commit_not_branch():
    # ruchoma galaz 'main' pozwalalaby podmienic plik po stronie zrodla
    assert not manifest.TESSDATA_BASE_URL.endswith("/main")
    assert "/main/" not in manifest.DICT_BASE_URL
    assert len(manifest.TESSDATA_BASE_URL.rsplit("/", 1)[1]) == 40
