"""Evidence-bound Forever leveling; draft candidates never become published gear."""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy

from tools.project import dataset_json
from tools.forever import (FACTIONS, SOURCE_CHILDREN, check_evidence_refs, digest, evidence_index,
                           has_review, item_observations, item_conflicts, load_verified_items, numeric, roster,
                           valid_route_eligibility)
from tools.forever_sources import evidence_ref, route_leads
from tools.recommend_leveling import (compact_adjacent_recommendation_ranges, materialized_items,
                                      recommendation_rows_for_items, roll_identity, rules_allow_equipment, slot_matches)
from tools.sources import summarize_sources
from tools import forever_availability as availability


def mask_has(mask: int, bit: int) -> bool:
    # Python integers preserve Forever's race bits above bit 31.
    return type(mask) is int and type(bit) is int and mask >= 0 and bit >= 0 and bool(mask & (1 << bit))


def preferred_item_id(review: dict) -> int | None:
    choices = review.get("choices")
    if isinstance(choices, list) and choices and isinstance(choices[0], dict):
        identifier = choices[0].get("item_id")
    else:
        identifiers = review.get("item_ids")
        identifier = identifiers[0] if isinstance(identifiers, list) and identifiers else None
    return identifier if type(identifier) is int and identifier > 0 else None


def eligibility_allows(eligibility: dict, faction: str, race: str, class_name: str, level: int) -> bool:
    if type(eligibility) is not dict or type(eligibility.get("min_level")) is not int:
        return False
    return (eligibility["min_level"] <= level
            and level <= eligibility.get("max_level", 60)
            and eligibility.get("side", "Both") in {"Both", faction}
            and (not eligibility.get("races") or race in eligibility["races"])
            and (not eligibility.get("classes") or class_name in eligibility["classes"]))


def route_allows(source: dict, faction: str, race: str, class_name: str, level: int) -> bool:
    """All dependency families are required; members of a family are alternatives."""
    if (source.get("side") not in {"Both", faction} or source.get("content_type") == "raid"
            or source.get("type") == "pvp" or not eligibility_allows(source.get("eligibility"), faction, race, class_name, level)):
        return False
    return all(not source.get(key) or any(route_allows(child, faction, race, class_name, level)
                                        for child in source[key]) for key in SOURCE_CHILDREN)


def valid_eligibility(source: dict) -> bool:
    return (isinstance(source, dict) and valid_route_eligibility(source.get("eligibility"))
            and all(isinstance(source.get(key, []), list) and all(valid_eligibility(child) for child in source.get(key, []))
                    for key in SOURCE_CHILDREN))


def starter_quest_items(snapshots: dict) -> dict:
    by_quest = defaultdict(list)
    for snapshot in snapshots.values():
        if snapshot.get("item_kind") == "quest_starter":
            for link in snapshot.get("linked_entities", []):
                if link.get("type") == "quest":
                    by_quest[link["id"]].append(snapshot)
    return by_quest


def validate_starter_gates(source: dict, snapshots: dict, by_quest: dict | None = None) -> None:
    """A reviewed quest-start item gate is independent of the reward's equip level."""
    identifier = source.get("quest_starter_item_id")
    by_quest = starter_quest_items(snapshots) if by_quest is None else by_quest
    known = by_quest.get(source.get("quest_id"), []) if source.get("type") == "quest" else []
    if identifier is None and known:
        identifiers = {row["item_id"] for row in known}
        if len(identifiers) != 1:
            raise ValueError("Multiple quest starter items require an explicit route review")
        identifier = next(iter(identifiers))
    if identifier is not None:
        starters = [row for row in snapshots.values() if row.get("item_id") == identifier
                    and row.get("item_kind") == "quest_starter"]
        # A complete tooltip may omit the numeric gate that the client table supplies.
        gate_rows = [row for row in starters if row.get("item_stats", {}).get("required_level") is not None]
        observed_levels = [row["item_stats"]["required_level"] for row in gate_rows]
        if any(type(level) is not int or not 0 <= level <= 60 for level in observed_levels):
            raise ValueError("Quest starter gate needs an unambiguous current item and quest relationship")
        levels = set(observed_levels)
        linked_gates = [row for row in gate_rows
                        if any(link.get("type") == "quest" and link.get("id") == source.get("quest_id")
                               for link in row.get("linked_entities", []))]
        if len(levels) != 1 or not linked_gates:
            raise ValueError("Quest starter gate needs an unambiguous current item and quest relationship")
        minimum = next(iter(levels))
        if source.get("eligibility", {}).get("min_level", 0) < minimum:
            raise ValueError("Acquisition minimum is below the quest starter's required level")
        support = {ref["evidence_id"] for ref in source.get("evidence_refs", [])}
        if not any(evidence_ref(row["url"], snapshots)["evidence_id"] in support for row in linked_gates):
            raise ValueError("Quest starter gate must bind the starter item evidence")
    for key in SOURCE_CHILDREN:
        for child in source.get(key, []):
            validate_starter_gates(child, snapshots, by_quest)


