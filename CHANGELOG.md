# Changelog

## 0.1.0 - Prerelease

Initial public prerelease for Big BiS List.

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

- This is a prerelease and should be checked during normal in-game use.
- Planner priority is heuristic and not simulation-backed.
- Leveling data is reference guidance, not a full route.
- Bank ownership requires opening the bank once per character.
