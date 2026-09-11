"""Store migrations from the oldest shapes: v3, v4, v6 and v8.

Every step from v9 on has tests of its own; nothing drove these four, so an
install upgrading from a very old release took a path no test had walked.

Two levels. The steps are driven on a dict through ``_async_migrate_func``,
exactly as the neighbouring migration tests do. Then one whole v3 document is
loaded through Home Assistant's real Store: ``hass_storage`` routes its mock
through the original ``_async_load`` so the migration runs as it does at
startup, and the result is hydrated into ``Config`` and ``ZoneEntry`` -- which
is where a key the migration forgot, or a step that raises, would actually
stop an install from loading.
"""

import pytest

from custom_components.irrigation_plus import const
from custom_components.irrigation_plus.store import (
    STORAGE_KEY,
    STORAGE_VERSION,
    MigratableStore,
    SmartIrrigationStorage,
)


def _zone(zone_id, name, **extra):
    """A zone as a v3-era release stored it: the twelve keys load indexes."""
    zone = {
        const.ZONE_ID: zone_id,
        const.ZONE_NAME: name,
        const.ZONE_SIZE: 25.0,
        const.ZONE_THROUGHPUT: 12.0,
        const.ZONE_STATE: "automatic",
        const.ZONE_DELTA: -1.25,
        const.ZONE_BUCKET: -3.5,
        const.ZONE_DURATION: 875,
        const.ZONE_MODULE: 0,
        const.ZONE_MULTIPLIER: 1.0,
        const.ZONE_MAPPING: 0,
        const.ZONE_LEAD_TIME: 0,
    }
    zone.update(extra)
    return zone


async def _migrate(hass, old_version, data):
    store = MigratableStore(hass, STORAGE_VERSION, STORAGE_KEY)
    return await store._async_migrate_func(old_version, data)


class TestV3:
    """v3 renamed ``use_owm`` and, when it was on, named the service."""

    async def test_use_owm_on_becomes_the_owm_weather_service(self, hass):
        out = await _migrate(hass, 3, {"config": {"use_owm": True}})
        assert "use_owm" not in out["config"]
        assert out["config"][const.CONF_USE_WEATHER_SERVICE] is True
        assert out["config"][const.CONF_WEATHER_SERVICE] == (
            const.CONF_WEATHER_SERVICE_OWM
        )

    async def test_use_owm_off_names_no_service(self, hass):
        out = await _migrate(hass, 3, {"config": {"use_owm": False}})
        assert out["config"][const.CONF_USE_WEATHER_SERVICE] is False
        assert const.CONF_WEATHER_SERVICE not in out["config"]


class TestV4:
    """v4 added the precipitation and days-between skip settings."""

    async def test_missing_settings_are_defaulted(self, hass):
        out = await _migrate(hass, 4, {"config": {}})
        cfg = out["config"]
        assert cfg[const.CONF_SKIP_IRRIGATION_ON_PRECIPITATION] == (
            const.CONF_DEFAULT_SKIP_IRRIGATION_ON_PRECIPITATION
        )
        assert cfg[const.CONF_PRECIPITATION_THRESHOLD_MM] == (
            const.CONF_DEFAULT_PRECIPITATION_THRESHOLD_MM
        )
        assert cfg[const.CONF_DAYS_BETWEEN_IRRIGATION] == (
            const.CONF_DEFAULT_DAYS_BETWEEN_IRRIGATION
        )
        assert cfg[const.CONF_DAYS_SINCE_LAST_IRRIGATION] == (
            const.CONF_DEFAULT_DAYS_SINCE_LAST_IRRIGATION
        )

    async def test_a_value_the_install_chose_is_kept(self, hass):
        # Not the default, on either key, so a migration that overwrote rather
        # than filled in would show.
        chosen = {
            const.CONF_SKIP_IRRIGATION_ON_PRECIPITATION: (
                not const.CONF_DEFAULT_SKIP_IRRIGATION_ON_PRECIPITATION
            ),
            const.CONF_PRECIPITATION_THRESHOLD_MM: 7.5,
            const.CONF_DAYS_BETWEEN_IRRIGATION: 3,
        }
        out = await _migrate(hass, 4, {"config": dict(chosen)})
        for key, value in chosen.items():
            assert out["config"][key] == value


