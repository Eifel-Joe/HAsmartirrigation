# Der saisonale Ausblick rechnet nach den Regeln der Integration

- **Issue:** Eifel-Joe#10 (Arbeitsreihenfolge `Eifel-Joe#42`, Punkt 11), `schwere:mittel` (bleibt, User 2026-10-05)
- **Stand:** Spec, Abschnitte 1–4 am 2026-10-05 im Chat freigegeben
- **Basis:** `upstream/master` = `bbf2e151` (v2026.10.04). `watering_calendar.py` ist Blob `6dbff934`, unverändert seit
  der Nachprüfung vom 2026-09-29. Zeilenangaben unten beziehen sich auf diesen Stand.
- **Herkunft des Codes:** `e106efb2` (`copilot-swe-agent[bot]`, 2025-07-13, „Implement 12-month watering calendar API
  and core functionality“), von JustChr in `e834d6a4` (Refactor C3) in eine eigene Datei ausgelagert, zuletzt berührt
  von `368a149e` (unser Fix für den Tag des Jahres in PyETO).

## Der Defekt

Die Monatsprognose (`async_generate_watering_calendar`) rechnet für jede Zone und jeden Monat eine „ET“ und eine
Wassermenge. Sie hat fünf Fehler. Die ersten vier betreffen die Rechnung, der fünfte das Klimamodell, aus dem sie
rechnet.

### 1. PyETO: Regen hinein und wieder heraus

`_calculate_monthly_et_pyeto` (`:298`) rechnet `abs(daily_et_delta) + precipitation / days_in_month` und gibt das mal
die Monatstage zurück. Der Kommentar in `:297` nimmt an, das Delta enthalte den Regen schon und müsse bereinigt werden.
Es enthält ihn nicht: `calculate_et_for_day` gibt `delta = -eto` zurück (`calcmodules/pyeto/__init__.py:434`).
`_calculate_monthly_watering_volume` (`:325`) zieht den Monatsregen danach wieder ab.

Folgen:
- Die Spalte „ET“ (`estimated_et_mm`) enthält den Monatsregen. Die Wetter-Ansicht zeigt genau diese Spalte.
- Die Wassermenge ist `ET × Tage`, gleich wie viel es regnet. `max(0, …)` in `:325` kann nie greifen.

### 2. Static: Tageswert als Monatswert, mit dem Vorzeichen der Rechnung

`:139` übernimmt `modinst.calculate()` als Monats-ET. Das ist ein **Tageswert**: Der andere Zweig rechnet mit `× 30`
(`:143`), und die echte Rechnung behandelt ihn als Tages-Delta. Und er trägt das **Vorzeichen der Rechnung**: negativ
heißt Bedarf (`calculation.py`, `bucket + delta`). Ein negativer Wert lässt `max(0, …)` in `:325` auf 0 fallen.

Folge: Eine Static-Zone zeigt bei jedem Bedarf 0 L.

### 3. Passthrough und andere: × 30 und ein Regenabzug, den die Rechnung nicht kennt

`:143` rechnet `average_daily_et × 30` statt mit den Tagen des Monats, anders als der PyETO-Zweig. `:325` zieht danach
den Monatsregen ab. Die echte Rechnung bucht bei Passthrough aber **keinen** Regen (`calculation.py:1176-1247`: nur
PyETO setzt `precip`). Dasselbe gilt für Static.

### 4. Kc fehlt

Die echte Rechnung skaliert den ET-Teil jeder Zone mit ihrem Pflanzenfaktor (`calculation.py:1229-1246`,
`et_delta = delta × kc × …`), den Regen nicht. Die Prognose kennt Kc nicht. Kc kam nach der Prognose dazu, sie wurde
nie nachgezogen.

### 5. Das Klimamodell widerspricht dreimal seinen eigenen Kommentaren

`_generate_monthly_climate_data` (`:184-257`) erfindet das Monatsklima aus dem Breitengrad allein. Drei Kurven haben
ihr Maximum im Juli, ihre Kommentare sagen „im Winter“:

| Kurve | Code | Kommentar | Norden heute |
|---|---|---|---|
| Luftfeuchte (`:230`) | `65 + 15·cos((m−7)·π/6)` | „higher in winter for temperate zones“ | Jan 50 %, Jul 80 % |
| Wind (`:233`) | `3 + 1·cos((m−7)·π/6)` | „slightly higher in winter“ | Jan 2, Jul 4 m/s |
| Niederschlag gemäßigt (`:219`) | `1.5 − 0.5·cos((m−1)·π/6)` | „More in winter“ | Jan 60, Jul 120 mm |

