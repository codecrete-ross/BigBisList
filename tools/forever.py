"""Offline Forever intake, recommendation scoring, and coverage checks."""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import date
from collections import Counter
from collections import defaultdict
from copy import deepcopy
from pathlib import Path

from tools.project import ROOT, FOREVER_CANONICAL_DIR, FOREVER_RAW_DIR, SLOT_NAMES, dataset_json, load_json, write_text
from tools.recommend_leveling import separate_weapon_dps
from tools.sources import summarize_sources
from tools.forever_sources import check_evidence_refs, evidence_index, evidence_ref, provider_snapshots, route_leads, source_provider


WOWHEAD_ROOT = "https://www.wowhead.com/forever/"
PRE_RAID = "PR"
FACTIONS = ("Alliance", "Horde")
LIVE_ACCEPTANCE_CHECKS = ("login_reload", "spec_selection", "equipment_bags", "comparisons", "tooltips",
                          "wishlist_persistence", "quest_progress", "waypoints", "combat", "existing_waypoint", "no_coordinates")
CLASSES = {"Druid", "Hunter", "Mage", "Paladin", "Priest", "Rogue", "Shaman", "Warlock", "Warrior"}
SOURCE_CHILDREN = ("recipe_sources", "quest_starter_sources", "token_sources")
ROUTE_TYPES = {
    "crafted", "drop", "pvp", "quest", "taught_by_item", "token_turnin", "trade", "trainer", "vendor", "world_drop",
}


def is_forever_url(url: object) -> bool:
    return isinstance(url, str) and url.startswith(WOWHEAD_ROOT)


def has_review(row: dict) -> bool:
    url = row.get("source_url")
    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", row.get("reviewed_at", "")):
            return False
        date.fromisoformat(row["reviewed_at"])
    except (TypeError, ValueError):
        return False
    return all(isinstance(row.get(key), str) and row[key].strip() for key in ("reviewer", "reviewed_at", "reason")) and (
        isinstance(url, str) and (url.startswith("https://") or source_provider(url) == "local_capture")
        and not re.match(r"https://(?:www\.)?wowhead\.com/(?:tbc|classic|wotlk|classic-ptr)/", url)
        and isinstance(row.get("client_build"), str) and re.fullmatch(r"1\.60\.\d+\.\d+", row["client_build"]) is not None
    )


