# Nach-Review Task 9, Fix-Runde 1

Geprüft: Fix-Commit `e62b046f` (Basis `e5d184e3`), Diff `review-t9-fix1.diff`, Bericht-Abschnitt „Fix-Runde 1“,
Rohausgaben `task-9-fix1-red.txt` / `-green.txt` / `-compare.txt`, Worktree nur lesend. Keine Tests gelaufen.

## Befund (Important: die Entscheidung „ungedrosselt“ hielt kein Test)

**ADDRESSED**

Beleg:

- `tests/test_sensor_liveness_coordinator.py:1236` setzt in `_silent_station` ein eigenes Double
  `coord.async_refresh_zone_estimates_throttled = AsyncMock()`. Die gedrosselte Methode reicht damit am
  `__new__`-Koordinator nicht mehr zum Mock der ungedrosselten durch (`live_estimate.py:1896-1910`: ohne
  `_zone_estimates_refreshed_at` ruft sie `async_refresh_zone_estimates()`; genau das war die Lücke).
- `:1245` (Öffnen) und `:1266` (Schließen) ergänzen `async_refresh_zone_estimates_throttled.assert_not_awaited()`.
- Produktionsstelle unverändert: `sensor_liveness.py:530` holt weiter `async_refresh_zone_estimates`.
  `git diff e5d184e3 HEAD -- custom_components` ist leer, Worktree sauber (`git status --short` leer).
- RED unter der Probe-Mutation ist in der Rohausgabe belegt (`task-9-fix1-red.txt:9-61`): `FFF.F.`, `4 failed, 2 passed`;
  fehlgeschlagen sind `:1244` (Öffnen), `:1253` („ändert nichts“), `:1265` (Schließen, `assert 0 == 2`), `:1283`
  („zwei Gruppen“). Die zwei Grünen sind „behalten“ und „Fehler folgenlos“. GREEN auf dem echten Code: `6 passed`
  (`task-9-fix1-green.txt`). Rücknahme belegt (Produktionsdiff leer, jetzt von mir nachgeprüft).

Beantwortung der drei Fragen:

1. **Double-Geltung.** `_silent_station` ist eine Methode von `TestTheEstimateFollowsTheRecord` und wird von allen sechs
   Tests der Klasse benutzt (`:1240, 1248, 1256, 1269, 1277, 1286`). Außerhalb der Klasse gibt es keinen Aufrufer
   (Grep über `tests/`), andere Klassen bauen über `_coord` ohne das Double. Der Prüfpfad (`sensor_liveness.py`)
   ruft die gedrosselte Methode nirgends (sie wird nur von `continuous_update.py:556` und `irrigation.py:3311`
   gerufen), das Double verdeckt also keine bisher geprüfte Aussage. `test_a_refresh_that_fails_leaves_the_check_intact`
   überschreibt nur das ungedrosselte Double (`:1289`), das gedrosselte bleibt daneben unberührt; unter dem echten Code
   bleibt seine Aussage (Fehler des Refresh bleibt folgenlos) unverändert.
2. **Hält das die Entscheidung?** Ja. Bei einem Rückfall auf die gedrosselte Variante landet der Aufruf am
   gedrosselten Double, das ungedrosselte wird nicht awaited: vier Tests rot (siehe oben, gemessen). Ein Rückfall
   „beide rufen“ schlägt zusätzlich an `:1245`/`:1266` an. Eine Feinheit, ehrlich benannt: Unter der Probe-Mutation
   scheitern die Tests an den **vorhandenen** Prüfungen (`:1244`, `:1265`), nicht an den neuen `assert_not_awaited`-Zeilen;
   tragend ist das Double selbst (`:1236`), die zwei neuen Assertions sind der Gürtel für den „beide“-Fall. Der Bericht
   (Zeilen 159-162) beschreibt das genau so und ist korrekt.
3. **Commit-Message.** `e62b046f`: englisch, WAS und WARUM, wörtlich nach Fix-Brief, letzte Zeile
   `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Keine Fork-/Upstream-Issues (`Eifel-Joe#…`, `JustChr#…`),
   keine Spec-/Plan-Kürzel, kein „PR 2/PR 3“, keine „Task N“-Verweise. Der Diff selbst fügt keinen Kommentar hinzu,
   also auch dort keine Verweise.

Weitere Prüfung: Diff exakt +3 Zeilen, Testdatei weiter reines CRLF (Bytezählung: `CRLF 1291, bareLF 0, bareCR 0`);
`task_compare t9f1`: `507 passed, 1 failed, 270 errors`, identisch zu t9 (Bericht Zeile 76 vs. 192), 2 bekannte Namen
entfallen, `new FAILED: 0`.

## New breakage in fix diff

**none**

## Out-of-scope observations

- Nit: Das Double in `:1236` trägt keinen Kommentar; wer es später als „ungenutzt“ entfernt, nimmt dem Test die
  Haltefunktion. Der Grund steht nur in der Commit-Message. Der Fix-Brief verbot weitere Änderungen an den Tests,
  deshalb kein Mangel dieser Runde; ein Einzeiler wäre bei Gelegenheit nützlich.
- Nit: `test_a_group_that_keeps_does_not` (`:1268-1274`) prüft nur das ungedrosselte Double. Würde ein späterer
  Umbau für eine *behalten*-Gruppe die **gedrosselte** Variante rufen, bliebe der Test grün. Mit dem neuen Double wäre
  ein `assert_not_awaited()` dort eine Zeile. Gehört nicht zur geprüften Entscheidung.
