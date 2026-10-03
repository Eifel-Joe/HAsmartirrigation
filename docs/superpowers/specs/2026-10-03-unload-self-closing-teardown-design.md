# Das Entladen räumt die Self-Closing-Timer ab, und ein Deaktivieren stoppt, was es nicht mehr betreut

Design für `Eifel-Joe#9`. Basis: `upstream/master` = `e9c79ec4` (Beta v2026.10.03). Alle Zeilenangaben
beziehen sich auf diesen Commit und auf `custom_components/irrigation_plus/`, sofern nicht anders
angegeben. Seit der letzten Nachprüfung (2026-09-29, `1876aa03`) hat kein Commit `self_closing.py` oder
`master.py` berührt, und keine Diff-Zeile nennt die betroffenen Tabellen, `_master_release_all`,
`_master_off_cancel` oder `async_unload` (am 2026-10-03 per `git log` / `git diff` geprüft).

**Status:** Verhalten mit dem User am 2026-10-03 entschieden (eine Frage, zwei Design-Abschnitte; siehe
*Entscheidungen*). **Mit JustChr nicht vorab abgestimmt:** Es geht direkt als PR; die Verhaltensänderung
beim Deaktivieren und Entfernen steht offen im PR-Text.

Belegart: Alles unter *Der Defekt* ist **gelesen, nicht gemessen**. Gemessen wird es als RED-Seite der
Tests im Plan und als RED-Seite des Live-Tests.

## Der Defekt

Ein Self-Closing-Lauf besitzt je Zone zwei Handles:

- den **Abtaster**, ein `async_track_time_interval` alle `FLOW_POLL_INTERVAL` (15 s), abgelegt in
  `_sc_flow_meters` (`self_closing.py:236-243`, angelegt `:294-297`), nur bei Zonen mit Durchflusssensor;
- den **Backstop** (Aufräum-Timer), ein `async_call_later`, abgelegt in `_sc_cleanup_handles`
  (`:245-257`, angelegt `:630`). Ihn teilen sich Service, OpenSprinkler und Batch (`_sc_schedule_cleanup`).

Beide Tabellen werden nur für jeweils eine Zone gesetzt, gelesen oder entnommen. `async_unload`
(`__init__.py:2207-2302`) räumt Tracker, Observed, Stop-Hook, Watcher samt Ketten, Batch, Continuous,
Zeitpläne, Master-Holds, Einlass-Watcher und Entitäts-Tabellen ab, aber **keine der beiden Tabellen**.
Die Timer bleiben scharf und gehören zum toten Koordinator: Die Closures halten `self`.

**Neuladen mitten im Lauf** (jede Options-Änderung über `options_update_listener`, `__init__.py:417-440`,
registriert `:329`; und jedes manuelle Neuladen). Der Lauf bleibt absichtlich stehen
(`__init__.py:468-474`), der neue Koordinator übernimmt ihn:
`async_resume_self_closing_runs` stellt Backstop (`self_closing.py:1270`), Watcher (`:1284`) und
Master-Hold (`:1239`) neu, aber **keinen Abtaster**. Danach:

1. **Leck (der Regelfall).** Der neue Backstop ist auf `RUN_STARTED + Plan + Nachfrist` gestellt, der
   alte wurde erst nach `_sc_add_run` gestellt (`:854`, `:888-890`) und liegt deshalb Millisekunden später.
   Gewinnt der neue oder bucht der Watcher am Aus-Bericht, findet der alte Backstop keinen Datensatz mehr
   und kehrt zurück (`:444-446`), **bevor** er `_sc_finish_flow` erreicht (`:467`). Der alte Abtaster wird
   damit nie gekündigt: Er tickt alle 15 s bis zum nächsten HA-Neustart und hält den ganzen alten
   Koordinator im Speicher. Ein Leck je Neuladen mitten in einem gemessenen Lauf.
2. **Der tote Koordinator bucht.** Endet der Lauf, während das Neuladen läuft, feuert der alte Backstop
   vor dem Resume und bucht den Lauf über den toten Koordinator: Eimer, Lauf-Log, nachgeholte Rechnung
   (`:605`), Kettenschritt (`:610`) und Master-Freigabe samt Aus-Timer auf dem alten Objekt.
