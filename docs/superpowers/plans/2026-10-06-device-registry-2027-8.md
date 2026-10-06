# Geräte-Registry vor HA 2027.8 — Implementierungsplan

> **Für agentische Ausführung:** PFLICHT-SKILL: `superpowers:subagent-driven-development` (empfohlen) oder
> `superpowers:executing-plans`, Task für Task. Schritte nutzen Checkboxen (`- [ ]`).

**Ziel:** Zonen- und Verteiler-Geräte nennen ihren Hub und werden beim Löschen gefunden, ohne die beiden in HA 2027.8
entfallenden Aufrufe (`via_device`, `async_get_device`), solange HA sie schon ersetzt, und unverändert auf HA unter 2026.8.

**Architektur:** Drei kleine Helfer in `entity.py` fragen die Klasse der Geräte-Registry, was sie anbietet
(`hub_link_for`, `find_device`), oder lesen, was das Setup entschieden hat (`hub_link`). `async_setup_entry` legt den
Verweis auf den Hub einmal ab; die beiden Geräte-Infos und die zwei Löschpfade nutzen die Helfer.

**Tech-Stack:** Python 3.12 (lokale Test-Env), Home Assistant 2024.12.5 über `pytest-homeassistant-custom-component`
(lokal; JustChrs CI: 2026.2.3 und 2025.5.0, Python 3.13).

**Stand:** Plan vom User am 2026-10-06 im Chat freigegeben. Umsetzung seit 2026-10-06 im Worktree `issue11-work\wt`;
Task 1b kam aus dem Quality-Review von Task 1 dazu (nicht Teil der Freigabe, eigener Commit; Begründung dort).

**Spec:** `docs/superpowers/specs/2026-10-06-device-registry-2027-8-design.md` (freigegeben 2026-10-06, archiviert
`archive/design-history` `bda83840`; danach um „Präzisierungen aus der Planung“ ergänzt).

**Probelauf (2026-10-06, gegen `7001c754`):** `D:\Entwicklung\HASI\issue11-work\apply_plan_task.py` hat jeden
„Lege an“-, „Ersetze“- und „Hänge an“-Block dieses Plans wörtlich im Wegwerf-Worktree `issue11-work\probe-wt`
angewandt; jeder Anker passte genau einmal.
- Jeder Task wurde mit genau den hier genannten Meldungen RED und danach GREEN; nach jedem Task waren black und ruff
  sauber, black änderte nichts (auch nicht an der Testdatei).
- Volle Suite `7 failed, 3795 passed, 9 skipped, 417 errors` gegen die Baseline `7 / 3783 / 9 / 415`
  (`run-probe.log`); neu sind genau die zwei teardown-ERRORs der Setup-Tests, nichts fiel weg.
- Mutationen: **16/16 KILLED** (`mutate-probe.txt`), jede durch mindestens einen Test der neuen Datei.
- Schwester-Pfade, eigene Verweise und Frontend wie in Task 6 geprüft: sauber.
- Getesteter Stand: `D:\Entwicklung\HASI\issue11-work\probe-2026-10-06.patch` (gilt bei Abweichung vom Plan).
- **Nachtrag Task 1b (2026-10-06):** die Blöcke von Task 1b im `probe-wt` auf dem Stand nach Task 5 angewandt (jeder
  Anker genau einmal); RED `1 failed, 15 passed, 2 errors` (der `NameError`-Test), GREEN mit den drei Dateien aus
  Task 1 `33 passed, 2 errors`; black und ruff sauber (auch ruff auf der Testdatei); Mutationen **23/23 KILLED**
  (`mutate-probe-1b.txt`, M17–M23 je durch den dafür gedachten Test). Probe-Commit `51e2a6da` (nach dem Re-Review per Amend berichtigt; erste Fassung `43931cae`); getesteter Stand
  jetzt `probe-2026-10-06-1b.patch`, der Nachtrag allein `delta-1b.patch`. Die Zahlen der Tasks 2–6 sind um die
  vier Tests aus 1b nachgezogen (mit „1b“ markiert).
- **Nachtrag Task 2b (2026-10-06):** aus dem Quality-Review von Task 2; Blöcke im `probe-wt` auf dem Stand nach
  Task 5 + 1b angewandt (jeder Anker genau einmal), Pin sofort grün, Mutationen M24–M26 neu. Belege und SHA unten in
  Task 2b bzw. im Sitzungsstand; die Zahlen der Tasks 3–6 sind um den einen Test nachgezogen (mit „1b/2b“ markiert).
- **Nachtrag Task 3b (2026-10-06):** aus dem Quality-Review von Task 3; ein Setup-Test mehr (Reihenfolge vor den
  Plattformen, Überschreiben, Lesen der Id-Form), lokal mit einem dritten teardown-ERROR; Mutationen M27/M28 neu.
  Probe auf dem Endstand: `18 passed, 3 errors` (drei teardown „Lingering timer“, einzeln geprüft), black/ruff
  sauber, **28/28 KILLED** (`mutate-probe-3b.txt`), Probe-Commit `9cdd024e` (nach dem Re-Review per Amend; erste Fassung `b4e9246a`), getesteter Stand
  `probe-2026-10-06-3b.patch`.
  Die Zahlen der Tasks 4–6 sind nachgezogen (mit „3b“ markiert).
- **Nachtrag Task 4b (2026-10-06):** aus dem Quality-Review von Task 4; zwei Tests am Zonen-Löschpfad (Fehlschlag,
  alte Bauart ohne `entry`) und ein Kommentar; Mutationen M29–M32 neu. Probe auf dem Endstand: `20 passed, 3 errors`,
  black/ruff sauber, **32/32 KILLED** (`mutate-probe-4b.txt`), Probe-Commit `e1a3b695`, getesteter Stand
  `probe-2026-10-06-4b.patch`. Die Zahlen der Tasks 5–6 sind nachgezogen
  (mit „4b“ markiert).
- **Nachtrag Task 5b (2026-10-06):** aus dem Quality-Review von Task 5, Schwester-Pfad zu 4b; zwei Tests am
  Verteiler-Löschpfad (Fehlschlag, alte Bauart ohne `entry`), der falsche Funktionsverweis im Kommentar berichtigt,
  gleicher Toleranz-Kommentar an beiden Löschpfaden; Mutationen M33–M36 neu. Die Zahlen von Task 6 sind nachgezogen.
  Probe auf dem Endstand: `22 passed, 3 errors`, mit den Verteiler-Dateien `58 passed, 3 errors`, black/ruff sauber,
  **36/36 KILLED** (`mutate-probe-5b.txt`), Probe-Commit `a9a8e834` (nach dem Re-Review per Amend; erste Fassung `ca19d96b`), getesteter Stand
  `probe-2026-10-06-5b.patch`.

## Arbeitsumgebung

- **Worktree:** `D:\Entwicklung\HASI\issue11-work\wt`, Branch `fix/device-registry-2027-8`, Basis `7001c754`
  (`upstream/master`), ohne Tracking. `_local_socket_unblock.py` liegt im Worktree (über `.git/info/exclude`
  ausgeblendet).
- **Tests** (aus dem Worktree; es gibt dort kein eigenes `.venv`):
  `/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest <pfad> -p _local_socket_unblock -q`
- **Plan-Blöcke anwenden:** `python D:/Entwicklung/HASI/issue11-work/apply_plan_task.py D:/Entwicklung/HASI/issue11-work/wt <N> tests`
  bzw. `… <N> code`. Das Werkzeug liest jeden „Lege an“-, „Ersetze“- und „Hänge an“-Block dieses Plans wörtlich und
  bricht ab, wenn ein Anker nicht genau einmal vorkommt oder eine anzulegende Datei schon existiert.
- **Volle Suite mit Namensvergleich:** `bash /d/Entwicklung/HASI/issue11-work/run_suite.sh wt <tag>` →
  `issue11-work\suite-<tag>.txt`, `names-<tag>.txt`, Vergleich gegen `names-base.txt` (Baseline auf `7001c754`).
- **Lint** (zählt in CI, nur das Integrationsverzeichnis): `uvx black custom_components/irrigation_plus/` und
  `uvx ruff check custom_components/irrigation_plus/`. Die Testdatei zusätzlich mit `uvx black` formatieren.
  ruff prüft auch die Import-Reihenfolge (Regel `I`).
- **Commits:** einer je grünem Task, Message per Heredoc (`git commit -F - <<'EOF' … EOF`), Englisch, endet mit
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. **Kein Text verweist auf unsere Issues oder auf
  JustChrs Nummern** (`Eifel-Joe#…`, `JustChr#…`, Spec- oder Task-Nummern), weder im Code noch in Tests noch in
  Commit-Messages: der PR geht an JustChr, und `JustChr#N` in einer Fork-Commit-Message legt auf seinem PR einen
  Rückverweis an.
- **Anker:** Jeder „Ersetze“-Block kommt in seiner Datei genau einmal vor. Kommt er nicht oder mehrfach vor, ist die
  Basis eine andere als geplant: STOP und melden, nicht frei anpassen.
- ⚠️ **Lokaler Vorbestand, kein Fehler dieses Plans:** Die zwei Setup-Tests aus Task 3 enden lokal **zusätzlich** mit
  `ERROR at teardown … Lingering timer after job … SensorLivenessMixin._async_sensor_liveness_tick` (der 300-s-Takt,
  den das Setup scharf schaltet; dieselbe Art steht für andere Coordinator-Tests in der Baseline, in JustChrs CI laufen
  sie sauber). RED und GREEN liest man an der **Testphase** ab („failed“ bzw. „passed“); die zwei teardown-ERRORs
  bleiben von Task 3 an in jedem Lauf der neuen Datei stehen. Ein ERROR, der **nicht** „at teardown“ mit „Lingering
  timer“ ist, ist echt: STOP.
- ⚠️ **Ebenfalls lokal:** `test_init.py::…::test_async_setup_entry_success` und `…_with_weather_service` scheitern in
  der Baseline an `aiodns needs a SelectorEventLoop on Windows`. Die neuen Setup-Tests ersetzen deshalb zusätzlich
  `async_get_clientsession` durch einen Stub.

## Datei-Übersicht

