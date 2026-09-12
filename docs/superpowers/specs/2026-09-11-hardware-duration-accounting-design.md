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

## Wer betroffen ist — eine Bedingung, nicht drei Pfade

Maßgeblich ist eine Eigenschaft der Hardware, nicht der Codepfad:

> **Der Schluss gehört der Hardware, und diese Hardware nimmt nur ganze Minuten.**

Alles andere folgt daraus. Ob das Ventil eine eigene Zone bedient, als Einlass vor
einem Verteiler sitzt oder von einem Queue-Controller bedient wird, ändert nichts an
der Rundung und nichts an ihrer Folge. Ein Ventil, das Sekunden nimmt, ist nie
betroffen; ein klassisch getaktetes Ventil, bei dem die Integration den Schluss
besitzt, ebenfalls nicht.

Geprüft, dass die Bedingung überall dieselbe ist:

| Stelle | Bedingung im Code |
| --- | --- |
| `self_closing.py:121` | self-closing per Definition des Modus |
| `distributor.py:74` | nur unter `watering_mode == WATERING_MODE_SERVICE`; der Docstring von `_dist_open_inlet` sagt selbst „service (self-closing): the hardware owns the close" |
| `batch.py:239` | verlangt ein `confirm_entity` als Beobachtungspunkt und beruft sich im Kommentar auf denselben Mechanismus wie `async_run_self_closing`; der Controller besitzt den Schluss, die Einheit kommt aus der Zone |

Die Umrechnung existiert dafür heute zweimal: `_sc_convert`
(`self_closing.py:100-105`, von `batch.py` als Mixin-Methode mitbenutzt) und
`_dist_convert` (`distributor.py:62-68`). Beide sind logisch identisch, nur die
Docstrings unterscheiden sich.

**Daraus folgt der Zuschnitt:** eine Bedingung, eine Rundungsregel, also eine
Funktion. Die Zusammenlegung ist kein nebenher mitgenommener Umbau, sondern die
Form, die zum Befund passt.

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
- Der OpenSprinkler-Pfad (`_sc_dispatch_open`, `max(1, math.ceil(seconds))`). Er
  erfüllt die Bedingung nicht: `run_station` nimmt **ganze Sekunden**, es gibt dort
  also keine Einheiten-Umrechnung. Das verbleibende Aufrunden beträgt unter eine
  Sekunde. Nicht „zu klein, um sich zu lohnen", sondern eine andere Hardware-Klasse.
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

**Für die Release-Notes**, im Review gefunden: ein manueller Lauf über „2,5 Minuten"
auf einer Minuten-Zone bucht künftig 180 s statt 150 s. Das ist genau das, was das
Ventil tut, aber Verlauf und Eimer zeigen dann 3 Minuten, wo der Nutzer 2,5 getippt
hat. Gehört benannt, nicht in den Code.

**Was der Fix nebenbei mitheilt**, ebenfalls im Review nachgewiesen und wert, im
PR-Text zu stehen:

- `async_stop_self_closing` rechnet `delivered_frac = min(elapsed / planned, 1.0)`.
  Ein Stopp bei t = 280 s auf einem echten 300-s-Ventil ergab bisher `280/263 --> 1,0`,
  also **volle** Gutschrift für 93 % des Wassers. Künftig 0,933.
- Der Neustart-Abgleich (`self_closing.py:807`) vergleicht `elapsed >= planned`. Ein
  Neustart bei t = 270 s las bisher 263, nahm den Finalisierungs-Zweig, gab den
  Master-Hold frei und schrieb `completed`, während das Ventil noch 30 s offen war.
- `_watch_finish` entscheidet `completed` gegen Früh-Stopp an derselben Zahl.

**Nicht in den PR-Text**, weil im Review widerlegt: die beiden Wiederarmierungen in
`run_watch.py` erben zwar formal mit, sind für diesen Modus aber unerreichbar —
beide hängen an `not opens_at_dispatch` beziehungsweise am segmentierten Pfad, und
`SERVICE_WATCH_POLICY` setzt `opens_at_dispatch=True` und `segmented=False`.

## Tests

Test vor Code, je ein fehlschlagender Test pro Punkt:

- Minuten-Zone: Lauf-Datensatz trägt das Hardware-Fenster.
- Minuten-Zone: die optimistische Gutschrift ist daraus gerechnet.
- Minuten-Zone: der Backstop wird auf das Hardware-Fenster armiert.
- Batch: der Plan an den Controller und die Buchhaltung nennen dieselbe Dauer.
- Verteiler: Einlass-Fenster und Buchhaltung nennen dieselbe Dauer.

Dazu zwei Pins:

