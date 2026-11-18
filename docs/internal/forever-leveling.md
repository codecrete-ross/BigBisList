# Forever leveling implementation and intake

Status: in progress. This is internal development evidence, not a declaration
that the leveling dataset is complete or ready to deploy.

The current scope is levels 1–59 for all 28 profiles and each supported
race/faction persona, plus the separately audited level-60 pre-raid dataset.
Standard deployment requires strict leveling and pre-raid coverage.
The explicitly authorized local prerelease may carry unresolved leveling
availability and must still pass validated generation and strict pre-raid
coverage. Live gameplay acceptance remains with the user.

## Gear progression and gap triage

Starter zones mostly offer basic weapons and armor. Class quests, dungeons,
and professions broaden the choices as characters level. Later armor
training adds options such as plate for Warriors at level 40. Shoulders,
jewelry, relics, and off-hands can open up at different points for different
characters. Some slots normally go unfilled at early levels, including
shoulders in the original game's gear progression.
[Blizzard's original game manual, Equipment section](https://bnetcmsus-a.akamaihd.net/cms/template_resource/263A8NGR8HLZ1556919642368.pdf)

In the audit checked on November 12, 2026, a level-14 Human
Arms Warrior had approved recommendations for 13 slots. The first reviewed
shoulder options start at level 15. [Leveling audit](../../data/canonical/forever/leveling_audit.json)

- **Equipment unlock** is when the character can use the equipment type or
  configuration. Combat Rogues can start using an off-hand weapon at level
  10. Druids can train two-handed polearms at level 20.
  [Forever equipment rules](../../data/canonical/forever/leveling_rules.json),
  [Live trainer report](https://github.com/timbers-addons/timbers-field-guide/blob/af77b439058ece15525b9447519e3fb2e37d0d43/CHANGELOG.md#v20261105h-2026-11-05)
- **Equip requirement** is what the individual item requires, such as a
  minimum character level on its tooltip.
- **Acquisition minimum** is the earliest level at which the character can
  complete a verified route, including prerequisites and eligibility. The
  approved Talbar Mantle routes start at level 15 for both factions because
  the quest starter requires level 15. [Glowing Shard](https://www.wowhead.com/forever/item=10441/glowing-shard)

Start with the first reviewed recommendation for each slot and character
context. Shoulders at levels 1–14 on both factions form an empty-slot review.
Keep the recommendation slot empty while checking specific exceptions.
Record each shared requirement once and apply it to every affected character
and level. Report the range as an availability review and name the evidence
that could change the outcome.
A verified later equip requirement rules out the item across the range.
An acquisition gate rules out only the route it describes. For example,
Corpsefeeder's Carapace awards Clacking Carapace Spaulders from level 35.
The reported beta vendor listing still needs its own evidence.
[Corpsefeeder's Carapace](https://guide.wow4ever.se/en/quests/93574)

For a group encounter, distinguish who can start it from who can receive
loot. The Greater Wind Stone catalog lists three exact shoulder drops.
The ring required to summon the boss has a level-60 equip requirement.
That verifies the summoner's gate. The recipient's level and the shoulder
requirements still need evidence.
[Forever Silithus catalog](https://api.github.com/repos/ATTWoWAddon/AllTheThings/git/blobs/4e74a778ceddb6a031f3fcd8ac5f49476f529d77),
[Current item requirements](https://wago.tools/db2/ItemSparse/csv?build=1.60.1.70938)

- Use `not_applicable` when a verified equipment rule disallows the slot
  or configuration at that level.
- Use `no_useful_item` for an applicable slot once the inventory is complete
  and the evidence supports excluding every candidate for that scope.
- Use `unreviewed` while evidence or approval is pending, even when an early
  slot would ordinarily be empty.

Read `availability_review_combinations` as the number of cells awaiting an
availability decision. Summarize progress by shared slot range and unresolved
candidate IDs. The cell count measures how many character and level combinations
each decision affects. `pending_ranking_combinations` counts cells with eligible
gear whose order still needs review. The availability ranges show each faction,
the first reviewed recommendation, inventory completeness, and the count of
unresolved candidate IDs at each level. `pending_empty_slot_review` means the
inventory and candidate exclusions support an empty slot and the scope still
needs sign-off. `unreviewed_availability` means an inventory or candidate fact
remains open.

The November 12, 2026 retry recovered three of 670 Forever tooltips.
Runed Ring requires level 45, Innervating Band requires 54, and Band of the
Damned requires 56. Those requirements exclude the three rings from the
level 1–3 gap. The other 667 lookups yielded no tooltip.
Zephras lists those same 667 IDs as unrevealed for build 1.60.1.70888.
Recheck individual IDs when a registry entry changes or a current source
publishes equip or acquisition evidence for the item.
[Retry ledger](../../data/canonical/forever/retry_ledger.json),
[Zephras unrevealed items](https://zephras.com/forever/enUS/item/not-revealed/)

## Availability review examples

Nine exact resistance-test shoulder IDs and Mark of Deflection match the
shared fields in the current client and their historical records. The
historical pages explicitly mark those IDs unavailable to players. The
November 13 review found no alternate grant in the current quest, vendor,
loot, or creation records checked and excluded them for the affected early
ranges. Separately, the Ring of the Fallen God route requires the level-60
Eye of C'Thun from Ahn'Qiraj Temple. Keep those scoped decisions with their
sources and reopen them when an exact grant or access condition changes.
[Test shoulder record](https://www.wowhead.com/classic/item=16154/test-arcane-res-shoulders-cloth),
[Eye of C'Thun](https://www.wowhead.com/forever/item=21221/eye-of-cthun),
[Candidate reviews](../../data/canonical/forever/leveling_reviews.json)

Follow quest-provided equipment to the first step that grants it. For example,
both factions can keep the Brilliant Gold Ring after the Sparklematic cleans
it. The Grime-Encrusted Ring that starts that chain requires level 28.
[Gnomeregan quest guide](https://www.wowhead.com/forever/guide/gnomeregan-dungeon-overview-location-rewards)

The build 70938 review ruled out four Zandalar class mantles for levels 1–14.
Each quest requires a bind-on-pickup token from Zul’Gurub, whose four client
difficulties carry raid-availability gates. This resolves those candidates for
the early range. The remaining shoulder candidates still need a disposition
before the range can receive an empty-slot approval.
[Zul’Gurub entry conditions](https://wago.tools/db2/MapDifficultyXCondition/csv?build=1.60.1.70938#/maps/309),
[Blizzard’s raid schedule](https://worldofwarcraft.blizzard.com/en-us/news/24303009)

The November 13 follow-up ruled out 24 exact legacy drops from Zul’Gurub,
Ahn’Qiraj Temple, and Naxxramas for the affected early shoulder, ring, and
off-hand ranges. The pinned loot references identify the items. The current
client gates and Blizzard’s first raid schedule establish when the routes
are closed. Reopen each decision if the raid opens or an alternate source
for the exact item appears.
[Current raid access conditions](https://wago.tools/db2/MapDifficultyXCondition/csv?build=1.60.1.70938),
[Reviewed items](../../data/canonical/forever/source_review_backlog.json)

The next pass traced 265 inherited item IDs to seasonal boss, quest, and
token routes. It compared those routes with current Forever entry rules
and checked for alternate sources, including Pix Xizzix's inventory. The
45 exact rewards reviewed from Blackfathom Deeps, Gnomeregan, and Sunken
Temple bind on pickup in the seasonal tooltip archive. Check trade access
alongside any dungeon entry gate. The Mind-Expanding Mushroom lead remains
open because the current Blackfathom Deeps entry boundary falls within the
Idol review. An empty-slot approval still requires a complete inventory and
a supported decision for every candidate in the range.
[Blackfathom Deeps entry conditions](https://wago.tools/db2/MapDifficultyXCondition/csv?build=1.60.1.70938#/maps/48),
[Seasonal tooltip archive](https://github.com/Napalmsteak/WoW-Classic-Item-Caches/tree/eff4560809de2e852e9164183e3edf5a795edd20),
[Review backlog](../../data/canonical/forever/source_review_backlog.json)

The exact source of Putress’ Diary is a Scarlet Enclave drop. Its six upgrades
each require the previous diary and a raid page. The extra creation spell also
requires the diary as a tool. All seven items can be ruled out for the early
range. For the three dungeon relics, current entry evidence leaves only level
15 for Mind-Expanding Mushroom, levels 15–19 for Discarded Tenets of the Silver
Hand, and level 19 for Libram of Benediction in the open review.
[Diary spell effects](https://wago.tools/db2/SpellEffect/csv?build=1.60.1.70938),
[Review backlog](../../data/canonical/forever/source_review_backlog.json)

Ten crafted shoulder IDs share two required reagents in build 70938. The
archived Inert Mantle of Nightmares and Nightmare Seed routes lead through
the Temple of Atal’Hakkar, and the archived versions of the exact crafts
bind on pickup. The lower of the two current entry bounds is level 40, which
is enough to exclude those candidates from levels 1–14 under the reviewed
routes. Recheck if the recipe, binding, or source changes. The shoulder slot
stays empty while the remaining exceptions are reviewed.
[Forever recipe reagents](https://wago.tools/db2/SpellReagents/csv?build=1.60.1.70938),
[Review backlog](../../data/canonical/forever/source_review_backlog.json)

For crafted gear that can be traded, check whether anyone can learn the
recipe. Fourteen early-slot candidates have exact Forever creation spells
that link to bind-on-pickup recipes from the Gilded Scarab in the seasonal
Temple of Ahn’Qiraj. Both current raid modes are closed. The reviewed
trainer, vendor, quest and loot records show no other route for those recipes
or finished items. Recheck when the raid opens or another source appears.
[Seasonal recipe sources](https://api.github.com/repos/ATTWoWAddon/AllTheThings/git/blobs/fc9bcb864cddbf17215d660df1f6fd41373b2feb),
[Current raid gates](https://wago.tools/db2/MapDifficultyXCondition/csv?build=1.60.1.70938#/maps/531)

The November 13 review reconciled two additional public catalogs. All 3,982
applicable item IDs in the LibItemDB release scan and all 4,997 in The Forever
Era search index were already in the inventory. The two sources cover an
earlier build, and The Forever Era marks its historical fallback records.
[LibItemDB release scan](https://www.curseforge.com/wow/addons/libitemdb/files/9580874),
[The Forever Era catalog](https://theforeverera.com/en/items/)

The same day's Wowhead sitemap listed 25,559 Forever item IDs. Four were
absent from the current client tables. Their exact tooltips showed quest
items, a ledger, and food with no equipment slot. Use the sitemap to find new
IDs and use counted slot and quality listings to verify complete coverage.
The counted listings still need verification.
[Wowhead item sitemap](https://www.wowhead.com/forever/sitemap/item?page=1),
[Review backlog](../../data/canonical/forever/source_review_backlog.json)

The November 13 Icy Veins cross-check reconciled all 2,530 entries across
the shoulder, ring, held-off-hand, and relic partitions reviewed. Every ID
was already in the inventory. The default shoulder sort repeated rows across
pages. Sorting by unique item ID recovered each partition's advertised count.
Unrevealed entries still need current equipment or acquisition evidence.
The required counted Wowhead listings also remain open.
[Icy Veins armor catalog](https://db.icy-veins.com/wow-forever/items/armor/),
[Review backlog](../../data/canonical/forever/source_review_backlog.json)

Five exact legacy items were excluded from their early shoulder, Horde ring,
or Libram ranges. For Twain's Shoulder, two archival sources explicitly identify
the exact item as unused or unavailable. Its current record still matches the
legacy identity and shows 28 armor. The scoped exclusion uses the archived
player-access finding and the reviewed current item and grant records.
The archives disagree on the player status of Libram of Divinity item 23202,
so its current equip requirement and availability remain open.
[Current client items](https://wago.tools/db2/Item/csv?build=1.60.1.70938#/legacy-equipment/4728),
[Scoped reviews](../../data/canonical/forever/leveling_reviews.json)

The follow-up excluded two Horde ring candidates for levels 1–3. The
original Tremors of the Earth offered Burning Obsidian Band. The live
level-40 quest awards four different choices, and the archived post-alpha
database marks the exact ring unavailable. The archived quest for Ring of
the Dawn is obsolete, and the Forever entry still marks it unimplemented.
Both rings bind on pickup. Reopen either review if an exact player grant
appears. Inscribed Gold Ring and Band of the Wraith still need exact
availability evidence.
[Live Tremors of the Earth record](https://raw.githubusercontent.com/JIVESCORP/eg-link-output-wowf/164bd1e2d89579ada4ee5e2de7e5fd4db684a9f1/data/wowf/1.60.1.70888/quests.enUS.json#/quests/717),
[Ring of the Dawn quest](https://www.wowhead.com/forever/quest=5532),
[Scoped reviews](../../data/canonical/forever/leveling_reviews.json).

Ragnaros Core was removed from Ragnaros's loot table in patch 1.4.0.
The exact item was checked against the current Molten Core gates, the
October beta event's separate copies, and published live acquisition
records. The scoped decision excludes it for Horde rings at levels 1–3
on build 70938. Recheck on an exact live grant or change to the phase.
[Ragnaros Core history](https://warcraft.wiki.gg/wiki/Ragnaros_Core),
[Forever raid schedule](https://worldofwarcraft.blizzard.com/en-us/news/24303009),
[Current Molten Core conditions](https://wago.tools/db2/MapDifficultyXCondition/csv?build=1.60.1.70938#/maps/409)

Wit's Edge illustrates a class-specific crafting route shared by both
factions. A Mage obtains Witchblade from Darkmaster Gandling, deciphers
Comprehension 175 scrolls for a chance at Scroll of Wit, and uses it on
the dagger. The route uses level 57 as the reviewed Scholomance access
threshold and requires a key holder in the group. The sword's separate
equip requirement is also 57. The Mage rankings preserve Spell
Penetration and the melee Clearcasting proc as conditional effects.
[Exact conversion](https://www.wowhead.com/forever/spell=1302294),
[Public discovery](https://www.wowhead.com/forever/news/new-high-level-battle-mage-weapon-discovered-in-wow-forever-383860),
[Scholomance access](https://azeroth.wiki/forever/dungeons/scholomance)

Forever Item Finder's 19,023-ID index also adds no equipment IDs in the
affected slots. Its public feed returned four partial observations for the
252 open candidates checked on November 13. A shared find can identify an
item while leaving the exact drop, container, or buyer eligibility open.
For example, the Mark of Hakkar entry records a sighting of another player's
loot and supplies no container ID. A null entry only describes this feed's
published observations.
[Forever Item Finder](https://github.com/ArcSim/ForeverItemFinder),
[Mark of Hakkar observation](https://forever-item-finder.pages.dev/api/finds?id=10780)

The November 12 shoulder review checked all 704 entries in Eternadex's
listing. Every ID was already in the inventory. The first explicit
equip requirement above level 1 was 15. Check the acquisition of the
level-1 and no-minimum exceptions before approving the empty range.
[Shoulder listing](https://eternadex.com/en/datenbank/items/schultern/),
[Review backlog](../../data/canonical/forever/source_review_backlog.json)

Use exact client equipment flags to rule out explicitly deprecated gear when
the current item record corroborates the restriction. The client can also
rule a main-hand-only weapon out of the off-hand inventory when an auction
catalog lists it generically as a weapon. Check the inventory type to tell
off-hand weapons apart from held items. For off-hand weapons, check both the
dual-wield requirement and the weapon proficiency. For example, the Illidan
off-hand warglaive bypasses the dual-wield requirement and still requires a
proficiency outside the supported roster.
[Item flag and inventory type definitions](https://github.com/TrinityCore/TrinityCore/blob/c8ec3740265a237bc4da2ded4641203ae4fc102d/src/server/game/Entities/Item/ItemTemplate.h)

Treat an observed vendor inventory as evidence for the exact items it shows.
On November 11, EG Link recorded 16 items at Lady Palanseer. The reported beta
stock included Scavenger's Ring, Desolate Band and Clacking Carapace
Spaulders. Their current stock and purchase gates remain open. The separate
Corpsefeeder quest is a verified level-35 route for the spaulders.
[November 11 vendor observation](https://guide.wow4ever.se/en/npc/12792),
[beta ring listing](https://zugzugdb.com/item/271808/scavengers-ring).

Bind faction-specific exclusions to the exchange or other acquisition route.
For example, Malignant Root is an early Alliance option, and Rethiel's hostility
to Horde excludes that exchange from the Horde review. A new route reopens
the review. [Malignant Root exchange](https://www.method.gg/wow-forever/how-to-get-malignant-root-powerful-rare-ring-in-wow-forever)

Check captured suffixes before approving a cosmetic exclusion. For example,
Restored Ring has an effect-free base tooltip and a variant with Agility and Stamina.
[Restored Ring variant](https://www.wowhead.com/forever/item=281718?bonus=12721)

For a statless item with an effect, trace its linked spells against the current
build before excluding it. Bouquet of Red Roses only displays petals, so the
review excludes it from the early off-hand range. [Cascade of Roses](https://www.wowhead.com/forever/spell=27571)

Check documented effects that are absent from the tooltip too. Ancient
Heirloom reveals Dawn Waker quest targets through Arcane Marker. Its early ring
review preserves the quest evidence and excludes it from gearing recommendations
for levels 1–3. [Dawn Waker walkthrough](https://www.wowhead.com/forever/guide/dawn-waker-secret-walkthrough)

Check the realm and build on apparent exceptions. Blizzard's one-day beta loot
event ended on October 23, 2026. The build 70938 review matched twelve early-slot
candidates to the archived event hotfix and the exact item IDs that All The
Things lists as unavailable on live realms. Use those IDs to distinguish beta
variants from ordinary items with the same names. A beta auction can help
identify an item. A live acquisition approval needs evidence for the production game.
In the build 70888 comparison, Zephras uses "removed" for items the server
stopped answering for. Those items still need an availability decision.
[Blizzard's beta event](https://us.forums.blizzard.com/en/wow/t/the-wow-forever-beta-celebration-is-underway/2389633/1)
[All The Things beta-event item list](https://api.github.com/repos/ATTWoWAddon/AllTheThings/git/blobs/2d09300630a0bf36670165be46287eb36ad95ce9)
[Zephras build comparison](https://zephras.com/builds/1.60.1.70888/)

The November 13 review excluded five exact beta ring variants from the Horde
level 1–3 range. Wowhead explicitly marks those IDs unavailable to players, and
the beta hotfix archive places the same IDs in the October 22 event. Use item IDs
when comparing old event loot with similarly named gear.
[Quick Strike Ring variant](https://www.wowhead.com/forever/item=288927/quick-strike-ring),
[Ring of Spell Power variant](https://www.wowhead.com/forever/item=288931/ring-of-spell-power),
[Candidate reviews](../../data/canonical/forever/leveling_reviews.json)

Wowhead marks some inherited Season of Discovery items `Unconfirmed` in its
Forever catalog. Keep those IDs open until exact evidence resolves them. An
explicit unavailable label can support an exclusion when the item identity
matches the current record. Preserve any conflicting tooltip or route evidence.
[Wowhead data update](https://www.wowhead.com/latest-dev-updates)

Since November 10, Wowhead also shows inherited drops labelled `(Classic Era)`
on Forever pages until its collector sees the drop in Forever. Keep those rows
as leads and verify the exact item and source on live Forever before approving
an acquisition route. A current equipment tooltip can establish an equip
requirement while the drop source remains open.
[Wowhead drop provenance](https://www.wowhead.com/latest-dev-updates)

Follow the specific reward variant for dungeon-set shoulders. For example,
Anthion's Parting Words lists a bind-on-pickup Astral bundle that names the
Feralheart Spaulders variant 226778. Its exact quest gate and any separate
acquisition sources need their own review.
[Alliance reward record](https://forever.warcraftdb.com/api/data/node/quest/84179),
[Horde reward record](https://forever.warcraftdb.com/api/data/node/quest/84187)

The November 13 hotfix caches confirm that Darkmantle Spaulders, Deathmist
Mantle, and Sorcerer's Mantle bind on pickup and have class restrictions.
Icy Veins reports level 58 for the Horde quest that awards Sorcerer's
Mantle. The Alliance quest minimum and the reported outdoor exchanges still
need current evidence. An equip-level field of zero leaves those acquisition
requirements open. [Verified hotfix cache index](https://www.raidbots.com/api/dbcache/verified),
[Horde quest 84189](https://db.icy-veins.com/wow-forever/quests/84189)

For build 70938, the two Grobbulus shoulders have a supported early-range
exclusion. Their bind-on-pickup drop route is gated by Naxxramas's phase.
Treat public hotfix caches as partial observations. Use their valid current
rows for exact equip requirements and retain historical IDs in the inventory
for review when current facts are missing.
[Naxxramas entry conditions](https://wago.tools/db2/MapDifficultyXCondition/csv?build=1.60.1.70938)
[Public hotfix cache index](https://www.raidbots.com/api/dbcache/verified)

The November 13 live Razorfen Kraul records show why equip and acquisition
levels must be tracked separately. Dokebi Bracers require level 22 to equip.
The verified drop from Raging Agam'ar is available from level 25, the normal
dungeon's entry requirement. Dokebi Mantle has the same entry requirement
for its Quilguard Champion route and requires level 27 to equip.
[Razorfen Kraul entrance data](https://wago.tools/db2/MapDifficulty/csv?build=1.60.1.70938#/maps/47),
[Efficient Games loot observations](https://raw.githubusercontent.com/JIVESCORP/eg-link-output-wowf/e0f8585914c134d9cb5d76756bd065b1e3e92ece/data/wowf/1.60.1.70938/loot.json)

The client can list an item ID before its tooltip is public. Blizzard described
withholding item stats until the item drops on a server. A candidate without a
tooltip can still be ruled out by a verified equipment restriction or a gate
covering all of its acquisition routes. An item ID or an empty lookup leaves
its availability open.
[Developer interview](https://www.mmorpg.com/interviews/blizzcon-2026-interview-chatting-wow-forevers-campsites-horizontal-progression-and-more-with-blizzard-2000138932)

The November 13 Drowned City review records the normal route for both
factions. Its reviewed access threshold is level 35. Heart of the Primeval
also requires level 35 to equip, Viscera Spaulders and Knucklebone Ring require
36, and Maw of Min'loth and Serpentbane Crown require 37. Apply each
item's equip requirement and character proficiencies before ranking it.
[Blizzard's dungeon overview](https://worldofwarcraft.blizzard.com/en-us/news/24301455),
[Forever loot table](https://wowtbc.gg/warcraftforever/loot-tables/dungeons/the-drowned-city/)

Linken's Boots of Iron illustrate why equip and acquisition reviews also need
to account for hidden effects. The boots require level 33 to wear, and the
Primeval Elemental route uses the reviewed level-35 threshold. Public player
reports and the client spell establish a substantial land movement penalty
and the ability to walk along the bottom underwater. Keep the route and stats
as item facts and exclude the boots from general leveling rankings.
[Forever item record](https://www.wowhead.com/forever/item=271718/linkens-boots-of-iron),
[Drowned City loot guide](https://www.wowhead.com/forever/guide/the-drowned-city-dungeon-overview-location-rewards)

Dark Advisor's Pendant requires level 56 to equip. Its reviewed route starts
at level 57 for both factions, when a Scholomance group can use Dawn's Gambit
to activate the Viewing Room encounter and defeat Vectus. Keep the activation
with the group and apply the pendant's Shadow damage bonus only under the
profile's matching weight.
[Forever item record](https://www.wowhead.com/forever/item=18691/dark-advisors-pendant),
[Scholomance guide](https://www.wowhead.com/forever/guide/scholomance-dungeon-overview-location-rewards)

## Data boundaries

- `data/canonical/forever/leveling_rules.json` contains versioned level bands,
  class proficiencies, weapon/training policies, form breakpoints, and race/class
  personas. The supported conservative policies have source reviews, including
  separate one-handed and two-handed proficiency lists. The Shaman weapon
  policies allow shields and supported two-handers.
- `leveling_scoring_profiles.json` is separate from pre-raid scoring. Its 112
  records review all 28 profiles independently in four level bands. Coefficients
  are editorial comparisons, not claimed simulations or numbers quoted from guides.
- `leveling_reviews.json` owns leveling fact and ranking approvals. Item and
  route approvals reference collected evidence. Ranking approvals bind the
  obtainable candidate set, rules, profile version, variants, racial document,
  and supporting guide evidence for a faction/race/level/slot interval.
- `leveling_items.json`, `leveling_item_stats.json`, `leveling_gear.json`,
  `leveling_recommendations.json`, and `leveling_audit.json` are derived by
  the Forever import. They do not overwrite pre-raid fact/ranking documents.
- The generator combines approved runtime facts from both families and keeps
  their routes. Conflicting approved facts reject generation. Forever-only
  schema fields do not change Anniversary output.

Missing equip level and missing acquisition eligibility are unknown. An
observer's faction is not a route restriction. A quest's displayed level is not
its minimum acceptance level. An unrestricted shared route can serve a Human
outside Human starting zones. Unverified coordinates never create waypoints.

Selection filters eligibility before choosing three leaders and positive-score
alternatives within five percent. Zero-score ties retain three deterministic
choices. Suffix approvals identify the actual variant. No-item dispositions
require explicit exhaustive evidence for the exact persona, slot, and levels;
an empty source response or missing lookup cannot establish absence.
Slot minimums describe verified equipment unlocks. The level of the first
known item does not establish that an earlier slot is inapplicable.

## Public collection

Run the availability refresh against the current audit and saved evidence.

```powershell
python tools/scrape_wowhead.py refresh-availability --flavor forever
python tools/scrape_wowhead.py refresh-availability --flavor forever --online
```

The first command replays caches. The second checks public sources within
80 HTTP attempts and a five-minute collection window. Rerun the same command
to use its checkpoint and provider cooldowns. Unchanged failed item lookups
become eligible again after seven days. A relevant source or reviewed build
change can make a lookup eligible sooner.

Read `build/forever-refresh/report.json` for changed facts, unresolved items,
stale reviews, and any proposed manifest entries. `staged_snapshots` identifies
each normalized file and its repository destination. Review the evidence and
its affected approvals, register the accepted sources, and copy the accepted
snapshots to those destinations before the regular import and generation.
The collection command writes its checkpoint and evidence to the build folder.
Use the [ranking refresh checks](forever-scoring.md#ranking-checks-for-a-data-refresh)
to record before and after results and review the reported scoring contexts.

Counted Icy Veins and Eternadex listings can certify the public catalog
partition alongside the reviewed client export and AHledger catalog. Reconcile
every page with its advertised unfiltered count and check unique IDs across
the partition. Eternadex lists weapons by subtype, so join all its weapon
categories to exact client inventory types for one-hand and off-hand scopes.
Keep candidates with unknown requirements in the audit. Complete inventory
coverage still needs a supported exclusion for every candidate before an
empty slot can be approved. [Icy Veins](https://db.icy-veins.com/wow-forever/items/) and [Eternadex](https://eternadex.com/en/datenbank/items/)

On Windows the refresh uses system `curl.exe` with certificate verification
for Raidbots, Everloot, and Eternadex. Use the checkpoint when a provider is
unavailable. EG Link evidence is pinned to a commit and the reviewed client
build. Join only exact item and entity IDs. Observed quest acceptance metadata
can establish a recorded minimum while the event, turn-in, or alternate routes
still require evidence. [EG Link datasets](https://github.com/JIVESCORP/eg-link-output-wowf/blob/main/DATASETS.md)

The refresh also compares exact pending IDs with EG Link's item disclosure and
quest scan exports and the same-build Zephras unrevealed registry. A new
disclosure or a departure from the counted registry triggers an exact lookup.
Withheld items and unanswered quest scans remain open in the audit. Each item
status keeps its source receipt and build. [Zephras unrevealed registry](https://zephras.com/forever/enUS/item/not-revealed/)

Availability decisions keep their original snapshot receipts and verify the
equipment facts and acquisition dependencies they used. A complete catalog
can carry forward an existing review after an additive refresh when its
original rows and scope still match. A changed item fact, a new route for the
reviewed item, or a coverage change for a reviewed empty slot triggers review.

All 28 Forever leveling guides are registered and cached. Inline acquisition
links, including class quests and abilities, are discoverable in addition to
table links. Anniversary IDs and QuestieDB raw records supply discovery leads;
they do not supply published Forever recommendations.

AHledger's public armor and weapon catalogs supply identity metadata. Its
documented text export supplies observed quest/reward leads. Exact item IDs
resolve only when a reward name is unique in the catalog or an ID is explicit.
Each refresh archives distinct quest observations with the source digest.
Older rows retain their original evidence when they leave the export's rolling
window. Unknown levels and unresolved names remain unknown. The required
credit is preserved with each snapshot.

Everloot's current public edge feed contains observations, unlike the earlier
empty rate feed. Its public corpus is being paged separately. Partial or
duplicate page sequences cannot replace complete evidence. The provider's
public allowance is 30 shared requests per hour and 500 records per page;
respect its Retry-After response. Single reports remain leads. Corroborated
edges retain their reporter count, attribution, and share-alike terms.
Uploader/event identifiers are stripped from normalized evidence.

QuestieDB inputs are pinned to commit
`80866960788084ae1592abf66a08f0d306458a95`. The original literal-parsed
`questiedb_raw_lead` snapshots remain separate. Additional curated records
come from the repository's documented emulator API after Forever
Static/Derived/Dynamic composition, exported in both factions and all nine
class contexts. Corroborated quest and dungeon associations use that composed
result, with attribution; provider runtime code is not bundled. Coordinates
remain unverified. The API's documented Skyborne masks use bits 32 and 33,
not race-ID-minus-one; those integers remain exact.

The public acquisition run encountered a transient Windows reader lock while
replacing the retry ledger. Successful normalized snapshots were retained and
used to recover collected statuses; unrecorded missing URLs were retried
explicitly. Atomic writes now retry short Windows sharing conflicts while
preserving the previous complete artifact. Original attributed metadata for
all 197 unresolved item lookups is retained.

The review can consult public ForeverDB pages. Keyed API access remains
unavailable. The current scope uses public records and existing caches.

## Audits and deployment

Use the explicit flavor on every command:

```powershell
python tools/scrape_wowhead.py discover-sources --flavor forever
python tools/scrape_wowhead.py import --flavor forever
python tools/scrape_wowhead.py gaps --flavor forever --family leveling --json
python tools/scrape_wowhead.py coverage --flavor forever --family leveling --strict
python tools/scrape_wowhead.py coverage --flavor forever --family bis_lists --strict
```

Discovery previews by default; `--write` registers the displayed sources.
`import --family leveling` derives only the leveling documents. Gap reports
retain provisional items, acquisition leads, evidence conflicts, and invalid
review details even when production imports reject stale approvals.

`scripts/deploy.ps1 -Flavor forever` checks both strict data families and the
generated payload before changing installed files. Add `-Prerelease -NoClean`
for the local pilot with uncovered leveling combinations. Public release
requires artifact-bound live acceptance in `live_acceptance.json` and the
authoritative clean-commit `-FullData` workflow in
[the release playbook](release-process.md).

## Outstanding review work

The November 14 import reconciled 4,386 unique IDs across all nine early-slot
equipment partitions. All matched the reviewed client catalog and inventory
type. The audit still has 244 open candidate reviews across 17 shared
availability ranges. Of the 220 candidates still missing equipment facts,
216 appear only as numbered placeholders in the checked Icy Veins listings.
The remaining 24 candidates need acquisition decisions. Keep the affected
slots unreviewed until their candidate evidence is resolved.
[Candidate audit](../../data/canonical/forever/leveling_candidate_audit.json)

The newest November 14 verified cache for build 70938 provides an exact
equipment record for Feralheart Pauldrons. It confirms no explicit equip-level
gate and leaves the quest variants and vendor exchange requirements open.
The off-hand review needs the lowest level that can reach Honored with
Timbermaw Hold and buy Furbolg Medicine Pouch.
[Retry ledger](../../data/canonical/forever/retry_ledger.json),
[Furbolg Medicine Pouch](https://forevertwinking.com/items/furbolg-medicine-pouch).

The observed rewards for The Great Ursera Spirit and Strength and Mercy cover
the Bear Form quest chain. Both quest records omit Mark of Urs'endris. Ur'endra
loot reports leave the exact relic grant unresolved. Past Due lists Salve and
Salvation or Knucklebound Thimble, so A Lesson in Destruction still needs its
own route. The game calendar lists Midsummer for June 21–July 5, 2027. The
Mantle of the Fire Festival review needs live event access and eligibility for
the four bonfires and the quest hand-in.
[Bear Form chain](https://www.foreverdb.app/en/forever/quests/94638/strength-and-mercy),
[Ur'endra loot observations](https://ahledger.com/wow-forever/npcs/258443-urendra),
[Past Due](https://guide.wow4ever.se/en/quests/96800),
[Forever calendar](https://undying.app/events).

The November 16 recheck matched the two numbers used by Repair and Recharge
Pylon to monster-credit objectives for Powering the Pylons. Mark of Urs'endris
and Firestorm Totem still need an observed item source. The Windshaper Call of
Earth chain records a Stoneskin Totem teaching reward from level three. Decoy
Totem still needs a verified player unlock before judging whether Firestorm
Totem can help at earlier levels.
[Powering the Pylons quest](https://zephras.com/forever/enUS/quest/96018/) ·
[Build-pinned relic evidence](../../data/raw/forever/wago/go-tools-db2-spelleffect-csv-build-1-60-1-70938-relic-dependencies-263435-263436-170b39c68d1c235f.json)

The November 17 batch revalidated 23 quest exclusions against exact reward
IDs and minimum levels. Revenge Exacted still requires level 44 and offers
Pyrestone Orb. Nine records now use direct equipment requirements from levels
56–58. Beastmaster's Shoulders and Shoulders of The Five Thunders require the
relevant class's level-40 Mail training. The Deathmist Mantle reward from
quest 84193 requires level 58. Independent exchange routes still need stock
and prerequisite evidence. The regenerated audit has 242 open candidates,
including 213 missing tooltips and 29 availability reviews. It reports 3,448
unresolved combinations across the early slot ranges.
[Pinned quest export](https://raw.githubusercontent.com/JIVESCORP/eg-link-output-wowf/06b4cc7b814c1cb16ff56b746181c2c62944fbc9/data/wowf/1.60.1.70938/quests.enUS.json) ·
[Verified cache index](https://www.raidbots.com/api/dbcache/verified)

Use Windows curl with certificate validation for AHledger. Both counted
catalogs and the sampled quest export responded through that transport.
Collect Everloot item facts, quest observations, and vendor observations
independently so a changed revision leaves the previous complete capture
available. Their three complete partitions held 8,055 records across 18 pages.
The raw loot feed required 32 pages at the anonymous limit. Use observed
edges and exact item filters for targeted acquisition checks. When a counted
listing returns HTTP 403, observe its cooldown and use the corresponding
validated Eternadex partition where one exists.
[AHledger public data](https://ahledger.com/data) ·
[Everloot corpus and limits](https://everloot.app/docs/api/corpus-public) ·
[Everloot item relationships](https://everloot.app/docs/api/edges)

The Druid rule review added Impaling Harpoon, Armor Piercer and Grimlok's
Charge to the eligible two-handed pools at levels 20, 30 and 42. Those
breakpoints use the latest of the training, equip and verified route levels.
The feral tank and DPS pre-raid rankings include Grimlok's Charge.
Xorothian Firestick is reviewed as a level-57 ranged alternative for both
factions through the existing Lord Hel'nurath group summon in Dire Maul
West. Its fire proc stays separate from the flat score.
[Forever weapon training](https://www.wowhead.com/forever/guide/classes/weapon-trainer-skill-locations),
[Firestick tooltip](https://www.wowhead.com/forever/item=18755/xorothian-firestick).

The remaining coverage work starts with availability reviews before the first
reviewed recommendations for shoulders, Horde rings, held off-hands and class
relics. Leave those slots blank while checking candidates against the shared
gates. Approve a blank interval once the inventory and exclusions support it.
Review profession access, suffix variants, procs, sets and contextual effects
when they affect candidate eligibility or ranking.
No numeric item-dependent racial modifier or random suffix is approved yet;
the reviewed racial policy excludes unsupported values and old TBC weapon
preferences. Existing ordinary alternatives can cover a slot while higher
or contextual candidates remain pending.

Dungeon routes use explicitly described conservative access thresholds from
current guide ranges; they do not claim the earliest possible entry level.
Investigate earlier entry separately before extending those leveling intervals.
Unknown availability and missing lookups never establish a no-item disposition.

The Jaw Breaker and Band of Mending have reviewed group routes for both
factions and appear from their equip levels, 56 and 57. The Jaw Breaker
requires a group member with a brazier for Mor Grayhoof. The published
guides disagree on the summoning room, so the route gives the verified
dungeon and activation instructions. The Band of Mending uses the main-gate
Stratholme route to Grand Crusader Dathrohan, who becomes Balnazzar.
[Lower Blackrock Spire](https://www.wowhead.com/forever/guide/lower-blackrock-spire-dungeon-overview-location-rewards),
[Stratholme Live](https://www.wowhead.com/forever/guide/stratholme-live-side-dungeon-overview-location-rewards)

Fel Hardened Bracers are approved for both factions from equip level 57.
Bring a Crescent Key holder and a Warlock with the three summoning items
to Dire Maul West. The Warlock starts the ritual after the group defeats
Immol'thar. The two level-58 items attributed to Sothos and Jarien's
Heirlooms have current tooltips and still need a verified cache drop.
[Lord Hel'nurath](https://www.wowhead.com/forever/dungeon-journal/dire-maul-west/lord-helnurath),
[Stratholme Live](https://www.wowhead.com/forever/guide/stratholme-live-side-dungeon-overview-location-rewards).

## Current handoff evidence (2026-11-05 local date)

The evidence index contains 9,386 snapshots: 83 guides (including publisher
and launch-client rule references), 4,983 items, 2,081 NPCs, 1,406 quests,
813 spells, fifteen observation documents, two catalogs, two raw lead documents and one API
reference. Current class-quest body facts were also read through public web
pages; the browser human-verification challenge did not prevent those checks.

External snapshots contain 15,578 AHledger catalog records, 1,847 observed
quests, 16,960 Everloot public records, 45 Everloot edge records, and the two
pinned QuestieDB lead sets. The Everloot public pages span a provider refresh;
`pagination_consistent_as_of` is false. This is retained explicitly and does
not establish a coherent exhaustive inventory or three independent reports.

A later public refresh advertised 17,793 records. HTTP 429 stopped collection
after 27 valid pages (13,500 records); the public allowance is 30 requests per
hour per address. A staging loop repeated its last successful page after that
error. The pagination validator rejected the incomplete sequence, and nine
repeated pages were quarantined. Canonical evidence was not replaced. The valid
prefix contains 851 observations absent from the earlier corpus; its equipment,
quest, vendor and loot records did not resolve the pending early slots.
The partial status, resume offset, collection time and cooldown are recorded in
`source_review_backlog.json` and `build/forever-review/provider-probes`.
The provider's documented bulk export was also checked: its newest published
index is dated October 19, build 70450, with zero public-corpus or observed-drop
rows. Its older unconfirmed game-file rows cannot establish current routes.
After the cooldown, use the documented `kinds` filter for targeted acquisition
records rather than restarting an unfiltered 36-page download inside a
30-request hourly allowance.

The retry ledger contains 1,486 pending URL records, including ten requested
Everloot item cards that return 404, and 1,163 attributed catalog metadata
observations. All 197 original `metadata_only` records and their
upstream metadata-source digests were checked unchanged after recovery and
enrichment. Catalog metadata is not imported as equipment stats.

The leveling import contains 905 approved item facts and 94,413 compact interval
recommendations. All 28 profiles have independent ranking decisions, stored
in 13,940 groups of identical race decisions and validated per persona. Five
reviewed cosmetic rings retain their acquisition facts but are explicitly
excluded from combat recommendations. Four profession-tool decisions are held
with their prior reviews preserved because no combat weapon proficiency was
observed. The approved intervals cover 147,332 of
155,284 individual profile/faction/race/level/slot combinations; 7,952 remain
uncovered. There are 4,548 provisional
items and no stale approvals. Six eligible guide-claim intervals accompany the
computed recommendations in the existing Leveling Gear Guide. All
currently eligible approved candidates have completed ranking review. This
retains eligible zero-score choices throughout 1–59 under the agreed
deterministic policy; recovered positive headgear now displaces weaker
zero-score hats. No extra age cutoff is used.
The removed jewelry has no armor, damage, stats or functional effect. This
exclusion does not discard verified statless starter armor and weapons.

The covered routes include rendered vendor inventories, exact observed BoE
auction listings, checked starter quest chains, and corroborated named normal
dungeon drops. Call of Fire now supplies a qualitatively reviewed level-10
Totem of Charged Flames for Dwarf, Orc, Tauren, Troll and Windshaper Skyborne
Shamans. The separately checked four-step Skyborne branch ends at quest 97257;
the earlier Meddlesome Mages reward lead remains conflicted and unapproved.
Aquatic Form supplies Idol of Shifting Tides from level 16 for Night Elves and
Tauren. The conservative reviewed route completes the entire level-14 poison
training before the four Aquatic trials, covering the reported preparation
gate without asserting an unverified direct prerequisite link or shortcut.
Skyborne eligibility remains conflicted and held. No unverified location
creates a waypoint.

The continued review added 267 ordinary unbound trade items, eight additional
named dungeon facts, profession-gated goggles, and two dungeon trinkets.
Flying Tiger Goggles retain Engineering 100 and its level-10 Journeyman gate
even when bought. Minor Recombobulator has a level-10 Alliance route through an
observed schematic listing and Engineering 140 self-crafting; a Horde schematic
path remains unverified. Its ten expendable charges and recovery effect remain
contextual rather than flat regeneration. Worgenbane Talisman's direct two
mana per five seconds is separate from its Worgen-only stun.

The two library necklaces retain the complete ten-distinct-book requirement,
separate faction librarians, and a checked non-instance collection route.
The quest permits acceptance from level 1; this is substantial, dangerous
travel rather than a starter-area handout or a solo-safety claim. Depleted
Ritual Band is a Horde quest reward from level 4. Avala's Binding has a complete
three-quest Alliance route from level 5, including Humans visiting Dun Morogh.
Their real armor/resistance benefits remain eligible when their weighted score
is zero. Recipe and quest-starter evidence is preserved separately from gear.

Journeyman's Stave adds an equip-level-five off-hand alternative for both
factions, supported by exact positive-quantity listings and the current tooltip.
Its purchase route is available earlier than its equip requirement. This closes
118 combinations; earlier off-hand levels remain uncovered. A populated runtime
case checks both factions at levels four and five.

Gnomish Universal Remote remains held: the neutral recipe-vendor association
conflicts with a current report that the NPC offers nothing. Old raid-named
low-level rings also remain held. Their current tooltips differ from beta
catalog values, and their observed starter-zone drops coincide with the
[documented beta finale](https://www.wowhead.com/news/world-bosses-legendaries-and-a-scourge-invasion-the-wow-forever-beta-is-over-383554).
Neither those beta observations nor absent current listings establish launch
availability or exhaustive absence.

Mystic Mushroom, Polished Driftwood Icon and Tenets of the Silver Hand are
self-crafted level-20 relics with Enchanting 130 formulas costing 45 Merchant's
Favor. Libram of Invocation requires level 40, Enchanting 210, a 120-Favor
formula and Friendly reputation. The generic reputation tooltip's organization
is explicitly inferred from the vendor's faction, not silently presented as
an observed faction name. Currency crate hand-ins and reputation writs are
documented. Percentage Spirit/regeneration, Seal mana savings, and Undead-only
damage are reviewed qualitatively; no flat-stat conversion is invented.
Distinct faction recipe vendors survive merging. Conflicting nested faction,
level, profession and reputation requirements reject generation.

Three additional quest trinkets have complete reviewed routes: Thunderbrew's
Boot Flask (Alliance, minimum 40), Rune of the Guard Captain (Horde, minimum 46)
and Shard of the Splithooves (Alliance entry minimum 50, Horde entry minimum 45).
Every step's current public tooltip and the composed API were checked. The
shared final reward quest retains both distinct prerequisite branches through
payload merging. The same branch with conflicting restrictions still rejects
generation; an older route without its chain cannot bypass the reviewed gates.
On-use damage and environmental/target multipliers are retained contextually,
without an invented always-on score. The publisher confirms unified Forever
hit/critical chance; Anniversary's separate scoring remains unchanged.

Pre-raid remains separate: 217 approved items, 431 alternative slot lists and
all 862 faction/profile/slot cells covered. Its strict coverage audit passes.
Each faction pool is reviewed before selecting positive-score alternatives.
The three crafted relics have item- and role-specific qualitative approvals.
For physical profiles without an approved positive flat-stat trinket in their
faction, Cursed Murloc Eye is a modest obtainable offensive alternative: its
two Shadow damage is an attack/spell effect, not two spell power. Its exact
normal-dungeon drop and linked spell are checked. These lists cover reviewed
alternatives; they do not claim exhaustive BiS or superiority to unverified
endgame gear. Arbitrary statless filler is not approved. All 28 profile policies have offline source reviews;
live acceptance remains pending. Older approvals are retained in review history.
All four pilot profiles now pass both-faction pre-raid coverage.

All remaining leveling gaps are early. Levels 22–59 have approved continuous
coverage across the roster. The pending ranges are recorded with exact counts
in `source_review_backlog.json`, and the full persona rows remain available
through `gaps --flavor forever --family leveling --json`.

| Slot | Remaining cells | Pending levels |
| --- | ---: | --- |
| Head | 1,548 | 1–9 |
| Shoulder | 2,408 | 1–14 |
| Ring | 602 | Alliance 1–4; Horde 1–3 |
| Trinket | 2,580 | Alliance 1–9; Horde 1–21 |
| Off Hand | 236 | 1–4, applicable caster profiles |
| Idol | 272 | Night Elf/Tauren 1–15; other supported Druid personas 1–19 |
| Libram | 171 | 1–19 |
| Totem | 135 | 1–9 |

The captured current Glowing Shard starter tooltip requires level 15 and links
quest 6981. This resolves the older dungeon guide's level-10 claim in favor of
the starter gate. It does not close shoulder coverage at 10–14 or prove absence.
Polished Bronze Safety Goggles, Mark of Urs'endris and Firestorm Totem have
wearable observations but unverified routes. Catalog BuyPrice fields are not
vendor inventories. Neither those leads nor an empty lookup can establish an
exhaustive no-item explanation. Unknown data remains uncovered.

Cached-response review fixed inline effect values, healing/damage splits,
shield block, elemental weapon damage, conditional attack power and set
metadata. Against-target and location bonuses do not become general stats.
Separate ranged DPS prevents bows and thrown weapons from inflating melee
scores; Forever feral weapon DPS remains active in forms. One-handed sword
or mace proficiency does not permit two-handed versions. Auction markets
remain distinct routes, and shared dungeon routes are present before ranking.
Cached equipment lines also recover direct resistance fields in 172 snapshots,
including 19 approved items; conditional set resistance is not unconditional.
Affected fact and ranking reviews were rechecked, retaining their history.

Weapon-pair review also recognizes the actual `Unique` and `Unique-Equipped`
headers. A restricted preferred main hand is filtered out of the off-hand
candidate set before truncation. Off-hand approvals bind the main-hand pool
and preferred identity, with intervals split at main-hand-only availability
changes. Updating either side invalidates the affected decision. Forever's
runtime preserves reviewed rank ahead of compacted interval length; Anniversary's
existing ordering remains unchanged.

The populated quest-trinket corpus also exposed an empty-filter pre-raid query
that included opposing-faction entries. Forever pre-raid queries now default
to the current faction and race and carry the selected class through source
evaluation. Gear lists, planner, wishlist, comparison recommendations and
tooltips have a regression for the default faction context; explicit filter
previews remain available. Anniversary's defaults are unchanged.

Anniversary `Data.lua` remains byte-identical to the starting worktree
(SHA-256 `bfc3849948d974a6fc5c06bb7cb18590952b02f6530791b2cc5d865994d48cb8`).
All 633 tests pass with no skips using the declared release virtual environment
and installed Lua 5.1. This includes the atlas check, populated Forever
manifest, level-14 Human case, faction filtering before selection, grouped race
decisions, weapon handedness, contextual effects, suffix identity, quest
endpoints without coordinates, trade venues, faction recipe branches and nested
requirements, the shared Human starter ring, conservative Druid relic paths,
stale approvals and attribution.
Both flavors pass canonical validation and generated-payload checks. Derivation
is compared with canonical artifacts during validation, establishing deterministic
imports for the reviewed inputs.

Lua 5.1 compiles both payloads and the changed runtime. Loading the 54,464,116-byte
Forever payload alone in standalone Lua took 0.629 CPU seconds and retained
41.52 MiB of Lua heap after garbage collection; this is an offline parse measurement, not startup or first-open
gameplay acceptance. Final validation evidence is recorded in
`build/forever-review/*-current.*` and the final-batch import/generation logs.
Strict pre-raid coverage passes; strict leveling coverage exits 1 with 7,952
uncovered combinations, zero stale approvals and no implementation errors.
The actual Forever client was not updated.

No local captures were imported and no recorder was enabled in this batch.
Live gameplay, startup/first-open performance acceptance, and the clean-commit
`-FullData` release gate remain pending. The full release gate was not run
against this dirty worktree with known incomplete coverage. No tag or public
release was created.

The availability audit now reconciles current-build client table exports,
cached AHledger armor/weapon exports, and captured item tooltips. The initial
887 low-level catalog leads expand to 6,069 candidate IDs when unknown
requirements and client-only records are retained. Item level, names such as
`Deprecated`, and failed lookups do not eliminate a candidate. The generated
`leveling_candidate_audit.json` records source reviews, digests, each candidate's
evidence, pending facts and affected early-level contexts. Exact character,
slot and level gaps remain in the leveling audit. The original 197 metadata-only
retry records and their source digests are preserved.

This pass captured 1,074 additional Forever tooltips and retained 1,264 failed
lookups as unresolved. Verified equip requirements and equipment policies can
exclude a candidate for a specific early scope; incomplete routes cannot.
Six additional effect-free shoulder tooltips have explicit, evidence-bound
exclusion reviews. Real starter armor and weapons remain useful even when
their weighted score is zero. The unresolved early-slot candidate set shrank
from 3,025 to 2,357; this is evidence progress, not completed gear coverage.

Nine targeted Wowhead listings returned HTTP 403. Their completeness is still
open. Listing normalization checks the actual item Listview, advertised counts,
duplicates, quality and equipment partitions, and caps. Keep required-level
filters as discovery leads while their treatment of unknown requirements remains
unverified. Certify inventory from unfiltered slot listings or complete quality
partitions. The filtered Everloot corpus was collected completely in
four pages (1,559 records) with attribution and page digests retained.
No matching typed blocker entities or corroborated acquisition relationships
were found. This is coverage of those record kinds, not game-wide absence.

A pinned QuestieDB provenance review distinguishes inherited Classic chain
levels, copied Wowhead reward relationships, and actual trace changes. The
Meddlesome Mages trace updates objectives/endpoints without corroborating its
old reward links. Mark of Urs'endris and Firestorm Totem still have unpublished
acquisition paths. Copies of an upstream field are not independent corroboration.
Named blockers retain the missing fact and next evidence trigger in
`leveling_reviews.json` and `source_review_backlog.json`.

Empty-slot review requires complete inventory reconciliation and a supported
exclusion for every candidate in the exact character/level scope. Its
fingerprint binds the build, inventory, acquisition evidence, eligibility rules,
profile and candidate set. New candidates or acquisition evidence invalidate
absence approvals before gear publication. Stale approvals reject production
imports while diagnostic reports remain readable.

The Forever payload has a `leveling_availability` section and compact equipment
applicability rules. `GetLevelingSlotStatus` returns `recommended`,
`no_useful_item`, `not_applicable` or `unreviewed`; approved empty-slot reasons
render through the existing Leveling view alongside gear. The new section is
currently empty because absence evidence is incomplete. Anniversary's generated
payload and existing gear-query contracts are retained. Deployment still
requires both strict coverage gates; the live client has not been updated.

Verification after this availability pass: all 654 tests pass with no skips,
including populated manifests, the atlas, source pagination/failures, absence
invalidation, starter gates and runtime explanations. Both flavors pass
canonical validation and generated-payload checks. Strict pre-raid coverage
passes; strict leveling coverage exits 1 with the same 7,952 uncovered cells,
2,357 pending candidate reviews and zero stale approvals. The generated
Forever payload is 54,482,483 bytes. Anniversary retains its starting SHA-256.
The clean-commit `-FullData` release gate remains unrun because coverage is
incomplete and this worktree is dirty; recorded live acceptance is also pending.

The November 6 follow-up reduces the pending candidate set from 2,357 to
2,050: 1,521 still need an actual Forever tooltip and 529 need complete
acquisition evidence or a supported exclusion. The reconciled inventory remains
6,069 identities. Another 209 complete, effect-free equipment tooltips now have
explicit exclusion reviews. These do not discard starter armor, weapons,
unparsed numeric bonuses or situational effects. A raw `+2,500 Health` test ring
was retained for review despite its unparsed stat. Conflicting evidence and
unknown weapon subtypes remain unresolved where the reviewed equipment policy
cannot establish an exclusion.

Reviewed Engineering rank caps now support recipient-level exclusions:
Apprentice 75 at level 1, Journeyman 150 at 10, Expert 225 at 20 and Artisan 300
at 35. The current Gnome engineering racial improves reliability; it does not
grant the inherited Classic skill bonus. These rules bind the current racial
and profession evidence, every supported race explicitly, and the build. They
apply to equip/use requirements, not a profession needed only by a crafter.

Twelve additional AHledger faction/region market tables contain current
positive-quantity listings for the finished bind-on-equip Gnomish Universal
Remote, including Horde PvP US. Buying the finished item avoids the unresolved
schematic/vendor-stock conflict; it still requires Engineering 125 and level 10.
Each of the 28 profiles has a separate trinket ranking review after this change.
The against-Mechanical attack power and conditional control effect do not become
general numeric stats. The [ranking review history](../../data/canonical/forever/leveling_ranking_history.json)
indexes the preserved decisions by review batch, with a digest and count for
each batch file.

This closes 1,032 Horde trinket cells at levels 10–21. Leveling now has
148,364 of 155,284 applicable cells covered, 906 approved item records and 95,101
compact recommendation intervals. There are 6,920 remaining cells: Head 1,548,
Shoulder 2,408, Ring 602, Trinket 1,548, Off Hand 236, Idol 272, Libram 171 and
Totem 135. Trinket gaps for both factions are now levels 1–9; the other pending
ranges above are unchanged. No empty-slot explanations are approved, and no
stale item or ranking approvals remain.

Everloot's refreshed filtered observation feed contains 3,329 records across
seven consistent pages. It supplies no new facts for the missing-tooltip
candidates or named early-slot blockers. Its separate current-build client
layer contains 3,335 crafting relationships and adds no new inventory IDs.
Those edges remain metadata leads; route approvals reject client-only evidence.
The previous observation snapshot is archived and its digest retained. Provider
pagination, faction market identity, attribution and review history remain
explicit. Missing listings, HTTP failures and unpublished routes are not
availability exclusions. The strict leveling gate remains failing and the
client has not been updated.

Final follow-up verification: all 658 tests pass with no skips, including the
atlas and regenerated populated Forever manifest. Both flavors pass canonical
validation and generated-payload checks. Deterministic derivation agrees with
the imported canonical documents. The strict pre-raid audit passes; the strict
leveling audit exits 1 with 6,920 uncovered cells, no implementation errors
and zero stale approvals. The Forever payload is 54,851,367 bytes. All 197
original metadata-only retry records and their source digests are unchanged,
and Anniversary retains its starting payload SHA-256. Python compilation and
the whitespace check pass. No client deployment, live gameplay acceptance,
tagging or publishing occurred. The authoritative clean-commit `-FullData`
release gate remains pending because coverage is incomplete and the worktree
is dirty. Machine-readable evidence is in
`build/forever-review/continued/verification-final.json`.

### November 10 public refresh

The inventory targets client build 1.60.1.70888. Its item tables add 22
identities, including 10 equipment IDs and two candidates in the audited slot
families. Both were added to the inventory of 6,071 candidates. All 50 pages of
WCLBox's public armor listing and the complete Playfulls gear export supplied
no additional candidate identities. The Wowhead shoulder listing returned an
empty HTTP 202 response. The full inventory remains unverified.
[Client item table](https://wago.tools/db2/ItemSparse/csv?build=1.60.1.70888),
[WCLBox armor listing](https://wowforever.wclbox.com/en/wupin/fenlei/hujia),
[Playfulls gear catalog](https://playfulls.com/database).

Exact Forever tooltip lookups recovered 289 of the previously missing item
tooltips and seven for new equipment IDs. The retry ledger preserves the
other results and the original 197 metadata-only records. The refreshed
Everloot observation and relationship feeds returned no matching early routes.
The latest pinned QuestieDB files supplied no additional distinct acquisition
relationships. The broad Everloot feed changed during pagination, so the
review retained the previous broad snapshot and used consistent filtered feeds.
[Everloot public corpus](https://everloot.app/docs/api/corpus-public).

The new Berdun's Trusty Rifle is an approved Alliance reward from Gettin'
Buzzed at level 45. The Horde quest lists the same item ID and still needs a
verified giver and prerequisites. Other new equipment identities retain their
specific tooltip or acquisition review requirements.
[Alliance quest](https://www.wowhead.com/forever/quest=89013/gettin-buzzed),
[Horde quest](https://www.wowhead.com/forever/quest=91608/gettin-buzzed).

Lucky Fishing Hat now fills the head slot from levels 5 through 9 across the
roster. The reviewed route uses Apprentice Fishing 75, a Strong Fishing Pole
and Nightcrawlers to reach 130 effective Fishing. Both factions can turn in
Keefer's Angelfish to Fishbot 5000 during the fishing event. The catch is rare.
The item retains Fishing 1 as a wear requirement and its Fishing bonus stays
outside combat scoring. The head slots at levels 1 through 4 remain open.
[Reward quest](https://www.wowhead.com/forever/quest=8221/rare-fish-keefers-angelfish),
[Forever fishing guide](https://www.wowhead.com/forever/guide/professions/fishing/overview-leveling).

EZ-Thro Bronze Mortar fills the remaining trinket gaps at levels 1 through 9
for both factions. The same-faction markets have observed listings for the
tradeable schematic and every reagent. Commissioning an engineer with 190
skill makes the bind-on-equip trinket available to a level-one recipient. The
Horde market also listed the finished item. The limited charges, damage and
breakable stun remain contextual utility. Fifty-six additional exact-item
market lookups produced no positive observations for the tested early rings
and shoulders.
[Alliance schematic](https://api.ahledger.com/v1/prices/forever.pvp.alliance.us/264212),
[Horde finished item](https://api.ahledger.com/v1/prices/forever.normal.horde.us/260802).

This pass closed 520 of the original 2,050 pending candidate reviews. One
newly inventoried candidate remains pending, for 1,531 remaining reviews.
Of these, 1,043 need current tooltips and 488 need availability evidence.
There are 929 approved leveling item records and 97,930 compact recommendation
intervals. Verified recommendations cover 150,772 of 155,284 applicable
combinations. All 4,512 remaining gaps are in Shoulder (2,408), Head (688),
Ring (602), Idol (272), Off Hand (236), Libram (171), or Totem (135). No empty
slot explanations have been approved.

Strict pre-raid coverage passes across all 28 profiles. Strict leveling
coverage exits 1 with 4,512 uncovered combinations and zero stale approvals.
Both flavors pass canonical validation and generated-data checks. All 661
offline tests pass with no skips, including the populated manifest, the atlas,
and the level-1, level-5 and level-14 character cases. The Forever payload is
56,480,551 bytes. Anniversary retains its starting payload SHA-256. The live
client deployment remains gated on both coverage audits. Live acceptance and
the clean-commit `-FullData` release gate remain pending. Machine-readable
verification is in `build/forever-review/nov10/verification-final.json` and
the candidate transitions are in `data/canonical/forever/source_review_backlog.json`.
