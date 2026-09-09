"""Removing the pre-#120 install for the user: the repair behind #120's cleanup.

The order is the whole design, and it is not cosmetic. Home Assistant can only
run an integration's own `async_remove_entry` while it can still import it, so
the config entry has to go BEFORE the directory. Reversed, the entry becomes
something Home Assistant cannot clean up -- an orphaned entry beside an orphaned
storage file, which is exactly the state that made v2026.09.07's failed setups
unrecoverable.
"""

import json
from types import SimpleNamespace

import pytest

from custom_components.irrigation_plus import const, legacy_services
from custom_components.irrigation_plus.migrate_domain import (
    BRIDGE_VERSION,
    async_bridge_status,
    async_cleanup_is_safe,
    async_delete_legacy_directory,
    async_remove_legacy_entry,
    async_report_bridge_status,
    came_from_bridge,
    cleanup_is_safe,
    legacy_directory,
    parse_version,
    storage_path,
)
from custom_components.irrigation_plus.repairs import LeftoverInstallRepairFlow


@pytest.fixture(autouse=True)
def _clean_alias_state():
    """Alias bookkeeping is module-level; one test must not decide the next."""
    legacy_services._ALIASED.clear()
    legacy_services._WARNED.clear()
    yield
    legacy_services._ALIASED.clear()
    legacy_services._WARNED.clear()


OUR_MANIFEST = {
    "domain": const.LEGACY_DOMAIN,
    "documentation": "https://github.com/JustChr/HAsmartirrigation",
    "codeowners": ["@JustChr"],
}
THEIR_MANIFEST = {
    "domain": const.LEGACY_DOMAIN,
    "documentation": "https://github.com/altmenorg/HAsmartirrigation",
    "codeowners": ["@altmenorg"],
}


class _Service:
    """Home Assistant stores a wrapper, not the handler. Mirror that."""

    def __init__(self, func):
        self.job = SimpleNamespace(target=func)


class _Services:
    """Enough of hass.services for the reclaim step."""

    def __init__(self, registry=None):
        self._registry = {
            d: {n: _Service(h) for n, h in s.items()}
            for d, s in (registry or {}).items()
        }

    def async_services(self):
        return {d: dict(s) for d, s in self._registry.items()}

    def has_service(self, domain, service):
        return service in self._registry.get(domain, {})

    def async_register(self, domain, service, handler):
        self._registry.setdefault(domain, {})[service] = _Service(handler)

    def async_remove(self, domain, service):
        self._registry.get(domain, {}).pop(service, None)

    def supports_response(self, domain, service):
        from homeassistant.core import SupportsResponse

        return SupportsResponse.NONE

    async def async_call(self, domain, service, data, blocking=False, context=None):
        return None


def _hass(tmp_path, entries=(), removed=None, services=None):
    """A hass double with a real config dir and a recording entry remover."""
    (tmp_path / ".storage").mkdir(parents=True, exist_ok=True)

    async def _executor(func, *args):
        return func(*args)

    async def _async_remove(entry_id):
        if removed is not None:
            removed.append(entry_id)

    return SimpleNamespace(
        config=SimpleNamespace(
            path=lambda *parts: str(tmp_path.joinpath(*parts)),
            components=set(),
        ),
        config_entries=SimpleNamespace(
            async_entries=lambda domain: (
                list(entries) if domain == const.LEGACY_DOMAIN else []
            ),
            async_remove=_async_remove,
        ),
        # The repair reclaims the old domain's service names once its entry is
        # gone (#130): removing a config entry does not unregister the services
        # its integration declared, and the pre-rename tree never removed its
        # own, so without this they stay bound to a torn-down coordinator until
        # the next restart.
        services=services if services is not None else _Services(),
        data={},
        async_add_executor_job=_executor,
    )


def _install(tmp_path, manifest=OUR_MANIFEST):
    directory = tmp_path / "custom_components" / const.LEGACY_DOMAIN
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (directory / "__init__.py").write_text("# code\n", encoding="utf-8")
    return directory


def _our_store(hass, zones):
    storage_path(hass).write_text(
        json.dumps({"version": 14, "data": {"config": {}, "zones": zones}}),
        encoding="utf-8",
    )