- **KORREKTUR 2026-09-11, im Review gemessen:** die ursprüngliche Zusage „eine
  Sekunden-Zone verhält sich unverändert" ist **falsch**, und der Pin, der sie
  behauptete, konnte es nicht sehen, weil er mit einer ganzen Zahl arbeitete. Bei einer
  ganzzahligen Dauer ist die Umrechnung ein No-op; bei einer **gebrochenen** nicht, und
  eine gerechnete Dauer ist praktisch immer gebrochen. Gemessen: 263,4 s werden dem
  Ventil als 263 gemeldet und künftig als 263,0 gebucht statt 263,4; 263,6 s werden als
  264 gemeldet und als 264,0 gebucht. Das ist **richtig und dieselbe Regel** — das
  Ventil läuft die gerundete Zahl, also gehört sie in die Bücher —, nur eben unter einer
  Sekunde statt bis zu 59. Der Pin heißt jetzt
  `test_seconds_zone_books_what_the_rounding_told_the_valve` und arbeitet mit 263,6.
- Beide Aufrufer benutzen denselben Helfer — die Zusicherung schlägt fehl, sobald
  jemand eine zweite Kopie einführt.

**Was daraus für die Beschreibung folgt:** die Bedingung im Abschnitt „Wer betroffen
ist" bleibt richtig, sie benennt nur die Größenordnung. Minuten-Hardware ist der Fall,
der weh tut. Sekunden-Hardware hat denselben Fehler im Sub-Sekunden-Bereich und wird
vom selben Fix miterledigt, ohne dass dafür etwas Zusätzliches nötig wäre.

Maßgeblich ist die CI. Die lokale Suite ist unter Windows nicht verlässlich
(Memory `hasi-local-test-env-rebuild`).

## Reihenfolge gegenüber anderen Vorhaben

**Vor** dem fluss-verifizierten Öffnen für self-closing (Feature-Backlog Punkt 4).
Jene Regel urteilt auf der Messbasis, die hier repariert wird; auf einer Minuten-Zone
wird `_sc_finish_flow` heute bis zu 59 s vor dem echten Schluss gerufen.

---

## Nachtrag 2026-09-12 — Upstream kam parallel zum selben Fix

**Was passiert ist.** JustChr hat am 2026-09-12 um 08:41 (+0200) `e9f2da51`
committet, „fix(self-closing,batch): price a run at the window the hardware
actually runs (#88)". Unser PR wurde erst um 14:46 (+0200) eröffnet, er kann ihn
also nicht gesehen haben. Gearbeitet hat er aus unserem Messbericht auf Issue
#88, den er wörtlich zitiert; den Code hat er selbst geschrieben. Zwei
unabhängige Herleitungen desselben Befunds, was den Befund selbst bestätigt.

**Was dadurch entfällt.** Seine Fassung deckt `self_closing.py` und `batch.py` —
also unsere Tasks 2 bis 4. Anders faktoriert: `_sc_effective_seconds` leitet aus
`_sc_convert` ab, `_sc_planned_window` ist die eine Quelle für Versand und
Buchung. Fachlich gleichwertig.

**Was offen blieb und den PR jetzt ausmacht.** Der Verteiler-Einlass, der
Finish-Anker und die Doppelung der Rundungsregel. `_dist_convert` stand
unverändert als zweite, bytegleiche Kopie in `distributor.py`, und die
OpenSprinkler-Decke war innerhalb von `self_closing.py` zweimal ausgeschrieben.

**Entscheidung revidiert: OpenSprinkler wird umgerechnet.** Unsere Spec hatte
Stationen ganz ausgeschlossen und das mit einem Pin festgenagelt. Das war
falsch. `run_station` rundet sehr wohl — auf ganze Sekunden, mit Decke und
Untergrenze eins — also läuft eine Station für einen 263,4-s-Plan wirklich 264 s,
und die Bücher müssen das sagen. `_sc_planned_window` macht es richtig. Der
Anker folgt jetzt, über `opensprinkler_window`, damit beide Seiten dieselbe
Decke anwenden.

**Lehre, die über diesen Fall hinausgeht.** Die alten OpenSprinkler-Pins blieben
grün, als das Verhalten umgedreht wurde — weil sie bei 263,0 s prüften, wo die
Decke nichts tut. Dieselbe Falle wie in der ersten Runde, nur an anderer Stelle:
**ein Pin, der auf einer ganzen Zahl steht, prüft den Zweig nicht, den er
zu prüfen vorgibt.** Neu formuliert bei 263,4 s, wo Decke (264) und
Kaufmannsrundung (263) auseinandergehen.

**Zweite Lehre.** Bei einem Upstream-PR ist der eigene Branch kein Besitzstand.
Es war richtig, neun Commits wegzuwerfen und auf seinem Stand neu aufzusetzen,
statt Konflikte durchzuschleifen — der Rest-PR erzählt jetzt eine Geschichte
statt einer Kollision.
