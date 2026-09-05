"""Reviewed source corrections kept separate from source-page observations.

This module does not fetch data or choose new rankings.  The source_rules
records returned by ``reviewed_source_overrides`` are intended to be committed
to canonical/overrides.json and applied after ordinary source imports.  Their
input evidence is a small, committed audit of the Phase 3 refresh.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Iterable

from tools.sources import (
    PHASE_INDEX,
    classify_sources,
    derive_acquisition_phase,
    derive_primary_source,
    summarize_sources,
)


EVIDENCE_DIR = Path(__file__).resolve().parents[1] / "data/raw/wowhead/phase_source_evidence"
CHILD_SOURCE_KEYS = ("token_sources", "quest_starter_sources", "recipe_sources")
POTION_NEWS_URL = (
    "https://www.wowhead.com/tbc/news/"
    "take-advantage-of-mark-of-the-illidari-for-free-raid-consumables-382623"
)


def _matching(source: dict[str, Any], fields: dict[str, Any]) -> bool:
    for key, expected in fields.items():
        actual = source.get(key)
        if isinstance(expected, list):
            if actual not in expected:
                return False
        elif actual != expected:
            return False
    return True


def _source_signature(source: dict[str, Any]) -> str:
    # Provenance does not change the acquisition represented by an append.
    ignored = {"confidence", "source_url", "reviewed_override_id"}
    return json.dumps({key: value for key, value in source.items() if key not in ignored}, sort_keys=True)


def _apply_rule(
    source: dict[str, Any], rule: dict[str, Any], override_id: str, *, parent_key: str = "sources"
) -> dict[str, Any] | None:
    source = deepcopy(source)
    in_scope = not rule.get("source_keys") or parent_key in rule["source_keys"]
    if in_scope and _matching(source, rule.get("match", {})):
        if rule.get("exclude"):
            return None
        for field in rule.get("remove_fields", []):
            source.pop(field, None)
        for key, value in rule.get("set", {}).items():
            # A general item release cannot make an already later seller or
            # recipe available sooner, or extend a previously reviewed window.
            if key == "available_from_phase" and source.get(key) in PHASE_INDEX:
                value = max((source[key], value), key=PHASE_INDEX.__getitem__)
            if key == "available_until_phase" and source.get(key) in PHASE_INDEX:
                value = min((source[key], value), key=PHASE_INDEX.__getitem__)
            source[key] = deepcopy(value)
        if rule.get("append_requirements"):
            requirements = source.setdefault("requirements", [])
            for requirement in rule["append_requirements"]:
                identity = (requirement.get("type"), requirement.get("scope"), requirement.get("reputation"),
                            requirement.get("standing_rank"), requirement.get("profession"), requirement.get("skill"))
                matching_index = next((index for index, existing in enumerate(requirements)
                                       if (existing.get("type"), existing.get("scope"), existing.get("reputation"),
                                           existing.get("standing_rank"), existing.get("profession"), existing.get("skill")) == identity), None)
                if matching_index is None:
                    requirements.append(deepcopy(requirement))
                else:
                    # Re-importing a reviewed correction must replace stale
                    # confidence/provenance for that requirement identity.
                    requirements[matching_index].update(deepcopy(requirement))
        source["reviewed_override_id"] = override_id
    if rule.get("recursive", False):
        for key in CHILD_SOURCE_KEYS:
            if key in source:
                source[key] = [changed for child in source[key]
                               if (changed := _apply_rule(child, rule, override_id, parent_key=key)) is not None]
    return source


def apply_source_rule_overrides(
    entity: dict[str, Any],
    overrides: Iterable[dict[str, Any]],
    *,
    entity_kind: str = "item",
) -> dict[str, Any]:
    """Apply explicit rules to one item/gem/enchant source record without mutation.

    ``entity_kind`` is required to distinguish item IDs from spell IDs; gems
    and item-based enchantments use ``item`` and spell enchantments use
    ``spell``.  Rules can target one entity or all entities with an empty target.
    Existing source windows and nested dependency records are retained.
    """
    result = deepcopy(entity)
    entity_id = result.get("id", result.get(f"{entity_kind}_id"))
    changed = False
    for override in overrides:
        if override.get("type") != "source_rules":
            continue
        target = override.get("target", {})
        if target and target.get(f"{entity_kind}_id") != entity_id:
            continue
        data = override.get("data", {})
        for field, value in data.get("set_fields", {}).items():
            # These reviewed acquisition facts are the only supported entity
            # edits here; identity, rankings, binding and ownership stay intact.
            if field != "tradeable" or not isinstance(value, bool):
                raise ValueError(f"Unsupported source-rule entity field: {field}")
            if result.get(field) != value:
                result[field] = value
                changed = True
        sources = deepcopy(result.get("sources", []))
        for rule in data.get("rules", []):
            sources = [updated for source in sources
                       if (updated := _apply_rule(source, rule, override["id"])) is not None]
        known = {_source_signature(source) for source in sources}
        for source in data.get("append_sources", []):
            if _source_signature(source) not in known:
                appended = deepcopy(source)
                appended["reviewed_override_id"] = override["id"]
                sources.append(appended)
                known.add(_source_signature(source))
        if sources != result.get("sources", []):
            result["sources"] = sources
            changed = True
    if changed:
        result["sources"] = classify_sources(result.get("sources", []))
        result["primary_source"] = derive_primary_source(result["sources"])
        result["source_summary"] = summarize_sources(result["sources"])
        # Enhancement source records historically omit acquisition_phase.  Do
        # not add new fields to those records just to refresh their summaries.
        if "acquisition_phase" in result:
            result["acquisition_phase"] = derive_acquisition_phase(result["sources"])
    return result


def apply_source_rule_overrides_to_rows(
    rows: Iterable[dict[str, Any]], overrides: Iterable[dict[str, Any]], *, entity_kind: str = "item"
) -> list[dict[str, Any]]:
    records = list(overrides)
    return [apply_source_rule_overrides(row, records, entity_kind=entity_kind) for row in rows]


def _reviewed_record(
    record_id: str, entity_id: int, source_url: str, reason: str, data: dict[str, Any], *, entity_kind: str = "item"
) -> dict[str, Any]:
    return {
        "id": record_id,
        "type": "source_rules",
        "target": {f"{entity_kind}_id": entity_id},
        "reason": reason,
        "reviewer": "codex-source-review",
        "reviewed_at": "2026-09-04",
        "source_url": source_url,
        "data": data,
    }


def potion_purchase_overrides() -> list[dict[str, Any]]:
    records = []
    evidence = json.loads((EVIDENCE_DIR / "mark_of_the_illidari.json").read_text(encoding="utf-8"))
    for item_id in evidence["potion_item_ids"]:
        sources = []
        for vendor in evidence["vendors"]:
            requirements = [{
                "type": "reputation",
                "scope": "vendor_purchase",
                "reputation": reputation,
                "standing": "Exalted",
                "standing_rank": 8,
                "raw_text": f"Requires {reputation} - Exalted",
                "source_url": POTION_NEWS_URL,
                "confidence": "manual_review",
            } for reputation in ["The Sha'tar", "Cenarion Expedition", vendor["reputation"]]]
            sources.append({
                "type": "vendor",
                "entity_id": vendor["id"],
                "vendor_id": vendor["id"],
                "entity_name": vendor["name"],
                "zone": "Shattrath City",
                "location_area": "Shattrath City",
                "purchase_quantity": 10,
                "costs": [{"item_id": 32897, "name": "Mark of the Illidari", "amount": 1}],
                "available_from_phase": "T6",
                "requirements": requirements,
                "source_url": POTION_NEWS_URL,
                "confidence": "reviewed_override",
            })
        records.append(_reviewed_record(
            f"anniversary-phase3-mark-potions-{item_id}", item_id, POTION_NEWS_URL,
            "The September 2026 live report verifies ten ordinary potions per Mark of the Illidari at each Shattrath faction vendor, with three Exalted reputations. Append the new purchase routes while retaining crafting and other sources; Marks are tradeable, not a bound raid-tier token.",
            {"append_sources": sources, "evidence_path": "data/raw/wowhead/phase_source_evidence/mark_of_the_illidari.json"},
        ))
    return records


def _recipe_requirements(recipe: dict[str, Any]) -> list[dict[str, Any]]:
    if not recipe.get("reputation"):
        return []
    return [{
        "type": "reputation", "scope": "vendor_purchase",
        "reputation": recipe["reputation"], "standing": recipe["standing"],
        "standing_rank": recipe["standing_rank"],
        "raw_text": f"Requires {recipe['reputation']} - {recipe['standing']}",
        "source_url": f"https://www.wowhead.com/tbc/item={recipe['item_id']}",
        "confidence": "manual_review",
    }]


def profession_source_overrides() -> list[dict[str, Any]]:
    """Apply named T6 unlocks without backdating old-faction vendors.

    Recipe-child scope is deliberate: purchasing a tradeable raid-origin
    pattern permits personal crafting, but never makes its bound product or
    an unrelated raid-token dependency tradeable.
    """
    evidence_path = "data/raw/wowhead/phase_source_evidence/profession_phase3.json"
    evidence = json.loads((EVIDENCE_DIR / "profession_phase3.json").read_text(encoding="utf-8"))
    records = []
    recipes = evidence["recipes"]
    phase = evidence["content_phase"]
    floor = {"match": {}, "set": {"available_from_phase": phase}}
    global_rules = []
    for recipe in recipes:
        source_url = evidence["hunter_guide_url"] if recipe.get("phase_evidence") == "hunter_guide" else evidence["source_url"]
        rules = [deepcopy(floor)]
        requirements = _recipe_requirements(recipe)
        if requirements:
            rules.append({"match": {"type": "vendor"}, "append_requirements": requirements})
        records.append(_reviewed_record(
            f"anniversary-phase3-recipe-{recipe['item_id']}", recipe["item_id"], source_url,
            recipe.get("review_basis", "The named Anniversary Phase 3 recipe is unlocked with Black Temple and Hyjal even when its seller or reputation existed earlier."),
            {"rules": rules, "evidence_path": evidence_path},
        ))
        if recipe["item_id"] == 33165:
            # The current tooltip endpoint omits its seller table. The
            # reviewed article and original taught-by-item vendor relationship
            # identify this exact vendor; a window on an empty list cannot
            # supply the missing acquisition route.
            records[-1]["data"]["append_sources"] = [{
                "type": "vendor", "item_id": recipe["item_id"],
                "entity_id": recipe["vendor_id"], "vendor_id": recipe["vendor_id"],
                "entity_name": recipe["vendor_name"], "zone": recipe["vendor_zone"],
                "available_from_phase": phase, "requirements": requirements,
                "source_url": f"https://www.wowhead.com/tbc/item={recipe['item_id']}",
                "confidence": "reviewed_override",
            }]
        child_rule = {
            "match": {"item_id": recipe["item_id"]}, "source_keys": ["recipe_sources"],
            "set": {"available_from_phase": phase}, "recursive": True,
        }
        if recipe["binding"] == "unbound":
            child_rule["set"]["tradeable"] = True
        if requirements:
            child_rule["append_requirements"] = requirements
        global_rules.append(child_rule)
    dependency_record = _reviewed_record(
        "anniversary-phase3-reviewed-recipe-dependencies", 0, evidence["source_url"],
        "Apply exact recipe identities to nested acquisition paths. Only the reviewed unbound recipe is tradeable; the resulting crafted item's binding is preserved.",
        {"rules": global_rules, "evidence_path": evidence_path},
    )
    dependency_record["target"] = {}
    records.append(dependency_record)
    for entity_kind, key in (("item", "product_id"), ("spell", "spell_id")):
        for entity_id in sorted({recipe[key] for recipe in recipes if key in recipe}):
            records.append(_reviewed_record(
                f"anniversary-phase3-profession-{entity_kind}-{entity_id}", entity_id, evidence["source_url"],
                "The output or enchant cannot predate its newly released T6 recipe. Existing later seller windows and alternative recipe paths remain intact.",
                {"rules": [deepcopy(floor)], "evidence_path": evidence_path}, entity_kind=entity_kind,
            ))
    for ammunition in evidence["ammunition"]:
        records.append(_reviewed_record(
            f"anniversary-phase3-ammunition-{ammunition['item_id']}", ammunition["item_id"], evidence["hunter_guide_url"],
            "The current named Black Temple/Hyjal hunter guide explicitly introduces this ammunition in T6. Its reputation seller existed earlier, so the item needs its own unlock floor.",
            {"rules": [deepcopy(floor), {"match": {"type": "vendor"},
                                       "append_requirements": _recipe_requirements(ammunition)}],
             "evidence_path": evidence_path},
        ))
    return records


def reviewed_source_overrides() -> list[dict[str, Any]]:
    """Return deterministic reviewed records for canonical/overrides.json."""
    records = potion_purchase_overrides() + profession_source_overrides() + tradeable_enhancement_overrides()
    evidence = json.loads((EVIDENCE_DIR / "season3_pvp.json").read_text(encoding="utf-8"))
    for item in evidence["items"]:
        # These are explicit per-item reviewed identities, not a name-prefix
        # rule.  Vindicator's Brand/Hauberk are unrelated Aldor reputation gear.
        rules = [{"match": {}, "set": {"available_from_phase": item["content_phase"]}}]
        rules.append({
            "match": {"type": ["vendor", "pvp", "token_turnin"], "zone": "Isle of Quel'Danas"},
            "set": {"available_from_phase": "SWP"},
            "recursive": True,
        })
        # Undated table variants cannot establish a current-season discount.
        # Keep the access route and its raw snapshot, but omit unverified prices.
        rules.append({"match": {"type": "pvp"}, "remove_fields": ["costs", "price_copper"]})
        for price in item.get("verified_prices", []):
            rules.append({"match": {"type": "pvp", **price.get("match", {})}, "set": {
                "costs": price["costs"],
                "source_url": price["source_url"],
                "confidence": "reviewed_override",
            }})
        records.append(_reviewed_record(
            f"anniversary-pvp-source-context-{item['item_id']}", item["item_id"], item["source_url"],
            item["review_reason"],
            {"rules": rules, "evidence_path": "data/raw/wowhead/phase_source_evidence/season3_pvp.json"},
        ))
    return records


def tradeable_enhancement_overrides() -> list[dict[str, Any]]:
    evidence_path = "data/raw/wowhead/phase_source_evidence/tradeable_enhancements.json"
    evidence = json.loads((EVIDENCE_DIR / "tradeable_enhancements.json").read_text(encoding="utf-8"))
    return [_reviewed_record(
        f"anniversary-reviewed-unbound-enhancement-{item['item_id']}", item["item_id"], item["source_url"],
        item["review_basis"], {"set_fields": {"tradeable": True}, "evidence_path": evidence_path},
    ) for item in evidence["items"]]


def source_review_audit() -> dict[str, Any]:
    """Expose withheld acquisition evidence separately from ranking coverage."""
    evidence = json.loads((EVIDENCE_DIR / "season3_pvp.json").read_text(encoding="utf-8"))
    profession_evidence = json.loads((EVIDENCE_DIR / "profession_phase3.json").read_text(encoding="utf-8"))
    tradeable_evidence = json.loads((EVIDENCE_DIR / "tradeable_enhancements.json").read_text(encoding="utf-8"))
    return {
        "reviewed_item_count": len(evidence["items"]),
        "verified_price_item_ids": [item["item_id"] for item in evidence["items"] if item.get("verified_prices")],
        "unverified_price_item_ids": [item["item_id"] for item in evidence["items"] if not item.get("verified_prices")],
        "quarantined_price_variants": [
            {"item_id": item["item_id"], "variants": item["observed_price_variants"]}
            for item in evidence["items"] if item.get("observed_price_variants")
        ],
        "limitations": evidence["limitations"],
        "reviewed_unbound_enhancement_item_ids": [item["item_id"] for item in tradeable_evidence["items"]],
        "profession_review": {
            "recipe_item_ids": [recipe["item_id"] for recipe in profession_evidence["recipes"]],
            "tradeable_recipe_item_ids": [recipe["item_id"] for recipe in profession_evidence["recipes"]
                                          if recipe["binding"] == "unbound"],
            "ammunition_item_ids": [item["item_id"] for item in profession_evidence["ammunition"]],
            "limitations": profession_evidence["limitations"],
        },
    }
