7 failed / **3989 passed** / 9 skipped / 487 errors gegen die Baseline 7 / 3925 / 9 / 466 desselben Commits
  (`6fa424e8`, gemessen 2026-10-13). +64 passed = die neuen Fälle (9 + 17 + 9 + 10 + 8 + 5 + 6); FAILED-Namen identisch;
  es entfallen nur die zwei in Task 5 umbenannten Namen; die neuen ERROR-Namen sind alle Teardown-Fehler „Lingering
  timer“ der Tests mit echtem Koordinator (`test_live_estimate_silent_sensor.py` 8, `…_daily.py` 5,
  `test_silent_sensor_hourly_commit.py` 8, die 2 umbenannten in `test_silent_sensor_commit.py`), „Lingering timer“
  932 → 974 (= 2 × 21).
