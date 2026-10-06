# Gemeinsamer Auftrag für die Implementer (Plan „Geräte-Registry vor HA 2027.8“)

## Worum es geht

Home Assistant 2026.8 hat zwei Aufrufe der Geräte-Registry ersetzt, die alten fallen in 2027.8 weg:
`via_device` (Eltern-Verweis im `device_info`) → `via_device_id`, und `async_get_device(identifiers=…)` →
`async_get_device_by_identifier(identifier, config_entry_id)`. Die Integration (`custom_components/irrigation_plus/`)
muss aber weiter ab HA 2025.5 laufen, wo es die neuen Aufrufe nicht gibt. Deshalb fragen drei kleine Helfer in
`entity.py` die **Klasse** der Registry, was sie anbietet (`hub_link_for`, `find_device`), bzw. lesen, was das Setup
entschieden hat (`hub_link`). Der Plan diktiert jeden Code- und Testblock wörtlich; er ist in einem Wegwerf-Worktree
bereits einmal komplett probegelaufen (jede RED-/GREEN-Erwartung unten ist dort gemessen).

Du setzt **genau einen Task** um. Der Task-Text steht in der Datei, die dir der Auftrag nennt
(`D:\Entwicklung\HASI\issue11-work\prompts\t<N>-plan.md`, ein wörtlicher Ausschnitt des Plans).

## Arbeitsumgebung

- **Nur hier arbeiten:** `D:\Entwicklung\HASI\issue11-work\wt` (Git-Worktree, Branch `fix/device-registry-2027-8`,
  Basis `7001c754`). Git-Befehle mit `git -C D:/Entwicklung/HASI/issue11-work/wt …` oder nach `cd` dorthin.
  Es gibt dort **kein** eigenes `.venv`; `_local_socket_unblock.py` liegt im Worktree (ausgeblendet, nie committen).
- **Tests** (aus dem Worktree-Verzeichnis, absoluter Interpreter):
  `/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest <pfad> -p _local_socket_unblock -q`
- **Plan-Blöcke anwenden — ausschließlich mit dem Werkzeug, nie von Hand:**
  `python D:/Entwicklung/HASI/issue11-work/apply_plan_task.py D:/Entwicklung/HASI/issue11-work/wt <N> tests`
  bzw. `… <N> code`. Es liest die Blöcke des Tasks wörtlich aus dem Plan und bricht mit `STOP` ab, wenn ein Anker
  nicht genau einmal vorkommt oder eine anzulegende Datei schon existiert. **Bei `STOP`: nichts anpassen, nichts von
  Hand nachbauen, sofort mit Status BLOCKED und der vollständigen Werkzeug-Ausgabe zurückmelden.**
- **Lint:** `uvx black custom_components/irrigation_plus/ tests/test_device_registry_compat.py` (muss
  „unchanged“ melden, also nichts ändern) und `uvx ruff check custom_components/irrigation_plus/` (muss „All checks
  passed!“ melden). Ändert black doch etwas: nicht committen, BLOCKED melden mit `git diff`.

## Reihenfolge (TDD, verbindlich)

1. `… <N> tests` anwenden.
2. **RED:** den im Task genannten Testbefehl laufen lassen. Die Ausgabe muss der Erwartung des Tasks entsprechen
   (Zusammenfassungszeile und Fehlermeldung). Weicht sie ab: STOP, nicht weitermachen, Ausgabe zurückmelden.
3. `… <N> code` anwenden.
4. **GREEN:** den im Task genannten Testbefehl laufen lassen; Erwartung wie im Task.
5. Lint wie oben; `git status --short` darf nur die Dateien des Tasks zeigen.
6. Commit: `git add` genau der im Task genannten Dateien, dann `git commit -F - <<'EOF' … EOF` mit der Message des
   Tasks **wörtlich** (inklusive der letzten Zeile `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; keine
   Zeile hinzufügen, keine ändern).

## Lokale Eigenheiten (kein Fehler des Plans)

- Ab Task 3 enden die zwei Setup-Tests (`TestSetupRecordsTheLink`) lokal **zusätzlich** mit
  `ERROR at teardown … Lingering timer after job … SensorLivenessMixin._async_sensor_liveness_tick` (Windows-Umgebung;
  in der echten CI sauber). RED und GREEN liest man an der **Testphase** ab („failed“/„passed“); diese zwei
  teardown-ERRORs stehen in jedem Lauf der neuen Datei. Ein ERROR, der **nicht** „at teardown“ mit „Lingering timer“
  ist, ist echt: STOP.
- `tests/test_init.py::…::test_async_setup_entry_success` und `…_with_weather_service` scheitern lokal schon auf der
  Basis (aiodns unter Windows) — Vorbestand.
- Nach dem Lauf erscheinen manchmal harmlose `ProactorEventLoop … '_ssock'`/`__del__`-Meldungen — zählen nicht.

## Verboten

- `git push`, `git fetch`, `git stash`, `git reset`, `git rebase`, `git commit --amend`, Branch-Operationen, Änderungen
  außerhalb des Worktrees, weitere pytest-Läufe außer den im Task genannten (keine volle Suite — die fährt der
  Controller), Änderungen an Dateien, die der Task nicht nennt.
- Jeder Text (Code, Test, Commit-Message), der auf Issue-/PR-Nummern oder Dokumente verweist (`Eifel-Joe#…`,
  `JustChr#…`, „Task 3“, „spec …“). Die Blöcke des Plans sind schon sauber — wörtlich übernehmen genügt.

## Bericht (am Ende, knapp)

- **Status:** DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
- RED: die Zusammenfassungszeile und die maßgebliche Fehlermeldung (wörtlich kopiert)
- GREEN: die Zusammenfassungszeile (wörtlich)
- Lint: die Ausgabezeilen von black und ruff (wörtlich)
- `git status --short` direkt vor dem Commit
- Commit-SHA (`git log -1 --format=%H`) und `git show --stat --format=%B HEAD` (wörtlich)
- Auffälligkeiten (nur wenn es welche gibt)
