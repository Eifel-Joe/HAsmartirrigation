# Wetter-Clients: ein gemeinsamer Abruf, eine Pause nach dem Fehlschlag — Umsetzungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Jeder der vier Wetter-Clients stellt je Dokument höchstens eine Anfrage zur selben Zeit und fragt nach einem
Fehlschlag eine Weile gar nicht, ohne dass sich für einen Aufrufer ändert, was er bei Erfolg oder Fehlschlag bekommt.

**Architecture:** Ein neues Modul `weathermodules/fetch_gate.py` trägt die gemeinsame Frische-Prüfung und die Klasse
`FetchGate`. Jede der sieben Abrufstellen bekommt ein Tor: Die bisherige Methode wird zu einem privaten Body, die
öffentliche (bzw. `_fetch*`) ruft `gate.run(body)`. Das Tor hält eine Thread-Sperre, erkennt Erfolg am neuen
Zeitstempel und gibt in der Pause das Ergebnis des Fehlschlags wieder.

**Tech Stack:** Python 3.12 (lokal) / HA-CI, `requests`, `threading`, `time.monotonic`, pytest + freezegun 1.5.1,
pytest-homeassistant-custom-component.

**Spec:** `docs/superpowers/specs/2026-10-23-weather-client-fetch-gate-design.md` (freigegeben 2026-10-23). Abschnitts-
und Entscheidungsnummern (A1, C1–C13, §5 Tests, §6 Ende-zu-Ende) beziehen sich darauf.

**Status: vom User freigegeben am 2026-10-23, Umsetzung subagent-gesteuert** (`superpowers:subagent-driven-development`)
in einer frischen Sitzung. Je Task eine Auftragsdatei, Spec-Check, Review — keines auslassen (Memory
`workflow-agent-hygiene`).

**Umsetzungsstand 2026-10-23 (in derselben Sitzung, auf Wunsch des Users):** Tasks 0–7 erledigt, Kopf `2ba2f05a`
(7 Commits auf `c46c41fc`, ungepusht). Volle Suite 7/4101/9/496, FAILED-/ERROR-Namen = Basis, +88 = die neuen Tests;
Mutationen 12/12; Gesamt-Review „With fixes“ → eine Korrekturrunde, Nachprüfung ohne offenen Befund. Ledger mit allen
Festlegungen, Aufträgen, Berichten: `D:\Entwicklung\HASI\issue89-work\sdd\progress.md`. Die Checkboxen unten sind nicht
einzeln abgehakt; maßgeblich ist das Ledger. Offen: Task 8 (Live-Test) und Task 9 (Lieferung), je Außen-Schritt mit
Freigabe.