| Datei | Änderung | Task |
|---|---|---|
| `custom_components/irrigation_plus/entity.py` | `hub_link_for`, `hub_link`, `find_device`; Geräte-Infos nutzen `hub_link` | 1, 1b, 2, 2b |
| `custom_components/irrigation_plus/__init__.py` | Setup legt `hub_link` ab; Zone löschen über `find_device` | 3, 4, 4b, 5b |
| `custom_components/irrigation_plus/distributor.py` | Verteiler löschen über `find_device` | 5, 5b |
| `tests/test_device_registry_compat.py` | neu | 1, 1b, 2, 2b, 3, 3b, 4, 4b, 5, 5b |

---

### Task 0: Worktree und Baseline

- [x] **Schritt 1: Worktree**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git fetch upstream
git worktree add -b fix/device-registry-2027-8 D:/Entwicklung/HASI/issue11-work/wt upstream/master
git -C D:/Entwicklung/HASI/issue11-work/wt branch --unset-upstream
cp _local_socket_unblock.py D:/Entwicklung/HASI/issue11-work/wt/
git -C D:/Entwicklung/HASI/issue11-work/wt log -1 --format=%h
```
Expected: `7001c754`. Ein anderer Kopf heißt: upstream hat sich bewegt → Baseline neu messen (Schritt 2) und vor
Task 1 jeden Anker prüfen (`apply_plan_task.py` bricht sonst ab).

- [x] **Schritt 2: Baseline** — nur falls `D:\Entwicklung\HASI\issue11-work\names-base.txt` fehlt oder die Basis nicht
  `7001c754` ist: `bash /d/Entwicklung/HASI/issue11-work/run_suite.sh wt base`.

---

### Task 1: Der Hub-Verweis richtet sich nach der Registry

**Files:** Modify `custom_components/irrigation_plus/entity.py`; Create `tests/test_device_registry_compat.py`.

- [x] **Schritt 1: Testdatei anlegen**

**Lege `tests/test_device_registry_compat.py` an:**
```python
"""Device-registry calls across Home Assistant's 2026.8 change.

Home Assistant 2026.8 added ``via_device_id`` and
``async_get_device_by_identifier``; ``via_device`` and ``async_get_device`` are
deprecated and go in 2027.8. Before 2026.8 neither replacement exists, and the
declared floor is 2025.5. The integration asks the registry which shape it has,
so both shapes are pinned here with stand-ins, whichever Home Assistant the
suite runs against.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from custom_components.irrigation_plus import (
    SmartIrrigationCoordinator,
    async_setup_entry,
    const,
)
from custom_components.irrigation_plus.entity import (
    distributor_device_info,
    hub_link,
    hub_link_for,
    zone_device_info,
)
from tests.test_distributor import _host

_HUB = "hub-device-id"
_ZONE = (const.DOMAIN, "cid_zone_1")


class _RegistryFrom2026_8:
    """The device registry's shape from Home Assistant 2026.8 on."""

    def __init__(self, device=None):
        self.device = device
        self.calls = []

    def async_get_or_create(self, *, config_entry_id, via_device_id=None, **kwargs):
        self.calls.append(("get_or_create", config_entry_id))
        return SimpleNamespace(id=_HUB)

    def async_get_device_by_identifier(self, identifier, config_entry_id):
        self.calls.append(("by_identifier", identifier, config_entry_id))
        return self.device

    def async_get_device(self, identifiers=None, connections=None):
        self.calls.append(("get_device", identifiers))
        return self.device

    def async_remove_device(self, device_id):
        self.calls.append(("remove", device_id))


class _RegistryBefore2026_8:
    """The device registry's shape from the declared floor (2025.5) to 2026.7."""

    def __init__(self, device=None):
        self.device = device
        self.calls = []

    def async_get_or_create(self, *, config_entry_id, via_device=None):
        raise AssertionError("only the signature is read")

    def async_get_device(self, identifiers=None, connections=None):
        self.calls.append(("get_device", identifiers))
        return self.device

    def async_remove_device(self, device_id):
        self.calls.append(("remove", device_id))


class TestTheHubLinkFollowsTheRegistry:
    """Which key names the hub as parent depends on what the registry takes."""

    def test_a_registry_taking_via_device_id_gets_the_hubs_registry_id(self):
        assert hub_link_for(_RegistryFrom2026_8(), _HUB, "cid") == {
            "via_device_id": _HUB
        }

    def test_a_registry_before_it_gets_the_hubs_identifier(self):
        assert hub_link_for(_RegistryBefore2026_8(), _HUB, "cid") == {
            "via_device": (const.DOMAIN, "cid")
        }

    def test_a_test_double_gets_the_identifier_form(self):
        assert hub_link_for(Mock(), _HUB, "cid") == {
            "via_device": (const.DOMAIN, "cid")
        }

    def test_zone_and_distributor_devices_carry_the_recorded_link(self):
        hass = SimpleNamespace(
            data={const.DOMAIN: {"hub_link": {"via_device_id": _HUB}}}
        )
        for info in (
            zone_device_info(hass, 1, "Lawn"),
            distributor_device_info(hass, 0, "Gardena1"),
        ):
            assert info["via_device_id"] == _HUB
            assert "via_device" not in info

    def test_without_a_record_the_identifier_form_stands(self):
        hass = SimpleNamespace(data={})
        assert hub_link(hass) == {"via_device": (const.DOMAIN, const.DOMAIN)}
        info = zone_device_info(hass, 1, "Lawn")
        assert info["via_device"] == (const.DOMAIN, const.DOMAIN)
        assert "via_device_id" not in info
```

- [x] **Schritt 2: RED**

Run: `/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_device_registry_compat.py -p _local_socket_unblock -q`
Expected: `ImportError: cannot import name 'hub_link' from 'custom_components.irrigation_plus.entity'`, `1 error`.

- [x] **Schritt 3: Implementierung**

**Ersetze in `custom_components/irrigation_plus/entity.py`:**
```python
single hub device (via_device). Returns plain dicts (HA accepts these for
``device_info``) to avoid importing DeviceInfo from the test-mocked
device_registry module.
"""

from homeassistant.core import HomeAssistant
```
**durch:**
```python
single hub device (see ``hub_link``). Returns plain dicts (HA accepts these for
``device_info``) to avoid importing DeviceInfo from the test-mocked
device_registry module.
"""

import inspect

from homeassistant.core import HomeAssistant
```

**Ersetze in `custom_components/irrigation_plus/entity.py`:**
```python
        "sw_version": const.VERSION,
    }


def zone_device_info(hass: HomeAssistant, zone_id, zone_name: str) -> dict:
    """A per-zone device, parented to the hub via ``via_device``.
```
**durch:**
```python
        "sw_version": const.VERSION,
    }


def hub_link_for(registry, hub_device_id: str, cid: str) -> dict:
    """How a zone or distributor device names the hub as its parent.

    Home Assistant 2026.8 added ``via_device_id`` (the parent's registry id)
    and deprecated ``via_device`` (the parent's identifier), which goes in
    2027.8. Before 2026.8 ``via_device_id`` does not exist: there,
    ``async_get_or_create`` has a fixed keyword-only signature, and the
    ``TypeError`` would stop every zone entity from being added. So ask the
    registry which one it takes rather than branching on a version string; the
    question goes to the registry's class, as in ``find_device``. Once the
    declared floor is 2026.8 or later, return the id form outright.
    """
    method = getattr(type(registry), "async_get_or_create", None)
    try:
        takes_id = "via_device_id" in inspect.signature(method).parameters
    except (TypeError, ValueError):
        takes_id = False
    if takes_id:
        return {"via_device_id": hub_device_id}
    return {"via_device": (const.DOMAIN, cid)}


def hub_link(hass: HomeAssistant) -> dict:
    """The parent link for zone and distributor devices, as setup recorded it.

    ``async_setup_entry`` records it once the hub is registered (see
    ``hub_link_for``). Without a record, as for an entity built outside a
    set-up entry, the identifier form stands; every Home Assistant up to 2027.8
    takes it.
    """
    try:
        link = hass.data[const.DOMAIN].get("hub_link")
    except (KeyError, AttributeError, RuntimeError):
        link = None
    if isinstance(link, dict) and link:
        return dict(link)
    return {"via_device": (const.DOMAIN, coordinator_id(hass))}


def zone_device_info(hass: HomeAssistant, zone_id, zone_name: str) -> dict:
    """A per-zone device, parented to the hub (see ``hub_link``).
```

**Ersetze in `custom_components/irrigation_plus/entity.py`:**
```python
        "model": "Irrigation zone",
        "manufacturer": const.MANUFACTURER,
        "via_device": (const.DOMAIN, cid),
    }
```
**durch:**
```python
        "model": "Irrigation zone",
        "manufacturer": const.MANUFACTURER,
        **hub_link(hass),
    }
```

**Ersetze in `custom_components/irrigation_plus/entity.py`:**
```python
    """A per-distributor device, parented to the hub via ``via_device``."""
```
**durch:**
```python
    """A per-distributor device, parented to the hub (see ``hub_link``)."""
```

**Ersetze in `custom_components/irrigation_plus/entity.py`:**
```python
        "model": "Gardena water distributor",
        "manufacturer": const.MANUFACTURER,
        "via_device": (const.DOMAIN, cid),
    }
```
**durch:**
```python
        "model": "Gardena water distributor",
        "manufacturer": const.MANUFACTURER,
        **hub_link(hass),
    }
```

- [x] **Schritt 4: GREEN**

Run: `/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_device_registry_compat.py tests/test_distributor_entities.py "tests/test_sensor.py::TestSmartIrrigationZoneEntity::test_device_info" -p _local_socket_unblock -q`
Expected: `22 passed` (5 neue, 16 aus `test_distributor_entities.py`, `test_device_info`); die bestehenden Pins
(`test_device_info`, `test_distributor_device_info_identifiers_and_via_device`) bleiben unverändert grün.

- [x] **Schritt 5: Lint** — `uvx black custom_components/irrigation_plus/ tests/test_device_registry_compat.py` ändert
  nichts (`git status --short` zeigt nur die zwei Dateien des Tasks); `uvx ruff check custom_components/irrigation_plus/`
  sauber.

- [x] **Schritt 6: Commit**

```bash
git add custom_components/irrigation_plus/entity.py tests/test_device_registry_compat.py
git commit -F - <<'EOF'
fix(devices): name the hub by registry id where Home Assistant takes it

