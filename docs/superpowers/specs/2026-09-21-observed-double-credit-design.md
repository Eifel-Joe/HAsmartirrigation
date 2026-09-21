# Observed-Doppelgutschrift: SI übernimmt ein bereits extern offenes Ventil

Datum: 2026-09-21 · Arbeitseinheit **PR A** aus `ToDo.md`, Abschnitt „🎯 Arbeitsreihenfolge — verbindlich ab
2026-09-21" (Schwere hoch, Größe M, auf HA-Prod scharf)
· Basis `upstream/master` = `965a4f9d` („fix(pyeto): the solar-radiation default is the one it declares (#158)")
· Arbeitsbranch `fix/observed-credit-si-takeover`
· Vorbestand der Suite auf der Basis: siehe `D:/Entwicklung/HASI/prA-work/baseline-965a4f9d.txt`

**Zeilenangaben** gelten für `965a4f9d`, sofern nicht anders vermerkt.

**Quellen.** Karte des Codes: Workflow `wf_323d2029-909` (6 Leser + 6 Gegenprüfer, nur lesend, 70 Urteile —
63 bestätigt, 1 kassiert, 6 teilweise). Das kassierte Urteil war eine Zählfehler-Überschrift (`_observed_on_since`
hat fünf Fundstellen, nicht vier). Die sechs Teilurteile korrigierten Überspitzungen in hypothetischer Arithmetik
und Testzählungen, keine tragende Aussage. Eine Korrektur ist in diese Spec eingearbeitet: `run_watch.py:823`
hängt an einer **eigenen** Zustandswechsel-Anmeldung (`run_watch.py:593`), nicht an derselben wie der Observer.
Alle für den Fix tragenden Stellen sind zusätzlich von Hand nachgelesen.

---

## 1. Problem

Das experimentelle Observed-Watering (`observed_watering.py`) beobachtet je Zone die verknüpfte Ventil-Entität
und schreibt dem Eimer Wasser gut, das **außerhalb** des Irrigation-Plus-Läufers geflossen ist. Damit SI die
eigenen Läufe nicht doppelt bucht, gibt es eine Sperre — aber sie sitzt **ausschließlich an der Öffnen-Flanke**:

```python
# observed_watering.py:126, :138-140
if new_on and not old_on:
    if self.zone_run_in_flight(zone_id) or self.hass.loop.time() < (
        self._si_driven_until.get(zone_id, 0.0)
    ):
        return
    self._observed_on_since[zone_id] = dt_util.utcnow()
```

Die Schließen-Flanke hat **kein** SI-Prädikat. Sie entscheidet allein danach, ob ein Marker liegt:

```python
# observed_watering.py:157-172
elif old_on and not new_on:
    started = self._observed_on_since.pop(zone_id, None)
    measured, sensor_present = self._observed_finish_flow(zone_id)
    if started is None:
        return
    seconds = (dt_util.utcnow() - started).total_seconds()
    self.hass.async_create_task(self._credit_observed_watering(...))
```

**Die Wurzel:** trifft ein SI-Dispatch auf ein Ventil, das **schon extern offen ist**, entsteht *keine*
Zustandsflanke — das einzige Tor wird also nie befragt. Der Marker aus dem externen Öffnen überlebt in den
SI-Lauf hinein, und beim Schließen wird die ganze Spanne extern+SI ein zweites Mal gutgeschrieben, zusätzlich
zur Gutschrift des Läufers.

```
T0 extern auf ──── T1 SI-Dispatch ──── T2 SI-Lauf fertig ──── T3 Ventil zu
   |                                    ^ Läufer schreibt gut
   └──────────── Observer schreibt T0→T3 gut ──────────────────┘
```

SI läuft ohne jede Beschwerde in dieses Szenario hinein: `_confirm_valve_running` akzeptiert ausdrücklich ein
Ventil, das beim ersten Lesen **schon an** war (`self_closing.py:501-512`, Docstring zu `_sc_valve_on_instant`:
„`_confirm_valve_running` accepts a valve that was ALREADY on at its first read, whose last_changed can be
hours old").

### 1.1 Wie scharf das ist

- **Zone ohne Flusssensor** (HA-Prod: Beet): voll scharf. `_sc_finish_run` schreibt den Eimer nur, wenn
  `measured is not None` (`self_closing.py:409-425`) — es gibt also nichts, was die Observed-Gutschrift
  überschriebe.
- **Zone mit Flusssensor**: heute **manchmal zufällig maskiert**. `_sc_finish_run` schreibt den Eimer absolut
  aus `RUN_PRE_BUCKET` (`self_closing.py:414-421`), und bei `T2 == T3` sorgt die 5-s-Entprellung des Watchers
  dafür, dass SI zuletzt schreibt und die Observed-Gutschrift still überschreibt. Sobald der SI-Lauf zuerst
  endet (`T2 < T3`), fällt die Maskierung weg und die Doppelgutschrift ist **unwiederbringlich**, weil SI
  bereits bei T2 abgerechnet hat.
- **`T2 < T3` ist bei Service-/Self-Closing-Zonen die normale Form**, nicht die Ausnahme: SI schließt dort
  nichts, das macht die Hardware; SI beendet den eigenen Lauf per Backstop bei `planned + grace`
  (`self_closing.py:746-748`, grace = 5 s Settle + 4 s Vorgabemarge = 9 s, `run_watch.py:304-309`).
  Hält jemand das Ventil länger offen, endet der SI-Lauf vor dem Ventil.
- **Zweite, unabhängige Quelle derselben Klasse:** `unavailable` zählt als Schließen-Flanke
  (`_ON_STATES = ("on", "open", "opening")`, `observed_watering.py:38`, Auswertung `:123-124`). Ein
  Zigbee-Flap `on → unavailable` mitten im SI-Lauf schreibt also schon heute `T_flap − T0` gut und leert den
  Marker — eine Teil-Doppelgutschrift, die ohne die `T2/T3`-Reihenfolge auskommt.

### 1.2 Was heute getestet ist

Nichts davon. Kein Test ruft `_note_si_valve`, während `_observed_on_since` für dieselbe Zone gesetzt ist;
`_observed_cancel_meter` wird von keinem Test erwähnt. Die zwei vorhandenen Nachbartests
(`test_experimental_features.py:300` und `:308`) prüfen ausschließlich die **Öffnen**-Flanke.

---

## 2. Anforderungen

1. Trifft ein SI-Dispatch auf ein bereits extern offenes Ventil, darf die spätere Schließen-Flanke **keine**
   Observed-Gutschrift planen.
2. Der Fluss-Sampler des externen Laufs muss dabei abgebrochen werden — kein hängender 15-s-Timer, keine
   Messung, die nirgends landet.
3. Die Lösung muss **alle acht Dispatch-Pfade** abdecken, ohne acht Änderungen.
4. Sie darf die Fensterverkleinerung am Laufende (`irrigation.py:1523`, `:1702`) nicht entwerten: ein *echt*
   externes Öffnen nach dem Lauf wird weiterhin verfolgt.
5. Sie darf in keinem vorhandenen Test einen `AttributeError` erzeugen.
6. Keine Verhaltensänderung an Verteiler-Member-Zonen.

---

## 3. Optionen

### Option 1 — Prädikat an die Schließen-Flanke kopieren (VERWORFEN)

Die Öffnen-Flanken-Bedingung (`zone_run_in_flight(...) or loop.time() < _si_driven_until[...]`) auch beim
Schließen auswerten.

**In zwei entgegengesetzte Richtungen falsch**, getrennt durch die Frage, ob das Ventil vor oder nach
`dispatch + run_seconds + 30` zugeht:

- Schließt es **pünktlich**, lebt der Marker noch (`irrigation.py:129-130`: `until = dispatch + run_seconds + 30`;
  eine Tuya-Meldung kommt 2–3 s spät, `const.py:887-888`). Das Prädikat greift → die echten externen Minuten
  **vor** dem Dispatch werden stillschweigend verworfen, ohne dass sie je wieder gutgeschrieben würden.
- Schließt es **später** — genau der Fall, für den dieser PR existiert —, ist der Marker abgelaufen und
  `zone_run_in_flight` falsch (der Datensatz wurde von `_sc_remove_run`, `self_closing.py:387`, entfernt).
  Das Prädikat greift **nicht** → die volle Spanne *inklusive des SI-Laufs* wird ein zweites Mal
  gutgeschrieben. Die Lücke ist nach oben **unbegrenzt**.

Zusätzlich erbt diese Form die Fensterlücke aus ToDo-Punkt ➀ und vergrößert sie: das Prädikat wird an der
Öffnen-Flanke bei Fenster-Elapsed ≈ 0 ausgewertet (Spielraum: die ganze Lauflänge), an der Schließen-Flanke
bei Elapsed ≈ `planned` (Spielraum: 30 s; nach einem Neustart nur `grace`, also 9 s — und **0 s** für einen
write-only-Datensatz ohne `confirm_entity`, `run_watch.py:306-307`, wo es auf **jedem** Schließen falsch wäre).

### Option 2 — Verwerfen beim Anspruch, in `_note_si_valve` (GEWÄHLT)

`_note_si_valve` verwirft zusätzlich den Observer-Marker und dessen Sampler. Die Frage lautet dort nicht
„läuft SI **gerade**?", sondern „hat SI dieses Fenster **übernommen**?" — und die ist zeitunabhängig
beantwortbar.

**Hausvorbild, wörtlich:** der Verteiler macht seit dem 2026-07-12 genau das, mit genau dieser Begründung
(`distributor.py:1113-1121`):

> the instant SI claims this distributor, drop any lingering FOREIGN observed-watering open stash. The
> close-edge race guard (`_dist_on_inlet_close`) already discards a stash seen while `active_cycle` is set, but
> that relies on a close edge being processed before the cycle clears the marker. Popping here at the atomic
> claim makes the SI-exclusion **structural (timing-independent)**.

### Option 3 — Am Laufende neu scharfstellen (VERWORFEN für diesen PR)

Zusätzlich zu Option 2 beim Finalisieren die Entität gegen `_ON_STATES` nachlesen und, wenn sie noch an ist,
`_observed_on_since` **und** den Sampler neu setzen — dann bekäme auch der Schwanz `T2→T3` seine Gutschrift.

Verworfen, weil: fünf verschiedene Laufende-Stellen (`irrigation.py:1509`, `:1691`, `:2149`,
`self_closing.py:_sc_finish_run`, `async_stop_self_closing`); das Neuscharfstellen muss **beide** Hälften der
Öffnen-Flanke reproduzieren, denn ohne `_observed_start_flow_sampling` liefert `_observed_finish_flow`
`(None, False)` und die Zone fällt auf Zeit × Durchsatz zurück — also genau die Phantom-offen-Klasse, die #95
geschlossen hat; auf klassischen Zonen wäre es bei einem langsam meldenden Ventil sogar schädlich
(`irrigation.py:1416-1426` warnt vor diesen Ventilen); und es erzeugt **zwei** `RUN_RESULT_OBSERVED`-Einträge
für einen physischen Hand-Lauf, was eine eigene Produktentscheidung zur Verlaufslogik verlangt.

---

## 4. Entscheidung

**Option 2.** `_note_si_valve` (`irrigation.py:115-131`) verwirft beim Anspruch auf das Ventil zusätzlich
`_observed_on_since[zone]` und ruft `_observed_cancel_meter(zone)`.

```python
zid = int(zone_id)
until = getattr(self, "_si_driven_until", None)
if until is not None:
    window = (run_seconds or 0.0) + SI_VALVE_SUPPRESS_MARGIN
    until[zid] = self.hass.loop.time() + window
pending = getattr(self, "_observed_on_since", None)
if pending is not None:
    pending.pop(zid, None)
self._observed_cancel_meter(zid)
```

Die spätere Schließen-Flanke fällt damit in den **schon vorhandenen, schon getesteten** Zweig: `started` ist
`None` (`observed_watering.py:158`), `_observed_finish_flow` findet nichts und gibt `(None, False)` zurück
(`:246-248`), und `:163-166` kehrt vor jeder Gutschrift zurück. Es braucht keine neue Logik an der
Schließen-Flanke.

### 4.1 Drei Festlegungen mit Begründung

**(a) `getattr`-geschützt.** `tests/test_metered_run.py:261/275/607`, `tests/test_self_closing.py:548` und
`tests/test_opensprinkler.py:81` bauen den Koordinator per `SmartIrrigationCoordinator.__new__`, setzen nur
`_si_driven_until` und lassen das **echte** `_note_si_valve` laufen; `_observed_on_since` setzt keiner von
ihnen. Ein Direktzugriff wäre dort `AttributeError`. `_note_si_valve` macht es für `_si_driven_until` schon
genau so (`irrigation.py:127`). `_observed_cancel_meter` braucht den Schutz nicht: `_observed_meters()` heilt
sich selbst über `getattr` (`observed_watering.py:176-181`), und die Methode kommt über den Mixin auch an
einer `__new__`-Instanz mit.

**(b) `int(zone_id)`.** Die Aufrufer liefern gemischt: `batch.py:330` und `self_closing.py:573` wrappen selbst,
`irrigation.py:1413/:1639/:2123` und `run_watch.py:823` reichen durch. Beide Ziel-Dicts sind auf `int`
geschlüsselt (`observed_watering.py:69`, `store.py` `ZoneEntry.id: int`). Ein Roh-Schlüssel würde bei einem
String still danebengreifen. `int()` steht heute schon in Zeile 130, wird jetzt einmal oben berechnet.

**(c) Kein `run_seconds > 0`-Gate.** Zwei der acht Aufrufe sind Schließ-seitige Nachjustierungen
(`irrigation.py:1523`, `:1702`), die **nach** dem eigenen `turn_off` des Läufers laufen. Dort ist das Verwerfen
nachweislich ein No-op: zu diesem Zeitpunkt steht der Marker noch auf `dispatch + max_seconds + 30`, bei
`real_flow` also auf dem stundenlangen Sicherheitsfenster — eine externe Öffnen-Flanke dazwischen wäre
unterdrückt worden und hätte gar keinen Marker gesetzt. Ein Gate wäre ein Zweig ohne erreichbaren Fall; der
Grund kommt stattdessen als Kommentar in den Fix.

### 4.2 Nebenwirkung, die gewollt ist

An `run_watch.py:823` (`_watch_observed_start`, Wieder-Nehmen des Markers für warteschlangen-gebundene Läufe)
wird der Fix **strikt besser**: sollte die Öffnen-Flanke dort je vor dem Bestätigen durchgekommen sein, räumt
der Anspruch den Marker nun weg. `_watch_observed_start` hängt an einer eigenen Anmeldung
(`run_watch.py:593`), die Reihenfolge gegenüber dem Observer ist also nicht garantiert — mit dem Fix ist sie
auch egal.

---

## 5. Ausdrücklich NICHT Teil dieser Arbeit

- **Kein Prädikat an der Schließen-Flanke** (Abschnitt 3, Option 1).
- **Kein Neu-Scharfstellen am Laufende.** Damit bleiben der externe **Kopf** `T0→T1` und, bei `T2 < T3`, der
  **Schwanz** `T2→T3` unbewertet. Das ist eine bewusste Unter-Gutschrift: der Eimer steht zu niedrig, SI gießt
  später mehr. Das Modul benennt diese Vorzugsrichtung selbst (`observed_watering.py:307-309`: „Water wasted is
  the milder failure than water withheld"), und der Verteiler hat denselben Verlust bereits akzeptiert. Gehört
  als NOT-TO-DO-Kommentar in den Fix und in den PR-Body. → ToDo-Nachtrag, Schwere **niedrig**, Größe M.
- **Kein Marker-Nachzug in `async_resume_self_closing_runs`** (ToDo-Punkt ➀). Kein Resume-Pfad ruft
  `_note_si_valve` — nicht `async_resume_self_closing_runs`, nicht `_os_resume_run`, nicht `_batch_resume_run`.
  Der Fix hängt am Dispatch und ist nach einem Neustart deshalb **kein** No-op, lässt aber **beide Grenzen**
  der Restdifferenz von ➀ unverändert. → Abschnitt 7.
- **Kein Verteiler-Code.** Member-Zonen haben einen eigenen Mechanismus, der `active_cycle` an **beiden**
  Flanken nachprüft (`distributor.py:839` und `:883`) und nie über `_note_si_valve` läuft.
- **Kein Ausschluss von Verteiler-Member-Zonen aus der Observer-Entitätskarte.** Der Gegenprüfer hat bestätigt,
  dass `observed_watering.py:56-69` — anders als der klassische Dispatch-Pfad (`irrigation.py:835`,
  `z.get(const.ZONE_DISTRIBUTOR_ID) is None`) — keinen solchen Filter hat und nichts ein übrig gebliebenes
  `linked_entity`/`observed_entity` einer Member-Zone löscht. Das ist ein eigener, theoretischer
  Konfigurations-Drift-Fund ohne belegten Auftritt, keine Doppelgutschrift. Notieren, nicht hier fixen.
- **Kein Frontend, kein dist, keine i18n.** Reiner Python-Fix ohne neue Zeichenkette.

---

## 6. Tests

RED vor GREEN, jeder Test mit einer Zusicherung, die heute fällt bzw. die der Fix festnagelt.

| # | Datei | Was gepinnt wird | Heute |
|---|---|---|---|
| **T1** | `tests/test_experimental_features.py` | Externes Öffnen verfolgt → `_note_si_valve` → Schließen-Flanke plant **keine** Gutschrift (`hass.async_create_task` nicht gerufen) | **RED**: eine Gutschrift |
| **T2** | `tests/test_observed_watering.py` | Der Anspruch bricht den laufenden Fluss-Sampler ab: Zone nicht mehr in `_observed_meters()`, Cancel-Handle gerufen | **RED**: Meter bleibt, Timer läuft |
| **T3** | `tests/test_experimental_features.py` | `on → unavailable` mitten im SI-Lauf schreibt nichts gut | **RED**: Teilgutschrift `T_flap − T0` |
| **T4** | `tests/test_experimental_features.py` | String-Zonen-ID verwirft den Marker trotzdem (Mutationsschutz für `int()`) | **RED** |
| **T5** | `tests/test_experimental_features.py` | **Regressions-Pin:** nach `_note_si_valve(zone, 0)` und abgelaufener 30-s-Marge wird ein echt externes Öffnen weiter verfolgt | grün, muss grün bleiben |

Gerüst steht bereits: `_observer_coordinator` (`test_experimental_features.py:201-231`) setzt `_si_driven_until`,
`_observed_on_since`, `_observed_zone_by_entity` und ein `hass.async_create_task`, das die Koroutine schließt
statt sie zu laufen — genau die Zusicherung, die T1/T3/T4 brauchen. `_sampler_coord`
(`test_observed_watering.py:166-179`) ist die einzige Vorrichtung mit echtem `_flow_build_meter` und trägt T2.
Zustandswechsel werden in beiden Dateien als `SimpleNamespace`-Attrappe direkt an `_observed_state_changed`
gegeben (`_event` bzw. `_state_event`), nicht über `hass.states.async_set`.

**Schwester-Pfad-Prüfung (globale Regel).** Geändert wird eine Funktion mit acht Aufrufern:
- `batch.py:330` (Batch) und `self_closing.py:573` (Service/Self-Closing **und** OpenSprinkler, geteilter
  Dispatch über `_sc_dispatch_open`, `self_closing.py:172-181`) laufen durch dieselbe Funktion → mit abgedeckt,
  keine eigene Änderung.
- `run_watch.py:823` → Abschnitt 4.2.
- `irrigation.py:1413` (klassisch, sequential+parallel), `:1639` und `:2123` (rotierend) → mit abgedeckt.
- `irrigation.py:1523` und `:1702` (Schließ-seitig) → No-op, Abschnitt 4.1(c), festgenagelt durch T5.
- Verteiler → eigener Mechanismus, Abschnitt 5.

**Testbefehl** (kanonisch, Projekt-`CLAUDE.md`):

```bash
./.venv/Scripts/python.exe -m pytest tests -p _local_socket_unblock -q
```

---

## 7. Ende-zu-Ende-Kriterium

**Automatisiert:** T1 fällt vor dem Fix und ist danach grün, bei unverändertem Vorbestand der vollen Suite
(FAILED-/ERROR-Namen `diff`-identisch zu `baseline-965a4f9d.txt`).

**Live auf HA-Test** (Sonoff-Emulator, Memory `hasi-sonoff-emulator-testsystem`): Ventil von Hand öffnen, bei
offenem Ventil einen SI-Lauf auf dieselbe Zone auslösen, auslaufen lassen. Beweis = **genau eine** Gutschrift
und **kein** `RUN_RESULT_OBSERVED`-Verlaufseintrag für dieses Fenster. Vorher zwei Einträge.

**HA-Prod** ist ein eigener, ausdrücklich freizugebender Schritt (Projekt-`CLAUDE.md`; Neustart nur mit
Freigabe, Memory `ha-no-auto-restart`).

**Nachmessung von ToDo-Punkt ➀** — nach dem Fix, nicht vorher abhaken. Konkretes Kriterium: nach einem Neustart
wird der Datensatz bei `planned + grace` finalisiert; kommt danach ein `off → on` der beobachteten Entität vor
dem echten Schließen und vor jedem neuen Dispatch, und ruft die folgende Schließen-Flanke noch
`_credit_observed_watering`, ist ➀ offen. Die Restdifferenz ist `30 − grace`: **21 s** bei Vorgabewerten,
**25 s** bei Marge 0, **30 s** für einen write-only-Datensatz ohne `confirm_entity`, **0 s** bei Marge 25 und
**−5 s** (Fenster nach Neustart länger) bei der Maximalmarge 30 (`const.py` `MAX_LATENCY_MARGIN_SECONDS`).
Ein Fix wäre ein Einzeiler neben `self_closing.py:1087`. → ToDo-Nachtrag, Schwere **niedrig-mittel**, Größe S,
auf Prod scharf.

---

## 8. Umsetzung

- Branch `fix/observed-credit-si-takeover` von `upstream/master` = `965a4f9d` (Memory `hasi-pr-build-recipe`).
- Kommentierung nach Skill `code-doku`: Wurzel, Fix-Logik, verworfene Alternativen (Option 1 und 3), Verweis
  auf den Verteiler-Präzedenzfall und auf die Tests.
- Die Docstring von `_note_si_valve` beschreibt danach beide Wirkungen, nicht nur den Marker.
- Lint vor jedem Push: `uvx black custom_components/irrigation_plus/` und
  `uvx ruff check custom_components/irrigation_plus/`.
- Design-Historie nach Regel P1 auf `archive/design-history`, **vor** dem PR und außerhalb des PR-Diffs.
  `docs/superpowers/` ist nicht gitignored — gezielt stagen, nie `git add .`.
