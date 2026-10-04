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
from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from . import const
from .helpers import STAMP_FROM_STORE, coerce_stamp

_LOGGER = logging.getLogger(__name__)

STALE_AFTER = timedelta(seconds=const.SENSOR_STALE_AFTER_SECONDS)
RETENTION = timedelta(days=const.SENSOR_OUTAGE_RETENTION_DAYS)


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
    missing, unavailable or unknown the field is silent whatever its device does,
    so only the remembered sign counts. Otherwise its device vouches for it: at a
    living station some value reports or changes within the limit, while a quiet
    rain gauge on the same device may not change for days. ``remembered`` is the
    sign stored at the previous check, so an outage that spans a restart keeps its
    start; a sign never moves backwards.
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
    survives until the next check. Unavailable or unknown states do not count. None
    when nothing changed since ``start``. This only dates a return; whether the
    outage has ended is ``last_sign_of_life``'s call.
    """
    states = ([own] if own is not None else []) + list(siblings)
    stamps = [s.changed for s in states if s.valid and s.changed > start]
    return min(stamps) if stamps else None


@dataclass(frozen=True)
class Outage:
    """One stretch in which a sensor entity stayed silent for longer than the limit.

    ``start`` is its last sign of life, ``end`` its first report afterwards (None
    while it is still silent). Stored as ISO strings on HA's clock: the frame the
    reading buffer's row stamps are in.
    """

    entity_id: str
    device_id: str | None
    fields: tuple[str, ...]
    start: datetime
    end: datetime | None = None

    def to_store(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "device_id": self.device_id,
            "fields": list(self.fields),
            "start": self.start.isoformat(),
            "end": self.end.isoformat() if self.end is not None else None,
        }

    @classmethod
    def from_store(cls, raw) -> Outage | None:
        """Read one stored record; anything unreadable is dropped, never raised.

        Unreadable: not a dict, no entity id, no readable start, an end that is
        present but no stamp, ``fields`` that is not a list of strings (missing or
        empty means none).
        NOT-TO-DO: do not let this raise. The ledger is read in the setup and in the
        configuration paths; a file edited by hand, or written by another build of
        this integration, must cost one record, not the integration.
        """
        if not isinstance(raw, dict) or not raw.get("entity_id"):
            return None
        fields = raw.get("fields") or []
        if not isinstance(fields, list) or not all(isinstance(f, str) for f in fields):
            return None
        start = coerce_stamp(raw.get("start"), STAMP_FROM_STORE)
        if start is None:
            return None
        end = coerce_stamp(raw.get("end"), STAMP_FROM_STORE)
        if end is None and raw.get("end") is not None:
            return None  # a closed record must not come back open
        return cls(
            entity_id=str(raw["entity_id"]),
            device_id=raw.get("device_id"),
            fields=tuple(fields),
            start=start,
            end=end,
        )


def outages_of(mapping: dict) -> list[Outage]:
    """The readable outages stored on a sensor group; never raises."""
    stored = mapping.get(const.MAPPING_SENSOR_OUTAGES)
    if not isinstance(stored, list):
        return []
    return [outage for raw in stored if (outage := Outage.from_store(raw)) is not None]


@dataclass(frozen=True)
class Evidence:
    """What one check learned about one sensor-mapped entity."""

    fields: tuple[str, ...]
    device_id: str | None
    last: datetime | None  # its last sign of life; None: no evidence at all
    recovered: datetime | None = None  # first report after an open outage began


def advance_outages(
    outages: list[Outage],
    evidence: dict[str, Evidence],
    now: datetime,
    *,
    stale_after: timedelta = STALE_AFTER,
    retention: timedelta = RETENTION,
) -> tuple[list[Outage], list[Outage], list[Outage]]:
    """One check over one sensor group's ledger: ``(outages, opened, closed)``.

    Opens an outage for an entity without an open one whose last sign is older
    than ``stale_after`` (strictly: a silence of exactly the limit is still
    bridged), starting AT that sign. Closes an open one once a sign newer than its
    start appears: at the device's first report after the start when that is
    known, else at that sign. Ends one whose entity the group no longer reads (its
    sensor was replaced or unmapped by a path that did not empty the ledger) at
    ``now``, so neither it nor its notice stays open. Drops closed outages that
    ended more than ``retention`` ago; open ones stay whatever their age.
    """
    kept: list[Outage] = []
    opened: list[Outage] = []
    closed: list[Outage] = []
    still_open: set[str] = set()
    for outage in outages:
        if outage.end is not None:
            if now - outage.end <= retention:
                kept.append(outage)
            continue
        seen = evidence.get(outage.entity_id)
        if seen is None:
            ended = replace(outage, end=now)
            kept.append(ended)
            closed.append(ended)
            continue
        if seen.last is not None and seen.last > outage.start:
            back = seen.recovered
            end = back if back is not None and back > outage.start else seen.last
            ended = replace(outage, end=end)
            kept.append(ended)
            closed.append(ended)
            continue
        kept.append(outage)
        still_open.add(outage.entity_id)
    for entity_id, seen in evidence.items():
        if entity_id in still_open or seen.last is None:
            continue
        if now - seen.last > stale_after:
            outage = Outage(entity_id, seen.device_id, seen.fields, seen.last)
            kept.append(outage)
            opened.append(outage)
    return kept, opened, closed


def stale_issue_placeholders(group_name: str, outages: list[Outage]) -> dict | None:
    """The repair issue's placeholders for a group's OPEN outages, or None."""
    silent = sorted(
        (o for o in outages if o.end is None), key=lambda o: (o.start, o.entity_id)
    )
    if not silent:
        return None
    return {
        "group": group_name,
        "entities": ", ".join(f"{o.entity_id} ({', '.join(o.fields)})" for o in silent),
        "since": silent[0].start.strftime("%Y-%m-%d %H:%M"),
    }


def outage_event_payload(mapping_id, group_name: str, outage: Outage) -> dict:
    """The bus event's data for an outage starting (no end yet) or ending."""
    return {
        "mapping_id": mapping_id,
        "mapping": group_name,
        "entity_id": outage.entity_id,
        "device_id": outage.device_id,
        "fields": list(outage.fields),
        "since": outage.start.isoformat(),
        "until": outage.end.isoformat() if outage.end is not None else None,
        "stale": outage.end is None,
    }