class TestCleanupIsSafe:
    """Both gates guard something irreplaceable."""

    def test_ours_with_zones_is_safe(self):
        assert cleanup_is_safe(True, 3) is True

    def test_a_foreign_install_is_never_touched(self):
        """That directory is a different, working integration."""
        assert cleanup_is_safe(False, 3) is False

    def test_no_zones_means_the_migration_did_not_land(self):
        """Removing the old entry deletes the only full copy of their config."""
        assert cleanup_is_safe(True, 0) is False

    def test_an_unknown_zone_count_is_refused(self):
        """None is 'unreadable', not 'empty' -- refuse, as the import does."""
        assert cleanup_is_safe(True, None) is False

    async def test_against_the_live_filesystem(self, tmp_path):
        hass = _hass(tmp_path)
        _install(tmp_path)
        _our_store(hass, {"1": {"name": "Lawn"}})
        assert await async_cleanup_is_safe(hass) is True

    async def test_against_the_live_filesystem_when_empty(self, tmp_path):
        hass = _hass(tmp_path)
        _install(tmp_path)
        _our_store(hass, {})
        assert await async_cleanup_is_safe(hass) is False


class TestRemovingTheEntry:
    async def test_removes_the_legacy_entry(self, tmp_path):
        removed = []
        entry = SimpleNamespace(entry_id="legacy1", data={}, options={})
        hass = _hass(tmp_path, entries=[entry], removed=removed)

        assert await async_remove_legacy_entry(hass) is True
        assert removed == ["legacy1"]

    async def test_no_entry_is_not_an_error(self, tmp_path):
        removed = []
        hass = _hass(tmp_path, removed=removed)

        assert await async_remove_legacy_entry(hass) is False
        assert removed == []


class TestDeletingTheDirectory:
    async def test_deletes_our_own_leftover(self, tmp_path):
        hass = _hass(tmp_path)
        directory = _install(tmp_path)

        assert await async_delete_legacy_directory(hass) is True
        assert not directory.exists()

    async def test_refuses_a_foreign_install(self, tmp_path):
        """The gate is re-checked here, not trusted from the caller."""
        hass = _hass(tmp_path)
        directory = _install(tmp_path, THEIR_MANIFEST)

        assert await async_delete_legacy_directory(hass) is False
        assert (directory / "__init__.py").is_file()

    async def test_a_missing_directory_is_not_an_error(self, tmp_path):
        assert await async_delete_legacy_directory(_hass(tmp_path)) is False

    async def test_a_permission_error_does_not_raise(self, tmp_path):
        hass = _hass(tmp_path)
        _install(tmp_path)

        async def _boom(func, *args):
            raise OSError("permission denied")

        hass.async_add_executor_job = _boom
        assert await async_delete_legacy_directory(hass) is False


class TestTheRepairFlow:
    def _flow(self, hass):
        flow = LeftoverInstallRepairFlow()
        flow.hass = hass
        return flow

    def _ready(self, tmp_path, removed):
        entry = SimpleNamespace(entry_id="legacy1", data={}, options={})
        hass = _hass(tmp_path, entries=[entry], removed=removed)
        _install(tmp_path)
        _our_store(hass, {"1": {"name": "Lawn"}})
        return hass

    async def test_the_confirm_step_names_what_will_be_deleted(self, tmp_path):
        hass = self._ready(tmp_path, [])
        result = await self._flow(hass).async_step_confirm()

        assert result["type"] == "form"
        assert result["step_id"] == "confirm"
        placeholders = result["description_placeholders"]
        assert placeholders["path"] == str(legacy_directory(hass))
        assert placeholders["name"] == const.LEGACY_NAME

    async def test_the_entry_goes_before_the_directory(self, tmp_path):
        """The invariant. Reversed, Home Assistant cannot tear the old one down.

        Recorded as one ordered list so the assertion is about SEQUENCE, not
        merely about both things having happened.
        """
        order = []
        entry = SimpleNamespace(entry_id="legacy1", data={}, options={})
        hass = _hass(tmp_path, entries=[entry])
        directory = _install(tmp_path)
        _our_store(hass, {"1": {"name": "Lawn"}})

        async def _remove(entry_id):
            order.append(f"entry:{entry_id}")

        hass.config_entries.async_remove = _remove

        inner = hass.async_add_executor_job

        async def _watch(func, *args):
            result = await inner(func, *args)
            if not directory.exists() and "directory" not in "".join(order):
                order.append("directory")
            return result

        hass.async_add_executor_job = _watch

        result = await self._flow(hass).async_step_confirm(user_input={})

        assert order == ["entry:legacy1", "directory"]
        assert result["step_id"] == "done"
        assert not directory.exists()

    async def test_a_surviving_directory_is_reported_not_celebrated(
        self, tmp_path, monkeypatch
    ):
        """A flow that closes on a success it did not earn leaves duplicates.

        The cleanup is safe and the entry DOES go; only the delete fails, which
        in the field means a file permission the container cannot get past.
        """
        removed = []
        hass = self._ready(tmp_path, removed)

        def _denied(path):
            raise OSError("permission denied")

        monkeypatch.setattr(
            "custom_components.irrigation_plus.migrate_domain.shutil.rmtree", _denied
        )

        result = await self._flow(hass).async_step_confirm(user_input={})

        assert result["step_id"] == "partial"
        assert result["description_placeholders"]["path"] == str(legacy_directory(hass))
        # The entry still went: that half succeeded and must not be re-run.
        assert removed == ["legacy1"]

    async def test_it_refuses_when_the_migration_no_longer_looks_complete(
        self, tmp_path
    ):
        """Re-checked at execution: the issue was raised at setup, long before."""
        removed = []
        entry = SimpleNamespace(entry_id="legacy1", data={}, options={})
        hass = _hass(tmp_path, entries=[entry], removed=removed)
        directory = _install(tmp_path)
        _our_store(hass, {})  # emptied since the issue was raised

        result = await self._flow(hass).async_step_confirm(user_input={})

        assert result["step_id"] == "unsafe"
        assert removed == []
        assert (directory / "__init__.py").is_file()

    @pytest.mark.parametrize("step", ["done", "partial", "unsafe"])
    async def test_every_outcome_step_can_be_closed(self, tmp_path, step):
        hass = self._ready(tmp_path, [])
        flow = self._flow(hass)
        result = await getattr(flow, f"async_step_{step}")(user_input={})
        assert result["type"] == "create_entry"


