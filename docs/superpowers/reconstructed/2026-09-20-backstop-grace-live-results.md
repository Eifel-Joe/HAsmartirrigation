# Issue 139 — Live-Test-Ergebnisse, 2026-09-20 (HA-Test und HA-Prod)

Rescued from `pr139-work/live/` when that scratch directory was cleared on 2026-09-26.
Irreproducible: both runs needed Fork pre-release `v2026.09.18b2` installed via HACS, a
restart the user triggered, and actual irrigation. The archived spec and plan describe the
live test as PLANNED (`E10`, "Merge wartet auf die Nachmessung") and stop there, so these
are the only record of what it measured.

---

# Issue 139 — Live-Test HA-Test, 2026-09-20

Build: Fork-Pre-Release `v2026.09.18b2` (Commit `6b5c914d`, = upstream `2b2c403b` + `fix/backstop-grace` + Branding),
über HACS installiert, HA-Test vom User neu gestartet (der Auto-Modus-Klassifikator blockiert den Neustart-Aufruf).
Panel zeigt `v2026.09.18b2`. Im Log nur die vorbestehenden `via_device`-Warnungen von upstream, keine Fehler.

Testzone „Grace Test“ (id 8), Service-Modus: `run_service` `script.grace_emu_run`, `duration_field`/Einheit `seconds`,
`stop_service` `script.grace_emu_stop`, `confirm_entity` `binary_sensor.grace_emu_flowing`, `latency_margin` 4,
kein Durchflusssensor, kein `observed_entity`. Master der Instanz: `input_boolean.test_pumpe` (Settle 5 s, Kick aus,
`master_off_after` an). P = 60 s, Wartezeit bei Marge 4 = 9 s, Backstop also bei t0 + 69.

Gefahren per HA-Skript `script.grace_test_runner` (feste Zeitpunkte gegen die Uhr, damit keine MCP-Latenz in die
Messung geht). Alle Zeiten aus dem Recorder bzw. dem `run_log` der Zone (Diagnostics `data.store.zones`, id 8).

## Sichtprüfung Panel (T11)

Die Zeile „Latenz-Marge (s)“ erscheint erst, sobald eine Bestätigungs-Entität gesetzt ist, und kommt mit dem
Default 4. Vor dem Setzen der Entität ist sie nicht da. Das Feld wird gespeichert (Store: `latency_margin: 4`,
später 30, danach wieder 4).

## Ergebnisse

| Szenario | Einstellung | Ventil an → aus | Abschluss laut `run_log` | Eintrag | Erwartung erfüllt |
|---|---|---|---|---|---|
| S1 normales Ende | `off_delay` 0 | 10:34:14,712 → 10:35:14,715 (60,003 s) | 10:35:19,717 = Aus + 5,002 s | `completed`, `planned_s` 60, `actual_s` 60 | ja |
| S2 späte Meldung in der Marge (Tuya-artig) | +2,5 s | 10:37:22,241 → 10:38:24,744 (62,503 s) | 10:38:29,746 = Aus + 5,002 s (vor Backstop t0+69) | `completed`, 60, **63** | ja |
| S8 früher Schluss in der Marge | −2 s | 10:40:06,570 → 10:41:04,572 (58,002 s) | 10:41:09,575 = Aus + 5,003 s | `completed`, 60, **58** | ja |
| S9 früher Schluss jenseits der Marge | −6 s | 10:42:26,117 → 10:43:20,119 (54,002 s) | 10:43:25,121 = Aus + 5,002 s | **`partial`**, 60, **54**, `self_closing_stopped` | ja |
| S3 späte Meldung jenseits der Marge | +6 s | 10:44:46,331 → 10:45:52,333 (66,002 s) | 10:45:55,334 = **t0 + 69** (Backstop) | `completed`, 60, **60** (gemeldetes Fenster bewusst ungenutzt) | ja |
| S5 `unavailable` → `off`, keine Aus-Meldung | −10 s, Schalter bei t0+47/+52 | an 10:47:11,881; `flowing` `unavailable` 10:47:58,927, `off` 10:48:03,927 | 10:48:08,929 = Rückkehr + 5,002 s | **`partial`**, 60, **57** (Basis-Regel, Entscheidung b) | ja |
| S4 Stopp in der Wartezeit | +20 s, `stop_zone` bei t0+63 | an 10:49:43,134; Stopp schließt bei 10:50:46,262 | 10:50:46,183 = Stoppzeitpunkt | `completed`, 60, **60** (Entscheidung d, kein Teil-Lauf) | ja |
| S7 zweiter Dispatch in der Wartezeit | `off_delay` 0, `run_zone` bei t0+63 | **genau einmal** an: 10:52:04,623 → 10:53:04,625 | 10:53:09,627 = Aus + 5,005 s | `completed`, 60, 60; **ein** Eintrag, kein zweites Ventil-An | ja |
| S6 Neuladen in der Wartezeit | +20 s, Marge **30** (Wartezeit 35), Reload bei t0+63 | 11:51:46,111 → 11:53:06,113 (80,002 s) | 11:53:11,114 = Aus + 5,001 s (vor Backstop t0+95) | `completed`, 60, **80** | ja |

