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
