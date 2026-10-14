"""The live path adds the forecast credit (mm) to the live deficit (display units)."""

from types import SimpleNamespace

from custom_components.irrigation_plus import const
from custom_components.irrigation_plus.duration_math import zone_run_duration
from custom_components.irrigation_plus.irrigation import IrrigationRunnerMixin
from custom_components.irrigation_plus.live_estimate import LiveEstimateMixin

CREDIT_MM = 5.08  # forecast_weighting_credit returns millimetres


def zone(bucket):
    return {
        const.ZONE_ID: 1,
        const.ZONE_THROUGHPUT: 1.0,
        const.ZONE_SIZE: 10.0,
        const.ZONE_MULTIPLIER: 1.0,
        const.ZONE_MAXIMUM_DURATION: None,  # no cap, so a capped run cannot pass by accident
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