3. **Ein neuer Lauf wird vorzeitig beendet.** Startet dieselbe Zone, nachdem der neue Koordinator den
   alten Lauf gebucht hat, aber bevor der alte Backstop feuert, findet der alte Backstop den **neuen**
   Datensatz im gemeinsamen Store und beendet ihn vorzeitig. Das ist Review-Befund D (`:623-628`), nur
   über zwei Koordinatoren hinweg.

Die Messung geht beim Neuladen verloren (der neue Koordinator hat keinen Abtaster → Gutschrift nach
Zeit), genau wie nach einem Neustart (`:275-276`). Daran ändert diese Arbeit nichts.

**Schwester im selben Abbau: der Master-Aus-Timer.** `_master_release_all` (`master.py:145-147`) leert
nur die Holds; ein laufender `_master_off_cancel` (`master.py:208`) bleibt scharf. Er steht nach dem
Freigeben des letzten Holds für `MASTER_RELEASE_GRACE_SECONDS` = 5 s (`const.py:1142`) an, beim Verteiler
auch länger (`distributor.py:416`, `:1754`). Feuert er nach einem Neuladen, prüft er die **geleerten**
Holds des alten Objekts und schaltet bei „nach Lauf aus“ den Master ab (`master.py:188-206`), auch wenn
der neue Koordinator gerade einen Lauf darauf gestartet hat.

## Warum es auf HA-Prod scharf ist

HA-Prod hat drei Service-Zonen, zwei davon mit Durchflusssensor (Kirschlorbeer, Kirschbaum), und
`zone_sequencing = sequential` (Memory `hasi-prod-setup-snapshot`). Jedes Speichern in den Optionen lädt
neu. Fällt das in einen Lauf, bleibt ein Abtaster bis zum nächsten Neustart stehen, und die seltenen Fälle
2 und 3 sind möglich. Häufig ist es nicht, weil die Läufe zum Sonnenaufgang liegen.

Der Master-Teil trifft HA-Prod **nicht**: dort `master_off_after = false`, der Aus-Timer schaltet also nie
Hardware (`master.py:203-204`).

## Der Haken, den ein reines Abräumen erzeugt

Heute ist der alte Backstop der Mechanismus, der einen Service-Lauf nach dem **Deaktivieren** noch zu
Ende bucht und seinen Master freigibt. Mit „nach Lauf aus“ schaltet der tote Koordinator die Pumpe so rund
5 s nach Laufende ab (`master.py:123-143`, `:169-208`). Ebenso schaltet ein anstehender Master-Aus-Timer
nach dem Deaktivieren und nach dem Entfernen die Pumpe noch ab. Kappt das Entladen diese Timer, tut das
niemand mehr: Die Pumpe liefe bis zum Wiedereinschalten.

OpenSprinkler und Batch haben dafür schon eine Regel: Was nichts übernimmt (Deaktivieren, Entfernen,
echtes Herunterfahren), wird vor dem Abbau gestoppt (`opensprinkler.py:427-502`, `batch.py:672-699`,
`tests/test_opensprinkler_teardown.py:1-10`). Für Service-Läufe gibt es keinen Zwilling; der Docstring von
`_chain_forfeit_queue` sagt das selbst (`run_chain.py:624-625`).

## Anforderungen

1. Nach **jedem** Entladen feuert kein Abtaster, kein Backstop und kein beim Entladen anstehender
   Master-Aus-Timer des alten Koordinators mehr. Das Abräumen liest nichts und schreibt nichts. (Einen neuen
   Aus-Timer kann danach nur noch das Ende eines klassischen Laufs oder Verteiler-Durchlaufs stellen, siehe
   *Ausdrücklich nicht in dieser Arbeit*.)
2. **Neuladen:** Laufende Läufe bleiben für den Resume-Pfad stehen (kein Stopp, keine Buchung beim
   Entladen). Jeder Lauf wird genau einmal gebucht, vom neuen Koordinator.
