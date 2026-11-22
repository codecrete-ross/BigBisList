"""Compare the reviewed 0.15 leveling gaps with the current Forever evidence."""
from __future__ import annotations

import json
import re

from tools import forever_release as release
from tools.project import ROOT


# This commit contains the full reviewed per-character coverage and candidate evidence.
REVIEWED = "5693519f0e32cd5090ba08b2b2325f5544b82e31"


def gap_rows(rows):
    dimensions = ("class", "spec", "race_id", "faction", "slot", "level_min", "level_max", "status")
    return [
        {**{key: row[key] for key in dimensions}, "items": row.get("availability", {}).get("unresolved_item_ids", [])}
        for row in rows if row["status"] != "approved"
    ]


def cells(rows):
    covered = {}
    for row in rows:
        items = set(row["items"])
        for level in range(row["level_min"], row["level_max"] + 1):
            key = row["class"], row["spec"], row["race_id"], row["faction"], row["slot"], level, row["status"]
            covered[key] = items
    return covered


def reasons(rows):
    fields = ("status", "candidate_digest", "missing_fact", "next_evidence_trigger", "pending_facts",
              "disclosure_observations", "route_leads", "tooltip_urls")
    return {row["item_id"]: tuple(row.get(key) for key in fields)
            for row in rows if row["status"].startswith(("pending_", "missing_"))}


def compare(current, allowed):
    gaps, candidates = current
    known, reviewed_candidates = allowed
    return {
        "new_or_reopened_cells": sum(key not in known or not items <= known[key] for key, items in gaps.items()),
        "new_or_changed_candidates": sorted(item for item, why in candidates.items() if reviewed_candidates.get(item) != why),
    }


def recorded(root, ref):
    def read(name):
        return json.loads(release.blob(root, ref, release.CANONICAL + name + ".json"))
    return (cells(gap_rows(read("leveling_audit")["rows"])), reasons(read("leveling_candidate_audit")["candidate_reviews"]))


def evaluate(version, rows, candidates, summary, *, previous=None, root=ROOT):
    current = cells(rows), reasons(candidates)
    result = {"ok": False, "version": version, "uncovered": len(current[0]), "pending_items": len(current[1])}
    if (not re.fullmatch(r"0\.15\.(0|[1-9]\d*)", version)
            or not summary.get("reviewed_rules") or not summary.get("availability_inventory_complete")
            or summary.get("review_issues") != 0 or summary.get("pending_ranking_combinations") != 0
            or len(current[0]) != summary.get("uncovered_combinations")
            or len(current[1]) != summary.get("availability_pending_candidates")):
        return result
    refs = [REVIEWED]
    patch = int(version.split(".")[-1])
    if patch:
        refs.append(release.tag_commit(root, f"0.15.{patch - 1}"))
    if previous is not None:
        refs.append(previous)
    comparisons = {ref: compare(current, recorded(root, ref)) for ref in dict.fromkeys(refs)}
    return {**result, "ok": all(not any(review.values()) for review in comparisons.values()), "comparisons": comparisons}