def numeric(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def snapshot_digest(snapshot: dict) -> str:
    return digest({key: value for key, value in snapshot.items() if key != "fetched_at"})


def valid_destination(destination: dict) -> bool:
    return (
        isinstance(destination, dict)
        and type(destination.get("map_id")) is int and destination["map_id"] > 0
        and all(numeric(destination.get(axis)) and 0 <= destination[axis] <= 1 for axis in ("x", "y"))
        and destination.get("kind") in {"quest_start", "quest_end", "objective", "vendor", "trainer", "entrance", "spawn"}
        and type(destination.get("entity_id")) is int and destination["entity_id"] > 0
        and has_review(destination)
    )


def valid_quest_endpoint(endpoint: dict) -> bool:
    if not isinstance(endpoint, dict):
        return False
    if any(key in endpoint for key in ("map_id", "x", "y")):
        return valid_destination(endpoint)
    return (isinstance(endpoint.get("name"), str) and bool(endpoint["name"].strip())
            and type(endpoint.get("entity_id")) is int and endpoint["entity_id"] > 0
            and endpoint.get("kind") in {"quest_start", "quest_end"} and has_review(endpoint))


def valid_route_eligibility(rule: object) -> bool:
    if not isinstance(rule, dict) or type(rule.get("min_level")) is not int or not 1 <= rule["min_level"] <= 60:
        return False
    maximum = rule.get("max_level", 60)
    return (type(maximum) is int and rule["min_level"] <= maximum <= 60
            and rule.get("side", "Both") in ("Both", *FACTIONS)
            and all(isinstance(rule.get(key, []), list)
                    and all(isinstance(value, str) and value for value in rule.get(key, []))
                    for key in ("races", "classes")))


def valid_source(source: dict) -> bool:
    if (
        not isinstance(source, dict)
        or source.get("type") not in ROUTE_TYPES
        or source.get("content_type") == "raid"
        or (source.get("type") == "drop" and source.get("content_type") not in {"dungeon", "heroic_dungeon", "other"})
        or source.get("available_from_phase", PRE_RAID) != PRE_RAID
        or source.get("available_until_phase") == PRE_RAID
        or source.get("side") not in ("Both", *FACTIONS)
        or ("eligibility" in source and not valid_route_eligibility(source["eligibility"]))
        or not (source.get("entity_name") or source.get("zone"))
    ):
        return False
    destination = source.get("destination")
    if destination is not None and not valid_destination(destination):
        return False
    steps = source.get("quest_steps", [])
    if not isinstance(steps, list):
        return False
    for step in steps:
        if (
            not isinstance(step, dict)
            or type(step.get("quest_id")) is not int or step["quest_id"] <= 0
            or not step.get("name")
            or step.get("kind") not in {"prerequisite", "alternative", "reward"}
            or not has_review(step)
            or any(key in step and not valid_quest_endpoint(step[key]) for key in ("start", "finish"))
        ):
            return False
    return all(isinstance(source.get(key, []), list) and all(map(valid_source, source.get(key, []))) for key in SOURCE_CHILDREN)


def source_usable_by(source: dict, faction: str, class_name: str | None = None) -> bool:
    rule = source.get("eligibility", {})
    return (source.get("side") in ("Both", faction)
            and rule.get("side", "Both") in ("Both", faction)
            and rule.get("min_level", 1) <= 60 <= rule.get("max_level", 60)
            and (not class_name or not rule.get("classes") or class_name in rule["classes"])
            and all(not source.get(key) or any(source_usable_by(child, faction, class_name) for child in source[key])
                    for key in SOURCE_CHILDREN))


def roster() -> set[tuple[str, str]]:
    return {
        (row["name"], spec["name"])
        for row in dataset_json("forever", "classes")["classes"]
        for spec in row["specs"]
    }


def scoring_profiles() -> dict:
    document = dataset_json("forever", "scoring_profiles")
    for profile in document["profiles"]:
        equipment = document["class_equipment"][profile["class"]]
        profile["armor_types"] = equipment["armor_types"]
        profile["weapon_types"] = equipment["weapon_types"]
        profile["two_hand_weapon_types"] = equipment.get("two_hand_weapon_types", [])
        profile["slots"] = document["common_slots"] + profile["weapon_slots"]
    return document


def registered_urls(family: str | None = None) -> set[str]:
    manifest = dataset_json("forever", "scrape_manifest")
    urls = {
        row["url"] for row in manifest["sources"]
        if not family or row.get("data_family") == family
    }
    if family in (None, "item_corpus"):
        urls.update(manifest.get("item_seeds", []))
    return urls


def read_snapshots(input_dir: Path) -> dict[str, dict]:
    if not input_dir.is_dir():
        raise ValueError(f"Forever snapshot directory does not exist: {input_dir}")
    snapshots = {}
    registered = registered_urls()
    for path in sorted(input_dir.glob("*.json")):
        snapshot = load_json(path)
        url = snapshot.get("url")
        if snapshot.get("flavor") != "forever" or not is_forever_url(url) or url not in registered:
            raise ValueError(f"Unregistered or cross-flavor snapshot: {path}")
        if url in snapshots:
            raise ValueError(f"Duplicate Forever snapshot for {url}")
        snapshots[url] = snapshot
    if input_dir.resolve() == FOREVER_RAW_DIR.resolve():
        external = provider_snapshots(registered)
        if snapshots.keys() & external.keys():
            raise ValueError("Duplicate Forever evidence across providers")
        snapshots.update(external)
    return snapshots


def load_verified_items(snapshots: dict[str, dict], overrides: list[dict], *, records: dict | None = None,
                        conflicts: dict | None = None) -> tuple[dict, dict]:
    items, stats = {}, {}
    records = evidence_index(snapshots) if records is None else records
    conflicts = item_conflicts(snapshots) if conflicts is None else conflicts
    for review in overrides:
        if review.get("type") != "verify_item":
            continue
        url = review.get("snapshot_url")
        snapshot = snapshots.get(url, {})
        observed = snapshot
        if snapshot.get("item_id") != review.get("item_id"):
            observed = next((row for row in snapshot.get("embedded_items", []) if row.get("item_id") == review.get("item_id")), {})
        item_id = observed.get("item_id")
        sources = deepcopy(review.get("sources"))
        parsed = observed.get("item_stats", {})
        if (
            not has_review(review) or not snapshot or snapshot.get("page_type") != "item"
            or review.get("snapshot_digest") != snapshot_digest(snapshot)
            or type(item_id) is not int or item_id <= 0 or item_id != review.get("item_id") or item_id in items
            or parsed.get("slot") not in SLOT_NAMES | {"One Hand"} or not observed.get("name")
            or not isinstance(sources, list) or not sources or not all(map(valid_source, sources))
            or parsed.get("parse_confidence") not in {"tooltip", "tooltip_endpoint", "observed_tooltip"}
            or (parsed.get("parse_confidence") == "observed_tooltip" and snapshot.get("client_build") != review["client_build"])
            or (parsed.get("required_level") is not None and (
                not numeric(parsed["required_level"]) or not 0 <= parsed["required_level"] <= 60
            ))
        ):
            raise ValueError(f"Invalid Forever item review for {url}")
        try:
            support = check_evidence_refs(review, records)
            if url not in {record["source_url"] for record in support}:
                raise ValueError("Item approval must reference its tooltip evidence")
            if item_id in conflicts and (
                not isinstance(review.get("conflict_resolution"), str) or not review["conflict_resolution"].strip()
                or not set(conflicts[item_id]).issubset({record["source_url"] for record in support})
            ):
                raise ValueError("Conflicting item observations require an explicit resolution and all supporting evidence")
            for source in sources:
                validate_route_review(source, records)
        except ValueError as exc:
            raise ValueError(f"Invalid Forever item review for {url}: {exc}") from exc
        sources = [{"confidence": "reviewed", "source_url": review["source_url"], **source} for source in sources]
        items[item_id] = {
            "id": item_id, "name": observed["name"], "inventory_slot": parsed["slot"],
            "quality": observed.get("quality") or "unknown", "binding": observed.get("binding") or "unknown", "boe": observed.get("boe"),
            "wowhead_url": parsed.get("wowhead_url") or observed.get("url", url), "acquisition_phase": PRE_RAID, "sources": sources,
            "primary_source": sources[0], "source_summary": summarize_sources(sources),
            "requirements": observed.get("normalized_requirements", []),
        }
        stats[item_id] = {**parsed, "id": item_id, "name": observed["name"], "wowhead_url": observed.get("url", url), "phase": PRE_RAID, "sources": sources, "primary_source": sources[0]}
        if (parsed.get("weapon_subtype") and parsed.get("slot") in {"One Hand","Main Hand","Off Hand"}
                and re.search(r"\bUnique(?:-Equipped)?\s+(?:(?:One|Two)[- ]Hand|Main Hand|Off[- ]Hand|Ranged)\b", observed.get("description") or "")):
            stats[item_id]["max_equipped"] = 1
    return items, stats


def item_observations(snapshots: dict[str, dict]) -> dict[int, list[dict]]:
    observations = defaultdict(list)
    for url, snapshot in sorted(snapshots.items()):
        if snapshot.get("page_type") == "item" and type(snapshot.get("item_id")) is int:
            observations[snapshot["item_id"]].append({**snapshot, "evidence_url": url})
        for member in snapshot.get("embedded_items", []):
            observations[member["item_id"]].append({**member, "evidence_url": url, "embedded": True})
    for rows in observations.values():
        rows.sort(key=lambda row: (bool(row.get("embedded")), row["evidence_url"]))
    return dict(observations)


def item_conflicts(snapshots: dict[str, dict]) -> dict[int, list[str]]:
    conflicts = {}
    fields = ("slot", "required_level", "item_level", "armor_type", "weapon_subtype", "weapon_speed", "dps", "armor", "stats", "restrictions")
    for identifier, rows in item_observations(snapshots).items():
        for field in fields:
            values = {digest(row["item_stats"][field]) for row in rows if row.get("item_stats", {}).get(field) is not None}
            if len(values) > 1:
                conflicts[identifier] = sorted({row["evidence_url"] for row in rows})
                break
    return conflicts


def validate_route_review(source: dict, records: dict) -> None:
    if not has_review(source):
        raise ValueError("Every acquisition route requires its own review")
    support = check_evidence_refs(source, records)
    if all(record.get("confidence") in {"catalog_metadata", "client_metadata_only", "provenance_review_only",
                                       "questiedb_raw_lead", "guide_lead"} for record in support):
        raise ValueError("Acquisition approval needs corroborating evidence, not only metadata or raw leads")
    if any(record.get("observed_build") and record["observed_build"] != source["client_build"] for record in support):
        raise ValueError("Route evidence is from another client build")
    if source["source_url"] not in {record["source_url"] for record in support}:
        raise ValueError("Route review URL is absent from its evidence references")
    identity = source.get("quest_id") if source["type"] == "quest" else (
        source.get("spell_id") if source["type"] in {"crafted", "trainer"} else (
            source.get("item_id") if source["type"] == "trade" else source.get("entity_id") or source.get("vendor_id"))
    )
    if source["type"] != "world_drop" and (type(identity) is not int or identity <= 0):
        raise ValueError("Acquisition route needs an exact quest, spell, or source ID")
    for child_key in SOURCE_CHILDREN:
        for child in source.get(child_key, []):
            validate_route_review(child, records)
    for detail in [source.get("destination"), *source.get("quest_steps", [])]:
        if detail is not None:
            check_evidence_refs(detail, records)
            for key in ("start", "finish"):
                if detail.get(key):
                    check_evidence_refs(detail[key], records)
    credits = []
    for record in support:
        for credit in record.get("attribution", []):
            if credit not in credits:
                credits.append(credit)
    if credits:
        source["attribution"] = credits


def profile_key(profile: dict) -> tuple[str, str]:
    return profile["class"], profile["spec"]


def eligible(item: dict, profile: dict, slot: str, *, require_source: bool = True) -> bool:
    restrictions = item.get("restrictions", {})
    item_slot = item["slot"]
    armor_type = item.get("armor_type")
    shield = armor_type == "Shield"
    matching_slot = item_slot == slot or (
        item_slot == "One Hand" and (slot == "Main Hand" or (slot == "Off Hand" and profile.get("dual_wield")))
    )
    return (
        matching_slot
        and (slot != "Off Hand" or not profile.get("require_shield") or shield)
        and (not restrictions.get("classes") or profile["class"] in restrictions["classes"])
        and (not armor_type or armor_type in profile["armor_types"] or (shield and profile["class"] in {"Paladin", "Shaman", "Warrior"}))
        and (not item.get("weapon_subtype") or item["weapon_subtype"] in profile["weapon_types"])
        and (item_slot != "Two Hand" or not item.get("weapon_subtype")
             or item["weapon_subtype"] in profile.get("two_hand_weapon_types", []))
        and (not item.get("weapon_subtype") or not profile.get("slot_weapon_types", {}).get(slot)
             or item["weapon_subtype"] in profile["slot_weapon_types"][slot])
        and (not require_source or any(source_usable_by(source, faction, profile["class"])
                                       for source in item["sources"] for faction in FACTIONS))
    )


def score(item: dict, weights: dict) -> float:
    stats = {**item.get("stats", {}), **{key: item[key] for key in ("armor", "dps", "weapon_speed") if key in item}}
    separate_weapon_dps(item, stats)
    return round(sum(stats[key] * weight for key, weight in weights.items() if numeric(stats.get(key))), 6)


def guide_observations(snapshots: dict[str, dict]) -> dict:
    observations = {}
    for source in dataset_json("forever", "scrape_manifest")["sources"]:
        if source.get("data_family") != "bis_lists":
            continue
        url = source["url"]
        for table in snapshots.get(url, {}).get("tables", []):
            slot = table.get("slot")
            if not slot:
                continue
            if slot in {"Relic", "Idol", "Totem", "Libram"}:
                slot = {"Druid": "Idol", "Shaman": "Totem", "Paladin": "Libram"}.get(source["class"], slot)
            key = (*profile_key(source), slot)
            observations.setdefault(key, []).append({
                "source_url": url, "status": source["status"],
                "evidence_ref": evidence_ref(url, snapshots) if url in snapshots else None,
                "item_ids": list(dict.fromkeys(row["item_id"] for row in table["rows"])),
            })
    return observations


def validate_ranking_review(review: dict, version: str, context: dict) -> None:
    """Check one decision against the already computed candidate set."""
    candidate_ids = {row["item_id"] for row in context["candidates"]}
    approved_ids = review.get("item_ids", [])
    guide_ids = review.get("guide_item_ids", [])
    if (
        not has_review(review) or review.get("profile_version") != version
        or review.get("candidate_digest") != context["candidate_digest"]
        or not approved_ids or len(set(approved_ids)) != len(approved_ids)
        or ("best_in_slot" in review and type(review["best_in_slot"]) is not bool)
        or not set(approved_ids).issubset(candidate_ids)
        or (guide_ids and not is_forever_url(review.get("guide_url")))
        or (guide_ids and not any(
            observation["source_url"] == review.get("guide_url")
            and observation.get("evidence_ref") == review.get("guide_evidence_ref")
            and set(guide_ids).issubset(observation["item_ids"])
            for observation in context["guide_observations"]
        ))
    ):
        raise ValueError(f"Invalid Forever ranking review for {context['class']}/{context['spec']}/{context['slot']}")


def rank(stats: dict, profiles: dict, overrides: list[dict], guides: dict) -> tuple[list, list]:
    reviews = {}
    for review in overrides:
        if review.get("type") == "approve_ranking":
            key = (*profile_key(review), review["slot"])
            if key in reviews:
                raise ValueError(f"Duplicate Forever ranking review for {key}")
            reviews[key] = review

    lists, audit = [], []
    for profile in sorted(profiles["profiles"], key=profile_key):
        class_name, spec = profile_key(profile)
        weights = {**profiles["role_weights"][profile["role"]], **profile.get("weights", {})}
        for slot in profile["slots"]:
            candidates = [(item_id, score(row, weights)) for item_id, row in stats.items() if eligible(row, profile, slot)]
            candidates.sort(key=lambda candidate: (-candidate[1], candidate[0]))
            candidate_ids = {item_id for item_id, _ in candidates}
            key = (class_name, spec, slot)
            observations = guides.get(key, [])
            candidate_digest = digest({"weights": weights, "items": [stats[item_id] for item_id in sorted(candidate_ids)]})
            if slot == "Off Hand" and profile.get("dual_wield"):
                main_ids = sorted(item_id for item_id,row in stats.items() if eligible(row,profile,"Main Hand"))
                candidate_digest = digest({"off_hand":candidate_digest,"main_hand_items":[stats[item_id] for item_id in main_ids]})
            review = reviews.pop(key, None)
            approved_ids = review.get("item_ids", []) if review else []
            guide_ids = review.get("guide_item_ids", []) if review else []
            context = {
                "class": class_name, "spec": spec, "slot": slot,
                "candidate_digest": candidate_digest,
                "candidates": [{"item_id": item_id, "score": value} for item_id, value in candidates],
                "guide_observations": observations,
                "guide_item_ids": guide_ids, "approved_item_ids": approved_ids,
                "guide_order_differs": bool(guide_ids) and [item_id for item_id, _ in candidates if item_id in guide_ids] != guide_ids,
            }
            if review:
                validate_ranking_review(review, profiles["version"], context)
            audit.append(context)
            if review:
                first_is_bis = review.get("best_in_slot", True)
                lists.append({
                    "class": class_name, "spec": spec, "phase": PRE_RAID, "slot": slot,
                    "source_url": review.get("guide_url") or review["source_url"],
                    "items": [
                        {"item_id": item_id, "rank": position,
                         "rank_group": "bis" if position == 1 and first_is_bis else "ranked",
                         "rank_label": "BiS" if position == 1 and first_is_bis else "Alt"}
                        for position, item_id in enumerate(approved_ids, 1)
                    ],
                })
    if reviews:
        raise ValueError(f"Unknown Forever ranking profiles or slots: {sorted(reviews)}")
    return lists, audit


def derive(snapshots: dict[str, dict], *, include_leveling: bool = True) -> dict:
    from tools.forever_comparison import comparison_document

    overrides = dataset_json("forever", "overrides")["overrides"]
    if any(review.get("type") not in {"verify_item", "approve_ranking"} for review in overrides):
        raise ValueError("Unknown Forever approval type")
    profiles = scoring_profiles()
    items, stats = load_verified_items(snapshots, overrides)
    records = evidence_index(snapshots)
    for review in overrides:
        if review.get("type") == "approve_ranking":
            check_evidence_refs(review, records)
    lists, audit = rank(stats, profiles, overrides, guide_observations(snapshots))
    documents = {
        "evidence": {"evidence": list(records.values())},
        "items": {"items": [items[item_id] for item_id in sorted(items)]},
        "item_stats": {"item_stats": [stats[item_id] for item_id in sorted(stats)]},
        "bis_lists": {"lists": lists},
        "recommendation_audit": {"profile_version": profiles["version"], "rows": audit},
        "comparison_item_stats": comparison_document(snapshots),
    }
    if include_leveling:
        from tools.forever_leveling import documents as leveling_documents
        documents.update(leveling_documents(snapshots))
        if (FOREVER_CANONICAL_DIR / "scoring_model.json").is_file():
            from tools.forever_scoring import reviewed_runtime_model

            reviewed_runtime_model(snapshots, documents)
    return documents


def import_snapshots(input_dir: Path, *, dry_run: bool, family: str | None = None) -> dict:
    snapshots = read_snapshots(input_dir)
    if family == "leveling":
        from tools.forever_comparison import comparison_document
        from tools.forever_leveling import documents as leveling_documents
        documents = {"evidence": {"evidence": list(evidence_index(snapshots).values())},
                     "comparison_item_stats": comparison_document(snapshots),
                     **leveling_documents(snapshots)}
        if (FOREVER_CANONICAL_DIR / "scoring_model.json").is_file():
            from tools.forever_scoring import reviewed_runtime_model

            reviewed_runtime_model(snapshots, documents)
    else:
        documents = derive(snapshots)
    if not dry_run:
        for name, document in documents.items():
            write_text(FOREVER_CANONICAL_DIR / f"{name}.json", json.dumps(document, indent=2, sort_keys=True) + "\n")
        from tools.forever_sources import enrich_retry_metadata
        enrich_retry_metadata(snapshots)
    return {name: len(next((value for value in document.values() if isinstance(value, list)), [])) for name, document in documents.items()}


def live_acceptance() -> dict:
    path = FOREVER_CANONICAL_DIR / "live_acceptance.json"
    document = load_json(path) if path.is_file() else {}
    errors = []
    if document.get("status") != "accepted":
        errors.append("Forever live gameplay acceptance is pending")
    if not has_review(document):
        errors.append("Live acceptance needs reviewer, date, target build and evidence source")
    if document.get("artifact_digest") != release_artifact_digest():
        errors.append("Live acceptance does not cover the current Forever addon files")
    if any(document.get("checks", {}).get(key) is not True for key in LIVE_ACCEPTANCE_CHECKS):
        errors.append("Required live gameplay checks have not all been recorded")
    performance = document.get("performance", {})
    if any(not numeric(performance.get(key)) or performance[key] < 0 for key in ("startup_ms", "first_open_ms")):
        errors.append("Startup and first-open timings have not been recorded")
    return {"ok":not errors,"status":document.get("status", "pending"),"errors":errors}


def release_artifact_digest() -> str:
    toc = ROOT / "BigBiSList_Camelot.toc"
    entries = [line.strip() for line in toc.read_text(encoding="utf-8").splitlines()
               if line.strip() and not line.strip().startswith("#")]
    paths = [toc, *((ROOT / entry).resolve() for entry in entries)]
    if any(not path.is_relative_to(ROOT) or not path.is_file() for path in paths):
        raise ValueError("Forever manifest contains an invalid release artifact")
    return digest({str(path.relative_to(ROOT)).replace("\\", "/"):hashlib.sha256(path.read_bytes()).hexdigest()
                   for path in sorted(set(paths))})


def coverage() -> dict:
    scoring = scoring_profiles()
    profiles = scoring["profiles"]
    items = {row["id"]: row for row in dataset_json("forever", "items")["items"]}
    lists = dataset_json("forever", "bis_lists")["lists"]
    by_slot = {(row["class"], row["spec"], row["slot"]): row["items"] for row in lists}
    missing = []
    for profile in profiles:
        for slot in profile["slots"]:
            for faction in FACTIONS:
                choices = by_slot.get((*profile_key(profile), slot), [])
                if not any(
                    source_usable_by(source, faction, profile["class"])
                    for choice in choices for source in items.get(choice["item_id"], {}).get("sources", [])
                ):
                    missing.append({"class": profile["class"], "spec": profile["spec"], "slot": slot, "faction": faction})
    roster_reviewed = scoring.get("status") in {"source_reviewed", "live_reviewed"} and has_review(scoring.get("review", {})) and all(
        profile_reviewed(profile, scoring) for profile in profiles
    )
    return {
        "ok": not missing and bool(profiles) and roster_reviewed,
        "specs": len(profiles), "roster_reviewed": roster_reviewed,
        "missing_count": len(missing), "missing": missing,
    }


def profile_digest(profile: dict, document: dict) -> str:
    return digest({
        "version": document["version"],
        "weights": {**document["role_weights"][profile["role"]], **profile.get("weights", {})},
        **{key: profile.get(key) for key in ("class", "spec", "armor_types", "weapon_types", "two_hand_weapon_types", "slots", "dual_wield", "require_shield", "slot_weapon_types")},
    })


def profile_reviewed(profile: dict, document: dict) -> bool:
    review = profile.get("review", {})
    return has_review(review) and review.get("profile_digest") == profile_digest(profile, document)


def gaps(snapshots: dict[str, dict]) -> dict:
    """Read-only review queue; stale approvals never prevent inspecting inputs."""
    document = scoring_profiles()
    overrides = dataset_json("forever", "overrides")["overrides"]
    records = evidence_index(snapshots)
    leads = route_leads(snapshots)
    observed = item_observations(snapshots)
    raw = {identifier: rows[0] for identifier, rows in observed.items()}
    conflicts = item_conflicts(snapshots)
    items, stats, stale_items, issues = {}, {}, set(), []
    seen_items = set()
    for review in overrides:
        if review.get("type") != "verify_item":
            continue
        identifier = review.get("item_id")
        try:
            if identifier in seen_items:
                raise ValueError(f"Duplicate Forever item review: {identifier}")
            seen_items.add(identifier)
            approved_items, approved_stats = load_verified_items(snapshots, [review], records=records, conflicts=conflicts)
            items.update(approved_items)
            stats.update(approved_stats)
        except (KeyError, TypeError, ValueError) as exc:
            stale_items.add(identifier)
            items.pop(identifier, None)
            stats.pop(identifier, None)
            issues.append({"type": "item", "item_id": identifier, "error": str(exc)})
    observations = guide_observations(snapshots)
    _, audit = rank(stats, document, [], observations)
    audits = {(*profile_key(row), row["slot"]): row for row in audit}
    reviews = {}
    stale_rankings = set()
    for review in overrides:
        if review.get("type") != "approve_ranking":
            continue
        key = (review.get("class"), review.get("spec"), review.get("slot"))
        try:
            if key in reviews:
                raise ValueError(f"Duplicate Forever ranking review: {key}")
            check_evidence_refs(review, records)
            if key not in audits:
                raise ValueError(f"Forever ranking review refers to an unsupported slot: {key}")
            validate_ranking_review(review, document["version"], audits[key])
            reviews[key] = review
        except (KeyError, TypeError, ValueError) as exc:
            stale_rankings.add(key)
            reviews.pop(key, None)
            issues.append({"type": "ranking", "class": key[0], "spec": key[1], "slot": key[2], "error": str(exc)})

    provisional_items = {}
    for identifier, snapshot in sorted(raw.items()):
        parsed = snapshot.get("item_stats", {})
        level = parsed.get("required_level")
        if parsed.get("slot") not in SLOT_NAMES | {"One Hand"} or (level is not None and (not numeric(level) or not 0 <= level <= 60)):
            continue
        provisional_items[identifier] = {
            "item_id": identifier, "name": snapshot["name"], "snapshot_url": snapshot["evidence_url"],
            "evidence_ref": evidence_ref(snapshot["evidence_url"], snapshots),
            "slot": parsed["slot"], "required_level": level, "stats": parsed.get("stats", {}),
            "conflicting_evidence": conflicts.get(identifier, []),
            "item_reviewed": identifier in items, "stale_review": identifier in stale_items,
            "route_leads": leads.get(identifier, []),
            "effects_need_review": bool(parsed.get("equip_effects") or parsed.get("use_effects")),
            "equip_effects": parsed.get("equip_effects", []), "use_effects": parsed.get("use_effects", []),
        }
    rows = []
    status_counts = Counter()
    for profile in sorted(document["profiles"], key=profile_key):
        weights = {**document["role_weights"][profile["role"]], **profile.get("weights", {})}
        for slot in profile["slots"]:
            key = (*profile_key(profile), slot)
            context = audits[key]
            guide_ids = {identifier for observation in observations.get(key, []) for identifier in observation["item_ids"]}
            provisional = []
            for identifier in provisional_items:
                snapshot = raw[identifier]
                parsed = snapshot.get("item_stats", {})
                if not eligible(parsed, profile, slot, require_source=False):
                    continue
                provisional.append({
                    "item_id": identifier, "score": score(parsed, weights), "guide_observed": identifier in guide_ids,
                })
            provisional.sort(key=lambda row: (-row["score"], row["item_id"]))
            for faction in FACTIONS:
                usable = [row["item_id"] for row in context["candidates"] if any(
                    source_usable_by(source, faction, profile["class"]) for source in items[row["item_id"]]["sources"])]
                ranking = reviews.get(key, {}) if key not in stale_rankings else {}
                approved = [identifier for identifier in ranking.get("item_ids", []) if identifier in usable]
                statuses = []
                missing_stats = sorted(identifier for identifier in guide_ids if identifier not in raw or not raw[identifier].get("item_stats", {}).get("slot"))
                if not provisional or missing_stats:
                    statuses.append("missing_stats")
                if not usable:
                    statuses.append("missing_routes")
                if any(not provisional_items[row["item_id"]]["item_reviewed"] for row in provisional):
                    statuses.append("pending_item_review")
                if usable and not approved:
                    statuses.append("pending_ranking_review")
                if key in stale_rankings or any(provisional_items[row["item_id"]]["stale_review"] for row in provisional):
                    statuses.append("stale_review")
                if approved:
                    statuses.insert(0, "covered")
                status_counts.update(statuses)
                rows.append({
                    "class": profile["class"], "spec": profile["spec"], "slot": slot, "faction": faction,
                    "statuses": statuses, "covered": bool(approved), "approved_item_ids": approved,
                    "reviewed_candidate_ids": usable, "candidate_digest": context["candidate_digest"],
                    "profile_digest": profile_digest(profile, document), "profile_reviewed": profile_reviewed(profile, document),
                    "missing_stat_item_ids": missing_stats, "provisional_candidates": provisional,
                    "guide_observations": observations.get(key, []),
                })
    roster_reviewed = document.get("status") in {"source_reviewed", "live_reviewed"} and has_review(document.get("review", {})) and all(
        profile_reviewed(profile, document) for profile in document["profiles"])
    return {
        "ok": bool(rows) and all(row["covered"] for row in rows) and roster_reviewed and not issues,
        "summary": {"specs": len(document["profiles"]), "coverage_cells": len(rows),
                    "covered": sum(row["covered"] for row in rows), "missing": sum(not row["covered"] for row in rows),
                    "roster_reviewed": roster_reviewed, "item_snapshots": len(raw), "approved_items": len(items),
                    "conflicting_items": len(conflicts),
                    "status_counts": dict(sorted(status_counts.items()))},
        "review_issues": issues, "rows": rows, "provisional_items": list(provisional_items.values()),
    }


def validate() -> tuple[list[str], dict]:
    errors = []
    profiles = scoring_profiles()
    keys = [profile_key(row) for row in profiles["profiles"]]
    if {class_name for class_name, _ in keys} != CLASSES or set(keys) != roster() or len(keys) != len(set(keys)):
        errors.append("Forever scoring profiles must cover the class/spec roster exactly once")
    for row in profiles["profiles"]:
        if not row["slots"] or len(set(row["slots"])) != len(row["slots"]) or not set(row["slots"]).issubset(SLOT_NAMES):
            errors.append(f"Invalid applicable slots for {profile_key(row)}")
        if row["role"] not in profiles["role_weights"] or not all(map(numeric, row.get("weights", {}).values())):
            errors.append(f"Invalid role weights for {profile_key(row)}")
    if not all(numeric(value) for weights in profiles["role_weights"].values() for value in weights.values()):
        errors.append("Forever role weights must be finite numbers")
    manifest = dataset_json("forever", "scrape_manifest")
    if manifest.get("flavor") != "forever" or not all(source_provider(url) for url in registered_urls()):
        errors.append("Forever manifest contains cross-flavor sources")
    if dataset_json("forever", "phases")["phases"] != [{"key": PRE_RAID, "name": "Pre-Raid"}]:
        errors.append("Forever pilot requires a single Pre-Raid phase")
    try:
        documents = derive(read_snapshots(FOREVER_RAW_DIR))
        for name, document in documents.items():
            path = FOREVER_CANONICAL_DIR / f"{name}.json"
            if not path.is_file() or load_json(path) != document:
                errors.append(f"Forever {name}.json differs from the reviewed snapshots and scoring inputs")
        summary = {key: value for key, value in coverage().items() if key not in {"missing", "ok"}}
        summary["items"] = len(documents["items"]["items"])
        leveling = documents.get("leveling_audit", {}).get("summary", {})
        summary["leveling_recommendations"] = len(documents.get("leveling_recommendations", {}).get("leveling_recommendations", []))
        summary["leveling_uncovered_combinations"] = leveling.get("uncovered_combinations", 0)
        summary["leveling_rules_reviewed"] = leveling.get("reviewed_rules", False)
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(f"Invalid Forever dataset: {exc}")
        summary = {}
    return errors, summary
