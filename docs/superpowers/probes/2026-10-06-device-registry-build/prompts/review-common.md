# Code-Quality-Review je Task — gemeinsamer Kontext

## Das Vorhaben

Home-Assistant-Integration `custom_components/irrigation_plus/` (Fork-Beitrag an das Upstream-Projekt; der PR geht an
den Upstream-Maintainer). Zwei Aufrufe der Geräte-Registry sind in HA abgekündigt, Frist **HA 2027.8.0**:

1. `via_device` im `device_info` der Zonen- und Verteiler-Geräte (Eltern-Verweis auf den Hub als Kennung
   `(DOMAIN, cid)`). Ersatz seit HA 2026.8: `via_device_id` (die **Registry-ID** des Hub-Geräts).
2. `device_registry.async_get_device(identifiers=…)` beim Löschen einer Zone / eines Verteilers. Ersatz seit
   HA 2026.8: `async_get_device_by_identifier(identifier, config_entry_id)`.

**Randbedingung:** Die erklärte Untergrenze ist HA **2025.5.0** (`hacs.json`, CI-Job `test-ha-floor`); der
CI-Hauptjob läuft mit HA 2026.2.3 (Python 3.13). Dort gibt es keinen der Ersatz-Aufrufe; `async_get_or_create` hat bis
2026.7 eine feste Schlüsselwort-Signatur ohne `**kwargs` — ein unbekanntes `via_device_id` wäre ein `TypeError`, und
die Entity-Plattform fängt nur `DeviceInfoError`. Ab 2026.8 muss `via_device_id` eine echte Geräte-ID sein, sonst
verwirft HA das Entity (`DeviceInfoError`).

**Entscheidung (vom User freigegeben):** Weichen statt Versionsvergleich — die Helfer fragen die **Klasse** der
Registry (`type(registry)`), was sie anbietet (ein `Mock()` beantwortet jede Attributfrage an der Instanz mit Ja, und
bestehende Tests bauen die Registry als `Mock()`). `entity.hub_link_for(registry, hub_device_id, cid)` entscheidet die
Form des Eltern-Verweises, `async_setup_entry` legt sie einmal in `hass.data[DOMAIN]["hub_link"]` ab,
`entity.hub_link(hass)` liest sie (ohne Eintrag: alte Form), `entity.find_device(registry, identifier,
config_entry_id)` sucht ein Gerät auf dem angebotenen Weg. Rückbau, sobald die Untergrenze 2026.8 oder höher ist.
**Ausdrücklich nicht** Teil der Arbeit: Untergrenze anheben, Frontend, Übersetzungen, `dist`, Versions-Bump,
`sensor_liveness.py`, `parent_device_id`.

Der Plan diktiert jeden Block wörtlich und ist einmal komplett probegelaufen (RED/GREEN je Task, volle Suite ohne
Regression, 16/16 Mutationen getötet). Dein Review soll trotzdem echte Lücken finden: Fehlerpfade, ungepinnte
Entscheidungen, falsche Annahmen über HAs API, irreführende Kommentare, Tests, die nicht prüfen, was sie behaupten.

## Belege für HAs API

Lokale Kopien der HA-Quellen (gelesen über die GitHub-API, je Tag):
`D:\Entwicklung\HASI\issue11-work\ha-src\ha-<tag>-device_registry.py` für 2025.5.0, 2025.12.0, 2026.2.3, 2026.6.0,
2026.7.0, 2026.8.0, 2026.9.0, 2026.9.4, und `ha-<tag>-entity_platform.py` für 2025.5.0 und 2026.9.4. Die lokale
Test-Umgebung hat HA 2024.12.5. Aussagen über HAs Verhalten bitte mit Datei:Zeile aus diesen Kopien belegen; was sich
dort nicht belegen lässt, als Vermutung kennzeichnen.

## Regeln für dich

- **Nur lesen.** Keine Datei ändern, nichts committen, kein `git checkout`/`stash`/`reset`.
- **Kein pytest, kein Python-Lauf im Worktree** — der Controller fährt dort parallel die volle Suite; zwei
  pytest-Läufe gleichzeitig erzeugen unter Windows Fehlalarme. Lesen, `git diff`, `git show`, `git grep` sind erlaubt.
- Worktree: `D:\Entwicklung\HASI\issue11-work\wt` (Git-Befehle mit `git -C D:/Entwicklung/HASI/issue11-work/wt …`).
- Kein Verweis auf Issue-Nummern o. Ä. in Code/Tests/Messages ist Absicht (der Text geht an Upstream).
- Schweregrade ehrlich: Critical nur bei echtem Defekt; jede Aussage mit Datei:Zeile; bei jedem Befund ein konkretes
  Szenario (Eingabe/Zustand → falsches Ergebnis). Kein „sieht gut aus“ ohne Prüfung.
- Ausgabeformat: Strengths / Issues (Critical, Important, Minor; je Datei:Zeile, was, warum, wie beheben) /
  Recommendations / Assessment („Ready to merge? Yes/No/With fixes“ + 1–2 Sätze). Antwort auf Deutsch.
