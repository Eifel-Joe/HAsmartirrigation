# Review Task 2 — Stundenzeilen buchen nur gemessene Zeit (`d72c05d1..0d976997`)

### Spec Compliance

- ✅ Spec compliant. Die Diff-Zeilen entsprechen dem Plantext (Mechanik-Check des Controllers) und erfüllen dessen
  Anforderungen; die zwei freigegebenen Abweichungen sind wie beschrieben umgesetzt:
  - Gewicht-0-Zeile ist leer: nur `time`, `hour_start`, `hour`, `doy`, `coverage_h`, ggf. `tz_offset_h` und
    `precipitation` (`weather_aggregate.py:1293-1320`); beide Leser der Messfelder überspringen sie
    (`et_estimate.py:132-134`, `weather_aggregate.py:1065`, `:1107`).
  - Regenraten-Zuwachs wird an den Sperrgrenzen geteilt und landet am Ende seines gemessenen Teils
    (`weather_aggregate.py:907-925`); `TestRain` prüft Stunde 10 = 2/6, Stunde 11 = 0, Summe = Aggregat.
- Global Constraints geprüft:
  - Sperre halboffen: `_blocked_at` (`:679-681`, Basis) wird in allen neuen Stellen benutzt, keine eigene Vergleichslogik.
  - Pflichtmengen: `HOURLY_ROW_REQUIRED` öffentlich, `grep -rn "_HOURLY_ROW_REQUIRED"` über den ganzen Worktree (ohne `.git`) leer.
    Der Bericht hat recht: der alte Name stand nur in `weather_aggregate.py`, `et_estimate.py` kannte ihn nie (Hinweis im
    Brief ist dort ungenau).
  - `blocked=None` / `{}` / fremde Felder: `spans = blocked.get(key) if blocked else None` (`:1228`), `masked = {}` →
    `required_spans = []` → `booked = None` → `coverage_h` bleibt `coverage`; `_books_nothing` ist bei `coverage > 0`
    (garantiert durch `:1289-1292`) nie wahr; `_precip_increments(spans=None)` fällt in den alten Zweig. Pfad für
    *behalten* bleibt unverändert; `TestFieldsWithoutSpans` vergleicht mit `==` (leeres Dict, fremdes Feld).
  - Kein Store-Feld, keine Übersetzung, keine Verweise auf Issues/Kürzel in den hinzugefügten Zeilen
    (grep über die `+`-Zeilen des Diffs: leer).
- ⚠️ Nicht aus dem Diff prüfbar (gehört in spätere Tasks / Gesamtreview):
  1. Beide Aufrufer, `calculation.py:1001` und `live_estimate.py:762`, übergeben `blocked` noch nicht; das neue Verhalten
     ist produktiv noch nicht erreichbar. Ende-zu-Ende-Beleg kommt erst mit der Verdrahtung.
  2. `build_substeps` ruft `_precip_increments` (`weather_aggregate.py:1447`) noch ohne `spans`. Der Abgleich
     `calculation.py:1069` (Toleranz relativ 1e-6) hält für gesperrte Regenraten erst, wenn der spätere Task `spans`
     dort durchreicht. Die Rundung ist unkritisch: Zuwächse summieren je Segment, `_riemann_over` je Paar, Abweichung im
     Bereich 1e-16.
  3. `build_hourly_rows` nimmt `start`/`end` aus `_effective_series`; `zone_blocked_spans` schneidet die Spannen auf das
     Fenster des Aufrufers. Beide müssen Wasserzeichen und `now` teilen — Sache der Aufrufer in den späteren Tasks.
  4. Der Parameter `mask` von `_masked_hold_table` (`:803`) wird in diesem Commit nirgends benutzt und nicht getestet;
     laut Plan verbraucht ihn ein späterer Task (Plan Z. 1548-1553).

### Strengths

- Eine Wahrheit für die Haltegeschichte: `_masked_hold_table` folgt wörtlich den Regeln von `_aggregate_blocked`
  (Zeile in Sperre fällt weg; nie in eine Sperre halten; danach gilt der Wert von davor; vor der ersten Probe gilt die
  erste). Ich habe das gegen `_held`/`_valid_segments`/`_blocked_at` (`:632-691`) nachgerechnet: gleiche Halboffenheit,
  gleiche Randregel. Stückweise Konstanz ist korrekt, weil jede Probe und jede Sperrkante ein Schnittpunkt ist
  (`:826-831`), und `_masked_upto` greift nie über `points[-1]` hinaus.
