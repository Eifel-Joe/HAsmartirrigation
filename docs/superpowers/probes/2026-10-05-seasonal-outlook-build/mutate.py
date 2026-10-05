"""Mutation run for the seasonal-outlook fix.

Each mutation undoes or bends one changed line; the calendar tests must fail
for every one of them. The file is restored after each run, also on timeout.

Usage: python mutate.py <worktree> <result.txt>
"""

import re
import subprocess
import sys
from pathlib import Path

PY = r"D:\Entwicklung\HASI\HAsmartirrigation\.venv\Scripts\python.exe"
CAL = "custom_components/irrigation_plus/watering_calendar.py"
EN = "custom_components/irrigation_plus/translations/en.json"
YAML = "custom_components/irrigation_plus/services.yaml"
VIEW = "custom_components/irrigation_plus/frontend/src/views/weather/view-weather-data.ts"
DE = "custom_components/irrigation_plus/translations/de.json"
NOTE_EN = "custom_components/irrigation_plus/frontend/localize/languages/en.json"
TIMEOUT = 300

MUTATIONS = [
    ("M01 PyETO ET carries rain again", CAL,
     "return abs(daily_et_delta) * days_in_month",
     'return (abs(daily_et_delta) + month_data["precipitation"] / days_in_month) * days_in_month'),
    ("M02 PyETO ET keeps the sign", CAL,
     "return abs(daily_et_delta) * days_in_month",
     "return daily_et_delta * days_in_month"),
    ("M03 PyETO month is 30 days", CAL,
     "days_in_month = calendar.monthrange(2024, month)[1]  # 2024: reference year",
     "days_in_month = 30"),
    ("M04 Kc ignored", CAL,
     "net_water_need_mm = max(0, et_mm * kc - precipitation_mm)",
     "net_water_need_mm = max(0, et_mm - precipitation_mm)"),
    ("M05 Kc scales the rain too", CAL,
     "net_water_need_mm = max(0, et_mm * kc - precipitation_mm)",
     "net_water_need_mm = max(0, (et_mm - precipitation_mm) * kc)"),
    ("M06 Kc None guard dropped", CAL,
     "        if kc is None:\n            kc = const.CONF_DEFAULT_KC\n",
     ""),
    ("M07 rain subtracted for every module", CAL,
     "if zone_module_models_weather(self.store, zone):",
     "if True:"),
    ("M08 rain never subtracted", CAL,
     "if zone_module_models_weather(self.store, zone):",
     "if False:"),
    ("M09 static sign flipped", CAL,
     "et_estimate = max(0.0, -modinst.calculate()) * days_in_month",
     "et_estimate = max(0.0, modinst.calculate()) * days_in_month"),
    ("M10 static surplus not clamped", CAL,
     "et_estimate = max(0.0, -modinst.calculate()) * days_in_month",
     "et_estimate = -modinst.calculate() * days_in_month"),
    ("M11 static month is 30 days", CAL,
     "et_estimate = max(0.0, -modinst.calculate()) * days_in_month",
     "et_estimate = max(0.0, -modinst.calculate()) * 30"),
    ("M12 passthrough month is 30 days", CAL,
     'month_data.get("average_daily_et", 3.0) * days_in_month',
     'month_data.get("average_daily_et", 3.0) * 30'),
    ("M13 loop month from a non-leap year", CAL,
     "days_in_month = calendar.monthrange(2024, month)[1]\n\n            try:",
     "days_in_month = calendar.monthrange(2023, month)[1]\n\n            try:"),
    ("M14 humidity peaks in summer", CAL,
     "humidity = 65.0 - 15.0 * summer",
     "humidity = 65.0 + 15.0 * summer"),
    ("M15 wind peaks in summer", CAL,
     "wind_speed = 3.0 - 1.0 * summer",
     "wind_speed = 3.0 + 1.0 * summer"),
    ("M16 temperate rain peaks in summer", CAL,
     "precip_factor = 1.5 - 0.5 * summer",
     "precip_factor = 1.5 + 0.5 * summer"),
    ("M17 hemisphere ignored", CAL,
     "hemisphere = -1.0 if self._latitude and self._latitude < 0 else 1.0",
     "hemisphere = 1.0"),
    ("M18 daily ET not mirrored", CAL,
     '"average_daily_et": 2.0 + 2.0 * summer,',
     '"average_daily_et": 2.0 + 2.0 * math.cos((month - 7) * math.pi / 6),'),
    ("M19 temperature not mirrored", CAL,
     "avg_temp = base_temp + (temp_variation * summer)",
     "avg_temp = base_temp + (temp_variation * math.cos((month - 7) * math.pi / 6))"),
    ("M20 tropical rain curve changed", CAL,
     "precip_factor = 1.0 + 0.3 * math.sin(",
     "precip_factor = 1.0 - 0.3 * math.sin("),
    ("M21 notes claim typical climate", CAL,
     'f"Illustrative {month_name} climate derived from latitude only"',
     'f"Based on typical {month_name} climate patterns"'),
    ("M22 service description reverted", EN,
     "based on an illustrative climate derived from latitude only",
     "based on representative climate data"),
    ("M23 services.yaml reverted", YAML,
     "based on an illustrative climate derived from latitude only.",
     "based on representative climate data."),
    ("M24 card note removed", VIEW,
     '${localize("panels.setup.weather_data.seasonal_note", lang)}',
     ""),
    # Added after the task-1 review (deviations.md): the PyETO helper's month
    # length was pinned for July only, and "rain once" vs "twice" hung on the scene.
    ("M25 PyETO reference year not a leap year", CAL,
     "days_in_month = calendar.monthrange(2024, month)[1]  # 2024: reference year",
     "days_in_month = calendar.monthrange(2023, month)[1]  # 2024: reference year"),
    ("M26 rain subtracted twice", CAL,
     "net_water_need_mm = max(0, et_mm * kc - precipitation_mm)",
     "net_water_need_mm = max(0, et_mm * kc - 2 * precipitation_mm)"),
    # Added after the task-2 review: Kc for modules without rain, and Kc 0.
    ("M27 Kc only where rain is booked", CAL,
     "net_water_need_mm = max(0, et_mm * kc - precipitation_mm)",
     "net_water_need_mm = max(0, (et_mm * kc if precipitation_mm else et_mm) - precipitation_mm)"),
    ("M28 Kc 0 falls back to the default", CAL,
     "        kc = zone.get(const.ZONE_KC, const.CONF_DEFAULT_KC)\n        if kc is None:\n            kc = const.CONF_DEFAULT_KC\n",
     "        kc = zone.get(const.ZONE_KC) or const.CONF_DEFAULT_KC\n"),
    # Added after the task-3 review: the static branch's month length.
    ("M29 static month is a literal 31", CAL,
     "et_estimate = max(0.0, -modinst.calculate()) * days_in_month",
     "et_estimate = max(0.0, -modinst.calculate()) * 31"),
    # Added after the task-4 review: the passthrough branch's month length.
    ("M30 passthrough month is a literal 29", CAL,
     'month_data.get("average_daily_et", 3.0) * days_in_month',
     'month_data.get("average_daily_et", 3.0) * 29'),
    # Added after the task-5 review: the rain curve that names no season.
    ("M31 tropical rain mirrored too", CAL,
     "precip_factor = 1.0 + 0.3 * math.sin(",
     "precip_factor = 1.0 + 0.3 * hemisphere * math.sin("),
    # Added after the task-6 review: a note that keeps "latitude" but not the claim.
    ("M32 notes drop 'illustrative'", CAL,
     'f"Illustrative {month_name} climate derived from latitude only"',
     'f"{month_name} climate typical for your latitude"'),
    # Added after the task-7 review: wordings that keep "latitude" but not the
    # claim, and a translation left on the old text.
    ("M33 EN description keeps latitude, not the claim", EN,
     "based on an illustrative climate derived from latitude only",
     "based on typical climate data for your latitude"),
    ("M34 services.yaml keeps latitude, not the claim", YAML,
     "based on an illustrative climate derived from latitude only.",
     "based on typical climate data for your latitude."),
    ("M35 DE description back on the old claim", DE,
     "auf Basis eines allein aus dem Breitengrad abgeleiteten Beispielklimas erstellen",
     "auf Basis repräsentativer Klimadaten erstellen"),
    ("M37 services.yaml keeps the old claim and adds the new words", YAML,
     "based on an illustrative climate derived from latitude only.",
     "based on representative climate data (an illustrative climate derived from latitude only)."),
    # Added with the task-8 deviation: a card note that drops "illustrative".
    ("M36 card note drops 'illustrative'", NOTE_EN,
     "Illustrative values derived from your latitude only",
     "Values for your latitude"),
    # Added after the task-8 review: where and under which key the view shows it.
    ("M38 view asks a misspelled key", VIEW,
     '${localize("panels.setup.weather_data.seasonal_note", lang)}',
     '${localize("panels.setup.weather_data.seasonal_notes", lang)}'),
    ("M39 note only in the empty state", VIEW,
     '                ${localize("panels.zones.calendar.no_data", lang)}\n'
     '              </div>`\n'
     '            : html`\n'
     '                <div class="weather-note">\n'
     '                  ${localize("panels.setup.weather_data.seasonal_note", lang)}\n'
     '                </div>\n',
     '                ${localize("panels.zones.calendar.no_data", lang)}\n'
     '                ${localize("panels.setup.weather_data.seasonal_note", lang)}\n'
     '              </div>`\n'
     '            : html`\n'),
    # Added after the task-8 re-review: the note in both branches.
    ("M40 note in both branches", VIEW,
     '${localize("panels.zones.calendar.no_data", lang)}\n',
     '${localize("panels.zones.calendar.no_data", lang)}\n'
     '                ${localize("panels.setup.weather_data.seasonal_note", lang)}\n'),
]


