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

**Stand:** Plan vom User am 2026-10-06 im Chat freigegeben; Umsetzung noch nicht begonnen.

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
| `custom_components/irrigation_plus/entity.py` | `hub_link_for`, `hub_link`, `find_device`; Geräte-Infos nutzen `hub_link` | 1, 2 |
| `custom_components/irrigation_plus/__init__.py` | Setup legt `hub_link` ab; Zone löschen über `find_device` | 3, 4 |
| `custom_components/irrigation_plus/distributor.py` | Verteiler löschen über `find_device` | 5 |
| `tests/test_device_registry_compat.py` | neu | 1–5 |

---

### Task 0: Worktree und Baseline

- [ ] **Schritt 1: Worktree**

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

- [ ] **Schritt 2: Baseline** — nur falls `D:\Entwicklung\HASI\issue11-work\names-base.txt` fehlt oder die Basis nicht
  `7001c754` ist: `bash /d/Entwicklung/HASI/issue11-work/run_suite.sh wt base`.

---

### Task 1: Der Hub-Verweis richtet sich nach der Registry

**Files:** Modify `custom_components/irrigation_plus/entity.py`; Create `tests/test_device_registry_compat.py`.

- [ ] **Schritt 1: Testdatei anlegen**

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

- [ ] **Schritt 2: RED**

Run: `/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_device_registry_compat.py -p _local_socket_unblock -q`
Expected: `ImportError: cannot import name 'hub_link' from 'custom_components.irrigation_plus.entity'`, `1 error`.

- [ ] **Schritt 3: Implementierung**

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

- [ ] **Schritt 4: GREEN**

Run: `/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_device_registry_compat.py tests/test_distributor_entities.py "tests/test_sensor.py::TestSmartIrrigationZoneEntity::test_device_info" -p _local_socket_unblock -q`
Expected: `22 passed` (5 neue, 16 aus `test_distributor_entities.py`, `test_device_info`); die bestehenden Pins
(`test_device_info`, `test_distributor_device_info_identifiers_and_via_device`) bleiben unverändert grün.

- [ ] **Schritt 5: Lint** — `uvx black custom_components/irrigation_plus/ tests/test_device_registry_compat.py` ändert
  nichts (`git status --short` zeigt nur die zwei Dateien des Tasks); `uvx ruff check custom_components/irrigation_plus/`
  sauber.

- [ ] **Schritt 6: Commit**

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

### Task 2: Ein Gerät wird je Config-Eintrag gesucht, wo HA das anbietet

**Files:** Modify `custom_components/irrigation_plus/entity.py`; Test `tests/test_device_registry_compat.py`.

- [ ] **Schritt 1: Tests**

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

- [ ] **Schritt 2: RED**

Run: `/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_device_registry_compat.py -p _local_socket_unblock -q`
Expected: `ImportError: cannot import name 'find_device' from 'custom_components.irrigation_plus.entity'`, `1 error`.

- [ ] **Schritt 3: Implementierung**

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

- [ ] **Schritt 4: GREEN**

Run: wie Schritt 2. Expected: `8 passed`.

- [ ] **Schritt 5: Lint** — wie Task 1, Schritt 5.

- [ ] **Schritt 6: Commit**

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

### Task 3: Das Setup legt den Verweis auf den Hub ab

**Files:** Modify `custom_components/irrigation_plus/__init__.py` (Import, `async_setup_entry`); Test
`tests/test_device_registry_compat.py`.

- [ ] **Schritt 1: Tests**

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

- [ ] **Schritt 2: RED**

Run: `/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_device_registry_compat.py -p _local_socket_unblock -q`
Expected: `2 failed, 8 passed, 2 errors` — die zwei neuen Tests scheitern in der Testphase mit
`KeyError: 'hub_link'`; die zwei ERRORs sind ihre lokalen teardown-ERRORs (siehe Arbeitsumgebung).

- [ ] **Schritt 3: Implementierung**

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

- [ ] **Schritt 4: GREEN**

Run: `/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_device_registry_compat.py tests/test_init.py -p _local_socket_unblock -q`
Expected: `2 failed, 25 passed, 1 skipped, 11 errors`. Die zwei `failed` sind die Baseline-Fehlschläge von
`test_init.py` (aiodns, siehe Arbeitsumgebung); die elf ERRORs sind die neun aus `test_init.py` der Baseline plus die
zwei teardown-ERRORs der neuen Setup-Tests. Die neue Datei allein: `10 passed, 2 errors`.

- [ ] **Schritt 5: Lint** — wie Task 1, Schritt 5 (Datei des Tasks: `__init__.py`).

- [ ] **Schritt 6: Commit**

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

### Task 4: Eine gelöschte Zone findet ihr Gerät je Config-Eintrag

**Files:** Modify `custom_components/irrigation_plus/__init__.py` (Import, `async_remove_entity`); Test
`tests/test_device_registry_compat.py`.

- [ ] **Schritt 1: Test**

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

- [ ] **Schritt 2: RED**

