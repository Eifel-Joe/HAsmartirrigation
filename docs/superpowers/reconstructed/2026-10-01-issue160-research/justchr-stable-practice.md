# How JustChr promotes a beta to stable — research for Eifel-Joe#160 / PR #186

Read-only research (gh REST + GraphQL, plus a web search that found nothing beyond the GitHub pages below).
State as of **2026-10-01 07:23 UTC**. All times are UTC. Repository: https://github.com/JustChr/HAsmartirrigation

**Whose words count.** Only the account `JustChr` (release notes, issue and PR comments, PR reviews, issue bodies, commit messages) is treated as the maintainer's statement. The one bot comment in the repo (`watchtower-justchr[bot]` on #160, 2026-09-29 05:09) is excluded; JustChr withdrew it himself 58 minutes later: "Please disregard it." (https://github.com/JustChr/HAsmartirrigation/issues/160#issuecomment-5884685278). Many JustChr comments and commits carry Claude Code footers or co-author trailers, so the wording may be assistant-drafted, but it is posted from his account. None of his 199 comments was edited more than 2 minutes after posting, so quoted wording is as first posted.

**Corpus read.** 123 releases (REST and GraphQL agree), 183 issues and PRs, 304 issue/PR comments (199 by JustChr), 27 PR reviews (all by JustChr; there are no inline review comments), 3 discussions (none about release practice), 267 commits since 2026-07-25, `scripts/release.ps1`, `CONTRIBUTING.md`, README and docs. Quotes are verbatim (markdown bold markers removed, apostrophes normalised), each machine-checked against its source, each at most 27 words.

---

## 0. Summary

1. **Channel.** No pre-release existed before 2026-08-03. All 77 earlier releases (2026-05-30 to 2026-07-31) are non-prerelease. Since then: 46 releases = 18 stable + 28 pre-release, in 8 beta lines.
2. **Mechanism.** Two forms: (a) a new tag published as stable that contains the whole beta line plus more (6 lines); (b) the same tag promoted in place with `gh release edit --prerelease=false` (2 lines: v2026.08.17, v2026.09.05). Every stable is a strict superset of its line's last beta (8 of 8, `behind_by = 0`). No revert commits exist since 2026-07-25.
3. **Speed.** First beta to stable: 1.04, 1.16, 2.06, 2.22, 2.51, 2.53, 4.06, 8.98 days (median 2.4). The current line has 12 betas, is 10.7 days old, carries 51 commits / +16,087 lines beyond v2026.09.17, and has no announced freeze, date or criterion.
4. **Gate.** No written policy anywhere in the repo. Stated criteria: field evidence where the only proof is "arithmetic and tests", verified data migrations, audited code, and "a week" of beta for changes that reach people who never opt in. In practice he overrode these when waiting hurt stable users (v2026.08.13, v2026.09.12, v2026.09.17) and waited when a migration could not be undone (v2026.08.17).
5. **Open issues that await a field confirmation have never been a formal gate.** #148 was open when v2026.09.17 shipped with its fix; batch mode went stable (08.13) before its field test finished; #181 got the sentence "Leaving this open until it has been through a field test" and was closed by JustChr 1 h 43 min later without a comment. Two things did hold a stable: an unverified irreversible migration (08.17, about 2.5 days) and one PR he had said the stable would wait for (#139, about 24 h, then dropped from the stable).
6. **For #186.** It sits on master, so it goes into whichever stable is cut from master next, unless he delays that stable or branches around it. Whether #160 is open is unlikely to matter; whether #186 has had a field test or enough soak may influence the date. See section 4.

---

## 1. Release timeline

### 1.1 Facts

