# Task 9 — Fix-Runde 1 (nur Test)

Dein Commit `e5d184e3` ist wörtlich nach Plan. Die Task-Review hat eine Testlücke gefunden; der Controller hat entschieden:
**wird behoben, nur im Test** (der Produktionscode bleibt unverändert).

## Befund (Wortlaut der Review, `review-t9-report.md`, Important)

> Die Entscheidung "ungedrosselt" (`sensor_liveness.py:530`) wird von keinem der 6 Tests festgehalten. Die Tests doubeln nur
> `async_refresh_zone_estimates`. Stellt man auf `..._throttled` um, bleiben alle 6 grün: Am `__new__`-Koordinator ist
> `_zone_estimates_refreshed_at` nicht gesetzt, die gedrosselte Methode ruft also durch zum Mock. Genau das ist der
> Spec-Wortlaut, den der User verworfen hat.
> Fix, nur im Test (`tests/test_sensor_liveness_coordinator.py:1235`): In `_silent_station` zusätzlich
> `coord.async_refresh_zone_estimates_throttled = AsyncMock()` setzen. Im Öffnen-Test dann `.assert_not_awaited()` ergänzen.
> Zur Probe `:530` auf die gedrosselte Variante stellen, der Test muss rot werden.

Hintergrund (freigegeben vom User): Die gedrosselte Neuberechnung verwirft jeden Aufruf innerhalb von 60 s nach der letzten;
eine Pufferzeile kurz vor dem Öffnen hätte den Anstoß geschluckt, und bei einer stummen Station kommt danach keine mehr.

## Was zu tun ist

1. **Test** in `tests/test_sensor_liveness_coordinator.py`, Klasse `TestTheEstimateFollowsTheRecord`: im Helfer
   `_silent_station` (bzw. wo der Koordinator für diese Klasse gebaut wird) zusätzlich
   `coord.async_refresh_zone_estimates_throttled = AsyncMock()`; im Test für das **Öffnen** eines Ausfalls einer
   pausierenden Gruppe nach der vorhandenen Prüfung auf die ungedrosselte Methode ergänzen:
   `coord.async_refresh_zone_estimates_throttled.assert_not_awaited()`. Ist es im Schließen-Test genauso einfach, dort
   ebenfalls. Nichts sonst an den Tests ändern.
2. **GREEN auf dem jetzigen Code:** `-k TestTheEstimateFollowsTheRecord` → `6 passed`.
3. **RED per Probe-Mutation** (belegt, dass der Test die Entscheidung hält): in
   `custom_components/irrigation_plus/sensor_liveness.py` die Stelle (~Zeile 530), an der
   `async_refresh_zone_estimates` geholt/aufgerufen wird, vorübergehend auf `async_refresh_zone_estimates_throttled`
   ändern → derselbe Lauf muss **failed** zeigen (mindestens der Öffnen-Test). Ausgabe festhalten. Dann die Änderung mit
   dem Edit-Werkzeug exakt zurücknehmen und belegen: `git diff --quiet -- custom_components/irrigation_plus/sensor_liveness.py && echo restored`.
   Kein `git checkout`, kein `git stash`.
4. **Prüfen:** Lint wie im Brief (mit `UV_CACHE_DIR` auf D:), dann
   `../task_compare.sh t9f1 $(ls tests/test_live_estimate*.py tests/test_silent_sensor*.py tests/test_sensor_liveness*.py tests/test_next_irrigation*.py)`
   → wie t9 (passed-Zahl gleich, nichts entfällt außer den zwei bekannten, keine neuen FAILED).
5. **Commit** (neuer Commit, kein amend), nur die Testdatei stagen, Message wörtlich:

```
test(liveness): the refresh after an outage is the unthrottled one

The check refreshes the estimates through the unthrottled call on
purpose: the throttled one drops any call within a minute of the last
refresh, and a silent station sends no row afterwards to retry. The
tests only doubled the unthrottled call, and on a coordinator built
without a refresh history the throttled one passes straight through to
it, so switching to it went unnoticed. The throttled call is now a
double of its own that must not be awaited.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

## Bericht

An `D:\Entwicklung\HASI\issue8-pr3-work\sdd\task-9-report.md` **anhängen** (Abschnitt „Fix-Runde 1“): Teständerung,
GREEN-Ausgabe, RED unter der Probe-Mutation (Befehl + Ausgabe), Beleg `restored`, Lint, `task_compare`-Ausgabe, Commit-SHA.
Alle Regeln des Briefs gelten weiter (Temp und uv-Cache auf D:, keine Subagenten, keine volle Suite, kein Push).
