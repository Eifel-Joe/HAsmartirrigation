# Live-Test Eifel-Joe#89 + #20 (Spec 2026-10-23, §6) — HA-Test, 2026-10-23

Fork-Vorabversion **v2026.10.23b1** (`production` = `d42b5d65` = upstream `c46c41fc` + Branding + die 7 Branch-Commits +
Build), per HACS auf HA-Test installiert, Neustart, Hub-`sw_version` = `v2026.10.23b1`. Aufbau wie am 2026-10-11:
Pirate Weather, 9 automatische Zonen, 2 aktive Zeitpläne. DEBUG nur für `…weathermodules.PirateWeatherClient` und
`…weathermodules.fetch_gate`. Gezählt in der MCP-Sandbox nur aus den Zeilenköpfen (Zeitstempel, Thread, Art), nie aus
den Dokumenten (Skript: `pirate_count_sandbox.py` daneben). Zeiten = HA-Ortszeit.

## (a) Ein Aktualisierungszyklus — bestanden

Regulärer Zyklus 12:17:48,837–12:17:49,077 (0,24 s), Intervall 10 min:

| | 2026-10-23 | 2026-10-11 (vorher) |
|---|---|---|
| echte `get_forecast_data` | **1** | 18 |
| echte `get_data` | 1 | 1 |
| Zwischenspeicher-Treffer | 19 | 20 |
| „Connection pool is full“ | 0 | 8 |

Die 18 Vorhersage-Treffer kamen 1–46 ms nach dem einen echten Abruf aus 12 Threads → sie haben an der Sperre gewartet.
Zusätzlich: der durch das Umstellen des Intervalls ausgelöste Zyklus 12:07:48 (Zwischenspeicher abgelaufen, weil das
Fenster von 3599 auf 599 s sank): 1 + 1 echte Abrufe, 37 Treffer in 0,5 s.

Falle dabei: Ein Teil-Update `{"autoupdateinterval": "10"}` über `/api/irrigation_plus/config` speichert das Intervall,
setzt den Zeitgeber aber nicht neu — das tut `async_update_config` nur, wenn `autoupdateenabled` im Payload steht
(das Panel schickt immer alle Felder). Vorbestand, nicht Teil des Branches.

## (b) Zeitplan speichern — bestanden

Unverändertes Neuspeichern von `schedule_1fac4605` über `irrigation_plus/schedule_save` (wie der Panel-Knopf):
- mit frischem Zwischenspeicher (12:20:53): 18 Aufrufe in 73 ms, **0** echte;
- mit abgelaufenem Zwischenspeicher (Auto-Update kurz aus, letzter Abruf 680 s alt, 12:29:16): 18 Aufrufe in 66 ms aus
  11 Threads, **1** echter `get_forecast_data`, 17 Treffer (2–66 ms nach dem Abruf). Am 2026-10-11: 30 echte.

## (c) Fehlschlag — bestanden, ein Befund

Fehlschlag ohne Schlüssel-Eingriff: manuelle Koordinaten Breite 95°, Länge 0° (`irrigation_plus/coordinates_save`,
lädt den Eintrag neu) → Pirate Weather antwortet **400**. Zeitpunkte der Fehlschläge (ERROR-Zeilen) und der gezielten
Nachfragen über `irrigation_plus/weather_forecast` (läuft über den gemeinsamen Client):

| Zeit | Tor | Ereignis |
|---|---|---|
| 12:30:26,325 / ,578 | Vorhersage / aktuelle Werte | je 1 Fehlschlag (gut 3 s nach dem Neuladen = 3 Versuche, 1 s + 2 s), **37** Wiedergaben der wartenden Aufrufer |
| 12:30:54 | Vorhersage | Nachfrage → Wiedergabe „1 failed … another 32 s“ |
| 12:31:43 → 12:31:46,913 | Vorhersage | Nachfrage nach Pausenende → neuer Lauf (3,9 s) → Fehlschlag 2 |
| 12:33:21 | Vorhersage | Wiedergabe „2 failed … another 25 s“ (= 120 s) |
| 12:34:02 → 12:34:06,232 | Vorhersage | neuer Lauf → Fehlschlag 3 |
| 12:36:46 | Vorhersage | Wiedergabe „3 failed … another 80 s“ (= 240 s) |
| 12:38:23 → 12:38:26,824 | Vorhersage | neuer Lauf → Fehlschlag 4 (Pause 480 s) |
| 12:40:22-Zyklus | Vorhersage / aktuelle Werte | Vorhersage: **37 Wiedergaben, keine Anfrage**; aktuelle Werte: 1 Lauf (Fehlschlag 2) + 1 Wiedergabe |
| 12:50:22-Zyklus | beide | aktuelle Werte Fehlschlag 3 (12:50:25,881, Pause 240 s); Vorhersage Fehlschlag 5 (12:50:29,410, Pause gedeckelt 599 s), 28 Wiedergaben |
| 13:00:22-Zyklus | beide | aktuelle Werte Fehlschlag 4 (Pause 480 s); Vorhersage: Wiedergabe „5 failed … another **2 s**“ |