def absence_covers(snapshot: dict, profile: dict, persona: dict, slot: str, minimum: int, maximum: int) -> bool:
    """An exhaustive inventory is useful only within its explicitly reviewed scope."""
    if snapshot.get("exhaustive_eligibility") is not True:
        return False
    return any(isinstance(scope, dict)
               and all(scope.get(key) == value for key, value in {
                   **profile, "faction": persona["faction"], "race_id": persona["id"], "slot": slot}.items())
               and type(scope.get("level_min")) is int and type(scope.get("level_max")) is int
               and scope["level_min"] <= minimum <= maximum <= scope["level_max"]
               for scope in snapshot.get("eligibility_scopes", []))


def guide_gear(rows: list[dict], snapshots: dict, manifest: dict) -> list[dict]:
    """Keep guide claims separate from computed gear, but apply the same reviewed eligibility."""
    claims = {}
    for source in manifest.get("sources", []):
        if source.get("data_family") != "leveling" or not source.get("class") or not source.get("spec"):
            continue
        for table in snapshots.get(source["url"], {}).get("tables", []):
            for claim in table.get("rows", []):
                if type(claim.get("item_id")) is int:
                    claims.setdefault((source["class"], source["spec"], claim["item_id"]), []).append((source["url"], claim))
    gear = []
    for row in rows:
        for url, claim in claims.get((row["class"], row["spec"], row["item_id"]), []):
            lo = max(row["level_min"], claim.get("level_min") or 1)
            hi = min(row["level_max"], claim.get("level_max") or 59)
            if lo > hi:
                continue
            gear.append({**{key: row[key] for key in ("class", "spec", "race", "race_id", "faction", "slot", "item_id", "rank")},
                         **{key:row[key] for key in ("variant_id", "variant_name", "random_suffix_id") if key in row},
                         "level_min": lo, "level_max": hi, "level_label": f"{lo}-{hi}",
                         "category_label": "Recommended", "section": claim.get("section"),
                         "source_note": claim.get("source_text", ""), "source_url": url})
    return compact_adjacent_recommendation_ranges([dict(row) for row in {digest(row): row for row in gear}.values()])


def validate_rules(rules: dict, profiles: dict) -> list[str]:
    errors = []
    if rules.get("flavor") != "forever" or rules.get("max_level") != 59:
        errors.append("Forever leveling rules require flavor forever and max_level 59")
    covered = [level for _, lo, hi in rules.get("level_bands", []) for level in range(lo, hi + 1)]
    if covered != list(range(1, 60)):
        errors.append("Forever level bands must cover 1-59 exactly once")
    expected = {f"{c}/{s}" for c, s in roster()}
    if set(profiles.get("spec_roles", {})) != expected or set(rules.get("spec_policies", {})) != expected:
        errors.append("Leveling profiles and equipment policies must cover the Forever roster")
    identities = set()
    for race in rules.get("races", []):
        identity = race.get("id")
        if (type(identity) is not int or identity <= 0 or identity in identities
                or race.get("faction") not in FACTIONS or not race.get("name") or not race.get("classes")):
            errors.append("Invalid or duplicate Forever race persona")
        identities.add(identity)
    if not identities:
        errors.append("Forever race/class/faction personas have not been established")
    for equipment in rules.get("class_equipment", {}).values():
        if not equipment.get("armor_tiers") or not equipment.get("weapon_types"):
            errors.append("Incomplete Forever equipment rules")
        two_hand = equipment.get("two_hand_weapon_types", [])
        if not isinstance(two_hand, list) or not set(two_hand).issubset(equipment.get("weapon_types", [])):
            errors.append("Invalid Forever two-handed weapon proficiencies")
        for unlock in equipment.get("weapon_unlocks", []):
            if (not isinstance(unlock, dict) or not unlock.get("weapon_subtype") or not unlock.get("slots")
                    or type(unlock.get("min_level")) is not int or not 1 <= unlock["min_level"] <= 59):
                errors.append("Invalid Forever weapon-training breakpoint")
    for policy in rules.get("spec_policies", {}).values():
        for slot in policy.get("slots", []):
            minimum = policy.get("slot_min_levels", {}).get(slot, 1)
            maximum = policy.get("slot_max_levels", {}).get(slot, 59)
            if type(minimum) is not int or type(maximum) is not int or not 1 <= minimum <= maximum <= 59:
                errors.append("Invalid Forever applicable-slot level range")
    if not profiles.get("version") or not rules.get("version"):
        errors.append("Leveling profiles and rules require versions")
    for weights in list(profiles.get("role_defaults", {}).values()) + [p.get("weights", {}) for p in profiles.get("profiles", [])]:
        if not all(numeric(value) for value in weights.values()):
            errors.append("Leveling weights must be finite numbers")
    revisions = profiles.get("weight_revisions", {})
    band_names = {name for name, _, _ in rules.get("level_bands", [])}
    if not isinstance(revisions, dict) or any(
            key not in expected or not isinstance(revision, dict) or not isinstance(revision.get("version"), str)
            or not revision["version"].strip() or not isinstance(revision.get("weights"), dict)
            or not revision["weights"] or not all(numeric(value) for value in revision["weights"].values())
            or ("level_bands" in revision and (not isinstance(revision["level_bands"], list)
                or not revision["level_bands"] or not all(band in band_names for band in revision["level_bands"])))
            for key, revision in revisions.items()):
        errors.append("Invalid Forever specialization weight revision")
    return sorted(set(errors))