3. **Deaktivieren:** Jeder laufende Service-Lauf wird vor dem Abbau gestoppt und für das Gelaufene gebucht.
   „Service-Lauf“ heißt dieselbe Teilung wie im Resume-Pfad: jeder gespeicherte Lauf, der weder
   OpenSprinkler noch Batch ist, also auch ein Altdatensatz ohne Modus (`self_closing.py:1199-1207`). Keine
   Kette startet dabei eine weitere Zone, und jede Kette gibt ihren Master-Hold ab, auch in einer Pause
   zwischen zwei Läufen, wenn gerade nichts läuft. Danach ist der Master aus, wenn ein Master konfiguriert
   ist, „nach Lauf aus“ gesetzt ist, ein HASI-Zyklus lief und kein Hold mehr besteht.
4. **Entfernen:** Service-Läufe bekommen den Stopp-Befehl ohne Buchung (der Store wird gleich gelöscht).
   Master wie in 3. Beides vor dem Löschen des Stores.
5. Keiner der neuen Schritte kann ein Entladen oder Entfernen blockieren: Sie werfen nie, Fehler werden
   je Lauf geloggt.
6. Neustart und echtes Herunterfahren bleiben unverändert.
7. Bei `master_off_after = false` schaltet weder Deaktivieren noch Entfernen den Master.

## Entscheidungen (User, 2026-10-03)

