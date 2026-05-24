from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.project import PHASE_KEYS, REFERENCE_DIR, read_text

EXPECTED_BASELINE = {
    "classes": 9,
    "specs": 28,
    "phases": 6,
    "tooltip_items": 1836,
    "source_rows": 2163,
}


def _count_lines(path: Path, prefix: str) -> int:
    if not path.is_file():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8", errors="ignore").splitlines() if line.startswith(prefix))


def collect_counts(reference_dir: Path = REFERENCE_DIR) -> dict[str, int | str | bool]:
    toc_path = reference_dir / "BIS-TBC.toc"
    classes_path = reference_dir / "BIS-TBC_classes.lua"
    bislists_path = reference_dir / "BIS-TBC_bislists.lua"

    if not reference_dir.is_dir():
        return {
            "reference_dir": str(reference_dir),
            "available": False,
            "error": "reference directory not found",
        }

    classes_text = read_text(classes_path) if classes_path.is_file() else ""
    bislists_text = read_text(bislists_path) if bislists_path.is_file() else ""
    toc_text = read_text(toc_path) if toc_path.is_file() else ""

    phases = sorted(set(re.findall(r'\]\["(PR|T4|T5|T6|ZA|SWP)"\]\s*=\s*\{\};', bislists_text)), key=PHASE_KEYS.index)
    toc_version_match = re.search(r"^## Version:\s*(.+)$", toc_text, flags=re.MULTILINE)

    return {
        "reference_dir": str(reference_dir),
        "available": True,
        "toc_version": toc_version_match.group(1).strip() if toc_version_match else "",
        "classes": len(re.findall(r"^BISTBC_classes\[\d+\]\s*=", classes_text, flags=re.MULTILINE)),
        "specs": len(re.findall(r'^\s+\[\d+\]\s*=\s*"[^"]+"', classes_text, flags=re.MULTILINE)),
        "phases": len(phases),
        "tooltip_items": _count_lines(reference_dir / "BIS-TBC_items.lua", "BISTBC_items["),
        "source_rows": _count_lines(reference_dir / "BIS-TBC_sources.lua", "BISTBC_sources["),
        "gem_rows": len(re.findall(r"\[\d+\]\s*=\s*\{\s*id\s*=", read_text(reference_dir / "BIS-TBC_gems.lua") if (reference_dir / "BIS-TBC_gems.lua").is_file() else "")),
        "enchant_rows": len(re.findall(r"\[\d+\]\s*=\s*\{\s*id\s*=", read_text(reference_dir / "BIS-TBC_enchants.lua") if (reference_dir / "BIS-TBC_enchants.lua").is_file() else "")),
        "consumable_rows": len(re.findall(r"\[\d+\]\s*=\s*\{\s*category\s*=", read_text(reference_dir / "BIS-TBC_consumables.lua") if (reference_dir / "BIS-TBC_consumables.lua").is_file() else "")),
    }


def baseline_matches(counts: dict[str, int | str | bool]) -> bool:
    return all(counts.get(key) == value for key, value in EXPECTED_BASELINE.items())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect counts from the BIS-TBC 1.15 reference addon.")
    parser.add_argument("--reference-dir", type=Path, default=REFERENCE_DIR)
    parser.add_argument("--strict", action="store_true", help="Fail if key baseline counts do not match.")
    args = parser.parse_args(argv)

    counts = collect_counts(args.reference_dir)
    print(json.dumps(counts, indent=2, sort_keys=True))

    if not counts.get("available"):
        return 1 if args.strict else 0
    if args.strict and not baseline_matches(counts):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

