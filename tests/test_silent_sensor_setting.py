"""The sensor group's setting for a silent sensor: keep its last value or pause it."""

import pytest
import voluptuous as vol

from custom_components.irrigation_plus import const
from custom_components.irrigation_plus.store import STORAGE_KEY, SmartIrrigationStorage

KEY = const.MAPPING_ON_SILENT_SENSOR


async def _store(hass):
    store = SmartIrrigationStorage(hass)
    await store.async_load()
    return store


async def _group(store):
    created = await store.async_create_mapping(
        {const.MAPPING_NAME: "Garden", const.MAPPING_MAPPINGS: {}}
    )
    return created[const.MAPPING_ID]


@pytest.mark.asyncio
async def test_a_group_created_now_pauses(hass) -> None:
    store = await _store(hass)
    assert store.get_mapping(await _group(store))[KEY] == "pause"


@pytest.mark.asyncio
async def test_the_group_of_the_first_setup_pauses(hass) -> None:
    store = await _store(hass)
    await store.set_up_factory_defaults()
    assert store.get_mapping(0)[KEY] == "pause"


@pytest.mark.asyncio
@pytest.mark.parametrize("stored", [None, "sometimes", 1, ["pause"]])
async def test_a_stored_group_without_a_valid_setting_keeps(
    hass, hass_storage, stored
) -> None:
    """An existing install must not change its calculation by itself, and a value
    edited by hand must not start cutting either."""
    store = await _store(hass)
    group = await _group(store)
    await store.async_save()
    for mapping in hass_storage[STORAGE_KEY]["data"]["mappings"]:
        if stored is None:
            mapping.pop(KEY, None)
        else:
            mapping[KEY] = stored

    reloaded = await _store(hass)

    assert reloaded.get_mapping(group)[KEY] == "keep"


@pytest.mark.asyncio
async def test_a_group_carried_over_from_smart_irrigation_keeps(
    hass, hass_storage
) -> None:
    """The domain migration copies the old store byte for byte and reads it through
    this load path (test_migrate_domain::test_imports_the_legacy_store_verbatim).
    Smart Irrigation never wrote the setting, so its groups keep their last value."""
    store = await _store(hass)
    group = await _group(store)
    await store.async_save()
    legacy = hass_storage[STORAGE_KEY]["data"]["mappings"][0]
    for key in (KEY, const.MAPPING_SENSOR_OUTAGES, const.MAPPING_SENSOR_LAST_SEEN):
        legacy.pop(key, None)

    reloaded = await _store(hass)

    assert reloaded.get_mapping(group)[KEY] == "keep"


@pytest.mark.asyncio
@pytest.mark.parametrize("value", ["keep", "pause"])
async def test_a_stored_setting_survives_a_reload(hass, value) -> None:
    store = await _store(hass)
    group = await _group(store)
    await store.async_update_mapping(group, {KEY: value})
    await store.async_save()

    reloaded = await _store(hass)

    assert reloaded.get_mapping(group)[KEY] == value


@pytest.mark.asyncio
async def test_a_save_without_the_setting_leaves_it_alone(hass) -> None:
    """An older panel sends id, name and mappings only; what it omits stays."""
    store = await _store(hass)
    group = await _group(store)
    await store.async_update_mapping(group, {KEY: "keep"})

    await store.async_update_mapping(
        group, {const.MAPPING_NAME: "renamed", const.MAPPING_MAPPINGS: {}}
    )

    assert store.get_mapping(group)[KEY] == "keep"


def test_the_mapping_view_takes_the_setting_and_only_its_two_values():
    from custom_components.irrigation_plus.websockets import MAPPING_VIEW_SCHEMA

    assert MAPPING_VIEW_SCHEMA({KEY: "pause"}) == {KEY: "pause"}
    assert MAPPING_VIEW_SCHEMA({KEY: "keep"}) == {KEY: "keep"}
    with pytest.raises(vol.Invalid):
        MAPPING_VIEW_SCHEMA({KEY: "sometimes"})