| Frage | Gewählt | Verworfen |
|---|---|---|
| Was soll Deaktivieren mit einem laufenden Self-Closing-Lauf machen, wenn das Entladen seine Timer kappt? | **2: wie OpenSprinkler/Batch** — stoppen und buchen vor dem Abbau, Master gleich aus; Entfernen genauso ohne Buchung | **1: wie ein Neustart** (nichts bis zum Wiedereinschalten, Master beim Deaktivieren aus): kappt einer pumpengespeisten Zone den Rest, der voll gutgeschrieben bliebe. **3: nur beim Neuladen kappen:** ließe beim Deaktivieren Code gegen den abgebauten Koordinator laufen, entgegen der Hausregel, und ein Wiedereinschalten im selben Lauf brächte den Wettlauf zurück |
| Vorgehen upstream | **Direkt als PR**, Verhaltensänderung offen im Text | Vorschlag als Issue vorab (wie bei #8): hier gibt es nichts zu wählen, die Regel steht schon im Code |

Preis von 2: Service-Zonen liefen beim Deaktivieren bisher bis zum Hardware-Ende weiter; jetzt schließt
sie der Stop service. Ohne Stop service bucht der Stopp nur und warnt (`self_closing.py:1026-1031`).

## Das Design

Drei kleine Bausteine nach Hausmuster, jeweils dort, wo der Code das Gegenstück für OpenSprinkler/Batch
schon hat. Verworfen: ein gemeinsamer Abbau für alle Modi (baut bestehende Aufrufe um, ohne dass #9
etwas davon hat) und Timer, die beim Feuern den lebenden Koordinator nachschlagen (Doppel-Timer und Leck
blieben bestehen).

### 1. Jedes Entladen: `async_unload`

- **Neu `async_teardown_self_closing_handles()`** in `self_closing.py`, Form wie
  `async_teardown_observed_watering` (`observed_watering.py:103-112`): für jede Zone in `_sc_meters()` den
  Abtaster kündigen und den Eintrag verwerfen, **ohne** Schlusslesung, ohne `_sc_finish_flow`, ohne
  Buchung; für jede Zone in `_sc_cleanup_timers()` den Backstop kündigen; beide Tabellen leer. Aufruf aus
  `async_unload` neben den anderen Abbauten. Deckt Service, OpenSprinkler und Batch.
- **`_master_release_all` kündigt zusätzlich den Aus-Timer** (`_master_off_cancel` → `None`). Zwei Aufrufer:
  `async_unload` (`__init__.py:2266`) und die Boot-Bereinigung (`master.py:246`), dort steht nie ein Timer
  an; der Docstring („unload/reset only“) bleibt richtig.
- **Neuladen** übernimmt wie heute: Resume stellt Backstop, Watcher und Hold neu,
  `async_reconcile_master_after_restart` (`master.py:210-249`) schaltet einen verwaisten Master ab.

### 2. Deaktivieren: `async_unload_entry`, vor `async_unload`

- **Zuerst alle Ketten freigeben.** Eine Kette hält einen Master-Hold für den ganzen Zyklus, auch in den
  Pausen zwischen zwei Läufen und in den Absorptionspausen einer Rotation (`_chain_take_hold`,
  `run_chain.py:397-407`). Fällt das Deaktivieren in eine solche Pause, läuft kein Lauf, also gibt keiner
  der Abbrüche die Kette frei (die OpenSprinkler-Variante kehrt ohne Lauf vor ihrer Kettenfreigabe zurück,
  `opensprinkler.py:466-471`), und „Master-Zyklus jetzt beenden“ fände ihren Hold noch vor: Die Pumpe
  bliebe an. Deshalb gibt das Deaktivieren jede Kette frei wie `_chain_release` (`run_chain.py:667-681`:
  wartende Zonen benennen, Marker zurückgeben, Hold lösen), mit dem Grund „being disabled“ im Log statt
  „the cycle was stopped“. Heute geht dieselbe Kette beim Entladen über `_chain_teardown` unter, nur ohne
  ihren Hold zu lösen; den räumt dort `_master_release_all` ab.
- **Neu `async_abort_self_closing_runs(reason, *, settle=True)`** in `self_closing.py`, der Service-Zwilling
  von `async_abort_opensprinkler_runs` (`opensprinkler.py:427-502`), mit demselben Vertrag:
  1. gespeicherte Läufe lesen (scheitert das: loggen, `False`);
  2. Ziele = jeder Lauf, der weder OpenSprinkler noch Batch ist und eine Zone hat;
  3. **zuerst die Service-Kette freigeben** (`_chain_release(WATERING_MODE_SERVICE)`, `run_chain.py:667-681`;
     benennt die wartenden Zonen, gibt ihre Marker zurück, löst den Ketten-Hold). Sonst startet der Stopp
     über `_chain_advance_for_run` (`self_closing.py:1177`) die nächste Zone;
  4. je Lauf mit `settle=True`: `async_stop_self_closing(zone_id)` mit Ventil-Stopp. Der Abtaster lebt hier
     noch, gebucht wird also gemessen, wo gemessen wurde (`:1092`); Hold frei (`:1000`), Teillauf im Log
     (`:1162-1171`), Backstop gekündigt (`:1140`);
  5. je Lauf mit `settle=False`: nur der Stopp-Befehl (siehe 3.);
  6. jeder Lauf einzeln in `try/except` mit Log; Rückgabe `True`, wenn etwas gestoppt wurde.
- **Neu „Master-Zyklus jetzt beenden“** (Arbeitsname `async_master_end_cycle_now`) in `master.py`:
  nichts, wenn kein Master konfiguriert ist oder noch ein Hold besteht (ein klassischer Lauf läuft als Task
  weiter und beendet den Zyklus an seinem Ende selbst, wie heute; ebenso ein Verteiler-Durchlauf). Sonst
  Aus-Timer kündigen; nur wenn `_master_on` (ein HASI-Zyklus lief, `master.py:64-67`) **und** „nach Lauf
  aus“ gesetzt ist, den Master ausschalten; danach `_master_on = False`, `_master_off_deadline = None` —
  dieselben Felder, die `_fire` am Zyklusende setzt (`master.py:205-206`). Wirft nie.
- Reihenfolge im Zweig `entry.disabled_by is not None` (`__init__.py:475-481`): **alle Ketten freigeben**,
  OpenSprinkler abbrechen, Batch abbrechen (beide wie heute; ihre eigene Kettenfreigabe ist dann ein
  No-Op), **Service abbrechen**, **Master beenden**, dann `async_unload`.

### 3. Entfernen: `async_remove_entry`

- Nach den beiden bestehenden Abbrüchen mit `settle=False` (`__init__.py:505-510`):
  `async_abort_self_closing_runs(..., settle=False)`, dann „Master-Zyklus jetzt beenden“, **dann**
  `async_delete_config()` (`:511`); danach wäre die Master-Konfiguration weg (`master.py:38-39`).
- Das Entladen ist hier schon gelaufen, die Holds sind leer. Ein noch laufender klassischer Lauf verliert
  beim Entfernen seine Pumpe; beim Entfernen hinnehmbar.
- Für den Stopp ohne Buchung wird der Stopp-Befehl aus `async_stop_self_closing` (`self_closing.py:1005-1031`)
  in eine Hilfsfunktion gezogen (Arbeitsname `_sc_dispatch_stop(zone)`, wie `_os_dispatch_stop` und
  `_batch_dispatch_stop`); `async_stop_self_closing` ruft sie unverändert im selben Ablauf.

### Doku

`docs/configuration-my-zones.md:91` (Stop service, heute „closes the valve if you stop a run early (while
HA is up)“): ergänzen, dass er auch schließt, wenn die Integration mitten im Lauf deaktiviert oder entfernt
wird, so wie es `:129` für Batch schon sagt. Englisch, keine Übersetzungen (die Doku ist einsprachig).

### Betroffene Stellen (Überblick für den Plan)

| Datei | Änderung |
|---|---|
| `self_closing.py` | `async_teardown_self_closing_handles`, `async_abort_self_closing_runs`, `_sc_dispatch_stop` (herausgezogen) |
| `master.py` | `_master_release_all` kündigt den Aus-Timer; `async_master_end_cycle_now` |
| `run_chain.py` | alle Ketten freigeben, mit Grund im Log (etwa ein `why`-Parameter für `_chain_release`) |
| `__init__.py` | `async_unload` ruft den Abbau; Zweig „deaktiviert“ in `async_unload_entry`; `async_remove_entry` |
| `docs/configuration-my-zones.md` | Satz zum Stop service |
| `tests/test_self_closing_teardown.py` | neu |

Keine Store-Änderung, keine Migration, kein Frontend, kein dist. Keine neuen UI-Texte: Der Teillauf trägt
`RUN_DETAIL_SELF_CLOSING_STOPPED` wie jeder Stopp, also keine i18n-Runde. Neue Log-Zeilen sind englisch.

## Schwester-Pfade geprüft

Alle Handles, die der Koordinator anlegt (Inventur per `grep` über `async_call_later`,
`async_track_*`, `bus.async_listen`, `async_dispatcher_connect`, `async_create_task`):

- **Abgeräumt:** periodische Tracker (`__init__.py:2211-2224`), Stop-Hook (`:2233-2236`), Observed-Abo und
  -Abtaster (`observed_watering.py:103-112`), alle Run-Watcher samt Timern (`run_watch.py:399-411`, über
  `opensprinkler.py:504-507`, weil `_os_watchers()` die gemeinsame Tabelle ist, `:421`), Ketten samt
  Absorptions-Timer (`run_chain.py:683-697`), Batch-Pausen und Paused-Abo (`batch.py:701-705`),
  Continuous-Abo und Debounce (`continuous_update.py:298`), Zeitplan-Tracker und Rearm
  (`scheduler.py:158-189`), Einlass-Watcher (`__init__.py:2270-2273`), Koordinator-Abos (`:2301-2302`),
  Plattform-Abos (`sensor.py:201-224` über `config_entry.async_on_unload`).
- **In dieser Arbeit:** die beiden Self-Closing-Tabellen und der Master-Aus-Timer.
- **Andere Klasse, eigenes Issue:** Abos, deren Lösung verworfen wird: der `core_config_updated`-Listener
  (`__init__.py:269`; harmlos, der Handler liest den lebenden Koordinator und ist idempotent,
  `:392-414`) und die `async_dispatcher_connect` in Entitäts-Konstruktoren (etwa `sensor.py:296-305`,
  `:500-511`, `:644-646`). Sie wachsen mit jedem Neuladen; Schreiben auf entfernte Entitäten tut nichts.
- **Absichtlich nicht abgeräumt:** laufende Tasks des klassischen Läufers (`hass.async_create_task`,
  `irrigation.py:1155-1169`, nicht an den Eintrag gebunden; HA bricht sie erst beim Herunterfahren ab, ihr
  `finally` schließt dann das Ventil) und des Verteilers. Sie haben keinen Resume-Pfad: Brächen sie beim
  Entladen ab, endete jeder solche Lauf bei jedem Neuladen vorzeitig.

## Ausdrücklich nicht in dieser Arbeit

- **Echtes Herunterfahren von HA:** unverändert, es ist kein Entladen; Service-Läufe laufen dort bis zum
  Hardware-Ende. Beobachtung (gelesen, nicht gemessen): Auch bei OpenSprinkler und Batch hängt das
  Pumpen-Aus dort am 5-s-Timer, der womöglich nicht mehr feuert, bevor HA die Event-Schleife beendet →
  Kandidat für ein eigenes Issue.
- **Die Messung über ein Neuladen retten** (Zähler an den neuen Koordinator übergeben): Neuladen behält die
  Semantik eines Neustarts.
- **Das Ende klassischer Läufe und Verteiler-Sweeps** kann den Master weiterhin über den toten Koordinator
  freigeben (siehe oben).
- **Die Abo-Lecks** (eigenes Issue, `schwere:niedrig`).
- **Master-Kick beim Resume** (beobachtet, gelesen): Der neue Koordinator kennt `_master_on` nicht, also
  schaltet `async_master_begin_cycle` (`master.py:64-77`) eine schon laufende Pumpe mit `kick_enabled` mitten
  im Lauf kurz aus und wieder an, auch nach einem Neustart. Issue nur auf Wunsch des Users.
- **Ein Live-Test auf HA-Prod** mit einem Neuladen mitten in einem echten Lauf.

## Tests

Jeweils RED vor GREEN, neue Datei `tests/test_self_closing_teardown.py`.

- **Abbau:** nach `async_unload` beide Tabellen leer; Zeit vorrücken (`async_fire_time_changed`) → beim alten
  Koordinator weder ein Abtaster-Tick noch eine Buchung; kein Master-Aus nach dem Entladen; ein teilweise
  gebauter Koordinator entlädt weiter sauber.
- **Abbruch:** trifft Service und Altdatensatz ohne Modus, nicht OpenSprinkler und nicht Batch; die Kette ist
  vor dem ersten Stopp freigegeben und keine wartende Zone startet; `settle=True` stoppt und bucht;
  `settle=False` sendet nur den Befehl und schreibt nichts; ein werfender Stopp hält die übrigen nicht auf;
  ein werfendes Lesen der Läufe gibt `False`; Rückgabewert.
- **Master beenden:** je Bedingung ein Test (konfiguriert; Hold übrig; `_master_on`; „nach Lauf aus“); Timer
  danach gekündigt; Flag und Frist zurückgesetzt; ein werfender Schalter blockiert nicht.
- **Einstiege:** Neuladen bricht nicht ab (Pin, heute schon grün — per Mutation belegt, dass er greift);
  Deaktivieren gibt erst alle Ketten frei, bricht dann ab und beendet den Master, alles vor `async_unload`;
  Entfernen bricht mit `settle=False` ab und beendet den Master, beides vor `async_delete_config`.
- **Szene Neuladen** (echter Koordinator): Lauf mit Durchflusssensor, alter Koordinator entlädt mitten im
  Lauf, neuer übernimmt → genau eine Buchung, vom neuen; beim alten tickt und feuert danach nichts. Dazu der
  Fall „Lauf endet während des Neuladens“: Nach dem Entladen bucht nichts, bis der neue übernimmt.
- **Szene Deaktivieren** (echter Koordinator): Lauf mit Durchflusssensor, sequenzielle Kette mit einer
  wartenden Zone, Master mit „nach Lauf aus“ → Stop service mit `duration 0`, Teillauf mit Messvolumen,
  wartende Zone startet nicht, Master aus, danach feuert nichts. Zahlen so gewählt, dass gemessen,
  zeitbasiert und Plan verschieden sind und keine falsche Kombination zufällig stimmt.
- **Deaktivieren in einer Kettenpause** (rotierende Kette in der Absorptionspause, kein Lauf aktiv, Master
  mit „nach Lauf aus“): Die Absorption feuert nicht mehr, die Kette ist leer, der Master ist aus.
- **Mutationsmatrix** (rund ein Dutzend, alle müssen sterben, Killer ansehen): Abbau fehlt; kündigt nur
  Abtaster; nur Backstops; bucht beim Abbau; Aus-Timer nicht gekündigt; Kette nach dem Stopp freigegeben;
  Ketten beim Deaktivieren nicht freigegeben; Filter `== service`; Abbruch auch beim Neuladen;
  `settle=False` bucht doch; Master-Aus ignoriert Hold, `_master_on` oder „nach Lauf aus“; Master-Aus nach
  `async_delete_config`.
- **Gates:** volle Suite unter `TZ=UTC`, FAILED/ERROR-Namen gegen die Baseline auf dem dann aktuellen
  `upstream/master` (Filter `^(FAILED|ERROR) tests`); `uvx black` und `uvx ruff check`.

## Ende-zu-Ende-Kriterium

**HA-Test**, Pre-Release. Dieselbe Szene läuft vorher auf dem dort installierten Stand als RED-Seite.
Voraussetzungen, im Plan zu klären: Profiler-Integration (fehlt auf HA-Test, am 2026-10-03 per
`ha_list_services` geprüft), eine Service-Zone mit Stop service und Durchfluss aus
`input_number.hasi_flow_probe`, ein Master mit „nach Lauf aus“ (sonst ein Test-Master).

1. **Neuladen** mitten im Service-Lauf (`run_zone` mit `duration`): genau ein Lauf im Log,
   `water_used_total` steigt genau einmal; `profiler.log_event_loop_scheduled` zeigt nach Laufende kein
   Handle aus `self_closing` mehr, auf dem alten Stand eines. Unbestätigt: ob die Ausgabe den Callback beim
   Namen nennt; sonst die Zahl der Handles vorher und nachher.
2. **Deaktivieren** mitten im Lauf: Das Ventil geht vor seinem Countdown zu; nach dem Wiedereinschalten genau
   ein Teillauf im Log, `water_used_total` genau einmal um das Teilvolumen; der Master ist aus.
3. **Entfernen:** nur per Unit-Test (auf HA-Test zerstörerisch).

## Lieferung

1. **Plan** nach `superpowers:writing-plans`, mit Probelauf (volle Suite mit Namensvergleich).
2. **Bau** in einer frischen Sitzung: Worktree von `upstream/master`, PR nur Fix, Test und Doku; Rezept:
   Memory `hasi-pr-build-recipe`. Vor dem Push die Greps aus Memory `no-own-issue-refs-upstream`.
3. **PR-Text:** erst deutsch zur Freigabe, dann englisch; Befund, Folgen, Fix, die Verhaltensänderung beim
   Deaktivieren und Entfernen offen benannt, Tests. Danach P2: `upstream:gemeldet` auf Eifel-Joe#9,
   Kommentar mit Link, #42 nachziehen.
4. **production** bekommt den Fix nach dem Bau sofort (User-Regel), auch vor dem Merge; ein HA-Prod-Update
   ist ein eigener, freigabepflichtiger Schritt.
5. **Eifel-Joe#9:** Kommentar zum erweiterten Umfang (Deaktivieren, Entfernen, Master-Aus-Timer) samt
   `groesse:S` → `groesse:M`; **neue Issues** für die Abo-Lecks und, wenn der User will, für das Pumpen-Aus
   beim echten Herunterfahren und den Master-Kick beim Resume. Texte gebündelt vorher zur Freigabe.
6. **P1:** Spec und Plan beim Abschluss nach `archive/design-history`.
