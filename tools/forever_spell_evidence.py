"""Review exact item-effect references against a build-pinned client export."""

from __future__ import annotations

import argparse
from collections import defaultdict
import csv
from hashlib import sha256
import json
from pathlib import Path
import re
from urllib.request import urlopen

from tools.forever_item_effects import resolve_spell_leads, set_catalog
from tools.forever_effect_benchmarks import missing_reason
from tools.project import FOREVER_CANONICAL_DIR, dataset_json, load_json, write_text


SPELL_LINK = re.compile(r"(?:equip|use|chance on hit): (\d+) .+", re.I)
SPELL_EXPORT = "https://www.everlookdb.com/downloads/spells.json"
SET_EXPORT = "https://wago.tools/db2/{table}/csv?build={build}"


def item_links(catalog: dict) -> dict[str, set[int]]:
    links = defaultdict(set)
    for row in resolve_spell_leads(catalog["items"], set_catalog(catalog)[1]).values():
        for lead in row.get("missing_effects", []):
            links[lead].add(row["id"])
    return links


def signature(value) -> str:
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def compare(catalog: dict, evidence: dict) -> dict:
    """New references and changed item-to-spell associations require review."""
    links = item_links(catalog)
    reviewed = evidence["references"]
    return {
        "reviewed_references": len(reviewed),
        "new_references": sorted(links.keys() - reviewed.keys()),
        "changed_associations": sorted(lead for lead in links.keys() & reviewed.keys()
                                       if links[lead] - set(reviewed[lead]["items"])),
    }


def audit_exports(catalog: dict, evidence: dict, refreshed: dict) -> dict:
    report = compare(catalog, evidence)
    prior, current = evidence["references"], refreshed["references"]
    report["changed_sources"] = sorted(lead for lead in prior.keys() & current.keys()
                                       if prior[lead].get("digest") != current[lead].get("digest"))
    return report


def audit(root: Path, *, online: bool = False) -> dict:
    directory = root / "data" / "canonical" / "forever"
    evidence = load_json(directory / "spell_effect_review.json")
    catalog = load_json(directory / "comparison_item_stats.json")
    if not online:
        return compare(catalog, evidence)
    with urlopen(SPELL_EXPORT, timeout=25) as response:
        spells = json.load(response)
    tables = []
    for table in ("ItemSet", "ItemSetSpell"):
        with urlopen(SET_EXPORT.format(table=table, build=evidence["build"]), timeout=25) as response:
            tables.append(list(csv.DictReader(response.read().decode("utf-8-sig").splitlines())))
    build = load_json(directory / "reviewed_builds.json")["target_client"]
    refreshed = review_exports(catalog, spells, tables[0], tables[1], {}, build=build)
    return audit_exports(catalog, evidence, refreshed)


def review_exports(catalog: dict, spells: dict, sets: list[dict], bonuses: list[dict], previous: dict, *, build: str) -> dict:
    if spells.get("build") != build or spells.get("table") != "spells":
        raise ValueError(f"Expected the spell export for Forever {build}")
    by_spell = {row["id"]: row for row in spells["data"]}
    by_name, by_set = defaultdict(list), defaultdict(list)
    for row in sets:
        by_name[row["Name_lang"]].append(row)
    for row in bonuses:
        by_set[row["ItemSetID"]].append(row)
    references = {}
    for lead, items in sorted(item_links(catalog).items()):
        entry = references[lead] = {"items": sorted(items)}
        if match := SPELL_LINK.fullmatch(lead):
            spell_id = int(match[1])
            spell = by_spell.get(spell_id)
            entry["spell"] = spell_id
            entry["gap"] = "Spell absent from client export"
            if spell:
                description = " ".join(spell["description"].split())
                entry["source"] = spell["url"]
                entry["digest"] = signature([description, spell["duration_ms"], spell["cooldown_ms"]])
                prefix = lead.split(":", 1)[0].capitalize()
                entry["gap"] = (missing_reason(f"{prefix}: {description}") if description
                                else "Spell has no description in the client export")
        elif lead.startswith("Set: "):
            matching = []
            for row in by_name[lead[5:]]:
                members = {int(value) for name, value in row.items() if name.startswith("ItemID_") and int(value)}
                if members & items:
                    matching.append((int(row["ID"]), sorted(members), by_set[row["ID"]]))
            matching.sort()
            entry["sets"] = [row[0] for row in matching]
            entry["digest"] = signature(matching)
            entry["gap"] = ("Set pieces matched; confirm bonus eligibility and effect for each threshold" if matching
                            else "Set name did not match the recorded item IDs")
        else:
            entry["gap"] = "No exact client spell or set link"
    for lead, rule in previous.get("rules", {}).items():
        old = previous.get("references", {}).get(lead, {})
        if lead in references and old.get("digest") == references[lead].get("digest"):
            references[lead].pop("gap", None)
        elif lead in references and old:
            raise ValueError(f"Re-review changed client evidence before carrying forward the rule for {lead}")
    return {"build": build, "spell_export": SPELL_EXPORT,
            "set_exports": [SET_EXPORT.format(table=table, build=build) for table in ("ItemSet", "ItemSetSpell")],
            "references": references, "rules": previous.get("rules", {})}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spells", type=Path)
    parser.add_argument("sets", type=Path)
    parser.add_argument("bonuses", type=Path)
    args = parser.parse_args()
    output = FOREVER_CANONICAL_DIR / "spell_effect_review.json"
    build = load_json(FOREVER_CANONICAL_DIR / "reviewed_builds.json")["target_client"]
    previous = json.loads(output.read_text(encoding="utf-8")) if output.exists() else {}
    with args.sets.open(encoding="utf-8", newline="") as sets, args.bonuses.open(encoding="utf-8", newline="") as bonuses:
        result = review_exports(dataset_json("forever", "comparison_item_stats"),
                                json.loads(args.spells.read_text(encoding="utf-8")),
                                list(csv.DictReader(sets)), list(csv.DictReader(bonuses)), previous, build=build)
    write_text(output, json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
