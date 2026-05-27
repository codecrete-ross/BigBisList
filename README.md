# Big BiS List

Big BiS List is an in-game TBC Anniversary gearing companion for World of
Warcraft. It shows phase-based BiS lists, acquisition details, gem/enchant and
consumable recommendations, item tooltip matches, ownership state, and a simple
priority planner.

This repository is prepared for the `0.1.0` prerelease. This addon targets TBC
Anniversary only. The `0.1.0` package uses WoW interface `20505`, matching the
local `wow_anniversary` 2.5.5 client, and is not intended for Retail, Classic
Era, Cataclysm Classic, Mists Classic, or other WoW releases.

## Install

Install via CurseForge, or copy the addon folder to your Anniversary client:

```text
World of Warcraft\_anniversary_\Interface\AddOns\BigBiSList
```

The folder must contain `BigBiSList.toc` directly inside it. Do not copy the
repository root or the `addon` parent folder into `Interface\AddOns`.

In game, use `/bbl` or `/bigbis` to open the main window. Use `/bbl status` to
print the loaded data summary and `/bbltest` for a basic saved-variable smoke
test.

## Features

- Phase-based TBC Anniversary BiS lists from Pre-Raid through Sunwell.
- Class, spec, phase, slot, source, zone, rank, ownership, binding, faction, and
  longevity filters.
- Gear view for currently equipped slots.
- Priority planner for missing and future-use items.
- Wishlist and ignore actions from item rows and details.
- Item tooltip matches for selected and alternate specs.
- Bank cache support after opening the bank once.
- Gem, enchant, and consumable recommendations with source and prerequisite
  details.
- Source-aware acquisition paths for drops, vendors, quests, crafted items,
  token turn-ins, reputation gates, profession gates, and tradeable alternatives.

## Data Scope

The `0.1.0` prerelease ships with generated data from audited local Wowhead TBC
snapshots plus curated overrides where source data needed correction.

Current generated data includes:

- 9 classes
- 28 specs
- 6 phases
- 4,549 BiS slot lists
- 2,382 item records
- 666 gem rows
- 1,776 enchant rows
- 1,536 consumable rows
- 1,337 leveling rows

The data pipeline validates manifest coverage, source requirements, duplicate
rows, slot compatibility, rank groups, and generated Lua consistency before
release.

## Known Limitations

- This prerelease is data-heavy and should still be checked against in-game
  behavior during normal play.
- Leveling entries are reference guidance, not a full questing route.
- Planner priority is heuristic; it is not a simulator and does not replace
  class-specific stat weights.
- Bank ownership only includes banked items after the character opens the bank.
- No profile import/export is included in `0.1.0`.

## Release Checks

Run these from the repository root before tagging or packaging:

```powershell
python -m unittest discover -s tests
python tools/validate_data.py --json
python tools/generate_lua.py --check
python tools/scrape_wowhead.py audit
python tools/scrape_wowhead.py coverage --summary --strict
```

Build the CurseForge/GitHub upload zip:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\package.ps1 -Version 0.1.0
```

The package script writes `dist\BigBiSList-0.1.0.zip`. The archive root is
`BigBiSList/`, and `BigBiSList.toc` is directly inside that folder.

For the full data audit, also run snapshot and requirements audits for each
family:

```powershell
python tools/scrape_wowhead.py snapshot-audit --input-dir data/raw/wowhead/full_bis --family bis_lists
python tools/scrape_wowhead.py snapshot-audit --input-dir data/raw/wowhead/full_gems --family gems
python tools/scrape_wowhead.py snapshot-audit --input-dir data/raw/wowhead/full_enchants --family enchants
python tools/scrape_wowhead.py snapshot-audit --input-dir data/raw/wowhead/full_consumables --family consumables
python tools/scrape_wowhead.py snapshot-audit --input-dir data/raw/wowhead/full_leveling --family leveling

python tools/scrape_wowhead.py requirements-audit --input-dir data/raw/wowhead/full_bis --family bis_lists
python tools/scrape_wowhead.py requirements-audit --input-dir data/raw/wowhead/full_gems --family gems
python tools/scrape_wowhead.py requirements-audit --input-dir data/raw/wowhead/full_enchants --family enchants
python tools/scrape_wowhead.py requirements-audit --input-dir data/raw/wowhead/full_consumables --family consumables
python tools/scrape_wowhead.py requirements-audit --input-dir data/raw/wowhead/full_leveling --family leveling
```

## Development

Regenerate addon data after canonical JSON changes:

```powershell
python tools/generate_lua.py
```

The scraper can fetch, reprocess, import, and audit Wowhead snapshots:

```powershell
python tools/scrape_wowhead.py coverage --summary --strict
python tools/scrape_wowhead.py fetch
python tools/scrape_wowhead.py reprocess --input-dir data/raw/wowhead/full_bis
python tools/scrape_wowhead.py import --input-dir data/raw/wowhead/full_bis --family bis_lists
python tools/scrape_wowhead.py audit
```

Full HTML cache files live under `data/raw/wowhead/html_cache` and are ignored
by git.

## Project Identity

- Display name: `Big BiS List`
- Folder/root: `BigBiSList`
- Target client: TBC Anniversary only (`## Interface: 20505`)
- Saved variable: `BigBiSListDB`
- Globals: `BigBiSList`, `BigBiSListData`
- Slash commands: `/bigbis`, `/bbl`, `/bbltest`

## License

Big BiS List is All Rights Reserved. See [LICENSE](LICENSE).

Third-party reference material and attribution are documented in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