def inputs() -> tuple[dict, dict, dict, dict, dict]:
    return tuple(dataset_json("forever", name) for name in (
        "leveling_rules", "leveling_scoring_profiles", "racial_modifiers", "item_variants", "leveling_reviews"))


def rule_reviewed(rules: dict, profiles: dict, racials: dict, records: dict) -> bool:
    for document in (rules, profiles, racials):
        if document.get("status") != "reviewed" or not has_review(document.get("review", {})):
            return False
        check_evidence_refs(document["review"], records)
    for revision in profiles.get("weight_revisions", {}).values():
        review = revision.get("review", {})
        if not has_review(review):
            return False
        check_evidence_refs(review, records)
    for racial in racials.get("racial_modifiers", []):
        if racial.get("type") != "numeric":
            continue
        if not has_review(racial):
            return False
        check_evidence_refs(racial, records)
        modifier = racial.get("modifier", {})
        if (not isinstance(modifier, dict) or not modifier.get("stat") or not numeric(modifier.get("value"))
                or racial.get("faction", "Both") not in {"Both", *FACTIONS}
                or type(racial.get("level_min", 1)) is not int or type(racial.get("level_max", 59)) is not int
                or not 1 <= racial.get("level_min", 1) <= racial.get("level_max", 59) <= 59):
            raise ValueError("Invalid reviewed Forever numeric racial effect")
    return True


def reviewed_facts(snapshots: dict, reviews: dict, *, diagnostic: bool, records: dict, conflicts: dict) -> tuple[dict, dict, list[dict]]:
    items, stats, issues = {}, {}, []
    starter_items = starter_quest_items(snapshots)
    for review in reviews.get("items", []):
        try:
            if review.get("type") != "verify_item":
                raise ValueError("Unknown leveling fact review")
            if not all(valid_eligibility(source) for source in review.get("sources", [])):
                raise ValueError("Every leveling route needs reviewed acquisition eligibility")
            for source in review.get("sources", []):
                validate_starter_gates(source, snapshots, starter_items)
            item_rows, stat_rows = load_verified_items(snapshots, [review], records=records, conflicts=conflicts)
            for item in stat_rows.values():
                if "recommendation_excluded" in review:
                    if (type(review["recommendation_excluded"]) is not bool
                            or (review["recommendation_excluded"] and not isinstance(review.get("exclusion_reason"), str))
                            or (review["recommendation_excluded"] and not review["exclusion_reason"].strip())):
                        raise ValueError("Recommendation exclusions need an explicit reviewed reason")
                    item["recommendation_excluded"] = review["recommendation_excluded"]
                if not isinstance(item.get("stats", {}), dict) or not all(numeric(value) for value in item.get("stats", {}).values()):
                    raise ValueError("Leveling stats must be finite numeric facts")
                if item["slot"] in {"Head", "Shoulder", "Chest", "Wrist", "Hands", "Waist", "Legs", "Feet"} and not item.get("armor_type"):
                    raise ValueError("Leveling armor needs an observed armor proficiency type")
                if item["slot"] in {"Main Hand", "Two Hand", "One Hand", "Ranged"} and not item.get("weapon_subtype"):
                    raise ValueError("Leveling weapons need an observed weapon subtype")
                declared = review.get("equip_level")
                if item.get("required_level") is None:
                    if type(declared) is not int or not 1 <= declared <= 60:
                        raise ValueError("Missing equip level needs an explicit evidence-bound review")
                    item["required_level"] = declared
                elif declared is not None and declared != item["required_level"]:
                    raise ValueError("Equip level review conflicts with the item tooltip")
                if type(item["required_level"]) is not int or not 0 <= item["required_level"] <= 60:
                    raise ValueError("Equip level must be an observed whole level")
                if any(item.get(key) for key in ("equip_effects", "use_effects", "effect_stats", "set_bonuses")) and review.get("effects_reviewed") is not True:
                    raise ValueError("Leveling effects require explicit review")
                if "variant_only" in review:
                    if type(review["variant_only"]) is not bool:
                        raise ValueError("Random-affix-only gear needs an explicit boolean review")
                    item["variant_only"] = review["variant_only"]
            if items.keys() & item_rows.keys():
                raise ValueError("Duplicate leveling item approval")
            items.update(item_rows)
            stats.update(stat_rows)
        except (KeyError, TypeError, ValueError) as exc:
            if not diagnostic:
                raise
            issues.append({"item_id": review.get("item_id"), "reason": str(exc)})
    return items, stats, issues