- First pre-release: v2026.08.01, published 2026-08-03 06:28, 2 min 20 s after commit [c026861](https://github.com/JustChr/HAsmartirrigation/commit/c02686108e6c4fce479688677309caafe20628fc) added `-Prerelease` to `scripts/release.ps1` (06:25).
- HACS offers a pre-release only to users who enable "show beta versions" for the repository (stated in the `release.ps1` header and in 20 of the 28 beta notes).
- "Stable" below means GitHub `prerelease: false` today. Two tags were published as pre-releases and flipped later (v2026.08.17, v2026.09.05). The REST API does not record that, so their promotion time is the GraphQL `updatedAt` of the release, corroborated by comments (table 1.2).
- Stables that contain their line: compare of each line's last beta tag against the stable tag shows `behind_by = 0` and `ahead_by` of 2 to 16 commits (08.04>08.05: 2, 08.06>08.07: 16, 08.12>08.13: 4, 08.16>08.17: 6, 09.04>09.05: 9, 09.09>09.10: 6, 09.11>09.12: 3, 09.16>09.17: 2).
- Branch cuts (`release.ps1 -Ref`) were used only for single-fix hotfix stables (v2026.09.01, v2026.09.03). Commit [fb2804e](https://github.com/JustChr/HAsmartirrigation/commit/fb2804ec16f34d51c5358bbd45cd02bbfd6599a9): "Master already holds the next release's worth of work, so the fix cannot be shipped from there without dragging all of it into a stable release".
- The repo documents no release-channel policy: README, `CONTRIBUTING.md` and the docs pages contain nothing on beta or stable. The only written statements are the `release.ps1` header, the commit messages above, and the release notes.

### 1.2 Stable releases since the beta channel started (18), with the betas of each line

Baseline before the channel: v2026.07.11 (2026-07-31 12:55).

| Stable | Stable date (UTC) | Betas of the line since previous stable | First beta (UTC) | Days first beta to stable | Remarks |
|---|---|---|---|---|---|
| v2026.08.05 | 08-05 07:52 | 4: 08.01, 08.02, 08.03, 08.04 | 08-03 06:28 | 2.06 | "first stable release since v2026.07.11"; #67 verified by reporter on 08.04 about 36 h earlier |
| v2026.08.07 | 08-12 08:44 | 1: 08.06 | 08-08 07:17 | 4.06 | A regression from 08.06 reached stable and was found 08-12 (#87), then hotfixes 08.08 to 08.10 the same day |
| v2026.08.13 | 08-18 10:59 | 2: 08.11, 08.12 | 08-17 07:13 | 1.16 | Batch mode went stable before its field test finished |
| v2026.08.17 | 08-23 07:06 (promoted in place; published as pre-release 08-22 14:47) | 08.16, plus itself as a beta | 08-20 18:59 | 2.51 | Held for migration verification (row 3 of table 3) |
| v2026.09.05 | 09-05 07:23 (promoted in place; published as pre-release 09-04 13:15) | 09.02, 09.04, plus itself as a pre-release | 09-02 18:44 | 2.53 | Asked for "a wet window"; no visible report (row 4 of table 3) |
| v2026.09.10 | 09-07 18:30 | 2: 09.08, 09.09 (09.07 withdrawn same day) | 09-05 13:10 | 2.22 | The rename; HACS cannot serve a renamed build while the newest stable is pre-rename |
| v2026.09.12 | 09-08 20:37 | 1: 09.11 | 09-07 19:45 | 1.04 | Beta asked for "a few days"; 25 h elapsed |
| v2026.09.17 | 09-20 08:08 | 3: 09.14, 09.15, 09.16 | 09-11 08:31 | 8.98 (4.59 from the last beta) | Freeze issue #147 opened 09-15 |
| (none yet) | | 12: 09.18 to 10.01 | 09-20 15:37 | 10.7 so far | See 1.3 |

Stables published directly, with no beta of their own (10):

| Stable | Date (UTC) | What it was |
|---|---|---|
| v2026.08.08 | 08-12 09:41 | Hotfix for the 08.07 regression (#87) |
| v2026.08.09 | 08-12 12:19 | One fix for finish-anchored schedules on self-closing and OpenSprinkler zones |
| v2026.08.10 | 08-12 13:08 | Stop button did not close self-closing valves |
| v2026.08.14 | 08-19 13:52 | Batch-mode pause defects found by the field tester, released "Same day, as promised" |
| v2026.08.15 | 08-20 10:15 | Three fixes for observed watering, batch, OpenSprinkler |
| v2026.08.18 | 08-23 09:39 | New work merged 08-23 07:04 (#105, #108, #109) shipped straight to stable; includes "the one change here that moves a real start time" |
| v2026.09.01 | 09-02 18:33 | Hotfix, schedule dialog on HA 2026.8+; "did not work" (#117) |
| v2026.09.03 | 09-04 08:01 | Second hotfix, off the stable line; beta 09.02 is not in it |
| v2026.09.06 | 09-05 07:37 | Bridge release, last one called Smart Irrigation |
| v2026.09.13 | 09-09 07:14 | "Nothing about your watering changes" |

Also: the tag v2026.09.07 exists (commit 2026-09-05 12:16) but its release was withdrawn the same day ("I published the rename on the 5th and withdrew it the same day", https://github.com/JustChr/HAsmartirrigation/issues/120#issuecomment-5574535660); whether it was published as stable or pre-release is unverified.

### 1.3 Statistics and the current line

- Eight lines, first beta to stable, in days: 1.04, 1.16, 2.06, 2.22, 2.51, 2.53, 4.06, 8.98. Median 2.36, mean 3.07.
- Current line (v2026.09.17 is still GitHub "Latest"): 12 betas, 09.18, 09.19, 09.20, 09.21, 09.22, 09.23, 09.24, 09.25, 09.26, 09.27, 09.28, 10.01, first on 2026-09-20 15:37, last 2026-10-01 05:29. That is 10.58 days first to last beta, 10.7 days to now. The previous maximum was 8.98.
- Time since the last stable: 10.97 days at 07:23. The longest earlier stable-to-stable gap is 11.04 days (v2026.09.13 to v2026.09.17); the current gap reaches it at about 09:00 today.
- Size of what waits: v2026.09.17 to v2026.10.01 is 51 commits, 125 files, +16,087 / -1,667 lines. Earlier stable-to-stable deltas were 8 to 29 commits (+2,141 to +13,301 lines). The v2026.10.01 notes have 29 sections (about 62 KB); the v2026.09.17 stable notes have 14 (about 26 KB).
- Adoption proxy (`download_count` of the release zip, HACS uses `zip_release`): v2026.09.17 has 31; the 12 betas have 0, 1, 0, 0, 2, 2, 0, 1, 0, 2, 0, 3 (11 in total, at most 3 for any one beta). Meaning of the counter is unverified (see section 5).

---

## 2. Stated promotion criteria (JustChr's own words)

### A. Mechanism

- 2026-08-03, commit [c026861](https://github.com/JustChr/HAsmartirrigation/commit/c02686108e6c4fce479688677309caafe20628fc): "Promoting a verified beta to stable is then a flag edit on the same tag rather than a second release"
- [scripts/release.ps1](https://github.com/JustChr/HAsmartirrigation/blob/master/scripts/release.ps1) header: "promote the same build to stable once it has been verified, just clear the flag - no new version, no re-tag"
- Evidence for the two in-place promotions. v2026.08.17: on 2026-08-22 14:47 JustChr wrote that it "is out as a beta" ([#105](https://github.com/JustChr/HAsmartirrigation/pull/105#issuecomment-5380990129)); v2026.08.18's notes call themselves "the first since" v2026.08.17 "became stable"; GraphQL `updatedAt` 2026-08-23 07:06. v2026.09.05: "I am going to promote my current pre-release to stable first" ([#120, 2026-09-04 14:02](https://github.com/JustChr/HAsmartirrigation/issues/120#issuecomment-5541550447)); "Pre-release promoted to stable" ([#120, 2026-09-05 07:57](https://github.com/JustChr/HAsmartirrigation/issues/120#issuecomment-5550431790)); notes now say "This is now the stable release."; `updatedAt` 2026-09-05 07:23.

### B. What he says decides promotion

- 2026-08-03, notes of [v2026.08.01](https://github.com/JustChr/HAsmartirrigation/releases/tag/v2026.08.01), repeated in 08.02, 08.03, 08.04: "Feedback on this build is what decides when it goes stable."
- 2026-08-20, [#101](https://github.com/JustChr/HAsmartirrigation/pull/101#issuecomment-5360390400): "It is a beta for one reason: the v13 to v14 migration cannot be undone, and it has not yet run against anyone's real stored data." and "If it holds up on your install I will promote the same build to stable — same tag, no re-bump."
- 2026-08-22, [#105](https://github.com/JustChr/HAsmartirrigation/pull/105#issuecomment-5380990129): "a standing ask that is now blocking a promotion" and "If all three hold on your install I will promote the tag to stable with `--prerelease=false`; no re-release, same tag."
- 2026-08-23, [#105](https://github.com/JustChr/HAsmartirrigation/pull/105#issuecomment-5384752044), accepting a partial verification (the contributor's constructed store, "not an aged store"): "I will not promote on a stronger reading than that." The stable's notes then say: "The schedule storage migration has now been run on a real store, and it worked." ([v2026.08.17](https://github.com/JustChr/HAsmartirrigation/releases/tag/v2026.08.17)).
- 2026-08-22, review on [#107](https://github.com/JustChr/HAsmartirrigation/pull/107#pullrequestreview-5000342303): 'on this fork "not audited" blocks promoting to stable rather than the merge'. 2026-09-01, review on [#113](https://github.com/JustChr/HAsmartirrigation/pull/113#pullrequestreview-5078270468): "a display-only feature still blocks a stable release while that is true".
- 2026-09-02, review on [#115](https://github.com/JustChr/HAsmartirrigation/pull/115#pullrequestreview-5093675748): "It wants a wet window on a real install before it reaches stable users, and that is something only you and the other testers can give it." Same day, [comment](https://github.com/JustChr/HAsmartirrigation/pull/115#issuecomment-5514616216): "Promotion to stable is `gh release edit v2026.09.02 --prerelease=false` once it has seen real weather."
- 2026-09-15, [#147](https://github.com/JustChr/HAsmartirrigation/issues/147) (stabilisation issue): "Before anything else goes in, I want that line stable." and, as the most useful contribution, "field reports from the beta on real hardware and real weather".

### C. Change classes he says do not go straight to stable

- 2026-08-16, [#88](https://github.com/JustChr/HAsmartirrigation/issues/88#issuecomment-5308571228): "A mode that has never touched real hardware is not something I will put in a stable release."
- 2026-09-07, notes of [v2026.09.11](https://github.com/JustChr/HAsmartirrigation/releases/tag/v2026.09.11) (a calculation change that moves the stored bucket): "That is exactly the class of change this project does not ship straight to stable." It asked users to "run it for a few days on a zone you water manually".
- 2026-09-20, [#139](https://github.com/JustChr/HAsmartirrigation/issues/139#issuecomment-5748594302): "That is exactly the shape of change I would want to watch in a beta for a week before it reaches people who never opt in"
- 2026-09-20, [#150](https://github.com/JustChr/HAsmartirrigation/pull/150#issuecomment-5750682256): "this wants soak time on other people's hardware before it is promoted"
- 2026-09-20, [#157](https://github.com/JustChr/HAsmartirrigation/pull/157#issuecomment-5752506508): "It goes into a beta rather than straight to stable precisely because the displacement risk is the part nobody has measured"

### D. Where he overrode the criterion, in his own words

- Batch mode. 2026-08-17, notes of [v2026.08.12](https://github.com/JustChr/HAsmartirrigation/releases/tag/v2026.08.12): "Once it has been confirmed in the field this will be promoted to stable." One day later the stable [v2026.08.13](https://github.com/JustChr/HAsmartirrigation/releases/tag/v2026.08.13) says "It has not been verified against real hardware on our side", and to the tester ([#88, 2026-08-18 11:00](https://github.com/JustChr/HAsmartirrigation/issues/88#issuecomment-5327226751)): "I have promoted batch mode to a stable release ... before you finished testing it." The reason he gave: "Holding all of that behind one opt-in feature's field test stopped being the right call." (Other fixes in the two betas were missing for stable users.) The field test then found two defects, fixed in v2026.08.14 the next day.
- 2026-09-08, notes of [v2026.09.12](https://github.com/JustChr/HAsmartirrigation/releases/tag/v2026.09.12), 25 h after the beta that had asked for days: "the migration fixes above are worth more to the people still on v2026.09.10 than another week of soak is worth to this one"
- 2026-09-05, notes of [v2026.09.05](https://github.com/JustChr/HAsmartirrigation/releases/tag/v2026.09.05), rewritten at promotion: "at the time the evidence was arithmetic and tests rather than a season of use. That period is over and this is now the stable release"
- 2026-09-19, [#139](https://github.com/JustChr/HAsmartirrigation/issues/139#issuecomment-5740329987): "We are holding the next stable for this PR." One day later, [#139](https://github.com/JustChr/HAsmartirrigation/issues/139#issuecomment-5748594302): "I said the stable would wait for this PR, and I have gone ahead and shipped it without waiting." and "Everything in the release had either run in a beta since 09-14 or, for #146, had your field test behind it."
- 2026-09-20, [#146](https://github.com/JustChr/HAsmartirrigation/pull/146#issuecomment-5748594104) (merged 09-19 07:44, in the stable 09-20 08:08): "it went from merge to stable in a day — your field test is the reason I was willing to do that."
- Stables that name what they have not verified: [v2026.09.17](https://github.com/JustChr/HAsmartirrigation/releases/tag/v2026.09.17): "several need real weather or real hardware to confirm", and a schedule state transition that "has not been seen live yet".

### E. The current line (v2026.09.18 to v2026.10.01)

- Contrast, the previous line: 2026-09-15, notes of [v2026.09.16](https://github.com/JustChr/HAsmartirrigation/releases/tag/v2026.09.16): "This beta starts the run towards the next stable release. From here on only fixes and tests go in, no new features, until this line is stable." Lifted with the stable: "New features, modes and refactors are welcome again." ([#147, 2026-09-20](https://github.com/JustChr/HAsmartirrigation/issues/147#issuecomment-5748595013)).
- 2026-09-21, [#159](https://github.com/JustChr/HAsmartirrigation/issues/159#issuecomment-5756652756): "the beta chain is open, so there is room". No freeze or stabilisation issue has been opened since (JustChr authored no issue after 09-15).
- None of the 12 beta notes since v2026.09.17 mentions a freeze, a date, "next stable" or a promotion criterion (grep: 0 hits). Their only stated reason: "several of them change a number somebody is watching, and the rain fixes have still not been confirmed on the install that reported them" (this exact wording from v2026.09.22 through [v2026.10.01](https://github.com/JustChr/HAsmartirrigation/releases/tag/v2026.10.01); 09.19 to 09.21 say "the two rain fixes have not yet been" or "have still not been confirmed on the install that reported them"), plus a list of 22 "what is worth a report" bullets, the first being the Docker or Core case of #186.
- 2026-09-27, [#149](https://github.com/JustChr/HAsmartirrigation/issues/149#issuecomment-5853529101), the rain issue: he asked the reporter which version he runs and whether a rainy day ended with the bucket rising by no more than the gauge total, then: "If yes, I will close the issue."
- 2026-09-30, [#181](https://github.com/JustChr/HAsmartirrigation/issues/181#issuecomment-5906128035): "Leaving this open until it has been through a field test"
- 2026-10-01, [#186](https://github.com/JustChr/HAsmartirrigation/pull/186#issuecomment-5925322223): "Merging this, and it goes into the next beta." and "Not something I could reproduce: the live HA 2026.9.3 upgrade, rollback and re-upgrade"
- 2026-10-01, [#160](https://github.com/JustChr/HAsmartirrigation/issues/160#issuecomment-5925362711): "Leaving this open until it has been through a field test on a Docker or Core install whose container zone differs from Home Assistant's."
- 2026-09-21, [#160](https://github.com/JustChr/HAsmartirrigation/issues/160#issuecomment-5756658370), on why nobody saw it: "this is invisible on HA OS and Supervised, which is where it will have been tested"

---

## 3. Open confirmation items versus stable

"Fix in that stable?" refers to the stable named in the third column. "Class": **carried** = the stable shipped while the confirmation was still outstanding; **held** = the stable was delayed by it; **followed** = the stable came after the confirmation; **pending** = no stable has happened since.

| # | Item | State at stable time | Fix in that stable? | Class | Evidence |
|---|---|---|---|---|---|
| 1 | #148 live bucket lag (reporter Megalos); fix #144 | Open. JustChr: "I am leaving this open until you have had a chance to confirm it on your install." Reporter said 09-20 11:42 he would test on a dry day. Stable v2026.09.17 at 09-20 08:08 | Yes (in beta since 09.16, 09-15) | carried | Confirmed 09-28 18:55, closed by JustChr 09-28 19:09: [#148 comments](https://github.com/JustChr/HAsmartirrigation/issues/148#issuecomment-5748594205), [reporter](https://github.com/JustChr/HAsmartirrigation/issues/148#issuecomment-5876477319), [close](https://github.com/JustChr/HAsmartirrigation/issues/148#issuecomment-5876688113) |
| 2 | #88 / #91 batch mode, tester pnaklicki | Field test unfinished (only an informal "mostly working" at 08-17 19:13). Stable v2026.08.13 at 08-18 10:59 | Yes (the whole feature) | carried | JustChr: "before you finished testing it" ([#88](https://github.com/JustChr/HAsmartirrigation/issues/88#issuecomment-5327226751)); [tester's note](https://github.com/JustChr/HAsmartirrigation/issues/88#issuecomment-5319107026); defects found that evening, hotfix v2026.08.14 next day; #88 stayed open until 09-20 |
| 3 | #101 / #105 schedule storage migration v13 to v14 (irreversible), contributor clarejor | Unverified on real data; JustChr called it "a standing ask that is now blocking a promotion" | Yes, after the evidence | held (about 16 h after the 08.17 beta, 2.5 d after the first) | Contributor's constructed-store run posted 08-22 16:48 ([comment](https://github.com/JustChr/HAsmartirrigation/pull/105#issuecomment-5381506452)), accepted 08-23 07:04, tag promoted in place 07:06 |
| 4 | v2026.09.02 / .04 water-balance rewrite and valve-confirm reserve ("wants a wet window") | Promoted in place 09-05 07:23. Notes: "That period is over" | Yes | carried (no visible confirmation) | I found no wet-window report in the 09-02 to 09-05 comments; real-install checks by Eifel-Joe on other points are credited in the notes. Whether a report arrived off-tracker is unverified |
| 5 | #124 mid-window credit change (beta 09.11 asked for "a few days") | Stable v2026.09.12 at 25 h; #124 has only JustChr's comment | Yes | carried (soak shortened by his stated trade-off) | [#124 comment](https://github.com/JustChr/HAsmartirrigation/pull/124#issuecomment-5575036334), notes of v2026.09.12 ("Why this is stable now") |
| 6 | #139 self-closing finish grace (PR #150) | 09-19: "We are holding the next stable for this PR." 09-20: shipped without it | No (merged 09-20 15:16, went into beta 09.18) | held about 24 h, then deferred out of the stable | [09-19](https://github.com/JustChr/HAsmartirrigation/issues/139#issuecomment-5740329987), [09-20](https://github.com/JustChr/HAsmartirrigation/issues/139#issuecomment-5748594302), [#150](https://github.com/JustChr/HAsmartirrigation/pull/150#issuecomment-5750682256) |
| 7 | #146 / #137 rain check on the run's own day | Merged 09-19 07:44; in no beta | Yes, 24 h later | followed (contributor's field test) | "your field test is the reason I was willing to do that" ([#146](https://github.com/JustChr/HAsmartirrigation/pull/146#issuecomment-5748594104)) |
| 8 | #67 unit-system conversion (clarejor) | Reporter confirmed on beta 08.04 at 08-03 19:45; stable 08.05 at 08-05 07:52; closed 07:54 | Yes | followed (about 36 h after the confirmation) | [verification](https://github.com/JustChr/HAsmartirrigation/issues/67#issuecomment-5170966655), [close](https://github.com/JustChr/HAsmartirrigation/issues/67#issuecomment-5189126025) |
| 9 | #117 schedule dialog (reporter jaaphoenderdos) | Hotfix v2026.09.01 shipped as stable without confirmation and did not work (reporter 09-02 19:31); "the fix in v2026.09.01 did not work" | No: the 09.01 fix did not work; v2026.09.03 fixed it, reporter confirmed 09-04 08:24 | carried (hotfix path, no beta) | [09-02](https://github.com/JustChr/HAsmartirrigation/issues/117#issuecomment-5514476518), [09-04](https://github.com/JustChr/HAsmartirrigation/issues/117#issuecomment-5537624932), [confirm](https://github.com/JustChr/HAsmartirrigation/issues/117#issuecomment-5537792130) |
| 10 | Regression from beta 08.06 | 4 days in beta without a report; reached stable 08.07; "it was a regression in .07, and your report was the first" | n/a | beta soak did not catch it | [#83 comment](https://github.com/JustChr/HAsmartirrigation/issues/83#issuecomment-5265033538), commit [b367c86](https://github.com/JustChr/HAsmartirrigation/commit/b367c86c65bdea0cc25e9894ee804a38b2ef9b46): "This shipped in v2026.08.06 (beta) and reached stable in v2026.08.07." |
| 11 | #181 distributor inlet gate (PR #185, beta 09.28) | 09-30 07:13: "Leaving this open until it has been through a field test". Closed by JustChr 08:56:49 (+1 h 43 min), no comment, no field report exists | n/a (no stable yet) | the hold sentence was not enforced | [comment](https://github.com/JustChr/HAsmartirrigation/issues/181#issuecomment-5906128035); timeline `closed` event by JustChr with no commit or comment |
| 12 | #149 rain double-count (reporter Megalos), fixes in beta 09.18 and 09.19 | Open since 09-20. Reporter's last word 09-26 (he did comment on #148 on 09-28 but not here). JustChr asked on 09-27 for version and a rainy-day result; no answer as of 10-01 07:23. Every beta from 09.19 to 10.01 says the rain fixes have not (yet) been confirmed on the install that reported them (see 2.E) | n/a (no stable yet) | pending | [#149](https://github.com/JustChr/HAsmartirrigation/issues/149) |
| 13 | #160 container time zone (fix #186, beta 10.01) | Open; "Leaving this open until it has been through a field test on a Docker or Core install" (sentence continues in the source) | n/a (no stable yet) | pending | [#160](https://github.com/JustChr/HAsmartirrigation/issues/160#issuecomment-5925362711) |

Other items checked: #72 (confirmed by the reporter on beta 08.02, closed 08-03 before any stable) and #170 (reporter confirmed beta 09.23 within 55 minutes and closed it himself) did not interact with a stable.

---

## 4. Assessment

### 4.1 What the evidence supports (no judgement)

- **F1.** Stable contains the last beta in 8 of 8 lines; no revert commits; JustChr himself writes that a release cut from master drags in everything on master (commit fb2804e). To keep a merged change out of a stable he would have to delay the stable or cut from a branch (done only for single-fix hotfixes).
- **F2.** Issue state has not gated a stable: rows 1, 2, 6, 11 of table 3. The same sentence as in #160 ("Leaving this open until it has been through a field test") was followed by closing the issue within 1 h 43 min (#181).
- **F3.** What did hold a stable: an unverified irreversible migration (row 3; ended after about 14 h once the contributor posted partial evidence) and one announced PR hold (row 6; reversed after about 24 h).
- **F4.** His stated soak norms: "a week" in a beta for changes that reach people who never opt in and move timing; a calculation change that moves stored values is "the class of change this project does not ship straight to stable". Applied inconsistently: v2026.09.12 followed its beta by 25 h.
- **F5.** What #186 is (PR body and notes): not opt-in; a one-time conversion of stored timestamps at first start (storage 14.1 to 14.2, minor on purpose; the PR body says a rollback "misreads one window on an affected install, then heals"); only installs whose container zone differs from Home Assistant's are affected; "Your durations may move on the first calculation". The author verified upgrade, rollback and re-upgrade live on HA OS 2026.9.3 and covered the zone mismatch in tests (process zone pinned, including a child process at `TZ=EST5EDT`), not on a real Docker or Core install. JustChr: "Not something I could reproduce: the live HA 2026.9.3 upgrade, rollback and re-upgrade".
- **F6.** JustChr's own words tie confirmation to exactly the missing environment: bug "invisible on HA OS and Supervised, which is where it will have been tested" and the 10-01 "field test on a Docker or Core install whose container zone differs".
- **F7.** The beta population is tiny: at most 3 downloads for any beta, 11 across the 12 betas of this line, against 31 for v2026.09.17. Comments from reporters other than the three contributors (Eifel-Joe, clarejor, pnaklicki) during the line: Megalos (4, on #148 and #149) and AxxlFoley (1, #170); altmenorg's one comment on #120 is a courtesy note. No reporter in the tracker states a Docker or Core install (AxxlFoley's "Home Assistant Core: 2026.9.2" on #170 is a version label; install type unverified).
- **F8.** The line is unusually long and large (section 1.3), the notes name unconfirmed rain fixes as a reason for the pre-release, the reporter of those has been silent since 09-26, and no freeze, date or criterion has been announced ("the beta chain is open").
- **F9.** #186 was merged at 05:26:07 and shipped in beta v2026.10.01 at 05:29:01, so it is about 2 hours old at the time of writing.

### 4.2 Judgement (mine; inference, not record)

1. **Will an open #160 by itself block #186 from the next stable? Probably not.** Basis: F2, F3 and especially #181. The open state has not been a gate he applied; he has repeatedly reversed holds when stable users were waiting (08.13, 09.12, 09.17). Confidence: fairly high, but it is a discretionary practice with n = 8 lines.
2. **Will #186 be in the next stable? Most likely yes** (F1). Ways it would not be: (a) he delays the stable until #186 is verified or soaked; (b) he cuts a stable from an older branch without it (never done for a line); (c) a revert (never happened). Only (a) is realistic.
3. **Does #186 raise the chance of (a)? Moderately yes**, through timing rather than through the issue. It is the class he soaks (non-opt-in, one-time stored-data conversion, moves numbers), the unverified part is the exact environment he named (F5, F6), and it is the newest change in the line: a stable cut within days would give it less beta time than any change he has called "a week". Mitigating: the migration is rollback-safe by design (unlike v13 to v14), the affected population is small, he accepted partial contributor evidence before (row 3) and shipped stables whose notes say plainly what was not verified (08.13, 09.17).
4. **If he cuts the stable soon, I would expect #186 inside it with an explicit "worth a report" request or a plain note that it was not verified on Docker or Core, and #160 still open**, the pattern of #148 in v2026.09.17 and of batch mode in v2026.08.13.
5. **Timing cannot be predicted from the record.** Historical median 2.4 days from first beta would put it around 10-03 or 10-04; applying "a week" to the newest change would give about 10-08; the line has already exceeded every earlier line. The item he names most often as outstanding is the rain-fix confirmation (#149), not #160.

### 4.3 What would shift this

- A post-merge field report on v2026.10.01 from a Docker or Core install whose container zone differs from Home Assistant's, including the one-time conversion on a real stored buffer. Contributor-run evidence has been accepted as the unblocker before: #101/#105 (constructed store, partial), #146 (contributor field test enabled a one-day fast track), #67 (contributor verification preceded 08.05). The contributor's own container would qualify only if it is a real Docker or Core install with a mismatched zone.
- A freeze or stabilisation announcement like #147: a fix such as #186 would be in scope.
- Any report that the conversion misbehaves would turn #160 from a note into a real blocker.

---

## 5. Uncertainties

- **Promotion timestamps** for v2026.08.17 and v2026.09.05 come from GraphQL `updatedAt`, not from a promotion event (the REST API has none). Corroboration: comments, rewritten release bodies, and the 16 h and 18 h gaps to `publishedAt`. A later unrelated edit would also bump `updatedAt`. That these two were first published as pre-releases is inferred from his comments and the notes, not from API history. For all 16 other stables `updatedAt` is within 30 s of `publishedAt` (likely the CI asset upload), so a flip within seconds cannot be excluded.
- **v2026.09.07** (withdrawn rename): tag exists, release deleted; stable or pre-release unknown.
- **Off-tracker evidence.** Email, chat, HACS or forum statements are invisible to me; confirmations for rows 4 and 5 could have arrived there. The web search surfaced only GitHub pages already read.
- **Small, evolving sample.** Eight lines, one maintainer, practice changing (apology for 08.13 on 08-18, freeze #147 on 09-15, hold reversal on 09-20). The current line is the longest and largest, with no precedent.
- **Download counts** are the `download_count` of the release zip; with `zip_release` HACS downloads it on install and update, but the counter also includes manual downloads and the maintainers' own installs and counts repeated updates by one user. Not unique users. Unverified.
- **Docker or Core users.** The finding that none appear in the tracker rests on text search of issue bodies and comments; the bug template has no install-type field and diagnostics attachments were not opened.
- **Authorship.** Many of his posts have Claude Code footers or trailers. All posts from the `JustChr` account are treated as his statements, as instructed; the `watchtower-justchr[bot]` comment is excluded.
- **Day counts** use first-beta publication to the stable's effective time; from the last beta they differ (given where it matters).
- **The "wet window" and "few days of real weather" claims** in v2026.09.05 and v2026.09.12 are his; I could not verify them against any visible report.

---

## Appendix A. All 123 releases (newest first; REST `gh api releases --paginate` and `gh release list --limit 200` give the same set)

```
tag          published (UTC)   kind
-----------  ----------------  ------------------------------------------------
v2026.10.01  2026-10-01 05:29  pre-release
v2026.09.28  2026-09-30 07:09  pre-release
v2026.09.27  2026-09-28 18:08  pre-release
v2026.09.26  2026-09-28 13:08  pre-release
v2026.09.25  2026-09-27 16:05  pre-release
v2026.09.24  2026-09-27 14:26  pre-release
v2026.09.23  2026-09-26 13:02  pre-release
v2026.09.22  2026-09-23 09:11  pre-release
v2026.09.21  2026-09-20 20:37  pre-release
v2026.09.20  2026-09-20 19:51  pre-release
v2026.09.19  2026-09-20 17:18  pre-release
v2026.09.18  2026-09-20 15:37  pre-release
v2026.09.17  2026-09-20 08:08  stable  <- GitHub 'Latest'
v2026.09.16  2026-09-15 17:58  pre-release
v2026.09.15  2026-09-13 16:55  pre-release
v2026.09.14  2026-09-11 08:31  pre-release
v2026.09.13  2026-09-09 07:14  stable
v2026.09.12  2026-09-08 20:37  stable
v2026.09.11  2026-09-07 19:45  pre-release
v2026.09.10  2026-09-07 18:30  stable
v2026.09.09  2026-09-05 16:54  pre-release
v2026.09.08  2026-09-05 13:10  pre-release
v2026.09.06  2026-09-05 07:37  stable
v2026.09.05  2026-09-04 13:15  stable (published as pre-release, promoted in place 2026-09-05 07:23)
v2026.09.04  2026-09-04 08:08  pre-release
v2026.09.03  2026-09-04 08:01  stable
v2026.09.02  2026-09-02 18:44  pre-release
v2026.09.01  2026-09-02 18:33  stable
v2026.08.18  2026-08-23 09:39  stable
v2026.08.17  2026-08-22 14:47  stable (published as pre-release, promoted in place 2026-08-23 07:06)
v2026.08.16  2026-08-20 18:59  pre-release
v2026.08.15  2026-08-20 10:15  stable
v2026.08.14  2026-08-19 13:52  stable
v2026.08.13  2026-08-18 10:59  stable
v2026.08.12  2026-08-17 07:49  pre-release
v2026.08.11  2026-08-17 07:13  pre-release
v2026.08.10  2026-08-12 13:08  stable
v2026.08.09  2026-08-12 12:19  stable
v2026.08.08  2026-08-12 09:41  stable
v2026.08.07  2026-08-12 08:44  stable
v2026.08.06  2026-08-08 07:17  pre-release
v2026.08.05  2026-08-05 07:52  stable
v2026.08.04  2026-08-03 18:39  pre-release
v2026.08.03  2026-08-03 17:17  pre-release
v2026.08.02  2026-08-03 10:09  pre-release
v2026.08.01  2026-08-03 06:28  pre-release
v2026.07.11  2026-07-31 12:55  stable
v2026.07.10  2026-07-31 08:53  stable
v2026.07.09  2026-07-16 08:56  stable
v2026.07.08  2026-07-15 09:02  stable
v2026.07.07  2026-07-14 15:16  stable
v2026.07.06  2026-07-14 12:34  stable
v2026.07.05  2026-07-13 16:14  stable
v2026.07.04  2026-07-09 06:30  stable
v2026.07.03  2026-07-05 13:36  stable
v2026.07.02  2026-07-04 17:20  stable
v2026.07.01  2026-07-02 14:03  stable
v2026.06.45  2026-06-28 15:21  stable
v2026.06.44  2026-06-26 08:28  stable
v2026.06.43  2026-06-26 06:58  stable
v2026.06.42  2026-06-25 18:04  stable
v2026.06.41  2026-06-25 09:09  stable
v2026.06.40  2026-06-24 10:35  stable
v2026.06.39  2026-06-23 16:26  stable
v2026.06.38  2026-06-21 18:09  stable
v2026.06.37  2026-06-21 13:54  stable
v2026.06.36  2026-06-21 10:09  stable
v2026.06.35  2026-06-21 07:36  stable
v2026.06.34  2026-06-20 16:45  stable
v2026.06.33  2026-06-20 07:08  stable
v2026.06.32  2026-06-16 18:13  stable
v2026.06.31  2026-06-15 18:41  stable
v2026.06.30  2026-06-14 06:40  stable
v2026.06.29  2026-06-13 22:32  stable
v2026.06.28  2026-06-13 15:47  stable
v2026.06.27  2026-06-13 10:24  stable
v2026.06.26  2026-06-12 20:02  stable
v2026.06.25  2026-06-12 19:23  stable
v2026.06.24  2026-06-12 11:22  stable
v2026.06.23  2026-06-12 06:31  stable
v2026.06.22  2026-06-11 19:52  stable
v2026.06.21  2026-06-09 18:54  stable
v2026.06.20  2026-06-09 17:34  stable
v2026.06.19  2026-06-09 16:30  stable
v2026.06.18  2026-06-09 14:54  stable
v2026.06.17  2026-06-09 11:29  stable
v2026.06.16  2026-06-09 07:30  stable
v2026.06.15  2026-06-09 06:57  stable
v2026.06.14  2026-06-07 22:01  stable
v2026.06.13  2026-06-07 20:04  stable
v2026.06.12  2026-06-07 16:37  stable
v2026.06.11  2026-06-04 14:37  stable
v2026.06.10  2026-06-04 12:01  stable
v2026.06.09  2026-06-04 06:53  stable
v2026.06.08  2026-06-03 22:21  stable
v2026.06.07  2026-06-02 19:05  stable
v2026.06.05  2026-06-01 19:21  stable
v2026.06.04  2026-06-01 19:16  stable
v2026.06.03  2026-06-01 19:10  stable
v2026.06.02  2026-06-01 19:01  stable
v2026.06.01  2026-06-01 18:49  stable
v2026.05.23  2026-05-31 20:59  stable
v2026.05.22  2026-05-31 20:45  stable
v2026.05.21  2026-05-31 20:13  stable
v2026.05.20  2026-05-31 20:02  stable
v2026.05.19  2026-05-31 19:02  stable
v2026.05.17  2026-05-31 18:45  stable
v2026.05.15  2026-05-31 17:51  stable
v2026.05.14  2026-05-31 17:11  stable
v2026.05.13  2026-05-31 16:53  stable
v2026.05.12  2026-05-31 15:40  stable
v2026.05.11  2026-05-31 12:10  stable
v2026.05.10  2026-05-31 11:02  stable
v2026.05.09  2026-05-31 10:43  stable
v2026.05.08  2026-05-31 10:14  stable
v2026.05.07  2026-05-31 09:54  stable
v2026.05.06  2026-05-31 09:18  stable
v2026.05.05  2026-05-30 23:24  stable
v2026.05.04  2026-05-30 22:49  stable
v2026.05.03  2026-05-30 22:06  stable
v2026.05.02  2026-05-30 21:37  stable
v2026.05.01  2026-05-30 17:15  stable
v2026.05.00  2026-05-30 16:10  stable
```

## Appendix B. How this was gathered (all read-only)

`gh release list --repo JustChr/HAsmartirrigation --limit 200`; `gh api repos/JustChr/HAsmartirrigation/releases --paginate`; GraphQL `repository.releases { isPrerelease isLatest createdAt publishedAt updatedAt tagCommit }`; `issues?state=all`, `issues/comments`, `pulls/comments` (0 rows), `pulls/{n}/reviews` for all 140 PRs (27 reviews); `issues/{n}/timeline` for #181; `compare/{a}...{b}` for each beta-to-stable pair and for 09.17 to 10.01; `commits?since=2026-07-25`; `contents/` for `scripts/release.ps1`, `CONTRIBUTING.md`, `hacs.json`, README and docs; GraphQL discussions and pinned issues; `pulls/{146,150,186}` merge times. Raw JSON and the quote checker are in the session scratchpad (`...\scratchpad\r160\`, not persistent).
