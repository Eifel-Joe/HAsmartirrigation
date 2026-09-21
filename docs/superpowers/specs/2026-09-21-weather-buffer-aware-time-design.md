# Wetterpuffer in der Zone lesen, in der er geschrieben wurde

Datum: 2026-09-21 · Fork-Issue [`Eifel-Joe#22`](https://github.com/Eifel-Joe/HAsmartirrigation/issues/22)
· Upstream-Issue [`JustChr#160`](https://github.com/JustChr/HAsmartirrigation/issues/160)
· Basis `upstream/master` = `965a4f9d` („fix(pyeto): the solar-radiation default is the one it declares (#158)")
· Arbeitsbranch `fix/weather-buffer-aware-time`
· Frühere Bezeichnungen: `T` (Arbeitsreihenfolge vom 2026-09-21)

**Zeilenangaben** gelten für `965a4f9d`.

**Quellen:** Workflow `wf_13ff51c7-ac7` (6 Code-Leser über Schreiber/Leser/Speicherform/Tests/Blast/Doku,
84 Gegenprüfer, 4-Linsen-Urteilspanel; 94 Agenten, 0 Fehler, nur lesend). Journal:
`…/subagents/workflows/wf_13ff51c7-ac7/journal.jsonl`. JustChrs Freigabe und seine Detektionsfrage:
Kommentar auf [`JustChr#160`](https://github.com/JustChr/HAsmartirrigation/issues/160).

## Herkunft

`datetime.now()` ohne Argument liefert einen **naiven** Stempel in der **Prozess**-Zone.
`dt_util.now()` liefert einen **aware** Stempel in HAs **konfigurierter** Zone. Beide sind im
Store vertreten, und weil naiv-gegen-naiv nie wirft, ist die Naht nie aufgefallen.

JustChr hat die Konvention entschieden: `dt_util` aware, durchgängig HA-lokal.

### Der Befund, der die Aufgabe verschiebt

Die Schreiber waren **richtig**, die Leser sind falsch.

`calculation.py:765-775` sagt im eigenen Kommentar:

> Buffer stamps are naive LOCAL times, so the solar-time correction wants the local UTC offset.

und nimmt dann `tz = dt_util.DEFAULT_TIME_ZONE` / `offset = dt_util.now().utcoffset()` — also HAs
Zone, nicht die des Prozesses. Auf einem Container ohne `TZ=` (Prozess UTC) mit HA auf
Europe/Berlin bekommen echte-UTC-Stempel +2 h aufgeschlagen. Nach demselben Kommentar sind das
**0,26–0,74 % auf die tägliche ETo, aber +23,5 % / −16 % auf die Strahlung**, die der
Clearness-Ratio-Hold nachfüllt, weil Rso dort im Nenner steht.

Dieselbe Verwechslung in `sensor.py:605-621` (`replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)`),
`live_estimate.py:134-156` (`_parse_local_naive`) und `auto_calc.py:86-90`.

Gemessen (eigener Beleg, `.venv`-Python, kein Testfixture):

```
geschrieben (naiv, ohne Offset):  2026-09-21T12:00:00      # Prozess UTC
HA-lokales now (naiv):            2026-09-21T15:00:00      # Europe/Berlin
Fenster, das der Code rechnet:    3:00:00   <-- FALSCH
Fenster in Wirklichkeit:          1:00:00
Fehler:                           2:00:00   == UTC-Offset, konstant
```

Daraus folgt für die Migration: **„naiv = OS-lokal" ist nicht nur pragmatisch, sondern korrekt.**
Sie stellt den wahren Zeitpunkt wieder her. Bei unveränderter Prozess-TZ verschiebt sie null und
macht nur explizit, was ohnehin galt.

„Die Schreiber waren richtig" heißt **in sich stimmig**, nicht „bleiben, wie sie sind":
`calculation.py` vergleicht heute naiv-OS-lokal gegen naiv-OS-lokal, die Fensterlänge *innerhalb*
dieser Datei ist deshalb korrekt — auch auf einem falsch gestellten Container. Sie werden trotzdem
umgestellt (D2), weil JustChr die Konvention entschieden hat und weil ein aware Stempel seinen
Offset selbst trägt, womit die Fehlerklasse strukturell verschwindet statt nur verschoben zu werden.

## Entscheidung

### D1 — Ein gemeinsamer Coerce-Helfer, nicht vier Annahmen

Heute liegen vier fast identische Parser nebeneinander, jeder mit eigener naiv-Deutung:
`live_estimate._parse_local_naive` (macht aware → naiv platt), `sensor._to_aware_datetime`
(naiv → HA-lokal), `weather_aggregate._parse` (:102), `helpers.as_datetime` (:987).
Diese Streuung **ist** die Krankheit.

Neu in `helpers.py`, neben `as_datetime`:

| Eingabe | Ergebnis |
|---|---|
| `None` | `None` |
| ISO-String | `fromisoformat`, dann wie unten |
| naiv | `.replace(tzinfo=<Prozess-Zone>)` |
| aware | unverändert |

Die Prozess-Zone kommt aus einer eigenen winzigen Funktion, damit der Test sie injizieren kann
(siehe D5). `dt_util.DEFAULT_TIME_ZONE` wäre hier falsch — genau das ist der Leser-Bug.

### D2 — Schreiber auf `dt_util.now()`

Persistierende naive Schreiber:

- `calculation.py` 265, 377, 430, 492, 884
- `continuous_update.py` 252, 378, 521
- `__init__.py` 1429, 1506, 1516, 1632, 1644, 1799, 2023 (über den `dt_datetime`-Alias aus Zeile 11)
- `store.py:1633` (`last_consumed_at` beim Anlegen der Zone)
- `weather_aggregate.py` 337, 891, 1072 — `if now is None: now = datetime.datetime.now()`.
  Nicht persistiert, aber sie werden gegen gespeicherte Stempel verglichen; bleiben sie naiv,
  wirft jeder Aufruf ohne explizites `now` nach der Umstellung `TypeError`.

`__init__.py` ist der Schwester-Pfad, den das Issue nicht nennt: derselbe Defekt, eigener Aufrufer.
1506 ist das On-Demand-Einzelzonen-Update, 1632 der Intervall-Poll `_async_update_all`. Beide
gehören in denselben Commit.

### D3 — Migration, `STORAGE_VERSION` 14 → 15

Allowlist; Watermark **und** Puffer im selben Durchgang:

- `zones[i].last_calculated`, `.last_consumed_at`, `.last_updated`
- `mappings[i].data[j].retrieved`, `mappings[i].data_last_updated`

Unangetastet, weil bereits aware: `last_irrigation`, `run_log[].ts`, `pending_bucket_events[].ts`.

**Die harte Regel:** Watermark und Puffer wandern zusammen oder gar nicht. Eine falsche Annahme ist
dann eine *uniforme Translation der gesamten gespeicherten Zeitachse*; in `select_window`
(`weather_aggregate.py:152-165`, `rt > watermark`) kürzt sie sich restlos weg. Nur einen der beiden
zu migrieren ist der **einzige** Weg, Doppelzählung zu erzeugen.

Idempotent von selbst: HAs `JSONEncoder` schreibt `datetime.isoformat()` (verifiziert in
`homeassistant/helpers/json.py`), aware Stempel tragen also ein Offset-Suffix, naive nicht.
Ein zweiter Lauf findet nichts mehr zu tun.

### D4 — Keine Detektion. Die Annahme kommt in den Kommentar.

JustChrs Frage: Ein naiver Stempel ist nur eindeutig OS-lokal, solange die Prozess-TZ sich nicht
geändert hat. Wer erst `TZ` repariert und **dann** aktualisiert, dessen alte Stempel stammen aus
der alten Zone.

**Antwort: Eine datenbasierte Erkennung ist nicht teuer, sondern prinzipiell unmöglich.**

1. **DST-Kollision (entscheidend).** Beim Herbst-Übergang läuft die naive Folge im Puffer eine
   Stunde **rückwärts** — genau die Signatur, nach der ein Detektor suchen müsste. Die Bytes eines
   DST-Rücksprungs und eines Container-TZ-Fixes sind identisch. `calculation.py:766-772` sagt
   selbst, dass ein Fenster sieben Tage erreicht und einen DST-Übergang überspannen kann. Ein
   Detektor träfe damit jeden DST-Nutzer zweimal jährlich — mit **derselben Fehlergröße**
   (1 h = 4,2 % eines Tages), die er verhindern soll.
2. **Ein Zukunfts-Clamp wäre richtungsblind.** JustChrs eigenes Szenario (UTC → echte Zone,
   Offset steigt) schiebt Stempel in die **Vergangenheit**. Trefferquote: exakt 0 %.
   Zusätzlich falsch-positiv bei Boards ohne gepufferte RTC: die Migration läuft Sekunden nach
   dem Start, vor der NTP-Konvergenz — dann stünde der ganze Puffer „in der Zukunft".
3. **Paarung naiv gegen aware scheitert quantitativ.** Die unbekannte echte Lücke zwischen einem
   naiven Poll-Stempel und einem aware Lauf-Stempel geht 1:1 in die Schätzung ein und ist über
   eine Stunde annähernd gleichverteilt, während die gesuchte Größe auf Stunden quantisiert ist —
   Rauschen = Signal. Schlimmer: auf einer frisch eingerichteten Installation, also genau der, die
   gerade die TZ korrigiert hat, gibt es **null** aware Stempel (`store.py:256` `last_irrigation =
   None`, `run_log`/`pending_bucket_events` leer per `factory=list`).

**Der Restschaden ist klein und heilt garantiert.** `_hour_multiplier`
(`weather_aggregate.py:291-305`) gibt `diff/3600/24` zurück: ein Watermark-Fehler Δ erzeugt exakt
Δ/24 relativen Fehler auf **ein** Fenster. Δ = 2 h → 8,3 % eines Tages ETo, bei 3 mm/Tag rund
0,25 mm Eimer. Danach ist der Fehler strukturell unmöglich, weil jeder neue Stempel seinen Offset
selbst trägt. Der Zyklus ist erzwungen: Fixed-Time über `calctime` (Default 23:00) bzw. Before-Run
über `AUTO_CALC_MAX_LEDGER_AGE_HOURS = 24`.

Der Kommentar in der Migration nennt die Annahme **und die verworfene Alternative**, sonst
„repariert" ein späterer Leser sie auf `DEFAULT_TIME_ZONE`, um zu `sensor.py:621` zu passen.

**Kein Clamp.** `_window_bounds` (`weather_aggregate.py:197-214`) absorbiert Stempel nach `now`
bereits nicht-destruktiv (`end = max([now, *stamps])`, Docstring: „so a clock skew cannot yield a
negative-length window"). Das ist die etablierte Redewendung des Hauses; ein zweiter,
destruktiver Mechanismus daneben wäre schlechter als gar keiner.

### D5 — Die Naht wird an der geänderten Funktion gepinnt

`time.tzset()` existiert unter Windows nicht; die lokale Env ist Windows, CI ist Linux
(`CLAUDE.md`). Der Test darf deshalb nicht an `os.environ["TZ"]` hängen, sonst ist er lokal
dauerhaft geskippt und wir sehen RED/GREEN nie selbst.

Stattdessen liest der Helfer aus D1 die Prozess-Zone über eine eigene interne Funktion, die der
Test monkeypatcht. Läuft auf Windows und Linux identisch und ruft **genau** den geänderten Pfad
(Memory `verification-must-exercise-the-change`: vor jedem Beleg benennen, welche geänderte
Funktion die Prüfung aufruft).

## Leser (B)

Alle rufen den Helfer aus D1:

- `live_estimate.py` — `_parse_local_naive` (:134-156) gibt aware zurück; die Entkleidungen bei
  :204 (`"now": now.replace(tzinfo=None)`, geteilt über alle Zonen), :980 und :1400 entfallen
- `weather_aggregate.py:102` `_parse` delegiert
- `sensor.py:605-621` `_to_aware_datetime` delegiert, verliert seine eigene `DEFAULT_TIME_ZONE`-Annahme
- `calculation.py:45-70` `pending_bucket_events` macht aware **nicht** mehr platt — das Plattmachen
  existiert ausschließlich, weil das Fenster naiv war
- `weather_aggregate.py:970` Solargeometrie — **eigene Code-Änderung, nicht bloß ein Nebeneffekt.**
  `et_estimate.py:140` und `weather_aggregate.py:725` lesen den Offset aus dem Schlüssel
  `row["tz_offset_h"]`, nicht aus der tzinfo des Stempels; gefüllt wird er nur an `:970-972`, und
  zwar mit `tz.utcoffset(hour_start)` — „welchen Offset hat **HA** zu dieser Wanduhrzeit". Das ist
  die Verwechslung an ihrer teuersten Stelle. Nach der Umstellung ist `hour_start` aware
  (`:946` aus `_window_bounds`' `start`), also `row_offset = hour_start.utcoffset()`; `tz` bleibt
  reiner Fallback. `calculation.py:773` wird dadurch zum Skalar-Fallback und ändert nur den Kommentar.
- `auto_calc.py:88` Cutoff wird aware

## Ende-zu-Ende-Kriterium

Ein Store, dessen Stempel unter Prozess-TZ UTC geschrieben wurden, gelesen mit HA auf
Europe/Berlin:

1. Die Fensterlänge entspricht der echten verstrichenen Zeit (heute: 1 h wird als 3 h gerechnet).
2. Die Solarzeit-Korrektur nutzt den wahren Offset der Zeilen, nicht HAs.
3. Die volle Suite bleibt ohne Regression grün (bekannt rot unter Windows, auch auf unverändertem
   `upstream/master`: `test_panel.py::test_async_register_panel_static_path_config`, Pfadtrenner).

## Nicht Teil dieser Arbeit

- **(C)** Laufzeit-Check `datetime.now().astimezone().utcoffset()` vs. `dt_util.now().utcoffset()`
  als Warnung/Repair-Issue. Eigener PR: das ist unsere Zugabe zur Detektionsfrage, kein Teil des
  Fixes, und JustChr soll sie ablehnen können, ohne den Fix zu blockieren. Sie beantwortet die
  *bessere* Frage — nicht „hat sich die TZ geändert", sondern „weicht die Prozess-TZ **jetzt** von
  HAs Zone ab" — und fängt damit die ganze „Container ohne `-e TZ`"-Klasse dauerhaft.
- **(D)** Doku-Absatz `TZ=`. Geht **zuerst und unabhängig** raus; JustChr schreibt ihn sonst selbst.
- Jede Rekonstruktion der alten Zone, jeder Zukunfts-Clamp, jede Heuristik (siehe D4).
- `services.py:273/289` und `watering_calendar.py:79/93` (`generated_at`): reine Anzeigewerte,
  erreichen den Store nicht.
