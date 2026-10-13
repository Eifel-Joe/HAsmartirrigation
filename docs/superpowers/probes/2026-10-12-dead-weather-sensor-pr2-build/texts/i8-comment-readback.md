## English

**PR 2 opened upstream as `JustChr#197` (2026-10-13)**: the cut in the daily path.

- A setting per sensor group, "When a sensor goes silent" (*Pause* / *Keep the last value*): every existing group keeps and stays byte-identical, new groups pause, as JustChr asked on `JustChr#188`.
- For a pausing group without the hourly calculation, the daily commit leaves a silent field's time out (outage start + 3 h to its end) and books ET only for the share in which the module's required fields were measured. Rain gauges are never cut. The notice and the zone's explanation say so; panel and docs in 8 languages.
- Built on `6a40e083` (upstream pre-release v2026.10.05): 18 commits, 106 new tests, 37/37 mutations killed, full suite clean by name. The final review asked for changes that were decided here: the paused notice only where a field is actually cut (a silent rain gauge alone keeps the plain text), and docs and notice warn about device-less sensors that report only on change.
- Live on HA-Test with pre-release v2026.10.13b1: the notice variants, the switch with the hourly calculation and the booked share (84 %, as computed beforehand) all held. The explanation wrote one sentence per field instead of one per span; fixed in the PR with tests, not re-checked live.
- production = pre-release v2026.10.13b1 (`77f041d2`, without that last fix). HA-Prod untouched (still v2026.10.05b1).

The label stays `upstream:freigegeben`; this issue stays open for PR 3 (hourly path and live estimate).

## Deutsch

**PR 2 upstream als `JustChr#197` eröffnet (2026-10-13)**: der Schnitt im Tagespfad.

- Eine Einstellung je Sensorgruppe, „Wenn ein Sensor verstummt“ (*Pausieren* / *Letzten Wert behalten*): Jede bestehende Gruppe behält und bleibt byte-identisch, neue Gruppen pausieren, wie JustChr auf `JustChr#188` verlangt hat.
- Für eine pausierende Gruppe ohne Stundenrechnung lässt der Tages-Commit die Zeit eines stummen Feldes aus (Ausfallbeginn + 3 h bis zum Ende) und bucht ET nur für den Anteil, in dem die Pflichtfelder des Moduls gemessen wurden. Regenzähler werden nie geschnitten. Hinweis und Erklärung der Zone sagen das; Panel und Doku in 8 Sprachen.
- Gebaut auf `6a40e083` (upstream-Pre-Release v2026.10.05): 18 Commits, 106 neue Tests, 37/37 Mutationen getötet, volle Suite namensgleich sauber. Die Abschluss-Review verlangte Änderungen, die hier entschieden wurden: der Pause-Hinweis nur, wo wirklich ein Feld geschnitten wird (ein stummer Regenzähler allein behält den normalen Text), und Doku und Hinweis warnen vor gerätelosen Sensoren, die nur bei Wertänderung melden.
- Live auf HA-Test mit dem Pre-Release v2026.10.13b1: die Hinweis-Varianten, der Wechsel mit der Stundenrechnung und der gebuchte Anteil (84 %, vorab gerechnet) stimmten. Die Erklärung schrieb einen Satz je Feld statt je Sperre; im PR mit Tests behoben, live nicht nachgeprüft.
- production = Pre-Release v2026.10.13b1 (`77f041d2`, ohne diese letzte Korrektur). HA-Prod unberührt (weiter v2026.10.05b1).

Das Label bleibt `upstream:freigegeben`; dieses Issue bleibt für PR 3 (Stundenpfad und Live-Schätzung) offen.

