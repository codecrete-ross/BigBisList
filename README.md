# Big BiS List

Big BiS List is an in-game TBC Anniversary gearing companion for World of
Warcraft. It shows phase-based BiS lists, acquisition details, gem/enchant and
consumable recommendations, item tooltip matches, ownership state, and a simple
priority planner.

This repository is prepared for the `0.13.0` release. This addon targets TBC
Anniversary only. The `0.13.0` package uses WoW interface `20506`, matching the
local `wow_anniversary` 2.5.6 client, and is not intended for Retail, Classic
Era, Cataclysm Classic, Mists Classic, or other WoW releases.

## Install

Install via CurseForge. For a development install, copy the root addon files
into your Anniversary client:

```text
World of Warcraft\_anniversary_\Interface\AddOns\BigBiSList
```

The folder must contain `BigBiSList.toc` directly inside it. CurseForge's
repository packager builds the installable file from the Git tag and root
`.pkgmeta`; generated zip files are not committed or required for release.

In game, use `/bbl` or `/bigbis` to open the main window. Use `/bbl status` to
print the loaded data summary and `/bbltest` for a basic saved-variable smoke
test.

## Features

- Phase-based TBC Anniversary BiS lists from Pre-Raid through Sunwell, with Pre-Raid automatically following live content.
- Leveling mode with guide-backed gear pickups, computed item recommendations,
  and level controls.
- Class, spec, phase, slot, source, zone, reputation, rank, ownership, BoE, and
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
- Quest starter provenance for raid-gated quest rewards.

## Data Scope

The `0.13.0` release ships with generated data from audited local Wowhead TBC
snapshots plus curated overrides where source data needed correction.

Current generated data includes:

- 9 classes
- 28 specs
- 6 phases
- 8,274 BiS slot lists
- 2,672 item records
- 15,109 item stat records
- 921 gem rows
- 1,990 enchant rows
- 1,518 consumable rows
- 1,337 leveling rows
- 456 guide-backed leveling gear rows
- 42,567 computed leveling recommendations

The data pipeline validates manifest coverage, source requirements, duplicate
rows, slot compatibility, rank groups, and generated Lua consistency before
release.

## Known Limitations

- This release is data-heavy and should still be checked against in-game
  behavior during normal play.
- Leveling entries are reference guidance, not a full questing route.
- Planner priority is heuristic; it is not a simulator and does not replace
  class-specific stat weights.
- Bank ownership only includes banked items after the character opens the bank.
- No profile import/export is included in `0.13.0`.

## Release Checks

The authoritative release checklist is
[`docs/internal/release-process.md`](docs/internal/release-process.md). Run its
single release gate from the repository root before tagging or releasing:

```powershell
.\scripts\check-release.ps1 -Version 0.13.0 -FullData
```

`CHANGELOG.md` preserves the complete history of player-observable addon
behavior, excluding internal development work. Generate `RELEASE_NOTES.md` with
`tools/generate_release_notes.py` during release preparation and use it for
GitHub release notes. It retains every version section in the current major/minor
line, so patches preserve that line's earlier changes. A version with no addon
behavior changes says so in its own section. CurseForge
automatically ingests the pushed Git tag, package metadata, and changelog
through the repository webhook. The release process has no manual CurseForge
upload or author-UI step.

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
- Addon folder: `BigBiSList`
- Source layout: addon `.toc` and Lua files at repository root for CurseForge
  auto-packaging
- Target client: TBC Anniversary only (`## Interface: 20506`)
- Saved variable: `BigBiSListDB`
- Globals: `BigBiSList`, `BigBiSListData`
- Slash commands: `/bigbis`, `/bbl`, `/bbltest`

## License

Big BiS List is All Rights Reserved. See [LICENSE](LICENSE).

Third-party reference material and attribution are documented in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
