# Big BiS List

Big BiS List is a renamed, coexistable TBC Anniversary BiS addon scaffold.
This repository is starting from tooling and data provenance rather than
hand-maintained generated Lua.

## Current Status

This first development pass provides:

- A minimal loadable WoW addon shell in `addon/BigBiSList`.
- Canonical JSON seed data in `data/canonical`.
- JSON schema documents in `data/schema`.
- Python tooling for validation, deterministic Lua generation, reference
  count reporting, parity reporting, and a normalized Wowhead scraping
  pipeline.
- Tests for canonical data, generation, reference counts, and Druid idol
  situational BiS handling.

Full UI/runtime feature parity is intentionally not implemented yet.

## Reference Baseline

The local `BIS-TBC-Anniversary` 1.15 addon is used only as a parity and
runtime reference. It should live in:

`vendor/reference/BIS-TBC-1.15`

The canonical data source for Big BiS List is expected to be Wowhead TBC guide
data plus explicit curated overrides where Wowhead does not expose clean data.

## Tooling

Run the local validation and test flow from the repository root:

```powershell
python tools/validate_data.py
python tools/generate_lua.py --check
python tools/reference_counts.py
python tools/parity_report.py
python -m unittest discover -s tests
```

Regenerate the addon data file:

```powershell
python tools/generate_lua.py
```

Run the scraper workflow:

```powershell
python tools/scrape_wowhead.py coverage --summary
python tools/scrape_wowhead.py fetch
python tools/scrape_wowhead.py import --dry-run
python tools/scrape_wowhead.py audit
```

`coverage` is fully offline. It reports the explicit manifest units required
before scraping: gear BiS, gems, enchants, consumables, and leveling for every
class/spec/phase, plus global class and phase sources. Gear BiS coverage is now
registered for every class/spec/phase unit; full strict coverage still fails
until gems, enchants, consumables, leveling, classes, and phases are registered.

Check only the gear BiS registry:

```powershell
python tools/scrape_wowhead.py coverage --family bis_lists --strict --summary
```

The fetch command writes normalized JSON snapshots to `data/raw/wowhead`.
Full HTML cache files are stored under `data/raw/wowhead/html_cache` and are
ignored by git.

## Addon Shell

The addon shell exposes:

- Display name: `Big BiS List`
- Folder/root: `BigBiSList`
- Saved variable: `BigBiSListDB`
- Globals: `BigBiSList`, `BigBiSListData`
- Slash commands: `/bigbis`, `/bbl`, `/bbltest`

## Attribution

This project preserves attribution to `BIS-TBC-Anniversary`, Hellixoid, Dweem,
csm_sudo, and future data contributors. The reference addon is MIT licensed.
Big BiS List should keep a distinct name, package root, saved variable, and
description when published.
