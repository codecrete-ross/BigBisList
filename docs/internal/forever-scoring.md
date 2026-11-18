# Character-aware gear scoring for WoW Forever

The Forever scoring audit covers 28 specializations in two settings. Leveling
uses the selected level's reference weights for outdoor enemies at that level.
Pre-Raid uses level-60 weights for first-tier boss combat. Each approval covers
the fixed gear comparison documented for that setting. Encounter-dependent
effects outside those calculations have separate review requirements.

## Client 1.60.1.70959

The November 17 build review compared the exact client tables and verified
hotfix caches for 70938 and 70959. All 1,014 published item IDs had matching
equipment facts. The published item effect links and the quest records present
in the caches matched. The base training table change was the Rogue Poisons
skill tier. The mechanics snapshot binds that comparison to the reviewed
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

The item effect inventory groups evidence by exact item or suffix, linked spell
where present, and effect text. Permanent dodge and school-specific chance
lines contribute through their appropriate stat channels. The audit includes
exact set spell IDs and reports the flat enchant effects verified for the
client build. The exception queue groups repeat descriptions so one review
can cover the mechanic across multiple items.

A numeric proc or on-use value needs a reviewed estimate for a specific
build, character profile, activity, and level range. Extra attacks use the
effective gain in weapon swings and the contribution per swing. Temporary
stats are valued in the active loadout before applying uptime, including any
shared caps. Multiple temporary stats need observations of the joint states
to receive a combined value. Concurrent on-use estimates need evidence for
the equipped combination and its cooldown interaction. The scorer keeps
unresolved effects conditional and the Guide can still surface reviewed
qualitative effects.

Outdoor and Pre-Raid retain the existing reference profiles. An optional
Dungeon preset has its own level range, evidence, and approval digest. The
selector appears where that preset has passed review. Preferences are saved
by character and specialization, separately for leveling and level 60.
Unreadable gear or talents use reference scores with the available evidence.

