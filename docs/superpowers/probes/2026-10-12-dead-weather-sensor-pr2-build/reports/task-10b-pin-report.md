# Task 10b: Pin fuer `if outage.end is None` in `_stale_issue_key`

Commit: 030e12a3b32dbdfae3a839293a84ec85b78c1fdd (Branch feat/pause-silent-weather-sensor, Basis 549d5e2e)
Geaendert: nur tests/test_sensor_liveness_coordinator.py (+26 Zeilen)

## Test-Code (Klasse TestThePausedNotice)

```python
    async def test_a_closed_temperature_outage_leaves_an_open_rain_gauge_plain(
        self, monkeypatch
    ):
        """Only an open outage counts for the text: the temperature is back, and
        what is silent now is a gauge the calculation does not cut."""
        group = self._rain_gauge_group({"Temperature": "sensor.temp"})
        group[const.MAPPING_SENSOR_OUTAGES] = [
            Outage(
                "sensor.temp",
                "dev1",
                ("Temperature",),
                T0 - timedelta(days=2),
                T0 - timedelta(days=1),
            ).to_store(),
            Outage(
                "sensor.rain", "dev1", ("Precipitation",), T0 - timedelta(hours=5)
            ).to_store(),
        ]
        coord, store, issues = _coord(monkeypatch, [group], {}, {})

        coord.async_resync_stale_issue(store.get_mapping(1))

        assert issues.open["weather_sensor_stale_1"]["translation_key"] == (
            const.ISSUE_WEATHER_SENSOR_STALE
        )
```

Pfad: `async_resync_stale_issue` -> `_sync_stale_issue` -> `_stale_issue_key` (Gruppe pausiert, Stundenrechnung aus
durch `_pausing`/Store ohne hourly, Niederschlag mit Aggregat `delta`).

## Gruen (vor der Mutation)

`TZ=UTC .../.venv/Scripts/python.exe -m pytest tests/test_sensor_liveness_coordinator.py -p _local_socket_unblock -q`
-> `49 passed in 3.57s`

## Rot unter der Mutation

Backup: `D:\Entwicklung\HASI\issue8-pr2-work\sdd\tmp\sensor_liveness.py.bak`.
Zeile 608 (`            if outage.end is None`) per `sed -i '608d'` entfernt, nur den neuen Test (`-k`) gelaufen:

```
FAILED tests/test_sensor_liveness_coordinator.py::TestThePausedNotice::test_a_closed_temperature_outage_leaves_an_open_rain_gauge_plain
E   AssertionError: assert 'weather_sensor_stale_paused' == 'weather_sensor_stale'
====================== 1 failed, 48 deselected in 1.95s =======================
```

## Ruecksetz-Beleg

- `cp` Backup -> `sensor_liveness.py`; `cmp` gegen Backup: identisch.
- `git diff --quiet -- custom_components/` -> wahr (Ausgabe "TRUE").
- Nach dem Zuruecksetzen erneut die ganze Datei: `49 passed in 3.56s`.
- `uvx black tests/test_sensor_liveness_coordinator.py`: "1 file left unchanged".
- Nach dem Commit: `git status --short` leer.

## Bedenken

Keine. Der Test liegt neben den beiden Rain-Gauge-Tests, nutzt deren Helfer (`_rain_gauge_group`, `_coord`),
bleibt ohne Issue-/Plan-Kuerzel. Nicht gepusht.
