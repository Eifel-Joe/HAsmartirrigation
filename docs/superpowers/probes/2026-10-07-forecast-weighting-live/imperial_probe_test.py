"""Probe for Eifel-Joe#61 / E3: does the live path add a mm credit to an inch deficit?

forecast_weighting_credit returns rain.mm (calculation.py:1039-1137, no unit
conversion); the live path adds it to live_deficit, which is in DISPLAY units
(live_estimate.py:1353, :1607-1614): run sizing irrigation.py:2501, panel
live_estimate.py:1742-1744 -> _live_run_duration (:1637-1663).
"""
import sys
from types import SimpleNamespace

sys.path.insert(0, r"D:/Entwicklung/HASI/issue61-work/src-6a40e083")

from custom_components.irrigation_plus import const  # noqa: E402
from custom_components.irrigation_plus.duration_math import zone_run_duration  # noqa: E402
from custom_components.irrigation_plus.irrigation import IrrigationRunnerMixin  # noqa: E402
from custom_components.irrigation_plus.live_estimate import LiveEstimateMixin  # noqa: E402

CREDIT_MM = 5.08  # what forecast_weighting_credit hands over: millimetres


def zone(bucket):
    return {
        const.ZONE_ID: 1,
        const.ZONE_THROUGHPUT: 1.0,
        const.ZONE_SIZE: 10.0,
        const.ZONE_MULTIPLIER: 1.0,
        const.ZONE_MAXIMUM_DURATION: None,  # no cap: a capped control would pass trivially
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


def test_control_metric_panel_and_run_agree_with_the_mm_credit():
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
