"""Build the item facts and reference profiles used by Forever stat ranks."""
from __future__ import annotations

import re

from tools.forever import item_observations, numeric, scoring_profiles, snapshot_digest, valid_source
from tools.forever_equipment_sources import publication_key
from tools.forever_effect_benchmarks import compile_rule, missing_reason, preset
from tools.forever_item_effects import (FLAT_PASSIVE_STATS, attach_rules, effect_lines, recover_permanent_stats,
                                       resolve_spell_leads, set_catalog, tooltip_sets, unresolved_lines)
from tools.project import FOREVER_CANONICAL_DIR, SLOT_NAMES, dataset_json, load_json
from tools.recommend_leveling import materialized_items, merged_stats, normalized_slot, profile_weights, separate_weapon_dps
from tools.sources import summarize_sources
from tools.forever_stats import normalized_stats, weight_review
from tools.forever_compatibility import supported_builds, target_class_restrictions


VERSION = "forever-stat-ranks-1"
ARMOR_SLOTS = {"Head", "Shoulder", "Chest", "Wrist", "Hands", "Waist", "Legs", "Feet"}
WEAPON_SLOTS = {"One Hand", "Main Hand", "Off Hand", "Two Hand", "Ranged"}
RANKED_SLOTS = (SLOT_NAMES | {"One Hand"}) - {"Dual Wield", "Ammo", "Quiver"}
ITEM_FIELDS = (
    "id", "name", "slot", "level", "stats", "armor_type", "weapon_subtype",
    "classes", "races", "max_equipped", "unique_group", "effects", "utility",
    "variant_id", "has_random_stats", "requires_dual_wield", "excluded", "effect_rules", "set_bonuses",
    "quality", "stats_unavailable", "roll_group", "roll_budget", "roll_armor", "roll_complete", "race_ids",
    "unreadable_effects", "missing_effects", "set_key",
)
TOOLTIP_CONFIDENCE = {"tooltip", "tooltip_endpoint", "observed_tooltip"}
WEAPON_STATS = {"dps", "ranged_dps", "wand_dps", "weapon_min_damage", "weapon_max_damage", "weapon_speed"}
DPS_STATS = {"dps", "ranged_dps", "wand_dps"}
DPS_TOLERANCE = 0.15

def normalized_item_stats(item: dict) -> dict:
    stats = normalized_stats(merged_stats(item))
    recover_permanent_stats(stats, effect_lines(item))
    stats.pop("socket", None)
    separate_weapon_dps(item, stats)
    if numeric(item.get("weapon_speed")) and item["weapon_speed"] > 0:
        stats["weapon_speed"] = item["weapon_speed"]
    low, high = item.get("weapon_min_damage"), item.get("weapon_max_damage")
    if numeric(low) and numeric(high) and 0 <= low <= high:
        stats["weapon_min_damage"], stats["weapon_max_damage"] = low, high
    return stats


def reviewed_guide_items(reviewed: list[dict]) -> tuple[list[dict], list[dict]]:
    items, stats = [], []
    for row in reviewed:
        review, sources = row.get("review", {}), row.get("sources", [])
        if (not comparison_facts(row) or not re.fullmatch(r"1\.60\.\d+\.\d+", review.get("client_build", ""))
                or not review.get("tooltip_url", "").startswith("https://")
                or not review.get("route_url", "").startswith("https://")
                or not sources or not all(map(valid_source, sources))):
            raise ValueError(f"Invalid Forever guide item review for {row.get('id')}")
        item = {key: row[key] for key in ("id", "name", "quality", "binding", "boe", "wowhead_url")}
        source = sources[0]
        item.update(inventory_slot=row["slot"], acquisition_phase="PR", primary_source=source,
                    sources=sources, source_summary=summarize_sources(sources))
        items.append(item)
        stats.append({key: value for key, value in row.items() if key != "review"})
    return items, stats


