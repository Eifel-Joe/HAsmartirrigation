# Nach-Review Task 7, Fix-Runde 1 (`2c374da9..08728aa7`)

Geprüft: Fix-Diff `review-t7-fix1.diff`, die Quelle im Worktree `issue8-pr3-work\wt` (nur gelesen), `calculation.py:570-583, 1299-1378`.
Keine Tests gelaufen (Läufe liegen beim Controller). Zustand: Kopf `08728aa7`, Arbeitsbaum sauber (`git status --short` = 0 Zeilen).

## Befund Important 1 (0-Abkürzung hinter der Prognose-Suche) — ADDRESSED

Belege (Datei:Zeile, Stand `08728aa7`):

- `live_estimate.py:1193-1194`: `_daily_form_applies` kommt zuerst; ohne sie `return None`. Zonen, deren Commit die Stundenform rechnet, werden von der Abkürzung nicht erfasst (Vorgabe des Befunds).
- `live_estimate.py:1200-1207`: Danach der Anteil; bei `share == 0` sofort `_DayTotal(0.0, TIER_OBSERVED)`, ohne dass `_commit_forecast` gefragt wurde. Genau das Verhalten des Commits: bei Anteil 0 entfällt die Gleichung (`calculation.py:1316`, `if hourly is None and share != 0:`), und `delta` bleibt 0.0.
- `live_estimate.py:1208-1210`: Erst jetzt `_commit_forecast`, bei `None` weiter `return None`. Der Teilanteil-Fall (0 < Anteil < 1) ohne spiegelbare Prognose bleibt damit der heutige Weg (`None` -> Quellenkette), wie die Spec es will.
- Kommentar `:1195-1199` erklärt die Reihenfolge knapp und sachlich richtig (englisch, im Stil der Umgebung).
- Anker-Zeilen: `return _DayTotal(0.0, TIER_OBSERVED)` steht genau einmal (`:1207`, 20 Leerzeichen), `total *= share` genau einmal (`:1229`, 12 Leerzeichen); `grep -c` selbst gezogen: 1 und 1.

### Verhält sich der Spiegel sonst wie vorher? — ja

Alt: `blend = _mirror_blend(...)` (= `_daily_form_applies`, dann `_commit_forecast`), bei `None` raus, dann Anteil. Neu: `_daily_form_applies`, Anteil, `_commit_forecast`. Fallweise:

| Fall | alt | neu |
|---|---|---|
| Tagesform gilt nicht | `None` | `None` (gleiche Stelle, vor jedem Anteil) |
| gilt, Anteil 0, Prognose spiegelbar | `_DayTotal(0.0, OBSERVED)` | gleich |
| gilt, Anteil 0, Prognose nicht spiegelbar | `None` | `_DayTotal(0.0, OBSERVED)` (die gewollte Änderung) |
| gilt, Anteil in (0,1) oder `None`, Prognose nicht spiegelbar | `None` | `None` |
| gilt, Anteil in (0,1) oder `None`, Prognose spiegelbar | `_composed_day_et` ... `total *= share` | identisch (`:1211-1230` unverändert) |

Die in der Umstellung vorgezogenen Aufrufe sind seiteneffektfrei und werfen nicht anders als zuvor: `store.get_module` (reine Lesung), `required_sensor_fields` (Wörterbuch-Zugriff, `calculation.py:81-93`), `valid_share` (reine Rechnung, `sensor_liveness.py:223-235`); `_commit_forecast` ist eine reine `staticmethod` (`:882-923`). Die Kette danach ist für alle Fälle außer dem einen unverändert. Der Zweig `fields is None` bleibt, wie schon in der ersten Review vermerkt, für den Spiegel unerreichbar (nur PyETO besteht `zone_module_models_weather`).

### Weitere Aufrufer von `_mirror_blend`

Genau einer: `live_estimate.py:2023` (`_intraday_for_zone`, Hochrechnung zum Entscheidungspunkt). `_mirror_blend` (`:876-880`) ist unverändert; sein Aufrufer braucht Guard und Prognose-Prüfung weiter zusammen (`own_equation = blend is not None`, `:2026`). Unverändert richtig. Die Begründung des Implementers (zweiter Aufrufer, deshalb nicht angefasst) stimmt. Docstring von `_daily_form_applies` (`:848-849`, „`_mirror_blend` asks that separately“) bleibt wahr.

### Prüft der neue Test, was er soll? — ja

`test_a_zone_that_averages_forecast_days_in_needs_no_forecast_for_it` (`tests/test_live_estimate_silent_sensor_daily.py:123-139`):

