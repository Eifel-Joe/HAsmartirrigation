# „Jetzt bewässern" nimmt Gutschrift weg — der Deckel darf nie unter den Bucket (Befund F6 aus #98)

**Stand:** 2026-09-20, Branch `fix/irrigate-now-credit` (von upstream/master `6d9c69e6` = v2026.09.17), Commit `458ec5d6`. **Noch kein PR** — Freigabe offen, #147-Stabilisierung läuft.
**Anlass:** Verifikation der sechs `sequential`-Befunde aus der #98-Analyse (2026-09-20, 19 Agenten gegen v2026.09.17). F6 war einer von fünf bestätigten; vom User als erster zu bauender Punkt gewählt, weil er klein ist und den geplanten #98-Live-Test entsperrt.

## Befund
Jeder zeitbasierte Lauf bucht `new_bucket = min(ceiling, pre_bucket + depth)` (`self_closing.py:567-568`, Schwester-Pfade in `batch.py:344` und `irrigation.py:1392`). `ceiling` kommt aus `_run_ceiling` und ist normalerweise der Ziel-Boden (0.0 bzw. der Vorhersage-Rest). Liegt der Bucket **über** diesem Ziel, schreibt derselbe `min` ihn **herunter** — der Lauf entfernt Gutschrift, die er nie verbraucht hat. Genau die Zeile, mit der Issue #88 aufmachte.

`_mark_manual_run` schließt das für `async_run_zone`, und sein Docstring beschreibt den Schaden wörtlich. `async_irrigate_now` (`irrigation.py:3279`) setzt den Marker nicht (grep: nur 3322/3359).

**Erreichbar, nicht hypothetisch:** „Eimer von Hand setzen" hebt den Bucket, und `store.py async_update_zone` nullt die gespeicherte Dauer nur bei exakt 0. Jeder andere von Hand gesetzte Wert lässt `duration > 0` stehen — und genau darauf filtert der Knopf.

**Live gemessen (RED):** Zone bei +3,0 mm, Knopf gedrückt → Bucket **0,0** geschrieben. 3 mm Gutschrift weg.

## Entscheidung
Fix an der geteilten Entscheidungsstelle `_run_ceiling`: der Deckel ist `max(Ziel, aktueller Bucket)`. Ein absenter Bucket bleibt beim blanken Ziel.

## Verworfen
- **`_mark_manual_run` auf `async_irrigate_now` spiegeln** (das war der ursprüngliche Vorschlag des Befunds). Dieser Zweig liefert `maximum_bucket`. Die Dauer von `async_run_zone` ist eine explizite Anweisung, die von `irrigate_now` dagegen kommt aus der Tagesberechnung **inklusive Vorlaufzeit** — also genau die Über-Gutschrift, die der Ziel-Boden absorbieren soll. **Empirisch belegt:** mit dem Marker leckt der Normalfall (Bucket −8) exakt **+3,000 mm** = 90 s Vorlauf bei 10 L/min auf 5 m² — die #88-Zeile, neu aufgerissen. Der Regressions-Pin fängt das.
- **Bucket `or 0` als Default.** Erster Wurf, brach `test_run_ceiling_uses_target`: bei einem Zonen-Dict ohne Bucket hebt eine erfundene 0 den Deckel über ein **negatives** Ziel und zerlegt die Vorhersage-Gewichtung, die eine Zone bewusst unter 0 lässt. Korrigiert auf `is None`, Test blieb unverändert.
- **Die gelieferte Wassermenge dem Überschuss-Bucket gutschreiben** (also +3 → +23). Physikalisch vertretbar, aber eine Verhaltensänderung statt einer Fehlerbehebung — unter #147 nicht vertretbar. Offen gelassen, siehe unten.

## Nachweis
- 2 neue Tests in `tests/test_credit_ceiling.py`: `test_irrigate_now_never_takes_credit_away` (RED zuerst gesehen: `assert 0.0 > 3.0`) und `test_irrigate_now_still_absorbs_the_lead_time_over_credit` als Regressions-Pin.
- **Pin auf Zähne geprüft:** verworfene Variante testweise eingebaut → Pin rot mit `3.0 == 0.0`. Variante wieder entfernt.
- Volle Suite gegen upstream/master: **3006 → 3008 passed**, 7 failed / 320 errors mit identischen FAILED-Namen (Vorbestand). `uvx black --check` 68 Dateien unverändert, `uvx ruff check` grün.

## Offen / Folge
- **Semantik-Entscheidung des Users:** Soll ein unnötiger Handlauf die gelieferte Menge obendrauf gutschreiben (+3 → +23) statt sie nur nicht wegzunehmen (+3 bleibt +3)? Dieser Fix beantwortet nur den Defekt, nicht die Frage.
- Restliche verifizierte Befunde: F1 + F3 + F4 als Bündel A in `run_chain.py` (gemeinsame Wurzel: die Kette hält Wartende als bloße ID-Liste), F5 nur notiert, F2 widerlegt. Stand in `D:\Entwicklung\HASI\ToDo.md`.
- Der geplante #98-Live-Test per „Alle Zonen jetzt bewässern" misst vor F3 und F6 durch beide Fehler hindurch.
