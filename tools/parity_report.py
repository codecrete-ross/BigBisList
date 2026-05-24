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


def build_report(reference_dir: Path = REFERENCE_DIR) -> dict:
    reference = collect_counts(reference_dir)
    canonical = canonical_counts()
    return {
        "status": "gear_bis_scraped_non_gear_pending",
        "reference": reference,
        "canonical": canonical,
        "notes": [
            "Reference counts are the full BIS-TBC 1.15 addon baseline.",
            "Canonical gear BiS is scraped from Wowhead; gems, enchants, consumables, and leveling are still pending.",
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
