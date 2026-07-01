"""Master switch / pump control."""

from custom_components.smart_irrigation.store import (
    STORAGE_VERSION,
    Config,
    async_get_registry,
)


def test_storage_version_is_11():
    assert STORAGE_VERSION == 11


def test_config_has_master_defaults():
    c = Config()
    assert c.master_entity is None
    assert c.master_settle_seconds == 10
    assert c.master_kick_enabled is False
    assert c.master_kick_pause_seconds == 1.0
    assert c.master_off_after is False


async def test_migration_seeds_master_defaults(hass):
    reg = await async_get_registry(hass)
    data = {"config": {}, "zones": []}
    await reg._store._async_migrate_func(10, data)
    cfg = data["config"]
    assert cfg["master_entity"] is None
    assert cfg["master_settle_seconds"] == 10
    assert cfg["master_kick_enabled"] is False
    assert cfg["master_kick_pause_seconds"] == 1.0
    assert cfg["master_off_after"] is False
