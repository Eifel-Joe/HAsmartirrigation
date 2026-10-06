"""Open HA-Test in an Edge window with a dedicated profile and wait for the user's login.

The user types the password; this script never sees or stores it. It only waits until
the Irrigation Plus setup view is on screen, reports language/theme, and closes. The
login stays in the profile (``edge-profile``) for capture.py, provided the user ticked
"Keep me logged in".
"""

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
PROFILE = HERE / "edge-profile"
URL = "http://192.168.10.196:8123/irrigation_plus/setup"

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        str(PROFILE),
        channel="msedge",
        headless=False,
        no_viewport=True,
        locale="en-US",
        color_scheme="light",
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto(URL)
    print("waiting for login ...", flush=True)
    page.wait_for_selector(
        "irrigation-plus-view-weather-data", state="attached", timeout=15 * 60 * 1000
    )
    page.wait_for_timeout(3000)
    info = page.evaluate(
        """() => {
            const h = document.querySelector("home-assistant").hass;
            let stored = null;
            try { stored = localStorage.getItem("hassTokens") !== null; } catch (e) {}
            return {
                language: h.language,
                selectedLanguage: h.selectedLanguage,
                selectedTheme: h.selectedTheme,
                darkMode: h.themes && h.themes.darkMode,
                tokensStored: stored,
                url: location.pathname,
            };
        }"""
    )
    print(json.dumps(info), flush=True)
    ctx.close()
sys.exit(0)
