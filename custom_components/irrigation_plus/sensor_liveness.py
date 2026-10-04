"""When a weather sensor stops reporting: liveness, the outage ledger, the notice.

A sensor group carries a field's last value forward while nothing new arrives (the
per-field boundary row, ``last_entry``). That is right for a value that is merely
steady and wrong for a sensor that died. This module tells the two apart by the
sensor's HA *device* -- at a living station some value reports or changes within
``SENSOR_STALE_AFTER_SECONDS``, a quiet rain gauge included -- records every outage
longer than that on the sensor group, and tells the user: a repair issue per group
while an outage is open, and a bus event when one starts and when it ends (#188).

Nothing here changes a calculation: a silent sensor's last value is still used, as
before. The ledger records when it fell silent and the notice tells the user.

The rules are pure functions, testable without Home Assistant; the
``SensorLivenessMixin`` at the end is the coordinator glue.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from . import const

_LOGGER = logging.getLogger(__name__)


def sensor_fields_by_entity(mappings_config: dict) -> dict[str, tuple[str, ...]]:
    """``{entity_id: fields}`` for every field this sensor group reads from an entity.

    Weather-service and static fields have no device to fall silent; a legacy bare
    string is not a field config. ``input_number`` is a value set by hand, which
    never reports on its own, so it is exempt.
    """
    found: dict[str, list[str]] = {}
    for field_name, cfg in mappings_config.items():
        if not isinstance(cfg, dict):
            continue
        if cfg.get(const.MAPPING_CONF_SOURCE) != const.MAPPING_CONF_SOURCE_SENSOR:
            continue
        entity_id = cfg.get(const.MAPPING_CONF_SENSOR)
        if not entity_id:
            continue
        if entity_id.split(".", 1)[0] in const.SENSOR_LIVENESS_EXEMPT_DOMAINS:
            continue
        found.setdefault(entity_id, []).append(field_name)
    return {entity_id: tuple(fields) for entity_id, fields in found.items()}


@dataclass(frozen=True)
class Seen:
    """One entity's state as liveness reads it, stamps naive on HA's clock."""

    entity_id: str
    valid: bool  # not unavailable/unknown
    reported: datetime  # State.last_reported
    changed: datetime  # State.last_changed


def last_sign_of_life(
    own: Seen | None, siblings: list[Seen], remembered: datetime | None
) -> datetime | None:
    """The newest report that vouches for a field, or None when there is none.

    ``own`` is the field's entity (None when it does not exist). While it is
    unavailable/unknown the field is silent whatever its device does, so only the
    remembered sign counts. Otherwise its device vouches for it: at a living station
    some value reports or changes within the limit, while a quiet rain gauge on the
    same device may not change for days. ``remembered`` is the sign stored at the
    previous check, so an outage that spans a restart keeps its start; a sign never
    moves backwards.
    """
    candidates = [remembered] if remembered is not None else []
    if own is not None and own.valid:
        candidates.append(own.reported)
        candidates.extend(s.reported for s in siblings if s.valid)
    return max(candidates) if candidates else None


def first_report_after(
    own: Seen | None, siblings: list[Seen], start: datetime
) -> datetime | None:
    """When the device spoke again after ``start``: its earliest change since then.

    A returning device's first report changes most of its values, so the earliest
    ``last_changed`` after the outage began is the closest record of its return that
    survives until the next check. None when nothing changed since ``start``.
    """
    states = ([own] if own is not None else []) + list(siblings)
    stamps = [s.changed for s in states if s.valid and s.changed > start]
    return min(stamps) if stamps else None
