Built fresh on [JustChr/HAsmartirrigation](https://github.com/JustChr/HAsmartirrigation) `master` at **v2026.10.03**, 0 behind. **This fork's delta is branding and nothing else**, as in v2026.10.01.

**New since v2026.10.01, all from upstream:** two changes, each inactive unless you use the settings it names. JustChr's release notes for [v2026.10.02](https://github.com/JustChr/HAsmartirrigation/releases/tag/v2026.10.02) and [v2026.10.03](https://github.com/JustChr/HAsmartirrigation/releases/tag/v2026.10.03) have the details.

- **Reduce durations when rain is forecast** now reaches zones without a flow sensor under **Live-estimate watering**, only if both options are on. The live bucket still shows the true deficit; only the run is shortened.
- **Zones that measure solar radiation** with PyETO and either use *Forecast days* above 0 or have hourly calculation off get a live bucket that lands on the nightly figure. One part is not opt-in: for a zone on a sensor group with a solar sensor, each nightly calculation stores one small record on that sensor group (the last seven days). There is no storage version change, and older releases ignore it.

**Already on v2026.10.01 or v2026.09.30?** If neither setting applies to you, updating changes nothing you would notice; the store stays at 14.2.

**Coming from v2026.09.20 or earlier?** Read the [v2026.09.30 notes](https://github.com/Eifel-Joe/HAsmartirrigation/releases/tag/v2026.09.30): this release carries everything listed there, including the store's move to 14.2 and the reminder to reload the panel (Ctrl+F5) after updating.

## Notes

Versions are synchronous across `manifest.json`, `const.py` and the frontend `package.json`. The HACS zip is attached and built from this commit.

Switching to JustChr's own build of the same version costs nothing: same domain, same entities, same storage.