Home Assistant 2026.8 added via_device_id and deprecated via_device, which goes
in 2027.8; before 2026.8 the id form does not exist, and the declared floor is
2025.5. The zone and distributor device infos now carry the parent link that
setup records (hub_link), and hub_link_for decides it from what the registry's
async_get_or_create takes. Without a record the identifier form stays, so
nothing changes until setup records one.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 1b: Nachtrag aus dem Quality-Review von Task 1

**Herkunft:** Quality-Review von Task 1 (2026-10-06), vom Controller gegen die HA-Quellen und CPython 3.14
nachgeprüft. Nicht Teil des am 2026-10-06 freigegebenen Plans; eigener Commit, damit er sich vor dem Push sauber
wieder herausnehmen lässt.

- **Latenter Setup-Abbruch (behoben):** HA braucht seit 2026.3.0 Python 3.14 (`pyproject.toml`
  `requires-python = ">=3.14.2"`; 2026.2.3: `">=3.13.2"`), und seit 2026.6.0 verzichtet `device_registry.py` auf
  `from __future__ import annotations` (2026.3.0–2026.5.0 haben es noch). Erst damit wertet `inspect.signature` dort die
  Annotationen aus (`annotation_format=Format.VALUE`, CPython v3.14.0 `inspect.py:3309-3310` und `:2325`). Ein Name,
  den die Registry nur unter `TYPE_CHECKING` importiert, wirft dann `NameError`; `hub_link_for` fing nur
  `TypeError`/`ValueError`, und das Setup bräche an der Erkennung ab. Heute nur latent: in 2026.6.0 bis 2026.9.4 sind
  alle Annotationsnamen von `async_get_or_create` zur Laufzeit gebunden (AST-Prüfung des Controllers); dieselbe Datei
  legt aber `ConfigEntry` und `entity_registry` schon hinter `TYPE_CHECKING`. (Erste Fassung von 1b sagte „3.14 ab
  2026.6“ — im Re-Review als falsch erkannt, nachgeprüft, per Amend berichtigt.)
- **Ungepinnte Entscheidungen (jetzt gepinnt):** die Regel an der Bauart von 2026.8.0 selbst (beide Schlüssel benannt,
  kein `**kwargs`; `ha-2026.8.0-device_registry.py:1768-1769`), sonst überleben die Mutanten „hat `**kwargs`“ und
  „`via_device` fehlt“; der Wächter `isinstance(link, dict) and link` und die `AttributeError`-Toleranz in `hub_link`;
  die Kopie, die `hub_link` herausgibt.
- **Docstrings genauer:** `DeviceEntry.via_device_id` gibt es lange vor 2026.8 (2025.5.0 `device_registry.py:295`);
  neu ist der Parameter von `async_get_or_create` bzw. der Schlüssel im Device-Info. Ab 2026.9 meldet HA das alte
  `via_device`.
- **Nicht übernommen (begründet):** `type()` in `hub_link_for` gegen die Instanz pinnen (kein beobachtbarer
  Unterschied, ein `Mock()` ergibt in beiden Fällen die Kennungs-Form; wo es zählt, in `find_device`, pinnt es M09);
  den Inhalt des Records prüfen (einziger Schreiber ist das Setup mit `hub_link_for`s Antwort); eine Konstante statt
  `"hub_link"` (das Repo führt auch `"coordinator"` als Literal); keyword-only-Parameter (die Reihenfolge pinnen
  Task 3 und M08).

**Files:** Modify `custom_components/irrigation_plus/entity.py`; Test `tests/test_device_registry_compat.py`.

- [x] **Schritt 1: Tests**

**Ersetze in `tests/test_device_registry_compat.py`:**
```python
declared floor is 2025.5. The integration asks the registry which shape it has,
so both shapes are pinned here with stand-ins, whichever Home Assistant the
suite runs against.
"""
```
**durch:**
```python
declared floor is 2025.5. The integration asks the registry which shape it has,
so each shape is pinned here with stand-ins, whichever Home Assistant the suite
runs against.
"""
```

**Ersetze in `tests/test_device_registry_compat.py`:**
```python
from unittest.mock import AsyncMock, Mock, patch
```
**durch:**
```python
from unittest.mock import AsyncMock, MagicMock, Mock, patch
```

**Ersetze in `tests/test_device_registry_compat.py`:**
```python
class _RegistryFrom2026_8:
    """The device registry's shape from Home Assistant 2026.8 on."""
```
**durch:**
```python
class _RegistryFrom2026_8:
    """The device registry's shape from Home Assistant 2026.9 on.

    ``via_device`` only reaches it through ``**kwargs``. The per-entry lookup is
    there since 2026.8; ``_RegistryOf2026_8_0`` has 2026.8.0's own signature.
    """
```

**Ersetze in `tests/test_device_registry_compat.py`:**
```python
class TestTheHubLinkFollowsTheRegistry:
```
**durch:**
```python
class _RegistryOf2026_8_0:
    """2026.8.0 itself: both keys named, and no ``**kwargs`` yet."""

    def async_get_or_create(
        self, *, config_entry_id, via_device=None, via_device_id=None
    ):
        raise AssertionError("only the signature is read")


class TestTheHubLinkFollowsTheRegistry:
```

**Ersetze in `tests/test_device_registry_compat.py`:**
```python
        info = zone_device_info(hass, 1, "Lawn")
        assert info["via_device"] == (const.DOMAIN, const.DOMAIN)
        assert "via_device_id" not in info
```
**durch:**
```python
        info = zone_device_info(hass, 1, "Lawn")
        assert info["via_device"] == (const.DOMAIN, const.DOMAIN)
        assert "via_device_id" not in info

    def test_a_registry_naming_both_keys_gets_the_hubs_registry_id(self):
        assert hub_link_for(_RegistryOf2026_8_0(), _HUB, "cid") == {
            "via_device_id": _HUB
        }

    def test_a_signature_that_cannot_be_read_leaves_the_identifier_form(self):
        class _Unreadable:
            """Reading it fails, as on Python 3.14 for an unbound annotation."""

            @property
            def __signature__(self):
                raise NameError("an annotation names what is not bound")

            def __call__(self, **kwargs):
                raise AssertionError("only the signature is read")

        class _Registry:
            async_get_or_create = _Unreadable()

        assert hub_link_for(_Registry(), _HUB, "cid") == {
            "via_device": (const.DOMAIN, "cid")
        }

    def test_anything_but_a_recorded_link_leaves_the_identifier_form(self):
        for hass in (
            SimpleNamespace(data={const.DOMAIN: {"hub_link": {}}}),
            SimpleNamespace(data={const.DOMAIN: {"hub_link": "via_device_id"}}),
            SimpleNamespace(),
        ):
            assert hub_link(hass) == {"via_device": (const.DOMAIN, const.DOMAIN)}
        assert set(hub_link(MagicMock())) == {"via_device"}

    def test_the_recorded_link_is_handed_out_as_a_copy(self):
        record = {"via_device_id": _HUB}
        hass = SimpleNamespace(data={const.DOMAIN: {"hub_link": record}})
        assert hub_link(hass) == record
        assert hub_link(hass) is not record
```

- [x] **Schritt 2: RED**

Run: `/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_device_registry_compat.py -p _local_socket_unblock -q`
Expected: `1 failed, 8 passed` — `test_a_signature_that_cannot_be_read_leaves_the_identifier_form` scheitert mit
`NameError: an annotation names what is not bound`; die drei anderen neuen Tests pinnen Bestehendes und sind schon grün
(ihre RED liefern die Mutationen M18–M23 in Task 6).

- [x] **Schritt 3: Implementierung**

**Ersetze in `custom_components/irrigation_plus/entity.py`:**
```python
    Home Assistant 2026.8 added ``via_device_id`` (the parent's registry id)
    and deprecated ``via_device`` (the parent's identifier), which goes in
    2027.8. Before 2026.8 ``via_device_id`` does not exist: there,
    ``async_get_or_create`` has a fixed keyword-only signature, and the
    ``TypeError`` would stop every zone entity from being added. So ask the
```
**durch:**
```python
    Home Assistant 2026.8 added ``via_device_id`` (the parent's registry id)
    to the device info and deprecated ``via_device`` (the parent's
    identifier), which goes in 2027.8. Before 2026.8 ``async_get_or_create``
    takes no ``via_device_id``: its keyword-only signature is fixed, and the
    ``TypeError`` would stop every zone entity from being added. So ask the
```

**Ersetze in `custom_components/irrigation_plus/entity.py`:**
```python
    except (TypeError, ValueError):
        takes_id = False
```
**durch:**
```python
    except Exception:  # noqa: BLE001 - unreadable means the identifier form
        # Home Assistant has needed Python 3.14 since 2026.3, and since 2026.6
        # its registry module no longer postpones annotations, so reading the
        # signature evaluates them: a name imported only for type checking
        # would raise NameError here and stop the setup.
        takes_id = False
```

**Ersetze in `custom_components/irrigation_plus/entity.py`:**
```python
    set-up entry, the identifier form stands; every Home Assistant up to 2027.8
    takes it.
    """
```
**durch:**
```python
    set-up entry, the identifier form stands; Home Assistant takes it until
    2027.8 (from 2026.9 on with a deprecation warning).
    """
```

- [x] **Schritt 4: GREEN**

Run: wie Task 1, Schritt 4. Expected: `26 passed` (9 aus der neuen Datei, 16 aus `test_distributor_entities.py`,
`test_device_info`).

- [x] **Schritt 5: Lint** — wie Task 1, Schritt 5.

- [x] **Schritt 6: Commit**

