# Forever pilot

This document records the level-60 Pre-Raid review and Forever client checks.
On build `1.60.1.70959`, the reviewed Pre-Raid dataset covers all 28 profiles.
The 0.15.x release gate permits only the remaining reviewed leveling gaps.
Strict scoring and Pre-Raid coverage apply to every release. See the
[leveling implementation and intake record](forever-leveling.md) and the
[release process](release-process.md).

The original pilot covered Warrior Protection and Arms, Shaman Restoration,
and Hunter Marksmanship. Source review now covers nine classes. The user-run
live acceptance record remains pending.

## 0.15.0 release plan

| Milestone | Evidence and remaining work |
| --- | --- |
| Home and navigation | Home has been retired in both modes. Offline tests cover save migration, native and fallback chrome, Settings over comparison Details, and returning to the selected item or workspace. |
| Endgame response | Compare full Protection and Retribution results with the original synchronous calculations. Measure the complete first viewport within three simulated 60 Hz frames and peak addon work within 4 ms. Record client timings separately. |
| Gearing evidence | Release coverage compares the 3,448 reviewed early-level cells and 242 unresolved candidates with the fixed review commit. Strict scoring and Pre-Raid checks remain required. |
| Client acceptance | Install the packaged candidate and record its digest, target build, cold and warm performance, title bar, return paths and gameplay checks in the release PR. Acceptance belongs to the player. |
| Publication | Merge the checked integration PR, dispatch one read-only hosted refresh from untagged main, review its evidence in release preparation and repeat client acceptance if the digest changes. Run the clean merged Forever full-data gate before the regular GitHub and CurseForge release. Verify the actual public Forever file. |
| Weekly updates | A new BigBisList workspace chat is scheduled Wednesdays at 9:25 a.m. Pacific with Sol 6.2 and Max reasoning. Main requires the release check and supports auto-merge. Activate the published baseline after acceptance and inspect the first scheduled chat and its hosted report. |

## Collect and review

Register Forever URLs in `data/canonical/forever/scrape_manifest.json`.
Refresh the registered gear guides, then derive item seeds from the snapshots.
`discover-items` prints candidates without `--write`. The collector preserves
successful snapshots when other URLs fail and reports the failed URLs separately.

```powershell
python tools/scrape_wowhead.py fetch --flavor forever --family bis_lists --refresh
python tools/scrape_wowhead.py discover-items --flavor forever --write
python tools/scrape_wowhead.py fetch --flavor forever --family item_corpus --missing-only
```

Add `--url <registered-url>` to run a focused fetch. The collector uses Wowhead's
Forever tooltip endpoint when an item page is unavailable. A tooltip establishes
what the endpoint returned about the item. Verify acquisition separately.
Guide snapshots contribute observed item IDs to the audit. Pre-launch guide rows
stay pending until a reviewer establishes the live context.

An item approval in Forever `overrides.json` has type `verify_item`, the item ID,
snapshot URL and `snapshot_digest`, and its verified acquisition routes.
`tools.forever.snapshot_digest` derives the digest from the normalized snapshot.
Include the reviewer, review date, client build, evidence URL, and reason. Route
destinations and quest steps also carry their own evidence. Record verified
routes independently when factions, entrances, or destinations differ.
When an item page is missing, register the item URL and record a normalized
live tooltip observation with its client build and `observed_tooltip` confidence.

Run the import to score the reviewed candidates. Read
`data/canonical/forever/recommendation_audit.json` for the score order,
guide observations, and candidate digest. An `approve_ranking` override records
the class, spec, slot, ordered item IDs, profile version, candidate digest,
and review evidence. For a guide-informed list, record the guide URL and
`guide_item_ids` in guide order. A changed snapshot or candidate set requires
fresh review.
After checking the live roster, set the scoring profile document's status to
`live_reviewed` and record the review evidence in its `review` object.

```powershell
python tools/scrape_wowhead.py import --flavor forever
python tools/validate_data.py --flavor forever
python tools/generate_lua.py --flavor forever
python tools/scrape_wowhead.py coverage --flavor forever --summary --strict
```

