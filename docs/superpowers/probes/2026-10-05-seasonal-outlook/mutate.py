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
