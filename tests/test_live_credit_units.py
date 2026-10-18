"""The live path folds the forecast credit (mm) into a deficit in display units (#195).

``forecast_weighting_credit`` always returns millimetres; the live deficit is in
inches on an imperial install. Both live consumers -- the runner's
``_zone_run_decision`` and the panel's ``_live_run_duration`` -- used to add the
two unconverted, so 0.5 mm of forecast rain cancelled a 0.5 in (12.7 mm)
deficit and the zone dropped out of the run. The three issue tests are the
reporter's (Eifel-Joe), kept as filed.

Zone: 10 m^2 or 10 sq ft, 1 l/min or 1 gal/min, no maximum duration (so a
capped run cannot pass by accident), credit 5.08 mm = 0.2 in.
"""

from types import SimpleNamespace

import pytest

from custom_components.irrigation_plus import const
from custom_components.irrigation_plus.duration_math import (
    forecast_sized_deficit,
    zone_run_duration,
)
from custom_components.irrigation_plus.irrigation import IrrigationRunnerMixin
from custom_components.irrigation_plus.live_estimate import LiveEstimateMixin

CREDIT_MM = 5.08  # forecast_weighting_credit returns millimetres


def zone(bucket):
    return {
        const.ZONE_ID: 1,
        const.ZONE_THROUGHPUT: 1.0,
        const.ZONE_SIZE: 10.0,
        const.ZONE_MULTIPLIER: 1.0,
        const.ZONE_MAXIMUM_DURATION: None,
        const.ZONE_LEAD_TIME: 0,
        const.ZONE_BUCKET_THRESHOLD: 0,
        const.ZONE_BUCKET: bucket,
        const.ZONE_DURATION: 100,
    }


def runner():
    return SimpleNamespace(
        store=SimpleNamespace(config=SimpleNamespace(live_estimate_enabled=True)),
        _duration_for_deficit=lambda z, d, m: zone_run_duration(z, d, m),
    )


def test_metric_panel_and_run_agree_with_the_mm_credit():
    z = zone(-12.7)
    expected = zone_run_duration(z, -12.7 + CREDIT_MM, True)
    assert expected > 0
    assert LiveEstimateMixin._live_run_duration(z, -12.7, True, CREDIT_MM) == expected
    d = IrrigationRunnerMixin._zone_run_decision(
        runner(), z, {"1": {"live_deficit": -12.7}}, True, credit=CREDIT_MM
    )
    assert d is not None and d.duration == expected


def test_imperial_panel_credits_the_forecast_in_the_deficits_unit():
    z = zone(-0.5)
    expected = zone_run_duration(z, -0.5 + CREDIT_MM / const.INCH_TO_MM_FACTOR, False)
    assert expected > 0
    assert LiveEstimateMixin._live_run_duration(z, -0.5, False, CREDIT_MM) == expected


def test_imperial_run_credits_the_forecast_in_the_deficits_unit():
    z = zone(-0.5)
    expected = zone_run_duration(z, -0.5 + CREDIT_MM / const.INCH_TO_MM_FACTOR, False)
    d = IrrigationRunnerMixin._zone_run_decision(
        runner(), z, {"1": {"live_deficit": -0.5}}, False, credit=CREDIT_MM
    )
    assert d is not None, "zone dropped: the mm credit covered the inch deficit"
    assert d.duration == expected


@pytest.mark.parametrize("deficit", [-0.5, -0.2, -0.15, -0.01])
def test_imperial_panel_and_run_state_the_same_duration(deficit):
    """The screen quotes the run that happens, on imperial too.

    Deficits on both sides of the 0.2 in credit: one the credit only shortens,
    one it exactly covers, and ones it more than covers (the zone drops, and the
    panel must then quote 0 s, not a run).
    """
    z = zone(deficit)
    panel = LiveEstimateMixin._live_run_duration(z, deficit, False, CREDIT_MM)
    d = IrrigationRunnerMixin._zone_run_decision(
        runner(), z, {"1": {"live_deficit": deficit}}, False, credit=CREDIT_MM
    )
    assert panel == (0 if d is None else d.duration)


def test_the_credit_shortens_the_imperial_run_by_its_inches():
    """0.2 in of credit on a 0.5 in deficit sizes a 0.3 in run, to the second."""
    z = zone(-0.5)
    assert LiveEstimateMixin._live_run_duration(
        z, -0.5, False, CREDIT_MM
    ) == zone_run_duration(z, -0.3, False)


@pytest.mark.parametrize("metric", [True, False])
def test_no_credit_leaves_the_deficit_untouched(metric):
    assert forecast_sized_deficit(-0.5, 0.0, metric) == -0.5
    assert forecast_sized_deficit(-0.5, None, metric) == -0.5
    assert forecast_sized_deficit(-0.5, -1.0, metric) == -0.5


@pytest.mark.parametrize("metric", [True, False])
def test_a_credit_never_lifts_the_deficit_above_zero(metric):
    assert forecast_sized_deficit(-0.1, 100.0, metric) == 0.0
