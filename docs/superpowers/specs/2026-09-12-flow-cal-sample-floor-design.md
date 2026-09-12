# Flow-Kalibrier-Beratung: Mindestprobe in Litern statt in Sekunden

Datum: 2026-09-12 · Issue [#133](https://github.com/JustChr/HAsmartirrigation/issues/133)
· Branch `fix/flow-cal-litre-floor` · Basis `e9f2da51`

## Wurzel

Die Beratung teilt gemessene Liter durch Minuten. Ein Haushaltszähler pulst bei
etwa einem Liter, der Fehler einer einzelnen Ablesung ist also ein ganzer Puls —
**unabhängig davon, wie lange das Ventil offen war**. Ein Puls gegen 6 L sind
17 %, gegen 60 L sind es 1,7 %. Das Band, gegen das die Probe beurteilt wird,
liegt bei 15 %. Eine Probe, die mehr Quantisierungsfehler trägt als dieses Band,
kann nichts aussagen. Drei davon füllen die Mindestzahl, lösen eine Benachrichtigung
aus und **verdrängen** die gesunden Proben aus dem nur fünf Einträge tiefen Fenster.

Gesichert war das über die **Dauer**, fest auf 300 s, und nur bei **einem von drei**
Aufrufern. Die Herleitung hinter der Zahl war schon immer ratenabhängig — der
Kommentar der Konstante sagt selbst „bei 3,1 L/min sind 1 L erst ab ~130 s
gleich 15 %", und 400 / 3,1 = 129. Eine feste Sekundenzahl ist damit die falsche
Achse. Die beiden anderen Aufrufer hatten gar kein Tor.

## Feldbeleg

37 Läufe, eine Zone, ein Ventil, ein Zähler, nichts variiert außer der Lauflänge:
die Streuung der beobachteten Raten fällt um etwa das Sechsfache, sobald ein Lauf
lang genug ist, um ein echtes Volumen zu liefern. Gemessen an Kirschlorbeer;
Kirschbaum ist als Quelle gesperrt ([[hasi-kirschbaum-hose-defect]]).

## Entwurf (mit JustChr auf #133 abgestimmt)

**Zwei Regeln, zwei Namen.** Der Kern der Einigung: Quantisierung ist eine
Eigenschaft des Zählers, Herkunft eine Eigenschaft dessen, der das Ventil geöffnet
hat. Beides in einer Sekundenzahl zu bündeln war der Fehler.

1. **`FLOW_CAL_MIN_SAMPLE_L = FLOW_CAL_METER_RESOLUTION_L / FLOW_CAL_DEVIATION`**,
   angewandt in der gemeinsamen Prüffunktion. Abgeleitet, nicht gewählt: wird das
   Band weiter, halbieren sich die nötigen Liter. Alle drei Aufrufer erben sie,
   keiner formuliert sie neu.
2. **`OBSERVED_SAMPLE_MIN_RUN_SECONDS = 300`** bleibt auf dem beobachteten Pfad,
   aber nur noch als **Herkunfts-Regel**. Niemand hält ein Ventil fünf Minuten
   von Hand auf; und an einer Zisterne mit Pumpe hängt die gelieferte Rate davon
   ab, ob die Pumpe belastet ist. Ein Handlauf ist keine Probe desselben Systems.
   Der Wert ist unverändert, weil er eine Aussage über menschliches Verhalten ist
   und keine Herleitung.

**Die Annahme wird benannt.** Ein Liter Pulsgröße ist ein Prior, keine Messung —
konfigurierbar ist sie nirgends. Sie versagt aber in die harmlose Richtung: ein
gröberer Zähler lässt eine Grenzprobe durch, die Beratung wird also eher eifrig
als stumm. Bei einem 10-L-Zähler wird daraus ein Zonenfeld, nicht jetzt.

## Verworfen

- **Die Dauer-Schwelle nur auf alle drei Aufrufer ausdehnen.** Hätte die falsche
  Achse verdreifacht statt sie zu ersetzen.
- **Die Herkunfts-Regel ersatzlos streichen.** Eine reine Literschwelle macht
  etwa 86 s Handöffnen an Kirschlorbeer zu einer gültigen Probe. Das ist genau
  der Fall, den der beobachtete Pfad ausschließen soll.

## Korrektur an der Begründung auf #88

JustChr schrieb, unsere Beet-Zone habe überhöhte Kalibrier-Proben beigetragen und
liege „knapp unter dem Band". **Beides trifft nicht zu: Beet hat keinen
Flusssensor.** `_sc_finish_flow` gibt dort `None` zurück, und `_flow_calibration_check`
steigt genau darauf sofort aus. Beet hat nie eine Probe beigetragen. Die 5,89 L
aus dem Lauf vom 2026-09-11 sind zeitgerechnet: 114 s bei 3,1 L/min.

Der **Mechanismus** bleibt echt. Er trifft jede Zone, die zugleich
Minuten-Hardware und Flussmessung hat. Auf dieser Anlage ist keine Zone beides:
Beet ist Minuten ohne Sensor, Kirschlorbeer ist Sekunden mit Sensor. Der Defekt
ist im Code real und hier schlicht nicht beobachtbar.

## Prüfkriterien

Sechs neue Zusicherungen, jede durch Mutation als beißend nachgewiesen:
Schwelle entfernt (3 fallen), Grenze von `<` auf `<=` verschoben (die Grenzprobe
fällt), Schwelle hart hingeschrieben statt abgeleitet (die Herleitung fällt),
ein Aufrufer holt sich die Schwelle zurück (der Ein-Ort-Pin fällt), ein
Dauer-Tor kehrt in die gemeinsame Prüfung zurück (der Entfernungs-Pin fällt).