Dazu spiegelt die Südhalbkugel nur die Temperatur (`:210-211`). Luftfeuchte, Wind, Niederschlag und
`average_daily_et` („Higher ET in summer“, `:252-253`) bleiben im Süden in der Phase des Nordens, im Widerspruch zu
„Winter“ und „Sommer“ in ihren Kommentaren.

Die **Konstanten** des Modells (gemäßigt 15 ± 15 °C, 60 mm Grundniederschlag, ± 5 K Tagesspanne, Breitengrenzen
23,5 / 35 / 45°) widersprechen keinem Kommentar. Sie sind grob (am Standort von HA-Prod ein Juli-Mittel von 30 °C), aber
das ist Modellgüte, kein Fehler im Sinne dieser Arbeit.

### Gemessen auf HA-Prod

2026-10-05, v2026.10.05b1, GET auf `/api/irrigation_plus/watering_calendar` (derselbe Abruf, den die Wetter-Ansicht
macht). Alle drei Zonen rechnen mit PyETO.

| Monat | „ET“ (mm) | Niederschlag (mm) | Mitteltemperatur | Kirschlorbeer (L) |
|---|---|---|---|---|
| Januar | 82,77 | 60 | 0 °C | 1 138,6 |
| Juli | 307,32 | 120 | 30 °C | 9 366,0 |

Kirschlorbeer: 25 m², Multiplikator 2. `(82,77 − 60) × 2 × 25 = 1 138,5` und `(307,32 − 120) × 2 × 25 = 9 366`: Die
Menge ist die reine ET, der Regen senkt sie in keinem Monat.

## Reichweite

- **Einstiege:** Dienst `generate_watering_calendar` (`services.py:247`, legt das Ergebnis in `hass.data` ab und feuert
  `irrigation_plus_watering_calendar_generated`), WebSocket `irrigation_plus/watering_calendar` (`websockets.py:663`),
  HTTP-View `/api/irrigation_plus/watering_calendar` (`websockets.py:682`). Die beiden letzten rechnen und antworten
  nur.
- **Panel:** Die Wetter-Ansicht (`frontend/src/views/weather/view-weather-data.ts:54-69`, `_renderSeasonal`) holt die
  Prognose bei jedem Öffnen und zeigt aus dem **ersten** Zonen-Eintrag Monat, ET, Niederschlag und Temperatur. Die
  Wassermenge zeigt sie nicht; die gibt es nur über Dienst, WebSocket und HTTP-View.
- **Keine Bewässerungsentscheidung** liest die Prognose.
- **Doku verspricht mehr:** `docs/configuration-weather-location.md:36` „A 12-month climate estimate for your
  location … It answers ‚how much watering should I expect over the year‘“; Dienstbeschreibung „based on
  representative climate data“ (`services.yaml`, acht `translations/*.json`, `docs/usage-services.md:18`).

## Anforderungen

- **A1** Die Spalte „ET“ ist bei PyETO die reine Referenz-ET des Monats, ohne Regen.
- **A2** Regen wird genau dort und genau einmal abgezogen, wo die echte Rechnung ihn bucht, und die Prognose fragt dafür
  dieselbe Regel (`calculation.zone_module_models_weather`), statt sie neu zu formulieren.
- **A3** Static liefert bei Bedarf eine positive Monatsmenge; Tageswerte werden mit den Tagen des Monats hochgerechnet,
  in allen drei Zweigen.
- **A4** Der ET-Teil wird mit dem Kc der Zone skaliert, der Regen nicht, wie in der echten Rechnung.
- **A5** Jede Jahreskurve des Klimamodells tut, was ihr Kommentar sagt, und folgt auf der Südhalbkugel der dortigen
  Jahreszeit.
- **A6** Wer die Prognose sieht oder abruft, erfährt, dass sie eine grobe Veranschaulichung aus dem Breitengrad ist.

## Entscheidungen (User, 2026-10-05, im Chat)

- **E1 Zweck: „Nur Fehler beheben“.** Rechenfehler weg, das Klimamodell nur richtig herum gedreht und klar als grobe
  Illustration beschriftet; kein Anspruch auf Ortsgenauigkeit. Verworfen wurden „Wasserbedarf je Zone“ (echtes
  Ortsklima), „Saisonüberblick“ (glaubwürdige Klimatabelle) und „Entfernen vorschlagen“.