QuestieDB's public API is a candidate for checking spawn and entrance gaps.
Its documentation describes Classic-to-Forever coordinate transforms and
their limitations. ForeverDB documents a keyed API and a visible attribution
requirement. Confirm data reuse and how attribution would appear in the addon
before importing either provider's records. The pilot currently uses registered
Wowhead evidence. [QuestieDB API](https://github.com/Questie/QuestieDB/blob/master/docs/api.md)
· [ForeverDB API](https://foreverdb.net/developers)

## Pre-launch verification on November 4, 2026

Installed executable metadata reported Forever `1.60.1.70790` and Anniversary
`2.5.6.70577`. Both manifests booted from their complete load lists in Lua 5.1
fixtures. The separately staged installs matched their manifests and each
contained only its own dataset. A local combined archive check confirmed both
manifests and datasets, version substitution, release notes, and packaging
exclusions.

The published Forever UI source and installed executable identified the talent
group APIs and the quest completion API. All 547 tests passed. Fixtures exercised
talent selection and the manual fallback, account and character save isolation,
quest starters and turn-ins, and explicit waypoints with combat restrictions.
A separate replay exercised both trait update events. The standalone Forever
Lua fixture took 28 ms to load its manifest and 31 ms to open the main frame with
the empty draft dataset. API behavior and timings in the logged-in client
remain live checks.

Both datasets passed structural validation and deterministic generation. All 14
offline FullData audits passed individually. The authoritative FullData gate
stopped at the clean-worktree check. Forever strict coverage reported 862 missing
faction/spec/slot entries and an unreviewed roster.

The launch-day collection saved 35 guide snapshots and 123 item tooltips. Six
of the 28 spec gear guides contained item rows. The item tooltips yielded gear
slots and stats, with acquisition evidence still to review separately. The
refreshed recommendation audit contains 82 rows and no approved items or lists.

## Launch collection on November 4, 2026

The remaining 378 registered item URLs produced 181 new snapshots and 197
HTTP 404 responses from Wowhead's Forever tooltip endpoint. The corpus now has
304 item snapshots, 271 with gear slots. The tooltip footers provided named
drop leads for 59 items, including 46 gear records. Treat the names and rates
as pending source evidence. The tooltips did not provide NPC IDs, difficulty,
or coordinates. The refresh of all 28 gear guides produced no new item URLs.

The launch build 70790 armor and weapon catalog corroborated item name, quality,
and item level for all 257 overlapping records. The required level differed on
item 281586, which the tooltip omitted and the catalog listed as level 1. The
catalog also contains metadata for 187 of the 197 IDs that returned 404. This
cross-check is separate from the bundled data. [AHledger open data](https://ahledger.com/data)

The follow-up retry checked all 197 missing tooltips and recovered none. The
launch build's base `Item` table includes every ID, while its `ItemSparse` and
`ItemSearchName` exports omit all 197. The local build 70755 game cache also
contained none of the missing IDs. `build/forever-item-recovery/metadata-snapshots.json`
preserves the base fields for all 197 and separately attributes catalog identity
hints for 190. The metadata file stays outside the addon import. [Launch `Item` table](https://wago.tools/db2/Item?build=1.60.1.70790)

## Gear Guide presentation and correctness

Commit `faaf96f8` reduced the level-51 Retribution head list from 4,386
catalog entries to four obtainable upgrades. The archived rolls used build
70959. On build 71037 the old compatibility check rejected the entire index.
The fallback produced 42,661 rows, including 40,853 with an unknown source.
The regression covers those builds, an incomplete index, and core data alone.

The Forever Guide opens on a complete, clickable viewport. Shipped picks,
named routes, activity groups, ranks, ranges, and exact lookup indexes supply
the first page. Core picks cover an unavailable index. A changed client build
requires new evidence for inferred rolls. A single pending comparison names
its dependency on the affected row.

The displayed page owns its scroll position and click targets until its
replacement is ready. One automatic personalization per opening can publish
when the item under the pointer keeps its position. Further membership or
ordering changes wait for **Update list** in the footer. Verdicts on retained
rows can update in place.
Explicit navigation shows the requested page. Returning to an item preserves
its screen position and Details when possible.

Each pursuit needs an obtainable route and a practical reason. Keep the best
attainable slot choices, competitive easier routes, useful bag gear, claimable
rewards, and gear with a named situational use. Group weaker same-activity
choices, alternate routes, and random rolls. Dungeon filters and partial search
use the same rules. Exact item inspection includes the comparison and any
reason for exclusion.

The same per-character evidence drives the Guide, My Gear, hovers, and
loot badges. Gear Guide and Upgrades name destinations, BiS List labels guide
rank, My Gear gives the selected slot a next action, Wishlist shows the route
and ownership, Compare Slot names its reference, and Details leads with the
reason and the route. Use native item quality colors, Blizzard controls, and a
word or icon with each decision. Compact hovers put the active spec first and
give one supported reason per spec. Alt exposes the named comparison and the
rank, score, and effect assumptions.
Leveling opens to Gear Guide and endgame opens to Upgrades on a fresh save.
Subsequent opens honor the remembered tab.

| Offline regression | Expected player outcome |
| --- | --- |
| Level-51 Protection, equipped Aegis of Stormwind, banked Sword of Serenity | Keep the equipped shield. Alt names both pieces of the best owned pair. |
| Equal shield, stronger banked shield, or winning banked two-hander | Show a tie, the competing shield by name, or the stronger weapon setup, respectively. |
| A bank-only sword and an exact random roll on Wishlist | Ownership, filters, Details, and scoring agree on each copy from the last bank visit. |
| Withdrawal from a bank snapshot without instance IDs | The carried ring counts once and the new ring gains 5 points. With a second identical ring verified at the bank the comparison correctly loses 5 points. |
| Bag item for the second spec; future tie, loss, or gain | Equip advice applies to the active spec. Other specs name the gear to keep. Every forecast includes its level. |
| Tusken Helm with only a +0.002 gain | Filtering to Razorfen Kraul or a partial name yields no trip. Exact lookup explains the gain. |
| Level-51 Retribution with the Gothic helm, then a better banked helm | Four obtainable targets in the original fixture. Adding the banked item changes the personal result. Retain useful immediate gains, proc-dependent options, and quest winners by spec. |
| Fresh save, reload, warm reopen, level change, matching, newer and unavailable indexes | Full first viewport within 50 ms, warm reopen by the next frame, and at most 4 ms of addon work per interaction frame at 60 Hz. Record loading time and retained memory. Ordinary opens, hovers, and duplicate events perform zero full-catalog or all-level ranking passes. |
| Fifteen stationary seconds, duplicate events, long scroll jumps, and opening Details | Row identity, position, highlight, and click targets stay consistent on every visible frame. Repeat in both densities and at 900 × 500. |

The level-51 replay with 43 saved bank links identifies Sword of Serenity
in the bank and Aegis of Stormwind equipped. The native inventory hover
uses the held shield comparison. An additional equal shield uses the loot
comparison. The copy-count test also closes the bank during a scan and
checks that the last successful visit survives. The Aegis test loads the
addon again with the same saved variables and checks the verdict and both
weapon locations.

Stoneslayer keeps its Uldaman route with its reviewed bonus against Earth
Elementals. The rounding test checks Tusken Helm in the Guide, in Razorfen
Kraul, in partial search, and by exact item link. The quest replay changes a
ready turn-in while the section is visible, applies **Update list**, then
checks that filtering by slot includes the bag action on the first personal
page.

## Verify the live client

The user runs the in-game checks personally. Agent verification uses the
offline Lua harness and package checks. Computer Use is excluded. The update
is pending user verification on build 71037. Record the client build,
character level, spec, and the values printed by `/bbltest perf` after a fresh
open and a reopen. Check that a Guide pick opens its named route with one
click, and that an ordinary item hover says who benefits, when, and why.
Check both list densities with Details open at 900 × 500.
Check the equipped shield with its banked weapon partner and the evidence
under Alt. Hold the pointer still during the first personalization, then use
Update list after a real inventory change. The peak frame in `/bbltest perf`
includes the work that last contributed to it. A cold hover gives the active
spec first and can finish the other specs while the same item is under the
pointer.
Check that the native title, portrait, Close, Settings, and class selector are visible and clickable.
Open Compare slot from Gear Guide, inspect an item, visit Settings, and return through the same
item and slot to the original filtered list. Also check the first Endgame Upgrades and BiS List pages.

### Offline timing replay

Run `lua5.1 tests/forever_guide_timing.lua 71037 full Protection comfortable`
from the repository root. The other choices are build `70959`, payload
`core`, spec `Retribution`, and density `compact`. Append `details` to
exercise the route click at 900 × 500. Append `wide endgame` or `details endgame` after the density to replay level-60 Upgrades and BiS List, including final row order, routes, and ownership. Each process loads the Forever manifest
and dispatches the addon and player login events on a fresh save. The replay
checks the complete clickable viewport, watches 900 stationary frames,
sends duplicate events, reopens the Guide, hovers an item and opens its route.
Frame numbers use a simulated 60 Hz clock. Load time, handler time, and
retained Lua heap come from the local interpreter. The replay fails when a
viewport arrives after frame three or an interaction exceeds 4 ms. The
second heap sample includes the simulated widgets, equipment comparisons
and open Details after browsing.

### November 21, 2026 offline checks

All 138 focused checks passed, including the complete first viewport, stable
row bindings, exact lookup, both level-51 outfits and the saved verdict after
reload. The Forever canonical payload and both generated Guide files passed
their integrity checks. The local prerelease audit reports all 28 Pre-Raid
profiles reviewed and 3,448 uncovered leveling combinations.

Thirteen final timing replays passed the 50 ms first-page and 4 ms per-frame
checks. Each fresh-save configuration ran twice in a separate Lua process.
The last replay used the saved 43-link bank with the level-51 Protection
outfit. Every first visible page had all its click targets. The 15-second
hold and subsequent duplicate events changed zero row bindings, positions or
item targets. All runs recorded zero full rankings and zero unindexed level
summaries across opening, hovering and clicking.

| Build and payload | Level-51 spec and density | First clickable frame | Highest addon frame | Retained heap after browsing |
| --- | --- | ---: | ---: | ---: |
| 71037 full | Protection, comfortable | 2 | 4 ms | 173.0 MiB |
| 70959 full | Protection, compact, Details at 900 × 500 | 2 | 4 ms | 172.5 MiB |
| 71037 full | Retribution, compact, Details at 900 × 500 | 2 | 3 ms | 170.3 MiB |
| 70959 full | Retribution, comfortable | 2 | 3 ms | 168.0 MiB |
| 71037 core | Protection, compact | 3 | 3 ms | 44.9 MiB |
| 71037 core | Retribution, comfortable | 2 | 4 ms | 44.4 MiB |
| 71037 full, saved bank | Protection, comfortable | 2 | 4 ms | 173.2 MiB |

At simulated 60 Hz, frame two is about 33 ms and frame three is 50 ms.
Warm pages were clickable immediately and reopening took 0–1 ms. Loading
the full manifest took 0.98–1.09 s and retained 157.6 MiB before browsing.
The core manifest took 0.37–0.38 s and retained 42.2 MiB. The login handlers
took 0–1 ms at the interpreter clock's 1 ms resolution. The saved-bank hover
took 2 ms and the click into its named route took 4 ms.

During tuning, the elapsed-time check caught a 10 ms background slice and
a 6 ms core refresh. The final renderer can yield between shipped picks
while preparing the first page. Keep the strict check and the in-game
measurement in the pilot.

### Earlier incremental renderer

Three full-payload runs on build 71037
showed the first item on frame two. The complete viewport
appeared on frame three. Warm opens
took 1 ms. Loading the addon took 0.98–1.02 s and retained 157.5 MiB, about
22 MiB more than the previous Guide. The login event handlers took 0–1 ms
at the replay clock’s 1 ms resolution across all nine runs. The three
matching-build runs also filled the viewport on frame three. The core
payload alone retained 42.1 MiB and one of its three runs needed a fourth
frame. All nine reported zero full rankings
and zero unindexed level summaries. The highest measured frame was 4 ms
on 71037 with the full payload and 5 ms across all configurations. The
earlier renderer missed the 4 ms target across configurations.

Stage the Forever manifest through the [release workflow](release-process.md).
The local prerelease can be used for gameplay checks during availability review.
Record the in-game build and check fresh login, reload, class and spec
selection, equipment and bags, tooltips, wishlist, and the smoke commands.
Compare a level-49 item with a level-50 Auction House option with highlights
enabled and disabled. Exercise a tie, a cached bank replacement, the Pre-Raid
transition, and a quest with different winners for two activities. Verify that
exact roll names and projected placements agree between Details and tooltips.
Exercise faction-specific and item-started chains, a relocated vendor, a
dungeon entrance, an unknown location, and an existing native waypoint.
Verify quest state and waypoint actions independently, including combat.
Record cold startup, first-open time, and memory for the Forever artifact.

The initial snapshots were gathered before launch. The follow-up below records
the current collection and the limited approvals made from public evidence.
Strict coverage remains a release gate.

## Historical implementation follow-up

The counts and initial pilot results in this section predate the full leveling
source-review batch. Current counts and verification are recorded in
[Forever leveling implementation and intake](forever-leveling.md).

The intake now holds 710 evidence snapshots: 444 item pages/tooltips, 121 NPC
tooltips, 75 spell tooltips, 34 quest tooltips, 35 guides, and one empty Everloot
drop feed. These are evidence records, not 710 usable gear candidates. All 28
gear guides were refreshed again; six contain item rows. The ten guide-linked
stat gaps were retried and still returned 404. Seven previously unattempted
faction/profession pages returned 403. NPC 10586 also returned 404.

Recipe tooltips retain their crafted results as separate observations. Recipes
and quest starters no longer become equipment because of embedded gear or an
item name. Relic subtypes and class restrictions are retained. Dungeon guide
tables inside Wowhead's noscript tabs can inherit an unrelated preceding boss
heading: use table membership for the dungeon, not that heading for the boss.
NPC map observations include area IDs and zero/sentinel positions; none were
promoted to reviewed destinations.

The reviewed subset contains 36 items and 12 guide-informed alternative slot
lists across five profiles. Each approved dungeon route binds the named item
drop, NPC identity and zone, and corroborating Forever guide to content digests.
These are offline source reviews for the target build, not claims of observed
in-game drops. Public tooltip endpoints do not supply their observed build.
Drop percentages, difficulty, coordinates, and quest prerequisites remain
unpublished where not verified. The subset covers 24 of 862 faction/spec/slot
cells, leaving 838. All 28 scoring profiles and the live roster still need their
release review. Higher guide choices and unavailable/speculative routes remain
pending; the shipped subset uses `Alt`, not an absolute BiS assertion.

The four-profile pilot remains incomplete:

| Profile | Covered faction/slot cells | Required cells |
| --- | ---: | ---: |
| Warrior Protection | 6 | 30 |
| Warrior Arms | 0 | 28 |
| Shaman Restoration | 4 | 32 |
| Hunter Marksmanship | 0 | 32 |

Across the full roster, 450 cells have no reviewed route and 388 have reviewed
candidates but still need an approved ranking. Ten distinct guide-linked item
IDs lack usable stats. Complete profile/weight review before approving scored
fallback orders; the existing role weights remain draft inputs. The report
distinguishes that remaining review work from unavailable source evidence.

`data/canonical/forever/evidence.json` is derived during import. Approvals bind
item, route, and guide evidence independently; changed candidate inputs invalidate
ranking review. Conflicting item observations need an explicit resolution.
`retry_ledger.json` preserves the original 197 metadata-only lookups and subsequent
attempts, with catalog attribution kept separate from live item statistics.

```powershell
python tools/scrape_wowhead.py discover-sources --flavor forever
python tools/scrape_wowhead.py discover-sources --flavor forever --write
python tools/scrape_wowhead.py fetch --flavor forever --family acquisition --missing-only
python tools/scrape_wowhead.py reprocess --flavor forever
python tools/scrape_wowhead.py gaps --flavor forever --json
python tools/scrape_wowhead.py gaps --flavor forever --summary
```

Discovery previews unless `--write` is supplied. Cache reprocessing never fetches
the network. The gap report remains usable when approvals are stale; production
imports reject stale approvals. Status counts overlap: a cell can have approved
alternatives and still have unreviewed candidates or missing guide item stats.
`build/forever-provider/gap-report.json` records that earlier review queue.

Everloot pagination, partial failure, attribution, and empty-feed handling are
implemented through `collect-provider --flavor forever --provider everloot --url
<registered-url>`. It only replaces a normalized snapshot after the complete
fetch succeeds. Its public drop feed currently contains zero relationships.
Python's TLS request failed in this environment; the recorded sample used
Windows' normal certificate validation. Certificate verification was not
disabled. Reused observations retain CC BY-SA attribution, rendered beside
their source evidence. No ForeverDB key was available; no account was created.
QuestieDB remains a source of leads rather than an assertion that an NPC has not
moved or that an Era coordinate is a verified Forever waypoint.

## Source-review batch, 2026-11-05 local date

The current pre-raid import has 217 approved items and 431 independently
reviewed alternative lists across all 28 profiles. It covers all 862
faction/profile/slot cells and passes the strict pre-raid coverage audit.
Leveling remains incomplete: 147,332 of 155,284 cells are covered, with 7,952
early-level cells held for actual route or exhaustive no-item evidence.
These are reviewed alternatives from the verified corpus, not a claim
that higher unreviewed gear or conditional effects have been exhausted.

| Profile | Covered faction/slot cells | Required cells |
| --- | ---: | ---: |
| Warrior Protection | 30 | 30 |
| Warrior Arms | 28 | 28 |
| Shaman Restoration | 32 | 32 |
| Hunter Marksmanship | 32 | 32 |

The reviewed quest-trinket batch adds Thunderbrew's Boot Flask, Shard of the
Splithooves and Rune of the Guard Captain. Branch-specific minimums, faction
eligibility, full prerequisites and conditional effects are retained. The two
Heroes of Old entry chains share a final reward quest ID without becoming the
same acquisition route. Each profile's faction pools were reviewed before
choosing alternatives; no zero-score item was used as generic endgame filler.

The remaining pre-raid relic slots now have explicit qualitative approvals for
Mystic Mushroom, Polished Driftwood Icon and Libram of Invocation. Both faction
formula vendors, self-crafting skill/tool/reagent requirements, currency costs
and the applicable reputation gate are retained. Percentages are not converted
to invented flat stats. Separate recipe-vendor branches survive payload merging;
conflicting nested requirements reject generation.

Cursed Murloc Eye closes the previously empty Alliance physical trinket lists
as a modest obtainable offensive alternative. Its normal Gelihast drop and
linked current spell establish the two-Shadow-damage effect. The effect is not
two spell power and no attack-frequency/DPS conversion or BiS claim is made.
Stronger unverified endgame trinkets remain in the evidence backlog.

Profiles use `source_reviewed`; gameplay acceptance remains a separate,
artifact-bound public-release gate. Neither incomplete coverage nor pending
live checks have been waived. No client deployment, tag or publication occurred.

`build/forever-review/pre-raid-gaps-current.json` records the current diagnostic
queue. Each row keeps scored provisional item references; evidence, routes and
conflicts are stored once in top-level `provisional_items`. The complete JSON
report is about 27 MB instead of repeating the same evidence in every profile
and faction cell. Stale decisions remain inspectable; production imports
continue to reject them.

Current item-tooltip retries still return 404 for the missing named trinket and
relic leads. Everloot's observed-edge endpoint was rechecked through Windows'
normal TLS validation and still returns 45 edges; its requested high-value
item cards return 404. That does not imply an item is unobtainable or that all
provider endpoints are empty. Pix Xizzix's currency acquisition remains
unconfirmed by the current source guide. QuestieDB's composed API now supports
corroborated facts; raw records and coordinates remain separate leads.

The later Everloot corpus refresh advertised 17,793 records but reached its
public hourly rate limit after 27 valid pages. The incomplete refresh and
repeated staging pages were quarantined; canonical evidence remains the
previous snapshot. The valid 13,500-record prefix did not resolve the pending
early slots. The retry ledger retains that failure and its cooldown.
Journeyman's Stave now has reviewed level-five market routes for both factions.
The neutral Gnomish Universal Remote formula route remains held for conflicting
vendor stock. Low-level raid-named rings with beta-finale drop observations
also remain held until ordinary launch availability is corroborated.

## Targeted local observations

The optional development addon is under `tools/recorder/BigBiSList_Recorder` and
is excluded from the main package. Its explicit targets cover the ten remaining
guide stat IDs, Felstriker, and the eight equipment results recovered from
recipe tooltips whose acquisition still needs review. Install the development
addon beside BigBiSList only when collecting those gaps. It starts disabled on
every login; enable it with `/run BigBiSList.Recorder:Enable()` and stop with
`/run BigBiSList.Recorder:Disable()`. A custom array of item IDs may be passed to
`Enable` for a different reviewed gap. It never probes unseen IDs.

It records public item text and targeted loot, quest reward, and vendor
interactions in the existing `BigBiSListDB.forever.capture` table. Ambiguous loot
has no attributed NPC. Player positions and entrance observations remain
approximate leads. The recorder writes no account/character names, chat, or
full source GUIDs, excludes creator text, and has no upload mechanism. Reload
or log out to flush SavedVariables before selecting the file for import.

```powershell
python tools/scrape_wowhead.py import-captures --flavor forever --file <selected-file> --client-build 1.60.1.70790
python tools/scrape_wowhead.py import-captures --flavor forever --file <selected-file> --client-build 1.60.1.70790 --write
```

The default is a preview. JSON capture documents and the SavedVariables literal
subset are parsed as data; Lua is never executed. Wrong-client, mixed/stale-build,
malformed, excessive, and private-tooltip records are rejected before writes.
Imports deduplicate observations, strip unrelated saved state, register only
normalized evidence, and never approve items or ranks. Limits are 8 MiB per input,
64 table nesting levels, and 5,000 observations. Import an existing build's
captures before starting collection on a new build; the recorder preserves them
instead of silently resetting the saved table.

## Earlier verification milestones

At the initial implementation milestone, all 580 tests passed without skips after restoring declared dependencies,
including Pillow. The safe importer, opt-in recorder, attribution rendering,
source discovery, conflicts, stale approvals, and both manifest load paths have
fixture coverage. Both generated payloads passed validation and generation
checks; both client packages compiled and were staged separately under
`build/forever-implementation-smoke`.

The current source-review batch passes all 633 tests without skips, both
flavors' canonical validation and generation checks, Lua 5.1 compilation and
PowerShell script parsing. Populated data covers default faction filtering
through gear lists, planner, wishlist, comparisons and tooltips, as well as the
separate Heroes of Old entry chains, shared starter rings, profession rank
minimums and prepared Druid relic routes. Strict pre-raid coverage passes.
Strict leveling coverage still fails with 7,952 early-level cells; these
successful offline checks do not authorize deployment.

Computer Use refused access to the running Forever window with "Computer Use
was not approved to use wow." The user requested that live checks remain
pending. No live reload, quest/waypoint acceptance test, or in-game performance
claim was made. The full release gate was not run: the worktree is dirty,
coverage is incomplete, and the live checks remain pending. Follow the
[authoritative release process](release-process.md) before tagging or publishing.
