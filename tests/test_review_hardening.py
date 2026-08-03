"""Fixes from the deferred-findings burndown (2026-08-03).

Four unrelated latent defects, grouped because they were closed in one pass:
the zone-selection character-iteration trap, the Lovelace resource that
outlived an uninstall, `@callback` on a coroutine function, and `localize()`
returning None (that one lives in test_localize.py, next to its siblings).
"""

import inspect
from unittest.mock import AsyncMock, Mock

from custom_components.smart_irrigation import const
from custom_components.smart_irrigation.helpers import normalize_zone_selection
from custom_components.smart_irrigation.irrigation import IrrigationRunnerMixin
from custom_components.smart_irrigation.panel import async_remove_card_resource


class TestNormalizeZoneSelection:
    """A schedule's `zones` is "all" or a list — never a bare id string."""

    def test_all_means_everything(self):
        assert normalize_zone_selection("all") is None

    def test_none_means_everything(self):
        assert normalize_zone_selection(None) is None

    def test_a_list_passes_through(self):
        assert normalize_zone_selection(["1", "2"]) == ["1", "2"]

    def test_a_bare_multi_digit_id_is_one_zone_not_two(self):
        """The bug: `for zone_id in "12"` targets zones 1 and 2, not zone 12.

        Single-digit ids work by coincidence, which is exactly why this
        survives casual testing — it only misfires once an install grows past
        zone 9, and then it waters the wrong ground silently.
        """
        assert normalize_zone_selection("12") == ["12"]

    def test_a_bare_single_digit_id_is_still_one_zone(self):
        assert normalize_zone_selection("3") == ["3"]

    def test_an_arbitrary_iterable_is_materialised(self):
        """Callers iterate the result more than once."""
        result = normalize_zone_selection(iter(["7", "8"]))
        assert result == ["7", "8"]
        assert result == ["7", "8"]


class TestIrrigateLinkedEntitiesIsNotACallback:
    """`@callback` on an `async def` is a latent silent-skip.

    It marks a SYNCHRONOUS function as safe to run directly in the event loop,
    and HA's job helpers read that flag to decide not to await. It was inert
    only because the one caller awaits directly — routing it through
    `async_add_job` would have dropped the coroutine and skipped every run.
    """

    def test_it_is_still_a_coroutine_function(self):
        assert inspect.iscoroutinefunction(
            IrrigationRunnerMixin._irrigate_linked_entities
        )

    def test_it_is_not_flagged_as_a_ha_callback(self):
        assert not getattr(
            IrrigationRunnerMixin._irrigate_linked_entities, "_hass_callback", False
        )


def _resources(items):
    """A stand-in for Lovelace's storage-backed ResourceStorageCollection."""
    res = Mock()
    res.__class__.__name__ = "ResourceStorageCollection"
    res.loaded = True
    res.async_items = Mock(return_value=list(items))
    res.async_delete_item = AsyncMock()
    return res


def _hass_with(resources):
    hass = Mock()
    hass.data = {"lovelace": Mock(resources=resources)}
    return hass


class TestRemoveCardResource:
    """Uninstall used to leave a resource pointing at a 404 forever."""

    async def test_our_resource_is_deleted(self):
        resources = _resources([{"id": "a", "url": f"{const.CARD_URL}?v=123"}])

        assert await async_remove_card_resource(_hass_with(resources)) is True

        resources.async_delete_item.assert_awaited_once_with("a")

    async def test_a_foreign_resource_is_left_alone(self):
        """Never touch a resource the user added pointing somewhere else."""
        resources = _resources([{"id": "b", "url": "/local/my-own-card.js"}])

        assert await async_remove_card_resource(_hass_with(resources)) is False

        resources.async_delete_item.assert_not_awaited()

    async def test_duplicates_are_all_removed(self):
        """Older builds could leave more than one cache-busted entry."""
        resources = _resources(
            [
                {"id": "a", "url": f"{const.CARD_URL}?v=1"},
                {"id": "b", "url": "/local/other.js"},
                {"id": "c", "url": f"{const.CARD_URL}?v=2"},
            ]
        )

        assert await async_remove_card_resource(_hass_with(resources)) is True

        assert [c.args[0] for c in resources.async_delete_item.await_args_list] == [
            "a",
            "c",
        ]

    async def test_yaml_mode_lovelace_is_a_no_op(self):
        """No writable resource store — must not raise."""
        resources = Mock()
        resources.__class__.__name__ = "ResourceYAMLCollection"

        assert await async_remove_card_resource(_hass_with(resources)) is False

    async def test_no_lovelace_at_all_is_a_no_op(self):
        hass = Mock()
        hass.data = {}
        assert await async_remove_card_resource(hass) is False

    async def test_an_unloaded_collection_is_loaded_first(self):
        resources = _resources([{"id": "a", "url": const.CARD_URL}])
        resources.loaded = False
        resources.async_load = AsyncMock()

        await async_remove_card_resource(_hass_with(resources))

        resources.async_load.assert_awaited_once()