Ergebnis: Folge 60 → 120 → 240 → 480 s und Deckel 599 s live belegt; gleichzeitige Aufrufer teilen den einen
Fehlschlag; je Lauf genau eine ERROR-Zeile des Clients — 9 in 30 min (5 Vorhersage, davon 4 durch die Nachfragen,
4 aktuelle Werte), statt 5505 + 552 in 46 h am 2026-10-09/11. Die eigene WARNING des Aufrufers („No weather data to
parse“) bleibt nach A1/C4 unverändert. In 30 min höchstens 5 Läufe je Tor (Kriterium: ≤ 6).

**Befund (Vorhersage bestätigt):** Die Pause beginnt am *Ende* des gescheiterten Laufs. Bei Pirate Weather dauert der
durch die Wiederholungen gut 3 s; Pause am Deckel 599 s, Zyklus 600 s → der nächste Zyklus kommt ~2 s vor Pausenende und
bekommt noch die Wiedergabe. Ein dauerhaft scheiterndes Pirate-Tor fragt am Deckel also nur jeden zweiten Zyklus nach.
Nie mehr Anfragen, aber eine Erholung des Dienstes wird bis zu einen Zyklus später bemerkt, als Spec C5 („höchstens das
normale Fenster“) sagt. Möglicher Fix: `_failed_at` beim *Beginn* des Laufs nehmen.

**Nicht live belegt:** die einzelnen Versuchsabstände (1 s, 2 s) — nur aus der Laufdauer erschlossen, weil
`urllib3`-DEBUG den Schlüssel in der URL zeigen würde; `Retry-After` (kein Dienst sendet es nachweislich); die Erholung
*innerhalb* einer Pause (das Zurückstellen lädt den Eintrag neu).

## Zurückgestellt

13:01:45 manuelle Koordinaten aus → Neuladen → 1 + 1 echte Abrufe, 55 Treffer, kein Fehler. Intervall 60 min (alle
Auto-Update-Felder), Logger `warning`, gespeichertes Sandbox-Werkzeug gelöscht. Neustart HA-Test 13:02 (Verteiler
`gardena1` war nach dem zweimaligen Neuladen `unavailable` — bekannter Vorbestand).

## Nachmessung 2026-10-27/28 mit v2026.10.27b1 (Pause ab Beginn des Laufs, Wartenden-Regel)

`production` = `c9d4d2cd` (upstream `c46c41fc` + Branding + 10 Branch-Commits + Build), HACS + Neustart, Hub-`sw_version`
`v2026.10.27b1`. Gleicher Aufbau, Fehlschlag wieder per Breite 95° (Neuladen 23:29:46), Intervall 10 min.

| Zeit | Tor | Ereignis |
|---|---|---|
| 23:29:49,9 / 50,1 | beide | Fehlschlag 1, 38 Wiedergaben; erste Wiedergabe 23:29:50,224 „another **56 s**“ (60 s ab Beginn, nicht ab Ende) |
| 23:31:07 → 23:31:10,686 | Vorhersage | Nachfrage → Fehlschlag 2 |
| 23:33:27 → 23:33:30,374 | Vorhersage | Nachfrage → Fehlschlag 3 |
| 23:38:06 → 23:38:09,914 | Vorhersage | Nachfrage → Fehlschlag 4 (Pause 480 s) |
| 23:39:46-Zyklus | Vorhersage / aktuelle Werte | Vorhersage 24 Wiedergaben „4 failed … another 377 s“; aktuelle Werte Fehlschlag 2 |
| 23:49:46-Zyklus | beide | aktuelle Werte Fehlschlag 3; Vorhersage Fehlschlag 5 (23:49:53,653), Wiedergaben „another 595 s“ (Deckel 599 ab Beginn) |
| **23:59:46-Zyklus** | beide | aktuelle Werte Fehlschlag 4; **Vorhersage Fehlschlag 6 (23:59:53,521) — der Zyklus fragt wieder**; vorher (v2026.10.23b1) an dieser Stelle Wiedergabe „another 2 s“ |

Ergebnis: Am Deckel fragt ein dauerhaft scheiterndes Pirate-Tor jetzt in jedem Zyklus. Vorsprung des Zyklus vor dem
Pausenende knapp 1 s (Fenster = Intervall − 1 s), wie berechnet. Zurückgestellt 00:01:22 (Koordinaten aus → 1 + 1 echte
Abrufe, kein Fehler; Intervall 60 min; Logger `warning`; Sandbox-Werkzeug gelöscht), Neustart HA-Test 00:0x.
