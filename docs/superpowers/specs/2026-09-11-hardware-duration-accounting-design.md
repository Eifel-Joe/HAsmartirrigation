# Hardware-Laufzeit ehrlich verbuchen — Design

**Datum:** 2026-09-11
**Status:** freigegeben (User, 2026-09-11)
**Ziel:** Upstream-PR an JustChr/HAsmartirrigation
**Arbeitsbranch:** `local/minute-rounding`, von `upstream/master` = `72406c8d` (v2026.09.14)

## Problem

Ein Ventil, das seine Laufzeit nur in ganzen Minuten entgegennimmt, bekommt eine
aufgerundete Dauer. Gebucht wird aber weiterhin die ungerundete Sekundenzahl. Die
Zone erhält dadurch jedes Mal mehr Wasser, als der Eimer sieht, und niemand merkt es.

`_sc_convert` (`self_closing.py:100-105`) rundet für `DURATION_UNIT_MINUTES` mit
`math.ceil` auf und liefert den aufgerundeten Wert an die Hardware
(`_sc_dispatch_open`, `self_closing.py:113-122`). Die gesamte Buchhaltung des Laufs
arbeitet dagegen mit `planned_seconds = float(zone.get(ZONE_DURATION))`
(`self_closing.py:386`): die optimistische Gutschrift (`:501`), der Lauf-Datensatz
(`:534`), das Start-Ereignis (`:559`), die Ventil-Überwachung (`:569`/`:583`), der
Backstop (`:575`) und das Observed-Sperrfenster (`:433`).

### Messung auf HA-Prod, Zone Beet (Tuya-Ventil, Minuten)

| gerechnet | Hardware bekommt | Ventil war offen | Mehrwasser |
| --- | --- | --- | --- |
| 502 s | 540 s | 542,8 s | +7,6 % |
| 265 s | 300 s | 302,3 s | +13,2 % |
| 263 s | 300 s | 302,1 s | +14,1 % |

Drei von drei Läufen, gegen die Recorder-Historie gemessen. Der Rest von 2 bis 3
Sekunden ist MQTT-Laufzeit, nicht die Rundung.

### Zweitwirkung: der Backstop schließt zu früh

Weil der Backstop mit der ungerundeten Zahl armiert wird, erklärt er den Lauf für
beendet, während das Ventil noch offen ist — gemessen 36 bis 40 Sekunden zu früh.
Damit ist der Abschlusspfad der Ventil-Überwachung auf einer Minuten-Zone
**unerreichbar**: `_watch_finish` kann nie entscheiden, weil `_sc_finish_run` immer
zuerst kommt. Der Vergleich `actual_s` gegen `planned_s`, der über `partial` gegen
`completed` entscheidet, urteilt aus demselben Grund auf der falschen Zahl.

## Schwester-Pfade

Dasselbe Muster, drei Aufrufstellen:

1. `self_closing.py:121` — `_sc_convert`, der Hauptpfad.
2. `batch.py:239` — der Plan an den Queue-Controller trägt
   `self._sc_convert(seconds, unit)`, `prepared` behält daneben die rohen `seconds`
   für die Buchhaltung.
3. `distributor.py:62-68` — `_dist_convert`, eine zeilengleiche Kopie von
   `_sc_convert`, für das Einlassventil.

`_sc_convert` und `_dist_convert` sind logisch identisch; nur die Docstrings
unterscheiden sich.

## Optionen

**A — Die Bücher folgen der Hardware.** Aufrunden bleibt; Gutschrift, Backstop,
Sperrfenster und Lauf-Datensatz rechnen mit der Zahl, die das Ventil wirklich
bekommen hat.

**B — Die Hardware folgt den Büchern.** Abrunden statt aufrunden; die Zone bekommt
nie mehr als gerechnet.

**Entscheidung: A.** B hat einen harten Rand — eine gerechnete Dauer unter einer
Minute ergäbe null, man bräuchte also doch eine Untergrenze von einer Minute und
hätte dort wieder aufgerundet. A beschreibt, was die Hardware ohnehin tut, hat keinen
Sonderfall, ändert kein Bewässerungsverhalten und macht nur die Buchführung ehrlich.
Dazu der Grundsatz des Betreibers: **lieber etwas überwässern als zu wenig.**

### `planned_s` bedeutet künftig das wirksame Fenster

Nicht mehr die gerechnete, sondern die an die Hardware gegebene Sekundenzahl. Geprüft:
der Verlauf-Tab rendert nur Ergebnis, Menge und Detail (`ip-zone-history.ts:49-108`),
`planned_s` ist nirgends sichtbar. Der Bedeutungswechsel trifft also keine Anzeige und
braucht keinen Release-Hinweis. Er repariert nebenbei den `partial`-Vergleich.

### Eine gemeinsame Umrechnung statt zweier Kopien

