"""Master switch / pump control.

Turns a shared master (pump / main valve) on before the first zone of a watering
cycle and optionally off after the last zone's planned end. Fully optional: with
no ``master_entity`` configured every method is a no-op, so existing behaviour is
byte-identical. The master is actuated via ``homeassistant.turn_on`` /
``turn_off`` (works for switch / valve / input_boolean).

Kicker (optional): a pressure-controlled pump may not restart promptly when it is
merely powered; pulsing it off -> pause -> on forces it to run. Then a settle
delay lets pressure build before the first valve opens.
"""

from __future__ import annotations

import asyncio
import datetime
import logging

from homeassistant.helpers.event import async_call_later
from homeassistant.util import dt as dt_util

from . import const

_LOGGER = logging.getLogger(__name__)


class MasterMixin:
    """Master (pump) sequencing. Mixed into SmartIrrigationCoordinator."""

    def _master_now(self) -> datetime.datetime:
        return dt_util.utcnow()

    async def _master_sleep(self, seconds) -> None:
        await asyncio.sleep(max(0.0, float(seconds or 0)))

    def _master_cfg(self):
        return self.store.config

    def _master_entity(self):
        return getattr(self._master_cfg(), const.CONF_MASTER_ENTITY, None)

    def _master_configured(self) -> bool:
        return bool(self._master_entity())

    async def _master_turn(self, on: bool) -> None:
        entity = self._master_entity()
        if not entity:
            return
        await self.hass.services.async_call(
            "homeassistant",
            "turn_on" if on else "turn_off",
            {"entity_id": entity},
        )

    async def async_master_begin_cycle(self) -> None:
        """Ensure the master is on before the first zone fires.

        Idempotent within a cycle: a second call while already on does nothing
        (no re-kick, no re-settle).
        """
        if not self._master_configured() or getattr(self, "_master_on", False):
            return
        cfg = self._master_cfg()
        if getattr(cfg, const.CONF_MASTER_KICK_ENABLED, False):
            await self._master_turn(False)
            await self._master_sleep(
                getattr(cfg, const.CONF_MASTER_KICK_PAUSE_SECONDS, 1.0)
            )
        await self._master_turn(True)
        self._master_on = True
        settle = getattr(cfg, const.CONF_MASTER_SETTLE_SECONDS, 10)
        if float(settle or 0) > 0:
            await self._master_sleep(settle)

    def _master_note_run(self, seconds: float) -> None:
        """Record the latest expected cycle end (now + seconds), for master_off."""
        deadline = self._master_now() + datetime.timedelta(
            seconds=max(0.0, float(seconds or 0))
        )
        cur = getattr(self, "_master_off_deadline", None)
        if cur is None or deadline > cur:
            self._master_off_deadline = deadline

    async def async_master_schedule_off(self) -> None:
        """Schedule master-off at the cycle end, iff master_off_after is set.

        Overlap-safe: fires only when the (possibly extended) deadline has passed;
        a later run pushes the deadline out and the timer reschedules instead of
        turning the master off under an active run.
        """
        cfg = self._master_cfg()
        if not self._master_configured() or not getattr(
            cfg, const.CONF_MASTER_OFF_AFTER, False
        ):
            return
        deadline = getattr(self, "_master_off_deadline", None)
        if deadline is None:
            return
        cancel = getattr(self, "_master_off_cancel", None)
        if cancel:
            cancel()
            self._master_off_cancel = None
        delay = max(0.0, (deadline - self._master_now()).total_seconds())

        async def _fire(_now=None):
            self._master_off_cancel = None
            dl = getattr(self, "_master_off_deadline", None)
            if dl is not None and self._master_now() < dl:
                # A later run extended the cycle — reschedule, don't turn off.
                await self.async_master_schedule_off()
                return
            await self._master_turn(False)
            self._master_on = False
            self._master_off_deadline = None

        self._master_off_cancel = async_call_later(self.hass, delay, _fire)