Zusatzlauf S6 mit Marge 4 (vor der Korrektur der Marge, deshalb Backstop statt Watcher): Ventil 10:54:47,410 →
10:56:07,413; Reload bei t0+63; Abschluss 10:55:56,414 = t0 + 69 durch den **neu gestellten** Backstop,
`completed`, 60. Master ging beim Reload **nicht** erneut an und erst 5 s nach dem Abschluss aus.

## Was damit live belegt ist

- **Der Watcher rechnet das normale Laufende ab**, nicht der Backstop: S1, S2, S8 (Abschluss jeweils Aus + 5 s).
- **`actual_s` ist das vom Ventil gemeldete Fenster**: 63 bei 62,5 s, 58 bei 58 s, 80 bei 80 s.
- **Toleranz max(1 s, Marge)**: S8 (58) bleibt vollständig, S9 (54) wird Teil-Lauf.
- **Bewusst unverändert**: S3 — meldet das Ventil später als die Marge, bucht der Backstop `planned_s` und ignoriert
  die gespeicherte Aus-Meldung.
- **Entscheidung (b)**: S5 — ohne verwertbare Aus-Meldung gilt die Basis-Regel; nach der ursprünglichen E4-Fassung
  wäre der Lauf fälschlich `completed` mit voller Gutschrift geworden.
- **Entscheidung (d)**: S4 — der Stopp in der Wartezeit endet als vollständiger Lauf.
- **Entscheidung (f) und Neustart-Übernahme**: S6 — der Datensatz überlebt das Neuladen, der Backstop wird neu
  gestellt, der Watcher rechnet die späte Meldung ab, und der Master wird **nicht** erneut angefordert.
- **In-flight (T9)**: S7 — der zweite Dispatch in der Wartezeit wird abgelehnt, ohne zweiten Datensatz und ohne
  zweites Ventil-An.
- **Pumpen-Freigabe** aus der Reichweiten-Liste: Master aus 5 s nach dem Abschluss (S7: 10:53:14,629; S6: 11:53:16,115).

## Grenzen dieses Tests

- Das Emulator-Ventil hat keine echte Hardware-Latenz; sie wurde über `input_number.grace_emu_off_delay` nachgestellt.
- Die Zone hat Durchfluss 0 und keinen Durchflusssensor, deshalb `volume_l: 0` und kein `last_irrigation`-Stempel
  (`_stamp_run_finalized` stempelt nur bei Volumen > 0). Der Durchfluss-Fix (C3/C5) ist hier **nicht** geprüft.
- „Neustart“ ist ein Neuladen des Config-Eintrags; ein echter HA-Neustart dauert länger als die Wartezeit.
- `irrigation_finished` wurde je Szenario nicht ausgezählt; die Hilfs-Automation
  `automation.grace_test_irrigation_finished_139` schreibt die Ereignisse ins Logbuch.

## Zustand HA-Test nach dem Test

Marge zurück auf 4, `off_delay` 0, `unavailable` aus, Ventil aus, Pumpe aus. Testzone „Grace Test“, Skript
`grace_test_runner` und die Hilfs-Automation bleiben stehen; das Pre-Release bleibt installiert.

