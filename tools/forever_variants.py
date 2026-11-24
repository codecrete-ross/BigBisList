"""Audit Forever rolls against build-pinned client bonus trees without importing them."""

from __future__ import annotations

from collections import Counter, defaultdict
import csv
from hashlib import sha256
from pathlib import Path
import re

from tools.project import dataset_json
from tools.recommend_leveling import roll_identity


def linked_rolls(directory: Path, build: str) -> tuple[dict, dict]:
    if not re.fullmatch(r"1\.60\.\d+\.\d+", build or ""):
        raise ValueError("Provide the Forever client build for the captured bonus tables")
    sources = {}

    def table(name: str) -> list[dict]:
        path = directory / f"{name}.csv"
        sources[name] = {"sha256": sha256(path.read_bytes()).hexdigest(),
                         "url": f"https://wago.tools/db2/{name}/csv?build={build}"}
        with path.open(encoding="utf-8-sig", newline="") as file:
            return list(csv.DictReader(file))

    descriptions = {int(row["ID"]): row["Description_lang"] for row in table("ItemNameDescription")}
    names, modifiers = {}, defaultdict(list)
    for row in table("ItemBonus"):
        bonus = int(row["ParentItemBonusListID"])
        if row["Type"] == "5" and (name := descriptions.get(int(row["Value_0"]), "")).startswith("of "):
            names[bonus] = name
        if row["Type"] == "2":
            modifiers[bonus].append(int(row["Value_0"]))
    nodes = defaultdict(list)
    for row in table("ItemBonusTreeNode"):
        nodes[int(row["ParentItemBonusTreeID"])].append(row)

    def walk(tree: int) -> tuple[set[int], bool]:
        visited, bonuses = set(), set()
        pending, indirect = [tree], False
        while pending:
            node = pending.pop()
            if node in visited:
                continue
            visited.add(node)
            for row in nodes[node]:
                child = int(row["ChildItemBonusTreeID"])
                if child:
                    pending.append(child)
                bonus = int(row["ChildItemBonusListID"])
                if bonus in names and bonus in modifiers:
                    bonuses.add(bonus)
                indirect |= any(int(row[key]) != 0 for key in ("ChildItemBonusListGroupID", "ChildItemLevelSelectorID"))
        return bonuses, indirect

    attached, trees = {}, {}
    for row in table("ItemXBonusTree"):
        tree, identifier = int(row["ItemBonusTreeID"]), int(row["ItemID"])
        if tree not in trees:
            trees[tree] = walk(tree)
        bonuses, indirect = trees[tree]
        if bonuses or indirect:
            family = attached.setdefault(identifier, {"lists": {}, "indirect_scaling": False})
            family["lists"].update({bonus: names[bonus] for bonus in sorted(bonuses)})
            family["indirect_scaling"] |= indirect
    return attached, sources


def suffix_audit(directory: Path | None = None, build: str | None = None) -> dict:
    known = {row["id"]: row for row in dataset_json("forever", "comparison_item_stats")["items"]
             if row.get("has_random_stats")}
    published = defaultdict(list)
    for row in dataset_json("forever", "item_variants")["item_variants"]:
        identity, _ = roll_identity(row)
        published[row["item_id"]].append({"variant": identity, "build": row["client_build"],
                                          "bonus_fields": row.get("bonus_fields", [])})
    attached, sources = linked_rolls(directory, build) if directory else ({}, {})
    families = []
    for identifier in sorted(known.keys() | published.keys() | attached.keys()):
        name = known.get(identifier, {}).get("name")
        family = attached.get(identifier, {"lists": {}, "indirect_scaling": False})
        verified = {roll["bonus_fields"][3] for roll in published[identifier] if roll["build"] == build
                    and roll["bonus_fields"][2:3] == [1]}
        candidates = [{"bonus": bonus, "suffix": suffix,
                       "status": "observed_exact_roll" if bonus in verified else "needs_exact_stats_and_link"}
                      for bonus, suffix in sorted(family["lists"].items())]
        pending = family["indirect_scaling"] or any(row["status"] == "needs_exact_stats_and_link" for row in candidates)
        status = "unresolved"
        if published[identifier]:
            status = "partial" if pending else "observed"
        families.append({"item_id": identifier, "name": name, "comparison_base": identifier in known, "status": status,
                         "indirect_scaling": family["indirect_scaling"], "client_candidates": candidates,
                         "reviewed_rolls": sorted(published[identifier], key=lambda row: row["variant"])})
    return {"ok": True, "client_build": build, "sources": sources, "known_random_bases": len(known),
            "matched_random_bases": sum(bool(attached.get(identifier, {}).get("lists")) for identifier in known),
            "reviewed_rolls": sum(map(len, published.values())),
            "status_counts": dict(Counter(row["status"] for row in families)), "families": families}