**Abschluss 2026-10-28:** Task 8 auf HA-Test mit v2026.10.23b1 bestanden, ein Befund (Pause ab Lauf-Ende → am Deckel
nur jeder zweite Zyklus). Behoben in drei weiteren Commits (Pause ab Beginn, `Retry-After` ab der Antwort, Wartenden-
Regel), Kopf `9455f2f5`, 10 Commits; live nachgemessen mit v2026.10.27b1 (am Deckel fragt jeder Zyklus). Volle Suite
auf `9455f2f5` 7/4104/9/496, Namen = Basis, 91 neue Tests, 16 Mutationen gefangen. Task 9: PR
[JustChr#199](https://github.com/JustChr/HAsmartirrigation/pull/199) am 2026-10-28 geöffnet. Belege im Archiv unter
`docs/superpowers/probes/2026-10-23-weather-fetch-gate-{build,live}/` und `…/2026-10-28-weather-fetch-gate-pr/`.

## Global Constraints

- **Basis:** `upstream/master` = `c46c41fc0ff688febbd74050c0602f9a2d35bc03` (v2026.10.07). Branch
  `fix/weather-client-fetch-gate`, Worktree `D:\Entwicklung\HASI\issue89-work\wt`. Steht `upstream/master` bei Task 0
  woanders: STOP, Basis neu messen und die Zeilenangaben der Spec nachprüfen.
- **Nur Code und Tests:** geändert werden `weathermodules/{fetch_gate,OWMClient,PirateWeatherClient,OpenMeteoClient,
  MetOfficeClient}.py` und zwei neue Testdateien. Kein Frontend, kein `dist/`, keine Übersetzungen, keine Doku (geprüft:
  `docs/*.md` beschreibt weder Abrufe noch Wiederholungen), keine Versionsänderung.
- **Erfolgsweg byte-gleich** (Spec A1, Vorgabe 5): Rückgabewerte, Zeitstempel, Log-Zeilen bei Erfolg unverändert. Die
  vorhandenen Tests bleiben **unverändert** grün.
- **Werte:** `MIN_CACHE_SECONDS = 60`; `FIRST_PAUSE_SECONDS = 60`, Pause nach dem n-ten Fehlschlag in Folge
  `60 × 2^(n−1)`, gedeckelt auf `cache_lifetime(owner.cache_seconds)` = `max(cache_seconds, 60)`;
  `MAX_RETRY_AFTER_SECONDS = 86400`; Pirate `RETRY_TIMES = 3` bleibt, Pausen `RETRY_PAUSES_SECONDS = (1, 2)`.
- **Uhren:** Frische weiter mit `datetime.datetime.now()`. Pause mit `time.monotonic()`, **zur Laufzeit aufgerufen**
  (nie als Default-Argument oder Modul-Alias gebunden): freezegun 1.5.1 bewegt `time.monotonic` mit `tick()` (Probe
  2026-10-23: `monotonic advanced 61.0`), aber nur, wenn der Aufruf über `time.monotonic` geht.
- **Bleibt, wie es ist:** `_SESSION` je Client-Modul (vier Testdateien patchen `<Modul>._SESSION.get`); Attribute
  `_cached_*`, `_cached_*_at`, `_cached_doc`, `cache_seconds`, `override_cache` mit Namen und Typ; `validate_key`.
- **Testbefehl** (aus dem Worktree; `PY=/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe`):
  `TZ=UTC $PY -m pytest <pfade> -p _local_socket_unblock -q --no-header`. Neue Tests:
  `tests/test_weather_fetch_gate.py` (Einheit) und `tests/test_weather_clients_fetch_gate.py` (sieben Tore).
- **Threads im Test** werden mit `join(timeout=5)` beendet und auf `not t.is_alive()` geprüft: Die HA-Testumgebung
  prüft am Testende auf übrig gebliebene Threads.
- **Keine Testklassen importieren:** Hilfen aus `tests/test_weather_modules.py` nur über das Modulobjekt
  (`from . import test_weather_modules as twm`), sonst sammelt pytest dessen `Test*`-Klassen ein zweites Mal.
- **Kommentare** nach Skill `code-doku` an Sperre (C2), Fehlschlag-Regel (C3), Pausenlänge (C5), Uhr (C7), Pirate-Schleife
  (C8): Wurzel, Fix-Logik, NOT-TO-DO, Test-Verweis.
- **Texte nach außen:** Code, Commits und PR englisch, ohne Verweis auf unsere Issues (Memory
  `no-own-issue-refs-upstream`; vor jedem Push `git log upstream/master..HEAD | grep -n "Eifel-Joe\|#[0-9]"` leer).
  Commit-Trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; Commit per `git commit -F - <<'EOF'`.
- **Commits:** einer je grünem Task. Spec §7 nennt vier Commits; ihr dritter („Pause nach dem Fehlschlag mit
  `Retry-After`“) ist hier auf die Tasks 3–5 verteilt, die Reihenfolge bleibt.
- **Lint vor jedem Push:** `uvx black custom_components/irrigation_plus/` und
  `uvx ruff check custom_components/irrigation_plus/`.

## Review Focus

1. **Häufung im Ausfall:** Mehrere Aufrufer gleichzeitig, und der erste Abruf scheitert → genau ein Fehlschlag-Lauf
   (Pirate: drei Versuche), alle Wartenden bekommen dessen Ergebnis. → Task 3,
   `test_concurrent_callers_during_an_outage_share_one_failed_run`.
2. **Intervall geändert, während eine Pause läuft:** Die Pause folgt sofort dem neuen Deckel und hält nicht den alten
   (Tagesintervall → 10 min). → Task 3, `test_a_shorter_update_interval_shortens_a_running_pause`.
3. **Ausnahme, die sich nicht kopieren lässt:** Die Wiedergabe wirft trotzdem denselben Typ. → Task 3,
   `test_replay_of_an_uncopyable_exception_keeps_its_type`.
4. **Wanduhr springt** (Winterzeit, NTP): Die Pause misst nur die monotone Uhr. → Task 3,
   `test_the_pause_runs_on_the_monotonic_clock`.
5. **Schlüssel neu eingeben während einer Pause:** `validate_key` fragt trotzdem wirklich (C11). → Task 3,
   `test_validate_key_ignores_a_running_pause`.

---

## Dateien

| Datei | Verantwortung |
|---|---|
| `custom_components/irrigation_plus/weathermodules/fetch_gate.py` (neu) | Konstanten, `cache_lifetime`, `is_fresh`, `retry_after_seconds`, `is_replay`, `failure_log_level`, `FetchGate` |
| `…/weathermodules/OWMClient.py` | Tore `_data_gate`, `_forecast_gate`; Bodies `_fetch_data`, `_fetch_forecast` |
| `…/weathermodules/PirateWeatherClient.py` | Tore wie OWM; `_get_with_retries`; Pausen und Abbruch |
| `…/weathermodules/OpenMeteoClient.py` | Tor `_doc_gate`; Body `_fetch_doc`; drei Log-Stellen |
| `…/weathermodules/MetOfficeClient.py` | Tore `_hourly_gate`, `_three_hourly_gate`; Bodies `_fetch_hourly_doc`, `_fetch_three_hourly_doc`; zwei Log-Stellen |
| `tests/test_weather_fetch_gate.py` (neu) | `FetchGate` und Helfer mit einem Schein-Besitzer, ohne HTTP |
| `tests/test_weather_clients_fetch_gate.py` (neu) | die sieben Tore über die echten Clients, `_SESSION.get` gepatcht |

---

### Task 0: Arbeitsplatz und Basis-Messung

**Files:** keine im Repo; Ablage `D:\Entwicklung\HASI\issue89-work\baseline\`.

- [ ] **Step 1: Upstream-Runde** (Memory `upstream-sweep-first`): Issues, Kommentare, Releases seit dem letzten Blick;
  `JustChr#196` ganz lesen. Neue Vorgabe von JustChr → STOP, Spec anpassen.
- [ ] **Step 2: Worktree anlegen**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation && git fetch upstream
git rev-parse upstream/master          # erwartet c46c41fc0ff688febbd74050c0602f9a2d35bc03
git worktree add -b fix/weather-client-fetch-gate /d/Entwicklung/HASI/issue89-work/wt upstream/master
git -C /d/Entwicklung/HASI/issue89-work/wt branch --unset-upstream
cp _local_socket_unblock.py /d/Entwicklung/HASI/issue89-work/wt/
cp _local_socket_unblock.py /d/Entwicklung/HASI/issue89-work/read-wt/
```

- [ ] **Step 3: Basis-Suite auf `c46c41fc` messen** (in `read-wt`, losgelöst auf demselben Commit; im Hintergrund,
  dauert mehrere Minuten)

```bash
mkdir -p /d/Entwicklung/HASI/issue89-work/baseline
cd /d/Entwicklung/HASI/issue89-work/read-wt
TZ=UTC $PY -m pytest tests -p _local_socket_unblock -q --no-header -rfE > ../baseline/suite-c46c41fc.txt 2>&1
grep -E "^(FAILED|ERROR) " ../baseline/suite-c46c41fc.txt | sed 's/ - .*//' | sort -u > ../baseline/names-c46c41fc.txt
tail -1 ../baseline/suite-c46c41fc.txt
```

Erwartet: Zusammenfassung „N passed, F failed, S skipped, E errors“; Zahlen und Namensdatei hier eintragen. ERRORs
„at teardown … Lingering timer“ sind Vorbestand (Memory `hasi-local-test-env-rebuild`).

---

### Task 1: Gemeinsame Frische-Prüfung (`Eifel-Joe#20`, keine Verhaltensänderung)

**Files:**
- Create: `custom_components/irrigation_plus/weathermodules/fetch_gate.py`
- Modify: `OWMClient.py:32-37` (Konstante), `:85-90` (`_is_fresh` weg), `:106`, `:247`;
  `PirateWeatherClient.py:39`, `:138-143`, `:235`, `:341`; `OpenMeteoClient.py:33-39`, `:96-102`;
  `MetOfficeClient.py:62`, `:129-134`, `:231`, `:239`, `:321-323`
- Test: `tests/test_weather_fetch_gate.py`, `tests/test_weather_clients_fetch_gate.py`

**Interfaces:**
- Produces: `MIN_CACHE_SECONDS: int = 60`; `cache_lifetime(cache_seconds: float) -> float`;
  `is_fresh(fetched_at: datetime.datetime | None, cache_seconds: float, override_cache: bool) -> bool` (Semantik wie das
  heutige `_is_fresh`: `None` oder `override_cache` → False, sonst `now < fetched_at + cache_lifetime`).
- Produces (Testdatei): in `tests/test_weather_clients_fetch_gate.py` die Tabelle `CASES` (siehe Step 1), die Tasks 2–6
  nutzen.

- [ ] **Step 1: Testtabelle und Tests schreiben**

`tests/test_weather_clients_fetch_gate.py` bekommt `CASES: list[GateCase]` (frozen dataclass mit `id`, `patch`,
`make`, `call`, `ok_body`, `stamp`, `failed_attempts`) und die Helfer `_ok(body)` und
`_failing(status, headers=None)`: MagicMock mit `status_code`, `text`, `headers` (echtes `dict`) und
`raise_for_status.side_effect = requests.HTTPError(str(status), response=<derselbe Mock>)`. `M` = 
`"custom_components.irrigation_plus.weathermodules."`, `twm` = `tests.test_weather_modules` als Modul.

| `id` | `patch` | `make()` | `call(c)` | `ok_body` | `stamp` | `failed_attempts` (Status 500) |
|---|---|---|---|---|---|---|
| `owm_data` | `M+"OWMClient._SESSION.get"` | `OWMClient(api_key="k", latitude=1.0, longitude=2.0, elevation=0)` | `c.get_data()` | `twm.TestOWMClientCaching._CURRENT_BODY` | `_cached_data_at` | 1 |
| `owm_forecast` | dito | dito | `c.get_forecast_data()` | `twm.TestOWMClientGetForecastData()._forecast_body()` | `_cached_forecast_at` | 1 |
| `pirate_data` | `M+"PirateWeatherClient._SESSION.get"` | `PirateWeatherClient("key", "1", 52.0, 5.0, 0)` | `c.get_data()` | `json.loads(tests/fixtures/pirate_weather_berlin.json)` | `_cached_data_at` | 3 |
| `pirate_forecast` | dito | dito | `c.get_forecast_data()` | dito | `_cached_forecast_at` | 3 |
| `openmeteo_doc` | `M+"OpenMeteoClient._SESSION.get"` | `OpenMeteoClient(latitude=1.0, longitude=2.0)` | `c.get_forecast_data()` | `{"hourly": {"time": []}, "daily": {"time": []}}` | `_cached_doc_at` | 1 |
| `met_hourly` | `M+"MetOfficeClient._SESSION.get"` | `MetOfficeClient(api_key="k", latitude=1.0, longitude=2.0)` | `c.get_data()` | `twm._met_doc([])` | `_cached_hourly_at` | 1 |
| `met_three_hourly` | dito | dito | `c.get_forecast_data()` | `twm._met_doc([])` | `_cached_three_hourly_at` | 1 |

Probe vom 2026-10-23 auf `c46c41fc` (`issue89-work\probe\probe_cases.py`): alle sieben `ok_body` setzen den Zeitstempel;
Status 500 → OWM wirft `OSError`, Pirate gibt `None` nach 3 Versuchen, Open-Meteo/Met Office geben am Zugriff `None`
(Ausnahme im `_fetch*`); `requests.ConnectionError` → OWM `get_data` und Pirate `get_data` werfen, die übrigen geben `None`.

Tests:

```python
# tests/test_weather_fetch_gate.py
def test_cache_lifetime_has_a_floor_of_sixty_seconds():
    assert cache_lifetime(0) == 60 and cache_lifetime(59) == 60 and cache_lifetime(599) == 599

@freeze_time("2026-10-23 12:00:00")
def test_is_fresh_matches_the_clients_old_rule():
    now = datetime.datetime.now()
    assert is_fresh(None, 599, False) is False
    assert is_fresh(now, 599, True) is False                      # override_cache
    assert is_fresh(now - timedelta(seconds=598), 599, False) is True
    assert is_fresh(now - timedelta(seconds=599), 599, False) is False
    assert is_fresh(now - timedelta(seconds=59), 0, False) is True  # floor

# tests/test_weather_clients_fetch_gate.py
@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_every_client_asks_the_shared_freshness_check(case):
    client = case.make()
    get = MagicMock(return_value=_ok(case.ok_body))
    with patch(case.patch, get), patch(M + "fetch_gate.is_fresh", return_value=False):
        case.call(client); case.call(client)
    assert get.call_count == 2            # without the shared check the second call is a cache hit
```

- [ ] **Step 2: Rot sehen** — `TZ=UTC $PY -m pytest tests/test_weather_fetch_gate.py tests/test_weather_clients_fetch_gate.py -p _local_socket_unblock -q --no-header`
  Erwartet: `test_weather_fetch_gate.py` bricht beim Sammeln mit `ModuleNotFoundError: …weathermodules.fetch_gate`
  ab; in `test_weather_clients_fetch_gate.py` scheitern alle sieben Fälle am Patch-Ziel `…fetch_gate.is_fresh`.
- [ ] **Step 3: `fetch_gate.py` anlegen und die vier Clients umstellen.** Die Clients rufen
  `fetch_gate.is_fresh(...)` über das **Modul** (`from . import fetch_gate`), damit der Patch im Test greift; die drei
  `_is_fresh`-Methoden und die vier `_MIN_CACHE_SECONDS` entfallen; Open-Meteo `_fetch` prüft per `is_fresh`;
  `_forecast_document` nimmt `cache_lifetime(self.cache_seconds)`. Den Kommentar `OWMClient.py:32-36` an die Konstante
  in `fetch_gate.py` mitnehmen.
- [ ] **Step 4: Grün sehen** — dieselben zwei Dateien plus `tests/test_weather_modules.py tests/test_pirateweather_daily.py
  tests/test_met_office_forecast_document.py tests/test_precipitation_guard_real_clients.py`. Erwartet: alles grün.
- [ ] **Step 5: Commit** — `refactor(weather): one freshness check shared by the four weather clients` (Body: die
  Prüfung war dreimal byte-gleich und einmal inline; die Lebensdauer wurde zweimal gerechnet; keine Verhaltensänderung).

---

### Task 2: Ein Abruf je Tor (C1, C2)

**Files:**
- Modify: `fetch_gate.py`; `OWMClient.py:104`, `:240`, `__init__`; `PirateWeatherClient.py:233`, `:339`, `__init__`;
  `OpenMeteoClient.py:88`, `__init__`; `MetOfficeClient.py:230`, `:238`, `__init__`
- Test: beide Testdateien

**Interfaces:**
- Consumes: `is_fresh`, `cache_lifetime` (Task 1).
- Produces: `class FetchGate: __init__(self, owner: Any, stamp_attr: str) -> None`, `run(self, fetch: Callable[[], T]) -> T`.
  Tore als Attribute am Ende jedes `__init__`: OWM/Pirate `_data_gate = FetchGate(self, "_cached_data_at")`,
  `_forecast_gate = FetchGate(self, "_cached_forecast_at")`; Open-Meteo `_doc_gate = FetchGate(self, "_cached_doc_at")`;
  Met Office `_hourly_gate = FetchGate(self, "_cached_hourly_at")`, `_three_hourly_gate = FetchGate(self, "_cached_three_hourly_at")`.
  Bodies (heutiger Methodeninhalt, unverändert, nur umbenannt): OWM/Pirate `_fetch_data`, `_fetch_forecast`;
  Open-Meteo `_fetch_doc`; Met Office `_fetch_hourly_doc`, `_fetch_three_hourly_doc`. Die alten Namen bleiben als
  Einzeiler mit ihrem Docstring: `return self._data_gate.run(self._fetch_data)` usw.

- [ ] **Step 1: Tests schreiben**

```python
# tests/test_weather_clients_fetch_gate.py
@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_concurrent_callers_make_one_request(case):
    # get blocks on `release` (Event); 5 threads call case.call(client); main waits until
    # get.call_count >= 1, sleeps 0.2 s, sets `release`, joins all (timeout 5, none alive)
    assert get.call_count == 1
    assert getattr(client, case.stamp) is not None
    assert len({repr(r) for r in results}) == 1           # everyone got the same answer

# tests/test_weather_fetch_gate.py — fake owner: cache_seconds, override_cache, stamp, and
# fetch_ok/fetch_none/fetch_raise that serve their cache when is_fresh(stamp, …), else count a call
def test_run_serialises_two_threads_onto_one_fetch(): ...   # owner.calls == 1
```

- [ ] **Step 2: Rot sehen** — Erwartet: `test_concurrent_callers_make_one_request` FAILED in allen sieben Fällen mit
  `assert 5 == 1` (Pirate/OWM/Open-Meteo/Met Office gleich), der Einheitstest mit `AttributeError`/`ImportError`.
- [ ] **Step 3: `FetchGate` mit `threading.Lock` und `run` = Sperre um `fetch()`; die sieben Stellen umstellen.** Die
  Frische-Prüfung im Body läuft damit innerhalb der Sperre: Wer wartet, findet danach den frischen Eintrag (C2).
  Code-doku-Kommentar an der Sperre (Wurzel: 19 Abrufe in 0,6 s; Fix-Logik; NOT-TO-DO: keine `asyncio`-Sperre, keine
  Sperre nur um die Anfrage).
- [ ] **Step 4: Grün sehen** — beide neuen Dateien plus die vier Client-Testdateien aus Task 1 Step 4. Erwartet: grün.
- [ ] **Step 5: Commit** — `fix(weather): concurrent callers wait for one fetch instead of each fetching`.

---

### Task 3: Pause nach dem Fehlschlag (C3, C4 Rückgabe, C5, C7, C10, C11)

**Files:** Modify `fetch_gate.py`; Test: beide Testdateien.

**Interfaces:**
- Produces: `FIRST_PAUSE_SECONDS = 60`; `is_replay(exc: BaseException) -> bool` (liest das Merkmal
  `_fetch_gate_replay`); `FetchGate` hält `_failures: int`, `_failed_at: float | None` (monoton), `_outcome`
  (`(raised: bool, value)`), `_retry_after: float = 0.0` (bleibt bis Task 5 null).

- [ ] **Step 1: Tests schreiben**

Einheit (`tests/test_weather_fetch_gate.py`, Schein-Besitzer, `freeze_time` + `tick`):

- `test_a_failure_is_replayed_without_a_fetch_during_the_pause` — `fetch_none`: 1. Aufruf `calls == 1`, Rückgabe
  `None`; nach `tick(59)` Rückgabe `None`, `calls == 1`; nach `tick(2)` `calls == 2`.
- `test_a_raised_failure_is_replayed_with_its_type_and_message` — `fetch_raise` (`OSError("down")`): in der Pause
  `pytest.raises(OSError, match="down")`, `is_replay(exc)` True, `exc is not` die erste Instanz, `calls == 1`.
- `test_consecutive_failures_double_the_pause_up_to_the_cache_lifetime` — `cache_seconds=599`: Abstände der echten
  Aufrufe 60, 120, 240, 480, 599, 599.
- `test_without_auto_update_the_pause_stays_at_sixty_seconds` — `cache_seconds=0`: 60, 60, 60.
- `test_a_success_resets_the_backoff` — zwei Fehlschläge, Erfolg, Zeitstempel altern lassen, Fehlschlag → nächste
  Pause wieder 60 s.
- `test_override_cache_bypasses_the_pause` — `override_cache=True`: jeder Aufruf ruft ab (C10).
- `test_waiters_served_from_cache_do_not_count_as_failures` — zwei Threads, der erste holt erfolgreich; danach
  `_failed_at is None` und `_failures == 0`.
- Review Focus 2 `test_a_shorter_update_interval_shortens_a_running_pause` — `cache_seconds=3599`, drei Fehlschläge
  (Pause 240), `cache_seconds = 0` → nach `tick(61)` ruft der nächste Aufruf ab.
- Review Focus 3 `test_replay_of_an_uncopyable_exception_keeps_its_type` — `class _Picky(Exception): __init__(self, a, *, b)`;
  in der Pause `pytest.raises(_Picky)`.
- Review Focus 4 `test_the_pause_runs_on_the_monotonic_clock` — ohne freezegun; `time.monotonic` per `patch` auf eine
  steuerbare Uhr: +59 → Wiedergabe, +61 → Abruf.

Sieben Tore (`tests/test_weather_clients_fetch_gate.py`, `freeze_time`):

- `test_a_failed_fetch_pauses_its_gate` (parametrisiert) — `_failing(500)`: Ergebnis des 1. Aufrufs merken
  (`("returned", v)` oder `("raised", type, str)`); `get.call_count == case.failed_attempts`; nach `tick(30)` gleiches
  Ergebnis, Zahl unverändert; nach `tick(31)` wieder `+ failed_attempts`.
- Review Focus 1 `test_concurrent_callers_during_an_outage_share_one_failed_run` (parametrisiert) — wie der
  Gleichzeitigkeitstest aus Task 2, aber `_failing(500)`: `get.call_count == case.failed_attempts`, alle fünf
  Ergebnisse gleich.
- `test_a_paused_forecast_does_not_hold_up_current_conditions` — OWM und Met Office: Vorhersage-Tor in Pause,
  `get_data()` ruft ab.
- Review Focus 5 `test_validate_key_ignores_a_running_pause` — OWM `get_data` in Pause; `validate_key()` mit
  `_ok({"cod": 200})` → `get.call_count` steigt um 1.

- [ ] **Step 2: Rot sehen** — Erwartet: die Pausen-Tests FAILED (`calls == 2` statt 1 bzw. `call_count` zu hoch);
  `test_override_cache_bypasses_the_pause`, `test_validate_key_ignores_a_running_pause` und
  `test_a_paused_forecast_does_not_hold_up_current_conditions` dürfen schon grün sein (Pins).
- [ ] **Step 3: `FetchGate.run` um die Pause erweitern.** Kern (Reihenfolge ist die Entscheidung, der Rest ist frei):

```python
def run(self, fetch):
    with self._lock:
        owner = self._owner
        before = getattr(owner, self._stamp_attr)
        was_fresh = is_fresh(before, owner.cache_seconds, owner.override_cache)
        if not was_fresh and not owner.override_cache and self._in_pause():
            return self._replay()                    # no request; DEBUG line with seconds left
        try:
            result = fetch()
        except Exception as exc:
            self._settle(before, was_fresh, raised=True, value=exc)
            raise
        self._settle(before, was_fresh, raised=False, value=result)
        return result
```

  `_settle`: neuer Zeitstempel (`!= before`) → Erfolg, `_failures = 0`, `_failed_at = None`, `_outcome = None`; sonst,
  wenn `not was_fresh` → Fehlschlag: `_failures += 1`, `_failed_at = time.monotonic()`, `_outcome` merken; sonst (aus dem
  Zwischenspeicher bedient) nichts. `_in_pause()` rechnet die Pause **bei jeder Prüfung neu**:
  `min(FIRST_PAUSE_SECONDS * 2 ** min(_failures - 1, 16), cache_lifetime(owner.cache_seconds))`; damit folgt sie einer
  Intervall-Änderung sofort (Review Focus 2). `_replay()`: Rückgabe → derselbe Wert; Ausnahme → `copy.copy(exc)` mit
  `_fetch_gate_replay = True` werfen; scheitert die Kopie, die Original-Instanz markieren und mit
  `with_traceback(None)` werfen. Kommentare an C3, C5, C7 nach `code-doku`.
- [ ] **Step 4: Grün sehen** — beide neuen Dateien plus die vier Client-Testdateien. Erwartet: grün.
- [ ] **Step 5: Commit** — `fix(weather): a failed fetch pauses that document instead of being retried at once`
  (Body: Pause 60 s, verdoppelt, gedeckelt auf das Cache-Fenster; Wiedergabe statt alter Werte; Begründung Kontingente).

---

### Task 4: Wiedergabe leise loggen (C4, Open-Meteo und Met Office)

**Files:** Modify `fetch_gate.py`; `OpenMeteoClient.py:201`, `:311`, `:478`; `MetOfficeClient.py:466`, `:569`.
Test: `tests/test_weather_clients_fetch_gate.py`.

**Interfaces:**
- Consumes: `is_replay` (Task 3).
- Produces: `failure_log_level(exc: BaseException) -> int` = `logging.DEBUG` für eine Wiedergabe, sonst `logging.ERROR`.

- [ ] **Step 1: Test schreiben**

```python
@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_a_replayed_failure_logs_nothing_above_debug(case, caplog):
    # first call with _failing(500) (no assertion on its logs: OWM's forecast lets its OSError
    # out unlogged); caplog.clear(); second call inside the pause (tick(30)) → outcome as before, and
    assert not [r for r in caplog.records
                if r.name.startswith("custom_components.irrigation_plus.weathermodules") and r.levelno > logging.DEBUG]
```

- [ ] **Step 2: Rot sehen** — Erwartet: FAILED für `openmeteo_doc`, `met_hourly`, `met_three_hourly` (ERROR-Zeile
  „… error: 500“); grün für OWM und Pirate (deren Body läuft in der Pause nicht).
- [ ] **Step 3:** Die fünf Stellen auf `_LOGGER.log(failure_log_level(ex), "<unveränderte Meldung>", ex)` umstellen.
- [ ] **Step 4: Grün sehen** — beide neuen Dateien plus `tests/test_weather_modules.py`. Erwartet: grün.
- [ ] **Step 5: Commit** — `fix(weather): a replayed failure is logged at DEBUG, not as a fresh error`.

---

### Task 5: `Retry-After` (C6)

**Files:** Modify `fetch_gate.py`; `OWMClient.py` (`_fetch_data`, `_fetch_forecast`: nach `_SESSION.get`);
`PirateWeatherClient.py` (beide Schleifen: nach `_SESSION.get`). Test: beide Testdateien.

**Interfaces:**
- Produces: `MAX_RETRY_AFTER_SECONDS = 86400`; `retry_after_seconds(response: Any) -> float | None` — liest
  `response.headers.get("Retry-After")`; nur ein `str` zählt (MagicMock-Köpfe in vorhandenen Tests → `None`);
  Ganzzahl-Sekunden ≥ 0 oder HTTP-Datum (`email.utils.parsedate_to_datetime`, Abstand zu
  `datetime.datetime.now(datetime.UTC)`); ≤ 0, unlesbar, fehlend → `None`.
  `FetchGate.note_response(self, response: Any) -> None` — merkt die Antwort des laufenden Versuchs (innerhalb der Sperre,
  also ohne Thread-Lokales). `run` setzt sie vor `fetch()` zurück; `_settle` liest bei einem Fehlschlag
  `retry_after_seconds(gemerkte Antwort)` oder, bei einer Ausnahme, `retry_after_seconds(exc.response)`, wo vorhanden.
  Pause = `max(Backoff aus Task 3, min(retry_after, MAX_RETRY_AFTER_SECONDS))`.

- [ ] **Step 1: Tests schreiben**

```python
# tests/test_weather_fetch_gate.py
@freeze_time("2026-10-23 12:00:00")
def test_retry_after_is_read_as_seconds_or_http_date():
    assert retry_after_seconds(_resp({"Retry-After": "120"})) == 120
    assert retry_after_seconds(_resp({"Retry-After": "Fri, 23 Oct 2026 12:05:00 GMT"})) == 300
    for bad in ("", "soon", "-5", "Fri, 23 Oct 2026 11:00:00 GMT"):
        assert retry_after_seconds(_resp({"Retry-After": bad})) is None
    assert retry_after_seconds(_resp({})) is None
    assert retry_after_seconds(MagicMock()) is None          # non-str header value
```

- `test_a_longer_retry_after_wins_over_the_backoff` — `Retry-After: 900`, `cache_seconds=599`: Wiedergabe bis 899 s,
  Abruf bei 901 s.
- `test_a_shorter_retry_after_keeps_the_backoff` — `Retry-After: 10`: Wiedergabe bei 30 s, Abruf bei 61 s.
- `test_retry_after_is_capped_at_a_day` — `Retry-After: 999999`: Abruf bei 86 401 s.
- Sieben Tore: `test_retry_after_reaches_the_gate` für `owm_data` (Antwort-Kopf, `cod` 429), `pirate_forecast`
  (Status 429, Kopf) und `openmeteo_doc` (über `HTTPError.response`): `_failing(429, {"Retry-After": "900"})` → nach
  `tick(600)` keine neue Anfrage, nach `tick(301)` mindestens eine. Die Zahl je Lauf nicht festnageln: Pirate macht bei
  `429` bis Task 6 drei Versuche, danach einen.

- [ ] **Step 2: Rot sehen** — Erwartet: `ImportError` für `retry_after_seconds`, danach FAILED (Abruf schon bei 61 s).
- [ ] **Step 3:** `retry_after_seconds`, `note_response` und die Einbindung in `_settle`; `self._data_gate.note_response(req)`
  bzw. `self._forecast_gate.note_response(req)` direkt nach jedem `_SESSION.get` in OWM und Pirate.
- [ ] **Step 4: Grün sehen** — beide neuen Dateien plus die vier Client-Testdateien. Erwartet: grün.
- [ ] **Step 5: Commit** — `fix(weather): the pause after a failure honours Retry-After`.

---

### Task 6: Pirate Weather — Pausen zwischen den Versuchen, Abbruch bei `429`/`Retry-After` (C8)

**Files:** Modify `PirateWeatherClient.py` (`import time`; `RETRY_PAUSES_SECONDS = (1, 2)`; neue Methode; beide
Schleifen `:237-247` und `:343-353`). Test: `tests/test_weather_clients_fetch_gate.py`.

**Interfaces:**
- Consumes: `retry_after_seconds`, `FetchGate.note_response` (Task 5).
- Produces: `PirateWeatherClient._get_with_retries(self, gate: FetchGate) -> requests.Response` — bis zu
  `RETRY_TIMES` Versuche; nach jedem `gate.note_response(req)`; Abbruch bei 200, bei 429 oder wenn
  `retry_after_seconds(req) is not None`; zwischen zwei Versuchen `time.sleep(RETRY_PAUSES_SECONDS[i])`, nach dem letzten
  keiner; Netz-Ausnahmen laufen wie heute ungefangen heraus. Beide Bodies rufen sie statt ihrer Schleife; der tote
  Ausdruck `i = i + 1` entfällt.

- [ ] **Step 1: Tests schreiben** — in der Datei eine autouse-Fixture, die `M + "PirateWeatherClient.time.sleep"` durch
  einen `MagicMock` ersetzt (`sleep`), für beide Pirate-Zugriffe parametrisiert:
  - `test_pirate_pauses_one_then_two_seconds_between_retries` — `_failing(500)`: `get.call_count == 3`,
    `sleep.call_args_list == [call(1), call(2)]`.
  - `test_pirate_stops_retrying_on_429` — `_failing(429)`: `call_count == 1`, `sleep` nicht gerufen.
  - `test_pirate_stops_retrying_when_told_when_to_come_back` — `_failing(503, {"Retry-After": "120"})`: `call_count == 1`.
  - `test_pirate_does_not_retry_a_network_error` — `side_effect=requests.ConnectionError`: `call_count == 1` (wie heute).
- [ ] **Step 2: Rot sehen** — Erwartet: `AttributeError` (Modul hat kein `time`), danach FAILED (`call_count == 3`
  bei 429, `sleep` nie gerufen).
- [ ] **Step 3:** `_get_with_retries` einbauen; Kommentar nach `code-doku` (Wurzel: drei Versuche ohne Pause, 429 heißt
  Monatskontingent; NOT-TO-DO: nicht `Retry-After` in der Schleife abwarten — das ist die Pause des Tors).
- [ ] **Step 4: Grün sehen** — beide neuen Dateien plus `tests/test_pirateweather_daily.py
  tests/test_precipitation_guard_real_clients.py`. Erwartet: grün; die Laufzeit dieser Dateien steigt nicht merklich
  (sonst schläft irgendwo ein echter `sleep`).
- [ ] **Step 5: Commit** — `fix(weather): Pirate Weather pauses between retries and stops on 429`.

---

### Task 7: Abschluss lokal

- [ ] **Step 1: Schwester-Pfade** — `grep -n "_SESSION.get\|_request(" custom_components/irrigation_plus/weathermodules/*.py`:
  jede Fundstelle liegt in einem Body hinter einem Tor oder in `validate_key` (C11). Ergebnis hier eintragen.
- [ ] **Step 2: Volle Suite gegen die Basis** — wie Task 0 Step 3, aus `wt`, Ausgabe nach
  `../baseline/suite-branch.txt`, Namen nach `names-branch.txt`; `diff names-c46c41fc.txt names-branch.txt` leer;
  `passed` = Basis + Zahl der neuen Testfälle (aus `pytest --collect-only -q` der zwei neuen Dateien).
- [ ] **Step 3: Mutationen** — je Mutation Datei ändern, die zwei neuen Testdateien mit `-x` laufen lassen (Timeout
  300 s), Killer notieren, `git checkout -- <datei>`. Jede muss rot werden:
  M1 `with self._lock:` → `with contextlib.nullcontext():` · M2 `was_fresh` vor der Sperre berechnen ·
  M3 `_failed_at` nie setzen · M4 Verdopplung weg (`2 ** …` → `1`) · M5 Deckel weg · M6 `max(` → `min(` bei
  `Retry-After` · M7 Pirate-Abbruch bei 429 weg · M8 `failure_log_level` immer `ERROR` · M9 `override_cache` nicht
  beachtet · M10 `_failures = 0` beim Erfolg weg. Überlebende → erst prüfen, ob Tests gesammelt wurden (Memory
  `mutation-survivor-suspects-the-test`), dann Test schärfen.
- [ ] **Step 4: Lint** — `uvx black custom_components/irrigation_plus/` (keine Änderung) und
  `uvx ruff check custom_components/irrigation_plus/` (sauber).
- [ ] **Step 5: Review** — `superpowers:requesting-code-review` auf `upstream/master..HEAD` mit Spec und Plan; Befunde über
  `superpowers:receiving-code-review`.

---

### Task 8: Live-Test HA-Test (Spec §6)

Jeder Schritt nach außen nur mit Freigabe im Chat; davor die Upstream-Runde wiederholen.

- [ ] **Step 1: Vorabversion bauen** nach Memory `hasi-production-on-upstream` (frisch auf `upstream/master` +
  Branding + dieser Branch; Versionen synchron, z. B. `v2026.10.2Xb1`; ZIP aus dem SHA). Push von `production` und
  Release **nur nach Freigabe**.
- [ ] **Step 2: HA-Test aktualisieren** (HACS, Neustart ankündigen), Version per `ha_get_hacs_info` belegen.
- [ ] **Step 3: Vorbereiten** — Wetterdienst Pirate Weather prüfen; Aktualisierung von 60 auf 10 min (alten Wert
  notieren); `logger.set_level` für `custom_components.irrigation_plus.weathermodules.PirateWeatherClient` und
  `…weathermodules.fetch_gate` auf `debug`. Zählweise wie 2026-10-11 (Köpfe der Log-Zeilen, siehe
  `issue89-work\fork89.md`).
- [ ] **Step 4: (a) Zyklus** — ein Aktualisierungszyklus: genau 1 echter `get_forecast_data`, höchstens 1 `get_data`.
- [ ] **Step 5: (b) Zeitplan speichern** — höchstens 1 echter Abruf je Zugriffsart.
- [ ] **Step 6: (c) Fehlschlag** — Schlüssel ungültig machen (Weg mit dem User abstimmen; der Schlüssel liegt in
  `D:\Entwicklung\HASI\secrets\`, nie in Chat, Log oder Commit). 30 Minuten beobachten (Monitor ≤ 30 min, Memory
  `long-waits-need-monitor`): erster Lauf drei Versuche im Abstand ~1 s/2 s; danach Läufe im Abstand
  60/120/240/480/599 s; je Lauf eine ERROR-Zeile des Clients; höchstens 6 Läufe je Tor.
- [ ] **Step 7: Zurückstellen** — Schlüssel, Intervall 60 min, Logger `warning`; HA-Test geprüft wie vorher.
- [ ] **Step 8: Ergebnis** nach `D:\Entwicklung\HASI\issue89-work\live\ergebnis-livetest.md`; was nicht live belegbar
  ist (`Retry-After`, Erholung innerhalb einer Pause), ausdrücklich nennen.

---

### Task 9: Lieferung (Spec §7)

- [ ] **Step 1:** Upstream-Runde; `git log upstream/master..HEAD` frei von eigenen Issue-Verweisen.
- [ ] **Step 2:** PR-Text deutsch im Chat → Freigabe → englisch im Chat → Freigabe. Inhalt: Problem (Messungen),
  Fix (drei Teile + Entdopplung), was nicht live belegbar ist, Angebot `Ratelimit-Reset` (C12), Footer
  `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- [ ] **Step 3:** nach Freigabe `git push -u origin fix/weather-client-fetch-gate`, `gh pr create --repo
  JustChr/HAsmartirrigation --base master --head Eifel-Joe:fix/weather-client-fetch-gate --title "…" --body-file <datei>`;
  PR binden (`ccd_pr`), CI lesen.
- [ ] **Step 4: P2** — Kommentar auf `Eifel-Joe#89` und `#20` (Link zum PR), `#42` nachziehen; Labels bleiben
  `upstream:freigegeben` bis zum Merge. Texte vorher zur Freigabe.
- [ ] **Step 5: P1** — Spec, Plan und Belege (`issue89-work\baseline`, `probe`, `live`) nach Freigabe auf
  `archive/design-history`.
- [ ] **Step 6:** Nebenbefunde N1–N4 (Spec §9) dem User als Issues anbieten; `docs/SESSION-STAND.md` ergänzen.
- [ ] **Step 7 (optional, eigene Freigabe, nach einem Release mit diesem Fix):** HA-Prod-Messung vom 2026-10-11
  wiederholen (OWM, DEBUG nur auf `…weathermodules.OWMClient`, danach zurück auf `warning`): je Erneuerung 1 echter
  Abruf statt 1 bzw. 3.
