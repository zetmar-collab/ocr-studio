import pytest

from src.ocr_service import OCRResult, parse_languages, parse_tsv

HEADER = "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext"


def row(block, par, line, word, text, conf, level=5):
    return f"{level}\t1\t{block}\t{par}\t{line}\t{word}\t0\t0\t10\t10\t{conf}\t{text}"


def test_parse_tsv_builds_lines_and_paragraphs():
    tsv = "\n".join(
        [
            HEADER,
            row(0, 0, 0, 0, "", -1, level=1),
            row(1, 1, 1, 1, "Alfa", 95),
            row(1, 1, 1, 2, "beta", 96),
            row(1, 1, 2, 1, "gamma", 97),
            row(2, 1, 1, 1, "Delta", 93),
        ]
    )
    result = parse_tsv(tsv)
    assert result.text == "Alfa beta\ngamma\n\nDelta"
    assert result.pages == 1


def test_parse_tsv_marks_low_confidence_words_with_exact_spans():
    tsv = "\n".join([HEADER, row(1, 1, 1, 1, "dobre", 95), row(1, 1, 1, 2, "watpliwe", 40), row(1, 1, 1, 3, "ok", 90)])
    result = parse_tsv(tsv, threshold=60)
    assert result.low_confidence == [(6, 14)]
    assert result.text[6:14] == "watpliwe"


def test_parse_tsv_ignores_non_word_levels_and_empty_text():
    tsv = "\n".join([HEADER, row(1, 1, 1, 0, "", -1, level=4), row(1, 1, 1, 1, "   ", 90), row(1, 1, 1, 2, "slowo", 80)])
    assert parse_tsv(tsv).text == "slowo"


def test_parse_tsv_tolerates_crlf_and_garbage_confidence():
    tsv = HEADER + "\r\n" + row(1, 1, 1, 1, "a", "abc") + "\r\n"
    assert parse_tsv(tsv).text == "a"


def test_parse_tsv_empty_input():
    result = parse_tsv("")
    assert result.text == "" and result.low_confidence == []


def test_ocrresult_append_shifts_spans():
    first = OCRResult(text="pierwszy", low_confidence=[(0, 3)], pages=1)
    second = OCRResult(text="drugi", low_confidence=[(1, 4)], pages=1, text_layer_pages=1)
    first.append(second)
    assert first.text == "pierwszy\n\ndrugi"
    assert first.low_confidence == [(0, 3), (11, 14)]
    assert first.text[11:14] == "rug"
    assert (first.pages, first.text_layer_pages) == (2, 1)


@pytest.mark.parametrize("spec,expected", [("pol", ["pol"]), ("pol+eng", ["pol", "eng"]), ("chi_sim", ["chi_sim"])])
def test_parse_languages_accepts_valid(spec, expected):
    assert parse_languages(spec) == expected


@pytest.mark.parametrize("spec", ["", "+", "pol; calc", "pol+../x", "po", "pol eng", "pol+", "a" * 40])
def test_parse_languages_rejects_dangerous_or_malformed(spec):
    # kod jezyka trafia do wiersza polecen Tesseract - musi byc scisle walidowany
    with pytest.raises(ValueError):
        parse_languages(spec)
