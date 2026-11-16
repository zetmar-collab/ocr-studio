"""Testy na prawdziwym, wbudowanym Tesseract (pomijane, gdy brak vendor/)."""

import subprocess
import tempfile
import threading
import time
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from src import ocr_service, pathsafe
from src.ocr_service import (
    OCRCancelled,
    OCRDocumentError,
    OCRLanguageMissingError,
    OCRService,
)

pytestmark = pytest.mark.engine


@pytest.fixture(scope="module")
def service():
    return OCRService()


def tesseract_processes() -> int:
    out = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq tesseract.exe", "/NH"], capture_output=True, text=True, errors="replace"
    ).stdout
    return out.lower().count("tesseract.exe")


def test_bundled_engine_is_used_and_available(service):
    assert service.is_available()
    assert service.uses_bundled_engine


def test_polish_text_with_diacritics(service, sandbox, make_image):
    image = make_image(["Zażółć gęślą jaźń", "Łódź, świnia, ręka"])
    text = service.ocr_document(image, "pol").text
    assert "Zażółć gęślą jaźń" in text and "Łódź" in text and "świnia" in text


def test_text_matches_classic_tesseract_output(service, sandbox, make_image):
    # zmienilismy sposob odbioru tekstu (TSV zamiast txt) - wynik musi byc ten sam
    from src.config import BUNDLED_TESSDATA_DIR, BUNDLED_TESSERACT_EXE

    image = make_image(["Pierwsza linia tekstu", "Druga linia tekstu"], name="cmp.png")
    classic = subprocess.run(
        [str(BUNDLED_TESSERACT_EXE), str(image), "stdout", "-l", "pol", "--tessdata-dir", str(BUNDLED_TESSDATA_DIR)],
        capture_output=True,
    ).stdout.decode("utf-8", "replace")
    ours = service.ocr_document(image, "pol").text
    assert [ln.strip() for ln in ours.strip().splitlines()] == [ln.strip() for ln in classic.strip().splitlines()]


def test_multipage_tiff_reads_every_frame(service, sandbox, tmp_path):
    # regresja: tylko pierwsza strona wielostronicowego TIFF byla rozpoznawana, bez ostrzezenia
    from tests.conftest import _font

    frames = []
    for word in ("alpha", "bravo", "charlie"):
        frame = Image.new("RGB", (1200, 200), "white")
        ImageDraw.Draw(frame).text((50, 60), f"STRONA {word}", fill="black", font=_font(48))
        frames.append(frame)
    tiff = tmp_path / "multi.tif"
    frames[0].save(tiff, save_all=True, append_images=frames[1:], dpi=(200, 200))

    progress = []
    result = service.ocr_document(tiff, "eng", progress=lambda d, t, n: progress.append((d, t)))

    assert result.pages == 3
    assert all(word in result.text for word in ("alpha", "bravo", "charlie"))
    assert progress == [(0, 3), (1, 3), (2, 3), (3, 3)]


def test_searchable_pdf_roundtrip_and_text_layer_reuse(service, sandbox, make_image, tmp_path):
    image = make_image(["Przeszukiwalny dokument alpha bravo"])
    pdf = tmp_path / "out.pdf"
    assert service.export_searchable_pdf(image, pdf, "pol") == 1

    reread = service.ocr_document(pdf, "pol")
    assert reread.text_layer_pages == 1 and "alpha" in reread.text

    forced = service.ocr_document(pdf, "pol", force_ocr=True)
    assert forced.text_layer_pages == 0 and "alpha" in forced.text


def test_searchable_pdf_keeps_text_layer_pages_untouched(service, sandbox, make_image, tmp_path):
    image = make_image(["Strona z warstwa tekstowa gamma delta"])
    first = tmp_path / "first.pdf"
    service.export_searchable_pdf(image, first, "pol")
    second = tmp_path / "second.pdf"
    service.export_searchable_pdf(first, second, "pol")  # wejscie ma juz tekst -> strona przepisana bez OCR
    assert "gamma" in service.ocr_document(second, "pol").text
    assert service.ocr_document(second, "pol").text_layer_pages == 1