def reviewed_source_items(review: dict, inventory: dict) -> list[dict]:
    equipment = {row[0]: dict(zip(inventory["fields"], row)) for row in inventory["items"]}
    by_item, bindings = {}, {}
    for route in review["routes"]:
        source = {**route["source"], "attribution": route.get("attribution", review["attribution"])}
        if not valid_source(source) or not route["corroboration_url"].startswith("https://"):
            raise ValueError(f"Invalid Forever acquisition review: {route}")
        for identifier in route["item_ids"]:
            if identifier not in equipment or source in by_item.get(identifier, []):
                raise ValueError(f"Invalid Forever route for item {identifier}")
            by_item.setdefault(identifier, []).append(source)
            binding = route.get("binding", review["binding"])
            if bindings.setdefault(identifier, binding) != binding:
                raise ValueError(f"Conflicting Forever binding for item {identifier}")
    return [{"id": identifier, "name": equipment[identifier]["name"], "quality": equipment[identifier]["quality"],
             "inventory_slot": equipment[identifier]["slot"], "binding": bindings[identifier],
             "boe": bindings[identifier] == "bind_on_equip",
             "wowhead_url": f"https://www.wowhead.com/forever/item={identifier}", "acquisition_phase": "PR",
             "primary_source": sources[0], "sources": sources, "source_summary": summarize_sources(sources)}
            for identifier, sources in sorted(by_item.items())]


def comparison_facts(item: dict, description: str = "", *, allow_empty: bool = False) -> dict | None:
    slot = normalized_slot(item.get("slot"))
    identifier, name = item.get("id"), item.get("name")
    if slot not in RANKED_SLOTS or type(identifier) is not int or identifier <= 0 or not name:
        return None
    level = item.get("required_level")
    if level is not None and (type(level) is not int or not 0 <= level <= 60):
        return None
    if slot in ARMOR_SLOTS and not item.get("armor_type"):
        return None
    weapon = item.get("weapon_subtype") if slot in WEAPON_SLOTS else None
    if slot in WEAPON_SLOTS - {"Off Hand"} and not weapon:
        return None
    if not isinstance(item.get("stats", {}), dict) or not all(map(numeric, item.get("stats", {}).values())):
        return None
    if any(item.get(field) is not None and not numeric(item[field]) for field in ("armor", "dps", "weapon_speed")):
        return None

    stats = normalized_item_stats(item)
    if not weapon:
        # Set member names and damage text can contain a weapon subtype even
        # when the tooltip's own item is a ring, cloak, or trinket.
        stats = {key: value for key, value in stats.items() if key not in WEAPON_STATS}
    if not all(map(numeric, stats.values())):
        return None
    effects = unresolved_lines(item)
    if not stats and not effects and not allow_empty:
        return None
    utility = not stats and bool(effects) and all(
        re.fullmatch(r"(?:Equip:\s*)?Increases mount speed by \d+%\.?", effect, re.IGNORECASE) for effect in effects
    )

    facts = {"id": identifier, "name": name, "slot": slot, "stats": stats}
    if level is not None:
        facts["level"] = level
    if effects:
        facts["effects"] = effects
    if utility:
        facts["utility"] = True
    if item.get("recommendation_excluded"):
        facts["excluded"] = True
    if weapon:
        facts["weapon_subtype"] = weapon
    for key in ("armor_type", "max_equipped", "unique_group", "variant_id", "requires_dual_wield", "variant_link", "quality"):
        if item.get(key) is not None:
            facts[key] = item[key]
    for key in ("classes", "races"):
        if item.get("restrictions", {}).get(key):
            facts[key] = sorted(set(item["restrictions"][key]))

    unique = re.search(r"\bUnique[- ]Equipped\s*:\s*([^()\r\n<]+?)\s*\((\d+)\)", description, re.IGNORECASE)
    if unique:
        facts.setdefault("unique_group", unique[1].strip())
        facts.setdefault("max_equipped", int(unique[2]))
    elif re.search(r"\bUnique(?:[- ]Equipped)?\b", description, re.IGNORECASE):
        facts.setdefault("max_equipped", 1)
    if item.get("variant_only") or re.search(r"\bRandom Enchantment\b", description, re.IGNORECASE):
        facts["has_random_stats"] = True
    return facts


def equipment_rows(catalog: dict) -> dict[int, dict]:
    return {row[0]: dict(zip(catalog["fields"], row)) for row in catalog["items"]}


def weapon_facts_agree(first: dict, second: dict) -> bool:
    return all(abs(first[key] - second[key]) <= (DPS_TOLERANCE if key in DPS_STATS else 0.01)
               for key in WEAPON_STATS & first.keys() & second.keys())