Beide Kopien werden durch **einen** Helfer in `duration_math.py` ersetzt, der zwei
Werte zurückgibt: den Wert für die Hardware und die Sekundenzahl, die dieser Wert
bedeutet. Aus 263 s auf einer Minuten-Zone wird `(3, 180.0)`; auf einer Sekunden-Zone
bleibt es `(263, 263.0)`.

**Begründung für den PR** — nicht „weniger Doppelung", sondern Zuständigkeit.
`duration_math.py` ist das reine Rechen-Ende der Dauer-Kette: Defizit → Sekunden, über
`duration_from_deficit`, `zone_run_duration` und `calibrated_flow_seconds`. Die
Umrechnung in die Einheit der Hardware ist der nächste und letzte Schritt derselben
Kette und gehört deshalb dorthin, nicht in die Ventil-Ansteuerung.

Der Modul-Docstring stellt dabei eine Bedingung, die geprüft ist: **keine
Home-Assistant-Importe**, damit `run_window` HA-frei bleiben kann. Der neue Helfer
erfüllt sie, er braucht nur `const`, und das ist dort bereits importiert. Ebenfalls
geprüft: das Modul hält seine drei Einheiten-Umrechnungen schon heute bewusst inline,
aus demselben Reinheits-Grund — eine vierte passt in dieselbe Begründung.

Zusatznutzen: die Rundungsregel lebt danach in einer Datei statt in zweien, die man
nur gemeinsam ändern darf.

**Zu klären im Plan:** keiner der drei Aufrufer importiert `duration_math` heute.
`batch.py` erreicht `_sc_convert` als Mixin-Methode über `self`. Ob die Mixins dünne
Weiterleitungen behalten oder alle drei direkt importieren, ist eine Plan-Frage; der
Spec ist nur wichtig, dass die Rechnung einmal existiert.

**Bedingung:** nur solange der gemeinsame Helfer beide Aufrufer unverändert bedient.
Braucht der Verteiler je eine Sonderbehandlung, ist die Zusammenlegung falsch.

## Nicht Teil dieser Änderung

- Die Rundungsrichtung. Was die Hardware bekommt, ändert sich nicht um eine Sekunde.
- Der OpenSprinkler-Pfad (`_sc_dispatch_open`, `max(1, math.ceil(seconds))`): rundet
  ebenfalls auf, aber um unter eine Sekunde und ohne Einheiten-Umrechnung, weil
  `run_station` ganze Sekunden nimmt.
- Die Dauer im Verlauf-Tab anzeigen — eigener Punkt, vom Betreiber angeregt.
- Die Verzerrung von rund 4,1 s auf `actual_s` (5-s-Entprellung minus 0,9 s
  Confirm-Schwanz, gemessen im #88-Test). Andere Ursache, anderer Fix.

## Ende-zu-Ende-Kriterium

Auf einer Minuten-Zone mit einer gerechneten Dauer, die kein Vielfaches von 60 ist,
muss nach der Änderung dreierlei gelten:

1. Der Lauf-Datensatz nennt das Hardware-Fenster, nicht die gerechnete Dauer.
2. Die gutgeschriebene Menge ist aus dem Hardware-Fenster gerechnet.
3. Der Backstop feuert nicht vor dem Ventil.

An den gemessenen Zahlen: aus 263 s und 13,59 L werden 300 s und 15,5 L, und die 36
bis 40 s, um die der Backstop dem Ventil zuvorkam, verschwinden.

**Erwartete Folge im Betrieb, ausdrücklich gewollt:** der Eimer der Minuten-Zone
steigt pro Lauf stärker, weil er endlich das ganze Wasser sieht. Der nächste Lauf
fällt kürzer aus oder kommt später.

## Tests

Test vor Code, je ein fehlschlagender Test pro Punkt:

- Minuten-Zone: Lauf-Datensatz trägt das Hardware-Fenster.
- Minuten-Zone: die optimistische Gutschrift ist daraus gerechnet.
- Minuten-Zone: der Backstop wird auf das Hardware-Fenster armiert.
- Batch: der Plan an den Controller und die Buchhaltung nennen dieselbe Dauer.
- Verteiler: Einlass-Fenster und Buchhaltung nennen dieselbe Dauer.

Dazu zwei Pins für das, was gleich bleiben muss:

- Eine Sekunden-Zone verhält sich unverändert.
- Beide Aufrufer benutzen denselben Helfer — die Zusicherung schlägt fehl, sobald
  jemand eine zweite Kopie einführt.

Maßgeblich ist die CI. Die lokale Suite ist unter Windows nicht verlässlich
(Memory `hasi-local-test-env-rebuild`).

## Reihenfolge gegenüber anderen Vorhaben

**Vor** dem fluss-verifizierten Öffnen für self-closing (Feature-Backlog Punkt 4).
Jene Regel urteilt auf der Messbasis, die hier repariert wird; auf einer Minuten-Zone
wird `_sc_finish_flow` heute bis zu 59 s vor dem echten Schluss gerufen.