- **E2 Ansatz 1, punktuell im Bestand** (siehe *Verworfen* für 2 und 3).
- **E3** Rechenregeln wie unten (Abschnitt 1 im Chat).
- **E4** Klimamodell: nur Phasen und Halbkugel, Konstanten bleiben (Abschnitt 2). Auch der gemäßigte Niederschlag folgt
  seinem Kommentar, obwohl der heutige Juli-Schwerpunkt für Mitteleuropa zufällig näher an der Wirklichkeit liegt.
- **E5** Beschriftung an vier Stellen (Abschnitt 3).
- **E6 Upstream direkt als PR**, ohne vorheriges Issue. Der PR-Text sagt, dass das Klimamodell synthetisch bleibt und nur
  beschriftet wird, und bietet echte Klimadaten als Folgeschritt an.
- **E7** `schwere:mittel` bleibt: Die Wetter-Ansicht zeigt auf HA-Prod sichtbar falsche Werte.

## Das Design

### Rechenregeln je Monat

`D` = Tage des Monats im Bezugsjahr 2024, wie bisher (`calendar.monthrange(2024, m)[1]`, Februar 29).
`P` = Monatsniederschlag aus dem Klimamodell.
`kc` = `zone.get(const.ZONE_KC, const.CONF_DEFAULT_KC)`, und `None` heißt `const.CONF_DEFAULT_KC`, genau wie
`calculation.py:1229-1231`.

| Modul | `estimated_et_mm` | Bedarf in mm |
|---|---|---|
| PyETO | `abs(calculate_et_for_day(…)) × D` | `max(0, ET × kc − P)` |
| Static | `max(0, −calculate()) × D` | `ET × kc` |
| Passthrough / andere | `average_daily_et × D` | `ET × kc` |

- Ob `P` abgezogen wird, entscheidet `calculation.zone_module_models_weather(self.store, zone)`, nicht der Zweig in der
  Prognose. Heute heißt das: nur PyETO.
- `estimated_watering_volume_liters` = Bedarf × Multiplikator × Fläche in m² (bei imperialem System aus ft² umgerechnet,
  wie bisher).
- `estimated_et_mm` bleibt die ET **vor** Kc: Die Wetter-Ansicht zeigt sie als Wert des Standorts, Kc gehört zur Zone.
- Bewusst bleibt es bei der **Monatsbilanz**. Die echte Rechnung bucht tageweise in einen Eimer mit Obergrenze und
  Drainage; Regen über der Obergrenze geht dort verloren. Die Prognose unterschätzt damit den Bedarf in nassen Monaten.
  Das gehört zur Modellgüte, nicht zu dieser Arbeit.

### Klimamodell

Ein Vorzeichen für alle Jahreskurven: `s = −1` auf der Südhalbkugel, sonst `+1`. Die Bedingung bleibt die heutige
(`self._latitude and self._latitude < 0`). Mit `c(m) = cos((m − 7)·π/6)`:

| Größe | künftig | Norden | Änderung |
|---|---|---|---|
| Mitteltemperatur | `base + variation · s · c(m)` | Maximum Juli | keine |
| Luftfeuchte | `65 − 15 · s · c(m)` | Jan 80 %, Jul 50 % | Phase |
| Wind | `3 − 1 · s · c(m)` | Jan 4, Jul 2 m/s | Phase |
| Niederschlag, Breite > 35° | `60 · (1.5 − 0.5 · s · c(m))` | Jan 120, Jul 60 mm | Phase |
| Niederschlag, Breite ≤ 35° | `60 · (1.0 + 0.3 · sin((m − 1)·π/6))` | Maximum April | keine (Kommentar nennt keine Jahreszeit) |
| `average_daily_et` | `2 + 2 · s · c(m)` | Maximum Juli | nur Süden |
| Taupunkt | `avg_temp − (100 − humidity) / 5` | folgt der Feuchte | Formel unverändert |

Alle Konstanten bleiben: Temperaturbänder, 60 mm, ± 5 K, Druck aus der Höhe, Bandgrenzen.

### Beschriftung

