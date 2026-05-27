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

Before release or data-heavy changes, keep the following checks green:

```powershell
python -m unittest discover -s tests
python tools/validate_data.py --json
python tools/generate_lua.py --check
python tools/scrape_wowhead.py coverage --summary --strict
```

For refreshed snapshots, also run the relevant `snapshot-audit` and
`requirements-audit` commands for the changed family.