```bash
git add custom_components/irrigation_plus/entity.py tests/test_device_registry_compat.py
git commit -F - <<'EOF'
fix(devices): an unreadable registry signature leaves the identifier form

Since 2026.6 Home Assistant's registry module no longer postpones its
annotations, so on Python 3.14, which Home Assistant has needed since 2026.3,
inspect.signature evaluates them: a name the module imports only for type
checking would make hub_link_for raise NameError, and setup would fail on the
detection. Any failure to read the signature now leaves the identifier form.
The tests also pin 2026.8.0's own shape (both keys named, no **kwargs), that
anything but a recorded link leaves the identifier form, and that the link is
handed out as a copy; the docstrings now say what 2026.8 and 2026.9 changed.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 2: Ein Gerät wird je Config-Eintrag gesucht, wo HA das anbietet

**Files:** Modify `custom_components/irrigation_plus/entity.py`; Test `tests/test_device_registry_compat.py`.

- [x] **Schritt 1: Tests**

**Ersetze in `tests/test_device_registry_compat.py`:**
```python
from custom_components.irrigation_plus.entity import (
    distributor_device_info,
    hub_link,
```
**durch:**
```python
from custom_components.irrigation_plus.entity import (
    distributor_device_info,
    find_device,
    hub_link,
```

**Hänge an `tests/test_device_registry_compat.py` an:**
```python


class TestADeviceIsFoundPerConfigEntryWhereOffered:
    """``find_device`` uses the per-entry lookup where the registry has it."""

    def test_the_per_entry_lookup_is_asked_with_the_entry(self):
        device = SimpleNamespace(id="dev")
        registry = _RegistryFrom2026_8(device)
        assert find_device(registry, _ZONE, "entry-1") is device
        assert registry.calls == [("by_identifier", _ZONE, "entry-1")]

    def test_a_registry_before_it_is_asked_the_old_way(self):
        device = SimpleNamespace(id="dev")
        registry = _RegistryBefore2026_8(device)
        assert find_device(registry, _ZONE, "entry-1") is device
        assert registry.calls == [("get_device", {_ZONE})]

    def test_a_test_double_is_asked_the_old_way(self):
        registry = Mock()
        registry.async_get_device.return_value = "dev"
        assert find_device(registry, _ZONE, "entry-1") == "dev"
        registry.async_get_device.assert_called_once_with(identifiers={_ZONE})
        registry.async_get_device_by_identifier.assert_not_called()
```

- [x] **Schritt 2: RED**

Run: `/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_device_registry_compat.py -p _local_socket_unblock -q`
Expected: `ImportError: cannot import name 'find_device' from 'custom_components.irrigation_plus.entity'`, `1 error`.

- [x] **Schritt 3: Implementierung**

**Hänge an `custom_components/irrigation_plus/entity.py` an:**
```python


def find_device(registry, identifier: tuple[str, str], config_entry_id: str | None):
    """The device registered under ``identifier``, or ``None``.

    Home Assistant 2026.9 deprecated ``async_get_device``, which goes in 2027.8,
    because identifiers are no longer unique across config entries; its
    replacement ``async_get_device_by_identifier`` exists from 2026.8 and looks
    up per config entry. Use it where the registry's class has it; the question
    goes to the class because a test double answers for any attribute on its
    instance. Once the declared floor is 2026.8 or later, call it outright.
    """
    if callable(getattr(type(registry), "async_get_device_by_identifier", None)):
        return registry.async_get_device_by_identifier(identifier, config_entry_id)
    return registry.async_get_device(identifiers={identifier})
```

- [x] **Schritt 4: GREEN**

Run: wie Schritt 2. Expected: `12 passed` (1b: vorher `8 passed`).

- [x] **Schritt 5: Lint** — wie Task 1, Schritt 5.

- [x] **Schritt 6: Commit**

```bash
git add custom_components/irrigation_plus/entity.py tests/test_device_registry_compat.py
git commit -F - <<'EOF'
fix(devices): look a device up per config entry where Home Assistant offers it

Home Assistant 2026.9 deprecated device_registry.async_get_device, which goes in
2027.8, because identifiers are no longer unique across config entries; its
replacement async_get_device_by_identifier exists from 2026.8. find_device uses
it where the registry's class has it and keeps the old lookup below 2026.8.
The two delete paths move onto it next.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 2b: Nachtrag aus dem Quality-Review von Task 2

**Herkunft:** Quality-Review von Task 2 (2026-10-06), vom Controller gegen die HA-Quellen nachgeprüft. Nicht Teil der
Freigabe; eigener Commit wie 1b.

- **Der Fehlschlag war ungepinnt.** Alle drei Tests finden ein Gerät. Ein naheliegender „defensiver“ Nachsatz („nichts
  gefunden → alter Weg“) bliebe grün und riefe auf 2026.9+ bei jedem Fehlschlag wieder das gemeldete
  `async_get_device` (ab 2027.8 ein `AttributeError`); der Live-Test löscht nur Zonen mit Gerät und sähe es nicht. Ein
  Test pinnt jetzt: ein Fehlschlag ergibt `None`, mit Entry-ID und mit `None`, und gefragt wird nur der neue Lookup.
- **`None` als Entry-ID:** Ab 2026.8 findet der neue Lookup damit nichts (`get_entry`: ein ausdrückliches `None` ist
  nicht `UNDEFINED`, und `None in by_config_entry` ist falsch; 2026.9.4 `device_registry.py:1314-1341`, Kernprüfung
  `:1329-1332`; 2026.8.0 `:1147-1174`, `:1162-1165`); der alte Lookup fragte nie danach. Im Betrieb ist die ID immer
  gesetzt (`__init__.py:569`); der Docstring sagt es jetzt.
- **Klassenfrage:** Ein `Mock` nimmt auch mit `spec` den alten Weg; der Docstring sagt es jetzt.
- **Re-Review (Ja, zwei Wortlaut-Hinweise übernommen, per Amend):** „so there“ legte eine logische Folge nahe — es
  entscheidet die `UNDEFINED`-Unterscheidung in `get_entry`, nicht das Nachschlagen je Eintrag (HAs Geschwister
  `get_entries`/`async_get_devices` lesen `None` als „alle“); jetzt „and there“. Die `spec`-Klammer hing an „answers for
  any attribute“, was ein Mock mit `spec` gerade nicht tut; jetzt als Folge der Klassenfrage („so a ``Mock`` …“).
- **Nicht übernommen:** den Fehlschlag auf der alten Registry eigens pinnen (reines Durchreichen von
  `async_get_device`); ein Fehlschlag-Test gegen die installierte Registry (lokal und in der CI HA unter 2026.8, er
  träfe nur den alten Weg).

**Files:** Modify `custom_components/irrigation_plus/entity.py`; Test `tests/test_device_registry_compat.py`.

- [x] **Schritt 1: Test**

**Ersetze in `tests/test_device_registry_compat.py`:**
```python
        registry.async_get_device.assert_called_once_with(identifiers={_ZONE})
        registry.async_get_device_by_identifier.assert_not_called()
```
**durch:**
```python
        registry.async_get_device.assert_called_once_with(identifiers={_ZONE})
        registry.async_get_device_by_identifier.assert_not_called()

    def test_a_miss_is_none_and_never_asked_the_old_way(self):
        registry = _RegistryFrom2026_8(None)
        assert find_device(registry, _ZONE, "entry-1") is None
        assert find_device(registry, _ZONE, None) is None
        assert registry.calls == [
            ("by_identifier", _ZONE, "entry-1"),
            ("by_identifier", _ZONE, None),
        ]
```

- [x] **Schritt 2: Pin statt RED** — der Test hält bestehendes Verhalten fest und ist sofort grün:
  `/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_device_registry_compat.py -p _local_socket_unblock -q`
  → `13 passed`. Seine RED liefern die Mutationen M24–M26 in Task 6.

- [x] **Schritt 3: Docstring**

**Ersetze in `custom_components/irrigation_plus/entity.py`:**
```python
    replacement ``async_get_device_by_identifier`` exists from 2026.8 and looks
    up per config entry. Use it where the registry's class has it; the question
    goes to the class because a test double answers for any attribute on its
    instance. Once the declared floor is 2026.8 or later, call it outright.
    """
```
**durch:**
```python
    replacement ``async_get_device_by_identifier`` exists from 2026.8 and looks
    up per config entry, and there an entry id of ``None`` finds nothing. Use it
    where the registry's class has it; the question goes to the class because a
    test double answers for any attribute on its instance, so a ``Mock``, even
    one with a ``spec``, takes the old way. Once the declared floor is 2026.8 or
    later, call it outright.
    """
```

- [x] **Schritt 4: GREEN** — wie Schritt 2: `13 passed`.

- [x] **Schritt 5: Lint** — wie Task 1, Schritt 5.

- [x] **Schritt 6: Commit**

```bash
git add custom_components/irrigation_plus/entity.py tests/test_device_registry_compat.py
git commit -F - <<'EOF'
test(devices): a miss never falls back to the deprecated lookup

On a registry with the per-entry lookup, find_device must not reach for
async_get_device even when nothing is found: from 2026.9 that call is reported,
and in 2027.8 it is gone. The new test pins a miss, with an entry id and with
None. The docstring now says that the per-entry lookup finds nothing for an
entry id of None, and that a Mock, even one with a spec, takes the old way.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 3: Das Setup legt den Verweis auf den Hub ab

**Files:** Modify `custom_components/irrigation_plus/__init__.py` (Import, `async_setup_entry`); Test
`tests/test_device_registry_compat.py`.

- [x] **Schritt 1: Tests**

**Hänge an `tests/test_device_registry_compat.py` an:**
```python


async def _set_up(hass: HomeAssistant, entry) -> bool:
    """Run async_setup_entry with store, session, panel and platforms stubbed.

    The stubbed session also keeps the run off aiodns, which needs a selector
    event loop on Windows; nothing here talks to the network.
    """
    entry.add_to_hass(hass)
    store = AsyncMock()
    store.async_get_config.return_value = {
        const.CONF_USE_WEATHER_SERVICE: False,
        const.CONF_WEATHER_SERVICE: None,
    }
    store.get_config = Mock(
        return_value={
            const.CONF_AUTO_UPDATE_ENABLED: False,
            const.CONF_AUTO_CALC_ENABLED: False,
            const.CONF_USE_WEATHER_SERVICE: False,
        }
    )
    with (
        patch(
            "custom_components.irrigation_plus.async_get_registry",
            return_value=store,
        ),
        patch("custom_components.irrigation_plus.async_get_clientsession"),
        patch("custom_components.irrigation_plus.async_register_panel"),
        patch("custom_components.irrigation_plus.async_register_websockets"),
        patch("custom_components.irrigation_plus.async_register_services"),
        patch.object(
            hass.config_entries, "async_forward_entry_setups", new=AsyncMock()
        ),
    ):
        return await async_setup_entry(hass, entry)


class TestSetupRecordsTheLink:
    """``async_setup_entry`` records the link once the hub is registered."""

    async def test_on_a_2026_8_registry_it_is_the_registered_hubs_id(
        self, hass: HomeAssistant, mock_config_entry, monkeypatch
    ) -> None:
        registry = _RegistryFrom2026_8()
        monkeypatch.setattr(
            "custom_components.irrigation_plus.dr.async_get", lambda hass: registry
        )
        assert await _set_up(hass, mock_config_entry) is True
        assert hass.data[const.DOMAIN]["hub_link"] == {"via_device_id": _HUB}

    async def test_on_the_installed_registry_a_zone_device_hangs_off_the_hub(
        self, hass: HomeAssistant, mock_config_entry
    ) -> None:
        assert await _set_up(hass, mock_config_entry) is True
        registry = dr.async_get(hass)
        coordinator = hass.data[const.DOMAIN]["coordinator"]
        hub = find_device(
            registry, (const.DOMAIN, coordinator.id), mock_config_entry.entry_id
        )
        assert hass.data[const.DOMAIN]["hub_link"] == hub_link_for(
            registry, hub.id, coordinator.id
        )
        zone = registry.async_get_or_create(
            config_entry_id=mock_config_entry.entry_id,
            **zone_device_info(hass, 1, "Lawn"),
        )
        assert zone.via_device_id == hub.id
```

- [x] **Schritt 2: RED**

Run: `/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_device_registry_compat.py -p _local_socket_unblock -q`
Expected: `2 failed, 13 passed, 2 errors` (1b/2b: vorher `8 passed`) — die zwei neuen Tests scheitern in der Testphase mit
`KeyError: 'hub_link'`; die zwei ERRORs sind ihre lokalen teardown-ERRORs (siehe Arbeitsumgebung).

- [x] **Schritt 3: Implementierung**

**Ersetze in `custom_components/irrigation_plus/__init__.py`:**
```python
from .distributor import DistributorMixin
```
**durch:**
```python
from .distributor import DistributorMixin
from .entity import hub_link_for
```

**Ersetze in `custom_components/irrigation_plus/__init__.py`:**
```python
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(const.DOMAIN, coordinator.id)},
        name=const.NAME,
        model=const.NAME,
        sw_version=const.VERSION,
        manufacturer=const.MANUFACTURER,
    )
