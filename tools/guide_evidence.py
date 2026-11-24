"""Conservative comparison evidence from committed guide tables.

The legacy ``rank`` is a source row position, not a strength measurement.  This
module adds evidence without changing recommendation membership or wording.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import sys

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.project import CANONICAL_DIR, PHASE_KEYS, RAW_WOWHEAD_DIR, canonical_json, write_text


GENERIC_GRADES = {
    "best": 1, "bis": 1, "best in slot": 1, "best-in-slot": 1,
    "great": 2, "good": 3, "mediocre": 4,
}
SETUP_HEADING = re.compile(
    r"\b(?:hit[- ]capped|threat|mitigation|avoidance|survivability|stamina|"
    r"personal dps|raid dps|set bonus|[246][ -]?(?:piece|pc)|"
    r"aldor|scryer|pvp|arena|resilience)\b", re.IGNORECASE)


def normalized_label(label: str) -> str:
    return " ".join(label.split()).casefold()


def rating_phase_from_label(label: str, guide_phase: str,
                            definitions: dict, terminology: str) -> str | None:
    """Recognize a rating's phase prefix, not a condition such as 'until T6'."""
    phase_prefix = re.match(r"^\s*(?:p(?:hase)?\s*)(\d+(?:\.\d+)?)\b", label, re.I)
    tier_prefix = re.match(r"^\s*(?:t(?:ier)?\s*)([456])\b", label, re.I)
    if phase_prefix:
        return definitions.get("source_phase_numbers", {}).get(terminology, {}).get(phase_prefix[1])
    if tier_prefix:
        return "T" + tier_prefix[1]
    if re.match(r"^\s*(?:best|bis)\s+pre[- ]raid\b", label, re.I):
        return "PR"
    return guide_phase


def table_evidence(snapshot: dict, table: dict, table_index: int, row: dict,
                   guide_phase: str, slot: str, *, terminology: str = "wowhead_classic",
                   definitions: dict | None = None) -> dict:
    definitions = canonical_json("phases") if definitions is None else definitions
    label = str(row.get("rank_label") or "Option")
    heading = str(table.get("heading") or "")
    content_phase = snapshot.get("content_phase", "PR") if guide_phase == "PR" else None
    # The occurrence distinguishes separate tables with identical headings. The
    # content fingerprint also prevents unrelated revisions sharing a group.
    identity = [snapshot.get("url"), guide_phase, content_phase, slot, table_index, table]
    fingerprint = hashlib.sha256(json.dumps(identity, sort_keys=True, ensure_ascii=False,
                                            separators=(",", ":")).encode("utf-8")).hexdigest()[:24]
    grade = GENERIC_GRADES.get(normalized_label(label))
    conditions = []
    if grade is None:
        conditions.append(label)
    if SETUP_HEADING.search(heading):
        conditions.append(heading)
        grade = None
    evidence = {
        "table_id": "guide:" + fingerprint,
        "guide_phase": guide_phase,
        "original_rating": label,
        "conditions": conditions,
        "source_url": snapshot.get("url", ""),
        "table_heading": heading,
    }
    rating_phase = rating_phase_from_label(label, guide_phase, definitions, terminology)
    if rating_phase is not None:
        evidence["rating_phase"] = rating_phase
    if grade is not None:
        evidence["grade"] = grade
    if content_phase is not None:
        evidence["content_phase"] = content_phase
    return evidence


def evidence_key(list_row: dict, item: dict, content_phase: str | None = None) -> tuple:
    return (list_row.get("class"), list_row.get("spec"), list_row.get("phase"),
            content_phase if list_row.get("phase") == "PR" else None,
            list_row.get("slot"), list_row.get("source_url"), item.get("item_id"),
            item.get("rank_label") or "Option")


def apply_recommendation_context(evidence: dict, item: dict) -> dict:
    """Reviewed setup variants remain conditional even if the raw cell says BiS."""
    result = deepcopy(evidence)
    context = item.get("context", "standard")
    if result.get("grade") is not None and context not in {"standard", "option"}:
        result.pop("grade")
        result["conditions"].append(item.get("note") or str(context).replace("_", " "))
    return result


def evidence_index(snapshots: list[dict]) -> dict[tuple, list[dict]]:
    # Import lazily: the importer also uses table_evidence during normal imports.
    from tools.scrape_wowhead import (bis_slot_from_row, item_snapshots_by_id,
                                      manifest_sources_for_snapshot, phase_from_row,
                                      select_pre_raid_snapshots)
    indexed = defaultdict(dict)
    item_snapshots = item_snapshots_by_id(snapshots)
    definitions = canonical_json("phases")
    for snapshot in select_pre_raid_snapshots(snapshots):
        if snapshot.get("page_type") != "guide" or snapshot.get("recommendation_status") in {
                "no_distinct_update", "unverified_phase"}:
            continue
        for source in manifest_sources_for_snapshot(snapshot, "bis_lists"):
            for table_index, table in enumerate(snapshot.get("tables", []), start=1):
                if table.get("data_family") not in (None, "bis_lists", "unknown"):
                    continue
                for row in table.get("rows", []):
                    phase = phase_from_row(source, table, row)
                    item_id = row.get("item_id")
                    if not phase or not item_id:
                        continue
                    slot = bis_slot_from_row(table, row, item_snapshots.get(item_id))
                    if not slot:
                        continue
                    evidence = table_evidence(snapshot, table, table_index, row, phase, slot,
                                              definitions=definitions,
                                              terminology=source.get("content_terminology", "wowhead_classic"))
                    list_row = {"class": source.get("class"), "spec": source.get("spec"),
                                "phase": phase, "slot": slot, "source_url": snapshot["url"]}
                    key = evidence_key(list_row, row, evidence.get("content_phase"))
                    indexed[key][json.dumps(evidence, sort_keys=True)] = evidence
    return {key: [entries[value] for value in sorted(entries)] for key, entries in indexed.items()}