class TestV6:
    """v6 -> v7 turned start triggers into recurring schedules.

    A store that old carries on through the v14 reshape in the same call, so
    what is asserted is the shape the scheduler finally reads, not the
    intermediate v7 one.
    """

    async def _schedules(self, hass, triggers, existing=None):
        config = {"irrigation_start_triggers": triggers}
        if existing is not None:
            config["recurring_schedules"] = existing
        out = await _migrate(hass, 6, {"config": config})
        assert "irrigation_start_triggers" not in out["config"]
        return out["config"]["recurring_schedules"]

    async def test_a_sunrise_trigger_finishing_at_sunrise(self, hass):
        (s,) = await self._schedules(
            hass,
            [
                {
                    "name": "Before sunrise",
                    "type": "sunrise",
                    "offset_minutes": -30,
                    "account_for_duration": True,
                }
            ],
        )
        assert s["name"] == "Before sunrise"
        assert s["action"] == "irrigate"
        assert s["zones"] == "all"
        assert s["enabled"] is True
        assert s["recurrence"] == "daily"
        # account_for_duration meant "finish by": the run is anchored to end
        # at sunrise - 30, and nothing bounds its start.
        assert s["anchor"] == "finish"
        assert s["finish_mode"] == "sunrise"
        assert s["finish_offset"] == -30
        assert s["start_mode"] == "none"
        for legacy in ("type", "offset_minutes", "account_for_duration"):
            assert legacy not in s

    async def test_an_azimuth_trigger_starting_at_the_angle(self, hass):
        (s,) = await self._schedules(
            hass,
            [
                {
                    "name": "Sun in the east",
                    "type": "solar_azimuth",
                    "azimuth_angle": 120,
                    "account_for_duration": False,
                    "enabled": False,
                }
            ],
        )
        assert s["enabled"] is False
        assert s["anchor"] == "start"
        assert s["start_mode"] == "solar_azimuth"
        assert s["start_azimuth"] == 120
        # An absent offset was stored as 0 by the v7 step, and carries over.
        assert s["start_offset"] == 0
        assert s["finish_mode"] == "none"
        assert "azimuth_angle" not in s

    async def test_existing_schedules_are_kept_and_the_triggers_appended(self, hass):
        existing = [
            {
                "id": "schedule_keep",
                "name": "Morning",
                "type": "daily",
                "time": "05:00",
                "enabled": True,
                "action": "irrigate",
                "zones": [1],
            }
        ]
        out = await self._schedules(
            hass,
            [
                {"name": "A", "type": "sunset"},
                {"name": "B", "type": "sunset"},
            ],
            existing=existing,
        )
        assert [s["name"] for s in out] == ["Morning", "A", "B"]
        kept = out[0]
        assert kept["id"] == "schedule_keep"
        assert kept["zones"] == [1]
        assert kept["recurrence"] == "daily"
        assert kept["start_mode"] == "time"
        assert kept["start_time"] == "05:00"
        # Two migrated triggers must not share an id: the scheduler keys its
        # trackers and fired occurrences by it.
        new_ids = [s["id"] for s in out[1:]]
        assert len(set(new_ids)) == 2
        assert all(i.startswith("schedule_") for i in new_ids)

    async def test_no_triggers_leaves_an_empty_collection(self, hass):
        assert await self._schedules(hass, []) == []