```
**durch:**
```python
    device_registry = dr.async_get(hass)
    hub = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(const.DOMAIN, coordinator.id)},
        name=const.NAME,
        model=const.NAME,
        sw_version=const.VERSION,
        manufacturer=const.MANUFACTURER,
    )
    # How the zone and distributor devices name the hub as their parent:
    # decided once, from what this Home Assistant's registry takes, before any
    # platform adds an entity (see entity.hub_link_for).
    hass.data[const.DOMAIN]["hub_link"] = hub_link_for(
        device_registry, hub.id, coordinator.id
    )
```

- [x] **Schritt 4: GREEN**

Run: `/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_device_registry_compat.py tests/test_init.py -p _local_socket_unblock -q`
Expected: `2 failed, 30 passed, 1 skipped, 11 errors` (1b/2b: vorher `25 passed`). Die zwei `failed` sind die Baseline-Fehlschläge von
`test_init.py` (aiodns, siehe Arbeitsumgebung); die elf ERRORs sind die neun aus `test_init.py` der Baseline plus die
zwei teardown-ERRORs der neuen Setup-Tests. Die neue Datei allein: `15 passed, 2 errors` (1b/2b: vorher `10 passed`).

- [x] **Schritt 5: Lint** — wie Task 1, Schritt 5 (Datei des Tasks: `__init__.py`).

- [x] **Schritt 6: Commit**

```bash
git add custom_components/irrigation_plus/__init__.py tests/test_device_registry_compat.py
git commit -F - <<'EOF'
fix(devices): setup records how zone and distributor devices name the hub

The hub's registration already returns its device entry; setup now keeps its id
and records hub_link_for's answer in hass.data before any platform adds an
entity. On Home Assistant 2026.8 and later the zone and distributor devices
therefore name the hub by registry id, and the via_device deprecation goes
away; below 2026.8 the identifier form stays as before.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 3b: Nachtrag aus dem Quality-Review von Task 3

**Herkunft:** Quality-Review von Task 3 (2026-10-06), vom Controller am Code nachgeprüft. Nicht Teil der Freigabe;
eigener Commit wie 1b/2b.

- **„Vor jeder Plattform“ war unbelegt.** Beide Setup-Tests lesen `hass.data` erst, wenn `async_setup_entry` fertig
  ist; die Zuweisung hinter das Laden der Plattformen und den anschließenden Replay (`__init__.py:314-324`) zu
  verschieben, bliebe grün. (Zwischen Forward-Ende und Replay liest niemand den Verweis; der Test hält trotzdem „vor
  dem Forward“ fest, wie Kommentar und Spec es sagen.) Dann bauten
  der Replay (`_platform_loaded`, `:324`) und jede später hinzukommende Zone ihr `device_info` mit dem Rückfall
  `via_device` — auf 2026.9+ käme die Warnung zurück. Der neue Test hält im Stand-in für den Forward fest, was dort
  schon abgelegt ist.
- **Überschreiben statt `setdefault`:** `hass.data[DOMAIN]` überlebt einen Reload (`async_unload_entry` fasst den
  Schlüssel nicht an); ein neues Setup muss den Verweis neu schreiben. Derselbe Test legt vorher einen alten Verweis ab.
- **Schreiben und Lesen in einem Test:** derselbe Test liest danach über `zone_device_info` die Id-Form.
- `_set_up` bekommt dafür den Parameter `forward` (Stand-in für das Laden der Plattformen).
- **Nicht übernommen:** `lambda hass:` → `lambda _hass:` im bestehenden Test (verdeckt nur innerhalb des Lambdas);
  die Importe `SmartIrrigationCoordinator`/`_host` (verbrauchen Task 4/5).
- **Vorgemerkt:** Task 7 bekommt einen Reload im Live-Test; Task 8 sagt im PR-Text, dass die CI die Id-Form nur mit
  einem Stand-in prüft.
- **Re-Review (Ja; per Amend übernommen):** der Stand-in hält eine Kopie fest (`dict(...)`; eine Referenz bliebe bei
  einer späteren Änderung in place grün), ein Kommentar erklärt den alten Verweis, der Commit-Text nennt die
  schädliche Lage genau (hinter Plattform-Setup und Replay). Nicht übernommen: Assertions umstellen (nur Diagnose).
- Lokal endet der neue Test wie die zwei anderen Setup-Tests zusätzlich mit dem teardown-ERROR „Lingering timer“.

**Files:** Test `tests/test_device_registry_compat.py`.

- [x] **Schritt 1: Test**

**Ersetze in `tests/test_device_registry_compat.py`:**
```python
async def _set_up(hass: HomeAssistant, entry) -> bool:
    """Run async_setup_entry with store, session, panel and platforms stubbed.
```
**durch:**
```python
async def _set_up(hass: HomeAssistant, entry, forward=None) -> bool:
    """Run async_setup_entry with store, session, panel and platforms stubbed.

    ``forward`` stands in for setting up the platforms, so a test can look at
    what setup has recorded by then.
```

**Ersetze in `tests/test_device_registry_compat.py`:**
```python
        patch.object(
            hass.config_entries, "async_forward_entry_setups", new=AsyncMock()
        ),
```
**durch:**
```python
        patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            new=forward or AsyncMock(),
        ),
```

**Ersetze in `tests/test_device_registry_compat.py`:**
```python
        assert zone.via_device_id == hub.id
```
**durch:**
```python
        assert zone.via_device_id == hub.id

    async def test_the_link_is_recorded_afresh_before_the_platforms_load(
        self, hass: HomeAssistant, mock_config_entry, monkeypatch
    ) -> None:
        registry = _RegistryFrom2026_8()
        monkeypatch.setattr(
            "custom_components.irrigation_plus.dr.async_get", lambda _hass: registry
        )
        # hass.data[DOMAIN] outlives a reload, so an old link can still be there.
        hass.data.setdefault(const.DOMAIN, {})["hub_link"] = {"via_device_id": "old"}
        seen = []

        async def forward(entry, platforms):
            seen.append(dict(hass.data[const.DOMAIN]["hub_link"]))

        assert await _set_up(hass, mock_config_entry, forward) is True
        assert seen == [{"via_device_id": _HUB}]
        info = zone_device_info(hass, 1, "Lawn")
        assert info["via_device_id"] == _HUB
        assert "via_device" not in info
```

- [x] **Schritt 2: Pin statt RED** — der Test hält bestehendes Verhalten fest und ist sofort grün:
  `/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_device_registry_compat.py -p _local_socket_unblock -q`
  → `16 passed, 3 errors` (die drei ERRORs: teardown „Lingering timer“ der drei Setup-Tests). Seine RED liefern die
  Mutationen M27 (Zuweisung hinter den Forward) und M28 (`setdefault`) in Task 6.

- [x] **Schritt 3: Lint** — `uvx black custom_components/irrigation_plus/ tests/test_device_registry_compat.py` ändert
  nichts; `uvx ruff check custom_components/irrigation_plus/` sauber; `git status --short` zeigt nur die Testdatei.

- [x] **Schritt 4: Commit**

```bash
git add tests/test_device_registry_compat.py
git commit -F - <<'EOF'
test(devices): setup records the hub link afresh before the platforms load

Both setup tests read hass.data only after async_setup_entry has returned, so
moving the link behind the platform setup and the zone replay that follows it
would have passed them, and the replayed zones would have named the hub the
deprecated way again. The new test looks at the link from a stand-in for the
platform setup, starts from a stale link as a reload leaves it, and reads the
id form back through zone_device_info.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 4: Eine gelöschte Zone findet ihr Gerät je Config-Eintrag

**Files:** Modify `custom_components/irrigation_plus/__init__.py` (Import, `async_remove_entity`); Test
`tests/test_device_registry_compat.py`.

- [x] **Schritt 1: Test**

**Hänge an `tests/test_device_registry_compat.py` an:**
```python


