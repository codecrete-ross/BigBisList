# Changelog

## 0.8.0 - 2026-06-09

### Added

- Multi-select filter facets for source context, including cost, vendor, zone,
  and reputation criteria where source data supports them.
- Actual-upgrade filtering on the upgrades tab so planner targets can focus on
  items that improve over equipped or already owned slot baselines.

### Fixed

- BiS variant classification and display labels now preserve top-choice
  variants such as threat, mitigation, raid DPS, and personal DPS while keeping
  alternatives classified separately.
- Updated generated data for the reviewed BiS variant corrections.

## 0.7.0 - 2026-06-08

### Added

- Phase-aware source filtering so source, zone, reputation, and related filters
  reflect the selected content phase more accurately.
- Runtime data compaction and lazy rendering paths to reduce addon memory use
  and avoid building unused UI rows.
- Player class and spec detection for first-run default selection when the
  saved character selection is still on the built-in fallback.

### Fixed

- PvP-primary items can retain raid token turn-in alternate source evidence for
  acquisition summaries and validation coverage.

## 0.6.0 - 2026-06-06

### Added

- Current-phase awareness so phase-based views can distinguish the active
  content phase from future phases.
- Character-specific current addon state, allowing per-character selections and
  runtime state to remain independent.

### Changed

- Validation now checks canonical phase current-state metadata.
- Refreshed generated Lua for the current phase metadata update.

## 0.5.0 - 2026-06-01

### Added

- Quest starter provenance for BiS-relevant quest rewards gated by raid drops,
  including starter item aliases for tooltip matching.
- Acquisition-phase and source-filter handling for quest rewards that depend on
  starter item drops.
- Validation coverage for quest starter source evidence and duplicate BiS rows.

### Changed

- Tooltip summaries now deduplicate equivalent matches, group weapon slots more
  cleanly, and collapse consecutive phase ranges where the rank is unchanged.
- ALT tooltip expansion now shows the full grouped summary instead of switching
  back to raw repeated rows.

### Data Quality

- Added reviewed quest starter overrides for Ancient Petrified Leaf, Heart of
  Hakkar, Eye of C'Thun, The Phylactery of Kel'Thuzad, Magtheridon's Head, and
  Verdant Sphere reward chains.
- Removed duplicate Hunter BiS entries that repeated identical item/context
  rows across weapon and waist slots.
- Refreshed generated Lua from the audited canonical data set.

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
