# Internal Provenance

This document records how Big BiS List source evidence, generated data, and
agent-authored decisions should remain traceable.

## Data Lineage

The intended data path is:

```text
Wowhead TBC guide/item/spell pages
-> normalized raw snapshots in data/raw/wowhead
-> scraper/import tooling in tools/scrape_wowhead.py
-> canonical JSON in data/canonical
-> generated Data.lua via tools/generate_lua.py
-> addon runtime reads BigBiSListData
```

`data/canonical/scrape_manifest.json` defines the registered source surface and
source policy. `tools/manifest_coverage.py` and
`tools/scrape_wowhead.py coverage --summary --strict` verify that the expected
class/spec/phase matrix is covered.

## Source Hierarchy

- Wowhead TBC guide pages are canonical for BiS rankings and contextual guide
  rows.
- Wowhead TBC item and spell pages are canonical for acquisition data,
  prerequisites, costs, vendors, quests, drops, recipes, and related source
  details.
- Guide source cells are retained as evidence and may fill gaps when item or
  spell page data is missing.
- Reviewed overrides apply last and must be explicit.

When sources conflict, prefer item/spell acquisition pages for acquisition
details and guide pages for ranking/context. If neither source is sufficient,
use an override and record why.

### Duplicate Snapshot Fidelity

Multiple committed snapshots may describe the same item. Their filesystem or
input-directory order must never decide which values survive import. Merging
must be deterministic and order-independent under these rules:

- Select the highest-fidelity evidence for each field. For item statistics,
  fidelity includes populated primary stats, damage and DPS, armor, sockets,
  weapon fields, effects, and parse confidence.
- A lower-fidelity snapshot may fill missing list, source, cost, requirement, or
  other complementary metadata, but it must not erase or replace populated
  higher-fidelity evidence with empty or less-specific values.
- Preserve distinct compatible evidence when sources contribute different
  fields; do not reduce a rich record to whichever whole snapshot happens to be
  read last.
- Apply reviewed overrides after the deterministic evidence merge.

The item-corpus audit compares canonical output with the richest committed
snapshot evidence. A best-source fidelity regression is a release-blocking
error even when aggregate row counts still look plausible.

### Content Schedule Evidence

Tier 6's Anniversary launch is recorded as `2026-08-27T22:00:00Z` (Unix epoch
`1787868000`) from Blizzard's official [August 2026 content
announcement](https://worldofwarcraft.blizzard.com/en-us/news/24291476). The
release schedule review was completed on 2026-08-26, with runtime coverage for
the instant immediately before launch and the launch instant itself.

## Override Policy

Every manual correction in `data/canonical/overrides.json` must include:

- stable `id`
- `type`
- precise `target`
- human-readable `reason`
- `reviewer`
- `reviewed_at`
- `source_url`

Overrides should be narrow. They should correct source gaps, source aliases,
rank/context ambiguities, or known source mistakes without becoming a parallel
data-entry system.

## Attribution Boundary

`vendor/reference/BIS-TBC-1.15` is included for parity checks and provenance
review. It does not define the Big BiS List addon identity, package name, saved
variables, globals, or license. Third-party attribution remains in
`THIRD_PARTY_NOTICES.md`; internal provenance details belong here and in
canonical data files.

## Agent-Work Provenance

Significant agent-authored decisions should be captured outside transient chat:

- Commit messages should state the durable reason for non-obvious changes.
- PR descriptions should summarize source, tooling, and validation impacts.
- Internal docs should be updated when governance or provenance policy changes.
- Data changes should be traceable to manifest entries, snapshots, import logic,
  overrides, and validation output.

Do not cite an agent chat as the only source of truth for data corrections or
governance changes. If a chat produced an important decision, move that decision
into an internal doc, an override reason, a test name, or a PR note.

## Validation Evidence

`docs/internal/release-process.md` is the authoritative release checklist.
Before tagging, run `scripts/check-release.ps1 -Version <version> -FullData`;
the script owns the exact automated command set so this document cannot drift
into a competing checklist. Record the gate result and any explicitly accepted
skip, including its reason, in the release handoff or PR.