def merge_comparison_facts(preferred: dict, fallback: dict, *, preserve_observed: bool = False) -> dict:
    """Keep the stronger fields and supplement compatible, incomplete rows."""
    identity = ("slot", "armor_type", "weapon_subtype")
    if any(preferred.get(key) and fallback.get(key) and preferred[key] != fallback[key] for key in identity):
        return preferred
    merged = {**fallback, **preferred}
    leading, secondary = preferred["stats"], fallback["stats"]
    supplemental = {}
    if "armor" in secondary:
        supplemental["armor"] = secondary["armor"]
    if weapon_facts_agree(leading, secondary):
        supplemental.update({key: value for key, value in secondary.items() if key in WEAPON_STATS})
    if preserve_observed or not preferred.get("attributes_known"):
        supplemental.update({key: value for key, value in secondary.items() if key not in WEAPON_STATS | {"armor"}})
    merged["stats"] = {**supplemental, **leading}
    if fallback.get("armor_base") is not None and leading.get("armor") == fallback["armor_base"]:
        merged["stats"]["armor"] = secondary["armor"]
    if preferred.get("effects_known"):
        primary = preferred.get("effects", [])
        merged["effects"] = list(dict.fromkeys([*primary, *fallback.get("effects", [])])) if preserve_observed else primary
    return merged


def verified_tooltip_armor(facts: dict, description: str) -> None:
    """Recover the total from older snapshots that parsed the base armor only."""
    if "armor" not in facts["stats"] or "+" not in description:
        return
    intrinsic = re.split(r"\b(?:Equip:|Use:|Chance on hit:|Sell Price:|Dropped by:)", description, maxsplit=1)[0]
    base = re.findall(r"(?<![\w+\-])(\d+) Armor\b", intrinsic)
    bonuses = re.findall(r"\+(\d+) Armor\b", intrinsic)
    if len(base) == 1 and bonuses and int(base[0]) == facts["stats"]["armor"]:
        facts["armor_base"] = int(base[0])
        facts["stats"]["armor"] += sum(map(int, bonuses))


def conflicting_fields(first: dict, second: dict) -> list[str]:
    fields = []
    primary, other = first["stats"], second["stats"]
    if not weapon_facts_agree(primary, other):
        fields.append("weapon")
    if "armor" in primary.keys() & other.keys() and primary["armor"] != other["armor"]:
        fields.append("armor")
    if any(primary[key] != other[key] for key in (primary.keys() & other.keys()) - WEAPON_STATS - {"armor"}):
        fields.append("attributes")
    if "level" in first.keys() & second.keys() and max(1, first["level"]) != max(1, second["level"]):
        fields.append("equip_level")
    if first["slot"] != second["slot"]:
        fields.append("slot")
    return fields