| Stelle | künftig |
|---|---|
| Karte „Saisonaler Ausblick“, `view-weather-data.ts` `_renderSeasonal` | Eine Hinweiszeile im vorhandenen Stil `.weather-note` über der Tabelle, nur wenn Daten da sind (sonst steht wie bisher `calendar.no_data`). Neuer Schlüssel `panels.setup.weather_data.seasonal_note` in **allen 8** Sprachdateien unter `frontend/localize/languages/`. EN: „Illustrative values derived from your latitude only — not measured weather data.“ DE: „Veranschaulichung allein aus dem Breitengrad – keine gemessenen Wetterdaten.“ Die übrigen sechs werden beim Bau übersetzt. |
| Dienstbeschreibung `generate_watering_calendar` | „… based on an illustrative climate derived from latitude only“ in `services.yaml` und in `services.generate_watering_calendar.description` aller 8 `translations/*.json`. |
| Doku | `docs/configuration-weather-location.md`, Abschnitt „Seasonal outlook“: sagt, was es ist (aus dem Breitengrad abgeleitet, nicht gemessen, keine Prognose für den Standort), dass „ET“ die Referenz-ET ist und dass es die Litermengen je Zone nur über den Dienst gibt. `docs/usage-services.md:18` entsprechend. |
| API-Feld `calculation_notes` | „Illustrative {month} climate derived from latitude only“ (nur Englisch, wie bisher). |

Der PR bringt die neu gebauten `dist`-Bundles mit (Frontend-Änderung).

### Betroffene Stellen

- `custom_components/irrigation_plus/watering_calendar.py`: die drei Zweige in `_calculate_monthly_watering_for_zone`,
  `_calculate_monthly_et_pyeto`, `_calculate_monthly_watering_volume`, `_generate_monthly_climate_data`, der Text von
  `calculation_notes`.
- `custom_components/irrigation_plus/frontend/src/views/weather/view-weather-data.ts`, acht Sprachdateien unter
  `frontend/localize/languages/`, `frontend/dist/` (vier Bundles).
- `custom_components/irrigation_plus/services.yaml`, acht `translations/*.json`.
- `docs/configuration-weather-location.md`, `docs/usage-services.md`.
- Tests: `tests/test_watering_calendar.py` (neue Tests, zwei Fixtures ergänzt).

## Schwester-Pfade geprüft

- **Die echte Rechnung** (`calculation.py:1176-1247`) ist die Referenz für Regen, Kc und das Tages-Delta. Sie stellt die
  Regen-Frage lokal (`:1179`, `m[MODULE_NAME] == "PyETO"`) mit derselben Antwort wie
  `zone_module_models_weather`. Kein Defekt, nicht Teil dieser Arbeit.
- **Live-Schätzung** fragt schon `zone_module_models_weather` (`live_estimate.py:693`, `:817`) und liest Kc wie die
  Rechnung (`:1519`, `:1905`).
