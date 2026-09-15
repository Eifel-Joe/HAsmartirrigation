# Finish-Backstop mit Wartezeit: der Watcher darf ein normales Laufende abschließen

Datum: 2026-09-15 · Upstream-Issue [#139](https://github.com/JustChr/HAsmartirrigation/issues/139)
· Basis `upstream/master` = `4e53caf4` · Arbeitsbranch `fix/backstop-grace`
· Form entschieden von JustChr ([issuecomment-5667625952](https://github.com/JustChr/HAsmartirrigation/issues/139#issuecomment-5667625952)), wir bauen.

Alle Zeilenangaben gelten für `4e53caf4`. **Nachtrag 2026-09-15 abends:** upstream hat #144/#145
gemergt und v2026.09.16 veröffentlicht (`0b418644`); die Arbeitsbasis ist jetzt `0b418644`. Betroffen
sind nur Zeilenangaben in `const.py` hinter ~Zeile 701 (neuer `FORECAST_DAY_*`-Block) und die
Versionsdateien; keine der hier genannten Funktionen hat sich geändert. JustChr hat mit
[#147](https://github.com/JustChr/HAsmartirrigation/issues/147) bis zum nächsten stabilen Release auf
„nur Fixes und Tests“ umgestellt; #139 läuft als Fix weiter, mit der Bitte, die Marge auf das zu
beschränken, was der Fix braucht. Die vier abtrennbaren Zusätze (Zeitfenster-Preis, Observed-Sperre,
Backstop mit gespeicherter Aus-Meldung, Stopp-Anker) werden deshalb vor dem PR auf #139 zur Wahl
gestellt (User-Entscheidung) und bleiben im Plan je ein eigener Commit. Karte des Codes: Workflow `wf_6e62f6f5-88b`
(7 Code-Leser, 5 Gegenprüfer, Vollständigkeitsprüfung, Recorder-Leser auf HA-Prod, nur lesend).

## Herkunft

Ein Service-Lauf mit `confirm_entity` hat zwei Wege zum Abschluss:

- **Watcher:** das Ventil meldet „aus“, nach `finish_settle_seconds` = 5 s Entprellung
  entscheidet `_watch_finish` (`run_watch.py:772-831`).
- **Backstop:** `_sc_schedule_cleanup(zone_id, planned_seconds)` (`self_closing.py:414-429`,
  scharf bei `:629`), ohne jeden Zuschlag.

Der Backstop kommt immer zuerst. Er ruft `_sc_finish_run`, das über `_os_cancel_watch`
auch die laufende Entprellung abbricht (`self_closing.py:348`, `run_watch.py:311-324`), und
schreibt `completed` mit `actual_s = planned_s` (`self_closing.py:385`).

### Messungen HA-Prod (Recorder, 10 Tage Aufbewahrung, alle Zeiten HA-Host-Uhr)

| Zone | Lauf | Ventil offen | Fenster | Backstop − Aus | Confirm-Schwanz |
|---|---|---|---|---|---|
| Beet (Tuya, Minuten) | 09.09. | 542,83 s | 540 | −39,94 s | 0,892 s |
| Beet | 10.09. | 302,35 s | 300 | −36,43 s | 0,912 s |
| Beet | 11.09. früh | 302,08 s | 300 | −38,18 s | 0,896 s |
| Beet | 13.09. (nach `e9f2da51`) | 422,90 s | 420 | **−2,03 s** | 0,863 s |
| Kirschlorbeer (SONOFF, Sekunden) | 11.09. | 2299,41 s | 2299 | +0,57 s | 0,973 s |
| Kirschlorbeer | 13.09. | 1118,33 s | 1119 | +1,13 s | 0,461 s |

- Beet schließt 2,08–2,90 s nach seinem Fenster (Gerät schließt ~62 s nach dem letzten
  Minuten-Tick). Der Backstop kam in allen vier normalen Läufen vor der Aus-Meldung.
- Kirschlorbeer meldet innerhalb ±0,7 s um Ein + geplant; der Backstop feuert 0,57/1,13 s
  nach „aus“, also mitten in die 5-s-Entprellung.
- Kirschbaum: kein Lauf im Aufbewahrungsfenster.
- Der einzige Watcher-Abschluss dieser Anlage (erzwungener Stopp 11.09. 16:26) kam bei Aus + 5,009 s;
  `actual_s` 113,98 gegen 109,89 s offen = +4,09 s.
- Backstop-Scharfschaltung liegt ~4 ms nach `RUN_STARTED`.
- Keine `unavailable`-Episode überlappt einen Lauf (alle Episoden treffen alle drei Ventile
  gleichzeitig = Neustart-Muster).

## Wurzel

1. Backstop ohne Zuschlag (`self_closing.py:629`, Neustart `:867`).
2. `actual_s` wird nicht am Aus-Übergang gemessen: `_watch_finish` liest `elapsed` erst in
   `_decide` nach der Entprellung (`run_watch.py:823`), `async_stop_self_closing` liest es
   noch einmal selbst (`self_closing.py:764`). Ein abgeschlossener Lauf verwirft es ganz
   (`self_closing.py:385`). Der +4-s-Versatz existiert deshalb nur in Teil-Läufen.
3. Startseite: `RUN_STARTED` wird nach `_confirm_valve_running` gestempelt
   (`self_closing.py:535` → `:587`), der Confirm pollt im 1-s-Takt (`irrigation.py:725-767`).

## Anforderungen (JustChr, #139)

1. Backstop = geplantes Fenster + `finish_settle_seconds` + Latenz-Marge je Zone, nur für
   Läufe mit bestätigtem `RUN_WATCH_ENTITY`; ohne `confirm_entity` exakt beim Fenster.
2. `actual_s` am Aus-Übergang; die Entprellung entscheidet nur, OB der Lauf endete.
3. Startseite nach unserer Wahl mit Recorder-Daten.
4. Überall, wo der Backstop scharf wird, dieselbe Marge (genannt: `_watch_resume`, Neustart).
5. Nur Service-Policy; Batch und OpenSprinkler unberührt, im PR benannt.
6. Zonenfeld → Panel, Übersetzungen in 8 Sprachen, dist unter Node 22 (wie #125).
7. Tests, je mutationsgeprüft: Schluss in der Marge → `_watch_finish` mit `actual_s` =
   beobachtetes Fenster; verpasster Schluss → Backstop; write-only unverändert;
   Pause/Resume trägt die Marge.
8. Default-Marge aus unseren Messungen; PR-Text listet jede nicht abschaltbare Änderung mit
   Reichweite.

### Befunde gegen die Vorgabe (im PR-Text mit Beleg erklären, nicht vorab auf #139 — User 15.09.)

- **Zu 4/7:** `_watch_resume` (`run_watch.py:744-762`) ist für Service-Läufe unerreichbar. Es
  wird nur aus `_watch_evaluate` gerufen, wenn `policy.segmented` (`run_watch.py:602-604`);
  `SERVICE_WATCH_POLICY.segmented=False` (`self_closing.py:56`). `_watch_pause` braucht
  `_watch_paused`, das nur Batch für Batch-Läufe überschreibt (`batch.py:415-416`). Eine Marge
  dort änderte nur Batch. Service-Backstops werden genau an zwei Stellen scharf: Dispatch
  (`self_closing.py:629`) und Neustart (`:867`). Der Pause/Resume-Test wird deshalb ein
  Neustart-Test plus ein Pin, dass die Batch-Wiederaufnahme unverändert `remaining` plant.
- **Zu 6:** Der Backend-Katalog `translations/*.json` hat nur `config`, `options`, `services`,
  `entity`, `issues` — keinen Bereich für Zonenfelder. #125 (`0e0bb5d1`) änderte nur die
  Panel-Sprachdateien, ebenso #47/#57. Es gibt also genau einen Katalog für dieses Feld.

## Entscheidungen (User, 2026-09-15)

- **E1 Startpunkt und Toleranz:** eigenes Laufdatenfeld mit der Ein-Meldung des Ventils;
  `RUN_STARTED` bleibt. Toleranz zwischen abgeschlossen und Teil-Lauf = max(1 s, Marge).
  Grund: ab `RUN_STARTED` gemessen wäre Kirschlorbeer 13.09. ein Teil-Lauf
  (1117,87 + 1 < 1119: kein `irrigation_finished`, keine Kalibrierprobe, Etikett
  `self_closing_stopped`); ab Ventil-Ein mit 1 s blieben nur 0,33 s Luft.
- **E2 Default-Marge 4 s** (ganze Sekunden). Deckt die gemessene Notwendigkeit 2,03 s mit
  ~2 s und die rohe Tuya-Latenz 2,90 s mit 1,1 s.
- **E3 Wartezeit zieht alles mit:** In-flight-Fenster, Zeitfenster-Preis und Observed-Sperre.
- **E4 Neustart ohne gespeicherte Aus-Meldung:** Fenster = min(jetzt − Ventil-Ein, geplant).
- **E5 Abweichungen von der Vorgabe** im PR-Text erklären.
- **E6 Aus-Meldung nur direkt nach „an“** (nach dem Probelauf der Planung): siehe Abschnitt 1,
  `RUN_VALVE_OFF`.
- **E7 Neutrale Namen in neuen Test-Fixtures** (keine echten Zonennamen der Anlage in neu
  hinzugefügten Tests; vorhandene upstream-Namen wie „Beet“ bleiben).
- **Wortlaut** der 16 Panel-Texte und des Docs-Punkts freigegeben (Plan, Task 12).
- **HA-Test-Aufspielweg:** Fork-Pre-Release über HACS = `production` + `fix/backstop-grace`. Da die
  Basis `0b418644` #144/#145 (upstream gemergt) enthält, kommen diese mit (User-Entscheidung nach der
  Revision); #146 bekommt ein eigenes Pre-Release (Plan, Task 15).

„Wartezeit“ heißt im Folgenden `SERVICE_WATCH_SETTLE_SECONDS` (5) + Marge, bei Default 9 s.

## Design

### 1. Laufdaten (nur bestätigte Service-Läufe, beim Dispatch festgelegt)

Präzedenz `RUN_CEILING` (`const.py:931-939`, `self_closing.py:591`): ein Wert, der mitten im
Lauf nicht von einer Zonenänderung verschoben werden darf. Laufdatensätze sind rohe Dicts in
`Config.active_valve_runs`; neue Schlüssel überstehen Neustarts ohne Schema-Änderung
(`store.py:1086-1092`, `:1568-1579`; Schreiben über `_watch_update_run`, `run_watch.py:408-428`).
`RUN_SEGMENT_STARTED`/`RUN_WATERED_SECONDS` NICHT wiederverwenden — sie schalten den Lauf auf
segmentierte Behandlung (`run_watch.py:81-84`, `irrigation.py:386-400`).

- **`RUN_LATENCY_MARGIN`** — Marge der Zone beim Dispatch, auf 0–30 begrenzt.
- **`RUN_VALVE_ON`** — ISO-UTC. `hass.states.get(confirm_target).last_changed` direkt nach
  `True` aus `_confirm_valve_running`, begrenzt auf [`t_dispatch`, Confirm-Rückkehr].
  `t_dispatch` ist ein neuer `utcnow`-Stempel unmittelbar vor `_sc_dispatch_open`
  (`self_closing.py:496`). Ein vor dem Dispatch schon offenes Ventil
  (`irrigation.py:750-753` bestätigt beim ersten Lesen) bekommt so `t_dispatch` statt einer alten
  Meldung. `_confirm_valve_running` behält seine Rückgabe (drei weitere Aufrufer vergleichen
  `is False`: `irrigation.py:1405`, `:2106`, `distributor.py:1493`, dazu viele Test-Stubs).
  Präzedenz für einen geklemmten Hardware-Start: `opensprinkler.py:283-318`.
- **`RUN_VALVE_OFF`** — ISO-UTC der ersten Aus-Meldung seit dem letzten „an“, aus
  `new_state.last_changed` des Zustandsereignisses. HA übernimmt `last_changed`, solange der
  Zustandstext gleich bleibt (`homeassistant/core.py:2328-2330`); ein reines Attribut-Update
  eines schon „aus“-Ventils löst zwar `state_changed` aus und startet die Entprellung neu
  (`run_watch.py:784-785`), verschiebt den gespeicherten Wert aber nicht. Gesetzt nur aus einem
  Ereignis der Subscription, dessen VORHERIGER Zustand laufend war (`on`/`open`/`opening`) —
  wörtlich „erste Aus-Meldung seit dem letzten an“ (E6). Also NIE aus der ersten Auswertung beim
  Neuaufnehmen nach einem Neustart und NIE aus `unavailable`/`unknown`/fehlend → `off`: nach einem
  Neustart melden die Z2M-Ventile zuerst `unavailable`, und `last_changed` des folgenden
  `off`-Ereignisses ist die Wiederkehr der Entität, nicht der Schluss (`core.py:2321-2326`; auf
  HA-Prod belegt). Bewusst in Kauf genommen: `on → unavailable → off` mitten im Lauf speichert
  nichts, der Lauf wird dann nach E4 von der Uhr begrenzt (10 Tage Recorder: keine solche Episode
  während eines Laufs). Gefunden im Probelauf der Planung (Plan-Kritik, Befund „major“).
  Gelöscht, wenn der Watcher für den Lauf wieder einen laufenden Zustand sieht. Nicht vor
  `RUN_VALVE_ON`: ein Fenster < 0 wird 0.

`RUN_STARTED`, `RUN_OBSERVED_START` und damit Panel-Fenster (`irrigation.py:377/401`),
`_sc_run_elapsed` (`self_closing.py:674-679`) und Neustart-`elapsed` (`:859`) bleiben unverändert.

### 2. Backstop

- Dispatch (`self_closing.py:629`): bei bestätigtem Lauf `planned + SERVICE_WATCH_SETTLE_SECONDS
  + margin`, sonst `planned`. Unbestätigt heißt: kein `confirm_entity` oder Confirm `None`
  (Entität nicht lesbar) — beide ohne `RUN_WATCH_ENTITY` (`self_closing.py:597-603`).
- `_sc_schedule_cleanup` bleibt unverändert; es wird auch von `run_watch.py:703/760` und
  `opensprinkler.py:666` benutzt. Die Marge wird an den Service-Aufrufstellen addiert.
- Tor für „gilt“: `RUN_MODE == service` UND `RUN_WATCH_ENTITY` UND `RUN_LATENCY_MARGIN`
  vorhanden. `RUN_WATCH_ENTITY` allein reicht nicht (OpenSprinkler `self_closing.py:596`,
  Batch `batch.py:359`). Datensätze aus der Zeit vor dem Update haben keine Marge und laufen
  nach der heutigen Formel.
- Feuert der Backstop:
  - ohne `RUN_VALVE_OFF` → `completed`, `actual_s = planned_s` (nichts hat den Schluss beobachtet);
  - mit `RUN_VALVE_OFF` → Abschluss nach der Fensterregel (Abschnitt 3). Fängt eine Latenz über
    der Marge ab, ohne das beobachtete Fenster zu verlieren.

### 3. Abschluss

Gesteuert über ein neues Feld der `WatchPolicy` (`run_watch.py:135-205`),
`settles_on_valve_window: bool = False`, das nur `SERVICE_WATCH_POLICY` auf `True` setzt. Batch
und OpenSprinkler bleiben byte-gleich; ihre Tests sind das Orakel.

- **Anker** eines Service-Laufs mit den neuen Feldern: `RUN_VALVE_ON`, sonst `RUN_OBSERVED_START`
  (für Service = `RUN_STARTED`, `run_watch.py:483-486`).
- **Fenster**: `RUN_VALVE_OFF − Anker`. Fehlt `RUN_VALVE_OFF` (das Ventil schloss, während HA aus
  war, siehe Abschnitt 5): `min(jetzt − Anker, planned)` (E4).
- **Klassifizierung** (`run_watch.py:828` für diese Läufe): abgeschlossen, wenn
  `Fenster + max(1, RUN_LATENCY_MARGIN) >= planned`, sonst Teil-Lauf. Ohne die neuen Felder gilt
  weiter `elapsed + 1 >= planned`.
- **`_sc_finish_run(zone_id, actual_s=None)`**: mit Wert wird dieser als `actual_s` geschrieben;
  ohne Wert wie heute `planned_s` (Backstop ohne Aus-Meldung, Sofort-Abschluss nach Neustart,
  OpenSprinkler `opensprinkler.py:660`, Batch). Zeitvolumen (`:378`) und Kalibrierprobe (`:404`)
  bleiben bei `planned_s`.
- **`async_stop_self_closing(..., actual_s=None)`**: mit Wert gilt er für `delivered_frac`
  (`:765`), Zeitvolumen (`:812`) und `actual_s` (`:820`). Ohne Wert wie heute.
- **Manueller Stopp** eines Service-Laufs mit gespeicherter Aus-Meldung (Stopp in der Wartezeit)
  nutzt das Fenster. Präzisierung: ein manueller Stopp mit offenem Ventil misst ab
  `RUN_VALVE_ON`, sofern vorhanden, damit alle Service-`actual_s` denselben Anker haben.
- Die Entprellung selbst bleibt 5 s und entscheidet nur noch, ob der Lauf endete (Blip-Prüfung
  `run_watch.py:803-813`).

Nachgerechnet 13.09. (Default-Marge 4):

| Zone | Fenster | Watcher schließt ab | Backstop | Ergebnis |
|---|---|---|---|---|
| Beet | 422,90 s | 06:20:36,86 | 06:20:38,82 | `completed` über `_watch_finish` |
| Kirschlorbeer | 1118,33 s | 06:32:11,68 | 06:32:16,81 | `completed` (1118,33 + 4 ≥ 1119) |

### 4. Mitgezogene Stellen (E3)

- **In-flight** (`run_state.py:88-99`): für Datensätze durch das Tor aus Abschnitt 2 ist das
  Fenster `planned + Wartezeit`; Anker unverändert. Schließt das Loch, in dem ein zweiter Dispatch
  derselben Zone alle Wächter passiert (`self_closing.py:476`, `irrigation.py:1035`, `:3309`,
  `run_chain.py:248`, `:408`, `batch.py:226`), den wartenden Datensatz ersetzt
  (`self_closing.py:209-216`) oder — wenn der alte Backstop/`_decide` während seiner Confirm-Abfrage
  feuert — den alten Lauf mit der Pumpen-Freigabe und dem Zähler des neuen abrechnet
  (`self_closing.py:350`, `:359`, `:412`). Ebenso wird eine Berechnung in dieser Zeit wieder
  aufgeschoben (`calculation.py:464`). Abschluss entfernt den Datensatz → sofort frei.
- **Zeitfenster-Preis** (`run_window.py:336-361`): `zone_confirm_seconds` für den Service-Track
  (`run_window.py:46`, `:225-226`; Station/Batch zweigen vorher ab) mit `confirm_entity` =
  `VALVE_CONFIRM_TIMEOUT + SERVICE_WATCH_SETTLE_SECONDS + Marge der Zone`. Wirkt auf Finish-Anker
  und Arm-Schranke (#140, `scheduler.py:818/847`); unter `sequential` summiert, unter `parallel`
  Maximum (`run_window.py:416-489`). Pins in `tests/test_confirm_reserve.py` ändern sich.
- **Observed-Sperre** (`self_closing.py:487`, `irrigation.py:115-130`): `_note_si_valve(zone,
  planned + Wartezeit)`, wenn die Zone ein `confirm_entity` hat (der Confirm steht zu diesem
  Zeitpunkt noch aus; ein unbestätigter Lauf wird 9 s zu lang gesperrt, harmlos).
- **Panel-Countdown** bleibt bei Start + geplant.

### 5. Neustart (`self_closing.py:859-875`, Datensätze durch das Tor)

`elapsed` wie heute ab `RUN_STARTED` einschließlich Ausfallzeit.

| Zustand | Verhalten |
|---|---|
| `RUN_VALVE_OFF` gespeichert | Abschluss nach der Fensterregel: sofort, wenn `elapsed >= planned + Wartezeit`, sonst über den neu aufgenommenen Watcher |
| `elapsed >= planned + Wartezeit`, keine Aus-Meldung | sofort `completed` mit `planned_s` (wie heute) |
| sonst | Pumpen-Freigabe neu nehmen (`:866`), Backstop `planned + Wartezeit − elapsed`, Watcher neu aufnehmen |
| Watcher sieht beim Neuaufnehmen „aus“, keine Aus-Meldung | Entprellung, dann Fenster = `min(jetzt − Anker, planned)` (E4, Anker wie Abschnitt 3) |

Write-only-Datensätze und Datensätze ohne die neuen Felder: heutige Formel, Pin
`tests/test_self_closing.py:491` `(2, 500.0)` bleibt.

### 6. Zonenfeld, Panel, Übersetzungen, Doku

- **`const.py`** Service-Block (`:839-853`): `ZONE_LATENCY_MARGIN = "latency_margin"`,
  `DEFAULT_LATENCY_MARGIN_SECONDS = 4`, Obergrenze 30 als benannte Konstante.
- **`store.py`**: `attr.ib` auf `ZoneEntry` (`:229-316`) UND `zone.get(ZONE_LATENCY_MARGIN, 4)` im
  Ladeblock (`:1115-1212`; ohne die Zeile fällt der Wert bei jedem Neuladen zurück, Kommentar
  `:1186-1187`). Kein Versionssprung, `STORAGE_VERSION` 14 bleibt (`tests/test_store_self_closing.py:17-21`).
  Folge: jede bestehende Service-Zone mit `confirm_entity` bekommt 4 s.
- **`websockets.py`** Zonen-Schema (`:274-333`): `vol.Coerce(int)`-Eintrag wie `maximum_duration`;
  nicht in die Liste der servereigenen Felder (`:340-375`).
- **`set_zone`** bleibt (feste Erlaubt-Liste, `const.py:431-437`).
- **Panel** `frontend/src/views/zones/view-zone-settings.ts`, nur Service-Block (`:1151-1348`), Zeile
  unter `confirm_entity` (`:1281-1312`), sichtbar nur mit gesetztem `confirm_entity`; Überschrift mit
  `(${UNIT_SECONDS})`, Zahlenfeld, gerundet, 0–30, Muster `lead_time` (`:1636-1685`). Sichtbarkeit als
  eigene Methode mit vitest nach `view-zone-settings-flow-counter-type.test.ts`.
  `const.ts` `ZONE_LATENCY_MARGIN`, `types.ts` `latency_margin?: number`.
- **Übersetzungen**: `panels.zones.labels.latency_margin` und `latency_margin_help` in allen 8
  `frontend/localize/languages/*.json`, echte Übersetzungen; Wortlaut im Plan zur Freigabe.
  `tests/test_i18n_completeness.py` prüft fehlende/verwaiste Schlüssel und englische Kopien.
- **dist**: `irrigation-plus.js` und `irrigation-plus-card-impl.js` (en.json steckt in beiden,
  `localize.ts`); Node 24 lokal = Node-22-CI; `git add -f`. `card.js`/`card-legacy.js` unverändert.
- **Doku**: `docs/configuration-my-zones.md` (`:88-92`) Punkt unter „Confirm entity“.

## Tests

Basis `tests/test_service_watch.py` (echtes `hass`, `_coord`/`_zone`/`_dispatch`). Für echte Timer
die Instanz-Mocks `_sc_schedule_cleanup` und `_sc_cancel_cleanup` entfernen, Dispatch und ganzen
Ablauf in EINEM `freeze_time`/`freezer`-Block (freezegun friert auch die Loop-Uhr ein), vorstellen
mit `tick(n)` + `async_fire_time_changed` + `async_block_till_done`; die Uhr zwischen Aus und
Entscheidung WIRKLICH vorstellen (sonst bleibt der +5-s-Fehler unsichtbar,
`test_service_watch.py:129-130`). `async_fire_time_changed` feuert bis 0,5 s zu früh — Grenzen mit
Abstand oder `async_fire_time_changed_exact`. Eimer negativ halten, damit die Deckelung den Beweis
nicht frisst. Jeder Test mit echten Timern endet abgerechnet (lokal sonst „Lingering timer“).
Jeder Test mutationsgeprüft.

1. Schluss in der Wartezeit → `_watch_finish`, `completed`, `actual_s` = Aus − Ein, Backstop-Handle entfernt.
2. Verpasster Schluss → kurz vor `planned + 9` noch in flight, danach `completed` mit `planned_s`.
3. Write-only und nicht prüfbarer Confirm → Backstop `(2, planned)`; Pins
   `test_self_closing.py:109/491/1198/1224` unverändert.
4. Früher Schluss innerhalb der Marge → `completed`, `actual_s` < planned; außerhalb → Teil-Lauf mit
   beobachtetem `actual_s` und Gutschrift aus dem Fenster.
5. Blip in der Entprellung behält den Lauf und löscht `RUN_VALVE_OFF`; Attribut-Update eines
   „aus“-Ventils verschiebt `RUN_VALVE_OFF` nicht.
6. `RUN_VALVE_ON`: vorher offenes Ventil → `t_dispatch`; späte Meldung → `last_changed`.
7. Latenz über der Marge: Backstop mit gespeicherter Aus-Meldung rechnet nach dem Fenster ab.
8. Neustart: alle vier Zeilen aus Abschnitt 5, dazu Backstop-Argument `planned + 9 − elapsed`;
   Ventil beim Neuaufnehmen `unavailable`, danach `off` → keine Aus-Meldung gespeichert, Abschluss
   nach E4. Dazu der Pin für `on → unavailable → off` mitten im Lauf (E6).
9. Batch-Wiederaufnahme plant unverändert `remaining`; OpenSprinkler-Pins
   (`test_opensprinkler.py:1116-1117`, `:469-484`) unverändert.
10. In-flight während der Wartezeit wahr, nach dem Abschluss falsch.
11. `zone_confirm_seconds` = 30 + 5 + Marge mit `confirm_entity`, 0 ohne.
12. Observed-Sperre `planned + 9 + 30`: geprüft wird das Argument `planned + 9` an
    `_note_si_valve`; die `+ 30` sind `SI_VALVE_SUPPRESS_MARGIN` in `_note_si_valve`
    (`irrigation.py:68`, `:129`) und bleiben unverändert (609 → 639 s).
13. Manueller Stopp in der Wartezeit mit gespeicherter Aus-Meldung nutzt das Fenster; manueller
    Stopp mitten im Lauf misst ab `RUN_VALVE_ON`.
14. Zonenfeld übersteht Neuladen; Zonen-Schema zwingt `int`; i18n vollständig; vitest Sichtbarkeit.

Geänderte Pins: `test_service_watch.py:216` `(2, 600)` → `(2, 609)` für bestätigte Läufe;
`test_service_watch.py:183` (`actual_s == planned_s == 600`) nach der neuen Messung;
`tests/test_confirm_reserve.py` Zeile 219 (30 → 39). Korrektur nach dem Probelauf: 193, 264 und
278 prüfen klassische Zonen und bleiben unverändert.

Suite am selben Tag gegen die Basis messen; black, ruff; `npm run build` reproduziert dist;
`npm test`.

## Reichweite: nicht abschaltbare Änderungen (für den PR-Text)

Betroffen ist jede Service-Zone mit `confirm_entity`. Die Marge kann auf 0 verkleinert werden,
die 5 s Entprellung bleiben.

- `actual_s` abgeschlossener Läufe = beobachtetes Fenster statt `planned_s`; Teil-Läufe ohne
  +5-s-Versatz. Sichtbar im Attribut `duration` des Sensors `last_water_used` (`sensor.py:1051`,
  gerundet `irrigation.py:2873-2874`); die Verlaufstabelle im Panel zeigt `actual_s` nicht.
- Teil-Läufe bei normalem Ende nur noch, wenn das Ventil mehr als die Marge vor dem Ende schließt.
- Abschluss bei Aus + 5 s, ohne Aus-Meldung bei geplant + 9 s. Verschiebt: nächste Zone einer
  `sequential`/rotierenden Kette (`run_chain.py:235-251`), `last_irrigation` und Verlaufs-Zeitstempel
  (`irrigation.py:2816-2918`), `irrigation_finished` (`self_closing.py:389-401`), Pumpen-Aus
  (Freigabe beim Abschluss + 5 s Nachlauf, `master.py:135-155`; innerhalb einer Kette hält der
  Ketten-Token ohnehin).
- In-flight-Fenster, Zeitfenster-Preis und Observed-Sperre je + Wartezeit.
- Durchfluss-Ratensensor, der nach dem Schluss seinen letzten Wert hält, wird bis zur
  Wartezeit länger integriert (`flow_metering.py:156-164`, rechter Endpunkt); Zähler unberührt.
- Unberührt: Batch, OpenSprinkler, Verteiler (eigener Pfad ohne `_sc_`/`_watch_`,
  `distributor.py:677-760`), write-only Service-Zonen, `irrigation_finished`-Nutzlast.

## Ausdrücklich nicht dazu

- `_watch_resume`, Watch-Policies von Batch und OpenSprinkler.
- `RUN_STARTED`, `RUN_OBSERVED_START`, Panel-Countdown.
- Divisor der Kalibrierprobe und Zeitvolumen abgeschlossener Läufe (bleiben `planned_s`).
- Stopp des Durchfluss-Samplers bei der Aus-Meldung.
- Rückgabeform von `_confirm_valve_running`.
- Vorbestehende Befunde (in `D:\Entwicklung\HASI\ToDo.md` eintragen, nicht in den PR):
  - `async_unload` bricht weder Backstop-Timer noch Durchfluss-Sampler ab
    (`__init__.py:2196-2294`); ein Neuladen lässt den alten Koordinator auf dem geteilten Store
    abrechnen.
  - Fehlerbehandlung des Dispatch (`self_closing.py:640-647`) lässt den bei `:629` scharfen
    Backstop und den bei `:604` gespeicherten Datensatz stehen.
  - Ein nach Neustart mitten in der Bewässerung übernommener Batch-Lauf bekommt keinen Backstop
    (`batch.py:741-756`).
  - Observed-Doppelgutschrift, wenn der Dispatch auf ein extern geöffnetes Ventil trifft und
    `observed_entity` dieselbe Entität ist (`observed_watering.py:146`, `:157-172`).
  - Veralteter Docstring `get_total_irrigation_duration` (`skip_conditions.py:410-415`).
  - Unbenutzter Parameter `planned` in `_watch_start` (`run_watch.py:491-563`).

## Verworfen

- **`actual_s` ab `RUN_STARTED` mit 1 s Toleranz (Vorgabe wörtlich):** normale
  Kirschlorbeer-Enden würden Teil-Läufe (siehe E1).
- **Ventil-Ein mit 1 s Toleranz:** 0,33 s Luft auf einer Stichprobe von zwei Läufen.
- **`RUN_STARTED` auf die Ventil-Meldung verschieben:** fünf Leser würden mitwandern (In-flight,
  Panel, `_sc_run_elapsed`, Neustart, `RUN_OBSERVED_START`); ein vorher offenes Ventil hätte einen
  Stunden alten Anker.
- **Rückgabe von `_confirm_valve_running` erweitern:** drei weitere Aufrufer und viele Stubs.
- **Marge in `_sc_schedule_cleanup`:** träfe Batch und OpenSprinkler.
- **Aus-Zeitpunkt beim Eintritt in `_watch_defer_finish` stempeln:** Attribut-Rauschen und
  Task-Latenz verschieben ihn; `last_changed` des ersten Aus-Ereignisses ist fest.
- **Default-Marge 3 s** (0,1 s Luft gegen die rohe Latenz) und **5 s** (User wählte 4).
- **Nur In-flight mitziehen und Marge deckeln / nichts mitziehen:** Worst Case unterpreist bzw.
  9-s-Loch für Doppel-Dispatch.
- **Neustart ohne Aus-Meldung immer `completed` mit `planned_s`:** ein im Ausfall von Hand
  geschlossenes Ventil bekäme volle Gutschrift. **Ungedeckelt wie heute:** Ausfallzeit im `actual_s`.
- **Wartezeit nur bei verpasstem Schluss preisen:** der Preis muss den schlimmsten Fall decken.

## End-to-End-Kriterium

1. **HA-Test** (eigene Freigabe), mit dem Sonoff-Emulator. Am 2026-09-15 per MCP gelesen, alle vier
   Entitäten vorhanden: `input_boolean.sonoff_emu_valve` (Ventil), `input_boolean.sonoff_emu_fault`
   (Fehler-Schalter), `binary_sensor.sonoff_emu_flowing` (Template, Confirm-Entität),
   `script.sonoff_emu_run` (`mode: restart`, Feld `seconds` 1–3600: Ventil an → `delay seconds | int`
   → Ventil aus; zuletzt ausgelöst 2026-09-14). Keine Automation verweist darauf.
   Service-Zone: `run_service` = `script.sonoff_emu_run`, `duration_field` = `seconds`, Einheit
   Sekunden, `confirm_entity` = `binary_sensor.sonoff_emu_flowing`; ein Lauf.
   Bestanden, wenn Verlauf `completed`, `actual_s` = Ventil-offen-Fenster aus dem Recorder ±1 s,
   Abschluss (`last_irrigation`) = Aus + 5 s ±0,5 s (Watcher, nicht Backstop), keine Exception im Log.
   **Grenze:** das Emulator-Ventil schließt praktisch ohne Latenz (Template folgt dem
   `input_boolean` im selben Moment, 20:24:05,3252 → ,3255). Der Test belegt den Watcher-Abschluss
   und `actual_s`, NICHT eine Tuya-artige Latenz von 2–3 s oder eine Latenz über der Marge —
   die bleiben der Nachmessung auf HA-Prod.
2. **HA-Prod** nach Release und freigegebenem Neustart: die nächsten natürlichen Läufe von Beet und
   Kirschlorbeer mit denselben Kriterien; Kirschbaum beim nächsten Lauf. Ergebnis auf #139.
