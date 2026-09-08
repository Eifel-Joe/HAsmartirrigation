"""Keep pre-#120 service calls working after the domain rename (#120).

The rename moves every service from ``smart_irrigation.*`` to
``irrigation_plus.*``. Storage, history and statistics are carried across, but a
service name is not data we own — it is baked into the user's own automations,
scripts and blueprints, and there is nothing in Home Assistant that rewrites
those. Without an alias, upgrade day silently breaks every automation that calls
``smart_irrigation.reset_bucket``: the call raises ``ServiceNotFound``, the
automation aborts mid-sequence, and the only evidence is a log line.

So each of our services is also registered under the old domain, forwarding to
the real one. Two rules make that safe:

* **Never claim a name somebody else owns.** If a DIFFERENT project holds the
  ``smart_irrigation`` domain on this machine, aliasing is exactly the collision
  the rename was meant to remove, so it is skipped entirely — the same gate,
  and for the same reason, as the legacy card shim in ``panel.py``. A service
  already registered under the old domain is left alone even then, because
  ``async_register`` overwrites silently and the loser would be the integration
  that actually owns the name.
* **Aliases are removed on unload**, so a disabled or removed integration does
  not leave phantom services behind. Removal matches on the callable Home
  Assistant is actually holding, not on the name -- see ``_registered_target``
  for why the obvious version of that check silently never matched.

Each alias also gets an explicit description via ``async_set_service_schema``.
That is not cosmetic. Home Assistant builds its service documentation by
resolving the INTEGRATION behind every domain that has a registered service, so
a name registered under a domain with no installed integration makes
``async_get_all_descriptions`` log

    Failed to load services.yaml for integration: smart_irrigation
    homeassistant.loader.IntegrationNotFound

at ERROR on every start, for the rest of the compatibility layer's life --
reported by a user who had completed the migration exactly as documented
(#130). Seeding the description cache ourselves means the lookup never happens,
and as a side effect the old names stop appearing in the Actions UI with no
description and no target selector.

The alias list is READ BACK from what we registered rather than restated here.
A hand-maintained second list would drift the first time somebody adds a
service and forgets, and the failure would be invisible until a user's
automation hit the missing name.

Deprecation is logged once per service, on first use, at WARNING — enough for a
user to find and fix their automations, quiet enough not to spam a log every
time a schedule fires.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.service import async_set_service_schema
from homeassistant.util.yaml import load_yaml_dict

from . import const

# Our own services.yaml, read once per registration to build the aliases'
# descriptions. Reading OUR file rather than calling async_get_all_descriptions
# is deliberate: that helper walks every integration on the machine, and -- on
# the first call after we register -- would trigger the very IntegrationNotFound
# lookup these descriptions exist to prevent.
_SERVICES_YAML = Path(__file__).parent / "services.yaml"

# Appended to each alias's description, where a user reading the Actions UI will
# actually see it. The log warning fires once per service per run and only when
# the service is CALLED; somebody browsing the action list sees neither.
_DEPRECATION_NOTE = (
    "Deprecated: this is the pre-rename name of {domain}.{name} and forwards to "
    "it. Update your automations and scripts -- this alias will be removed in a "
    "future release."
)

_LOGGER = logging.getLogger(__name__)

# Services we have already warned about, so the warning is one per service per
# Home Assistant run rather than one per call.
_WARNED: set[str] = set()

# The forwarders WE registered under the old domain, name -> handler.
#
# The handler, not just the name: "it exists under the old domain and we have
# one by that name" is a different question, and answering it that way would
# tear down a foreign integration's own services on our unload -- both projects
# publish `reset_bucket`. Keeping the object lets removal check identity, so a
# name that has since been taken over by somebody else is left alone.
_ALIASED: dict[str, object] = {}


def plan_service_aliases(ours, existing_legacy) -> list[str]:
    """Which of our service names should be mirrored onto the old domain.

    Pure so it can be exercised without a running Home Assistant. ``ours`` and
    ``existing_legacy`` are the service names registered under the new and the
    old domain respectively.

    A name already present under the old domain is skipped: registering over it
    would silently replace whatever owns it (an upstream install, or our own
    alias from a previous setup) and there is no error to notice.
    """
    return sorted(set(ours) - set(existing_legacy))


def plan_alias_description(name: str, entry: Any) -> dict:
    """The description dict to publish for one alias. Pure.

    ``entry`` is this service's block from our ``services.yaml`` (or anything
    else, including None -- a hand-edited or truncated file must not cost the
    user their aliases). Only the keys Home Assistant's own builder carries over
    are kept, so an alias reads in the Actions UI exactly like the real service
    it forwards to, with the deprecation said where it is visible.

    A description is returned even for a service the YAML does not mention: the
    point is to leave NO name under the old domain without a cached description,
    because a single missing one is enough to trigger the integration lookup.
    """
    entry = entry if isinstance(entry, dict) else {}
    note = _DEPRECATION_NOTE.format(domain=const.DOMAIN, name=name)
    described = str(entry.get("description") or "").strip()

    out: dict[str, Any] = {
        "name": str(entry.get("name") or name),
        "description": f"{described} {note}".strip() if described else note,
        "fields": entry.get("fields") or {},
    }
    # Only when the real service has one: an empty target would render a
    # picker that selects nothing.
    if entry.get("target"):
        out["target"] = entry["target"]
    return out


def _read_services_yaml() -> dict:
    """Our own services.yaml as a dict. Never raises.

    Blocking file read -- callers must hand it to an executor. Best-effort like
    the rest of this module: without it the aliases lose their descriptions,
    which is worth strictly less than the aliases themselves.
    """
    try:
        return load_yaml_dict(_SERVICES_YAML)
    except Exception as err:  # noqa: BLE001 - a missing description is not fatal
        _LOGGER.debug(
            "Could not read %s for alias descriptions: %s", _SERVICES_YAML, err
        )
        return {}


def _registered_target(entry: object) -> object:
    """The callable behind whatever the service registry stored under a name.

    ``hass.services.async_services()`` does NOT hand back the function that was
    passed to ``async_register``: Home Assistant wraps it in a ``Service`` whose
    ``job.target`` is the original. Comparing the wrapper against the function
    is therefore always False -- which is exactly what the removal below used to
    do, so from the day it shipped it removed nothing at all and the module's
    own "aliases are removed on unload" promise was never kept.

    Falls back to the object itself so a registry that stores plain callables
    still compares correctly.
    """
    job = getattr(entry, "job", None)
    return getattr(job, "target", entry)


def _service_names(hass: HomeAssistant, domain: str) -> list[str]:
    """Service names registered under ``domain``, or [] if there are none."""
    return list((hass.services.async_services() or {}).get(domain, {}) or {})


async def async_register_legacy_service_aliases(hass: HomeAssistant) -> list[str]:
    """Mirror ``irrigation_plus.*`` onto ``smart_irrigation.*``.

    Returns the aliased service names. Never raises: a missing alias costs a
    user their automations, but failing setup over one costs them the whole
    integration.
    """
    from .migrate_domain import foreign_legacy_install

    if await hass.async_add_executor_job(foreign_legacy_install, hass):
        _LOGGER.debug(
            "A different %s integration is installed; not aliasing its services",
            const.LEGACY_DOMAIN,
        )
        return []

    aliased = plan_service_aliases(
        _service_names(hass, const.DOMAIN),
        _service_names(hass, const.LEGACY_DOMAIN),
    )
    if not aliased:
        return []

    descriptions = await hass.async_add_executor_job(_read_services_yaml)
    for name in aliased:
        handler = _make_forwarder(hass, name)
        hass.services.async_register(const.LEGACY_DOMAIN, name, handler)
        _ALIASED[name] = handler
        # AFTER the register: async_set_service_schema reads supports_response
        # off the registered service, so the name has to exist first.
        async_set_service_schema(
            hass,
            const.LEGACY_DOMAIN,
            name,
            plan_alias_description(name, descriptions.get(name)),
        )

    _LOGGER.info(
        "Registered %s compatibility service(s) under %s.* so automations "
        "written before the rename keep working. Repoint them at %s.* — the "
        "aliases will be removed in a future release",
        len(aliased),
        const.LEGACY_DOMAIN,
        const.DOMAIN,
    )
    return aliased


def _make_forwarder(hass: HomeAssistant, name: str):
    """Build the handler that forwards one legacy service call to the real one."""

    async def _forward(call: ServiceCall) -> None:
        if name not in _WARNED:
            _WARNED.add(name)
            _LOGGER.warning(
                "%s.%s is the pre-rename name and is kept only for "
                "compatibility. Update your automations and scripts to call "
                "%s.%s instead",
                const.LEGACY_DOMAIN,
                name,
                const.DOMAIN,
                name,
            )
        # blocking=True so a caller that sequences on this service still gets
        # the ordering it had before the rename, and so an error raised by the
        # real handler propagates to the automation instead of vanishing into a
        # background task.
        await hass.services.async_call(
            const.DOMAIN,
            name,
            dict(call.data),
            blocking=True,
            context=call.context,
        )

    return _forward


def async_remove_legacy_service_aliases(hass: HomeAssistant) -> None:
    """Drop the aliases again on unload.

    Only the forwarders this module registered are removed, matched by identity
    rather than by name. A service under the old domain that belongs to a real
    integration must survive our unload — it was never ours, and removing it
    would break the OTHER project rather than tidy up after this one. Name is
    not enough to tell them apart: both projects publish ``reset_bucket``, and
    ``async_register`` overwrites silently, so the thing sitting under a name we
    once aliased may no longer be the thing we put there.
    """
    registered = (hass.services.async_services() or {}).get(const.LEGACY_DOMAIN, {})
    for name, handler in sorted(_ALIASED.items()):
        if _registered_target(registered.get(name)) is handler:
            hass.services.async_remove(const.LEGACY_DOMAIN, name)
    _ALIASED.clear()
    _WARNED.clear()


async def async_reclaim_legacy_service_names(hass: HomeAssistant) -> list[str]:
    """Take the old domain's service names over once its integration is gone.

    Called by the cleanup repair, straight after the legacy config entry is
    removed. Removing a config entry does NOT unregister the services its
    integration declared, and the pre-rename tree never called
    ``hass.services.async_remove`` for its own -- there are zero occurrences of
    it in ``v2026.09.06:custom_components/smart_irrigation/``. So all 24 names
    stay registered for the rest of the session, now bound to a torn-down
    coordinator whose storage file has just been deleted (#130).

    What the user sees until they restart is not uniform, which is what makes it
    hard to recognise: entity-targeted services resolve no state and silently
    do nothing, ``run_zone`` and ``stop_zone`` raise and abort the automation,
    and entity-less services run to completion against the dead coordinator's
    still-populated in-memory store.

    **Re-running the registration on its own fixes none of it, and looks
    entirely correct in a test with a clean registry**: the names are still
    taken, so ``plan_service_aliases`` returns ``[]`` and nothing happens. The
    stale names have to be removed first. That is the whole reason this is a
    separate function rather than a second call to the register above.

    Only ever call this on the path that has already established the legacy
    install was OURS (``async_cleanup_is_safe``). By the time it runs the
    directory is usually gone, so ``foreign_legacy_install`` can no longer tell
    us -- the ours-check belongs to the caller, before it deletes anything.
    """
    stale = _service_names(hass, const.LEGACY_DOMAIN)
    for name in stale:
        hass.services.async_remove(const.LEGACY_DOMAIN, name)
    _ALIASED.clear()

    aliased = await async_register_legacy_service_aliases(hass)
    if stale:
        _LOGGER.info(
            "Released %s service(s) left behind by the removed %s integration "
            "and re-registered %s of them as compatibility aliases",
            len(stale),
            const.LEGACY_DOMAIN,
            len(aliased),
        )
    return aliased
