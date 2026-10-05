## English

**What.** The `generate_watering_calendar` service returns nothing: it is registered without `supports_response` (`services.py:475-479`) and its handler returns `None`. The result goes out only as the event `irrigation_plus_watering_calendar_generated` (`zone_id`, `calendar_data`, `generated_at`; `services.py:268-275`), a failure as `irrigation_plus_watering_calendar_error` (`:282-291`). Neither event is in `docs/usage-events.md`, which lists six events "the integration fires"; both names are f-strings rather than `const.EVENT_*` like every other event. `irrigation_plus_distributor_halted` (`const.py:1256`) is missing from that page too.

Two more things around the same service:
- `services.yaml` declares `target: entity: domain: sensor`, but the handler reads only `call.data["zone_id"]` (`services.py:249`). A call with a target therefore always computes all zones, and the event reports `zone_id: None`.
- The copy in `hass.data[DOMAIN]["watering_calendars"]["last_generated"]` ("for retrieval by automation") is read by nothing; automations cannot read `hass.data`. It only rides along in a diagnostics dump (`diagnostics.py:61`).

**Source.** Found while documenting the seasonal outlook for JustChr#191, which names the `_generated` event in `docs/configuration-weather-location.md` and `docs/usage-services.md`, not in `usage-events.md`. Checked on `bbf2e151` (v2026.10.04).

**Fix sketch.** Return the calendar as a service response (`supports_response=OPTIONAL`); honour the target or replace it by a `zone_id` field; list both calendar events and `distributor_halted` in `usage-events.md` with their payloads; drop the unread `hass.data` copy. Upstream after JustChr#191.

**Severity:** `schwere:niedrig`; no watering decision reads the calendar.

**Former designations:** none (side finding of the Eifel-Joe#10 build; build notes on `archive/design-history`, `docs/superpowers/probes/2026-10-05-seasonal-outlook-build/deviations.md`, Task 9).

## Deutsch

**Was.** Der Dienst `generate_watering_calendar` liefert nichts zurück: Er ist ohne `supports_response` registriert (`services.py:475-479`), sein Handler gibt `None` zurück. Das Ergebnis geht nur als Event `irrigation_plus_watering_calendar_generated` hinaus (`zone_id`, `calendar_data`, `generated_at`; `services.py:268-275`), ein Fehlschlag als `irrigation_plus_watering_calendar_error` (`:282-291`). Keines der beiden Events steht in `docs/usage-events.md`, die sechs Events aufzählt, die „die Integration feuert“; beide Namen sind f-Strings statt `const.EVENT_*` wie bei allen anderen Events. Auch `irrigation_plus_distributor_halted` (`const.py:1256`) fehlt auf der Seite.

Zwei weitere Punkte am selben Dienst:
- `services.yaml` erklärt `target: entity: domain: sensor`, der Handler liest aber nur `call.data["zone_id"]` (`services.py:249`). Ein Aufruf mit Ziel rechnet deshalb immer alle Zonen, und das Event meldet `zone_id: None`.
- Die Kopie in `hass.data[DOMAIN]["watering_calendars"]["last_generated"]` („for retrieval by automation“) liest niemand; Automationen können `hass.data` nicht lesen. Sie landet nur in einem Diagnose-Dump (`diagnostics.py:61`).

**Quelle.** Gefunden beim Dokumentieren des saisonalen Ausblicks für JustChr#191, das das `_generated`-Event in `docs/configuration-weather-location.md` und `docs/usage-services.md` nennt, nicht in `usage-events.md`. Geprüft auf `bbf2e151` (v2026.10.04).

**Fix-Skizze.** Den Kalender als Dienst-Antwort liefern (`supports_response=OPTIONAL`); das Ziel beachten oder durch ein Feld `zone_id` ersetzen; beide Kalender-Events und `distributor_halted` mit Payload in `usage-events.md` aufnehmen; die ungelesene `hass.data`-Kopie entfernen. Upstream nach JustChr#191.

**Schwere:** `schwere:niedrig`; keine Bewässerungsentscheidung liest den Kalender.

**Frühere Bezeichnungen:** keine (Nebenbefund des Baus von Eifel-Joe#10; Bau-Notizen auf `archive/design-history`, `docs/superpowers/probes/2026-10-05-seasonal-outlook-build/deviations.md`, Task 9).
