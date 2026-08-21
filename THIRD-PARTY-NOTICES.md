# Informacje o oprogramowaniu innych producentow / Third-party notices

Studio OCR zawiera nastepujace komponenty innych producentow.
Studio OCR includes the following third-party components.

---

## Tesseract OCR

Silnik rozpoznawania tekstu dolaczony do aplikacji.
The text recognition engine bundled with the application.

- Strona / Homepage: https://github.com/tesseract-ocr/tesseract
- Licencja / License: Apache License 2.0
- Pliki jezykowe / Language data: https://github.com/tesseract-ocr/tessdata_best
  (Apache License 2.0)

Kopia licencji: https://www.apache.org/licenses/LICENSE-2.0

## Leptonica

Biblioteka przetwarzania obrazu, wymagana przez Tesseract.
Image processing library required by Tesseract.

- Strona / Homepage: http://www.leptonica.org/
- Licencja / License: BSD 2-Clause

## Biblioteki towarzyszace / Supporting libraries

Runtime Tesseract korzysta z bibliotek obslugi formatow obrazu, kompresji
i sieci, dystrybuowanych razem z nim w kompilacji UB Mannheim:
libtiff, libpng, libjpeg, libwebp, libopenjp2, libgif, zlib, zstd, lzma,
brotli, bzip2, libdeflate, libarchive, libcurl, libssh2, OpenSSL, libexpat,
libiconv, gettext (libintl), libpsl, libidn2, libunistring, Lerc, libb2, lz4
oraz biblioteki uruchomieniowe MinGW-w64 (libgcc, libstdc++, libwinpthread).

Kazda z nich jest rozpowszechniana na wlasnej licencji typu open source
(BSD, MIT, zlib, Apache 2.0, LGPL lub podobnej). Pelne teksty licencji
znajduja sie w repozytoriach zrodlowych tych projektow.

## pypdfium2 / PDFium

Renderowanie stron PDF przed rozpoznaniem tekstu.
Rendering of PDF pages before text recognition.

- Strona / Homepage: https://github.com/pypdfium2-team/pypdfium2
- Licencja / License: Apache 2.0 / BSD 3-Clause (PDFium)

## Hunspell dictionaries (wooorm/dictionaries)

Slowniki pisowni pobierane na zadanie uzytkownika.
Spelling dictionaries downloaded on user request.

- Strona / Homepage: https://github.com/wooorm/dictionaries
- Licencje / Licenses: rozne dla poszczegolnych jezykow (MIT, LGPL, BSD,
  Creative Commons) - szczegoly w katalogu kazdego slownika.

## Pozostale biblioteki Pythona / Other Python libraries

CustomTkinter (MIT), Pillow (MIT-CMU), python-docx (MIT), requests (Apache 2.0),
spylls (MPL 2.0), pytesseract (Apache 2.0), pywin32 (PSF).

---

Sama aplikacja Studio OCR jest rozpowszechniana na licencji MIT - zobacz plik
LICENSE. / Studio OCR itself is distributed under the MIT license - see LICENSE.
