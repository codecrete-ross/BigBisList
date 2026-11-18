# Character-aware gear scoring for WoW Forever

The local prerelease pilots Protection and Retribution Paladin, Enhancement
and Restoration Shaman, and Protection Warrior while full leveling coverage is deferred. Use
the [leveling guide](forever-leveling.md#audits-and-deployment) for the strict
audits. Extend personalized mechanics to the other 23 profiles after reviewing
the pilot and its gameplay results.

## Local pilot on build 1.60.1.70959

The November 17 build review compared the exact client tables and verified
hotfix caches for 70938 and 70959. All 1,014 published item IDs had matching
equipment facts. The published item effect links and the quest records present
in the caches matched. The only base training table change was the Rogue
Poisons skill tier. All eight existing scoring contexts kept the same modeled
inputs. The mechanics snapshot binds that comparison to the reviewed
equipment rules and published gear. Changing those inputs calls for a new
comparison.
[Build-pinned client tables](https://wago.tools/db2/ItemSparse/csv?build=1.60.1.70959) ·
[Verified hotfix caches](https://www.raidbots.com/api/dbcache/verified)

Both contexts start with the reviewed role weights. Retribution's pilot gives
Intellect an independent mana value of 0.5 score units per point and uses
the reviewed pre-raid spell power weight for spell damage in both contexts.
Champion of the Light adds 12%, 24%, 36%, 48%, or 60% of Intellect as spell
damage at ranks one through five. Enhancement applies Ancestral Knowledge
before Mental Dexterity. Mental Dexterity uses the current 33%, 66%, and 100%
rank values from hotfix 113722. Restoration values the gear-derived healing
values affected by Purification and the mana budget affected by Tidal
Focus. The latter estimates available healing casts at a fixed cost mix.
Protection Warrior uses the Defensive Stance preset. With a shield equipped,
Defiance scales melee weapon DPS and Attack Power. The level-63 pre-raid
benchmark gives 14 Attack Power the same value as 1 raw autoattack DPS and caps
melee hit at 8%. Strength contributes 2 Attack Power and 0.05 Block Value with a
shield equipped. Direct Attack Power scaling on Sunder Armor and other
abilities needs a rotation estimate.
[Forever Protection Warrior stat guide](https://www.icy-veins.com/wow-forever/protection-warrior-tank-pve-stat-priority)

Protection Paladin reads Divine Intellect, Divine Strength, Toughness, and
Shield Specialization from the active talent tree. The first three add 2–10%
to Intellect, Strength, or armor from gear. Shield Specialization adds 15%
or 30% to gear-derived Block Value with a shield equipped. The level-42
Human test scores Guise of Battle at 58.31 and Icemetal Barbute at 57.98 with
no Toughness. At two ranks, Barbute leads 59.07 to 59.02. Pre-raid reuses the
reviewed leveling coefficients for mana and Holy damage. The block-based mana
return needs a reviewed block and Holy Strike cadence.
[Forever Paladin development notes](https://us.forums.blizzard.com/en/wow/t/wow-forever-beta-development-notes-%E2%80%93-updated-november-2/2360696)

The current model evaluates Human Spirit's 10% Spirit increase and the
three-piece Lightforge Armor and Battlegear of Valor bonuses. The latter add
18 Spell Power and 15 Strength respectively. Mindfulness now has verified
17%, 33%, and 50% ranks. Its impact on effective Spirit needs the time spent
inside the five-second rule. Random suffix scoring still needs an obtainable
Forever variant with a confirmed ID and stats.

Proc, set, and cap values still need encounter evidence. The first proc
fixture captures Judgement of Command as a melee on-hit trigger. Numeric proc
scoring needs a reviewed encounter estimate for trigger rates. Flat permanent
enchant stats use the same build's client records. Unreadable gear, unreviewed
enchant effects, unsupported builds, and manual level previews use the existing
reference rankings.
[November 13 Blizzard hotfixes](https://us.forums.blizzard.com/en/wow/t/wow-forever-hotfixes-november-13-2026/2403040/10)

For a bounded, cache-first mechanics refresh and the current review status:

```powershell
python tools/scrape_wowhead.py collect-mechanics --flavor forever
python tools/scrape_wowhead.py scoring-audit --flavor forever
```

Add `--online` for the public sources and `--write` to register the staged
evidence. The scoring audit prints a digest for each context for use in review.
The imported data and generator require the reviewed digest and bound evidence
before compiling the active candidate pools.

## Reference weight verification

Forever's gear guide ranks compatible items with reviewed routes against the
default weights for its selected spec and level or phase. The pool is shared
across browsing filters. Compare Slot retains the exact equipped reference
and shows the live swap estimate when that comparison has a reviewed model.
My Gear uses the same reference weights for its outfit score and respects
weapon configurations and unique-equip limits when finding the benchmark.
Builds shows authored outfits and tracks exact copies independently of rank.

The Zockify Retribution Pre-Raid review identified several pieces outside the
verified item and route catalog. The first tracked build uses a separately
authored Lightforge dungeon setup with a reviewed three-piece bonus and
acquisition routes for every target. Big Bad Pauldrons uses the observed
Forever server tooltip and the published OneForAll dungeon loot record.
[Zockify Retribution](https://www.zockify.com/forever/paladin/retribution/)
· [Big Bad Pauldrons tooltip](https://bindonforever.com/item/9476)
· [Zul’Farrak loot record](https://guide.wow4ever.se/en/items/9476)

Bag and bank arrows require a legal swap with both a positive total change
and a meaningful role stat gain. The minimum is two role stat points and
five percent of the displaced role score. A role gain that rounds to 0.1
points qualifies for a genuinely empty slot. Defensive stats contribute to
this threshold for tanks. Gold BiS uses the item’s explicit guide approval.

The leveling scorer applies character and route eligibility before ranking by
the weighted sum of verified flat stats. It keeps the first three choices and
positive-score alternatives within 5% of the top score. Item level, name, and
ID break ties after score. Best Overall identifies that list. Pre-raid uses a
separate profile and publishes the reviewed slot order. The five active-build
profiles evaluate legal swaps against the same loadout baseline for each slot.
Ranged and wand DPS are separate from melee DPS.

The Protection Paladin leveling reference retains the tank survivability
weights and credits Intellect at 0.55, mana per five seconds at 1.6, shield
block value at 0.9, and general spell power, spell damage, and Holy-only
damage at 1.1 per point. Spell and block value weights follow the existing
pre-raid Protection profile. The mana weights reuse existing caster and healer
reference coefficients. These coefficients describe an outdoor leveling
balance. Talent ranks and associated mana refunds still need their own model.
Specialization weight revisions reopen the rankings for that specialization.
[Blizzard Paladin deep dive](https://worldofwarcraft.blizzard.com/en-us/news/24302099/world-of-warcraft-forever-class-deep-dives-paladin)
[Forever leveling stat guidance](https://www.icy-veins.com/wow-forever/protection-paladin-leveling/#stats)

The level-42 Protection reference ranked Guise of Battle (58.31), Icemetal
Barbute (57.98), and Serpentbane Crown (49.04) among 16 reviewed Human head
options. Guise receives 24 points for Stamina, 17.76 for armor, 11.05 for
Agility, and 5.50 for Intellect. Barbute trades some of that Stamina and Agility
for more armor. The 0.33-point lead is sensitive to the balance of armor and
avoidance in the reference weights. Crown scores on 213 armor and 16 Stamina.
Its on-use fire damage is recorded for later encounter review, when cooldown,
time on target, and creature type can be accounted for.
[Guise of Battle item record](https://www.wowhead.com/forever/item=287011/guise-of-battle) ·
[Icemetal Barbute item record](https://www.wowhead.com/forever/item=10763/icemetal-barbute) ·
[Serpentbane Crown item record](https://www.wowhead.com/forever/item=274609/serpentbane-crown)

In the active scorer, rank a ring or trinket by its best legal position.
An explicit equipment comparison uses the selected position so it preserves
the correct other ring or trinket and any equip restrictions. A reviewed suffix
has its own score. An equipped suffix outside the reviewed pool uses the
reference build.

## November 16 guide comparison

- **Enhancement Shaman.** Build 1.60.1.70938 confirms that Mental Quickness
  converts 15% or 30% of Intellect to spell damage and healing. The pilot applies
  both curves after Ancestral Knowledge alongside the post-hotfix Mental
  Dexterity conversion. Enhancement's current weights score the damage
  contribution. With max Ancestral Knowledge and Mental Dexterity, level-42 Orc
  Owl Bracers move from 7.70 to 8.44 at rank two, overtaking Patterned Bronze
  Bracers at 8.00. The outdoor preset puts value on the extra mana, which
  contributes to that reversal. Pre-raid gives 10 Strength 16.00 points and 10
  Intellect 15.46 at all three talents' maximum ranks. Hit still uses a flat
  weight. The next calibration needs separate melee and spell hit curves and
  the weapon-speed effect on Maelstrom Weapon.
  [Icy Veins Enhancement stat guide](https://www.icy-veins.com/wow-forever/enhancement-shaman-melee-dps-pve-stat-priority) ·
  [Mental Quickness spell record](https://www.wowhead.com/forever/spell=30812/mental-quickness)
- **Retribution Paladin.** With Champion of the Light at rank five, 10 Intellect
  keeps its 5.00 points and adds 3.90 points through 6 spell damage. Guide
  priorities vary by Seal and Holy Shock build. Icy Veins and Method also give
  different Intellect-to-spell-crit conversions. Resolve that coefficient from
  client data and measure the spell share before adding separate weights for
  those builds.
  [Icy Veins Retribution stat guide](https://www.icy-veins.com/wow-forever/retribution-paladin-melee-dps-pve-stat-priority) ·
  [Method Retribution stat guide](https://www.method.gg/wow-forever/class-guides/retribution-paladin/bis-gear-and-stats)
- **Restoration Shaman.** The pilot gives positive weight to healing, Crit,
  Intellect, Spirit, and MP5. The guide places Spirit higher with Mindfulness
  and attributes part of Crit's value to Water Shield. Quantifying those
  effects calls for a cast mix, time spent inside the five-second rule, and
  Water Shield returns by rank. The current values describe a fixed healing
  budget.
  [Icy Veins Restoration stat guide](https://www.icy-veins.com/wow-forever/restoration-shaman-healer-pve-stat-priority)
- **Protection Warrior.** Blizzard confirms Attack Power contributes threat
  through Sunder Armor. The pilot's pre-raid preset gives melee weapon DPS a
  threat contribution and prioritizes mitigation on other gear. Calibrate
  Attack Power and Defiance against a sustained Defensive Stance rotation
  before treating these rankings as a threat model.
  [Blizzard Warrior deep dive](https://worldofwarcraft.blizzard.com/en-us/news/24301514) ·
  [Icy Veins Protection Warrior stat guide](https://www.icy-veins.com/wow-forever/protection-warrior-tank-pve-stat-priority)

## Scoring contexts

- **Levels 1–59.** Model outdoor leveling against level-matched enemies over
  combat and recovery. Account for throughput, survivability, and recovery.
- **Level 60 Pre-Raid.** Rank gear obtainable before raiding for first-tier
  raid bosses. Verify the combat tables and caps. Evaluate sustained damage
  for DPS, effective healing and mana for healers, and survivability and threat
  for tanks.

## Evidence and reviews

Extend the existing scraper to register, cache, and normalize mechanics
snapshots in batches. Collect build-pinned client tables, resolved tooltips
for each relevant rank, official hotfixes, and attributable observations. Keep
stable IDs, flavor, build and hotfix revision, source URL, content digest,
collection time, and attribution. Follow the item snapshot workflow described
in the [internal provenance guide](provenance.md).

Inventory effects that can change gear choices, including talents, learned
abilities and ranks, class passives, racials, Legacy perks, forms and stances,
stat conversions, caps, weapon interactions, procs, on-use effects, sets,
enchants, and suffixes. Review triggers, inputs, units, stacking order, and caps.
Use a reviewed estimate for encounter-dependent uptime and rotations. Flag
rankings that unresolved effects could change and keep those effects out of
numeric scoring. Use guides to identify builds, mechanics, and benchmarks.
Record the evidence and calculation behind material differences in order.

Use Champion of the Light as the first conversion fixture. Verify each rank's
Intellect-to-spell-damage coefficient for the supported build, and account for
ordinary Intellect benefits separately. Use Judgement of Command as the first
proc fixture. Record the November 13 hotfix that made it a melee attack that
activates on-hit effects. [Blizzard's Deep Dive recap](https://worldofwarcraft.blizzard.com/en-us/news/24303313),
[November 13 hotfixes](https://worldofwarcraft.blizzard.com/en-us/news/24315281/wow-forever-hotfixes-november-13-2026).

Bind scoring approvals to the supporting mechanics, scenario, profile version,
and candidate pool. Reopen affected reviews when a prerequisite, coefficient,
proc trigger, or eligible candidate changes. Keep diagnostics readable and
reject stale approvals during production import.

## Addon behavior

Use one versioned model for offline reference rankings and in-addon scoring,
with shared Python and Lua test cases. Compare legal loadouts in the same
scenario. Hold the other slots fixed, replace the affected item or weapon pair,
and recalculate conversions, caps, set thresholds, and expected proc value.

Read the active Forever trait configuration by stable trait and spell IDs and
confirmed ranks. Combine it with level, race, learned abilities, persistent
bonuses, and readable equipment. Use the preset's combat assumptions to keep
rankings stable through temporary buffs and form changes. Invalidate cached
scores on relevant talent, level, and equipment events. Use reviewed reference
rankings for previews, unreadable inputs, and unsupported builds.
[Forever client trait API](https://github.com/Gethe/wow-ui-source/blob/forever/Interface/AddOns/Blizzard_APIDocumentationGenerated/SharedTraitsDocumentation.lua).

Filter the full reviewed candidate pool for faction, race, class, acquisition,
and legal equipment before ranking. Apply the existing selection and
tie-breaking policies after scoring. Use the same scoring result in gear
recommendations, comparisons, tooltips, and planner upgrade indicators. Identify
the active or reference build used and show the verified effects behind a
material swap.

### Gear presentation

- Stat tiers use the client rarity palette from poor gray through common white,
  uncommon green, rare blue, epic purple, and legendary orange. Placements
  use the full eligible variant pool and exact score ties. Percent of best uses
  the underlying score. A projected native item enters only its own comparison.
  The tier colors the spec heading and rank in its tooltip block and the rank
  text in the gear views. Item names use their actual item quality. Forever
  tooltip blocks always show their comparisons and matching guide notes.
- Pools with 2–12 scored variants and a positive best score group scores within
  the larger of 0.1 points and 1% of the best score from the group's leader.
  Up to six groups spread across the palette from orange. The bottom group's
  color is the lower of its score-gap tier and rarity index `6 − group count`.
  Wider pools or seven distinct groups use the 25%, 50%, 70%, 85%, and 97%
  score-gap cutoffs. The hover text identifies placement-based colors.
- An arrow indicates an estimated stat gain. The talent icon identifies the spec.
  Gold BiS requires an unconditional approval for the exact variant and guide
  context. A neutral coin identifies a resolved quest choice's best sell value.
- My Gear and Compare Slot follow the selected spec and level. Native item
  acquisition uses the live spec and Leveling weights through 59, then Pre-Raid
  weights. Active-spec quest and direct loot marks compare against worn gear.
  Other acquisition comparisons and the remembered inactive spec use the best
  legal setup from equipment, bags, and the last readable personal bank scan.
  Relevant unreadable inputs defer the gain. An owned variant requires a legal
  gain from adding another copy. The same assessment supplies the mark and its
  tooltip row.
- Visible gear in bags and the open personal bank compares against worn gear
  for the active spec, then the remembered inactive spec. These are existing
  copies. Native containers and Baganator share the same assessment and mark.
  Storage marks are static badges in the upper-right corner. A talent icon has
  a rank-colored border, and an approved item uses a gold BiS label in the same
  footprint. Baganator owns the visibility and priority of its corner widget.
  Redraws with unchanged links and physical locations reuse the assessment.
  Baganator's corner widget requires a current item location and matching exact
  link. Unverified cached character views retain their regular item tooltip.

## Verification and rollout

- Verify all 28 profiles in both contexts. Cover rank zero, partial ranks,
  stacked conversions, cap crossings, forms, weapon restrictions, proc triggers,
  set thresholds, suffixes, and rank reversals. Test a candidate moving into the
  displayed shortlist after personalization.
- Test loadout switches, level previews, unavailable API values, and changed
  mechanics evidence. Compare Python and Lua results. Check startup, first-open,
  and tooltip performance.
- Recheck both strict Forever coverage audits, reproducible generation, and
  Anniversary compatibility. Require recorded user-run live acceptance and the
  authoritative clean-commit `-FullData` gate before public release. Follow the
  [release playbook](release-process.md).