async def test_a_deleted_zones_device_is_found_per_entry_and_removed(monkeypatch):
    """Deleting a zone looks its device up through ``find_device``."""
    registry = _RegistryFrom2026_8(SimpleNamespace(id="dev"))
    monkeypatch.setattr(
        "custom_components.irrigation_plus.dr.async_get", lambda hass: registry
    )
    monkeypatch.setattr(
        "custom_components.irrigation_plus.er.async_get", lambda hass: Mock()
    )
    c = SmartIrrigationCoordinator.__new__(SmartIrrigationCoordinator)
    c.hass = SimpleNamespace(data={const.DOMAIN: {}})
    c.id = "cid"
    c.entry = SimpleNamespace(entry_id="entry-1")
    await c.async_remove_entity("1")
    assert registry.calls == [
        ("by_identifier", (const.DOMAIN, "cid_zone_1"), "entry-1"),
        ("remove", "dev"),
    ]
```

- [x] **Schritt 2: RED**

Run: `/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_device_registry_compat.py -p _local_socket_unblock -q`
Expected: `1 failed, 16 passed, 3 errors` (1b/2b/3b: vorher `10 passed, 2 errors`) — der neue Test scheitert mit
`At index 0 diff: ('get_device', {('irrigation_plus', 'cid_zone_1')}) != ('by_identifier', …)`.

- [x] **Schritt 3: Implementierung**

**Ersetze in `custom_components/irrigation_plus/__init__.py`:**
```python
from .entity import hub_link_for
```
**durch:**
```python
from .entity import find_device, hub_link_for
```

**Ersetze in `custom_components/irrigation_plus/__init__.py`:**
```python
        device_registry = dr.async_get(self.hass)
        device = device_registry.async_get_device(
            identifiers={(const.DOMAIN, f"{self.id}_zone_{zone_id}")}
        )
```
**durch:**
```python
        device_registry = dr.async_get(self.hass)
        device = find_device(
            device_registry,
            (const.DOMAIN, f"{self.id}_zone_{zone_id}"),
            getattr(getattr(self, "entry", None), "entry_id", None),
        )
```

- [x] **Schritt 4: GREEN**

Run: wie Schritt 2. Expected: `17 passed, 3 errors` (1b/2b/3b: vorher `11 passed, 2 errors`).

- [x] **Schritt 5: Lint** — wie Task 1, Schritt 5 (Datei des Tasks: `__init__.py`).

- [x] **Schritt 6: Commit**

```bash
git add custom_components/irrigation_plus/__init__.py tests/test_device_registry_compat.py
git commit -F - <<'EOF'
fix(zones): find a deleted zone's device per config entry

async_remove_entity looked the zone's device up with async_get_device, which
Home Assistant 2026.9 deprecated and removes in 2027.8. It now goes through
find_device with the coordinator's config entry, so 2026.8 and later use
async_get_device_by_identifier and earlier versions keep the old lookup.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 4b: Nachtrag aus dem Quality-Review von Task 4

**Herkunft:** Quality-Review von Task 4 (2026-10-06), vom Controller am Code nachgeprüft. Nicht Teil der Freigabe;
eigener Commit wie 1b–3b.

- **Am Aufrufort ungepinnt:** Der Test aus Task 4 hat nur den Treffer auf einer Registry neuer Bauart. Grün blieben ein
  „vereinfachter“ Direktaufruf von `async_get_device_by_identifier` (auf HA 2025.5–2026.7 ein `AttributeError` — die
  Zone ist dann schon aus dem Store gelöscht, `__init__.py:2073`, und die CI fährt den Löschpfad nie gegen eine echte
  Registry), ein „defensiver“ Rückfall auf `async_get_device` nach einem Fehlschlag (auf 2026.9+ die Warnung, ab 2027.8
  ein `AttributeError`), der Wegfall von `if device:` und ein striktes `self.entry.entry_id`. Zwei Tests pinnen das:
  Fehlschlag auf der neuen Bauart (nichts entfernt, kein alter Aufruf) und Löschen auf der alten Bauart ohne `entry`.
  Der Test aus Task 4 nutzt jetzt denselben Helfer; seine Aussage bleibt gleich, sein Docstring sagt nur noch, was er
  belegt.
- **Kommentar:** warum die Entry-ID tolerant gelesen wird (im Betrieb immer gesetzt, `__init__.py:576`; ein ohne
  `__init__` gebauter Coordinator hat keine; der alte Lookup braucht sie nicht).
- **Vorgemerkt für Task 5:** Der Kommentar über dem Verteiler-Löschzweig verweist auf ein `async_remove_zone` (gibt es
  nicht; gemeint ist `async_remove_entity`).

**Files:** Modify `custom_components/irrigation_plus/__init__.py` (Kommentar); Test `tests/test_device_registry_compat.py`.

- [x] **Schritt 1: Tests**

**Ersetze in `tests/test_device_registry_compat.py`:**
```python
async def test_a_deleted_zones_device_is_found_per_entry_and_removed(monkeypatch):
    """Deleting a zone looks its device up through ``find_device``."""
    registry = _RegistryFrom2026_8(SimpleNamespace(id="dev"))
    monkeypatch.setattr(
        "custom_components.irrigation_plus.dr.async_get", lambda hass: registry
    )
    monkeypatch.setattr(
        "custom_components.irrigation_plus.er.async_get", lambda hass: Mock()
    )
    c = SmartIrrigationCoordinator.__new__(SmartIrrigationCoordinator)
    c.hass = SimpleNamespace(data={const.DOMAIN: {}})
    c.id = "cid"
    c.entry = SimpleNamespace(entry_id="entry-1")
    await c.async_remove_entity("1")
    assert registry.calls == [
        ("by_identifier", (const.DOMAIN, "cid_zone_1"), "entry-1"),
        ("remove", "dev"),
    ]
```
**durch:**
```python
async def _delete_zone_1(monkeypatch, registry, **attrs):
    """Delete zone 1 on a coordinator built without ``__init__``.

    Only the device half of ``async_remove_entity`` does anything here: no
    entities are tracked, so the entity registry stand-in removes none.
    """
    monkeypatch.setattr(
        "custom_components.irrigation_plus.dr.async_get", lambda hass: registry
    )
    monkeypatch.setattr(
        "custom_components.irrigation_plus.er.async_get", lambda hass: Mock()
    )
    c = SmartIrrigationCoordinator.__new__(SmartIrrigationCoordinator)
    c.hass = SimpleNamespace(data={const.DOMAIN: {}})
    c.id = "cid"
    for name, value in attrs.items():
        setattr(c, name, value)
    await c.async_remove_entity("1")


async def test_a_deleted_zones_device_is_found_per_entry_and_removed(monkeypatch):
    """Deleting a zone finds its device per config entry and removes it."""
    registry = _RegistryFrom2026_8(SimpleNamespace(id="dev"))
    await _delete_zone_1(
        monkeypatch, registry, entry=SimpleNamespace(entry_id="entry-1")
    )
    assert registry.calls == [
        ("by_identifier", (const.DOMAIN, "cid_zone_1"), "entry-1"),
        ("remove", "dev"),
    ]


async def test_a_zone_without_a_device_removes_nothing(monkeypatch):
    """A miss removes nothing and is not asked again the old way."""
    registry = _RegistryFrom2026_8(None)
    await _delete_zone_1(
        monkeypatch, registry, entry=SimpleNamespace(entry_id="entry-1")
    )
    assert registry.calls == [
        ("by_identifier", (const.DOMAIN, "cid_zone_1"), "entry-1"),
    ]


async def test_before_2026_8_a_zone_is_deleted_without_an_entry(monkeypatch):
    """The old lookup needs no entry, so a coordinator without one deletes."""
    registry = _RegistryBefore2026_8(SimpleNamespace(id="dev"))
    await _delete_zone_1(monkeypatch, registry)
    assert registry.calls == [
        ("get_device", {(const.DOMAIN, "cid_zone_1")}),
        ("remove", "dev"),
    ]
```

- [x] **Schritt 2: Pin statt RED** — die Tests halten bestehendes Verhalten fest und sind sofort grün:
  `/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_device_registry_compat.py -p _local_socket_unblock -q`
  → `19 passed, 3 errors` (die drei teardown-ERRORs der Setup-Tests). Ihre RED liefern die Mutationen M29–M32 in
  Task 6.

- [x] **Schritt 3: Kommentar**

**Ersetze in `custom_components/irrigation_plus/__init__.py`:**
```python
        # Drop the zone's device as well (it would linger empty otherwise).
        device_registry = dr.async_get(self.hass)
```
**durch:**
```python
        # Drop the zone's device as well (it would linger empty otherwise).
        # The entry id is read tolerantly: the lookup before 2026.8 does not
        # need it, and a coordinator built without __init__ has none. A running
        # integration always has one (see entity.find_device).
        device_registry = dr.async_get(self.hass)
```

- [x] **Schritt 4: GREEN** — wie Schritt 2: `19 passed, 3 errors`.

- [x] **Schritt 5: Lint** — wie Task 1, Schritt 5 (Dateien des Tasks: `__init__.py`, Testdatei).

- [x] **Schritt 6: Commit**

```bash
git add custom_components/irrigation_plus/__init__.py tests/test_device_registry_compat.py
git commit -F - <<'EOF'
test(zones): a deleted zone's device lookup holds on both registry shapes

The test of the zone delete path only had a hit on a 2026.8 registry. A direct
call of async_get_device_by_identifier there, which earlier registries lack, or
a fallback to async_get_device after a miss, which 2026.9 reports, would have
passed it. Two more tests pin a miss and a delete on a registry from before
2026.8 by a coordinator without an entry; a comment says why the entry id is
read tolerantly.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 5: Ein gelöschter Verteiler findet sein Gerät je Config-Eintrag

**Files:** Modify `custom_components/irrigation_plus/distributor.py` (Import, Löschzweig von
`async_upsert_distributor`); Test `tests/test_device_registry_compat.py`.

- [x] **Schritt 1: Test**

**Hänge an `tests/test_device_registry_compat.py` an:**
```python


