"""The config flow's #120 migrate step, end to end over the seed.

`tests/test_config_flow.py` is quarantined (it drives a real flow, which needs
panel_custom -> frontend -> websocket_api), so the migrate step had no coverage
at all -- and it is the step that decides what a migrated install is created
with. These drive the handler directly and assert on the data it would create
the entry from: `_check_unique` and `async_create_entry` are Home Assistant's,
not ours, and are stubbed.
"""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

from custom_components.irrigation_plus import const
from custom_components.irrigation_plus.config_flow import SmartIrrigationConfigFlow
from custom_components.irrigation_plus.migrate_domain import legacy_storage_path


def _hass(tmp_path, legacy_entries=()):
    storage = tmp_path / ".storage"
    storage.mkdir(parents=True, exist_ok=True)

    async def _executor(func, *args):
        return func(*args)

    return SimpleNamespace(
        config=SimpleNamespace(path=lambda *parts: str(tmp_path.joinpath(*parts))),
        config_entries=SimpleNamespace(
            async_entries=lambda domain: (
                list(legacy_entries) if domain == const.LEGACY_DOMAIN else []
            )
        ),
        async_add_executor_job=_executor,
    )


def _flow(hass):
    """A flow whose entry creation is captured rather than performed."""
    flow = SmartIrrigationConfigFlow()
    flow.hass = hass
    flow._check_unique = AsyncMock()
    created = {}

    def _create_entry(title=None, data=None, **kwargs):
        created["title"] = title
        created["data"] = data
        return {"type": "create_entry", "title": title, "data": data}

    flow.async_create_entry = _create_entry
    return flow, created


class TestMigrateStep:
    async def test_carries_the_key_from_a_surviving_config_entry(self, tmp_path):
        entry = SimpleNamespace(
            entry_id="legacy1",
            data={const.CONF_WEATHER_SERVICE_API_KEY: "original"},
            options={
                const.CONF_USE_WEATHER_SERVICE: True,
                const.CONF_WEATHER_SERVICE: const.CONF_WEATHER_SERVICE_OWM,
                const.CONF_OWM_API_KEY: "current",
            },
        )
        flow, created = _flow(_hass(tmp_path, [entry]))

        await flow.async_step_migrate({const.CONF_MIGRATED_FROM_LEGACY: True})

        assert created["data"][const.CONF_OWM_API_KEY] == "current"
        assert created["data"][const.CONF_USE_WEATHER_SERVICE] is True
        assert created["data"][const.CONF_MIGRATED_FROM_LEGACY] is True

    async def test_a_leftover_storage_file_supplies_no_credentials(self, tmp_path):
        """Entry already removed. The key is gone, and the flow says so (#128).

        This used to assert the opposite -- that the bridge release's staged
        copy was read back out of the storage file. It passed because the
        fixture wrote those keys by hand, which no release ever did: the store
        filters every write against `attr.fields_dict(Config)` and `Config` has
        no credential attribute, so the staging wrote nothing on every install.
        The fixture agreed with the annotation instead of with the code.
        """
        hass = _hass(tmp_path)
        legacy_storage_path(hass).write_text(
            json.dumps(
                {
                    "version": 9,
                    "data": {
                        "config": {
                            const.CONF_USE_WEATHER_SERVICE: True,
                            const.CONF_WEATHER_SERVICE: const.CONF_WEATHER_SERVICE_PW,
                            const.CONF_PW_API_KEY: "never-actually-written",
                        }
                    },
                }
            ),
            encoding="utf-8",
        )
        flow, created = _flow(hass)

        result = await flow.async_step_migrate({const.CONF_MIGRATED_FROM_LEGACY: True})

        # Nothing was created yet -- the user is told first, and told WHICH
        # provider, which the store can still answer even though the entry
        # that held the key is gone.
        assert created == {}
        assert result["step_id"] == "credentials"
        assert (
            result["description_placeholders"]["service"]
            == const.CONF_WEATHER_SERVICE_PW
        )

        await flow.async_step_credentials({})
        assert const.CONF_PW_API_KEY not in created["data"]

    async def test_nothing_recoverable_still_creates_a_usable_entry(self, tmp_path):
        """A pre-bridge install with its entry gone: empty, but weather off, not broken."""
        flow, created = _flow(_hass(tmp_path))

        await flow.async_step_migrate({const.CONF_MIGRATED_FROM_LEGACY: True})

        assert created["data"][const.CONF_USE_WEATHER_SERVICE] is False
        assert created["data"][const.CONF_INSTANCE_NAME] == const.NAME

    async def test_declining_does_not_seed_anything(self, tmp_path):
        entry = SimpleNamespace(
            entry_id="legacy1",
            data={},
            options={const.CONF_OWM_API_KEY: "current"},
        )
        flow, created = _flow(_hass(tmp_path, [entry]))

        result = await flow.async_step_migrate({const.CONF_MIGRATED_FROM_LEGACY: False})

        assert created == {}
        assert result["step_id"] == "user"


class TestCredentialsStep:
    """The migration tells the user about the key it could not carry (#128).

    Without this the first evidence is weather quietly not updating, days
    later, on an install where everything else imported perfectly.
    """

    async def test_warns_and_names_the_service_then_still_creates_the_entry(
        self, tmp_path
    ):
        entry = SimpleNamespace(
            entry_id="legacy1",
            data={},
            options={
                const.CONF_USE_WEATHER_SERVICE: True,
                const.CONF_WEATHER_SERVICE: const.CONF_WEATHER_SERVICE_OWM,
            },
        )
        flow, created = _flow(_hass(tmp_path, [entry]))

        result = await flow.async_step_migrate({const.CONF_MIGRATED_FROM_LEGACY: True})
        assert result["step_id"] == "credentials"
        assert (
            result["description_placeholders"]["service"]
            == const.CONF_WEATHER_SERVICE_OWM
        )

        # Informational only: acknowledging it creates the entry, with
        # everything that DID import intact.
        await flow.async_step_credentials({})
        assert created["data"][const.CONF_MIGRATED_FROM_LEGACY] is True
        assert created["data"][const.CONF_WEATHER_SERVICE] == (
            const.CONF_WEATHER_SERVICE_OWM
        )

    async def test_no_warning_when_the_key_came_across(self, tmp_path):
        entry = SimpleNamespace(
            entry_id="legacy1",
            data={},
            options={
                const.CONF_USE_WEATHER_SERVICE: True,
                const.CONF_WEATHER_SERVICE: const.CONF_WEATHER_SERVICE_OWM,
                const.CONF_OWM_API_KEY: "carried",
            },
        )
        flow, created = _flow(_hass(tmp_path, [entry]))

        await flow.async_step_migrate({const.CONF_MIGRATED_FROM_LEGACY: True})

        assert created["data"][const.CONF_OWM_API_KEY] == "carried"

    async def test_no_warning_for_an_install_that_used_no_weather_service(
        self, tmp_path
    ):
        # The commonest shape of "nothing recoverable" is also the one with
        # nothing to recover. A warning here trains the user to skip them.
        flow, created = _flow(_hass(tmp_path))

        await flow.async_step_migrate({const.CONF_MIGRATED_FROM_LEGACY: True})

        assert created["data"][const.CONF_USE_WEATHER_SERVICE] is False
