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

