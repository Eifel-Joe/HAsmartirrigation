"""Observed watering extended to service/self-closing zones (Phase 1)."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import attr
import pytest

from custom_components.smart_irrigation import SmartIrrigationCoordinator, const
from custom_components.smart_irrigation.store import ZoneEntry


def test_zone_observed_entity_defaults_none():
    field = attr.fields_dict(ZoneEntry)["observed_entity"]
    assert field.default is None
    assert const.ZONE_OBSERVED_ENTITY == "observed_entity"


@pytest.fixture(autouse=True)
def _stub_state_tracker(monkeypatch):
    # async_setup_observed_watering subscribes via async_track_state_change_event,
    # a real HA helper that needs a live hass.data. These unit tests build a Mock
    # hass, so stub the tracker to a no-op returning a Mock unsub — this exercises
    # the entity_map build (the code under test) without standing up HA core.
    monkeypatch.setattr(
        "custom_components.smart_irrigation.observed_watering."
        "async_track_state_change_event",
        Mock(return_value=Mock()),
    )


@pytest.fixture(autouse=True)
def _stub_dispatcher(monkeypatch):
    # _credit_observed_watering ends with async_dispatcher_send(self.hass, ...),
    # which iterates hass.data — a Mock hass would misbehave. Stub it so the
    # crediting tests can run against the Mock coordinator (mirrors the
    # test_experimental_features observer setup).
    monkeypatch.setattr(
        "custom_components.smart_irrigation.observed_watering.async_dispatcher_send",
        Mock(),
    )


def _obs_coord(zones, enabled=True):
    coord = SmartIrrigationCoordinator.__new__(SmartIrrigationCoordinator)
    coord.hass = Mock()  # async_track_state_change_event returns a Mock
    coord.store = Mock()
    coord.store.config = SimpleNamespace(observed_watering_enabled=enabled)
    coord.store.async_get_zones = AsyncMock(return_value=zones)
    coord._observed_entities = frozenset()
    coord._observed_unsub = None
    coord._observed_on_since = {}
    coord._observed_zone_by_entity = {}
    return coord


async def test_setup_maps_observed_entity_for_service_zone():
    coord = _obs_coord([{const.ZONE_ID: 1, const.ZONE_OBSERVED_ENTITY: "switch.beet"}])
    await coord.async_setup_observed_watering()
    assert coord._observed_zone_by_entity == {"switch.beet": 1}


async def test_setup_prefers_linked_entity_over_observed():
    coord = _obs_coord(
        [
            {
                const.ZONE_ID: 1,
                const.ZONE_LINKED_ENTITY: "switch.lawn",
                const.ZONE_OBSERVED_ENTITY: "switch.other",
            }
        ]
    )
    await coord.async_setup_observed_watering()
    assert coord._observed_zone_by_entity == {"switch.lawn": 1}


async def test_setup_maps_nothing_when_feature_off():
    coord = _obs_coord(
        [{const.ZONE_ID: 1, const.ZONE_OBSERVED_ENTITY: "switch.beet"}], enabled=False
    )
    await coord.async_setup_observed_watering()
    assert coord._observed_zone_by_entity == {}


# --- Task 1: capped-seconds helper -----------------------------------------


def test_capped_seconds_bounds_at_maximum_duration_plus_margin():
    coord = _obs_coord([])
    zone = {const.ZONE_MAXIMUM_DURATION: 3600}
    # under the cap: unchanged
    assert coord._observed_capped_seconds(zone, 1200) == 1200
    # over the cap: bounded to maximum_duration + OBSERVED_CAP_MARGIN_SECONDS
    assert coord._observed_capped_seconds(zone, 21304) == 3600 + const.OBSERVED_CAP_MARGIN_SECONDS


def test_capped_seconds_falls_back_when_no_maximum_duration():
    coord = _obs_coord([])
    # a zone without maximum_duration uses the default cap, still bounded
    zone = {}
    capped = coord._observed_capped_seconds(zone, 99999)
    assert capped == const.CONF_DEFAULT_MAXIMUM_DURATION + const.OBSERVED_CAP_MARGIN_SECONDS


# --- Task 2/5: crediting helper --------------------------------------------


def _credit_coord(zone):
    """Coordinator stub able to run _credit_observed_watering end to end."""
    import custom_components.smart_irrigation.observed_watering as ow

    coord = _obs_coord([])
    coord.store.get_zone = Mock(return_value=zone)
    coord._record_run = AsyncMock()
    coord.async_write_watered_bucket = AsyncMock()
    coord.hass.config = SimpleNamespace(units=ow.METRIC_SYSTEM)  # metric: no conv
    return coord


async def test_non_flow_zone_credit_capped_at_maximum_duration():
    zone = {
        const.ZONE_ID: 2, const.ZONE_SIZE: 5.0, const.ZONE_THROUGHPUT: 3.1,
        const.ZONE_MAXIMUM_DURATION: 3600, const.ZONE_FLOW_SENSOR: None,
        const.ZONE_BUCKET: 0.0, const.ZONE_STATE: const.ZONE_STATE_AUTOMATIC,
    }
    coord = _credit_coord(zone)
    await coord._credit_observed_watering(2, 21304)  # ~6h stuck-open
    # volume recorded uses capped seconds (3630 s), NOT 21304 s
    capped_l = 3.1 * ((3600 + const.OBSERVED_CAP_MARGIN_SECONDS) / 60.0)
    kwargs = coord._record_run.call_args.kwargs
    assert kwargs["volume_l"] == pytest.approx(capped_l)
    assert kwargs["actual_s"] == 3630