- Aufbau trifft den Befund: `instance.forecast_days = 2` (dieselbe Instanz geht über `inputs["modules"]` in den Spiegel, `_estimating_inputs` `test_live_estimate_replayed_balance.py:1317`), `inputs["forecast"] = daily_forecast = None` (Default, `:1295/1308`; die `forecast=_hourly_forecast()` aus `_estimate` landet in `inputs["hourly_forecast"]`, nicht in `inputs["forecast"]`), Temperatur ab 4 h vor dem Anker offen stumm (`_silent(store, zone, -4)`, ganzes Fenster blockiert -> Anteil 0), Stundenreihe des Wetterdienstes `_provider_rows(0.0)` als verfügbare Alternative.
- Würde auf `2c374da9` rot: dort `_mirror_blend` -> `_commit_forecast` -> `days=2`, `forecast=None` -> `None` (`:898-903`) -> Spiegel `None` -> `buffer_et` ist bei der Tagesform `None` -> `elif rows:` (`:1557`) -> `method="hourly"`. Deckt sich mit der RED-Ausgabe des Implementers (`'hourly' == 'daily_mirror'`, Bericht Z. 110). Selbst nachvollzogen, nicht neu gelaufen.
- Prüft Methode, `et_since == 0.0` und Gleichlauf mit dem echten Commit-Eimer (`calculate_module` mit denselben `blocked`), nicht gegen eine Konstante.
- Docstring ein Satz, englisch, ohne Kürzel.

### Verweise auf Issues/Spec/Plan — keine

Diff (Code, Kommentar, Test, Docstring) und Commit-Message auf `#`, Spec, Plan, PR, Befund, Task, G9, Issue durchsucht: keine Treffer. Message wörtlich nach Brief, letzte Zeile `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Blobs in `08728aa7` ohne CR (Python-Bytezählung: 0 in beiden Dateien). Diffstat 2 Dateien, +28/-2 (`9/2` und `19/0` per `--numstat`).

## New breakage in fix diff

- Critical: none
- Important: none
- Minor (beide optional):
  1. `live_estimate.py:1197` (Kommentar) und Commit-Message-Satz „asks neither the equation nor the forecast for that“: etwas zu pauschal. Der Commit *holt* die Prognose für PyETO-Zonen mit `forecast_days > 0` vorher durchaus (`calculation.py:570-583`, `async_calculate_all`), er *verwendet* sie bei Anteil 0 nur nicht (`:1316`). Gemeint und für den Spiegel entscheidend ist „braucht sie nicht“. Die Message steht wörtlich im Brief, ein Nachziehen wäre nur Kosmetik und würde einen amend verlangen — daher nicht empfohlen; der Kommentar im Code könnte bei Gelegenheit „does not use“ sagen.
  2. Die Reihenfolge Guard -> Anteil (nicht Anteil -> Guard) ist durch keinen Test festgenagelt, der Anteil 0 *und* eine Stundenform-Zone zugleich hat (`tests/test_live_estimate_silent_sensor.py` kennt nur `hourly_sensor`, `:73`). Durch Lesen bestimmt, nicht per Mutation geprüft. Der Brief verlangt die Reihenfolge ausdrücklich; sie steht richtig im Code. Wer sie absichern will: Stundenform-Zone, Temperatur ganz stumm, Puffer so, dass `buffer_et` `None` ist -> erwartet `method != "daily_mirror"`.

## Out-of-scope observations

- Die Hochrechnung zum Entscheidungspunkt (`live_estimate.py:2017-2036`) liest den Anteil weiter nicht: `_aggregate_live_window` ohne `blocked` (`:2017`), `_composed_day_et` ohne `blocked` (`:2027-2036`), und bei `forecast_days > 0` ohne Prognose ist dort `own_equation` falsch (`:2026`), die Zone wird also mit der Fremdgleichung hochgerechnet. Im Befund-Szenario steht jetzt der Live-Eimer richtig bei „0 gebucht“, die Hochrechnung rechnet den Rest aber ungeschnitten. Das ist der vom Controller schon abgegrenzte nächste Task (Doku-Satz „The live estimate leaves out the same time …“ erst dann voll wahr, wie in der ersten Review vermerkt).
- Der neue Test verwendet die Sensor-only-Fixture (`CONF_USE_WEATHER_SERVICE: False`) mit `forecast_days = 2`; auf einer echten Installation überspringt der Commit eine solche Zone ganz (`calculation.py:576-586`, so auch die Docstring-Aussage `tests/test_live_estimate_without_hourly_calculation.py:336-340`). Für die geprüfte Gleichheit Spiegel gegen `calculate_module` unschädlich; das Befund-Szenario selbst (Wetterdienst da, Prognose für die Zeile unvollständig) ist damit nur als Spiegel-/Commit-Paar abgebildet, nicht als ganze Installation.
- Festplatte `C:` ist voll (Implementer-Bericht Z. 177, bei mir ebenfalls ein `head: No space left on device`); das kann Läufe und Werkzeug-Ausgaben beeinträchtigen.