async def test_a_deleted_distributors_device_is_found_per_entry_and_removed(
    monkeypatch,
):
    """Deleting a distributor looks its device up through ``find_device``."""
    registry = _RegistryFrom2026_8(SimpleNamespace(id="dev123"))
    monkeypatch.setattr(
        "custom_components.irrigation_plus.distributor.dr.async_get",
        lambda hass: registry,
    )
    monkeypatch.setattr(
        "custom_components.irrigation_plus.distributor.async_dispatcher_send",
        lambda *a, **k: None,
    )
    c = _host()
    c.id = "cid"
    c.entry = SimpleNamespace(entry_id="entry-1")
    c.store.get_distributor = Mock(return_value={"id": 3})
    c.store.async_delete_distributor = AsyncMock(return_value=True)
    await c.async_upsert_distributor({"id": 3, "remove": True})
    assert registry.calls == [
        ("by_identifier", (const.DOMAIN, "cid_distributor_3"), "entry-1"),
        ("remove", "dev123"),
    ]
```

- [x] **Schritt 2: RED**

Run: `/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_device_registry_compat.py -p _local_socket_unblock -q`
Expected: `1 failed, 19 passed, 3 errors` (1b–4b: vorher `11 passed, 2 errors`) — der neue Test scheitert mit
`At index 0 diff: ('get_device', {('irrigation_plus', 'cid_distributor_3')}) != ('by_identifier', …)`.

- [x] **Schritt 3: Implementierung**

**Ersetze in `custom_components/irrigation_plus/distributor.py`:**
```python
from .duration_math import hardware_window
```
**durch:**
```python
from .duration_math import hardware_window
from .entity import find_device
```

**Ersetze in `custom_components/irrigation_plus/distributor.py`:**
```python
                registry = dr.async_get(self.hass)
                device = registry.async_get_device(
                    identifiers={(const.DOMAIN, f"{self.id}_distributor_{int(did)}")}
                )
```
**durch:**
```python
                registry = dr.async_get(self.hass)
                device = find_device(
                    registry,
                    (const.DOMAIN, f"{self.id}_distributor_{int(did)}"),
                    getattr(getattr(self, "entry", None), "entry_id", None),
                )
```

- [x] **Schritt 4: GREEN**

Run: `/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_device_registry_compat.py tests/test_distributor_entities.py tests/test_distributor_integration.py -p _local_socket_unblock -q`
Expected: `56 passed, 3 errors` (20 neue, 16 aus `test_distributor_entities.py`, 20 aus
`test_distributor_integration.py`; die drei ERRORs sind die teardown-ERRORs der Setup-Tests). Die Lösch-Tests der
Verteiler-Dateien mit `Mock()`-Registry laufen unverändert weiter über `async_get_device`.

- [x] **Schritt 5: Lint** — wie Task 1, Schritt 5 (Datei des Tasks: `distributor.py`).

- [x] **Schritt 6: Commit**

```bash
git add custom_components/irrigation_plus/distributor.py tests/test_device_registry_compat.py
git commit -F - <<'EOF'
fix(distributors): find a deleted distributor's device per config entry

Deleting a distributor looked its device up with async_get_device, which Home
Assistant 2026.9 deprecated and removes in 2027.8. It now goes through
find_device with the coordinator's config entry; the entry is read tolerantly,
since the old lookup below 2026.8 does not need it.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 5b: Nachtrag aus dem Quality-Review von Task 5

**Herkunft:** Quality-Review von Task 5 (2026-10-06), vom Controller am Code nachgeprüft; Schwester-Pfad zu 4b. Nicht Teil
der Freigabe; eigener Commit wie 1b–4b.

- **Spiegel-Pins zu 4b fehlten:** Der Rückfall auf `async_get_device` nach einem Fehlschlag blieb grün (der neue Test
  trifft, die Miss-Tests mit `Mock()`-Registry zählen keine Aufrufe); ein Direktaufruf des neuen Lookups fiel nur
  zufällig über `assert_called_once` eines Mock-Tests auf, den das Mutationswerkzeug nicht fährt. Zwei Tests pinnen
  Fehlschlag (danach läuft das Löschen weiter: der Einlass-Watch wird abgemeldet, `True` kommt zurück) und Löschen auf
  der alten Bauart ohne `entry`. Der Task-5-Test nutzt jetzt denselben Helfer und prüft das Abmelden ebenfalls.
- **Falscher Verweis:** Der Kommentar über dem Löschzweig nennt `__init__.py async_remove_zone, ~L1415` — die Funktion
  gab es nie (`git grep` trifft nur diese Zeile); gemeint ist `async_remove_entity`. Nur diese Zeile ändert sich, der
  übrige (schon upstream stehende) Kommentar bleibt.
- **Gleicher Kommentar an beiden Löschpfaden:** warum die Entry-ID tolerant gelesen wird, und warum das sicher ist (ab
  2026.8 findet `None` nichts, ein laufendes Setup hat sie immer). Der Zonen-Kommentar aus 4b bekommt denselben Wortlaut
  (auch der Hinweis aus dem 4b-Re-Review).
- **Re-Review (Ja; per Amend übernommen):** Satzbau des Kommentars an beiden Pfaden (der Teil nach dem Doppelpunkt ist
  der Grund, warum die Zusicherung zählt, nicht der Grund für „sicher“); beide Helfer prüfen die Prämisse „kein
  `entry`“ (bekäme `_host()` oder der Coordinator eines, blieben die Alt-Bauart-Tests sonst still grün). Nicht
  übernommen: den „siehe“-Verweis im bestehenden Upstream-Kommentar ergänzen.
- **Rückbau (für Spec und PR-Text):** Mit Untergrenze ≥ 2026.8 werden beide toleranten Lesestellen strikt, und die drei
  Mock-Tests, die `async_get_device` namentlich binden (`test_distributor_entities.py`, `test_distributor_integration.py`),
  ziehen mit um.

**Files:** Modify `custom_components/irrigation_plus/distributor.py`, `custom_components/irrigation_plus/__init__.py`
(Kommentare); Test `tests/test_device_registry_compat.py`.

- [x] **Schritt 1: Tests**

**Ersetze in `tests/test_device_registry_compat.py`:**
```python
async def test_a_deleted_distributors_device_is_found_per_entry_and_removed(
    monkeypatch,
):
    """Deleting a distributor looks its device up through ``find_device``."""
    registry = _RegistryFrom2026_8(SimpleNamespace(id="dev123"))
    monkeypatch.setattr(
        "custom_components.irrigation_plus.distributor.dr.async_get",
        lambda hass: registry,
    )
    monkeypatch.setattr(
        "custom_components.irrigation_plus.distributor.async_dispatcher_send",
        lambda *a, **k: None,
    )
    c = _host()
    c.id = "cid"
    c.entry = SimpleNamespace(entry_id="entry-1")
    c.store.get_distributor = Mock(return_value={"id": 3})
    c.store.async_delete_distributor = AsyncMock(return_value=True)
    await c.async_upsert_distributor({"id": 3, "remove": True})
    assert registry.calls == [
        ("by_identifier", (const.DOMAIN, "cid_distributor_3"), "entry-1"),
        ("remove", "dev123"),
    ]
```
**durch:**
```python
async def _delete_distributor_3(monkeypatch, registry, **attrs):
    """Delete distributor 3 on a host built without the coordinator's ``__init__``.

    The dispatcher is silenced; the registry and the inlet watch take part.
    """
    monkeypatch.setattr(
        "custom_components.irrigation_plus.distributor.dr.async_get",
        lambda hass: registry,
    )
    monkeypatch.setattr(
        "custom_components.irrigation_plus.distributor.async_dispatcher_send",
        lambda *a, **k: None,
    )
    c = _host()
    c.id = "cid"
    for name, value in attrs.items():
        setattr(c, name, value)
    # A test that passes no entry relies on the host having none.
    assert "entry" in attrs or not hasattr(c, "entry")
    c.store.get_distributor = Mock(return_value={"id": 3})
    c.store.async_delete_distributor = AsyncMock(return_value=True)
    return await c.async_upsert_distributor({"id": 3, "remove": True})


async def test_a_deleted_distributors_device_is_found_per_entry_and_removed(
    monkeypatch,
):
    """Deleting a distributor finds its device per config entry and removes it."""
    registry = _RegistryFrom2026_8(SimpleNamespace(id="dev123"))
    unsubscribe = Mock()
    await _delete_distributor_3(
        monkeypatch,
        registry,
        entry=SimpleNamespace(entry_id="entry-1"),
        _dist_inlet_watchers={3: unsubscribe},
    )
    assert registry.calls == [
        ("by_identifier", (const.DOMAIN, "cid_distributor_3"), "entry-1"),
        ("remove", "dev123"),
    ]
    unsubscribe.assert_called_once_with()


async def test_a_distributor_without_a_device_removes_nothing(monkeypatch):
    """A miss removes nothing, is not asked the old way, and the delete goes on."""
    registry = _RegistryFrom2026_8(None)
    unsubscribe = Mock()
    result = await _delete_distributor_3(
        monkeypatch,
        registry,
        entry=SimpleNamespace(entry_id="entry-1"),
        _dist_inlet_watchers={3: unsubscribe},
    )
    assert registry.calls == [
        ("by_identifier", (const.DOMAIN, "cid_distributor_3"), "entry-1"),
    ]
    unsubscribe.assert_called_once_with()
    assert result is True


async def test_before_2026_8_a_distributor_is_deleted_without_an_entry(monkeypatch):
    """The old lookup needs no entry, so a host without one deletes."""
    registry = _RegistryBefore2026_8(SimpleNamespace(id="dev"))
    await _delete_distributor_3(monkeypatch, registry)
    assert registry.calls == [
        ("get_device", {(const.DOMAIN, "cid_distributor_3")}),
        ("remove", "dev"),
    ]
```

**Ersetze in `tests/test_device_registry_compat.py`:**
```python
    c.id = "cid"
    for name, value in attrs.items():
        setattr(c, name, value)
    await c.async_remove_entity("1")
```
**durch:**
```python
    c.id = "cid"
    for name, value in attrs.items():
        setattr(c, name, value)
    # A test that passes no entry relies on the coordinator having none.
    assert "entry" in attrs or not hasattr(c, "entry")
    await c.async_remove_entity("1")
```

