# Task 7 — Fix-Runde 1

Dein Commit `2c374da9` ist wörtlich nach Plan. Die Task-Review hat im **Plancode** eine Lücke gegen die Spec gefunden;
der Controller hat entschieden: **wird behoben** (Spec ist bindend, der Plan hat diesen Unterfall nicht bedacht).

## Befund (Wortlaut der Review, `review-t7-report.md`, Important 1)

> `live_estimate.py:1193-1203` — die 0-Abkürzung sitzt hinter `if blend is None: return None`; bei fehlender/unvollständiger
> Prognose rutscht die Kette trotz Anteil 0 doch zum Wetterdienst (Plancode, wörtlich aus dem Probelauf; Spec G9 „nie wegen
> einer Sperre“).
> Szenario: PyETO-Zone mit `forecast_days > 0` (Standard ist 0, `calcmodules/pyeto/__init__.py:56`), pausierende Gruppe,
> ein Pflichtfeld der Tagesform das ganze Fenster stumm (Anteil 0), und `_commit_forecast` (`:898-922`) liefert `None` —
> keine Tagesprognose in `inputs["forecast"]` oder ein Prognosetag ohne ein Feld aus `DAILY_FORM_FIELDS`. Der Commit bucht
> dann 0 (er fragt die Gleichung nicht, `calculation.py:1316`, und die Prognose braucht er nicht). Der Spiegel gibt `None`
> zurück, `mirrored is None` → `elif rows:` (`:1550`) = Stundenreihe des Wetterdienstes (`method="hourly"`), also genau die
> Überschätzung, die G9 verhindern soll.
> Fix: den Anteil vor der Prognose-Suche bestimmen, aber *nach* der Frage „läuft der Commit überhaupt die Tagesgleichung“
> (`_daily_form_applies`) — die Abkürzung darf Zonen nicht erfassen, deren Commit die Stundenform rechnet. Test dazu:
> Instanz mit `forecast_days = 2` (wie `test_live_estimate_replayed_balance.py:1516`), `daily_forecast=None`, Temperatur ganz
> stumm, `rows=_provider_rows(0.0)` → erwartet `daily_mirror`, `et_since == 0.0`. Der Teilanteil-Fall (0 < Anteil < 1) mit
> `blend is None` bleibt laut Spec „heutiger Weg“.

Vom Controller am Code bestätigt (`calculation.py:1311-1316`: bei `share == 0` wird `modinst.calculate` nicht gerufen;
`live_estimate.py:876-880`: `_mirror_blend` = `_daily_form_applies` und dann `_commit_forecast`).

## Was zu tun ist (TDD)

1. **Test zuerst**, in `tests/test_live_estimate_silent_sensor_daily.py`, in der Klasse
   `TestNothingMeasuredIsNothingBooked` (dort steht schon `test_it_does_not_fall_back_to_a_weather_service`; nutze deren
   Fixtures und Muster). Neuer Test, Name:
   `test_a_zone_that_averages_forecast_days_in_needs_no_forecast_for_it`. Aufbau wie im Befund: Modulinstanz mit
   `forecast_days = 2` (Muster `tests/test_live_estimate_replayed_balance.py` um Zeile 1516), keine Tagesprognose
   (`daily_forecast=None` bzw. was das Fixture dafür vorsieht), Temperatur das ganze Fenster stumm, Stundenreihe des
   Wetterdienstes vorhanden (`rows=_provider_rows(0.0)` o. ä.) — erwartet: Methode `daily_mirror`, ET seit dem Anker
   `== 0.0`. Docstring in einem Satz, englisch, im Stil der Datei, ohne Spec-/Plan-Kürzel.
2. **RED** laufen lassen: nur dieser Test (`-k test_a_zone_that_averages_forecast_days_in_needs_no_forecast_for_it`).
   Erwartet: failed (Methode `hourly` statt `daily_mirror` oder ET ≠ 0). Ausgabe festhalten. Ist er grün, STOP und melden.
3. **Code** in `custom_components/irrigation_plus/live_estimate.py`, `_daily_mirror_et`: Reihenfolge
   `_daily_form_applies` → Anteil (bei 0 sofort `_DayTotal(0.0, TIER_OBSERVED)`) → erst dann `_commit_forecast`
   (bei `None` weiter `return None`). `_mirror_blend` selbst nicht ändern, wenn es noch andere Aufrufer hat (prüfen per
   `grep -n "_mirror_blend" custom_components/irrigation_plus/*.py`); sonst die kleinste Umstellung wählen und im Bericht
   begründen. **Die zwei Zeilen
   `                    return _DayTotal(0.0, TIER_OBSERVED)` (20 Leerzeichen) und `            total *= share` (12)
   müssen danach je genau einmal und unverändert in der Datei stehen** (sie sind Anker eines Mutationslaufs):
   `grep -c "^                    return _DayTotal(0.0, TIER_OBSERVED)" …` und `grep -c "^            total \*= share" …`
   → je `1`.
   Ein knapper Kommentar an der Umstellung, im Stil der umgebenden Kommentare (englisch): warum der Anteil vor der Prognose
   kommt (der Commit fragt bei Anteil 0 weder Gleichung noch Prognose; ohne das fiele die Kette zum Wetterdienst). Den
   Docstring-Absatz „A pausing sensor group's commit books only the part …“ nur anpassen, wenn er sonst falsch würde.
4. **GREEN:** `TZ=UTC … -m pytest tests/test_live_estimate_silent_sensor_daily.py -p _local_socket_unblock -q` → alle
   `passed` (4 statt 3), dazu Teardown-ERROR „Lingering timer“.
5. **Prüfen:** Lint wie im Brief (black + ruff@0.16.10), dann
   `../task_compare.sh t7f1 $(ls tests/test_live_estimate*.py tests/test_silent_sensor*.py tests/test_next_irrigation*.py)`.
   Erwartet wie t7, plus 1 neuer Teardown-ERROR in `test_live_estimate_silent_sensor_daily.py`.
6. **Commit** (neuer Commit, kein amend), gezielt stagen (`live_estimate.py` und die Testdatei), Message wörtlich:

```
fix(live): a silent window books nothing even without a forecast to mirror

The mirror asked for the commit's forecast blend before it looked at the
share, so a zone that averages forecast days in, with no usable forecast
in hand, returned None and the source chain moved on to a weather
service's hourly series. The commit books nothing when a field its daily
form needs was silent for the whole window, and asks neither the
equation nor the forecast for that. The share is now taken once the
daily form applies and before the forecast is looked up; a partly silent
window without a forecast to mirror still goes the way it went before.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

## Bericht

An `D:\Entwicklung\HASI\issue8-pr3-work\sdd\task-7-report.md` **anhängen** (Abschnitt „Fix-Runde 1“): Test (Name, Inhalt
kurz), RED-Befehl + Ausgabe, Code-Änderung, GREEN-Befehl + Ausgabe, die zwei Anker-`grep -c`, Lint, `task_compare`-Ausgabe,
Commit-SHA. Antwort an den Controller kurz wie zuvor. Weiter gelten alle Regeln des Briefs (keine Subagenten, keine volle
Suite, kein Push, nichts außerhalb des Worktrees).