def comparison_document(snapshots: dict[str, dict], catalog: dict | None = None) -> dict:
    catalog = dataset_json("forever", "guide_equipment") if catalog is None else catalog
    build = catalog["client_build"]
    reviewed = dataset_json("forever", "leveling_rules")["review"]["client_build"]
    target = load_json(FOREVER_CANONICAL_DIR / "reviewed_builds.json")["target_client"]
    inventory = equipment_rows(catalog)
    observations = item_observations(snapshots)
    candidates, scans = {}, {}
    digests = {}

    def add(item, url, priority, *, description="", tooltip=False, embedded=False):
        identifier = item.get("id")
        base = inventory.get(identifier, {})
        if not item.get("name"):
            return
        if base.get("slot") == normalized_slot(item.get("slot")):
            item = {**{k: base[k] for k in ("weapon_subtype", "armor_type") if base.get(k)}, **item}
        facts = comparison_facts(item, description, allow_empty=True)
        if facts is None:
            return
        if tooltip:
            verified_tooltip_armor(facts, description)
        source = snapshots[url]
        if url not in digests:
            digests[url] = snapshot_digest(source)
        if priority > 0 and not item.get("unparsed_attributes"):
            facts["attributes_known"] = True
        if tooltip or (priority > 0 and not item.get("effect_leads")):
            facts["effects_known"] = True
        elif item.get("effect_leads"):
            facts["effect_leads"] = item["effect_leads"]
        if source.get("client_build") != build and facts.get("level") == 0:
            facts.pop("level")
        order = (priority, not embedded, publication_key(source))
        candidates.setdefault(identifier, []).append((order, {**facts, "evidence": {"url": url, "digest": digests[url]}}))

    for identifier, rows in observations.items():
        for observed in rows:
            item = observed.get("item_stats", {})
            url = observed["evidence_url"]
            if (item.get("id") == identifier and observed.get("item_kind") == "equipment"
                    and item.get("parse_confidence") in TOOLTIP_CONFIDENCE
                    and (item["parse_confidence"] != "observed_tooltip" or snapshots[url].get("client_build") in {reviewed, build})):
                add(item, url, 2, description=observed.get("description") or "", tooltip=True, embedded=observed.get("embedded", False))

    for url, source in sorted(snapshots.items()):
        if source.get("page_type") != "equipment_facts":
            continue
        if source.get("provider") == "libitemdb":
            for item in source["items"]:
                scans.setdefault(item["id"], []).append((url, item))
            continue
        tooltip = source.get("confidence") == "forever_tooltip"
        source_build = source.get("client_build")
        if tooltip and source_build not in {None, build, target} or not tooltip and source_build != build:
            continue
        priority = 3 if tooltip else 0 if source.get("confidence") == "client_armor_tables" else 1
        for item in source["items"]:
            add(item, url, priority, description=item.get("description", ""), tooltip=tooltip)

    rows, conflicts = [], []
    for identifier, choices in sorted(candidates.items()):
        ordered = sorted(choices, key=lambda choice: choice[0], reverse=True)
        (priority, best), *others = ordered
        disputed_attributes = set()
        for other_priority, alternative in others:
            differences = conflicting_fields(best, alternative)
            for field in differences:
                conflicts.append({"id": identifier, "field": field,
                                  "sources": sorted({best["evidence"]["url"], alternative["evidence"]["url"]}),
                                  "needs_tooltip": priority[0] < 3})
            if "attributes" in differences and priority[0] == 2 and priority[:2] == other_priority[:2]:
                primary, secondary = best["stats"], alternative["stats"]
                disputed_attributes.update(key for key in (primary.keys() & secondary.keys()) - WEAPON_STATS - {"armor"}
                                           if primary[key] != secondary[key])
            combined = merge_comparison_facts(best, alternative, preserve_observed=priority[0] >= 2 and other_priority[0] >= 2)
            if combined != best:
                url = alternative["evidence"]["url"]
                urls = set(best.get("supporting_sources", ())) | {url}
                fields = {key: url for key in combined["stats"].keys() - best["stats"].keys()}
                if "level" in combined and "level" not in best:
                    fields["equip_level"] = url
                best = {**combined, "supporting_sources": sorted(urls), **({"field_sources": {**best.get("field_sources", {}), **fields}}
                                                                         if fields else {})}
        for url, scan in scans.get(identifier, ()):
            if scan["slot"] != best["slot"]:
                continue
            stats = dict(scan["stats"])
            if "dps" in stats:
                separate_weapon_dps(best, stats)
            field_sources = best.get("field_sources", {})
            weapon_sources = {key: field_sources.get(key, best["evidence"]["url"])
                              for key in WEAPON_STATS & best["stats"].keys()}
            bulk_fields = {key for key, source in weapon_sources.items()
                           if snapshots[source].get("provider") == "wowsims_gamedata"}
            shared = bulk_fields & stats.keys()
            if not shared:
                continue
            if not weapon_facts_agree({key: best["stats"][key] for key in shared}, stats):
                conflicts.append({"id": identifier, "field": "weapon", "sources": sorted({url, *(weapon_sources[key] for key in shared)}),
                                  "needs_tooltip": True})
                best = {**best, "stats": {key: value for key, value in best["stats"].items() if key not in bulk_fields}}
            elif snapshots[url].get("client_build") == build:
                best = {**best, "stats": {**stats, **best["stats"]},
                        "supporting_sources": sorted(set(best.get("supporting_sources", ())) | {url})}
        if disputed_attributes:
            best = {**best, "attributes_known": False,
                    "stats": {key: value for key, value in best["stats"].items() if key not in disputed_attributes}}
        rows.append(best)
    restrictions = target_class_restrictions()
    for item in rows:
        if str(item["id"]) in restrictions:
            item["classes"] = restrictions[str(item["id"])]
    effect_sets = tooltip_sets(observations, rows)
    return {"version": VERSION, "items": rows, "conflicts": conflicts, **({"effect_sets": effect_sets} if effect_sets else {})}