- [x] **Schritt 2: Pin statt RED** — die Tests halten bestehendes Verhalten fest und sind sofort grün:
  `/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_device_registry_compat.py -p _local_socket_unblock -q`
  → `22 passed, 3 errors` (die drei teardown-ERRORs der Setup-Tests). Ihre RED liefern die Mutationen M33–M36 in Task 6.

- [x] **Schritt 3: Kommentare**

**Ersetze in `custom_components/irrigation_plus/distributor.py`:**
```python
                # cleanup (__init__.py async_remove_zone, ~L1415): look the device
```
**durch:**
```python
                # cleanup (async_remove_entity in __init__.py): look the device
```

**Ersetze in `custom_components/irrigation_plus/distributor.py`:**
```python
                # test_upsert_delete_removes_device.
                registry = dr.async_get(self.hass)
```
**durch:**
```python
                # test_upsert_delete_removes_device.
                # The entry id is read tolerantly: the lookup before 2026.8 does
                # not need it, and a coordinator built without __init__ has none.
                # That is safe only because a running integration always has
                # one; without it, the lookup from 2026.8 would find nothing and
                # the device would linger (see entity.find_device).
                registry = dr.async_get(self.hass)
```

**Ersetze in `custom_components/irrigation_plus/__init__.py`:**
```python
        # The entry id is read tolerantly: the lookup before 2026.8 does not
        # need it, and a coordinator built without __init__ has none. A running
        # integration always has one (see entity.find_device).
```
**durch:**
```python
        # The entry id is read tolerantly: the lookup before 2026.8 does not
        # need it, and a coordinator built without __init__ has none. That is
        # safe only because a running integration always has one; without it,
        # the lookup from 2026.8 would find nothing and the device would linger
        # (see entity.find_device).
```

- [x] **Schritt 4: GREEN** — `/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_device_registry_compat.py tests/test_distributor_entities.py tests/test_distributor_integration.py -p _local_socket_unblock -q`
  → `58 passed, 3 errors` (22 aus der neuen Datei, 16, 20).

- [x] **Schritt 5: Lint** — wie Task 1, Schritt 5 (Dateien des Tasks: `distributor.py`, `__init__.py`, Testdatei).

- [x] **Schritt 6: Commit**

```bash
git add custom_components/irrigation_plus/distributor.py custom_components/irrigation_plus/__init__.py tests/test_device_registry_compat.py
git commit -F - <<'EOF'
test(distributors): a deleted distributor's device lookup holds on both shapes

As on the zone side, the distributor delete path was only tested with a hit on
a 2026.8 registry: a fallback to async_get_device after a miss would have
passed, and a direct call of async_get_device_by_identifier was caught only by
chance, by a Mock-based test. Two more tests pin a miss, after which the delete
still drops the inlet watch, and a delete on a registry from before 2026.8 by a
host without an entry; both delete helpers assert that premise. The comment
above the branch named a function that does not exist; it now points at
async_remove_entity, and both delete paths say why reading the entry id
tolerantly is safe.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 6: Gesamtprüfung

- [ ] **Schritt 1: Volle Suite** — `bash /d/Entwicklung/HASI/issue11-work/run_suite.sh wt final`.
  Expected: `7 failed, 3805 passed, 9 skipped, 418 errors` gegen die Baseline `7 / 3783 / 9 / 415`: +22 passed =
  die zweiundzwanzig neuen Tests (1b–5b: berechnet aus dem Probelauf `3795` + 4 + 1 + 1 + 2 + 2; nach Task 5 in
  `wt` gemessen: `3803`), +3 errors = die teardown-ERRORs der drei Setup-Tests.
  `NAMES DIFFER (422 -> 425)`, unter „added“ **genau** diese drei, unter „gone“ nichts:
  `ERROR tests/test_device_registry_compat.py::TestSetupRecordsTheLink::test_on_a_2026_8_registry_it_is_the_registered_hubs_id`,
  `ERROR tests/test_device_registry_compat.py::TestSetupRecordsTheLink::test_on_the_installed_registry_a_zone_device_hangs_off_the_hub`,
  `ERROR tests/test_device_registry_compat.py::TestSetupRecordsTheLink::test_the_link_is_recorded_afresh_before_the_platforms_load`.
  Jeder andere neue oder fehlende Name ist ein echter Befund: STOP.
- [ ] **Schritt 2: Lint** — `uvx black --check custom_components/irrigation_plus/` und `uvx ruff check
  custom_components/irrigation_plus/` sauber; `uvx black --check tests/test_device_registry_compat.py` sauber.
- [ ] **Schritt 3: Mutationen** — `/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe
  D:/Entwicklung/HASI/issue11-work/mutate.py D:/Entwicklung/HASI/issue11-work/wt
  D:/Entwicklung/HASI/issue11-work/mutate-final.txt`. Expected: alle 36 `KILLED` (1b: M17–M23, 2b: M24–M26, 3b:
  M27/M28, 4b: M29–M32, 5b: M33–M36 neu, im Probelauf `mutate-probe-5b.txt` gemessen), keine `SURVIVED`, `HANG`
  oder `ANCHOR`.
- [ ] **Schritt 4: Keine eigenen Verweise** (Diff und Commit-Messages):

```bash
git diff 7001c754..HEAD -- custom_components/ tests/ docs/ | grep "^+" | grep -nE "Eifel-Joe|JustChr#|spec D[0-9]|spec §|Task [0-9]|M[0-9][a-z]?:|PR [A-T]\b"
git log 7001c754..HEAD --format='%H%n%B' | grep -nE "Eifel-Joe#|JustChr#"
```
Expected: beide ohne Ausgabe.

- [ ] **Schritt 5: Schwester-Pfade** — `git grep -n -E "via_device|async_get_device\(" -- custom_components/irrigation_plus/`:
  Treffer nur noch in `entity.py` (Rückfall in `hub_link_for`, `hub_link`, `find_device` und deren Docstrings).
- [ ] **Schritt 6: Kein Frontend** — `git diff --stat 7001c754..HEAD -- custom_components/irrigation_plus/frontend` leer.

---

### Task 7: Pre-Release und Live-Test auf HA-Test (Ende-zu-Ende-Kriterium der Spec)

Braucht die Freigabe des Users für Push, Release und den Neustart von HA-Test (vorher ankündigen). Ablauf des Rebuilds
nach Memory `hasi-production-on-upstream` und Projekt-`CLAUDE.md` (production = `upstream/master` + Branding + alle
offenen eigenen PRs; Versionen synchron; ZIP aus dem SHA).

- [ ] **Schritt 1: RED auf dem installierten Pre-Release (v2026.10.05b2)**, Ergebnis in
  `D:\Entwicklung\HASI\issue11-work\livetest\L-device-registry.md`:
  - System-Log: `ha_get_logs(source="system", search="via_device")` zeigt die Warnung von `irrigation_plus`.
  - Eltern-Verweise aller Geräte der Integration per `ha_eval_template`:
    ```jinja
    {% for d in integration_entities('irrigation_plus') | map('device_id') | reject('none') | unique %}
    {{ d }} | {{ device_attr(d, 'name') }} | {{ device_attr(d, 'via_device_id') }}
    {% endfor %}
    ```
  - Eine Wegwerf-Zone anlegen und wieder löschen (Panel → Zonen, oder POST `/api/irrigation_plus/zones` über
    `ha_manage_custom_tool`, Löschen mit `remove: true`): das System-Log zeigt die `async_get_device`-Warnung von
    `irrigation_plus`.
- [ ] **Schritt 2: production-Rebuild** mit `fix/seasonal-outlook` (offener PR zum saisonalen Ausblick) und diesem
  Branch obendrauf, Pre-Release mit der Kalender-Version des Bautags, ZIP aus dem SHA, Download geprüft.
- [ ] **Schritt 3: HA-Test** per HACS aktualisieren (`update_information`, dann `download` mit `version`), Neustart
  ankündigen und ausführen.
- [ ] **Schritt 4: GREEN:** keine der beiden Warnungen von `irrigation_plus` im System-Log; jedes Gerät hat denselben
  Eltern-Verweis wie in Schritt 1; eine neue Wegwerf-Zone und ein neuer Wegwerf-Verteiler hängen am Hub (Template),
  nach dem Löschen ist ihr Gerät weg, ohne Warnung. Die Diagnostics zeigen unter `data.hub_link` die Form
  `via_device_id`.
- [ ] **Schritt 5 (aus dem Review von Task 3): Reload.** Die Integration neu laden (Optionen speichern oder
  „Neu laden“), danach noch eine Wegwerf-Zone anlegen und löschen: am Hub, ohne Warnung, `data.hub_link` unverändert
  die Id-Form. Der Reload ist der einzige Weg, auf dem ein alter Verweis in `hass.data` stehen bleibt.

---

### Task 8: PR und Nachlauf

Jeder Schritt nach außen nur mit Freigabe im Chat; vorher die Upstream-Runde wiederholen.

- [ ] **Schritt 1:** PR-Text deutsch, dann englisch zur Freigabe (`## Problem` / `## Fix` / `## Testing`; nennt die
  Versionslage, beide Abkündigungen und bietet die Alternative an: Untergrenze auf 2026.8 oder höher, Weichen weg;
  `## Testing` sagt offen, dass die CI (2026.2.3, 2025.5.0) die Id-Form nur mit Stand-in-Registrys prüft und die
  echte Registry ab 2026.8 erst der Live-Test auf 2026.9.x;
  Footer „🤖 Generated with [Claude Code](https://claude.com/claude-code)“; keine eigenen Issue-Verweise).
- [ ] **Schritt 2:** `git push -u origin fix/device-registry-2027-8`;
  `gh pr create --repo JustChr/HAsmartirrigation --base master --head Eifel-Joe:fix/device-registry-2027-8
  --title "<freigegebener Titel>" --body-file D:/Entwicklung/HASI/issue11-work/texts/pr-en.md`. Titelvorschlag (mit dem
  Text freizugeben): `fix(devices): use the device registry's 2026.8 calls where offered, keep the 2025.5 floor`.
- [ ] **Schritt 3:** P2: Kommentar auf Eifel-Joe#11 (PR-Link, Stand), Label `upstream:gemeldet`; `Eifel-Joe#42`
  Punkt 12.
- [ ] **Schritt 4:** P1: Plan mit Häkchen, Probelauf- und Live-Belege auf `archive/design-history`.