- **`day_projection.forecast_rain_mm`** ist eine weitere Projektion mit einer eigenen, abweichenden Regel. Sie hat ihr
  eigenes Issue (Eifel-Joe#29) und bleibt draußen.
- **Die Wetter-Ansicht** nimmt ihre ET-Spalte vom ersten Zonen-Eintrag und nimmt an, die Klimaspalten seien für alle
  Zonen gleich (`view-weather-data.ts:63-64`). Für Niederschlag und Temperatur stimmt das; für „ET“ nicht, sobald Zonen
  verschiedene Module haben (vorher wie nachher). Siehe *Ausdrücklich nicht*.

## Ausdrücklich nicht in dieser Arbeit

- Konstanten und Bänder des Klimamodells; jede Änderung, die das Modell „besser“ statt „wie kommentiert“ macht.
- Echte Klimadaten (Open-Meteo-Archiv, HA-Langzeitstatistik der gemappten Sensoren). Wird angeboten, nicht gebaut.
- Eine tageweise Eimer-Simulation (Obergrenze, Drainage, Schwelle).
- Welche Zone die Wetter-Ansicht für die ET-Spalte nimmt.
- Die Prognose zu entfernen.
- Die Phase des tropischen und subtropischen Niederschlags.

## Verworfen

- **Ansatz 2, reine Funktionen herauslösen:** klarer geschnitten, aber ein Umbau in einem Fehler-PR; mehr Diff, ohne
  mehr zu beheben.
- **Ansatz 3, die echte Tagesrechnung mit Klimazeilen füttern:** maximal treu, aber die Prognose hinge am
  zustandsbehafteten Läufer (Eimer, Drainage, Stundenpuffer, Vorhersage).
- **Beschriftung über den Kartentitel** („Seasonal outlook (illustrative)“): kürzer, sagt aber nicht, woraus die Werte
  kommen.

## Tests

Neu in `tests/test_watering_calendar.py`, jeder vor dem Fix rot:

1. PyETO-ET ohne Regen: Tageswert −2,0, Juli (31 Tage), Niederschlag 50 → `62.0` (heute `112.0`).
2. PyETO-Menge zieht den Regen einmal ab: Zone mit PyETO-Modul, ET 62, P 50, Kc 1, Multiplikator 1, 10 m² → `120 L`.
3. Static: Delta −3,0, Juli → ET `93.0`, Menge `93 × Kc × Multiplikator × Fläche`, ohne Regenabzug (heute 0 L).
4. Static mit positivem Delta → ET 0, Menge 0.
5. Passthrough rechnet mit den Monatstagen (Februar 2024: 29) und zieht keinen Regen ab.
6. Kc 0,5 halbiert den ET-Teil, der Regen bleibt ungeteilt.
7. Klimamodell, Norden: Feuchte, Wind und gemäßigter Niederschlag im Januar höher als im Juli; Süden umgekehrt;
   `average_daily_et` im Norden im Juli, im Süden im Januar am höchsten; tropischer Niederschlag unverändert
   (festgenagelt).
8. Der neue Sprachschlüssel steht in allen acht Sprachdateien (die vorhandenen Vollständigkeitstests der Kataloge
   müssen grün bleiben).

Bestehende Tests: `test_calculate_monthly_watering_volume` und `…_no_irrigation_needed` (`:166`, `:186`) benutzen eine
Zone **ohne Modul** und erwarten den Regenabzug. Sie bekommen ihr PyETO-Modul ausdrücklich, ihre Erwartungen (4 000 L,
0 L) bleiben. *(Präzisiert in der Planung, siehe unten: Grün blieben sie auch ohne, der Mock-Store antwortet auf jede ID
mit PyETO; das Modul steht trotzdem in der Zone, damit die Tests nicht von diesem Auffangverhalten leben.)*

Danach: volle Suite mit Namensvergleich gegen eine Baseline auf derselben Basis; Mutationslauf gegen die geänderten
Zeilen (jede Mutation muss einen Test rot machen).

## Ende-zu-Ende-Kriterium

Erst auf HA-Test (Pre-Release per HACS), nach dem Release auch auf HA-Prod, je mit demselben GET auf
`/api/irrigation_plus/watering_calendar` wie oben:

1. Für jede PyETO-Zone und jeden Monat gilt
   `estimated_watering_volume_liters = round(max(0, estimated_et_mm × kc − average_precipitation_mm) × Multiplikator ×
   Fläche, 1)`, nachgerechnet aus den Spalten der Antwort und der Zonen-Konfiguration aus den Diagnostics. Toleranz
   `0,005 mm × kc × Multiplikator × Fläche + 0,05 L`, weil die Antwort die ET auf 0,01 mm und die Menge auf 0,1 L rundet
   (Kirschlorbeer: 0,3 L).
2. Niederschlag Januar 120 mm, Juli 60 mm (Norden, Breite > 35°).
3. Die Karte „Saisonaler Ausblick“ zeigt die Hinweiszeile (Sichtprüfung im Panel nach Strg+F5).

Vorher-Werte für den Vergleich stehen oben unter *Gemessen auf HA-Prod*.

## Präzisierungen aus der Planung (2026-10-05)

- **Fixtures der alten Volumen-Tests:** `mock_store.get_module` liefert für jede ID (auch `None`) das PyETO-Modul. Die
  zwei Tests wären mit A2 also auch ohne Modul in der Zone grün geblieben; die Spec sagte das Gegenteil. Sie bekommen
  das Modul trotzdem ausdrücklich (Plan, Task 2).
- **Lokale teardown-ERRORs:** Jeder Test am `coordinator`-Fixture endet lokal zusätzlich mit „Lingering timer after
  test“ (Zeit-Listener `_reset_event_fired_today`); alle elf bestehenden Kalender-Tests stehen so in der Baseline
  `bbf2e151`, in JustChrs CI laufen sie sauber. Die neuen Fixture-Tests kommen deshalb lokal als neue ERROR-Namen in
  den Namensvergleich, sonst nichts.
- **Bundles:** Der Probelauf änderte genau `irrigation-plus.js` und `irrigation-plus-card-impl.js` (Kataloge);
  `-card.js` und `-card-legacy.js` bleiben inhaltlich gleich.

## Lieferung

- Worktree `D:\Entwicklung\HASI\issue10-work\wt` von `upstream/master` (`--no-track`), Branch `fix/seasonal-outlook`.
- Ein PR an JustChr: Fix, Tests, `dist`. Texte vorher deutsch, dann englisch zur Freigabe; keine Verweise auf unsere
  Issues (Grep über Diff und Commit-Messages).
- Danach: Eifel-Joe#10 bekommt einen Kommentar und `upstream:gemeldet`; `Eifel-Joe#42` Punkt 11; production-Rebuild als
  Pre-Release (HA-Prod nur auf Zuruf); Spec und Plan auf `archive/design-history`.
