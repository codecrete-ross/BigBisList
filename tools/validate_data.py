from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.manifest_coverage import GLOBAL_FAMILIES, MATRIX_FAMILIES, STATIC_DATA_FAMILIES, units_covered_by_source
from tools.project import CANONICAL_DIR, CANONICAL_FILES, PHASE_KEYS, SLOT_NAMES, canonical_json
from tools.sources import derive_primary_source, summarize_sources


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str]
    summary: dict[str, int | str]


def _require(condition: bool, errors: list[str], message: str) -> None:
    if not condition:
        errors.append(message)


def validate() -> ValidationResult:
    errors: list[str] = []

    for file_name in CANONICAL_FILES.values():
        _require((CANONICAL_DIR / file_name).is_file(), errors, f"Missing canonical file: {file_name}")

    if errors:
        return ValidationResult(False, errors, {})

    classes_doc = canonical_json("classes")
    phases_doc = canonical_json("phases")
    bis_doc = canonical_json("bis_lists")
    items_doc = canonical_json("items")
    gems_doc = canonical_json("gems")
    gem_sources_doc = canonical_json("gem_sources")
    enchants_doc = canonical_json("enchants")
    enchant_sources_doc = canonical_json("enchant_sources")
    consumables_doc = canonical_json("consumables")
    leveling_doc = canonical_json("leveling")
    manifest_doc = canonical_json("scrape_manifest")
    overrides_doc = canonical_json("overrides")

    class_names: set[str] = set()
    specs_by_class: dict[str, set[str]] = {}
    spec_count = 0

    for class_data in classes_doc.get("classes", []):
        name = class_data.get("name")
        _require(isinstance(name, str) and bool(name), errors, "Class name must be a non-empty string")
        _require(name not in class_names, errors, f"Duplicate class: {name}")
        class_names.add(name)
        specs_by_class[name] = set()

        for spec in class_data.get("specs", []):
            spec_name = spec.get("name")
            _require(isinstance(spec_name, str) and bool(spec_name), errors, f"Spec name missing for class {name}")
            _require(spec_name not in specs_by_class[name], errors, f"Duplicate spec for {name}: {spec_name}")
            specs_by_class[name].add(spec_name)
            spec_count += 1

    _require(len(class_names) == 9, errors, f"Expected 9 classes, found {len(class_names)}")
    _require(spec_count == 28, errors, f"Expected 28 specs, found {spec_count}")

    phase_keys = [phase.get("key") for phase in phases_doc.get("phases", [])]
    _require(phase_keys == PHASE_KEYS, errors, f"Expected phases {PHASE_KEYS}, found {phase_keys}")

    item_ids: set[int] = set()
    for item in items_doc.get("items", []):
        item_id = item.get("id")
        _require(isinstance(item_id, int) and item_id > 0, errors, f"Invalid item id: {item_id}")
        _require(item_id not in item_ids, errors, f"Duplicate item id: {item_id}")
        item_ids.add(item_id)
        _require(bool(item.get("name")), errors, f"Item {item_id} is missing a name")
        _require(item.get("binding") in {"bind_on_equip", "bind_on_pickup", "bind_on_use", "quest", "unknown"}, errors, f"Item {item_id} has invalid binding: {item.get('binding')}")
        _require(item.get("boe") in {True, False, None}, errors, f"Item {item_id} has invalid boe value: {item.get('boe')}")
        if item.get("binding") == "bind_on_equip":
            _require(item.get("boe") is True, errors, f"Item {item_id} bind_on_equip must have boe=true")
        if item.get("binding") in {"bind_on_pickup", "quest"}:
            _require(item.get("boe") is False, errors, f"Item {item_id} {item.get('binding')} must have boe=false")
        _require(str(item.get("wowhead_url", "")).startswith("https://www.wowhead.com/tbc/"), errors, f"Item {item_id} must have a Wowhead TBC URL")
        sources = item.get("sources")
        _require(isinstance(sources, list) and len(sources) > 0, errors, f"Item {item_id} must have at least one structured source")
        if isinstance(sources, list) and sources:
            _require(item.get("primary_source") == derive_primary_source(sources), errors, f"Item {item_id} primary_source is not derived from sources")
            _require(item.get("source_summary") == summarize_sources(sources), errors, f"Item {item_id} source_summary is not derived from sources")
            for source in sources:
                source_type = source.get("type")
                _require(source_type in {"drop", "quest", "vendor", "crafted", "pvp", "token_turnin", "world_drop", "unknown"}, errors, f"Item {item_id} has invalid source type: {source_type}")
                _require(bool(source.get("confidence")), errors, f"Item {item_id} source is missing confidence")
                source_url = source.get("source_url")
                if source_url:
                    _require(str(source_url).startswith("https://www.wowhead.com/tbc/"), errors, f"Item {item_id} source URL must be a Wowhead TBC URL")
                if source_type == "drop":
                    _require(bool(source.get("entity_name")) or source.get("world_drop") is True, errors, f"Item {item_id} drop source needs entity_name or world_drop")
                if source_type in {"vendor", "pvp"}:
                    _require(bool(source.get("entity_name")), errors, f"Item {item_id} {source_type} source needs entity_name")
                if source_type == "quest":
                    _require(bool(source.get("entity_name")), errors, f"Item {item_id} quest source needs entity_name")
                    if source.get("quest_id") is not None:
                        _require(isinstance(source.get("quest_id"), int), errors, f"Item {item_id} quest source quest_id must be an integer")
                if source_type == "token_turnin":
                    _require(bool(source.get("entity_name")), errors, f"Item {item_id} token_turnin source needs turn-in entity_name")
                    _require(isinstance(source.get("token_sources"), list) and bool(source.get("token_sources")), errors, f"Item {item_id} token_turnin source needs token_sources")
                    for token_source in source.get("token_sources", []):
                        _require(isinstance(token_source.get("token_item_id"), int) and token_source.get("token_item_id") > 0, errors, f"Item {item_id} token source needs token_item_id")
                        _require(bool(token_source.get("token_name")), errors, f"Item {item_id} token source needs token_name")
                        _require(isinstance(token_source.get("token_count"), int) and token_source.get("token_count") > 0, errors, f"Item {item_id} token source needs token_count")
                        _require(bool(token_source.get("entity_name")) or token_source.get("world_drop") is True, errors, f"Item {item_id} token source needs entity_name or world_drop")
                        token_source_url = token_source.get("source_url")
                        if token_source_url:
                            _require(str(token_source_url).startswith("https://www.wowhead.com/tbc/"), errors, f"Item {item_id} token source URL must be a Wowhead TBC URL")
                        token_snapshot_url = token_source.get("token_source_url")
                        if token_snapshot_url:
                            _require(str(token_snapshot_url).startswith("https://www.wowhead.com/tbc/"), errors, f"Item {item_id} token snapshot URL must be a Wowhead TBC URL")
                for cost in source.get("costs", []):
                    _require(isinstance(cost.get("amount"), int) and cost.get("amount") >= 0, errors, f"Item {item_id} source cost needs a non-negative amount")
                    _require(bool(cost.get("name")), errors, f"Item {item_id} source cost needs a name")

    for list_row in bis_doc.get("lists", []):
        class_name = list_row.get("class")
        spec_name = list_row.get("spec")
        phase = list_row.get("phase")
        slot = list_row.get("slot")
        _require(class_name in class_names, errors, f"Unknown class in bis list: {class_name}")
        _require(spec_name in specs_by_class.get(class_name, set()), errors, f"Unknown spec in bis list: {class_name}/{spec_name}")
        _require(phase in PHASE_KEYS, errors, f"Unknown phase in bis list: {phase}")
        _require(slot in SLOT_NAMES, errors, f"Unknown slot in bis list: {slot}")
        _require(str(list_row.get("source_url", "")).startswith("https://www.wowhead.com/tbc/"), errors, f"Missing Wowhead source URL for {class_name}/{spec_name}/{phase}/{slot}")

        seen_item_contexts: set[tuple[int, str]] = set()
        for entry in list_row.get("items", []):
            item_id = entry.get("item_id")
            _require(item_id in item_ids, errors, f"BiS list references unknown item id: {item_id}")
            _require(bool(entry.get("rank_label")), errors, f"Item {item_id} is missing rank_label")
            _require(bool(entry.get("rank_group")), errors, f"Item {item_id} is missing rank_group")
            _require(bool(entry.get("context")), errors, f"Item {item_id} is missing context")
            item_context = (item_id, str(entry.get("context")))
            _require(item_context not in seen_item_contexts, errors, f"Duplicate BiS item/context in {class_name}/{spec_name}/{phase}/{slot}: {item_id}/{entry.get('context')}")
            seen_item_contexts.add(item_context)

    for gem in gems_doc.get("gems", []):
        class_name = gem.get("class")
        spec_name = gem.get("spec")
        phase = gem.get("phase")
        gem_id = gem.get("id")
        _require(class_name in class_names, errors, f"Unknown class in gem row: {class_name}")
        _require(spec_name in specs_by_class.get(class_name, set()), errors, f"Unknown spec in gem row: {class_name}/{spec_name}")
        _require(phase in PHASE_KEYS, errors, f"Unknown phase in gem row: {phase}")
        _require(isinstance(gem_id, int) and gem_id > 0, errors, f"Invalid gem id: {gem_id}")
        if "quality" in gem:
            _require(gem.get("quality") in {1, 2, 3, 4, 5}, errors, f"Gem {gem_id} has invalid quality: {gem.get('quality')}")
        if "meta" in gem:
            _require(isinstance(gem.get("meta"), bool), errors, f"Gem {gem_id} meta must be boolean")
        _require(str(gem.get("source_url", "")).startswith("https://www.wowhead.com/tbc/"), errors, f"Gem {gem_id} needs a Wowhead source URL")

    for enchant in enchants_doc.get("enchants", []):
        class_name = enchant.get("class")
        spec_name = enchant.get("spec")
        phase = enchant.get("phase")
        enchant_id = enchant.get("id")
        _require(class_name in class_names, errors, f"Unknown class in enchant row: {class_name}")
        _require(spec_name in specs_by_class.get(class_name, set()), errors, f"Unknown spec in enchant row: {class_name}/{spec_name}")
        _require(phase in PHASE_KEYS, errors, f"Unknown phase in enchant row: {phase}")
        _require(enchant.get("slot") in SLOT_NAMES, errors, f"Unknown enchant slot: {enchant.get('slot')}")
        _require(isinstance(enchant_id, int) and enchant_id > 0, errors, f"Invalid enchant id: {enchant_id}")
        _require(enchant.get("type") in {"item", "spell"}, errors, f"Enchant {enchant_id} has invalid type: {enchant.get('type')}")
        _require(str(enchant.get("source_url", "")).startswith("https://www.wowhead.com/tbc/"), errors, f"Enchant {enchant_id} needs a Wowhead source URL")

    for consumable in consumables_doc.get("consumables", []):
        class_name = consumable.get("class")
        spec_name = consumable.get("spec")
        _require(class_name in class_names, errors, f"Unknown class in consumable row: {class_name}")
        _require(spec_name in specs_by_class.get(class_name, set()), errors, f"Unknown spec in consumable row: {class_name}/{spec_name}")
        _require(bool(consumable.get("category")), errors, "Consumable row needs category")
        _require(isinstance(consumable.get("items"), list) and len(consumable.get("items", [])) > 0, errors, f"Consumable {consumable.get('category')} needs item ids")
        for item_id in consumable.get("items", []):
            _require(isinstance(item_id, int) and item_id > 0, errors, f"Invalid consumable item id: {item_id}")
        if consumable.get("phase"):
            _require(consumable.get("phase") in PHASE_KEYS, errors, f"Unknown consumable phase: {consumable.get('phase')}")
        _require(str(consumable.get("source_url", "")).startswith("https://www.wowhead.com/tbc/"), errors, f"Consumable {consumable.get('category')} needs a Wowhead source URL")

    for leveling in leveling_doc.get("leveling", []):
        class_name = leveling.get("class")
        spec_name = leveling.get("spec")
        _require(class_name in class_names, errors, f"Unknown class in leveling row: {class_name}")
        _require(spec_name in specs_by_class.get(class_name, set()), errors, f"Unknown spec in leveling row: {class_name}/{spec_name}")
        if leveling.get("phase"):
            _require(leveling.get("phase") in PHASE_KEYS, errors, f"Unknown leveling phase: {leveling.get('phase')}")
        _require(bool(leveling.get("section")), errors, "Leveling row needs section")
        _require(bool(leveling.get("text")), errors, "Leveling row needs text")
        _require(str(leveling.get("source_url", "")).startswith("https://www.wowhead.com/tbc/"), errors, f"Leveling row {leveling.get('section')} needs a Wowhead source URL")

    for source_doc_name, source_doc, rows_key in [
        ("gem_sources", gem_sources_doc, "gem_sources"),
        ("enchant_sources", enchant_sources_doc, "enchant_sources"),
    ]:
        seen_source_ids: set[tuple[str, int]] = set()
        for source_row in source_doc.get(rows_key, []):
            source_id = source_row.get("id")
            source_type = source_row.get("type", "item")
            _require(source_type in {"item", "spell"}, errors, f"{source_doc_name} {source_id} has invalid type: {source_type}")
            _require(isinstance(source_id, int) and source_id > 0, errors, f"{source_doc_name} row has invalid id: {source_id}")
            source_key = (str(source_type), int(source_id) if isinstance(source_id, int) else 0)
            _require(source_key not in seen_source_ids, errors, f"Duplicate {source_doc_name} source row: {source_type}/{source_id}")
            seen_source_ids.add(source_key)
            _require(bool(source_row.get("name")), errors, f"{source_doc_name} {source_id} needs name")
            _require(str(source_row.get("source_url", "")).startswith("https://www.wowhead.com/tbc/"), errors, f"{source_doc_name} {source_id} needs a Wowhead source URL")

    for source in manifest_doc.get("sources", []):
        _require(str(source.get("url", "")).startswith("https://www.wowhead.com/tbc/"), errors, "Manifest source URL must be a Wowhead TBC URL")
        _require(bool(source.get("status")), errors, f"Manifest source {source.get('url')} is missing status")
        _require(bool(source.get("id")), errors, f"Manifest source {source.get('url')} is missing id")
        families = source.get("data_families") if isinstance(source.get("data_families"), list) else [source.get("data_family")]
        families = [family for family in families if family]
        _require(bool(families), errors, f"Manifest source {source.get('url')} is missing data_family")
        for family in families:
            _require(family in STATIC_DATA_FAMILIES or family in {"items", "spells"}, errors, f"Manifest source {source.get('url')} has unknown data_family: {family}")
            if family in MATRIX_FAMILIES:
                _require(source.get("class") in class_names, errors, f"Manifest source {source.get('id')} has unknown class: {source.get('class')}")
                _require(source.get("spec") in specs_by_class.get(source.get("class"), set()), errors, f"Manifest source {source.get('id')} has unknown spec: {source.get('spec')}")
                _require(bool(units_covered_by_source({**source, "data_family": family})), errors, f"Manifest source {source.get('id')} covers no valid phases for {family}")
            if family in GLOBAL_FAMILIES:
                _require(bool(units_covered_by_source({**source, "data_family": family})), errors, f"Manifest source {source.get('id')} covers no global unit for {family}")

    for override in overrides_doc.get("overrides", []):
        override_id = override.get("id")
        _require(bool(override_id), errors, "Override is missing id")
        _require(bool(override.get("type")), errors, f"Override {override_id} is missing type")
        _require(bool(override.get("reason")), errors, f"Override {override_id} is missing reason")
        _require(bool(override.get("reviewer")), errors, f"Override {override_id} is missing reviewer")
        _require(bool(override.get("reviewed_at")), errors, f"Override {override_id} is missing reviewed_at")
        _require(str(override.get("source_url", "")).startswith("https://www.wowhead.com/tbc/"), errors, f"Override {override_id} source_url must be a Wowhead TBC URL")

    summary = {
        "classes": len(class_names),
        "specs": spec_count,
        "phases": len(phase_keys),
        "items": len(item_ids),
        "bis_lists": len(bis_doc.get("lists", [])),
        "consumables": len(consumables_doc.get("consumables", [])),
        "enchant_sources": len(enchant_sources_doc.get("enchant_sources", [])),
        "enchants": len(enchants_doc.get("enchants", [])),
        "gem_sources": len(gem_sources_doc.get("gem_sources", [])),
        "gems": len(gems_doc.get("gems", [])),
        "leveling": len(leveling_doc.get("leveling", [])),
        "overrides": len(overrides_doc.get("overrides", [])),
        "coverage": str(bis_doc.get("coverage", "")),
    }
    return ValidationResult(not errors, errors, summary)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Big BiS List canonical JSON.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable output.")
    args = parser.parse_args(argv)

    result = validate()
    payload = {"ok": result.ok, "errors": result.errors, "summary": result.summary}

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif result.ok:
        print("Canonical data is valid.")
        print(json.dumps(result.summary, indent=2, sort_keys=True))
    else:
        print("Canonical data validation failed:", file=sys.stderr)
        for error in result.errors:
            print(f"- {error}", file=sys.stderr)

    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