def compile_comparison_data(item_stats: list[dict], *, data: dict | None = None, catalog: dict | None = None) -> dict:
    data = dataset_json("forever", "comparison_item_stats") if data is None else data
    if data["version"] != VERSION:
        raise ValueError("Unexpected Forever comparison catalog version")
    items = {}
    definitions, set_members = set_catalog(data)
    for item in resolve_spell_leads(data["items"], set_members).values():
        facts = {**item, "stats": normalized_stats(item["stats"])}
        recover_permanent_stats(facts["stats"], effect_lines(item))
        if "effects" in facts:
            facts["effects"] = unresolved_lines(item)
        items[str(item["id"])] = facts
    variants = dataset_json("forever", "item_variants")["item_variants"]
    for item in materialized_items(item_stats, variants):
        facts = comparison_facts(item, allow_empty=True)
        key = item.get("variant_id") or str(item["id"])
        if facts:
            inherited = items.get(str(item["id"]), {})
            if not item.get("variant_id") and inherited:
                facts = merge_comparison_facts(facts, inherited)
            if item.get("variant_id"):
                facts.pop("has_random_stats", None)
            if item.get("set_bonuses"):
                facts["set_bonuses"] = [{"pieces": bonus["pieces"], "spell_id": bonus.get("spell_id")}
                                        for bonus in item["set_bonuses"]]
            items[key] = facts

    rules = dataset_json("forever", "leveling_rules")
    profiles = reference_profiles(rules)
    guide_effects, seen_reviews = {}, set()
    known_roles = {profile["role"] for profile in profiles.values()}
    for review in dataset_json("forever", "leveling_guide_effects")["effects"]:
        key = review["variant"]
        roles, specs = review.get("roles", []), review.get("specs", [])
        if (key in seen_reviews or not (roles or specs) or set(roles) - known_roles or set(specs) - profiles.keys()
                or not review["note"].strip()):
            raise ValueError(f"Invalid Forever Gear Guide effect review for {key}")
        seen_reviews.add(key)
        if key not in items:
            continue
        if review["effect"] not in items[key].get("effects", []):
            raise ValueError(f"Forever Gear Guide effect changed for {key}")
        guide_effects[key] = {field: review[field] for field in ("roles", "specs", "note") if field in review}
    gaps = {}
    reviewed = dataset_json("forever", "spell_effect_review")
    if reviewed["build"] != load_json(FOREVER_CANONICAL_DIR / "reviewed_builds.json")["target_client"]:
        raise ValueError("Forever spell effect evidence must be reviewed for the target client")
    for key, item in items.items():
        if set_key := set_members.get(item["id"]):
            item["set_key"] = set_key
            if "Set bonuses" not in item.setdefault("effects", []):
                item["effects"].append("Set bonuses")
        items[key] = item | attach_rules(item)
        item = items[key]
        for lead in item.get("effect_leads", []):
            mechanic = reviewed["rules"].get(lead)
            if not mechanic or item["id"] not in reviewed["references"][lead]["items"]:
                continue
            trigger = lead.partition(":")[0].casefold() + ":"
            # A single exact spell link owns the description for this trigger.
            # Leave other triggers and items alone, including copies with different spells.
            if sum(link.casefold().startswith(trigger) for link in item["effect_leads"]) != 1:
                continue
            item["effects"] = [label for label in item.get("effects", []) if not label.casefold().startswith(trigger)]
            item["effects"].append(mechanic["label"])
            item_rules = [rule for rule in item.get("effect_rules", []) if not rule["label"].casefold().startswith(trigger)]
            item_rules.append(compile_rule({k: v for k, v in mechanic.items() if k not in {"source", "rate_source", "rate_sample"}}, item))
            item["effect_rules"] = item_rules
            item["missing_effects"] = [other for other in item.get("missing_effects", []) if other != lead]
            item["effects_known"] = not item["missing_effects"]
        rules_by_label = {label: rule for rule in items[key].get("effect_rules", [])
                          for label in (rule["label"], *rule.get("aliases", []))}
        for label in item.get("effects", []):
            rule = rules_by_label.get(label)
            if rule and rule["kind"] == "situational":
                gaps[label] = "Situational benefit outside the ordinary encounter"
            elif not rule or (not rule.get("rates") and rule["kind"] != "passive_stats"):
                gaps[label] = rule.get("gap", "Missing eligible activation rate or resource use") if rule else missing_reason(label)
    catalog = dataset_json("forever", "guide_equipment") if catalog is None else catalog
    for base in equipment_rows(catalog).values():
        key = str(base["id"])
        item = items.setdefault(key, {})
        if not item and base["id"] in set_members:
            item.update(set_key=set_members[base["id"]], effects=["Set bonuses"], stats_unavailable=True)
        for field in ("id", "name", "slot", "armor_type", "weapon_subtype", "classes", "race_ids", "quality"):
            if base.get(field) is not None and (field != "weapon_subtype" or base["slot"] in WEAPON_SLOTS):
                item.setdefault(field, base[field])
        # Older Guide catalog rows use 1 for both an explicit zero and an
        # unknown requirement. A sourced level resolves that ambiguity.
        if (base.get("level") or 0) > 1:
            item.setdefault("level", base["level"])
        if base.get("group"):
            item["has_random_stats"] = True
            item.update(roll_group=base["group"], roll_budget=base.get("budget"),
                        roll_armor=base.get("armor"), roll_complete=base.get("roll_complete"))
    variant_links = {key: item["variant_link"] for key, item in items.items() if item.get("variant_link")}
    guide_reviews = dataset_json("forever", "guide_item_reviews")
    excluded = {identifier for review in guide_reviews.get("exclusions", []) for identifier in review["item_ids"]}
    packed = {}
    by_slot = {}
    for key, item in items.items():
        if item["id"] in excluded:
            item["excluded"] = True
        stats = item.get("stats", {})
        if (not stats and not item.get("effects") and not item.get("attributes_known")) or (
            item.get("weapon_subtype") and not DPS_STATS.intersection(stats)
        ):
            item["stats_unavailable"] = True
        if item.get("effect_leads") and not item.get("effects_known"):
            item["unreadable_effects"] = True
        row = [item.get(field) for field in ITEM_FIELDS]
        while row[-1] is None:
            row.pop()
        packed[key] = row
        by_slot.setdefault(item["slot"], []).append(key)
    return {
        "version": VERSION,
        "roll_build": int(catalog["client_build"].split(".")[-1]),
        "roll_builds": supported_builds(catalog=catalog),
        "roll_templates": catalog["templates"],
        "roll_groups": catalog["groups"],
        "flat_passive_stats": [list(rule) for rule in FLAT_PASSIVE_STATS],
        "profiles": profiles,
        "guide_effects": guide_effects,
        "effect_gaps": gaps,
        "effect_sets": definitions,
        "equipment": rules["class_equipment"],
        "common_slots": rules["common_slots"],
        "feral_uses_weapon_dps": rules["feral_uses_weapon_dps"],
        "item_fields": list(ITEM_FIELDS),
        **({"variant_links": variant_links} if variant_links else {}),
        "items": packed,
        "slot_keys": {slot: sorted(keys) for slot, keys in by_slot.items()},
    }