def test_missing_language_is_reported_before_any_work(service, sandbox, make_image):
    image = make_image(["tekst"])
    with pytest.raises(OCRLanguageMissingError) as info:
        service.ocr_document(image, "pol+xyz")
    assert info.value.lang_code == "xyz"


def test_broken_pdf_raises_document_error(service, sandbox, tmp_path):
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"to nie jest pdf")
    with pytest.raises(OCRDocumentError) as info:
        service.ocr_document(bad, "pol")
    assert info.value.path == bad


def test_cancel_before_start_raises_immediately(service, sandbox, make_image):
    event = threading.Event()
    event.set()
    with pytest.raises(OCRCancelled):
        service.ocr_document(make_image(["tekst"]), "pol", cancel=event)


def test_cancel_during_run_kills_the_engine_process(service, sandbox, tmp_path):
    # Jeden ciezki obraz (~8 s OCR): bez zabicia procesu tesseract.exe pracowalby dalej po anulowaniu.
    from tests.conftest import _font

    image = Image.new("RGB", (4000, 7300), "white")
    draw = ImageDraw.Draw(image)
    for index in range(80):
        draw.text((60, 50 + index * 90), f"Linia {index} Lorem ipsum dolor sit amet consectetur adipiscing", fill="black", font=_font(44))
    path = tmp_path / "heavy.png"
    image.save(path, dpi=(300, 300))

    before = tesseract_processes()
    event = threading.Event()
    threading.Timer(0.7, event.set).start()
    started = time.perf_counter()
    with pytest.raises(OCRCancelled):
        service.ocr_document(path, "eng", cancel=event)
    elapsed = time.perf_counter() - started

    assert elapsed < 3.0, f"anulowanie trwalo {elapsed:.1f}s (OCR calosci to ~8s)"
    time.sleep(0.4)
    assert tesseract_processes() <= before, "po anulowaniu zostal proces tesseract.exe"


def test_cancel_between_pages_of_a_long_document(service, sandbox, tmp_path):
    from tests.conftest import _font

    frames = []
    for index in range(30):
        frame = Image.new("RGB", (1500, 300), "white")
        ImageDraw.Draw(frame).text((50, 80), f"Strona numer {index} alpha bravo charlie", fill="black", font=_font(48))
        frames.append(frame)
    tiff = tmp_path / "long.tif"
    frames[0].save(tiff, save_all=True, append_images=frames[1:], dpi=(200, 200))

    seen = []
    event = threading.Event()

    def progress(done, total, name):
        seen.append(done)
        if done == 2:
            event.set()

    with pytest.raises(OCRCancelled):
        service.ocr_document(tiff, "eng", cancel=event, progress=progress)
    assert max(seen) <= 3, f"po anulowaniu przetworzono za duzo stron: {seen}"


def test_ocr_creates_no_temporary_files(service, sandbox, make_image):
    # regresja: obrazy stron trafialy do %TEMP% (mktemp) i po awarii zostawaly na dysku
    tmp = Path(tempfile.gettempdir())
    before = {p.name for p in tmp.iterdir()}
    service.ocr_document(make_image(["bez plikow tymczasowych"]), "pol")
    leftovers = {p.name for p in tmp.iterdir()} - before
    assert not [n for n in leftovers if n.lower().endswith(".png")], leftovers


def test_console_window_is_suppressed(service, sandbox, make_image, monkeypatch):
    # regresja: bez CREATE_NO_WINDOW kazde wywolanie otwieralo okno konsoli w aplikacji okienkowej
    seen = {}
    real_popen = subprocess.Popen

    def spy(*args, **kwargs):
        seen.update(kwargs)
        return real_popen(*args, **kwargs)

    monkeypatch.setattr(ocr_service.subprocess, "Popen", spy)
    service.ocr_document(make_image(["okno konsoli"]), "pol")
    assert seen["creationflags"] & subprocess.CREATE_NO_WINDOW
    assert seen["startupinfo"].wShowWindow == subprocess.SW_HIDE


