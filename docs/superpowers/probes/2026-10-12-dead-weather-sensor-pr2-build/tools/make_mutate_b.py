"""Derive mutate-pr2b.py from mutate-pr2.py: re-anchor M12/M20 after the fix wave, add M23-M33."""

src = open("mutate-pr2.py", encoding="utf-8").read()


def rep(old, new):
    global src
    assert src.count(old) == 1, (src.count(old), old[:90])
    src = src.replace(old, new)


# M12: the gate's filter now calls cuts_field
rep(
    '''     "            if effective_aggregate(field, config) != const.MAPPING_CONF_AGGREGATE_DELTA\\n",''',
    '''     "            if cuts_field(field, config)\\n",''',
)
# M20: the notice key condition changed shape
rep(
    '''     "        if self._group_cuts(mapping):\\n"
     "            return const.ISSUE_WEATHER_SENSOR_STALE_PAUSED\\n",
     "        if False:\\n"
     "            return const.ISSUE_WEATHER_SENSOR_STALE_PAUSED\\n",''',
    '''     "        if self._group_cuts(mapping) and any(\\n",
     "        if False and any(\\n",''',
)

NEW = '''    (23, WS, "the mapping view defaults an omitted setting to pause",
     "        vol.Optional(const.MAPPING_ON_SILENT_SENSOR): vol.In(\\n",
     "        vol.Optional(\\n            const.MAPPING_ON_SILENT_SENSOR, default=const.ON_SILENT_SENSOR_PAUSE\\n        ): vol.In(\\n",
     "test_the_mapping_view_leaves_an_omitted_setting_omitted"),
    (24, LIVE, "_merged: touching spans stay apart",
     "        if merged and lo <= merged[-1][1]:\\n",
     "        if merged and lo < merged[-1][1]:\\n",
     "test_outages_whose_spans_touch_merge"),
    (25, CALC, "the gate ends an open outage after the commit's now",
     "                outages_of(mapping), watermark, now\\n",
     "                outages_of(mapping), watermark, now + timedelta(hours=1)\\n",
     "test_an_open_outage_blocks_up_to_the_commits_now"),
    (26, LIVE, "the notice ignores which fields are cut",
     "            cuts_field(field, config)\\n            for outage in outages\\n",
     "            True\\n            for outage in outages\\n",
     "test_a_silent_rain_gauge_alone_keeps_the_plain_notice"),
    (27, LIVE, "the warning claims a cut for every outage of a cutting group",
     "                    if cuts and any(cuts_field(f, config) for f in outage.fields)\\n",
     "                    if cuts\\n",
     "test_a_silent_rain_gauge_alone_keeps_the_plain_notice"),
    (28, INIT, "no re-sync of the notice when the group's mapping changes",
     "            if const.MAPPING_ON_SILENT_SENSOR in data or const.MAPPING_MAPPINGS in data:\\n",
     "            if const.MAPPING_ON_SILENT_SENSOR in data:\\n",
     "test_a_rain_gauge_turned_rain_rate_rewrites_the_open_notice"),
    (29, CALC, "a sliver of booked time reads 0 %",
     "            if share > 0:\\n                percent = max(percent, 1)\\n",
     "",
     "test_a_share_that_would_round_to_0_reads_1"),
    (30, CALC, "a two-minute cut reads 100 %",
     "            percent = min(percent, 99)\\n",
     "",
     "test_a_share_that_would_round_to_100_reads_99"),
    (31, AGG, "plain mean without a valid sample has no fallback",
     "            resultdata[key] = statistics.mean(values) if values else held[0]\\n",
     "            resultdata[key] = statistics.mean(values)\\n",
     "test_the_held_value_stands_in"),
    (32, AGG, "the other aggregates without a valid sample have no fallback",
     "    elif not values:\\n        resultdata[key] = held[0]\\n",
     "",
     "test_the_held_value_stands_in"),
    (33, LIVE, "cuts_field cuts a rain gauge too",
     "    return (\\n        effective_aggregate(field, mappings_config)\\n        != const.MAPPING_CONF_AGGREGATE_DELTA\\n    )\\n",
     "    return True\\n",
     "test_only_a_cumulative_rain_gauge_is_never_cut"),
    (34, LIVE, "a closed outage decides the notice text too",
     "            if outage.end is None\\n",
     "",
     "test_a_closed_temperature_outage_leaves_an_open_rain_gauge_plain"),
'''

marker = '''     "test_the_mapping_view_takes_the_setting_and_only_its_two_values"),
]
'''
rep(marker, marker[: -len("]\n")] + NEW + "]\n")
rep('mutations-pr2.json"', 'mutations-pr2b.json"')
open("mutate-pr2b.py", "w", encoding="utf-8", newline="\n").write(src)
print("ok")