def reference_profiles(rules: dict, *, leveling: dict | None = None, model: dict | None = None) -> dict:
    leveling = leveling or dataset_json("forever", "leveling_scoring_profiles")
    raid = scoring_profiles()
    model = model or dataset_json("forever", "scoring_model")
    profiles = {}
    calibration = weight_review()["profiles"]
    for profile in raid["profiles"]:
        class_name, spec = profile["class"], profile["spec"]
        key = f"{class_name}/{spec}"
        settings = model["profiles"][key]
        common = settings.get("weights", {})
        scenarios = settings.get("scenario_overrides", {})
        weights = [
            [low, high, {**profile_weights(leveling, class_name, spec, low, "best_overall", rules=rules)[1],
                         **common, **scenarios.get("leveling", {}).get("weights", {})}]
            for _, low, high in rules["level_bands"]
        ]
        raid_weights = {**raid["role_weights"][profile["role"]], **profile.get("weights", {}), **common,
                        **scenarios.get("pre_raid", {}).get("weights", {})}
        raid_weights.update(calibration[key]["weights"])
        if key == "Druid/Feral tank":
            raid_weights["parry_percent"] = 0
        for mode, bands in (("leveling", weights), ("pre_raid", [(60, 60, raid_weights)])):
            benchmark = preset(profile["role"], mode)
            for _, _, values in bands:
                for channel in ("proc_dps", "proc_hps"):
                    values[channel] = benchmark[channel]
        profiles[key] = {
            "role": profile["role"],
            "leveling": {**rules["spec_policies"][key], "weights": weights},
            "pre_raid": {
                **{field: profile[field] for field in (
                    "slots", "armor_types", "weapon_types", "two_hand_weapon_types",
                    "dual_wield", "require_shield", "slot_weapon_types",
                ) if field in profile},
                "weights": raid_weights,
            },
        }
    return profiles