The usable Alliance level-49 reference includes both Sword of Serenity and
Thrash Blade. The measured scores for a Human Protection Paladin are 108.44
and 105.57. Thrash's additional swing is confirmed. A realized rate for the
Protection Paladin in the relevant content remains open. The new Guide route
checks use quest acceptance levels and prerequisites. At a choice, the
guaranteed rewards are included in the baseline and winning choices are
evaluated independently for each available scenario and specialization.
[Client-derived Thrash effect](https://wow-forever.gg/db/spells/21919-thrash/)
[November 13 Blizzard hotfixes](https://us.forums.blizzard.com/en/wow/t/wow-forever-hotfixes-november-13-2026/2403040/10)

For a bounded, cache-first mechanics refresh and the current review status:

```powershell
python tools/scrape_wowhead.py collect-mechanics --flavor forever
python tools/scrape_wowhead.py scoring-audit --flavor forever --effects
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

Bag and bank badges require a legal swap with both a positive total change
and a meaningful role stat gain. The minimum is two role stat points and
five percent of the displaced role score. A role gain that rounds to 0.1
points qualifies for a genuinely empty slot. Defensive stats contribute to
this threshold for tanks. Gold BiS uses the item’s explicit guide approval.

The Leveling Guide applies character and route eligibility before ranking
with the reference scoring model. It shows the full qualifying band at 85%
or greater and admits candidates from 70% in **More options**. Reviewed
qualitative effects can also qualify for the list. Pre-Raid gives the
reference placement alongside authored recommendations and their phase
history. Owned exact items outside the verified reference pool can show a
projected placement. Inserting an owned projection leaves the published
placements and denominators stable. Personal comparisons evaluate legal
swaps with the rest of the outfit retained. Ranged and wand DPS are separate
from melee DPS. Weapon speed bonuses use the physical main hand.

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

Feral tank previously inherited the Cat DPS weights after level 9. The Bear
revision uses the tank mitigation and threat coefficients with the reviewed
Feral tank Agility and weapon DPS weights. It values no shield block or parry.
The replay retained the same item and route scope. It updated 409 approvals,
with a change in item choice or order in 211. The level 1–9 casting weights
and other specializations retain their existing approvals. The prior decisions
and both decision digests are in the
[November 17 review batch](../../data/canonical/forever/leveling_ranking_history/029-2026-11-17.json).

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

- Placement and swaps use the reviewed facts for a matching exact variant.
  The client stat API supplies other exact rolls. Forever's importer and
  live reader share the verified flat-passive rules for Defense, Attack
  Power, and spell damage. The live reader fills missing stats from those
  tooltip lines and keeps unresolved effects conditional.
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
- Storage recommendations choose the best legal slot or paired-slot setup from
  worn gear, bags, and the last readable personal bank scan. The spec icon
  requires a meaningful improvement over the worn setup. On an exact tie,
  equipped copies take priority, followed by bags and bank. Another reviewed
  scenario can earn a dotted badge when it favors a meaningfully stronger
  choice for that use. Native containers and Baganator share the same assessment.
  Storage marks are static badges in the upper-right corner. A talent icon has
  a rank-colored border, and an approved item uses a gold BiS label in the same
  footprint. Baganator owns the visibility and priority of its corner widget.
  Redraws with unchanged item facts and physical locations reuse the assessment.
  Storage tooltips match the same physical copy and allow different hyperlink
  formatting. Baganator requires a current item location and agrees with the
  native link and readable GUID. Unverified cached character views retain
  their regular item tooltip.

## Verification and rollout

- The Gear Guide chooses all eligible, role-relevant items at or above 70% of
  the best qualifying score. Under 85% goes under **More options**, along with
  applicable reviewed effects whose numeric ranking falls below that band.
  Ownership and acquisition filters narrow that set. The player's talents and
  gear determine the separate swap estimate and **Within reach** actions.
- The native and in-addon comparisons share item facts and one worn-swap
  evaluator. Placement uses base gear. Swap estimates apply verified permanent
  modifiers from exact links. Unknown modifiers, unscored effects, and
  weapon-speed or hit changes outside the reviewed model can make an estimate
  conditional. Acquisition uses default weights for best-owned comparisons.
- The scoring audit checks four Leveling bands and Pre-Raid for each of the
  28 specs. At least one exact swap in every context must change with an active
  talent. Each fixture records the reason, character, physical slots, exact
  variants, talent ranks, and independently calculated expectations in
  [the scoring model](../../data/canonical/forever/scoring_model.json).
  The reference matrix at levels 9, 19, 39, 59, and 60 checks eligibility,
  role contribution, score bands, and stable Guide membership.
- Test loadout switches, level previews, unavailable API values, and changed
  mechanics evidence. Compare Python and Lua results. Check startup, first-open,
  and tooltip performance.
- `python tools/scrape_wowhead.py scoring-audit --flavor forever --strict`
  checks approved inputs and executes the independent swap fixtures in Python
  and Lua 5.1. Both calculations must match expected points within 0.01,
  legality, and order. Local Forever deployment and the full release check
  require all 56 contexts. Follow the [release playbook](release-process.md)
  for data coverage, reproducible generation, and recorded gameplay acceptance.

### Scope of the talent models

The fixed presets apply verified gear-dependent talent curves in the class's
stat channels. The points remain editorial units. Damage effects that apply
only to specified spells use the preset documented on the profile. Crit
multipliers change the selected school's weighted Crit contribution. The
direct-healing presets estimate the affected healing and mana budget. Healing
mix, actual overheal, and time inside the five-second rule need encounter
observations before they enter a score.

| Class | Verified effects used in the comparison | Inputs requiring separate observations |
|---|---|---|
| Druid | Heart of the Wild scales Intellect, Bear Stamina, and Cat Strength separately. Cat applies after level 19. Naturalist, Moonfury, Living Spirit, Natural Instinct, and Gift of Nature affect the relevant damage, recovery, or healing. | Swing cadence uses the 1.0-second cat and 2.5-second bear benchmark. Periodic effects, shifting frequency, and rage feedback need encounter evidence. |
| Hunter | Lightning Reflexes scales Agility. Survivalist scales gear-derived health through Stamina. Careful Aim contributes once in the selected Attack Power channel. Ranged Weapon Specialization adjusts the ranged contribution. | Family-specific pet stats, focus and damage share, and Survival's melee and ranged mix. |
| Mage | Arcane Mind scales Intellect, with a separate Arcane critical-bonus curve. Arcane Instability, Ice Shards, Frost Channeling, and Wand Specialization use the appropriate school or damage channel. | Fire Power depends on the caster's active Fire effects. Freeze, mana refunds, mixed schools, and proc effects depend on the target and casts. |
| Paladin | Divine Intellect and Divine Strength apply when invested. Holy uses the Healing Light direct-heal preset. Protection applies Toughness and shield Block Value. Retribution uses Champion of the Light and two-handed damage scaling. | Oath uptime, Illumination refunds, block mana returns, different Judgement attack tables, and seal uptime. |
| Priest | Mental Strength, Wand Specialization, Spiritual Guidance, Spiritual Healing, and Darkness apply to the relevant healing, recovery, and damage contributions. Spiritual Guidance models separate 25% healing and 8% damage at rank five. | Meditation time, Divine Aegis and absorption share, Spirit Tap uptime, and target-specific Shadow damage. |
| Rogue | Dual Wield Specialization uses the off-hand weapon damage component and verified 25% and 50% rank bonuses. Item stats remain fully valued for either hand. | Poison cadence, attack-specific hit, weapon-specific Hack and Slash, and the defense and bleed mechanics in Serrated Blades. |
| Shaman | Elemental applies Concussion and Convection to its Lightning and Earth Shock preset. Enhancement uses the current Intellect conversions. Restoration uses its direct healing and mana-cost curves. | Mixed melee and spell hit, Maelstrom Weapon stacks and casts, Windfury, and time spent casting or recovering mana. |
| Warlock | Demonic Embrace scales gear Stamina. Shadow Mastery and Agonizing Flames apply in their supported spell contributions. | Fel Vitality scales mana independently of Intellect's spell crit. Life Tap needs a health and mana budget. Pet and Fire or Shadow buffs need pet, cast, and uptime evidence. |
| Warrior | Weapon specialization scopes damage to the equipped two-hander or the off-hand damage component. Bastion and Defiance require a shield for the modeled contributions. | Separate off-hand hit, Flurry, Deep Wounds, rage, and weapon-type effects require encounter evidence. |

The Rogue and Warrior off-hand benchmark uses half the item weapon DPS as
the autoattack contribution. The fixture score adds the verified talent
multiplier to that component. Weapon abilities and energy or rage return
may differ from the autoattack estimate and stay conditional. The initial
leveling bands also include rank-zero swap fixtures.

The unified Hit stat can affect melee specials, dual-wield swings, ranged
attacks, spells, and Rogue poisons against different caps. Only the reviewed
Protection Warrior melee benchmark currently has a priced cap. Judgement of
Command activates melee on-hit effects. Other Judgements use ranged attacks.
Rank-five Maelstrom Weapon has a nominal chance of `10 × main-hand speed / 60`
on a qualifying attack. Blizzard's 3.6 and 2.0 benchmarks yield 60% and about
33%. The scorer uses changes to that chance to detect uncertainty and keeps
effective stack and cast uptime outside the numeric estimate.
[Blizzard Hunter and Druid](https://worldofwarcraft.blizzard.com/en-us/news/24301515/) ·
[Blizzard Mage and Shaman](https://worldofwarcraft.blizzard.com/en-us/news/24302097) ·
[Blizzard Priest and Warrior](https://worldofwarcraft.blizzard.com/en-us/news/24301514/) ·
[Blizzard Rogue and Warlock](https://worldofwarcraft.blizzard.com/en-us/news/24310968) ·
[November 16 Forever hotfixes](https://worldofwarcraft.blizzard.com/en-us/news/24315281/wow-forever-hotfixes-november-16-2026)

## Ranking checks for a data refresh

1. Save a reference ranking report from the last generated Forever payload.
   Use the same reviewed content phase for both reports. Each report uses the
   addon query and includes all 28 specs at each band end and Pre-Raid, plus
   the level-48 Human Retribution case. It records the score, placement,
   guide section, selected source, and input digests.

   ```powershell
   New-Item -ItemType Directory -Path build -Force | Out-Null
   python tools/scrape_wowhead.py scoring-audit --flavor forever --rankings --content-phase PR > build/forever-ranks-before.json
   ```

2. Replay the cached availability refresh or collect new evidence from the
   registered sources. Inspect `ranking_review` in
   `build/forever-refresh/report.json` for changed item IDs, their known
   scoring contexts, and newer client builds. On a build or hotfix change,
   collect the pinned mechanics again and review any changed trait IDs,
   coefficients, attack rules, and equipment compatibility evidence.
3. Review the updated item and route decisions, then derive the new scoring
   bindings before importing. Pass the full snapshot directory to
   `scoring-audit --input-dir` to compute the draft bindings without writing
   canonical files. A changed cross-build equipment proof reports the
   proposed scope digest. Verify the equipment inputs against both builds
   before updating that proof. Recalculate changed talent fixtures from the
   source curves and item facts, explain rank reversals, and record the
   reviewer and reasoning. A weight revision can name the affected Leveling
   bands so an update preserves earlier, unaffected approvals. Change the
   model version when the arithmetic or assumptions change across all profiles.
   Follow the
   [Forever availability intake](forever-leveling.md#public-collection)
   to register accepted evidence and regenerate the payload.

   ```powershell
   python tools/scrape_wowhead.py scoring-audit --flavor forever --input-dir data/raw/wowhead/forever
   ```
4. Capture the same ranking report again. Check changes to eligibility,
   shortlist membership, sources, and order against the evidence.

   ```powershell
   python tools/generate_lua.py --flavor forever --check
   python tools/scrape_wowhead.py scoring-audit --flavor forever --rankings --content-phase PR > build/forever-ranks-after.json
   git diff --no-index -- build/forever-ranks-before.json build/forever-ranks-after.json
   python tools/scrape_wowhead.py scoring-audit --flavor forever --strict
   ```

   The last command runs both engines against the approved fixtures before
   the local prerelease can be installed. Keep the source revisions, report
   diff, and validation evidence with the refresh review.
