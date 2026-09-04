# Changelog

## 0.12.3 - 2026-09-04

- No addon behavior changes.

## 0.12.2 - 2026-08-29

- No addon behavior changes.

## 0.12.1 - 2026-08-29

- No addon behavior changes.

## 0.12.0 - 2026-08-26

### Added

- Separate Endgame and Leveling content modes with mode-specific tabs and saved
  views. Existing character selections carry forward into the appropriate mode.
- Vendor and token turn-in details now show seller, location, cost, faction,
  reputation, and where required tokens come from.
- Tables adapt their columns when the window or item inspector changes width.
- Wishlist rankings span every phase and relevant spec across the expansion.

### Changed

- Leveling recommendations cover more items and acquisition sources, with
  improved acquisition filtering and fallback recommendations.
- Item details retain more complete stats, sockets, weapon information, and
  effects when an item appears in multiple sources.
- Tier 6 is recognized as the live phase beginning August 27, 2026 at 22:00 UTC.

### Fixed

- Vendor routes prefer complete purchase details and keep the selected
  acquisition path consistent across rows, filters, tooltips, and inspectors.
- Resizing the window and adjusting the layout reuse displayed rows for smoother
  refreshes.

## 0.11.0 - 2026-06-17

### Added

- Computed leveling recommendations with race-aware scoring and fallback item
  names and quality for additional recommended items.

### Changed

- Leveling recommendations suppress invalid projectile and relic rows while
  preserving valid ammo for ranged-weapon classes and hunter quiver support.
- Leveling recommendations cap at level 69 so level-70 raid and endgame items
  stay out of the leveling view.
- `/bbl status` reports both guide-backed leveling rows and computed leveling
  recommendations.

### Fixed

- Recommendation-only detail titles use fallback item quality.
- Unknown race filtering matches generic leveling recommendations without also
  matching race-specific alternatives.

## 0.10.0 - 2026-06-14

### Added

- Leveling gear recommendations with a dedicated Leveling phase view, level
  filtering, source notes, ownership state, wishlist actions, and item details.

### Changed

- Leveling mode uses compact arrow and numeric level controls clamped to 1-70.

## 0.9.1 - 2026-06-14

### Fixed

- Scrolling no longer rebuilds visible rows and hitches during item-list
  navigation.

## 0.9.0 - 2026-06-14

### Changed

- Class and spec selection re-detects the current character on addon load and
  reload while preserving other saved filters.
- Spec detection retries when talent information becomes available after login.

### Fixed

- Druid Feral Combat talent detection selects the Feral DPS list instead of
  another Druid spec.
- Owned-upgrade filtering follows the actual-upgrade planner mode without a
  separate owned-upgrade toggle.

## 0.8.0 - 2026-06-09

### Added

- Multi-select filters for source context, including cost, vendor, zone, and
  reputation where source details are available.
- Actual-upgrade filtering on the upgrades tab to focus on items that improve
  over equipped or already owned items.

### Fixed

- BiS labels preserve top-choice variants such as threat, mitigation, raid DPS,
  and personal DPS while keeping alternatives classified separately.

## 0.7.0 - 2026-06-08

### Added

- Source and zone filters reflect the selected content phase more accurately.
- Lower addon memory use and delayed rendering of views until they are needed.
- First-run class and spec selection uses the current character when saved
  selections still have their initial values.

### Fixed

- Items primarily acquired through PvP can also show raid token turn-in routes
  in their acquisition summaries.

## 0.6.0 - 2026-06-06

### Added

- Phase views distinguish the active content phase from future phases.
- Character selections and current addon state are saved independently for
  each character.

## 0.5.0 - 2026-06-01

### Added

- Quest rewards gated by raid drops show their quest-starting items, including
  tooltip matches and acquisition-phase and source filtering.

### Changed

- Tooltip summaries remove duplicate matches, group weapon slots, and collapse
  consecutive phase ranges where rank is unchanged.
- ALT tooltip expansion shows the full grouped summary.

### Fixed

- Quest reward chains show the appropriate starters for Ancient Petrified Leaf,
  Heart of Hakkar, Eye of C'Thun, The Phylactery of Kel'Thuzad, Magtheridon's
  Head, and Verdant Sphere.
- Hunter BiS lists no longer repeat identical weapon and waist entries.

## 0.4.0 - 2026-05-29

### Added

- Applied enhancement status shows which recommended enhancements are already
  on equipped gear.
- Drop-source filters distinguish raid, heroic dungeon, ordinary dungeon, and
  other drops.

### Changed

- Item tooltip matches prioritize the player's spec, and tooltip spec filters
  default to all enabled.
- Enhancement views use clearer wording and acquisition badges, with expanded
  enchant source details.

### Fixed

- Crafted item availability and enhancement acquisition badges reflect their
  acquisition routes more accurately.

## 0.3.0 - 2026-05-28

### Added

- A dedicated addon icon and minimap launcher support compatible minimap-button
  managers while retaining the saved button position and visibility.

### Changed

- Tooltip spec settings use an improved layout.
- Source filters offer sources available for the current selection and reset
  unavailable choices when the view changes.

### Fixed

- Consumable recommendations distinguish alternatives more accurately.

## 0.2.0 - 2026-05-28

### Added

- Tooltip settings select exactly which class and spec matches appear.
- Tooltip summaries group repeated matches by class, spec, and slot, with ALT
  expansion for full details.

### Changed

- Gear, planner, source, reputation, and access-path displays handle more item
  and acquisition cases.
- BiS annotations stay on primary item tooltips to avoid interfering with
  comparison and auxiliary tooltips.

### Fixed

- Addon tooltip errors no longer interrupt other tooltip updates.
- Spec filter headings align class labels with their All/None controls.
- Source and reputation details are more consistent across acquisition filters
  and access checks.

## 0.1.0 - 2026-05-27

### Added

- TBC Anniversary BiS browser for class, spec, phase, and slot lists.
- Gear, planner, enhance, wishlist, and settings tabs.
- Item tooltip integration with selected-spec ordering and ALT expansion.
- Minimap button and slash commands: `/bbl`, `/bigbis`, `/bbl status`,
  `/bbl settings`, and `/bbltest`.
- Bank item tracking after opening the bank, plus saved wishlists and ignored
  items.
- Gem, enchant, consumable, and leveling references.
- Acquisition paths for drops, vendors, quests, crafted items, token turn-ins,
  reputation gates, profession gates, and tradeable alternatives.

### Fixed

- BiS lists classify weapon, off-hand, two-hand, ranged, ammo, quiver, and relic
  slots and preserve Best, ranked, PvP, situational, and unrealistic rank groups.
- BiS lists omit duplicate entries, and consumable and leveling labels are
  easier to read.

### Known Limitations

- Planner priority is heuristic and not simulation-backed.
- Leveling references are guidance, not a full route.
- Bank ownership requires opening the bank once per character.