def eligible_item(item: dict, profile: dict, persona: dict, level: int, slot: str, rules: dict) -> dict | None:
    if item.get("recommendation_excluded") is True:
        return None
    if not slot_matches(item.get("slot"), slot):
        return None
    equip_level = item.get("required_level")
    # Missing equip-level evidence is unknown, never implicitly level one.
    if type(equip_level) is not int or equip_level > level:
        return None
    restrictions = item.get("restrictions", {})
    if ((restrictions.get("classes") and profile["class"] not in restrictions["classes"])
            or (restrictions.get("races") and persona["name"] not in restrictions["races"])):
        return None
    sources = [source for source in item.get("sources", []) if route_allows(
        source, persona["faction"], persona["name"], profile["class"], level)]
    if not sources or not rules_allow_equipment(item, profile["class"], profile["spec"], level, slot, rules):
        return None
    return {**item, "sources": sources, "primary_source": sources[0], "source_summary": summarize_sources(sources)}


AVAILABILITY_REVIEW_STATUSES = {"unreviewed_availability", "pending_empty_slot_review"}


def availability_review_ranges(audit: list[dict]) -> list[dict]:
    def context(row):
        return row["class"], row["spec"], row["faction"], row["race_id"], row["slot"]

    first_recommendations = {}
    for row in audit:
        if row["status"] == "approved":
            key, level = context(row), row["level_min"]
            first_recommendations[key] = min(level, first_recommendations.get(key, level))

    per_level = Counter()
    unresolved_by_level = defaultdict(set)
    for row in audit:
        if row["status"] not in AVAILABILITY_REVIEW_STATUSES:
            continue
        first = first_recommendations.get(context(row))
        availability = row["availability"]
        for level in range(row["level_min"], row["level_max"] + 1):
            key = (row["slot"], row["faction"], row["status"], first, availability["complete"], level)
            per_level[key] += 1
            unresolved_by_level[key].update(availability["unresolved_item_ids"])
    return compact_adjacent_recommendation_ranges([
        {"slot": slot, "faction": faction, "status": status, "level_min": level, "level_max": level,
         "first_recommended_level": first, "combinations_per_level": count, "inventory_complete": complete,
         "unresolved_candidate_count": len(unresolved_by_level[(slot, faction, status, first, complete, level)])}
        for (slot, faction, status, first, complete, level), count in per_level.items()
    ])


