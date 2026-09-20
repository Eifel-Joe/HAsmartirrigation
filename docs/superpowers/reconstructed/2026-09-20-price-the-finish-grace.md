# Die Nachsicht ins Fenster einpreisen (#151, vierter von vier)

**Stand:** 2026-09-20, Branch `fix/price-the-finish-grace` von `upstream/master` = v2026.09.19 (`2ff4e155`), Commit `8059f30f`.
**Anlass:** Warteschlange aus vier von JustChr freigegebenen Issues, vom Einfachsten zum Schwersten (#143 → #142 → #152 → #151). Dieser war der einzige mit echter Verhaltensänderung an der Auswahl und wurde deshalb zuletzt gebaut.

## Befund
Seit #150 settelt ein bestätigter Service-Lauf auf dem Aus-Bericht des Ventils plus 5 s Entprellung, ersatzweise beim Backstop auf `plan + 5 s + latency_margin` der Zone. Die nächste Zone der Kette startet erst dann. `zone_confirm_seconds` bepreiste so eine Zone aber weiter mit der 30-s-Poll-Obergrenze **allein**; Finish-Anker und Arm-Schranke lesen diesen Preis.

## Entscheidung
Zwei Terme statt eines fetteren: neu `zone_finish_grace_seconds(zone)` (Spiegel von `run_watch.run_finish_grace_seconds`, aber aus dem Zonen-Dict, weil zur Bepreisungszeit noch kein Record existiert) und `zone_non_water_seconds(zone)` = Poll + Nachsicht. Beide Erzeuger — Dial `nominal_demand_seconds` und Arm `async_plan_zone_runs` — werden **gemeinsam** umgestellt, weil `TestTheDialAgreesWithTheArm` die ausformulierte Projektregel dazu ist. Umfang nach User-Entscheidung: Entprellung **und** Marge (+9 s bei Default, bis +35 s bei Marge = MAX).

## Verworfen
- **`zone_confirm_seconds` überladen** (mein erster Vorschlag). Dessen Docstring beschreibt ausdrücklich den Öffnungs-Poll („paid before any water flows"); die Nachsicht liegt hinter dem Wasser. Überladen hätte den vorhandenen Pin `test_a_self_closing_zone_pays_only_with_a_confirm_entity` **falsch** statt unvollständig gemacht und ihn zum Umschreiben gezwungen. Mit zwei Termen bleibt er grün und wahr.
- **Dial billig, Arm teuer** (Vorschlag des Qualifikations-Gegenprüfers). Bricht `TestTheDialAgreesWithTheArm`: „Pricing it on a different model than the one the run is fitted to means the schedule they drew is not the schedule they get."
- **Gar nicht bauen** (Urteil des Überreservierungs-Gegenprüfers, „Vorschlag fällt"). Sein Gegenvorschlag — am Anker zusätzlich `VALVE_CONFIRM_TIMEOUT` einrechnen — ist ein No-Op: genau das tut der Code seit #150 (`self_closing.py` armt auf `planned_seconds + run_finish_grace_seconds(record)`). Er hat in seinem eigenen `residual_risk` eingeräumt, die Anker-Implementierung nicht gelesen zu haben. Seine **Warnung** ist trotzdem in den PR-Body übernommen.

## Nachweis
- 7 neue Tests, die ersten beiden zuerst rot gesehen (Import-Fehler für die neue Funktion; Dial `630 ≠ 639`).
- Volle Suite 3159 → **3166 passed**, 7 failed / 320 errors mit identischen Vorbestandsnamen. black/ruff grün. **Kein vorhandener Test wurde rot** — genau das war der Grund für die gewählte Form.
- Analyse vorab: 4 Leser (Konsumenten, Qualifikation, Zahlen, betroffene Tests) + 2 Gegenprüfer mit festen Linsen + Entscheider, 7 Agenten, 0 Fehler.

## Feldmessung HA-Prod (2026-09-20, in den PR-Body übernommen)
Kette Kirschlorbeer → Kirschbaum → Beet, Zielanker = Sonnenaufgang − 30 min (bestätigt über `next_irrigation` gegen `sun.sun`): Wasser 1078 s, Gesamtdauer 1082,07 s → **4,07 s Nicht-Wasser-Zeit**, bepreist waren **90 s**. Übergaben 3,02 s und 1,04 s. **Die Unter-Bepreisung beißt auf dieser Anlage nicht** — der Fix ist Vorsorge für ein träges Ventil, für das die 30 s überhaupt existieren. Das wird im PR offengelegt, nicht verschwiegen.

## Offen / Folge
- Die ehrlichen Verschlechterungen stehen im PR-Body: Fensterbudget −9 s je Zone; eine verdrängte Zone verliert einen ganzen Zyklus (`scheduler.py`: „they carry their deficit and lead the next run"); bezahlt wird auch für Läufe, deren `confirm_entity` im Dispatch-Moment nicht lesbar war und die nie eine Nachsicht bekommen; unter `rotating` fällt der Aufschlag je Slot an.
- Form-Frage (eine Funktion oder zwei) ist im PR-Body ausdrücklich an JustChr zurückgegeben.