class TestBridgeDetection:
    """Did the install we are migrating from ever run the bridge release?

    It decides what to tell a user about credentials, so "cannot tell" must stay
    distinct from "no": only a KNOWN pre-bridge version justifies warning that
    nothing was staged.
    """

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("v2026.09.06", (2026, 9, 6)),
            ("2026.09.06", (2026, 9, 6)),
            ("v2026.10.00", (2026, 10, 0)),
            ("V2026.09.06", (2026, 9, 6)),
            ("  v2026.09.06  ", (2026, 9, 6)),
        ],
    )
    def test_parses_the_scheme(self, value, expected):
        assert parse_version(value) == expected

    @pytest.mark.parametrize(
        "value",
        [
            "",
            "latest",
            "1.2",
            "2026.09",
            "v2026.09.06.1",
            None,
            20260906,
            "vYYYY.MM.NN",
            "2026.09.xx",
        ],
    )
    def test_anything_else_is_unknown(self, value):
        assert parse_version(value) is None

    def test_the_bridge_itself_counts(self):
        assert came_from_bridge("v2026.09.06") is True

    def test_a_later_release_counts(self):
        """The bridge was the last on the old domain, but be ordering-correct."""
        assert came_from_bridge("v2026.09.07") is True
        assert came_from_bridge("v2026.10.01") is True

    @pytest.mark.parametrize("value", ["v2026.09.05", "v2026.08.18", "v2025.12.01"])
    def test_earlier_releases_do_not(self, value):
        assert came_from_bridge(value) is False

    def test_an_unreadable_version_is_unknown_not_false(self):
        assert came_from_bridge(None) is None
        assert came_from_bridge("garbage") is None

    async def test_reads_the_version_from_the_leftover_manifest(self, tmp_path):
        hass = _hass(tmp_path)
        _install(tmp_path, {**OUR_MANIFEST, "version": "v2026.09.06"})

        status = await async_bridge_status(hass)

        assert status == {"legacy_version": "v2026.09.06", "came_from_bridge": True}

    async def test_a_pre_bridge_install_is_reported_as_such(self, tmp_path):
        hass = _hass(tmp_path)
        _install(tmp_path, {**OUR_MANIFEST, "version": "v2026.08.18"})

        status = await async_bridge_status(hass)

        assert status == {"legacy_version": "v2026.08.18", "came_from_bridge": False}

    async def test_a_missing_directory_is_unknown(self, tmp_path):
        assert await async_bridge_status(_hass(tmp_path)) == {
            "legacy_version": None,
            "came_from_bridge": None,
        }

    async def test_a_manifest_without_a_version_is_unknown(self, tmp_path):
        hass = _hass(tmp_path)
        _install(tmp_path, OUR_MANIFEST)  # no version key
        assert (await async_bridge_status(hass))["came_from_bridge"] is None

    async def test_the_warning_names_the_bridge_and_the_order(self, tmp_path, caplog):
        """The warning is only actionable BEFORE the old integration is removed."""
        hass = _hass(tmp_path)
        _install(tmp_path, {**OUR_MANIFEST, "version": "v2026.08.18"})

        with caplog.at_level("INFO"):
            await async_report_bridge_status(hass)

        text = caplog.text
        assert BRIDGE_VERSION in text
        assert "v2026.08.18" in text
        assert "do NOT remove the old integration" in text

    async def test_a_bridged_install_does_not_warn(self, tmp_path, caplog):
        hass = _hass(tmp_path)
        _install(tmp_path, {**OUR_MANIFEST, "version": "v2026.09.06"})

        with caplog.at_level("INFO"):
            await async_report_bridge_status(hass)

        assert "do NOT remove" not in caplog.text
        assert "staged for this migration" in caplog.text


