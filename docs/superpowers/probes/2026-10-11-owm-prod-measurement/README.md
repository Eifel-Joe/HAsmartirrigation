# OWM-Client auf HA-Prod gemessen, 2026-10-11

Beleg für die Schwere-Einstufung von Eifel-Joe#89 (Weather-Client: gleichzeitige Aufrufer verfehlen den Cache) und für
den Upstream-Bericht dazu. Protokoll: `owm-prod-measurement-2026-10-11.md`.

`owm_count_sandbox.py` ist die Datei aus dem Arbeitsordner `session-1011b-work`. Das Protokoll sagt, die Auswertung
sei mit `sorted()` auf Strings gelaufen, weil die Sandbox Listen von Listen nicht sortieren kann; die Datei zeigt
noch `events.sort()` auf Listen. Welche Fassung lief, ist unbestätigt. Die Zahlen stehen im Protokoll.