---

# Issue 139 — Nachmessung HA-Prod, 2026-09-20

Build: Fork-Pre-Release `v2026.09.18b2` (Commit `6b5c914d` = upstream `2b2c403b` + `fix/backstop-grace` + Branding),
über HACS installiert, Neustart vom User ausgelöst. Nach dem Neustart tragen alle drei Zonen `latency_margin: 4`
(Default für Bestandszonen), die Integration lädt fehlerfrei; im Log nur die vorbestehenden `via_device`-Warnungen
von upstream.

Zwei manuelle Läufe über `irrigation_plus.run_zone` mit `duration: 1` (Minute). Kirschbaum bleibt außen vor
(defekter Schlauch, Memory `hasi-kirschbaum-hose-defect`). Zeiten aus dem Recorder (`last_changed` der
Bestätigungs-Entität) und dem Verlaufseintrag der Zone.

## Kirschlorbeer (SONOFF, Sekunden-Ventil, `valve.wasser_vorne`)

| Messpunkt | Zeit |
|---|---|
| Ventil auf | 13:06:13,828 |
| Ventil meldet zu | 13:07:13,829 (60,001 s offen) |
| Abschluss | 13:07:18,838 = **Zu + 5,009 s** |
| Eintrag | `completed`, `actual_s` 60, 3,0 L (Durchfluss-Zähler `per_run`) |

Der alte Backstop hätte bei rund 13:07:14,3 bis 14,8 gefeuert (Fenster ab `RUN_STARTED`, Confirm-Schwanz auf
dieser Anlage 0,46–0,97 s), also **nach** der Schlussmeldung und mitten in der 5-s-Entprellung — der Fall, der
auf dieser Anlage bisher jeden Lauf abgerechnet hat. Der neue Backstop wäre erst bei ~13:07:23 fällig gewesen.

## Beet (Tuya, Minuten-Ventil, `valve.wasser_beet_valve_l1`)

| Messpunkt | Zeit |
|---|---|
| Ventil auf | 13:08:55,109 |
| Ventil meldet zu | 13:09:58,331 (**63,222 s** offen) |
| Abschluss | 13:10:03,335 = **Zu + 5,004 s** |
| Eintrag | `completed`, **`actual_s` 63**, 3,1 L (zeitbasiert auf `planned_s`, kein Durchflusssensor) |

Vor dem Fix hätte der Backstop bei etwa 13:09:55,6 gefeuert, **2,7 s bevor** das Ventil seinen Schluss meldet,
und `planned_s` 60 gebucht. Der Eintrag zeigt jetzt das vom Ventil gemeldete Fenster.

## Was damit belegt ist

- Auf beiden echten Ventilen rechnet der **Watcher** das normale Laufende ab, nicht mehr der Backstop
  (Abschluss jeweils Aus + 5,00 s). Dieser Pfad war auf dieser Anlage vorher unerreichbar.
- `actual_s` ist das vom Ventil gemeldete Fenster: 63 statt 60 beim Minuten-Ventil.
- Die Default-Marge 4 s deckt die gemessene Latenz (3,2 s beim Tuya-Ventil) ab; der Lauf bleibt `completed`.
- Kein zusätzlicher `observed`-Eintrag, obwohl beide Zonen dieselbe Ventil-Entität als `observed_entity` tragen:
  Das In-flight-Fenster unterdrückt die Beobachtung über die Wartezeit hinweg (T3b ist gestrichen).
- Das Zeitvolumen bleibt bewusst auf `planned_s` (Beet 3,1 L = 3,1 L/min × 60 s), nicht auf `actual_s`.

## Grenzen

- Nur zwei Läufe, beide manuell ausgelöst; natürliche Läufe folgen mit dem nächsten Zeitplan.
- Der Raten-Durchflusspfad (Fix C3/C5) ist hier NICHT geprüft: Kirschlorbeer zählt `per_run`, Beet hat keinen
  Sensor.
- Keine Messung zum Stopp in der Wartezeit oder zum Neustart auf Prod; beides ist auf HA-Test belegt.
