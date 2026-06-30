"""Self-closing valve mode: delegate the valve close to self-closing hardware.

A zone in WATERING_MODE_SERVICE is run by firing a configured service with the
run duration; the valve owns the close (a hardware countdown), so an HA outage
mid-run cannot cause continuous irrigation. The bucket is credited optimistically
at start and the in-flight run is persisted for restart reconciliation.
"""

from __future__ import annotations

import logging
import math

from homeassistant.util import dt as dt_util

from . import const

_LOGGER = logging.getLogger(__name__)


class SelfClosingMixin:
    """Self-closing actuation lifecycle. Mixed into SmartIrrigationCoordinator."""

    @staticmethod
    def _sc_convert(seconds: float, unit: str) -> int:
        """Convert a run duration (seconds) to the hardware's unit, rounding up."""
        seconds = float(seconds or 0)
        if unit == const.DURATION_UNIT_MINUTES:
            return max(1, math.ceil(seconds / 60.0)) if seconds > 0 else 0
        return int(round(seconds))

    def _sc_split_service(self, dotted: str):
        """'domain.service' -> (domain, service)."""
        domain, _, service = (dotted or "").partition(".")
        return domain, service

    async def _sc_dispatch_open(self, zone: dict) -> None:
        """Fire the zone's run_service with the converted duration."""
        seconds = float(zone.get(const.ZONE_DURATION) or 0)
        unit = zone.get(const.ZONE_DURATION_UNIT, const.DURATION_UNIT_SECONDS)
        field = zone.get(const.ZONE_DURATION_FIELD)
        domain, service = self._sc_split_service(zone.get(const.ZONE_RUN_SERVICE))
        data = dict(zone.get(const.ZONE_RUN_DATA) or {})
        if field:
            data[field] = self._sc_convert(seconds, unit)
        data["zone_id"] = zone.get(const.ZONE_ID)
        data["zone_name"] = zone.get(const.ZONE_NAME)
        await self.hass.services.async_call(domain, service, data)

    def _sc_fire(self, event: str, data: dict) -> None:
        """Fire a domain-prefixed bus event."""
        self.hass.bus.async_fire(f"{const.DOMAIN}_{event}", data)

    async def _sc_active_runs(self) -> list:
        """Return the persisted list of in-flight self-closing runs."""
        cfg = await self.store.async_get_config()
        return list(cfg.get(const.CONF_ACTIVE_VALVE_RUNS, []) or [])

    async def _sc_persist_runs(self, runs: list) -> None:
        await self.store.async_update_config({const.CONF_ACTIVE_VALVE_RUNS: runs})

    async def _sc_add_run(self, record: dict) -> None:
        runs = [
            r
            for r in await self._sc_active_runs()
            if r.get(const.RUN_ZONE_ID) != record[const.RUN_ZONE_ID]
        ]
        runs.append(record)
        await self._sc_persist_runs(runs)

    async def _sc_remove_run(self, zone_id) -> None:
        runs = [
            r
            for r in await self._sc_active_runs()
            if r.get(const.RUN_ZONE_ID) != zone_id
        ]
        await self._sc_persist_runs(runs)

    async def async_run_self_closing(
        self, zone: dict, *, trigger: str = "schedule"
    ) -> bool:
        """Fire a self-closing run for one zone. Returns True if started."""
        zone_id = zone.get(const.ZONE_ID)
        planned_seconds = float(zone.get(const.ZONE_DURATION) or 0)
        if planned_seconds <= 0:
            return False

        await self._sc_dispatch_open(zone)

        # Confirm the open BEFORE crediting (None = write-only valve, treat as ok).
        confirmed = await self._confirm_valve_running(
            zone_id, zone.get(const.ZONE_RUN_SERVICE)
        )
        if confirmed is False:
            self._sc_fire(
                const.EVENT_ZONE_PROBLEM,
                {
                    "zone_id": zone_id,
                    "zone": zone.get(const.ZONE_NAME),
                    "entity_id": zone.get(const.ZONE_RUN_SERVICE),
                    "reason": const.PROBLEM_VALVE_DID_NOT_OPEN,
                },
            )
            return False

        # Optimistic bucket credit (the valve owns the close -> assume completion).
        volume_l = self._timed_volume_l(zone, planned_seconds)
        depth = self._credited_depth_native(zone, volume_l)
        ceiling = zone.get(const.ZONE_MAXIMUM_BUCKET)
        new_bucket = float(zone.get(const.ZONE_BUCKET) or 0) + depth
        if ceiling and new_bucket > ceiling:
            new_bucket = float(ceiling)
        await self.store.async_update_zone(zone_id, {const.ZONE_BUCKET: new_bucket})
        await self._record_run(
            zone_id,
            result=const.RUN_RESULT_COMPLETED,
            volume_l=volume_l,
            planned_s=planned_seconds,
            actual_s=planned_seconds,
            detail=const.RUN_DETAIL_OPTIMISTIC,
            trigger=const.RUN_TRIGGER_SELF_CLOSING,
            add_to_total=True,
        )

        # Persist the in-flight run for restart reconciliation.
        await self._sc_add_run(
            {
                const.RUN_ZONE_ID: zone_id,
                const.RUN_ENTITY_ID: zone.get(const.ZONE_RUN_SERVICE),
                const.RUN_STARTED: dt_util.utcnow().isoformat(),
                const.RUN_PLANNED_SECONDS: planned_seconds,
                const.RUN_PLANNED_MM: depth,
                const.RUN_MODE: const.WATERING_MODE_SERVICE,
                const.RUN_CREDITED: True,
            }
        )

        self._sc_fire(
            const.EVENT_IRRIGATE_STARTED,
            {
                "zones": [
                    {
                        "zone_id": zone_id,
                        "zone": zone.get(const.ZONE_NAME),
                        "seconds": int(planned_seconds),
                    }
                ],
            },
        )
        return True
