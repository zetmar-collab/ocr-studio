---
title: Studio OCR — polityka prywatności
---

# Polityka prywatności — Studio OCR

Ostatnia aktualizacja: 17 sierpnia 2026

## Krótko

Studio OCR nie zbiera, nie przechowuje ani nie przesyła żadnych danych
osobowych. Dokumenty, które rozpoznajesz, skanujesz i eksportujesz, pozostają
wyłącznie na Twoim komputerze — nigdy nie są wysyłane na żaden serwer.

## Jakie dane przetwarza aplikacja

Wszystkie dokumenty (obrazy, pliki PDF, skany) są przetwarzane lokalnie, przez
silnik Tesseract uruchamiany na Twoim komputerze. Rozpoznany tekst pojawia się
w oknie aplikacji i trafia do pliku tylko wtedy, gdy sam wybierzesz eksport do
TXT lub DOCX i wskażesz miejsce zapisu.

Aplikacja zapisuje na dysku wyłącznie:

- ustawienia interfejsu (motyw jasny/ciemny/systemowy oraz język PL/EN),
- pobrane pliki językowe OCR i słowniki pisowni,
- słowa, które sam dodasz do własnego słownika pisowni,
- tymczasowe pliki robocze potrzebne w trakcie rozpoznawania, usuwane po
  zakończeniu operacji.

Dane te znajdują się w folderze danych aplikacji na Twoim urządzeniu i nie
opuszczają go.

## Połączenia internetowe

Studio OCR łączy się z internetem **wyłącznie wtedy, gdy sam o to poprosisz** —
klikając przyciski instalacji silników, języków OCR lub słowników pisowni.
Pobierane są wtedy publicznie dostępne pliki z następujących źródeł:

- silnik Tesseract OCR — `digi.bib.uni-mannheim.de`,
- Ghostscript — `github.com/ArtifexSoftware`,
- pliki językowe OCR — `github.com/tesseract-ocr/tessdata_best`,
- słowniki pisowni Hunspell — `github.com/wooorm/dictionaries`.

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
- nie korzysta z lokalizacji, kamery, mikrofonu ani kontaktów,
- nie wyświetla reklam i nie udostępnia niczego stronom trzecim.

## Uprawnienia w pakiecie

Pakiet ze Sklepu Windows deklaruje uprawnienie `runFullTrust`. Jest ono
wymagane technicznie dla klasycznych aplikacji desktopowych (Win32) i pozwala
programowi uruchamiać silnik OCR, korzystać ze skanera oraz zapisywać własne
pliki ustawień i słowników. Nie jest wykorzystywane do odczytu Twoich plików
ani do dostępu do danych innych aplikacji.

Instalacja silników Tesseract i Ghostscript z poziomu aplikacji uruchamia
oficjalne instalatory tych programów i wymaga potwierdzenia w oknie kontroli
konta użytkownika (UAC). Możesz też zainstalować je samodzielnie i pominąć
ten krok.

## Kod źródłowy

Aplikacja jest otwartoźródłowa (licencja MIT). Cały kod można sprawdzić pod
adresem <https://github.com/zetmar-collab/ocr-studio>.

## Kontakt

Pytania dotyczące prywatności: <https://github.com/zetmar-collab/ocr-studio/issues>
