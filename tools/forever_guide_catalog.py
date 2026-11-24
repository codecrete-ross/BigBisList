"""Normalize the independent equipment inventory and build-pinned random properties."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from collections import defaultdict
from pathlib import Path

from tools.forever_availability import CLASS_BITS
from tools.forever_variants import linked_rolls
from tools.project import ROOT, dataset_json


# InventoryType, Guide slot, random-property budget column.
LOCATIONS = {
    "HEAD": (1, "Head", 0), "NECK": (2, "Neck", 2), "SHOULDER": (3, "Shoulder", 1),
    "CHEST": (5, "Chest", 0), "WAIST": (6, "Waist", 1), "LEGS": (7, "Legs", 0),
    "FEET": (8, "Feet", 1), "WRIST": (9, "Wrist", 2), "HAND": (10, "Hands", 1),
    "FINGER": (11, "Ring", 2), "TRINKET": (12, "Trinket", 1), "WEAPON": (13, "One Hand", 3),
    "SHIELD": (14, "Off Hand", 2), "RANGED": (15, "Ranged", 0), "CLOAK": (16, "Back", 2),
    "TWOHWEAPON": (17, "Two Hand", 0), "ROBE": (20, "Chest", 0), "WEAPONMAINHAND": (21, "Main Hand", 3),
    "WEAPONOFFHAND": (22, "Off Hand", 3), "HOLDABLE": (23, "Off Hand", 2), "THROWN": (25, "Ranged", 3),
    "RANGEDRIGHT": (26, "Ranged", 0), "RELIC": (28, "Relic", 4),
}
STATS = {3: "agility", 4: "strength", 5: "intellect", 6: "spirit", 7: "stamina", 12: "defense",
         38: "attack_power", 41: "healing_power", 42: "spell_damage", 43: "mp5", 45: "spell_power", 46: "hp5",
         51: "fire_resistance", 52: "frost_resistance", 54: "shadow_resistance", 55: "nature_resistance",
         56: "arcane_resistance", 84: "holy_damage", 85: "fire_damage", 86: "nature_damage",
         87: "frost_damage", 88: "shadow_damage", 89: "arcane_damage"}
ARMOR = {"Cloth": "Cloth", "Leather": "Leather", "Mail": "Chain", "Plate": "Plate"}
QUALITY = {"POOR": 0, "COMMON": 1, "UNCOMMON": 2, "RARE": 3, "EPIC": 4, "LEGENDARY": 5}
RACE_BITS = {race: race - 1 for race in range(1, 9)}
NON_PLAYER = re.compile(r"^(?:Monster\s*[-–]|Deprecated|Obsolete|TEST\b|PH\b|QA\b|zzOLD)|\b(?:UNUSED|NYI|Not Yet Implemented)\b", re.I)
FIELDS = ("id", "name", "slot", "level", "armor_type", "weapon_subtype", "classes", "race_ids",
          "quality", "group", "budget", "armor", "roll_complete")


def compile_catalog(directory: Path, build: str) -> dict:
    attached, sources = linked_rolls(directory, build)

    def table(name):
        path = directory / (name + ".csv")
        sources[name] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                         "url": f"https://wago.tools/db2/{name}/csv?build={build}"}
        with path.open(encoding="utf-8-sig", newline="") as file:
            return list(csv.DictReader(file))

    names = {bonus: name for family in attached.values() for bonus, name in family["lists"].items()}
    fractions, unsupported = defaultdict(dict), set()
    for row in table("ItemBonus"):
        bonus = int(row["ParentItemBonusListID"])
        if bonus not in names:
            continue
        if row["Type"] == "2" and int(row["Value_0"]) in STATS and not int(row["Value_2"]) and not int(row["Value_3"]):
            stat = STATS[int(row["Value_0"])]
            fractions[bonus][stat] = fractions[bonus].get(stat, 0) + int(row["Value_1"])
        elif row["Type"] != "5":
            unsupported.add(bonus)
    templates = {str(key): [name, fractions[key] if key not in unsupported else None] for key, name in sorted(names.items())}
    budgets, totals, qualities, locations = ({int(x["ID"]): x for x in table(name)}
                                            for name in ("RandPropPoints", "ItemArmorTotal", "ItemArmorQuality", "ArmorLocation"))
    sparse = {int(x["ID"]): x for x in table("ItemSparse")}
    mask_path, = (ROOT / "data/raw/forever/questiedb").glob("*docs-api-md-*.json")
    mask_doc = json.loads(mask_path.read_text(encoding="utf-8"))
    sources[mask_path.stem] = {"sha256": hashlib.sha256(mask_path.read_bytes()).hexdigest(), "url": mask_doc["url"]}
    race_bits = {**RACE_BITS, **{row["race_id"]: row["bit"] for row in mask_doc["race_masks"]}}
    audit = dataset_json("forever", "leveling_candidate_audit")
    excluded = {x["item_id"] for x in audit["candidate_reviews"] if x["status"] in
                {"reviewed_cosmetic_exclusion", "reviewed_non_gearing_exclusion"}}
    observed = {x["item_id"]: next((o for o in x["observations"] if o.get("kind") == "client_hotfix"), {})
                for x in audit["candidates"]}
    inventory = {}
    for path in sorted((ROOT / "data/raw/forever/ahledger").glob("*api-catalog-class-*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        sources[path.stem] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "url": doc["url"]}
        for entry in doc["records"]:
            inventory[entry["item_id"]] = entry
    groups, rows = {}, []
    for identifier, entry in sorted(inventory.items()):
        location = LOCATIONS.get(entry["slot"])
        subtype, name = entry["subclass"], entry["name"]
        if not location or identifier in excluded or subtype in {"Cosmetic", "Fishing Pole"} or NON_PLAYER.search(name):
            continue
        inv, slot, column = location
        if slot == "Relic":
            if subtype not in {"Idol", "Libram", "Totem"}:
                continue
            slot = subtype
        hotfix, client = observed.get(identifier, {}), sparse.get(identifier, {})
        required = int(hotfix.get("required_level", client.get("RequiredLevel", entry.get("required_level") or 0)))
        if required > 60:
            continue
        facts = dict(id=identifier, name=name, slot=slot, level=max(1, required), quality=entry["quality"].lower())
        if subtype in {*ARMOR, "Shield"} and slot != "Back":
            facts["armor_type"] = subtype
        if subtype not in {*ARMOR, "Shield", "Miscellaneous", "Idol", "Libram", "Totem"}:
            facts["weapon_subtype"] = subtype
        race_mask = (int(client.get("AllowableRace_0", -1)) & 0xffffffff) | ((int(client.get("AllowableRace_1", -1)) & 0xffffffff) << 32)
        for field, mask, bits in (("classes", hotfix.get("class_mask", client.get("AllowableClass", -1)), CLASS_BITS),
                                  ("race_ids", hotfix.get("race_mask", race_mask), race_bits)):
            allowed = [k for k, bit in bits.items() if int(mask) & (1 << bit)]
            if int(mask) > 0 and len(allowed) < len(bits):
                if not allowed:
                    break
                facts[field] = allowed
        else:
            family = attached.get(identifier)
            if family and family["lists"]:
                keys = tuple(sorted(family["lists"]))
                facts["group"] = groups.setdefault(keys, len(groups) + 1)
                ilvl, q = int(client.get("ItemLevel", entry["item_level"])), QUALITY.get(entry["quality"])
                if subtype == "Wand":
                    column = 3
                if q in (2, 3, 4) and ilvl in budgets and not family["indirect_scaling"]:
                    facts["budget"] = int(budgets[ilvl][("Good", "Superior", "Epic")[q - 2] + "_" + str(column)])
                    if subtype in ARMOR and ilvl in totals and inv in locations:
                        armor = (float(totals[ilvl][subtype]) * float(qualities[ilvl]["Qualitymod_" + str(q)])
                                 * float(locations[inv][ARMOR[subtype] + "modifier"]))
                        facts["armor"] = math.floor(armor + 0.5)
                    # A suffix budget describes the bonus only. Some bases also
                    # carry intrinsic stats. Weapons and shields need physical
                    # damage or block evidence in addition to their bonus.
                    intrinsic = int(client.get("ItemSet", 0)) or any(
                        int(client.get(f"StatModifier_bonusStat_{index}", -1)) >= 0
                        and int(client.get(f"StatPercentEditor_{index}", 0)) != 0 for index in range(10))
                    facts["roll_complete"] = (not intrinsic and bool(facts.get("armor") or slot in {"Neck", "Ring"})) or None
            values = [facts.get(field) for field in FIELDS]
            while values[-1] is None:
                values.pop()
            rows.append(values)
    return {"client_build": build, "sources": sources, "fields": FIELDS, "templates": templates,
            "groups": list(groups), "items": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--build", required=True)
    args = parser.parse_args()
    doc = compile_catalog(args.directory, args.build)
    # One equipment identity per line keeps inventory reviews and diffs small.
    metadata = {key: value for key, value in doc.items() if key != "items"}
    dump = lambda obj: json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    path = ROOT / "data/canonical/forever/guide_equipment.json"
    with path.open("w", encoding="utf-8", newline="\n") as file:
        file.write(dump(metadata)[:-1] + ',\n"items":[\n')
        file.write(",\n".join(dump(row) for row in doc["items"]) + "\n]}\n")


if __name__ == "__main__":
    main()
