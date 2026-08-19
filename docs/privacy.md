---
title: Studio OCR — polityka prywatności
---

# Polityka prywatności — Studio OCR

Ostatnia aktualizacja: 19 sierpnia 2026

## Krótko

Studio OCR nie zbiera, nie przechowuje ani nie przesyła żadnych danych
osobowych. Dokumenty, które rozpoznajesz, skanujesz i eksportujesz, pozostają
wyłącznie na Twoim komputerze — nigdy nie są wysyłane na żaden serwer.

## Jakie dane przetwarza aplikacja

Wszystkie dokumenty (obrazy, pliki PDF, skany) są przetwarzane lokalnie, przez
silnik Tesseract wbudowany w aplikację i uruchamiany na Twoim komputerze.
Rozpoznany tekst pojawia się w oknie aplikacji i trafia do pliku tylko wtedy,
gdy sam wybierzesz eksport do TXT lub DOCX i wskażesz miejsce zapisu.

Aplikacja zapisuje na dysku wyłącznie:

- ustawienia interfejsu (motyw jasny/ciemny/systemowy oraz język PL/EN),
- dodatkowe pliki językowe OCR i słowniki pisowni, jeśli je doinstalujesz,
- słowa, które sam dodasz do własnego słownika pisowni,
- tymczasowe pliki robocze potrzebne w trakcie rozpoznawania, usuwane po
  zakończeniu operacji.

Dane te trafiają do folderu aplikacji w Twoim profilu użytkownika
(`%LOCALAPPDATA%\OCR Studio\`) i nie opuszczają urządzenia.

## Połączenia internetowe

Silnik OCR oraz języki polski i angielski są wbudowane w aplikację, więc
rozpoznawanie tekstu działa od razu po instalacji, **bez połączenia
z internetem**.

Aplikacja łączy się z siecią wyłącznie wtedy, gdy sam poprosisz o doinstalowanie
dodatkowego języka OCR lub słownika pisowni. Pobierane są wtedy publicznie
dostępne pliki z:

- `github.com/tesseract-ocr/tessdata_best` — pliki językowe OCR,
- `github.com/wooorm/dictionaries` — słowniki pisowni Hunspell.

Są to zwykłe pobrania plików. Aplikacja nie wysyła przy tym Twoich dokumentów,
tekstu ani żadnych informacji o Tobie — poza tym, co każda przeglądarka
przekazuje przy pobieraniu pliku (adres IP, na poziomie serwera dostawcy).

## Skaner

Jeśli korzystasz ze skanowania, aplikacja używa systemowego interfejsu Windows
(WIA), aby pobrać obraz z Twojego skanera i zapisać go w miejscu, które
wskażesz. Obraz nie jest nigdzie wysyłany.

## Czego aplikacja nie robi

- nie zbiera telemetrii, statystyk użycia ani identyfikatorów urządzenia,
- nie wymaga konta ani logowania,
- nie wysyła dokumentów, skanów ani rozpoznanego tekstu na serwery,
- nie instaluje żadnego dodatkowego oprogramowania w systemie,
- nie wymaga uprawnień administratora,
- nie korzysta z lokalizacji, kamery, mikrofonu ani kontaktów,
- nie wyświetla reklam i nie udostępnia niczego stronom trzecim.

## Uprawnienia w pakiecie

Pakiet ze Sklepu Windows deklaruje uprawnienie `runFullTrust`. Jest ono
wymagane technicznie dla klasycznych aplikacji desktopowych (Win32) i pozwala
programowi uruchomić wbudowany silnik OCR, skorzystać ze skanera oraz zapisać
własne pliki ustawień i słowników. Nie jest wykorzystywane do odczytu Twoich
plików ani do dostępu do danych innych aplikacji.

## Kod źródłowy i składniki open source

Aplikacja jest otwartoźródłowa (licencja MIT). Cały kod można sprawdzić pod
adresem <https://github.com/zetmar-collab/ocr-studio>.

Wbudowany silnik rozpoznawania tekstu to Tesseract OCR (licencja Apache 2.0).
Pełna lista komponentów innych producentów wraz z licencjami znajduje się
w pliku
<https://github.com/zetmar-collab/ocr-studio/blob/main/THIRD-PARTY-NOTICES.md>.

## Kontakt

Pytania dotyczące prywatności: <https://github.com/zetmar-collab/ocr-studio/issues>