class TestV8:
    """v9 introduced watering modes; every older zone is a classic one."""

    async def test_zones_default_to_classic_seconds(self, hass):
        out = await _migrate(hass, 8, {"config": {}, "zones": [_zone(0, "Lawn")]})
        (zone,) = out["zones"]
        assert zone["watering_mode"] == "classic"
        assert zone["duration_unit"] == "seconds"
        assert out["config"][const.CONF_ACTIVE_VALVE_RUNS] == []

    async def test_an_existing_mode_is_not_overwritten(self, hass):
        zone = _zone(0, "Bed", watering_mode="self_closing", duration_unit="minutes")
        out = await _migrate(hass, 8, {"config": {}, "zones": [zone]})
        assert out["zones"][0]["watering_mode"] == "self_closing"
        assert out["zones"][0]["duration_unit"] == "minutes"


class TestAV3StoreLoadsEndToEnd:
    """A whole v3 document, through HA's real Store and into the entries."""

    @pytest.fixture
    def v3_document(self):
        return {
            "config": {
                "use_owm": True,
                const.CONF_CALC_TIME: "23:00",
                const.CONF_AUTO_CALC_ENABLED: True,
                # A key no Config field declares. The load must still succeed.
                # (Not because the migration's allowlist strips it: load builds
                # Config from explicit .get()s, and removing the strip leaves
                # every test here passing.)
                "some_long_gone_setting": 1,
            },
            "zones": [
                _zone(0, "Front lawn"),
                _zone(1, "Vegetables", bucket=2.25, duration=0, multiplier=1.5),
            ],
            "modules": [
                {
                    const.MODULE_ID: 0,
                    const.MODULE_NAME: "PyETO",
                    const.MODULE_DESCRIPTION: "Calculate duration based on FAO56",
                    const.MODULE_CONFIG: {},
                }
            ],
            "mappings": [
                {
                    const.MAPPING_ID: 0,
                    const.MAPPING_NAME: "Weather service",
                    # min/max temperature lived in the mapping in releases
                    # that old; load removes them.
                    const.MAPPING_MAPPINGS: {
                        const.MAPPING_MAX_TEMP: {},
                        const.MAPPING_MIN_TEMP: {},
                    },
                }
            ],
        }

    async def _load(self, hass, hass_storage, document):
        hass_storage[STORAGE_KEY] = {
            "version": 3,
            "minor_version": 1,
            "key": STORAGE_KEY,
            "data": document,
        }
        registry = SmartIrrigationStorage(hass)
        await registry.async_load()
        return registry

    async def test_the_config_survives_with_its_values(
        self, hass, hass_storage, v3_document
    ):
        registry = await self._load(hass, hass_storage, v3_document)
        config = registry.config
        assert config.use_weather_service is True
        assert config.weather_service == const.CONF_WEATHER_SERVICE_OWM
        assert config.calctime == "23:00"
        assert config.autocalcenabled is True
        assert config.recurring_schedules == []
        assert config.active_valve_runs == []
        assert config.master_entity is None

    async def test_every_zone_survives_with_its_values(
        self, hass, hass_storage, v3_document
    ):
        registry = await self._load(hass, hass_storage, v3_document)
        assert sorted(registry.zones) == [0, 1]
        front, veg = registry.zones[0], registry.zones[1]
        assert front.name == "Front lawn"
        assert front.bucket == -3.5
        assert front.duration == 875
        assert front.size == 25.0
        assert front.throughput == 12.0
        assert veg.name == "Vegetables"
        assert veg.bucket == 2.25
        assert veg.multiplier == 1.5
        for zone in (front, veg):
            assert zone.watering_mode == "classic"
            assert zone.duration_unit == "seconds"
            assert zone.distributor_id is None
            assert zone.outlet_number is None

    async def test_the_module_and_mapping_survive(
        self, hass, hass_storage, v3_document
    ):
        registry = await self._load(hass, hass_storage, v3_document)
        assert registry.modules[0].name == "PyETO"
        mapping = registry.mappings[0]
        assert mapping.name == "Weather service"
        assert const.MAPPING_MAX_TEMP not in mapping.mappings
        assert const.MAPPING_MIN_TEMP not in mapping.mappings
        assert registry.distributors == {}
