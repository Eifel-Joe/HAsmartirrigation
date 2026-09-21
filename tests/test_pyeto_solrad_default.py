"""The PyETO solar-radiation setting, in both the forms it really arrives in (#158).

``DEFAULT_SOLRAD_BEHAVIOR`` is an enum MEMBER; every branch that reads the
setting compares against ``.value`` strings. So the default matched nothing and
fell through to the implicit else -- ``EstimateFromSunHours`` -- while the
constant, the schema default and the panel dropdown all said EstimateFromTemp.

A fresh install is exactly that case rather than an edge one: the factory
``ModuleEntry`` is built with no ``MODULE_CONFIG``, so ``if config:`` in
``PyETO.__init__`` never runs. Anyone who assigned PyETO to a zone and never
opened the module settings computed from sun hours from day one.

These drive the real constructor and the real branch selection.
"""

from unittest.mock import MagicMock

import pytest

from custom_components.irrigation_plus.calcmodules.pyeto import (
    DEFAULT_SOLRAD_BEHAVIOR,
    PyETO,
    SOLRAD_behavior,
    solrad_behavior_value,
)
from custom_components.irrigation_plus.const import CONF_PYETO_SOLRAD_BEHAVIOR


def _hass():
    hass = MagicMock()
    hass.config.as_dict.return_value = {"latitude": 52.0, "elevation": 30.0}
    return hass


def _module(config):
    return PyETO(_hass(), description="", config=config)


class TestTheFactoryDefault:
    """What a zone gets when nobody has opened the module settings."""

    def test_a_fresh_install_estimates_from_temperature(self):
        """The whole issue: no MODULE_CONFIG at all, as store.py creates it.

        Before the fix this held the enum member, which equals none of the
        ``.value`` strings the branches test, so the calculation silently took
        the sun-hours else.
        """
        assert _module(None)._solrad_behavior == SOLRAD_behavior.EstimateFromTemp.value

    def test_an_empty_config_is_the_same_case(self):
        assert _module({})._solrad_behavior == SOLRAD_behavior.EstimateFromTemp.value

    def test_a_config_that_omits_the_setting_still_gets_the_default(self):
        """Setting forecast_days in the panel writes a config without this key.

        The dropdown meanwhile displays EstimateFromTemp, which it never saved --
        so before the fix the UI and the arithmetic disagreed and neither said so.
        """
        module = _module({"forecast_days": 2})
        assert module._solrad_behavior == SOLRAD_behavior.EstimateFromTemp.value

    def test_the_declared_default_is_what_actually_runs(self):
        """The constant and the behaviour must not be able to drift apart."""
        assert _module(None)._solrad_behavior == solrad_behavior_value(
            DEFAULT_SOLRAD_BEHAVIOR
        )


class TestBothStoredForms:
    """A bare string from the panel, an enum member from the default.

    Not from the schema: ``CalcModule.__init__`` discards what ``self._schema()``
    returns, so ``vol.Coerce`` validates without rewriting the config. The member
    form arrives via ``DEFAULT_SOLRAD_BEHAVIOR``. Both are accepted anyway, and
    both are driven here, because the setting has two legal spellings either way.
    """

    @pytest.mark.parametrize(
        "stored",
        [
            SOLRAD_behavior.DontEstimate,  # the member form
            SOLRAD_behavior.DontEstimate.value,  # straight from the panel select
            "3",
        ],
    )
    def test_dont_estimate_is_recognised_in_every_form(self, stored):
        module = _module({CONF_PYETO_SOLRAD_BEHAVIOR: stored})
        assert module._solrad_behavior == SOLRAD_behavior.DontEstimate.value

    @pytest.mark.parametrize(
        "behaviour",
        list(SOLRAD_behavior),
    )
    def test_every_member_normalises_to_its_own_value(self, behaviour):
        """Both spellings of the SAME setting must land on the same string.

        The mirror check: a member and its value are two forms of one choice, so
        a test that drove only one of them would not have caught the defect --
        the panel's string form worked the whole time.
        """
        as_member = _module({CONF_PYETO_SOLRAD_BEHAVIOR: behaviour})
        as_string = _module({CONF_PYETO_SOLRAD_BEHAVIOR: behaviour.value})
        assert (
            as_member._solrad_behavior == as_string._solrad_behavior == behaviour.value
        )

    def test_an_absent_setting_reads_as_the_default(self):
        """Driven at the helper, because the constructor cannot reach this.

        ``CalcModule.__init__`` validates against the schema, which rejects a
        None for this key outright -- so the None case only arrives through
        ``live_estimate``'s ``config.get(...)`` on a module whose config omits
        it. There the effective behaviour IS the default, which is what this
        pins; before the fix that site produced the string ``"None"``.
        """
        assert solrad_behavior_value(None) == SOLRAD_behavior.EstimateFromTemp.value


class TestTheBranchActuallySelected:
    """Normalising is only worth anything if it changes which branch runs."""

    @staticmethod
    def _branch(module):
        """Which arm of the solrad if/elif/else the stored value selects.

        Mirrors the predicates at the top of ``calculate_et_for_day`` rather
        than calling it, so the test states the mapping it is pinning instead of
        asserting a number that could come out right for the wrong reason.
        """
        b = module._solrad_behavior
        if b == SOLRAD_behavior.DontEstimate.value:
            return "measured"
        if b == SOLRAD_behavior.EstimateFromTemp.value:
            return "from_temp"
        if b == SOLRAD_behavior.EstimateFromSunHoursAndTemperature.value:
            return "sun_hours_and_temp"
        return "from_sun_hours"

    def test_the_default_install_no_longer_lands_in_the_sun_hours_else(self):
        assert self._branch(_module(None)) == "from_temp"

    @pytest.mark.parametrize(
        ("stored", "expected"),
        [
            (SOLRAD_behavior.EstimateFromTemp, "from_temp"),
            (SOLRAD_behavior.EstimateFromSunHours, "from_sun_hours"),
            (SOLRAD_behavior.DontEstimate, "measured"),
            (
                SOLRAD_behavior.EstimateFromSunHoursAndTemperature,
                "sun_hours_and_temp",
            ),
        ],
    )
    def test_each_choice_reaches_its_own_branch_as_a_member(self, stored, expected):
        """Before the fix EVERY one of these fell to ``from_sun_hours``."""
        assert self._branch(_module({CONF_PYETO_SOLRAD_BEHAVIOR: stored})) == expected
