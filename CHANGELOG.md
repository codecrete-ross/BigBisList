# Changelog

## 0.2.0 - 2026-05-28

### Added

- Tooltip settings for choosing exactly which class/spec matches should appear.
- Grouped tooltip summaries that collapse repeated phase matches by class, spec,
  and slot while preserving ALT expansion for full details.
- Gear, planner, source, reputation, and access-path UI hardening from the
  prerelease data cleanup work.
- Internal release governance and a local deploy script for Anniversary client
  smoke testing.

### Changed

- Big BiS tooltip annotations now stay on the primary item tooltip frames to
  avoid interfering with comparison and auxiliary tooltip layouts.
- Tooltip callbacks are protected so Big BiS errors cannot break the tooltip
  hook chain.
- Settings class/spec filter headers align class labels with their All/None
  controls.

### Data Quality

- Normalized source and reputation data used by acquisition filters and access
  checks.
- Refreshed generated Lua from the audited canonical data set.

## 0.1.0 - Release

Initial public release for Big BiS List. This release targets TBC
Anniversary only using WoW interface `20505`.

### Added

- In-game TBC Anniversary BiS browser for class, spec, phase, and slot lists.
- Gear, planner, enhance, wishlist, and settings tabs.
- Item tooltip integration with selected-spec ordering and ALT expansion.
- Minimap button and slash commands: `/bbl`, `/bigbis`, `/bbl status`,
  `/bbl settings`, and `/bbltest`.
- Bank cache support after opening the bank.
- Wishlist and ignored-item saved variables.
- Gem, enchant, consumable, and leveling reference data.
- Source-aware acquisition paths, including drops, vendors, quests, crafted
  items, token turn-ins, reputation gates, profession gates, and tradeable
  alternatives.
- Audited generated data from local Wowhead TBC snapshots.
- CurseForge-compatible root addon layout for repository webhook packaging.

### Data Quality

- Corrected nested Wowhead table parsing so child rows are not imported under
  parent slots.
- Added weapon, off-hand, two-hand, ranged, ammo, quiver, and relic-aware slot
  derivation.
- Preserved `Best`, ranked, PvP, situational, and unrealistic rank groups.
- Removed duplicate same-item BiS rows from canonical lists.
- Cleaned prose-sized consumable labels and malformed leveling text artifacts.
- Added strict audits for manifest coverage, source requirements, rank groups,
  slot compatibility, duplicate rows, and generated Lua consistency.

### Known Limitations

- This release should be checked during normal in-game use.
- Planner priority is heuristic and not simulation-backed.
- Leveling data is reference guidance, not a full route.
- Bank ownership requires opening the bank once per character.