Run: `/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_device_registry_compat.py -p _local_socket_unblock -q`
Expected: `1 failed, 10 passed, 2 errors` — der neue Test scheitert mit
`At index 0 diff: ('get_device', {('irrigation_plus', 'cid_zone_1')}) != ('by_identifier', …)`.

- [ ] **Schritt 3: Implementierung**

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

- [ ] **Schritt 4: GREEN**

Run: wie Schritt 2. Expected: `11 passed, 2 errors`.

- [ ] **Schritt 5: Lint** — wie Task 1, Schritt 5 (Datei des Tasks: `__init__.py`).

- [ ] **Schritt 6: Commit**

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

### Task 5: Ein gelöschter Verteiler findet sein Gerät je Config-Eintrag

**Files:** Modify `custom_components/irrigation_plus/distributor.py` (Import, Löschzweig von
`async_upsert_distributor`); Test `tests/test_device_registry_compat.py`.

- [ ] **Schritt 1: Test**

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

- [ ] **Schritt 2: RED**

Run: `/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_device_registry_compat.py -p _local_socket_unblock -q`
Expected: `1 failed, 11 passed, 2 errors` — der neue Test scheitert mit
`At index 0 diff: ('get_device', {('irrigation_plus', 'cid_distributor_3')}) != ('by_identifier', …)`.

- [ ] **Schritt 3: Implementierung**

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

- [ ] **Schritt 4: GREEN**

Run: `/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_device_registry_compat.py tests/test_distributor_entities.py tests/test_distributor_integration.py -p _local_socket_unblock -q`
Expected: `48 passed, 2 errors` (12 neue, 16 aus `test_distributor_entities.py`, 20 aus
`test_distributor_integration.py`; die zwei ERRORs sind die teardown-ERRORs der Setup-Tests). Die Lösch-Tests der
Verteiler-Dateien mit `Mock()`-Registry laufen unverändert weiter über `async_get_device`.

- [ ] **Schritt 5: Lint** — wie Task 1, Schritt 5 (Datei des Tasks: `distributor.py`).

- [ ] **Schritt 6: Commit**

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

### Task 6: Gesamtprüfung

- [ ] **Schritt 1: Volle Suite** — `bash /d/Entwicklung/HASI/issue11-work/run_suite.sh wt final`.
  Expected (im Probelauf so gemessen): `7 failed, 3795 passed, 9 skipped, 417 errors` gegen die Baseline
  `7 / 3783 / 9 / 415`: +12 passed = die zwölf neuen Tests, +2 errors = die teardown-ERRORs der zwei Setup-Tests.
  `NAMES DIFFER (422 -> 424)`, unter „added“ **genau** diese zwei, unter „gone“ nichts:
  `ERROR tests/test_device_registry_compat.py::TestSetupRecordsTheLink::test_on_a_2026_8_registry_it_is_the_registered_hubs_id`,
  `ERROR tests/test_device_registry_compat.py::TestSetupRecordsTheLink::test_on_the_installed_registry_a_zone_device_hangs_off_the_hub`.
  Jeder andere neue oder fehlende Name ist ein echter Befund: STOP.
- [ ] **Schritt 2: Lint** — `uvx black --check custom_components/irrigation_plus/` und `uvx ruff check
  custom_components/irrigation_plus/` sauber; `uvx black --check tests/test_device_registry_compat.py` sauber.
- [ ] **Schritt 3: Mutationen** — `/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe
  D:/Entwicklung/HASI/issue11-work/mutate.py D:/Entwicklung/HASI/issue11-work/wt
  D:/Entwicklung/HASI/issue11-work/mutate-final.txt`. Expected: alle 16 `KILLED`, keine `SURVIVED`, `HANG` oder
  `ANCHOR`.
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

---

### Task 8: PR und Nachlauf

Jeder Schritt nach außen nur mit Freigabe im Chat; vorher die Upstream-Runde wiederholen.

- [ ] **Schritt 1:** PR-Text deutsch, dann englisch zur Freigabe (`## Problem` / `## Fix` / `## Testing`; nennt die
  Versionslage, beide Abkündigungen und bietet die Alternative an: Untergrenze auf 2026.8 oder höher, Weichen weg;
  Footer „🤖 Generated with [Claude Code](https://claude.com/claude-code)“; keine eigenen Issue-Verweise).
- [ ] **Schritt 2:** `git push -u origin fix/device-registry-2027-8`;
  `gh pr create --repo JustChr/HAsmartirrigation --base master --head Eifel-Joe:fix/device-registry-2027-8
  --title "<freigegebener Titel>" --body-file D:/Entwicklung/HASI/issue11-work/texts/pr-en.md`. Titelvorschlag (mit dem
  Text freizugeben): `fix(devices): use the device registry's 2026.8 calls where offered, keep the 2025.5 floor`.
- [ ] **Schritt 3:** P2: Kommentar auf Eifel-Joe#11 (PR-Link, Stand), Label `upstream:gemeldet`; `Eifel-Joe#42`
  Punkt 12.
- [ ] **Schritt 4:** P1: Plan mit Häkchen, Probelauf- und Live-Belege auf `archive/design-history`.