def enrich_document(document: dict, snapshots: list[dict]) -> tuple[dict, dict]:
    """Replace only evidence; exact label/source matches preserve ambiguity."""
    result = deepcopy(document)
    indexed = evidence_index(snapshots)
    counts = Counter()
    for list_row in result.get("lists", []):
        # A copied Pre-Raid path still cites its verified historical source. It
        # must not become fresh comparison evidence for the inherited phase.
        content_phase = list_row.get("inherited_from_phase", list_row.get("content_phase", "PR"))
        for item in list_row.get("items", []):
            counts["recommendations"] += 1
            matches = indexed.get(evidence_key(list_row, item, content_phase), [])
            item.pop("guide_evidence", None)
            if matches:
                item["guide_evidence"] = [apply_recommendation_context(e, item) for e in matches]
                counts["with_evidence"] += 1
                counts["evidence_records"] += len(matches)
                counts["with_grade"] += any(e.get("grade") is not None for e in item["guide_evidence"])
                counts["multiple_matches"] += len(matches) > 1
            else:
                counts["unresolved"] += 1
    return result, dict(sorted(counts.items()))


def validate_evidence(evidence: object, label: str, source_url: str, context: str = "standard") -> list[str]:
    if not isinstance(evidence, list) or not evidence:
        return ["guide_evidence must be a nonempty array when present"]
    errors = []
    seen = set()
    for entry in evidence:
        if not isinstance(entry, dict):
            errors.append("guide evidence must be an object")
            continue
        fingerprint = json.dumps(entry, sort_keys=True)
        if fingerprint in seen:
            errors.append("duplicate guide evidence")
        seen.add(fingerprint)
        if not re.fullmatch(r"guide:[a-f0-9]{24}", str(entry.get("table_id", ""))):
            errors.append("guide evidence has invalid table identity")
        if entry.get("guide_phase") not in PHASE_KEYS:
            errors.append("guide evidence has invalid guide phase")
        if "rating_phase" in entry and entry["rating_phase"] not in PHASE_KEYS:
            errors.append("guide evidence has invalid rating phase")
        if entry.get("original_rating") != label:
            errors.append("guide evidence must retain the exact recommendation label")
        if entry.get("source_url") != source_url:
            errors.append("guide evidence must retain the recommendation source")
        conditions = entry.get("conditions")
        if not isinstance(conditions, list) or any(not isinstance(c, str) or not c for c in conditions):
            errors.append("guide evidence conditions must be an array of nonempty strings")
        grade = entry.get("grade")
        if grade is not None:
            if type(grade) is not int or grade != GENERIC_GRADES.get(normalized_label(label)):
                errors.append("guide evidence grade is not an explicit generic source rating")
            if conditions or entry.get("rating_phase") != entry.get("guide_phase"):
                errors.append("conditional or historical guide evidence cannot have a comparison grade")
            if context not in {"standard", "option"}:
                errors.append("setup-specific recommendations cannot have an unconditional comparison grade")
        if entry.get("guide_phase") == "PR":
            if entry.get("content_phase") not in PHASE_KEYS:
                errors.append("Pre-Raid guide evidence requires its verified content phase")
        elif "content_phase" in entry:
            errors.append("only Pre-Raid guide evidence has a separate content phase")
    return errors


def committed_guide_snapshots() -> list[dict]:
    # The full_bis family includes its immutable historical Pre-Raid snapshots.
    # Avoid other families' duplicate/partial copies of the same guide URL.
    snapshots = []
    for path in sorted((RAW_WOWHEAD_DIR / "full_bis").glob("*.json")):
        snapshot = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(snapshot, dict) and snapshot.get("page_type") in {"guide", "item"}:
            snapshots.append(snapshot)
    return snapshots


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="Add evidence to existing canonical recommendations.")
    mode.add_argument("--check", action="store_true", help="Check canonical evidence against committed snapshots.")
    args = parser.parse_args(argv)
    original = canonical_json("bis_lists")
    enriched, counts = enrich_document(original, committed_guide_snapshots())
    print(json.dumps(counts, indent=2, sort_keys=True))
    if args.check:
        if original != enriched:
            print("Canonical guide evidence is not up to date.", file=sys.stderr)
            return 1
    elif args.write:
        write_text(CANONICAL_DIR / "bis_lists.json", json.dumps(enriched, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
