# Distributor documentation page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a comprehensive, image-free end-user documentation page for the mechanical water distributor to the Jekyll docs site, wired into the Configuration index, the Experimental page, and the Previous/Next breadcrumb chain.

**Architecture:** One new Markdown page `docs/configuration-distributors.md` (Jekyll `layout: default` + a breadcrumb header, like every sibling `configuration-*.md`), plus three small edits to existing pages so it is reachable and correctly framed as an opt-in experimental feature. Docs only — no code, no build.

**Tech Stack:** Jekyll (GitHub Pages), Markdown.

**Spec:** `docs/superpowers/specs/2026-07-08-distributor-docs-design.md`

---

## Notes for the author
- Voice: match the existing docs — second person, concise, **bold** for UI labels/tabs, back-ticks for entity/field/service names, `[text](sibling.md)` cross-links. No images, no screenshot placeholders (user decision).
- Facts must match the shipped b28 behaviour. Ground truth for wording already exists in i18n (`panels.distributors.*` in `frontend/localize/languages/en.json`) and the code (`distributor.py`); reuse that phrasing where natural.
- Breadcrumb chain after this change: `Sensor groups → Experimental → Distributors → Usage`. `usage.md` has no breadcrumb block, so nothing to change there.

## File structure
- Create: `docs/configuration-distributors.md` — the reference page.
- Modify: `docs/configuration-experimental.md` — intro framing + a short distributors subsection + both breadcrumb instances (Next → Distributors).
- Modify: `docs/configuration.md` — add Distributors to the Setup-tabs list + the reading order.

---

## Task 1: Author `docs/configuration-distributors.md`

**Files:** Create `docs/configuration-distributors.md`

- [ ] **Step 1: Front matter + header.** Start the file exactly with:
```markdown
---
layout: default
title: "Configuration: Distributors"
---
# Mechanical water distributors

> Main page: [Configuration](configuration.md)<br/>
> Previous: [Experimental](configuration-experimental.md)<br/>
> Next: [Usage](usage.md)
```

- [ ] **Step 2: Write the body** — eleven `##`/`###` sections, in this order, each stating at least the listed facts (expand into clear prose; target ~150–200 lines total):

  1. **Intro / what it is** — a mechanical **indexing / pressure distributor** splits one supply into several outlets and advances to the next outlet each time the water is pulsed **off then on**. Consumer example: the **Gardena Water Distributor**; professional equivalent: K-Rain / FIMCO indexing valves. The device has **no position feedback** — it's a "blind" ring of outlets, so Smart Irrigation *tracks* the position rather than reading it.

  2. **Experimental — read first** (a blockquote callout `> **Experimental.** …`) — the feature is **opt-in** and could **not be fully hardware-tested**; **watch the first days of use closely** and keep the device's **manual override within reach**; you can switch it back **off at any time** without losing data.

  3. **## Enabling it** — turn on **Setup → Experimental → Mechanical water distributors** (off by default). That reveals the **Distributors** setup tab and the per-zone **Water distributor** field. Link: [Experimental](configuration-experimental.md).

  4. **## Creating a distributor** — give it a name and pick how its inlet is driven: **Classic** — Home Assistant opens/closes an inlet `switch`/`valve` entity directly; **Self-closing service** — a **run** (and optional **stop**) script actuates a device that closes itself, and the inlet entity is *watch-only*. Set the **inlet valve** entity (optional in service mode), and the **pulse duration** + **unit** (seconds/minutes).

  5. **## Assigning zones to outlets** — on each zone's settings, the **Water distributor** selector assigns the zone to this distributor; the **outlet numbers** are arranged on the distributor page as a contiguous **1..n** map. A **member zone** is watered *through* its outlet — its own valve and schedule are managed by the distributor. An outlet with **no mapped zone** is passed with a short **skip pulse** (not watered).

  6. **## Commissioning & position tracking** — blind outlets can't report position, so an **advance is counted on the inlet valve's off-edge**. **Set current outlet** re-anchors the tracked position (behind a safety confirm) after you turn the device by hand. The **test run** waters each mapped outlet ~30 s so you can watch it step and read the pause it needs. **Confirm commissioning** to arm automatic cycles. If the position becomes ambiguous, the distributor is marked **uncertain** and must be **re-synced** before the next cycle.

  7. **## Advance pause & skip pulses** — the **advance pause** between outlets must be long enough for the device to physically step (a **10-second floor** is enforced). The **skip pulse** used to pass an unmapped outlet also has a **10-second floor**.

  8. **## Master valve / pump coordination** — a configured **master valve/pump** is switched for the distributor; with **master off after each zone** under sequential/rotating sequencing the pump **cycles per outlet**; and because a distributor feeds **one outlet at a time**, its zones water **in sequence even under parallel sequencing** (plan the supply draw accordingly).

  9. **## Watching the inlet for foreign pulses** — the optional **inlet-watch** reacts when the inlet opens **outside** a Smart Irrigation run, via one of three **watch modes**: **Count it** (advance the tracked position), **Warn** (mark the position uncertain), **Ignore**. Only pulses Home Assistant can actually see are detected — purely mechanical turns at the device stay invisible.

  10. **## Optional flow sensor** — assign the distributor's shared **inlet flow meter** and each outlet's **delivered volume is measured** and credited instead of the time estimate; where the valve can be stopped (a classic inlet, or a self-closing stop-service) the outlet also **stops early** once its target volume is reached. **Caveat:** this path is **rate-only** and **could not be hardware-tested** — treat it as the least-proven part of an already-experimental feature.

  11. **## Troubleshooting & tips** — give the distributor at least **1 bar pressure and 20 l/h flow**; a firm pulse is needed to advance reliably. After turning the device by hand, use **Set current outlet** to re-sync. Under parallel sequencing, remember the distributor still waters its zones in sequence. "**Uncertain**" means the tracked position may be wrong — re-sync (test run + set outlet + confirm) to clear it.

