# Big BiS List

Big BiS List is an in-game gearing companion for World of Warcraft. It shows
gear recommendations, acquisition details, item tooltip matches, ownership,
and a priority planner.

The `0.15.0` public prerelease includes TBC Anniversary (interface `20506`)
and WoW Forever (interface `16001`). Forever is available as a local prerelease
while leveling coverage review and in-game acceptance are pending.

## Install

Install via CurseForge. For a development install, copy the root addon files
into your Anniversary client:

```text
World of Warcraft\_anniversary_\Interface\AddOns\BigBiSList
```

The Anniversary folder must contain `BigBiSList.toc` directly inside it.
CurseForge builds the release package from the Git tag and root `.pkgmeta`.

For a local Forever prerelease, run `scripts/deploy.ps1 -Flavor forever
-Prerelease -NoClean`. The script installs `BigBiSList_Camelot.toc` and its files
in `_forever_\Interface\AddOns\BigBiSList`. Each client uses bundled data and
keeps its own saves.

In game, use `/bbl` or `/bigbis` to open the main window. Use `/bbl status` to
print the loaded data summary and `/bbltest` for a basic saved-variable smoke
test.

## Features

- Phase-based TBC Anniversary BiS lists from Pre-Raid through Sunwell, with Pre-Raid automatically following live content.
- WoW Forever Leveling and level-60 Pre-Raid gear for 28 profiles, with race,
  faction, and route eligibility. Supported specs can use active talent ranks
  when comparing gear.
- Forever ranks by spec, activity, and character level. Details shows which
  stats drive a swap and when a stronger option appears. Item tooltips identify
  tied and projected ranks, compare future gear at its first usable level, and
  show which quest choices serve each activity.
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

### TBC Anniversary

The Anniversary dataset uses audited Wowhead snapshots and reviewed
corrections. It includes the following recommendations and item records.

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

### WoW Forever

The Forever dataset includes reviewed Pre-Raid coverage for all 28 profiles
and leveling recommendations from 1 to 59. Some slots below level 20 still
have unreviewed availability. See the [leveling review](docs/internal/forever-leveling.md)
and [scoring guide](docs/internal/forever-scoring.md) for the remaining work.

## Known Limitations

- Leveling guidance covers gear pickups and their recorded acquisition steps.
- Planner priority estimates upgrade value from the reviewed recommendations.
- Bank ownership only includes banked items after the character opens the bank.
- Forever effects with an unverified score are marked conditional. Exact rolls
  awaiting catalog review can show a projected rank from their readable stats.
- No profile import/export is included in `0.15.0`.

## Release Checks

The authoritative release checklist is
[`docs/internal/release-process.md`](docs/internal/release-process.md). Run its
single release gate from the repository root before tagging or releasing:

```powershell
.\scripts\check-release.ps1 -Version 0.15.0 -Flavor forever -FullData
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
python tools/generate_lua.py --flavor anniversary
python tools/generate_lua.py --flavor forever
```

The scraper can fetch, reprocess, import, and audit Wowhead snapshots:

```powershell
python tools/scrape_wowhead.py coverage --flavor anniversary --summary --strict
python tools/scrape_wowhead.py fetch --flavor anniversary
python tools/scrape_wowhead.py reprocess --flavor anniversary --input-dir data/raw/wowhead/full_bis
python tools/scrape_wowhead.py import --flavor anniversary --input-dir data/raw/wowhead/full_bis --family bis_lists
python tools/scrape_wowhead.py audit --flavor anniversary
```

Full HTML cache files live under `data/raw/wowhead/html_cache` and are ignored
by git.

## Project Identity

- Display name: `Big BiS List`
- Addon folder: `BigBiSList`
- Source layout: addon `.toc` and Lua files at repository root for CurseForge
  auto-packaging
- Target clients: TBC Anniversary (`BigBiSList.toc`) and WoW Forever
  (`BigBiSList_Camelot.toc`)
- Saved variable: `BigBiSListDB`
- Globals: `BigBiSList`, `BigBiSListData`
- Slash commands: `/bigbis`, `/bbl`, `/bbltest`

## License

Big BiS List is All Rights Reserved. See [LICENSE](LICENSE).

Third-party reference material and attribution are documented in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