def run_tests(worktree):
    cmd = [PY, "-m", "pytest", "tests/test_watering_calendar.py", "-p",
           "_local_socket_unblock", "-q", "--no-header", "-rf"]
    proc = subprocess.Popen(cmd, cwd=worktree, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                            errors="replace")
    try:
        out, _ = proc.communicate(timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)],
                       capture_output=True)
        proc.communicate()
        return None, []
    killers = sorted(set(re.findall(r"^FAILED (\S+)", out, re.M)))
    summary = [ln for ln in out.splitlines() if re.search(r"\d+ (passed|failed)", ln)]
    return (summary[-1].strip() if summary else out[-300:]), killers


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    worktree = Path(sys.argv[1])
    result = Path(sys.argv[2])
    lines = []
    survived = 0
    for name, rel, old, new in MUTATIONS:
        path = worktree / rel
        original = path.read_bytes()
        text = original.decode("utf-8")
        crlf = "\r\n" in text
        plain = text.replace("\r\n", "\n")
        count = plain.count(old)
        if count != 1:
            lines.append(f"{name}: ANCHOR {count}x -- not run")
            survived += 1
            print(lines[-1])
            continue
        mutated = plain.replace(old, new)
        if crlf:
            mutated = mutated.replace("\n", "\r\n")
        path.write_bytes(mutated.encode("utf-8"))
        try:
            summary, killers = run_tests(worktree)
        finally:
            path.write_bytes(original)
        if summary is None:
            verdict = "HANG"
        elif not re.search(r"\d+ (passed|failed)", summary):
            verdict = "NOT COLLECTED"
        elif killers:
            verdict = "KILLED"
        else:
            verdict = "SURVIVED"
        if verdict != "KILLED":
            survived += 1
        lines.append(f"{name}: {verdict} | {summary}")
        for k in killers:
            lines.append(f"    {k}")
        print("\n".join(lines[-1 - len(killers):]))
    lines.append(f"TOTAL {len(MUTATIONS)}, not killed {survived}")
    print(lines[-1])
    result.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