- [ ] **Step 3: Close with the breadcrumb footer** (repeat the header breadcrumb at the end, matching sibling pages):
```markdown
> Main page: [Configuration](configuration.md)<br/>
> Previous: [Experimental](configuration-experimental.md)<br/>
> Next: [Usage](usage.md)
```

- [ ] **Step 4: Sanity-check the page** — headings present, blockquote callout renders, all `[...](*.md)` links point to files that exist (`configuration.md`, `configuration-experimental.md`, `usage.md`, and any others you link). See Task 3 for the link check.

- [ ] **Step 5: Commit**
```bash
git add docs/configuration-distributors.md
git commit -F - <<'MSG'
docs(distributor): add the mechanical water distributor reference page

Comprehensive, image-free page: what it is, enabling the experimental toggle, creating a
distributor (classic vs self-closing), assigning zones to outlets, commissioning &
position tracking, advance/skip pulses, master coordination, inlet-watch modes, optional
flow sensor (rate-only caveat), and troubleshooting.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
MSG
```

---

## Task 2: Wire it into the Experimental page and the Configuration index

**Files:** Modify `docs/configuration-experimental.md`, `docs/configuration.md`

- [ ] **Step 1: Experimental page — accommodate a third, non-bucket toggle.** In `configuration-experimental.md`, the intro (line 11) currently reads:
```markdown
The **Setup → Experimental** tab holds opt-in features that change how each zone's [bucket](how-it-works.md) is filled. They are **off by default** and still being refined, so turn them on one at a time and keep an eye on your zones — you can switch them back off at any time without losing data.
```
Replace it with (broadens the framing so the distributor toggle fits — it is not a bucket feature):
```markdown
The **Setup → Experimental** tab holds opt-in features that are **off by default** and still being refined — turn them on one at a time and keep an eye on things; you can switch them back off at any time without losing data. Two change how each zone's [bucket](how-it-works.md) is filled; a third gates the experimental [mechanical water distributor](configuration-distributors.md) support.
```

- [ ] **Step 2: Experimental page — fix the "Both toggles" line (line 13).** It currently reads:
```markdown
Both toggles are global (they apply to every zone) and take effect from the next calculation or watering event onward.
```
Replace with (the sentence is about the two bucket toggles, not the distributor one):
```markdown
The two bucket toggles are global (they apply to every zone) and take effect from the next calculation or watering event onward.
```

- [ ] **Step 3: Experimental page — add a short distributors subsection.** At the END of the page body, immediately BEFORE the closing breadcrumb block (the `> Main page: …` lines at 52–54), insert:
```markdown
## Mechanical water distributors

Enables Smart Irrigation's support for a **mechanical pressure-distributor** (for example a Gardena Water Distributor) that splits one supply into several outlets. Turning it on reveals the **Distributors** setup tab and a per-zone **Water distributor** field; leaving it off keeps the feature entirely hidden. Unlike the bucket features above this does not change any calculation — it is a new, **experimental** capability that could not be fully hardware-tested, so treat it as a beta and watch the first days of use closely. Full details are on the **[Distributors](configuration-distributors.md)** page.

```

