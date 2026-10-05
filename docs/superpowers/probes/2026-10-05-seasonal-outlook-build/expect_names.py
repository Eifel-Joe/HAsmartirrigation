"""Check a full-suite run after task N against the baseline, by name and by count.

run_suite.sh <tag> writes ../suite-<tag>.txt and ../names-<tag>.txt. After task N
the only new FAILED/ERROR names may be the new tests on the coordinator fixture
added up to task N (each one ERRORs at teardown locally, "Lingering timer"); no
baseline name may be gone. The counts follow from the baseline 7/3667/9/415.

Usage: python expect_names.py <tag> <N>
"""

import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
CAL = "tests/test_watering_calendar.py::"
PRICED = CAL + "TestAMonthIsPricedByTheCalculationsRules::"
CLIMATE = CAL + "TestTheClimateCurvesDoWhatTheirCommentsSay::"
SAYS = CAL + "TestTheOutlookSaysWhatItIs::"

# task -> (new tests on the coordinator fixture, new tests without it)
NEW = {
    1: ([PRICED + "test_a_pyeto_month_carries_no_rain",
         PRICED + "test_a_pyeto_zone_has_the_rain_subtracted_once"], []),
    2: ([PRICED + "test_kc_scales_the_et_term_and_not_the_rain",
         PRICED + "test_a_zone_whose_kc_is_none_reads_as_the_default",
         PRICED + "test_a_module_without_rain_gets_none_subtracted"], []),
    3: ([PRICED + "test_a_static_demand_becomes_a_monthly_volume",
         PRICED + "test_a_static_surplus_needs_nothing"], []),
    4: ([PRICED + "test_a_passthrough_month_has_its_own_number_of_days"], []),
    5: ([CLIMATE + "test_a_northern_winter_is_wetter_windier_and_more_humid",
         CLIMATE + "test_the_southern_hemisphere_mirrors_every_temperate_curve",
         CLIMATE + "test_tropical_rain_keeps_its_curve"], []),
    6: ([SAYS + "test_each_month_notes_its_climate_comes_from_latitude"], []),
    7: ([], [SAYS + "test_the_service_description_says_where_the_climate_comes_from"]),
    8: ([], [SAYS + "test_the_seasonal_card_shows_the_illustration_note"]),
    9: ([], []),
}
BASE = (7, 3667, 9, 415)


def main():
    tag, n = sys.argv[1], int(sys.argv[2])
    fixture = [t for k in range(1, n + 1) for t in NEW[k][0]]
    plain = [t for k in range(1, n + 1) for t in NEW[k][1]]
    want_added = {f"ERROR {t}" for t in fixture}
    base = set((HERE / "names-base.txt").read_text().split("\n")) - {""}
    now = set((HERE / f"names-{tag}.txt").read_text().split("\n")) - {""}
    added, gone = now - base, base - now
    problems = []
    if added != want_added:
        problems.append(f"ADDED unexpected: {sorted(added - want_added)}")
        problems.append(f"ADDED missing: {sorted(want_added - added)}")
    if gone:
        problems.append(f"GONE: {sorted(gone)}")

    suite = (HERE / f"suite-{tag}.txt").read_text(encoding="utf-8", errors="replace")
    tail = suite.replace("\r", "\n").strip().splitlines()[-1]
    got = tuple(int(m.group(1)) if (m := re.search(rf"(\d+) {w}", tail)) else 0
                for w in ("failed", "passed", "skipped", "error"))
    want = (BASE[0], BASE[1] + len(fixture) + len(plain), BASE[2], BASE[3] + len(fixture))
    if got != want:
        problems.append(f"COUNTS {got} != expected {want}")

    teardown_new = [t for t in fixture
                    if re.search(rf"ERROR at teardown of {re.escape(t.split('::', 1)[1].replace('::', '.'))}",
                                 suite)]
    if len(teardown_new) != len(fixture):
        problems.append(f"TEARDOWN: only {len(teardown_new)}/{len(fixture)} new names ERROR at teardown")

    print(f"{tag} after task {n}: {tail}")
    print(f"expected f/p/s/e {want}; added {len(added)} (want {len(want_added)}), gone {len(gone)}")
    for p in problems:
        print(p)
    print("NAMES CHECK", "OK" if not problems else f"{len(problems)} PROBLEM(S)")


if __name__ == "__main__":
    main()
