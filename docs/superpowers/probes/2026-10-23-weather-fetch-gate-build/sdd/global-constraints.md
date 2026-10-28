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