def generate(snapshots: dict, *, diagnostic: bool = False, review_document: dict | None = None) -> dict:
    rules, profiles, racials, variants, reviews = inputs()
    if review_document is not None:
        reviews = review_document
    errors = validate_rules(rules, profiles)
    records = evidence_index(snapshots)
    conflicts = item_conflicts(snapshots)
    items, stats, issues = reviewed_facts(snapshots, reviews, diagnostic=diagnostic, records=records, conflicts=conflicts)
    availability_doc = reviews.get("availability", {})
    inventory = availability.build_inventory(snapshots, availability_doc, rules, records)
    for issue in inventory["source_issues"] + inventory["decision_issues"]:
        if not diagnostic:
            raise ValueError("Invalid availability review: " + issue["reason"])
        issues.append({**issue, "kind":"availability"})
    excluded_items = {row["item_id"]: row for row in reviews.get("items", [])
                      if row.get("recommendation_excluded") is True and row["item_id"] in items}
    availability_rows = []
    availability_equipment_cache = {}
    availability_support_digest_cache = {}
    availability_rules_digest = digest(rules)
    ready = False
    try:
        ready = not errors and rule_reviewed(rules, profiles, racials, records)
    except ValueError as exc:
        if not diagnostic:
            raise
        issues.append({"reason": str(exc)})
    if errors and not diagnostic:
        raise ValueError("; ".join(errors))
    reviewed_variants = []
    seen_variants = set()
    for variant in variants.get("item_variants", []):
        try:
            if not isinstance(variant, dict):
                raise ValueError("Invalid Forever suffix variant")
            identity, _ = roll_identity(variant)
            if (identity in seen_variants or variant["item_id"] not in stats
                    or any(not isinstance(variant.get(field, {}), dict) for field in ("stat_delta", "stats"))
                    or not all(numeric(value) for field in ("stat_delta", "stats") for value in variant.get(field, {}).values())
                    or not (variant.get("stat_delta") or variant.get("stats"))
                    or ("required_level" in variant and (type(variant["required_level"]) is not int
                                                        or not 0 <= variant["required_level"] <= 60))
                    or ("item_level" in variant and (type(variant["item_level"]) is not int or variant["item_level"] < 1))
                    or not isinstance(variant.get("suffix_name"), str) or not variant["suffix_name"].strip()
                    or not has_review(variant)):
                raise ValueError("Forever suffix variants need an explicit review")
            support = check_evidence_refs(variant, records)
            if (variant.get("bonus_fields") or variant.get("suffix_parameter") or "required_level" in variant
                    or "item_level" in variant) and not any(
                    row["observed_build"] == variant["client_build"] for row in support):
                raise ValueError("An exact Forever bonus or scaling payload needs evidence from its reviewed client build")
            seen_variants.add(identity)
            reviewed_variants.append(variant)
        except (KeyError, TypeError, ValueError) as exc:
            if not diagnostic:
                raise
            issues.append({"reason": str(exc), "kind": "variant"})
    candidates = materialized_items(list(stats.values()), reviewed_variants)
    candidates = [item for item in candidates if not item.get("variant_only") or item.get("variant_id")]
    roll_reviews = {roll_identity(variant)[0]: digest(variant) for variant in reviewed_variants}
    candidate_facts = {(item["id"], item.get("variant_id")): digest({key:value for key,value in item.items()
                       if key not in {"sources", "primary_source", "source_summary"}}) for item in candidates}
    source_digests = {id(source):digest(source) for item in candidates for source in item.get("sources", [])}
    all_slots = set(rules.get("common_slots", [])) | {slot for policy in rules.get("spec_policies", {}).values() for slot in policy.get("slots", [])}
    candidates_by_slot = {slot:[item for item in candidates if slot_matches(item.get("slot"),slot)] for slot in all_slots}
    approvals = {}
    expanded_reviews = []
    for review in reviews.get("rankings", []):
        race_ids = review.get("race_ids")
        if race_ids is None:
            expanded_reviews.append(review)
            continue
        if ("race_id" in review or not isinstance(race_ids, list) or not race_ids
                or any(type(value) is not int or value <= 0 for value in race_ids) or len(set(race_ids)) != len(race_ids)):
            if not diagnostic:
                raise ValueError("Invalid grouped leveling race approval")
            issues.append({"reason":"Invalid grouped leveling race approval","kind":"ranking"})
            continue
        expanded_reviews.extend({**review, "race_id":race_id} for race_id in race_ids)
    for review in expanded_reviews:
        key = (review.get("class"), review.get("spec"), review.get("slot"), review.get("faction"), review.get("race_id"), review.get("level_min"), review.get("level_max"))
        if key in approvals:
            if not diagnostic:
                raise ValueError("Duplicate leveling ranking approval")
            approvals[key] = {**review, "invalid_overlap": True}
            issues.append({"reason": "Duplicate leveling ranking approval", "kind": "ranking"})
            continue
        approvals[key] = review
    approvals_by_context = defaultdict(list)
    for key, review in approvals.items():
        approvals_by_context[key[:5]].append((key, review))
    rows, audit, gaps = [], [], []
    used = set()
    observations = item_observations(snapshots)
    leads = route_leads(snapshots)
    provisional_items = []
    item_reviews = {r.get("item_id"):r for r in reviews.get("items", []) if isinstance(r, dict)}
    for identifier, observations_for_item in sorted(observations.items()):
        observation = observations_for_item[0]
        parsed = observation.get("item_stats", {})
        if not parsed.get("slot"):
            continue
        provisional_items.append({"item_id": identifier, "name": observation.get("name"),
            "slot": parsed["slot"], "equip_level": parsed.get("required_level"),
            "armor_type": parsed.get("armor_type"), "weapon_subtype": parsed.get("weapon_subtype"),
            "restrictions": parsed.get("restrictions", {}), "stats": parsed.get("stats", {}),
            "snapshot_url": observation["evidence_url"],
            "evidence_ref": evidence_ref(observation["evidence_url"], snapshots),
            "conflicting_evidence": conflicts.get(identifier, []), "item_reviewed": identifier in items,
            "recommendation_excluded": item_reviews.get(identifier, {}).get("recommendation_excluded", False),
            "exclusion_reason": item_reviews.get(identifier, {}).get("exclusion_reason"),
            "effects_need_review": bool(parsed.get("equip_effects") or parsed.get("use_effects") or parsed.get("set_bonuses")),
            "route_leads": leads.get(identifier, [])})
    # Preserve the original inputs of existing approvals. Each weight revision
    # binds only the ranking scopes that use it.
    base_profiles = {key: value for key, value in profiles.items() if key != "weight_revisions"}
    input_signature = {"profile": digest(base_profiles), "rules": digest(rules), "racials": digest(racials),
                       "variants": digest({**variants, "item_variants": []})}
    revisions = profiles.get("weight_revisions", {})
    revision_digests = {key: digest(revision) for key, revision in revisions.items()} if isinstance(revisions, dict) else {}

    def candidate_signature(eligible, spec_key, level):
        revision = revision_digests.get(spec_key)
        if revision and (bands := revisions[spec_key].get("level_bands")):
            if not any(low <= level <= high and band in bands for band, low, high in rules["level_bands"]):
                revision = None
        return digest({"candidates": [{"fact":candidate_facts[(item["id"],item.get("variant_id"))],
            "routes":[source_digests[id(source)] for source in item["sources"]],
            **({"roll_review": roll_reviews[item["variant_id"]]} if item.get("variant_id") in roll_reviews else {})}
            for item in sorted(eligible,key=lambda item:(item["id"],item.get("variant_id") or ""))],
            **input_signature, **({"weight_revision": revision} if revision else {})})
    contexts = profiles.get("runtime_contexts", ["best_overall"])
    if contexts != ["best_overall"]:
        raise ValueError("Forever leveling currently publishes the best_overall context")
    for spec_key in sorted(profiles.get("spec_roles", {})):
        class_name, spec_name = spec_key.split("/", 1)
        policy = rules.get("spec_policies", {}).get(spec_key, {})
        profile = {"class": class_name, "spec": spec_name}
        for persona in rules.get("races", []):
            if class_name not in persona["classes"]:
                continue
            for slot in rules.get("common_slots", []) + policy.get("slots", []):
                context_approvals = approvals_by_context.get((class_name, spec_name, slot, persona["faction"], persona["id"]), [])
                slot_candidates = candidates_by_slot[slot]
                paired = slot == "Off Hand" and policy.get("dual_wield_level") is not None
                pair_candidates = candidates_by_slot.get("Main Hand", []) if paired else []
                minimum = policy.get("slot_min_levels", {}).get(slot, 1)
                maximum = policy.get("slot_max_levels", {}).get(slot, 59)
                points = {minimum, maximum + 1}
                points.update(rank["min_level"] for rule in availability_doc.get("profession_rules", []) for rank in rule.get("ranks", []))
                for candidate in inventory["candidates"]:
                    if slot in candidate["slots"]:
                        points.update(row["required_level"] for row in candidate["observations"]
                                      if type(row.get("required_level")) is int)
                for decision in availability_doc.get("decisions", []):
                    scope = decision.get("scope", {})
                    if scope.get("slot", slot) == slot:
                        hi = scope.get("level_max", 59)
                        points.update(value for value in (scope.get("level_min"), hi + 1 if type(hi) is int else None,
                                                         decision.get("minimum_level")) if type(value) is int)
                points.update(lo for _, lo, _ in rules["level_bands"] if lo >= minimum)
                points.update(tier["level"] for tier in rules.get("class_equipment", {}).get(class_name, {}).get("armor_tiers", []) if tier["level"] >= minimum)
                points.update(unlock["min_level"] for unlock in rules.get("class_equipment", {}).get(class_name, {}).get("weapon_unlocks", []))
                for racial in racials.get("racial_modifiers", []):
                    points.update((racial.get("level_min", 1), racial.get("level_max", 59) + 1))
                if policy.get("dual_wield_level") is not None:
                    points.add(policy["dual_wield_level"])
                if policy.get("form_level") is not None:
                    points.add(policy["form_level"])
                def route_points(source):
                    value = source.get("eligibility", {}).get("min_level")
                    if type(value) is int:
                        points.add(value)
                    maximum = source.get("eligibility", {}).get("max_level")
                    if type(maximum) is int:
                        points.add(maximum + 1)
                    for child_key in SOURCE_CHILDREN:
                        for child in source.get(child_key, []):
                            route_points(child)
                # A main-hand-only upgrade can change the legal preferred pair
                # while leaving the off-hand pool itself unchanged.
                for item in slot_candidates + pair_candidates:
                    if type(item.get("required_level")) is int:
                        points.add(item["required_level"])
                    for source in item.get("sources", []):
                        route_points(source)
                paired_reviews = approvals_by_context.get((class_name,spec_name,"Main Hand",persona["faction"],persona["id"]), []) if paired else []
                for key, _ in context_approvals + paired_reviews:
                    if type(key[5]) is int and type(key[6]) is int:
                        points.update((key[5], key[6] + 1))
                points = sorted(point for point in points if minimum <= point <= maximum + 1)
                for level, end in zip(points, points[1:]):
                    eligible = [result for item in slot_candidates if (result := eligible_item(item, profile, persona, level, slot, rules))]
                    pair_signature = None
                    pair_main_id = None
                    if paired:
                        pair_eligible = [result for item in pair_candidates if (result := eligible_item(item, profile, persona, level, "Main Hand", rules))]
                        pair_signature = candidate_signature(pair_eligible, spec_key, level)
                        pair_selected, _ = recommendation_rows_for_items(pair_eligible, racials, profiles, class_name=class_name,
                            spec_name=spec_name, race=persona["name"], level=level, slot="Main Hand", rules=rules, faction=persona["faction"])
                        if pair_selected:
                            pair_main_id = pair_selected[0]["item_id"]
                        main_reviews = [r for key,r in paired_reviews if type(key[5]) is int and type(key[6]) is int
                                        and key[5] <= level <= key[6] and r.get("candidate_digest")==pair_signature
                                        and r.get("profile_version")==profiles["version"] and r.get("rules_version")==rules["version"]]
                        if len(main_reviews)==1:
                            declared_main=preferred_item_id(main_reviews[0])
                            if declared_main in {item["id"] for item in pair_eligible}:
                                pair_main_id=declared_main
                        if pair_main_id is not None and stats.get(pair_main_id, {}).get("max_equipped")==1:
                            eligible=[item for item in eligible if item["id"]!=pair_main_id]
                    selected, _ = recommendation_rows_for_items(eligible, racials, profiles, class_name=class_name,
                        spec_name=spec_name, race=persona["name"], level=level, slot=slot, rules=rules, faction=persona["faction"])
                    signature = candidate_signature(eligible, spec_key, level)
                    if paired:
                        signature = digest({"off_hand":signature,"main_hand":pair_signature})
                    found = None
                    for key, review in context_approvals:
                        if type(key[5]) is int and type(key[6]) is int and key[5] <= level <= key[6]:
                            if found is not None:
                                if not diagnostic:
                                    raise ValueError("Overlapping leveling ranking approvals")
                                found = (key, {**review, "invalid_overlap": True})
                                break
                            found = (key, review)
                    status = "pending_ranking_review"
                    approved = False
                    availability_check = None
                    if not eligible:
                        availability_check = availability.review_scope(inventory, availability_doc, profile, persona,
                            slot, level, end - 1, rules, records, snapshots, excluded_items=excluded_items,
                            equipment_cache=availability_equipment_cache, rules_digest=availability_rules_digest,
                            support_digest_cache=availability_support_digest_cache)
                        status = "unreviewed_availability"
                        if (availability_check["complete"] and not availability_check["unresolved_item_ids"]
                                and not availability_check["review_issues"]):
                            status = "pending_empty_slot_review"
                    if not ready:
                        status = "pending_profile_review"
                    if found:
                        key, review = found
                        used.add(key)
                        try:
                            if review.get("invalid_overlap"):
                                raise ValueError("Overlapping leveling ranking approvals")
                            unavailable = review.get("disposition") == "no_eligible_item"
                            support = check_evidence_refs(review, records)
                            if (not unavailable and not any(snapshots[record["source_url"]].get("page_type") == "guide"
                                                            for record in support)):
                                raise ValueError("Leveling ranking needs supporting guide evidence")
                            if (not ready or not has_review(review) or review.get("candidate_digest") != signature
                                    or review.get("profile_version") != profiles["version"] or review.get("rules_version") != rules["version"]):
                                raise ValueError("Stale leveling ranking approval")
                            wanted = review.get("item_ids")
                            choices = review.get("choices")
                            if unavailable:
                                if (selected or eligible or (wanted != [] and choices != []) or not availability_check
                                        or not availability_check["complete"] or availability_check["unresolved_item_ids"]
                                        or availability_check["review_issues"]):
                                    raise ValueError("No-item disposition needs exhaustive eligibility evidence: a complete inventory and supported exclusions")
                                if review.get("availability_digest") != availability_check["availability_digest"]:
                                    raise ValueError("Stale empty-slot availability approval")
                                if (not isinstance(review.get("display_reason"), str)
                                        or not review["display_reason"].strip() or len(review["display_reason"]) > 180):
                                    raise ValueError("Empty-slot approval needs a concise player explanation")
                                wanted_keys = []
                            elif choices is not None:
                                if not isinstance(choices, list) or not choices or any(not isinstance(choice, dict) for choice in choices):
                                    raise ValueError("Invalid variant-aware ranking choices")
                                if any(type(choice.get("item_id")) is not int or choice["item_id"] <= 0
                                       or (choice.get("variant_id") is not None and not isinstance(choice["variant_id"], str)) for choice in choices):
                                    raise ValueError("Invalid item or variant identity in ranking choices")
                                wanted_keys = [(choice.get("item_id"), choice.get("variant_id")) for choice in choices]
                            else:
                                if not isinstance(wanted, list) or not wanted or any(type(identifier) is not int or identifier <= 0 for identifier in wanted) or any(r.get("variant_id") for r in selected if r["item_id"] in wanted):
                                    raise ValueError("Suffix recommendations require variant-aware ranking choices")
                                wanted_keys = [(identifier, None) for identifier in wanted]
                            chosen = {(r["item_id"], r.get("variant_id")): r for r in selected}
                            if len(wanted_keys) != len(set(wanted_keys)) or set(wanted_keys) != set(chosen):
                                raise ValueError("Ranking approval does not match obtainable candidates")
                            if paired and not unavailable:
                                main_reviews = [r for key, r in approvals_by_context.get(
                                    (class_name,spec_name,"Main Hand",persona["faction"],persona["id"]), [])
                                    if type(key[5]) is int and type(key[6]) is int and key[5] <= level <= key[6]]
                                main_id = preferred_item_id(main_reviews[0]) if len(main_reviews) == 1 else None
                                if (review.get("paired_main_hand_digest") != pair_signature or main_id is None
                                        or review.get("paired_main_hand_item_id") != main_id):
                                    raise ValueError("Stale paired main-hand approval")
                            for rank, identity in enumerate(wanted_keys, 1):
                                row = deepcopy(chosen[identity])
                                row.update(level_min=level, level_max=end - 1, rank=rank, faction=persona["faction"], race_id=persona["id"])
                                rows.append(row)
                            approved = True
                            status = "no_useful_item" if unavailable else "approved"
                            if unavailable:
                                availability_rows.append({**profile, "race": persona["name"], "race_id": persona["id"],
                                    "faction": persona["faction"], "slot": slot, "level_min": level, "level_max": end - 1,
                                    "state": "no_useful_item", "reason": review["display_reason"]})
                        except (KeyError, TypeError, ValueError) as exc:
                            if not diagnostic:
                                raise
                            status = "stale_review"
                            issues.append({"class": class_name, "spec": spec_name, "slot": slot, "reason": str(exc)})
                    cell = {**profile, "faction": persona["faction"], "race": persona["name"], "race_id": persona["id"],
                            "slot": slot, "level_min": level, "level_max": end - 1, "candidate_digest": signature,
                            "candidate_item_ids": sorted({r["item_id"] for r in selected}),
                            "candidate_choices": [{"item_id":r["item_id"], "variant_id":r.get("variant_id")} for r in selected],
                            "candidate_scores": [{"item_id":r["item_id"], "variant_id":r.get("variant_id"),"score":r["score"]} for r in selected],
                            "eligible_candidate_count": len(eligible),
                            **({"paired_candidate_digest":pair_signature,"paired_main_hand_item_id":pair_main_id} if paired else {}),
                            "status": status, "statuses": [] if approved else [status]}
                    if availability_check:
                        cell["availability"] = availability_check
                    audit.append(cell)
                    if not approved:
                        gaps.append(cell)
    if set(approvals) - used:
        message = "Leveling ranking approval refers to an unsupported persona, slot, or level"
        if not diagnostic:
            raise ValueError(message)
        issues.append({"reason": message, "kind": "ranking"})
    gap_counts = Counter()
    for row in gaps:
        gap_counts[row["status"]] += row["level_max"] - row["level_min"] + 1
    summary = {"profiles": len(profiles.get("spec_roles", {})), "approved_items": len(items), "provisional_items": len(provisional_items),
               "excluded_items": sum(item.get("recommendation_excluded") is True for item in stats.values()),
               "recommendations": len(rows), "uncovered_combinations": sum(gap_counts.values()), "reviewed_rules": ready,
               "status_counts": dict(gap_counts), "review_issues": len(issues),
               "pending_ranking_combinations": gap_counts["pending_ranking_review"],
               "availability_review_combinations": sum(gap_counts[status] for status in AVAILABILITY_REVIEW_STATUSES),
               "availability_review_ranges": availability_review_ranges(audit),
               "approved_empty_combinations": sum(row["level_max"] - row["level_min"] + 1 for row in availability_rows)}
    target_ranges = availability_doc.get("target_ranges", [
        {"slot": slot, "level_min": 1, "level_max": 59} for slot in sorted(availability.INVENTORY_SLOTS)])
    inventory_complete = bool(target_ranges) and all(
        row.get("slot") in availability.INVENTORY_SLOTS and type(row.get("level_min")) is int
        and type(row.get("level_max")) is int and 1 <= row["level_min"] <= row["level_max"] <= 59
        and availability.complete_for(inventory, row["slot"], row["level_min"], row["level_max"])
        for row in target_ranges)
    summary.update(availability_candidates=inventory["candidate_count"], availability_inventory_complete=inventory_complete,
                   approved_empty_intervals=len(availability_rows))
    reviewed_exclusions = {**excluded_items, **{row["item_id"]:row for row in availability_doc.get("decisions", [])
                                               if row.get("exclusion") in {"not_useful", "non_gearing_effect"}}}
    inventory.pop("effective_decisions", None)
    inventory["candidate_reviews"] = availability.candidate_backlog(inventory, gaps, snapshots, items, reviewed_exclusions, leads,
                                                                 availability_doc.get("pending_facts"))
    inventory["review_status_counts"] = dict(Counter(row["status"] for row in inventory["candidate_reviews"]))
    summary["availability_pending_candidates"] = sum(count for status,count in inventory["review_status_counts"].items()
                                                    if status.startswith(("pending_","missing_")))
    return {"items": items, "item_stats": stats,
            "leveling_gear": {"leveling_gear": guide_gear(rows, snapshots, dataset_json("forever", "scrape_manifest"))},
            "leveling_recommendations": {"leveling_recommendations": compact_adjacent_recommendation_ranges(rows)},
            "leveling_availability": {"leveling_availability": compact_adjacent_recommendation_ranges(availability_rows)},
            "leveling_candidate_audit": inventory,
            "leveling_audit": {"summary": summary, "rows": compact_adjacent_recommendation_ranges(audit),
                               "review_issues": issues, "provisional_items": provisional_items},
            "coverage": {"ok": bool(audit) and ready and not gaps and not issues and not errors,
                         "summary": summary, "errors": errors, "rows": compact_adjacent_recommendation_ranges(gaps),
                         "review_issues": issues, "provisional_items": provisional_items,
                         "inventory_summary": {key:inventory[key] for key in ("version", "inventory_digest", "candidate_count",
                                                                            "source_issues", "decision_issues", "review_status_counts")}}}


def documents(snapshots: dict) -> dict:
    result = generate(snapshots)
    return {"leveling_items": {"items": [result["items"][key] for key in sorted(result["items"])]},
            "leveling_item_stats": {"item_stats": [result["item_stats"][key] for key in sorted(result["item_stats"])]},
            **{name: result[name] for name in ("leveling_gear", "leveling_recommendations", "leveling_audit",
                                             "leveling_availability", "leveling_candidate_audit")}}