- [ ] **Step 4: Experimental page — repoint BOTH breadcrumb blocks.** The file has the breadcrumb twice (top, lines 7–9; bottom, lines 52–54). In BOTH, change the `Next` line
```markdown
> Next: [Usage](usage.md)
```
to
```markdown
> Next: [Distributors](configuration-distributors.md)
```
(Use `replace_all` or edit both occurrences — there are exactly two.)

- [ ] **Step 5: Configuration index — add Distributors to the Setup-tabs list.** In `configuration.md`, the panel-layout numbered list has items 1–6 (Weather & Location, My Zones, When to Water, Advanced, Experimental, Help). Insert a new item after **My Zones** (item 2) and renumber the following items, OR add it as an explicitly labelled optional item. Concretely, after the "My Zones" list item, add:
```markdown
  3. [**Distributors**](configuration-distributors.md) — *(experimental, off by default)* drive a mechanical water distributor that splits one supply across several outlets, and assign zones to its outlets. Enable it under **Experimental** first.
```
and renumber the subsequent items (When to Water → 4, Advanced → 5, Experimental → 6, Help → 7).

- [ ] **Step 6: Configuration index — mention it in the reading order.** The last paragraph ends: "The [Experimental](configuration-experimental.md) features are optional extras you can explore once the basics work." Append one sentence:
```markdown
 If you use a mechanical water distributor, see [Distributors](configuration-distributors.md) (also opt-in, enabled from the Experimental tab).
```

- [ ] **Step 7: Commit**
```bash
git add docs/configuration-experimental.md docs/configuration.md
git commit -F - <<'MSG'
docs(distributor): link the distributor page from the experimental page and index

Broaden the Experimental intro to cover a third, non-bucket toggle, add a short
distributors subsection, repoint the Experimental "Next" breadcrumb to Distributors, and
list Distributors in the Configuration index (tabs + reading order).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
MSG
```

---

## Task 3: Verify links + breadcrumb chain

**Files:** none (verification only)

- [ ] **Step 1: Every internal link in the new/edited files resolves to an existing file.**
```bash
cd /d/Entwicklung/HASI/HAsmartirrigation/docs
for f in configuration-distributors.md configuration-experimental.md configuration.md; do
  grep -oE '\]\(([a-z0-9-]+\.md)(#[a-z0-9-]+)?\)' "$f" | sed -E 's/^\]\(//; s/(#.*)?\)$//' | sort -u | while read -r t; do
    [ -f "$t" ] && echo "OK   $f -> $t" || echo "MISS $f -> $t"
  done
done | grep -E "MISS" || echo "all internal links resolve"
```
Expected: `all internal links resolve`.

- [ ] **Step 2: Breadcrumb chain is consistent both directions.**
```bash
cd /d/Entwicklung/HASI/HAsmartirrigation/docs
echo "experimental Next:"; grep -E "Next:" configuration-experimental.md
echo "distributors Prev/Next:"; grep -E "Previous:|Next:" configuration-distributors.md
```
Expected: experimental `Next: [Distributors]` (both occurrences); distributors `Previous: [Experimental]` + `Next: [Usage]`.

- [ ] **Step 3: The new page has all eleven sections.**
```bash
grep -cE "^#{1,3} " configuration-distributors.md
```
Expected: ≥ 12 headings (the H1 + eleven section headings; sub-`###` add more).

- [ ] **Step 4:** No commit needed (verification only). If Steps 1–3 reveal a problem, fix it and amend the relevant Task 1/2 commit.

---

## Self-review

- **Spec coverage:** new page with the 11 sections → Task 1 ✓; experimental-page subsection + Next breadcrumb → Task 2 Steps 3–4 ✓; the "keep the bucket framing accurate" note → Task 2 Steps 1–2 ✓; index tabs + reading order → Task 2 Steps 5–6 ✓; breadcrumb chain (Experimental→Distributors→Usage; usage has no breadcrumb so unchanged) → Task 1 header/footer + Task 2 Step 4 + Task 3 ✓; no images → honored throughout ✓; link/breadcrumb verification → Task 3 ✓. `navigation.yml` correctly untouched (spec out-of-scope).
- **Placeholder scan:** the companion edits are verbatim old→new; the new-page body is a concrete per-section fact brief (author expands to prose) — appropriate for a docs deliverable, not a code placeholder.
- **Consistency:** breadcrumb target `configuration-distributors.md` / label `Distributors` used identically everywhere; the file created in Task 1 is exactly what Task 2/3 link to.