- Der Pfad für ungesperrte Felder ist unberührt: `continue` vor `_hold_integral_table`, gesperrte Felder laufen in eine
  getrennte `masked`-Tabelle. Keine Fließkomma-Reihenfolge ungesperrter Felder verändert sich.
- Das Fehlermodell ist sauber getrennt: „nie gelesen“ → `None` → Tagesform wie heute; „alles in Sperre“ →
  `masked[key] is None` → `booked = []` → Zeilen mit Gewicht 0, kein `KeyError` (`:1254-1258`); beide Fälle haben einen Test.
- Die zwei Leser der Messfelder sind vollständig erfasst: ich habe die Fundstellen von `["temperature"|"humidity"|
  "wind_2m"|"solar_mj_h"]` im Paket durchsucht — außer in `eto_hourly_series` und `_row_rso_eq36` (nur von
  `_ratio_hold_solar` aus erreicht) liest niemand diese Felder. Beide sind abgesichert.
- `_ratio_hold_solar` wird mit leerem `solar_samples` nicht gerufen (`if solar_samples:`, `:1347`), `next(...)` ist durch
  `if not measured: return` geschützt — also auch dann sicher, wenn die Sonne komplett in der Sperre liegt.
- Tests prüfen Verhalten, nicht Mocks, und Kanten mit Handrechnung in den Docstrings (23,5 / 15,0 / 20 Minuten). Mehrere
  Mutationen werden bemerkt: `_overlap_hours` ohne `max(0.0, …)` (Teilstunde 0,75), Weglassen der beiden
  `_books_nothing`-Wächter in `_ratio_hold_solar` (`KeyError` auf `temperature`), `booked = []` bei leerer Tabelle,
  Landung des Regenzuwachses am Anfang statt am Ende des gemessenen Teils.
- Kommentare erklären Wurzel und Gründe (Rain landet am Ende; warum die Quote über eine leere Stunde getragen wird).

### Issues

#### Critical (Must Fix)
Keine.

#### Important (Should Fix)
Keine.

#### Minor (Nice to Have)

1. **Randprobe der Sonne zählt als „gelesene Stunde“ und Quotenquelle, auch wenn das Fenster in der Sperre beginnt**
   (plan-vorgegeben, wörtlich so im Probe-Commit) — `weather_aggregate.py:1233-1238`. Der Filter `t <= start or not
   _blocked_at(t, spans)` behält die Randprobe (auf `start` geklemmt) auch dann in `solar_samples`, wenn `start` in einer
   Sperre liegt. Spec §2.2 verlangt: Randzeile bleibt als Wert, zählt als Probe nur, wenn der Fensterstart gültig ist;
   §2.3/G5: Proben in der Sperre zählen weder als `newest` noch als `measured`. Fürs *Halten* ist `t <= start` richtig
   (`_masked_hold_table`, `_precip_increments`, wie `_aggregate_blocked`); für `solar_samples` nicht.
   Fehlerbild: Sperre `(03:00, 03:30)` für die Sonne, Fensterstart 03:10 (jedes Folgefenster einer lang anhaltenden
   Sperre beginnt in ihr), keine weitere Sonnenzeile in Stunde 3 (Totband): Stunde 3 gilt als „eigene Messung“
   (`newest[3]`), wird nicht aus der Quote nachgefüllt, und die Randprobe liefert die Quote für spätere Leerstunden.
   Wirkung klein (der gehaltene Wert ist derselbe), aber der Pfad ist nur über Zeilenenden erreichbar, die kein Test
   berührt: `test_the_dead_sensors_boundary_value_is_never_priced` hat nur gesperrte Stunden 0-2 (`_books_nothing`) und echte
   Zeilen ab 03:00. Wer den Wortlaut ändern will: Filter einfach `not _blocked_at(t, spans)` für `solar_samples`.
   Der Mensch entscheidet, weil der Plan den Wortlaut vorgibt.

2. **Spannen-Sortierung über Felder nicht festgenagelt** — `weather_aggregate.py:1258`. `sorted(required_spans)` ist
   tragend (`_valid_segments` setzt sortierte, hier aus mehreren Feldern gemischte Spannen voraus; bei ungeordneter Eingabe
   würde z. B. Feld A 12:00-13:00 vor Feld B 10:00-11:00 B als gültig durchlassen). Der einzige Test mit zwei gesperrten
   Feldern (`test_two_fields_silent_in_different_parts_of_one_hour`) hat T vor RH in der Reihenfolge von
   `HOURLY_ROW_REQUIRED`; die Mutation „`sorted` weglassen“ überlebt. Ein zusätzlicher Test mit umgekehrter Reihenfolge (und
   einer sich überlappenden Sperre zweier Felder) nagelt es fest.

