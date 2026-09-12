# Ein von Hand gesetzter Eimer setzt das Wetter außer Kraft, auf dem er gesetzt wurde

Datum: 2026-09-12 · Branch `fix/manual-bucket-assertion` · Basis `e9f2da51`
· Quelle des Befunds: [altmenorg](https://github.com/altmenorg/HAsmartirrigation),
Commit `616ec7ca`, deren Issue #811

## Herkunft

**Nicht unser Fund.** Beim Durchsehen von altmenorg auf Portierbares fiel deren
Commit „two ways the same rain was counted wrongly" auf. Eine der beiden Hälften
beschreibt einen Defekt, den unser Code ebenfalls hat. Neu hergeleitet statt
portiert — ihr Schema ist weit weg, und ihre Lösung hat eine andere Form (sie
merken sich den bis dahin gesammelten Regen; wir verschieben das Wasserzeichen).

## Wurzel

`ZONE_BUCKET` ist der Stand **jetzt**. Die Wasserbilanz nimmt ihn für den Stand,
den das unverbrauchte Wetterfenster beim **Öffnen** hatte — `replay_water_balance`
bekommt `bucket - applied_total` — und legt das ganze Fenster obendrauf. Ein von
Hand gesetzter Stand schrieb nur das Feld, also landete das Wetter des Fensters
**nach** der Aussage, die es bereits berücksichtigt hatte.

Gemessen an der echten Berechnung, nicht argumentiert:

| | Eimer am Tagesende |
|---|---|
| ohne Regen | **-3,00 mm** |
| 8 mm Regen, 8 h **vor** dem Setzen auf -2 | **+4,06 mm** |

Über Feldkapazität, also bewässert die Zone gar nicht mehr, bis der Überschuss
abgebaut ist — ausgehend von einer Zahl, die ihr Besitzer gewählt hatte, **damit**
sie bewässert.

## Verworfen: Buchung als Delta im vorhandenen Register

Der erste Versuch. `ZONE_PENDING_BUCKET_EVENTS` existiert genau dafür, eine
Eimer-Änderung mitten im Fenster an ihrem eigenen Zeitstempel abzuspielen, und
sah damit naheliegend aus.

**Falsch, und der Test hat es gefangen.** Eine Behauptung ist kein Delta. So
gebucht wird aus „-2 nach 8 mm Regen": öffne bei 0, addiere die 8 mm, ziehe dann 2
ab → **+2,75**. Eine andere falsche Antwort. Das Register ist für Wasser, das
**geflossen** ist; dies ist eine Aussage darüber, **wo der Stand liegt**.

Lehre über den Fall hinaus: dass ein vorhandener Mechanismus thematisch passt,
heißt nicht, dass die Semantik passt.

## Gewählt: das Wasserzeichen verschieben

Wer den Stand nennt, hat auf den Boden geschaut. Alles davor steckt in seiner
Zahl. Also rückt `ZONE_LAST_CONSUMED` auf diesen Moment und das Fenster beginnt
dort neu. Das Register wird mitgeleert, aus demselben Grund: eine Gutschrift von
vor der Aussage ist Teil dessen, was angeschaut wurde.

## Platzierung

Im allgemeinen Zweig von `async_update_zone_config`, **nicht** in
`store.async_update_zone`. Die Begründung steht schon im Docstring von
`async_write_watered_bucket` und gilt unverändert: ein Wechsel des
Einheitensystems schreibt den Eimer um 25,4 um, ohne dass Wasser floss oder
jemand auf den Boden geschaut hat. Dieser Pfad schreibt direkt in den Store, ebenso
die Gutschrift-Pfade und das Ergebnis der Berechnung. Nur die **zwei
Behauptungs-Pfade** erreichen den Zweig: die Dienste `set_bucket`/`reset_bucket`
und das Speichern der Zone im Panel. Das Rückankern des Bodenfeuchte-Vetos auf 0
kommt ebenfalls dort an und will genau diese Behandlung.

Ein Speichern, das den Eimer unverändert lässt, bewegt nichts — das Panel schickt
bei **jedem** Einstellungs-Speichern die ganze Zone mit.

## Prüfkriterien

Vier Zusicherungen, jede einzeln durch Mutation als beißend nachgewiesen: Aufruf
entfernt (2 fallen), Wasserzeichen bleibt (die Gleichheit fällt), Register bleibt
(sein Test fällt), unveränderter Eimer wird gebucht (der Panel-Test fällt).

Der Haupttest ist als **Gleichheit** formuliert — „mit Regen vor der Behauptung"
gegen „ganz ohne Regen" — damit ET-Stub, Sonnenverlauf und Drainage-Integral sich
wegkürzen und nur der Defekt die Zahl bewegen kann. Ein Wächter-Test zeigt, dass
derselbe Regen einen **nicht** behaupteten Eimer sehr wohl bewegt.

## Falle, die unterwegs zuschlug

`test_datetime_platform_shadowing` verbietet `datetime.now(` im Quelltext von
`__init__.py`, weil das Platform-Submodul `datetime.py` den Namen überschattet.
Der Wächter sucht im **Text** und traf einen Kommentar, der die verbotene
Schreibweise ausschrieb. Der Code war durchgehend aliasiert.
