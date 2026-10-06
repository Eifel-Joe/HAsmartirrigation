Pre-release for a live test. Built on [JustChr/HAsmartirrigation](https://github.com/JustChr/HAsmartirrigation) `master` at **v2026.10.03**, 0 behind, plus one fix that is not upstream yet.

**The fix**

- A reload of the integration (every save in its options) no longer leaves the flow sampler and the backstop of a running self-closing run behind on the old instance. The master's pending off timer no longer outlives an unload either.
- Disabling the integration in the middle of a run stops service runs through their stop service, books them as partial, gives up the zones still waiting, and with *switch off after run* switches the master off at once. Removing it in the middle of a run stops the runs without booking them.
- A distributor sweep without the master no longer clears the cycle flag under a pump-fed zone that is still running.

The HACS zip is attached and built from this commit. Versions are synchronous across `manifest.json`, `const.py` and the frontend `package.json`. No storage change.
