"""Verified phase enchant recommendations in Wowhead BiS guide loadouts.

Wowhead's TBC planner stores enchant spell IDs (its picker assigns
state.slots[slot].enchant = enchant.spell), not in-game enchant effect IDs.
Item applications are mapped only through committed enchant_effects evidence.
Unknown application spells remain auditable candidates, never guessed recipes.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import re
import sys
from typing import Any

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.phase_gems import PLANNER_FORMAT_SOURCE, _guide_markup, _planner_context, decode_tbc_planner, reviewed_gem_items
from tools.project import PHASE_KEYS, RAW_WOWHEAD_DIR, canonical_json


PLANNER_SLOTS = {1: "Head", 3: "Shoulder", 5: "Chest", 7: "Legs", 8: "Feet", 9: "Wrist",
                 10: "Hands", 11: "Ring", 12: "Ring", 15: "Back", 16: "Main Hand", 17: "Off Hand", 18: "Ranged"}
UNVERIFIED = {"no_distinct_update", "unverified_phase"}


def normalize_phase_enchant_guide(snapshot: dict[str, Any], html: str,
                                   bindings: list[dict[str, Any]],
                                   effect_rows: list[dict[str, Any]],
                                   inventory_slots: dict[int, str]) -> dict[str, Any]:
    markup = _guide_markup(html)
    spell_map = {row.get("source_spell_id", row["id"] if row["type"] == "spell" else 0): row for row in effect_rows}
    item_map = {row["id"]: row for row in effect_rows if row["type"] == "item"}
    guidance = []
    errors = []
    for match in re.finditer(r"\[gear-planner=([^\]\s]+)[^\]]*\]", markup):
        planner = match[1].lstrip("#")
        try:
            decoded = decode_tbc_planner(planner)
        except ValueError as exc:
            errors.append({"planner": planner, "error": str(exc)})
            continue
        applications = []
        for equipment in decoded["slots"]:
            spell_id = equipment.get("enchant_id")
            slot = PLANNER_SLOTS.get(equipment["slot"])
            if not spell_id or not slot:
                continue
            if slot == "Main Hand" and inventory_slots.get(equipment["item_id"]) == "Two Hand":
                slot = "Two Hand"
            application = {"slot": slot, "equipment_item_id": equipment["item_id"], "spell_id": spell_id}
            if spell_id in spell_map:
                known = spell_map[spell_id]
                application["entity"] = {key: known[key] for key in ("id", "type", "name")}
                application["mapping_source"] = "data/canonical/enchant_effects.json"
            applications.append(application)
        if applications:
            guidance.append({"kind": "gear_planner", "planner": planner,
                             "label": _planner_context(markup, match.start()), "applications": applications})

    # Only recommendation prose mentioning an enchant is considered.  The
    # canonical item mapping excludes equipment cited beside an enchant.
    for block in re.split(r"(?:\r?\n){2,}", markup):
        if not re.search(r"\benchant(?:s|ment|ing)?\b", block, re.I):
            continue
        position = markup.find(block)
        headings = re.findall(r"\[h[1-6][^\]]*\](.*?)\[/h[1-6]\]", markup[:position], re.S | re.I)
        heading = re.sub(r"\[[^\]]+\]", "", headings[-1]) if headings else ""
        for kind, entity_id_text in re.findall(r"\[(spell|item)=(\d+)[^\]]*\]", block):
            entity_id = int(entity_id_text)
            known = item_map.get(entity_id) if kind == "item" else spell_map.get(entity_id)
            # Greater Agility is named explicitly by the current Hunter prose.
            # Its identity is checked against the spell snapshot at import.
            if not known and not (kind == "spell" and entity_id == 42620):
                continue
            from tools.scrape_wowhead import slot_from_heading
            slot = (known or {}).get("slot") or slot_from_heading(heading)
            slots = [slot] if slot and slot != "Weapon" else ["Main Hand"] if slot == "Weapon" else []
            if kind == "spell" and entity_id == 42620 and re.search(r"dual.wield", heading, re.I):
                slots = ["Main Hand", "Off Hand"]
            for slot in slots:
                application = {"slot": slot, "spell_id": (known or {}).get("source_spell_id", entity_id)}
                if known:
                    application["entity"] = {key: known[key] for key in ("id", "type", "name")}
                    application["mapping_source"] = "data/canonical/enchant_effects.json"
                guidance.append({"kind": "linked_prose", "label": heading,
                                 "text": re.sub(r"\[[^\]]+\]", "", block).strip()[:1200],
                                 "applications": [application]})
    contexts = sorted({(binding["class"], binding["spec"], snapshot.get("content_phase", "PR")
                        if binding["phase"] == "PR" else binding["phase"])
                       for binding in bindings if binding.get("phase") in PHASE_KEYS})
    result = {"parser_version": "phase-enchants-1", "page_type": "phase_enchant_guide",
              "url": snapshot["url"], "fetched_at": snapshot["fetched_at"], "title": snapshot.get("title", ""),
              "planner_format_source": PLANNER_FORMAT_SOURCE,
              "bindings": [{"class": cls, "spec": spec, "phase": phase} for cls, spec, phase in contexts],
              "enchant_guidance": guidance}
    if snapshot.get("recommendation_status"):
        result["recommendation_status"] = snapshot["recommendation_status"]
    if errors:
        result["parse_errors"] = errors
    return result


def _prepare_evidence(snapshots: list[dict[str, Any]]) -> tuple[dict, dict, dict]:
    from tools.phase_source_overrides import apply_source_rule_overrides
    from tools.scrape_wowhead import reviewed_overrides, spell_snapshots_by_id
    items = reviewed_gem_items(snapshots)
    spells = spell_snapshots_by_id(snapshots)
    overrides = reviewed_overrides()
    for spell_id, spell in spells.items():
        reviewed = apply_source_rule_overrides({"id": spell_id, "sources": spell.get("normalized_sources", [])},
                                               overrides, entity_kind="spell")
        spell["normalized_sources"] = reviewed["sources"]
    contexts = {}
    for snapshot in snapshots:
        if snapshot.get("page_type") != "phase_enchant_guide" or snapshot.get("recommendation_status") in UNVERIFIED:
            continue
        for binding in snapshot.get("bindings", []):
            key = (binding["class"], binding["spec"], binding["phase"])
            for entry in snapshot.get("enchant_guidance", []):
                for application in entry["applications"]:
                    contexts.setdefault(key, []).append((snapshot, entry, application))
    return items, spells, contexts


def _recommendation(application: dict, items: dict, spells: dict, guide_url: str) -> tuple[dict | None, list[dict]]:
    from tools.scrape_wowhead import (enchant_formula_item_ids, enchant_requirements_for_import,
                                     formula_item_ids_for_spell, summarize_enchant_spell_sources,
                                     resolve_enchant_source_spell_snapshot, spell_snapshots_by_normalized_name)
    from tools.sources import summarize_sources
    entity = deepcopy(application.get("entity"))
    spell = spells.get(application["spell_id"], {})
    if entity is None:
        if not str(spell.get("name", "")).startswith("Enchant "):
            return None, []
        entity = {"type": "spell", "id": application["spell_id"], "name": spell["name"]}
    row = {**entity, "slot": application["slot"]}
    if entity["type"] == "item":
        sources = items.get(entity["id"], {}).get("normalized_sources", [])
        row["source_summary"] = summarize_sources(sources)
        requirements = enchant_requirements_for_import({}, guide_url, entity, None, None, [], items)
    else:
        source_spell = resolve_enchant_source_spell_snapshot(entity["id"], spell,
                           spell_snapshots_by_normalized_name(list(spells.values())), items) or spell
        source_spell_id = source_spell.get("spell_id", entity["id"])
        if source_spell_id != entity["id"]:
            row["source_spell_id"] = source_spell_id
        formula_ids = sorted(set(enchant_formula_item_ids(source_spell)) | set(formula_item_ids_for_spell(entity["id"], items))
                             | set(formula_item_ids_for_spell(source_spell_id, items)))
        direct = [source for source in source_spell.get("normalized_sources", []) if source.get("type") not in {"taught_by_item", "taught_by_spell"}]
        sources = direct + [source for formula_id in formula_ids for source in items.get(formula_id, {}).get("normalized_sources", [])]
        if formula_ids:
            row["formula_item_ids"] = formula_ids
        row["taught_by"] = deepcopy(source_spell.get("normalized_sources", []))
        row["source_summary"] = summarize_enchant_spell_sources(source_spell, formula_ids, items)
        requirements = enchant_requirements_for_import({}, guide_url, entity, spell, source_spell, formula_ids, items)
    if requirements:
        row["requirements"] = requirements
    return row, sources


def import_phase_enchants(snapshots: list[dict[str, Any]], base_enchants: dict[str, Any]) -> dict[str, Any]:
    from tools.scrape_wowhead import row_context
    from tools.sources import source_is_phase_available
    items, spells, contexts = _prepare_evidence(snapshots)
    rows = deepcopy(base_enchants.get("enchants", []))
    known = {(r["class"], r["spec"], r["phase"], r["slot"], r["type"], r["id"]): r for r in rows}
    for key, entries in sorted(contexts.items()):
        for snapshot, entry, application in entries:
            row, sources = _recommendation(application, items, spells, snapshot["url"])
            if not row or not sources or not any(source_is_phase_available(source, key[2]) for source in sources):
                continue
            row_key = (*key, row["slot"], row["type"], row["id"])
            if row_key in known:
                continue
            row.update({"class": key[0], "spec": key[1], "phase": key[2], "source_url": snapshot["url"],
                        "context": row_context({"heading": entry.get("label", "")}, {})})
            if re.search(r"mitigation|surviv|safety", entry.get("label", ""), re.I):
                row["context"] = "mitigation"
            rows.append(row)
            known[row_key] = row
    # Earlier recommendations remain available as alternatives.  A loadout does
    # not prove a lower price or that a situational enchant has become obsolete.
    return {"enchants": rows}


def build_phase_enchant_audit(snapshots: list[dict[str, Any]], base_enchants: dict[str, Any]) -> dict[str, Any]:
    from tools.sources import source_is_phase_available
    items, spells, contexts = _prepare_evidence(snapshots)
    coverage = []
    for key in sorted({(r["class"], r["spec"], r["phase"]) for r in base_enchants.get("enchants", [])}):
        verified, unmapped, missing, unavailable = set(), set(), set(), set()
        for snapshot, entry, application in contexts.get(key, []):
            row, sources = _recommendation(application, items, spells, snapshot["url"])
            if not row:
                unmapped.add(application["spell_id"])
            elif not sources:
                missing.add((row["type"], row["id"]))
            elif not any(source_is_phase_available(source, key[2]) for source in sources):
                unavailable.add((row["type"], row["id"]))
            else:
                verified.add((row["slot"], row["type"], row["id"]))
        coverage.append({"class": key[0], "spec": key[1], "phase": key[2],
                         "status": "partial_phase_guidance" if verified and (unmapped or missing) else "verified_phase_guidance" if verified else "general_guide_fallback",
                         "verified_recommendations": [list(r) for r in sorted(verified)],
                         "source_urls": sorted({snapshot["url"] for snapshot, _, _ in contexts.get(key, [])}),
                         "unmapped_application_spell_ids": sorted(unmapped),
                         "missing_acquisition_entities": [list(r) for r in sorted(missing)],
                         "phase_unavailable_entities": [list(r) for r in sorted(unavailable)]})
    errors = [{"url": s["url"], **e} for s in snapshots
              if s.get("page_type") == "phase_enchant_guide" for e in s.get("parse_errors", [])]
    return {"coverage": coverage, "parse_errors": errors,
            "unverified_guide_updates": [{"url": s["url"], "status": s["recommendation_status"], "bindings": s.get("bindings", [])}
                                         for s in snapshots if s.get("page_type") == "phase_enchant_guide" and s.get("recommendation_status") in UNVERIFIED],
            "complete_phase_guidance": bool(coverage) and not errors and all(r["status"] == "verified_phase_guidance" for r in coverage)}


def reviewed_enchant_effects() -> list[dict[str, Any]]:
    """New applied-enchant IDs reviewed from Wowhead's Spell Details table."""
    evidence = json.loads((RAW_WOWHEAD_DIR / "phase_enchants" / "reviewed_effects.json").read_text(encoding="utf-8"))
    return [{key: row[key] for key in ("type", "id", "name", "slot", "source_spell_id", "effect_ids", "source_url")}
            for row in evidence["records"]]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--input-dir", type=Path, default=RAW_WOWHEAD_DIR / "full_bis")
    parser.add_argument("--output-dir", type=Path, default=RAW_WOWHEAD_DIR / "phase_enchants")
    args = parser.parse_args()
    from tools.scrape_wowhead import html_cache_name, manifest_sources_for_snapshot, snapshot_name
    effects = canonical_json("enchant_effects")["enchant_effects"]
    inventory_slots = {row["id"]: row.get("inventory_slot") for row in canonical_json("items")["items"]}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for path in sorted(args.input_dir.glob("*.json")):
        snapshot = json.loads(path.read_text(encoding="utf-8"))
        if snapshot.get("page_type") != "guide" or "--pr-" in path.stem:
            continue
        html_path = args.cache_dir / html_cache_name(snapshot["url"])
        if not html_path.exists():
            continue
        result = normalize_phase_enchant_guide(snapshot, html_path.read_text(encoding="utf-8"),
                    manifest_sources_for_snapshot(snapshot, "bis_lists"), effects, inventory_slots)
        (args.output_dir / snapshot_name(snapshot["url"])).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        count += 1
    print(f"Normalized phase enchant guidance for {count} guide snapshots")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
