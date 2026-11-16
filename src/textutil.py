"""Operacje na tekscie rozpoznanym przez OCR."""

from __future__ import annotations

import re

# znaki sterujace niedozwolone w XML (DOCX) - poza \t, \n, \r
_XML_ILLEGAL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f￾￿]")
_LIST_MARKER = re.compile(r"^\s*(?:[-–—•*●]|\d{1,3}[.)])\s+")
_SOFT_HYPHEN = "­"


def strip_control_chars(text: str) -> str:
    """Usuwa znaki, ktore psuja XML (np. znak konca strony \\f z Tesseract)."""
    return _XML_ILLEGAL.sub("", text)


def reflow_paragraphs(text: str) -> str:
    """Skleja linie w akapity.

    Tesseract zwraca tekst lamany tak jak na papierze: kazda linia wizualna to
    osobny wiersz. Tu laczymy linie nalezace do jednego akapitu (akapity sa
    rozdzielone pustymi liniami), zachowujac punktory list i lacząc wyrazy
    podzielone myslnikiem na koncu linii.
    """
    text = strip_control_chars(text).replace("\r\n", "\n").replace("\r", "\n")
    out: list[str] = []

    for block in re.split(r"\n\s*\n", text):
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if not lines:
            continue

        paragraphs: list[str] = []
        current = lines[0]
        for line in lines[1:]:
            if _LIST_MARKER.match(line):
                paragraphs.append(current)
                current = line
                continue
            current = _join_lines(current, line)
        paragraphs.append(current)
        out.extend(paragraphs)

    return "\n\n".join(out)


def _join_lines(previous: str, following: str) -> str:
    if previous.endswith(_SOFT_HYPHEN):
        return previous[:-1] + following
    # "wyra-" + "zenie" -> "wyrazenie"; ale "np. A-" + "B" zostaje, bo nastepna linia
    # nie zaczyna sie od malej litery
    if previous.endswith("-") and len(previous) > 1 and previous[-2].isalpha() and following[:1].islower():
        return previous[:-1] + following
    return previous + " " + following
