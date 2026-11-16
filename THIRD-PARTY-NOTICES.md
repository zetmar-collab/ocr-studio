# Informacje o oprogramowaniu innych producentów / Third-party notices

Studio OCR zawiera komponenty innych producentów, rozpowszechniane na wymienionych
niżej licencjach. Pełne teksty licencji Tesseract i słowników są dołączone do aplikacji
(patrz „Gdzie szukać pełnych tekstów").

Studio OCR includes third-party components distributed under the licences listed below.
Full licence texts for Tesseract and the dictionaries ship inside the application
(see "Where to find the full texts").

---

## Tesseract OCR 5.3.1

Silnik rozpoznawania tekstu dołączony do aplikacji. / The text recognition engine
bundled with the application.

- Strona / Homepage: https://github.com/tesseract-ocr/tesseract
- Licencja / License: **Apache License 2.0**
- Pełny tekst / Full text: `LICENSE-tesseract-apache-2.0.txt` (katalog `tesseract` w aplikacji)
- Pliki językowe `eng` i `pol` (`tessdata_best`): Apache License 2.0
  (https://github.com/tesseract-ocr/tessdata_best)
- Dystrybucja kompilacji: UB Mannheim (https://github.com/UB-Mannheim/tesseract/wiki)

Dodatkowe języki pobierane na życzenie użytkownika pochodzą z tego samego repozytorium
i są weryfikowane sumą SHA-256 przypiętą w `src/downloads_manifest.py`.

## Leptonica 1.83

Biblioteka przetwarzania obrazu wymagana przez Tesseract. / Image processing library
required by Tesseract. http://www.leptonica.org/ — licencja **BSD 2-Clause**:

```
Copyright (C) 2001 Leptonica. All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

## Biblioteki towarzyszące Tesseract / Libraries bundled with Tesseract

Do aplikacji dołączone są wyłącznie biblioteki DLL, od których `tesseract.exe` faktycznie
zależy (34 pliki, wyznaczone z tablicy importów PE przez `scripts/vendor_tesseract.py`).
Only the DLLs that `tesseract.exe` actually depends on are bundled (34 files, derived from
the PE import table by `scripts/vendor_tesseract.py`).

| Biblioteka / Library | Licencja / License |
| --- | --- |
| libtiff, libjpeg-turbo (libjpeg), libpng, libgif, libwebp, libsharpyuv, libopenjp2, libjbig | BSD / zlib / IJG / libtiff / MIT-style |
| zlib, libdeflate, libzstd, liblzma, libbz2, liblz4, brotli (libbrotlicommon, libbrotlidec) | zlib / BSD / public domain / MIT |
| libarchive | BSD 2-Clause |
| libb2 (BLAKE2) | CC0 / Apache 2.0 / OpenSSL (do wyboru) |
| libcurl, libssh2, libpsl, libidn2, libunistring | curl licence / BSD / MIT / LGPL-3.0+ / GPL-2+ or LGPL-3+ |
| OpenSSL (libcrypto) | Apache License 2.0 |
| libexpat | MIT |
| libiconv, libintl (gettext) | LGPL-2.1+ |
| Lerc | Apache License 2.0 |
| MinGW-w64 runtime: libgcc_s_seh, libstdc++, libwinpthread | GCC Runtime Library Exception (GPL-3.0 with exception) / MIT-style |

Biblioteki LGPL (libiconv, libintl, libidn2, libunistring) są dołączone jako osobne pliki
`.dll`, które można podmienić na własną kompilację tej samej biblioteki. / The LGPL
libraries are shipped as separate `.dll` files that can be replaced with your own build of
the same library. Kod źródłowy / Source: https://www.gnu.org/software/libiconv/ ,
https://www.gnu.org/software/gettext/ , https://github.com/libidn/libidn2 ,
https://www.gnu.org/software/libunistring/ .

Licencje bibliotek towarzyszących podano **orientacyjnie** (typowe dla tych projektów);
w razie rozbieżności obowiązują teksty licencji w repozytoriach źródłowych danego projektu.
Nie dołączamy ich pełnych tekstów poza Apache 2.0 (Tesseract) i BSD (Leptonica). /
The licences of the supporting libraries are given **indicatively**; in case of any
discrepancy the licence texts in each project's source repository prevail. Full texts are
bundled only for Apache 2.0 (Tesseract) and BSD (Leptonica).

## PDFium / pypdfium2

Renderowanie stron PDF i odczyt warstwy tekstowej. / PDF rendering and text-layer reading.

- https://github.com/pypdfium2-team/pypdfium2 — Apache 2.0 / BSD 3-Clause (PDFium)
- Pełne teksty licencji: katalog `pypdfium2-*.dist-info/licenses` w aplikacji.

## Słowniki pisowni Hunspell / Hunspell spelling dictionaries

Wbudowane słowniki `pl_PL` i `en_US` (z https://github.com/wooorm/dictionaries, MIT)
oraz słowniki pobierane na życzenie (de_DE, fr_FR, es_ES, it_IT).

| Słownik | Źródło / Origin | Licencja / License |
| --- | --- | --- |
| `pl_PL` | Polish Native Lang Project (pl.openoffice.org), opiekun Marek Futrega | GPL, LGPL, MPL i Creative Commons ShareAlike (do wyboru) |
| `en_US` | SCOWL (http://wordlist.sourceforge.net) | permisywna licencja SCOWL |

Pełne teksty: `LICENSE-pl_PL.txt` i `LICENSE-en_US.txt` (katalog `dictionaries` w aplikacji).
Słowniki są danymi, nie kodem — używamy ich bez modyfikacji i rozpowszechniamy wraz z
tekstem licencji.

## Biblioteki Pythona / Python libraries

| Biblioteka / Library | Licencja / License |
| --- | --- |
| CustomTkinter, darkdetect | MIT, BSD 3-Clause |
| Pillow | MIT-CMU (HPND) |
| python-docx, lxml | MIT, BSD |
| requests, urllib3, certifi, idna | Apache 2.0, MIT, MPL 2.0, BSD |
| spylls | MPL 2.0 |
| tkinterdnd2 (tkdnd) | MIT (BSD-style) |
| pywin32 | PSF |
| Python, Tcl/Tk | PSF, Tcl/Tk licence |

## Gdzie szukać pełnych tekstów / Where to find the full texts

W zainstalowanej aplikacji: katalog `_internal` — `tesseract\LICENSE-tesseract-apache-2.0.txt`,
`dictionaries\pl_PL\LICENSE-pl_PL.txt`, `dictionaries\en_US\LICENSE-en_US.txt`, `LICENSE`
(licencja MIT samej aplikacji).

---

Sama aplikacja Studio OCR jest rozpowszechniana na licencji MIT — zobacz plik `LICENSE`.
Studio OCR itself is distributed under the MIT license — see `LICENSE`.