3. **Regen in einer buchungslosen Stunde ungetestet** — `weather_aggregate.py:1316-1317`. Kein Test kombiniert ein
   gesperrtes Pflichtfeld mit einem Regenfeld; das Streichen der `precipitation`-Zuweisung im `_books_nothing`-Zweig
   bliebe unbemerkt. Das ist eine tragende Entscheidung (Regen aus einem lebenden Messer fällt in eine ET-gesperrte
   Stunde und muss in der Zeile stehen, sonst gleicht die Zeilensumme nicht dem Aggregat). Heute liest zwar niemand im
   Paket `row["precipitation"]` (Suche im Paket), aber die Spec-Zeile „Summe gleicht dem Aggregat“ lebt genau hier.

4. **Aufbewahrungsregel viermal verstreut** — `weather_aggregate.py:632` (Basis), `:822`, `:909`, `:1236`
   (`t <= start or not _blocked_at(t, spans)`). Spec G12 nennt „ein Helfer liefert … behaltene Proben“. Ein
   `_kept_samples(samples, spans, start)` hätte Punkt 1 verhindert (die Randregel stünde an einer Stelle) und ist bei der
   nächsten Regeländerung die Stelle, an der die Kopien auseinanderlaufen. Nicht blockierend.

5. **`_precip_increments(spans=…)` ohne `start`/`end` bricht mit `TypeError`** — `weather_aggregate.py:885`, `:909`
   (`t <= None`). Die Signatur macht `start`/`end` optional, der Zweig braucht sie. Kein Aufrufer in diesem Commit
   betroffen (`build_hourly_rows` übergibt alle drei); ein späterer Aufrufer kann hineinlaufen. Keyword-only
   Pflicht, wenn `spans` gesetzt ist, oder `assert`/`raise`, wäre ehrlicher.

6. **Kleine Testlücken, jeweils ohne akutes Risiko:** (a) kein Fenster, das nicht auf der vollen Stunde beginnt/endet,
   zusammen mit `booked` (Randstunden werden von `_overlap_hours(booked, a, b)` korrekt geklemmt, aber ungeprüft);
   (b) kein Test mit `tz` ≠ `None` auf einer leeren Zeile (`tz_offset_h` wird vor dem `_books_nothing`-Zweig gesetzt);
   (c) `_precip_increments`: `len(kept) < 2 → None` und „Sperre bei Regenrate, aber nicht-`riemannsum`“ ohne Test;
   (d) `mask=` ohne Test in diesem Commit.

### Assessment

**Task quality:** Approved

**Reasoning:** Implementierung folgt der Spec, lässt *behalten*-Gruppen byte-identisch und ist in den Kernfällen (Teilstunde,
Schnittmenge zweier Felder, eingefrorener Wert in der Sperre, Quote nach der Sperre, Regenzuwachs) belastbar getestet. Die
Befunde sind Randfälle und Testlücken; Punkt 1 ist eine plan-vorgegebene Randabweichung zur Spec, die der Mensch entscheidet.

### Gelesen / geprüft (Belege)

- Diff komplett gelesen; zusätzlich Basis-Code zur Gegenprobe der Haltelogik: `weather_aggregate.py:560-730`
  (`_aggregate_blocked`, `_valid_segments`, `_blocked_at`, `_held`, `_riemann_over`), `:885-940`, `:1020-1120`,
  `:1275-1350`; `sensor_liveness.py:169-280` (Spannen sind je Feld sortiert, zusammengeführt und auf das Fenster
  geschnitten); `et_estimate.py:125-198`.
- Benannte Risiken und jeweilige Einzelprüfung: (1) weitere Leser der Messfelder → Suche im Paket, nur zwei;
  (2) Altname `_HOURLY_ROW_REQUIRED` → Suche im ganzen Worktree, leer; (3) weitere Aufrufer der geänderten Signaturen →
  Suche, nur `calculation.py:1001`, `live_estimate.py:762`, `weather_aggregate.py:1447`, keiner übergibt `blocked`/`spans`
  schon; (4) Abgleich-Toleranz → `calculation.py:1069`.
- Keine Tests gelaufen (Vorgabe). Frage an die RED/GREEN-Belege des Berichts (17 passed; `task_compare`: 0 neue FAILED,
  15 bekannte „Lingering timer“): keine offene.
