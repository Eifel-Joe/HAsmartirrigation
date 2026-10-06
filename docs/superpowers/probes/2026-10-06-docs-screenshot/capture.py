"""Capture the Weather & Location tab's weather-data view (Forecast, Weather records,
Seasonal outlook) from HA-Test as a PNG at device scale 2, like the docs image it
replaces. Reuses the login stored in ``edge-profile`` by login.py; never logs in.

Usage: capture.py <out.png> [css_width]
Prints the values the seasonal card shows, for the K2 check against the websocket data.
"""

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
PROFILE = HERE / "edge-profile"
URL = "http://192.168.10.196:8123/irrigation_plus/setup"
OUT = Path(sys.argv[1])
WIDTH = int(sys.argv[2]) if len(sys.argv) > 2 else 1440

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        str(PROFILE),
        channel="msedge",
        headless=True,
        viewport={"width": WIDTH, "height": 4000},
        device_scale_factor=2,
        locale="en-US",
        color_scheme="light",
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto(URL)
    view = page.locator("irrigation-plus-view-weather-data")
    view.wait_for(state="attached", timeout=60_000)
    # Data arrives asynchronously: wait until the seasonal table has its 12 rows,
    # then let the other cards, fonts and layout settle.
    page.locator("irrigation-plus-view-weather-data .seasonal-table .weather-row").nth(
        11
    ).wait_for(state="attached", timeout=60_000)
    page.wait_for_timeout(2500)
    state = page.evaluate(
        """() => {
            const h = document.querySelector("home-assistant").hass;
            return {language: h.language, darkMode: h.themes && h.themes.darkMode};
        }"""
    )
    rows = page.locator(
        "irrigation-plus-view-weather-data .seasonal-table .weather-row"
    ).all_inner_texts()
    note = page.locator(
        "irrigation-plus-view-weather-data .weather-note"
    ).all_inner_texts()
    box = view.bounding_box()
    view.screenshot(path=str(OUT), animations="disabled")
    print(
        json.dumps(
            {
                "state": state,
                "box_css": box,
                "notes": note,
                "seasonal_rows": rows,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    ctx.close()