def test_image_in_non_ascii_directory(service, sandbox, make_image, tmp_path):
    # obraz idzie przez stdin, wiec jego sciezka nie ma znaczenia
    folder = tmp_path / "Юзер_名前"
    folder.mkdir()
    image = make_image(["sciezka z cyrylica"], name="x.png")
    moved = folder / "x.png"
    image.replace(moved)
    assert "cyrylica" in service.ocr_document(moved, "pol").text


def test_downloaded_language_in_non_ascii_profile_directory(service, sandbox, make_image, tmp_path, monkeypatch):
    # regresja: dane uzytkownika z nazwa konta spoza strony kodowej ANSI powodowaly "Error opening data file"
    unsafe = tmp_path / "Юзер_名前" / "tessdata"
    unsafe.mkdir(parents=True)
    from src.config import BUNDLED_TESSDATA_DIR

    (unsafe / "deu.traineddata").write_bytes((BUNDLED_TESSDATA_DIR / "eng.traineddata").read_bytes())  # model dowolny
    program_data = tmp_path / "ProgramData"
    program_data.mkdir()
    monkeypatch.setattr(ocr_service, "TESSDATA_DIR", unsafe)
    monkeypatch.setenv("ProgramData", str(program_data))

    result = service.ocr_document(make_image(["Hello unsafe profile"]), "deu")

    assert "Hello" in result.text
    prepared = service.prepare_languages("deu")
    assert pathsafe.is_ansi_safe(prepared), f"Tesseract dostal niebezpieczna sciezke: {prepared}"


def test_bundled_languages_use_bundled_directory_directly(service, sandbox):
    from src.config import BUNDLED_TESSDATA_DIR

    assert service.prepare_languages("pol") == BUNDLED_TESSDATA_DIR
    assert service.prepare_languages("pol+eng") == BUNDLED_TESSDATA_DIR
    assert list(sandbox.tessdata.iterdir()) == [], "jezyki z pakietu nie powinny byc kopiowane do profilu"


def test_exif_rotated_photo_is_straightened(service, sandbox, make_image, tmp_path):
    upright = Image.open(make_image(["Obrocone zdjecie z telefonu"], name="up.png")).convert("RGB")
    sideways = upright.rotate(90, expand=True)  # fizycznie lezy bokiem
    exif = Image.Exif()
    exif[0x0112] = 6  # "obroc o 90 w prawo, zeby wyswietlic prosto"
    photo = tmp_path / "photo.jpg"
    sideways.save(photo, exif=exif, dpi=(200, 200))
    assert "telefonu" in service.ocr_document(photo, "pol").text


def test_transparent_png_is_composited_on_white(service, sandbox, tmp_path):
    # regresja: tekst na przezroczystym tle zamienial sie w czarne na czarnym
    from tests.conftest import _font

    image = Image.new("RGBA", (1400, 200), (0, 0, 0, 0))
    ImageDraw.Draw(image).text((50, 60), "Przezroczyste tlo", fill=(0, 0, 0, 255), font=_font(52))
    path = tmp_path / "alpha.png"
    image.save(path, dpi=(200, 200))
    assert "Przezroczyste" in service.ocr_document(path, "pol").text


def test_low_confidence_spans_point_at_real_words(service, sandbox, make_image):
    image = make_image(["Pierwsza linia", "Druga linia dokumentu"])
    result = service.ocr_document(image, "pol", threshold=101)  # prog 101 -> kazde slowo "niepewne"
    flagged = [result.text[s:e] for s, e in result.low_confidence]
    assert flagged == result.text.split() and flagged, "zakresy musza wskazywac dokladnie slowa"


def test_multiple_languages_in_one_call(service, sandbox, make_image):
    text = service.ocr_document(make_image(["Zażółć gęślą oraz English words"]), "pol+eng").text
    assert "Zażółć" in text and "English" in text


def test_large_image_is_handled(service, sandbox, tmp_path):
    from tests.conftest import _font

    image = Image.new("RGB", (6000, 4000), "white")
    ImageDraw.Draw(image).text((200, 200), "Duzy skan alpha", fill="black", font=_font(160))
    path = tmp_path / "big.png"
    image.save(path, dpi=(300, 300))
    assert "alpha" in service.ocr_document(path, "pol").text
