from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.project import REFERENCE_DIR, canonical_json
from tools.reference_counts import collect_counts


def canonical_counts() -> dict[str, int | str]:
    classes = canonical_json("classes")["classes"]
    bis_lists = canonical_json("bis_lists")
    items = canonical_json("items")["items"]
    gems = canonical_json("gems")["gems"]
    enchants = canonical_json("enchants")["enchants"]
    consumables = canonical_json("consumables")["consumables"]
    leveling = canonical_json("leveling")["leveling"]
    return {
        "coverage": bis_lists["coverage"],
        "classes": len(classes),
        "specs": sum(len(class_data["specs"]) for class_data in classes),
        "items": len(items),
        "bis_slot_lists": len(bis_lists["lists"]),
        "bis_item_refs": sum(len(row["items"]) for row in bis_lists["lists"]),
        "gem_rows": len(gems),
        "enchant_rows": len(enchants),
        "consumable_rows": len(consumables),
        "leveling_rows": len(leveling),
    }


def family_status(row_count: int, expected_units_missing: int | None = None) -> str:
    if expected_units_missing is not None and expected_units_missing > 0:
        return "manifest_pending"
    if row_count == 0:
        return "scrape_pending"
    return "scraped_snapshot"


def family_report(reference: dict, canonical: dict) -> dict[str, dict[str, int | str | None]]:
    return {
        "bis_lists": {
            "status": str(canonical["coverage"]),
            "canonical_rows": int(canonical["bis_slot_lists"]),
            "canonical_refs": int(canonical["bis_item_refs"]),
            "reference_rows": None,
            "reference_delta": None,
        },
        "gems": {
            "status": family_status(int(canonical["gem_rows"])),
            "canonical_rows": int(canonical["gem_rows"]),
            "reference_rows": int(reference.get("gem_rows", 0) or 0),
            "reference_delta": int(canonical["gem_rows"]) - int(reference.get("gem_rows", 0) or 0),
        },
        "enchants": {
            "status": family_status(int(canonical["enchant_rows"])),
            "canonical_rows": int(canonical["enchant_rows"]),
            "reference_rows": int(reference.get("enchant_rows", 0) or 0),
            "reference_delta": int(canonical["enchant_rows"]) - int(reference.get("enchant_rows", 0) or 0),
        },
        "consumables": {
            "status": family_status(int(canonical["consumable_rows"])),
            "canonical_rows": int(canonical["consumable_rows"]),
            "reference_rows": int(reference.get("consumable_rows", 0) or 0),
            "reference_delta": int(canonical["consumable_rows"]) - int(reference.get("consumable_rows", 0) or 0),
        },
        "leveling": {
            "status": family_status(int(canonical["leveling_rows"])),
            "canonical_rows": int(canonical["leveling_rows"]),
            "reference_rows": None,
            "reference_delta": None,
        },
        "classes": {
            "status": "canonical_static",
            "canonical_rows": int(canonical["classes"]),
            "reference_rows": int(reference.get("classes", 0) or 0),
            "reference_delta": int(canonical["classes"]) - int(reference.get("classes", 0) or 0),
        },
        "phases": {
            "status": "canonical_static",
            "canonical_rows": 6,
            "reference_rows": int(reference.get("phases", 0) or 0),
            "reference_delta": 6 - int(reference.get("phases", 0) or 0),
        },
    }


def build_report(reference_dir: Path = REFERENCE_DIR) -> dict:
    reference = collect_counts(reference_dir)
    canonical = canonical_counts()
    return {
        "status": "per_family",
        "families": family_report(reference, canonical),
        "reference": reference,
        "canonical": canonical,
        "notes": [
            "Reference counts are the full BIS-TBC 1.15 addon baseline.",
            "Reference parity is an audit signal only; Wowhead guide rankings and reviewed overrides remain canonical.",
            "Each data family reports its own completion state so non-gear progress is not hidden behind gear BiS status.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare canonical scraped data to the reference baseline.")
    parser.add_argument("--reference-dir", type=Path, default=REFERENCE_DIR)
    args = parser.parse_args(argv)
    print(json.dumps(build_report(args.reference_dir), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
