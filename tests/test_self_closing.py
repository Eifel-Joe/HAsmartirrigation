"""Self-closing valve mode (Phase 1)."""

from unittest.mock import AsyncMock, Mock

from custom_components.smart_irrigation import SmartIrrigationCoordinator, const


def _coord():
    c = SmartIrrigationCoordinator.__new__(SmartIrrigationCoordinator)
    c.hass = Mock()
    c.hass.services.async_call = AsyncMock()
    c.store = Mock()
    c.store.async_update_zone = AsyncMock()
    c.store.async_update_config = AsyncMock()
    return c


def _zone(**kw):
    z = {
        const.ZONE_ID: 2,
        const.ZONE_NAME: "Beet",
        const.ZONE_DURATION: 600.0,  # seconds (matches _run_valve_metered)
        const.ZONE_WATERING_MODE: const.WATERING_MODE_SERVICE,
        const.ZONE_RUN_SERVICE: "script.irrigation_beet",
        const.ZONE_DURATION_FIELD: "dauer",
        const.ZONE_DURATION_UNIT: const.DURATION_UNIT_MINUTES,
        const.ZONE_RUN_DATA: {},
    }
    z.update(kw)
    return z


def test_convert_duration_minutes_rounds_up_sub_minute():
    c = _coord()
    assert c._sc_convert(600.0, const.DURATION_UNIT_SECONDS) == 600
    assert c._sc_convert(600.0, const.DURATION_UNIT_MINUTES) == 10
    # sub-minute rounds up to 1 on minute hardware
    assert c._sc_convert(15.0, const.DURATION_UNIT_MINUTES) == 1


async def test_open_calls_run_service_with_duration_field():
    c = _coord()
    await c._sc_dispatch_open(_zone())
    c.hass.services.async_call.assert_awaited_once()
    domain, service, data = c.hass.services.async_call.await_args.args
    assert (domain, service) == ("script", "irrigation_beet")
    assert data["dauer"] == 10  # 600 s -> 10 min
    assert data["zone_id"] == 2
    assert data["zone_name"] == "Beet"