class TestTheRepairReclaimsTheOldServiceNames:
    """#130: the entry goes, its 24 services do not.

    Removing a config entry does not unregister the services its integration
    declared, and the pre-rename tree never called `hass.services.async_remove`
    for its own -- so until the next restart every `smart_irrigation.*` name is
    still there, now bound to a torn-down coordinator whose storage file has
    just been deleted. What the user sees is not uniform, which is what makes
    it hard to recognise: entity-targeted services silently no-op, `run_zone`
    raises and aborts the automation.
    """

    def _flow(self, hass):
        flow = LeftoverInstallRepairFlow()
        flow.hass = hass
        return flow

    def _ready(self, tmp_path, services):
        entry = SimpleNamespace(entry_id="legacy1", data={}, options={})
        hass = _hass(tmp_path, entries=[entry], services=services)
        _install(tmp_path)
        _our_store(hass, {"1": {"name": "Lawn"}})
        return hass

    async def test_the_dead_handlers_are_replaced_by_live_forwarders(self, tmp_path):
        dead = object()
        services = _Services(
            {
                const.DOMAIN: {"reset_bucket": object(), "run_zone": object()},
                const.LEGACY_DOMAIN: {"reset_bucket": dead, "run_zone": dead},
            }
        )
        hass = self._ready(tmp_path, services)

        result = await self._flow(hass).async_step_confirm(user_input={})

        assert result["step_id"] == "done"
        legacy = services.async_services()[const.LEGACY_DOMAIN]
        assert set(legacy) == {"reset_bucket", "run_zone"}
        for name in legacy:
            assert legacy[name].job.target is not dead

    async def test_it_happens_on_the_partial_path_too(self, tmp_path):
        """A directory that could not be deleted leaves the same dead services."""
        dead = object()
        services = _Services(
            {
                const.DOMAIN: {"reset_bucket": object()},
                const.LEGACY_DOMAIN: {"reset_bucket": dead},
            }
        )
        hass = self._ready(tmp_path, services)

        inner = hass.async_add_executor_job

        async def _fail_the_delete(func, *args):
            if "delete" in getattr(func, "__name__", "").lower():
                raise OSError("permission denied")
            return await inner(func, *args)

        hass.async_add_executor_job = _fail_the_delete

        result = await self._flow(hass).async_step_confirm(user_input={})

        assert result["step_id"] == "partial"
        legacy = services.async_services()[const.LEGACY_DOMAIN]
        assert legacy["reset_bucket"].job.target is not dead

    async def test_a_refused_cleanup_leaves_the_old_services_alone(self, tmp_path):
        """`unsafe` removed nothing, so there is nothing dead to reclaim.

        Taking the names here would strip a still-running integration of its
        services on the strength of a repair that deliberately did nothing.
        """
        alive = object()
        services = _Services(
            {
                const.DOMAIN: {"reset_bucket": object()},
                const.LEGACY_DOMAIN: {"reset_bucket": alive},
            }
        )
        entry = SimpleNamespace(entry_id="legacy1", data={}, options={})
        hass = _hass(tmp_path, entries=[entry], services=services)
        _install(tmp_path)
        _our_store(hass, {})  # no zones -> the migration does not look complete

        result = await self._flow(hass).async_step_confirm(user_input={})

        assert result["step_id"] == "unsafe"
        assert (
            services.async_services()[const.LEGACY_DOMAIN]["reset_bucket"].job.target
            is alive
        )
