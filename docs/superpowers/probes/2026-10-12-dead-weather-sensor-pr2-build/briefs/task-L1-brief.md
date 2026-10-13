# Auftrag L1 — ein Satz je angezeigter Sperre (Befund aus dem Live-Test)

Lies zuerst `D:\Entwicklung\HASI\issue8-pr2-work\sdd\header.md` (Kontext, Regeln 1–10; Regel 9 entfällt hier, es gibt
keinen Probe-Commit). Worktree `D:\Entwicklung\HASI\issue8-pr2-work\wt`, Branch `feat/pause-silent-weather-sensor`,
HEAD `030e12a3`.

## Befund (Live-Test auf HA-Test, 2026-10-13)

Ein Gerät mit vier Feldern (Temperatur, Taupunkt, Wind, Druck) war stumm und kam zurück. Die Ausfall-Liste hat für alle
vier denselben Beginn (`2026-10-13T17:15:27.531578`), aber jedes Feld endet mit seiner eigenen Rückkehr:
`20:52:00.184966`, `.190707`, `.197112`, `.203012`. `calculation._silent_sensor_explanation` gruppiert die Felder nach
der exakten Sperre `(start, end)` und erzeugt deshalb vier Sätze, die minutengenau gleich aussehen:
„Keine Werte von Temperatur von 2026-10-13 20:15 bis 2026-10-13 20:52 (Sensor stumm). Keine Werte von Taupunkt von
2026-10-13 20:15 bis 2026-10-13 20:52 (Sensor stumm). …“. Gewollt (Spec: „Felder mit gleicher Sperre zusammengefasst“)
ist ein Satz, der alle vier nennt. Eine echte Station meldet ihre Felder nacheinander, das ist also der Normalfall.

## Änderung (nur `calculation.py`, Methode `_silent_sensor_explanation`)

- Nach der Sperre gruppieren, **wie der Satz sie zeigt**: Schlüssel = `(start.strftime(FMT), end.strftime(FMT))` mit
  `FMT = "%Y-%m-%d %H:%M"`; die Felder einer Gruppe als Menge (`set`), damit ein Feld mit zwei Sperren in derselben
  angezeigten Minute nicht doppelt genannt wird. Sortiert wie bisher (`sorted(fields_by_span.items())` — die
  formatierten Zeiten sortieren chronologisch), die Feldnamen innerhalb eines Satzes `sorted(fields)` wie bisher.
- Die Zeichenketten direkt einsetzen (`.replace("{start}", start)` usw.); das Format bleibt `%Y-%m-%d %H:%M`.
- Ein kurzer Kommentar an der Gruppierung: warum nach der angezeigten Sperre (die Felder eines Geräts kommen einzeln,
  Millisekunden auseinander, zurück; jede eigene Gruppe gäbe gleich lautende Sätze).
- Den Docstring-Satz „One per blocked span, the fields silent over the same span named together“ so anpassen, dass er
  „the same span as the sentence shows it“ sagt. Keine Wortlaute in den Sprachdateien ändern.

## Test zuerst (RED zeigen)

In `tests/test_silent_sensor_commit.py`, Klasse `TestTheExplanation` (Helfer und Stil der Klasse übernehmen):
- `test_fields_back_milliseconds_apart_share_one_sentence`: vier Felder (Temperatur, Taupunkt, Wind, Druck) mit gleichem
  Beginn und Enden, die sich nur in Millisekunden unterscheiden → genau **ein** Satz mit „(sensor silent)“ bzw. dem
  englischen Wortlaut der Testsprache, der alle vier Feldnamen nennt.
- `test_a_field_twice_in_one_shown_minute_is_named_once`: ein Feld mit zwei Sperren, die in derselben angezeigten Minute
  beginnen und enden → ein Satz, das Feld einmal genannt.
- RED auf dem heutigen Code: der erste Test findet vier Sätze, der zweite den Feldnamen zweimal (oder zwei Sätze).
- Die bestehenden Erklärungs-Tests bleiben grün (`test_each_span_gets_its_own_sentence` u. a. — zwei wirklich
  verschiedene Sperren bleiben zwei Sätze).

Testbefehl (Regel 2): `TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_silent_sensor_commit.py -p _local_socket_unblock -q`
(Teardown-ERROR „Lingering timer“ ist erwartet, Regel 3.)

## Commit

```
fix(calculation): fields back milliseconds apart share one silent-time sentence

A station's fields return one by one, milliseconds apart, so each field's
outage ends at its own instant. The explanation grouped fields by the
exact span and wrote one sentence per field, all reading the same at the
minute the sentence shows. Fields are now grouped by the span as the
sentence shows it, each named once.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

Lint (Regel 4), gezielt stagen, `git status --short` danach leer. Bericht nach
`D:\Entwicklung\HASI\issue8-pr2-work\sdd\task-L1-report.md` (RED/GREEN mit Befehl und Ausgabe, Lint, SHA).
