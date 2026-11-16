from src.textutil import reflow_paragraphs, strip_control_chars


def test_strip_control_chars_removes_form_feed_and_null():
    assert strip_control_chars("a\x0cb\x00c\x0bd") == "abcd"


def test_strip_control_chars_keeps_newlines_and_tabs():
    assert strip_control_chars("a\tb\nc\r\nd") == "a\tb\nc\r\nd"


def test_reflow_joins_lines_within_paragraph():
    text = "To jest pierwszy\nakapit dokumentu\ni konczy sie tutaj.\n\nDrugi akapit\njest tutaj."
    assert reflow_paragraphs(text) == "To jest pierwszy akapit dokumentu i konczy sie tutaj.\n\nDrugi akapit jest tutaj."


def test_reflow_removes_hyphenation_before_lowercase():
    assert reflow_paragraphs("wyra-\nzenie jest poprawne") == "wyrazenie jest poprawne"


def test_reflow_keeps_hyphen_before_uppercase_or_digit():
    # "A-" + "B" to nie przeniesienie wyrazu
    assert reflow_paragraphs("punkt A-\nB oraz") == "punkt A- B oraz"


def test_reflow_removes_soft_hyphen():
    assert reflow_paragraphs("wyra\u00ad\nzenie") == "wyrazenie"


def test_reflow_keeps_list_items_separate():
    text = "Lista zakupow:\n- chleb\n- maslo\n1. pierwszy\n2) drugi"
    result = reflow_paragraphs(text)
    assert result.split("\n\n") == ["Lista zakupow:", "- chleb", "- maslo", "1. pierwszy", "2) drugi"]


def test_reflow_handles_crlf_and_blank_input():
    assert reflow_paragraphs("a\r\nb\r\n\r\nc") == "a b\n\nc"
    assert reflow_paragraphs("") == ""
    assert reflow_paragraphs("\n\n  \n") == ""


def test_reflow_strips_control_characters():
    assert reflow_paragraphs("linia\x0c\nkolejna") == "linia kolejna"
