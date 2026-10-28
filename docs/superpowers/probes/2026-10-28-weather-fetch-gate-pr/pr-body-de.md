Titel: fix(weather): ein Abruf je Dokument zur selben Zeit, und eine Pause nach dem Fehlschlag

## Problem

Die Wetter-Clients prüfen ihren Zwischenspeicher ohne Sperre. Jeder Aufrufer, der beginnt, bevor die erste Antwort da ist, stellt seine eigene Anfrage, und ein Fehlschlag wird gar nicht gespeichert: Der nächste Aufrufer fragt sofort wieder, Pirate Weather dreimal ohne Pause (#196). Gemessen: 19 Anfragen in 0,6 s je Aktualisierung, 30 nach dem Speichern eines Zeitplans, und 5 505 + 552 Fehler in 46 Stunden einer `429`-Lage. Das ist der PR zu den drei Punkten, die du auf #196 erbeten hast.

## Fix

**1. Ein gemeinsamer Abruf.** Ein neues Modul `weathermodules/fetch_gate.py` setzt ein Tor vor jeden Abruf, der einen Zeitstempel setzt. Das sind sieben Stellen: OWM `get_data` und `get_forecast_data`, Pirate Weather `get_data` und `get_forecast_data`, Open-Meteo `_fetch`, Met Office `_fetch_hourly` und `_fetch_three_hourly`. Jedes Tor hat eine Thread-Sperre, und die Frische wird *innerhalb* der Sperre geprüft. Wer wartet, bekommt also den eben gefüllten Zwischenspeicher, statt selbst zu fragen. Die Clients laufen nur in Executor-Threads; deshalb eine Thread-Sperre, keine `asyncio`-Sperre. Die Ereignisschleife nimmt keine davon. Ein Tor je Zeitstempel statt je Client: Aktuelle Werte und Vorhersage bleiben unabhängig, und eine Pause auf der einen hält die andere nicht auf.

**2. Pause nach dem Fehlschlag, mit `Retry-After`.**
- *Fehlschlag* heißt: Ein Lauf hat abgerufen und keinen neuen Zeitstempel hinterlassen. Das deckt alle Formen ab, in denen die sieben Stellen heute scheitern (Ausnahme, `None` nach Nicht-200, `None` nach unvollständigem Dokument), ohne Liste von Codes oder Typen.
- *Länge:* 60 s, verdoppelt mit jedem weiteren Fehlschlag in Folge, höchstens das normale Cache-Fenster `max(cache_seconds, 60)`. Ein Erfolg setzt zurück. Begründung: 60 s legen die gemessenen Bündel vollständig zusammen und entsprechen der vorhandenen Untergrenze („at most one call per method per minute“). Durch den Deckel fragt ein Tor im Ausfall nie öfter als im Normalbetrieb. Bei festen 60 s wären es bis zu 1 440 Anfragen am Tag gegen 144 bei 10 min; Met Office erlaubt kostenlos 360 am Tag und hat zwei Tore.
- *`Retry-After`* (Sekunden oder HTTP-Datum) gilt als Untergrenze. Ist es länger als die Pause, zählt es, ein kürzeres hebelt die Pause nicht aus. Höchstens 24 h; unlesbar oder vergangen bleibt es ohne Wirkung. Die Pause zählt ab dem *Beginn* des gescheiterten Laufs, so wie der Zyklus; `Retry-After` zählt ab der Antwort, die es gesendet hat.
- *Was die Aufrufer in der Pause bekommen:* genau das Ergebnis des Fehlschlags. Das ist derselbe Rückgabewert, oder eine Ausnahme desselben Typs mit derselben Meldung (eine Kopie ohne den wachsenden Traceback). Es werden keine alten Werte weitergereicht, und der Fehlerweg jedes Aufrufers bleibt wie heute; der PR ändert nur die Zahl der Anfragen. Der Typ muss bleiben, weil `__init__.py` gezielt `OSError` fängt.
- *Logs:* Eine ERROR-Zeile eines Wetter-Clients heißt weiterhin: Es gab eine echte Anfrage, und sie ist gescheitert. Eine Wiedergabe steht auf DEBUG, mit dem Ende der Pause oder dem Hinweis, dass der Aufrufer den Fehlschlag abgewartet hat. Das gilt auch für die fünf Zugriffe von Open-Meteo und Met Office über dem Tor; ihr Rückgabewert ändert sich nicht. Die Logs der Aufrufer außerhalb von `weathermodules/` bleiben, wie sie sind, etwa die WARNING „No weather data to parse“.
- *Uhren:* Die Pause misst auf `time.monotonic()`, springt also weder bei der Zeitumstellung noch beim Stellen der Uhr. Die Frische-Prüfung bleibt auf `datetime.datetime.now()`, damit der Erfolgsweg unverändert ist.

**3. Pause zwischen den Versuchen von Pirate Weather:** 1 s, dann 2 s, nach dem letzten keine. Eine `429` (bei Pirate Weather „Monatskontingent erschöpft“) oder ein `Retry-After` beenden die Versuche sofort, denn ein zweiter Versuch nach 1 s kann nicht gelingen bzw. missachtete die Ansage. Sonst wie heute: drei Versuche, wiederholt nur bei Nicht-200, Netzfehler werden nicht wiederholt.

**Erfolgsweg unverändert**, wie erbeten: Frische, Untergrenze, Zeitstempel, Rückgabewerte und Log-Zeilen bleiben gleich. Neu ist nur, dass ein zweiter gleichzeitiger Aufrufer wartet und aus dem Zwischenspeicher bedient wird.

## Begleitende Änderungen

- Die Frische-Prüfung steht jetzt einmal in `fetch_gate.py`: die drei gleichen `_is_fresh`, die Inline-Prüfung von Open-Meteo, die eigene Lebensdauer-Rechnung in Met Office' `_forecast_document` und die vier `_MIN_CACHE_SECONDS`. Das ist der gemeinsame Helfer, den du genannt hast. Eine Basisklasse habe ich nicht eingeführt; die vier Clients bleiben unabhängig, und `_SESSION` bleibt in jedem Modul, weil vier Testdateien es dort patchen.
- `override_cache` umgeht wie heute den Zwischenspeicher und jetzt auch die Pause (ein gespeicherter Fehlschlag ist auch etwas Gespeichertes). `validate_key` bleibt außerhalb des Tors, damit ein korrigierter Schlüssel nicht die Pause des alten erbt.
- Der tote Ausdruck `i = i + 1` in Pirate Weathers Schleifen ist weg; die Schleifen liegen jetzt in einem gemeinsamen `_get_with_retries`.
- Kein Frontend, keine Bundles, keine Übersetzungen. Die Doku beschreibt weder Abrufe noch Wiederholungen und bleibt deshalb, wie sie ist.

## Nicht eingebaut — dein Ruf

- **Pirate Weathers `Ratelimit-Reset`** wird nicht gelesen. Es zählt bis zum Monatswechsel, nicht bis zur nächsten sinnvollen Anfrage. Mit dem 24-h-Deckel brächte es eine Anfrage am Tag statt einer je Cache-Fenster, und das auf einem schon erschöpften Schlüssel. Wenn du es willst, ist es eine Zeile im Tor.

## Abhängigkeiten

Keine. Basis ist der aktuelle `master`; kein anderer offener PR berührt `weathermodules/`.

## Tests

- **91 neue pytest-Fälle** in zwei neuen Dateien (`test_weather_fetch_gate.py`, `test_weather_clients_fetch_gate.py`); kein vorhandener Test ist geändert. Die beiden erbetenen Tests gibt es für **jedes der sieben Tore**: Gleichzeitige Aufrufer erzeugen genau eine Anfrage und bekommen dasselbe Ergebnis (ohne das Tor rot: 5 Anfragen bei 5 Threads). Nach einem Fehlschlag gibt es in der Pause keine Anfrage und dasselbe Ergebnis, danach wieder eine Anfrage; das gilt für Rückgabe `None` und für Ausnahmen (Typ und Meldung gleich). Dazu: Folge 60 → 120 → 240 s und Deckel, auch bei `cache_seconds = 0`. `Retry-After` in Sekunden, als HTTP-Datum, länger, kürzer, über 24 h, unlesbar, vergangen. Pirate `sleep(1)`/`sleep(2)` und `429` → ein Versuch. Keine Zeile über DEBUG bei einer Wiedergabe. Unabhängige Tore. Wartende hinter einem langsamen Fehlschlag teilen ihn. Die Pause zählt ab Beginn, `Retry-After` ab der Antwort.
- **16 Mutationen** der tragenden Prüfungen, jede gefangen: Sperre weg, Frische außerhalb der Sperre, Pause vor Frische, keine Verdopplung, kein Deckel, `Retry-After` als Obergrenze, `429` wiederholt, Wiedergabe auf ERROR, Pause ab Ende, Wartenden-Regel weg und weitere.
- **Volle Suite lokal** (Python 3.12, HA 2024.12): dieselben fehlschlagenden Tests nach Namen wie auf `master`, bestanden 4013 → 4104. `black` sauber, `ruff` sauber.
- **Live auf einer Test-Instanz** (Pirate Weather, 9 Zonen × 2 Zeitpläne, Aktualisierung 10 min):
  - je Zyklus **1** echter Vorhersage-Abruf statt 18; „Connection pool is full“ 0-mal statt 8-mal;
  - Zeitplan speichern bei abgelaufenem Zwischenspeicher: **1** Abruf statt 30;
  - Fehlschlag, erzeugt mit einer ungültigen Breite (95°), auf die Pirate Weather mit `400` antwortet: Läufe nur im Abstand 60/120/240/480/599 s, je Lauf eine ERROR-Zeile, gleichzeitige Aufrufer teilen den Fehlschlag (37 Wiedergaben). In 30 Minuten 9 ERROR-Zeilen über beide Tore, mehrere davon durch gezielte Nachfragen; vorher 6 057 in 46 Stunden.
  - Die erste Messung zeigte eine Kante: Die Pause zählte damals ab dem *Ende* des gut 3 s langen Laufs. Am Deckel kam der nächste 10-min-Zyklus deshalb 2 s zu früh, und ein dauerhaft gestörtes Tor fragte nur jeden zweiten Zyklus. Jetzt zählt sie ab dem Beginn. In der Nachmessung fragt das Tor am Deckel wieder in jedem Zyklus.
- **Nicht live belegt:** `Retry-After`, weil kein Dienst es nachweislich sendet; das ist nur im Test belegt. Die einzelnen Abstände 1 s und 2 s sind nur aus der Laufdauer erschlossen, weil das Anfrage-Log von `urllib3` den Schlüssel in der URL zeigen würde. Die Erholung *innerhalb* einer Pause: Das Zurückstellen lädt den Eintrag neu.

## Nebenbei gesehen, nicht in diesem PR

- Pirate Weathers `get_data` und `get_forecast_data` holen dieselbe Adresse und speichern getrennt; je Erneuerung sind das zwei Anfragen, wo eine reichte (Open-Meteo macht es mit einem Dokument).
- Der Projektions-Cache im Planer vervielfacht die Aufrufer. Nach diesem PR sind die 18 Aufrufe je Zyklus Treffer ohne Netzverkehr, aber weiterhin Executor-Aufträge.
- `override_cache` / `ATTR_OVERRIDE_CACHE` hat im Integrationscode keinen Nutzer.

Wenn du zu einem davon ein Issue willst, sag Bescheid.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
