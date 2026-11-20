"""Normalize bulk equipment publications for the Forever Gear Guide."""

from __future__ import annotations

import csv
from hashlib import sha256
from io import BytesIO, StringIO
import json
from math import floor
import re
from zipfile import ZipFile

from tools.forever_guide_catalog import ARMOR, LOCATIONS, NON_PLAYER, QUALITY


WOWSIMS_ROOT = "https://raw.githubusercontent.com/wowsims/gamedata"
WOWSIMS_HEAD = "https://api.github.com/repos/wowsims/gamedata/commits?per_page=1"
LIBITEMDB_URL = "https://edge.forgecdn.net/files/9633/029/ItemDB-ItemDB-v1.10.0.zip"
LIBITEMDB_DIGEST = "1765004d45e16d6d7c2c4d9fb55e209e7c4b37900f123edb910cfd78e47ba7a0"
FOREVER_CLASSES = {"Warrior", "Paladin", "Hunter", "Rogue", "Priest", "Shaman", "Mage", "Warlock", "Druid"}
WEAPON_TYPES = {"Axe", "Bow", "Crossbow", "Dagger", "Fist Weapon", "Gun", "Mace", "Polearm", "Staff", "Sword", "Thrown", "Wand"}
ARMOR_TYPES = {"Cloth", "Leather", "Mail", "Plate", "Shield"}
RELIC_TYPES = {"Idol", "Libram", "Totem"}
SLOTS = {"head": "Head", "neck": "Neck", "shoulders": "Shoulder", "chest": "Chest", "waist": "Waist",
         "legs": "Legs", "feet": "Feet", "wrists": "Wrist", "hands": "Hands", "finger": "Ring",
         "trinket": "Trinket", "one-hand": "One Hand", "shield": "Off Hand", "back": "Back",
         "two-hand": "Two Hand", "main hand": "Main Hand", "off hand": "Off Hand",
         "held in off hand": "Off Hand", "ranged": "Ranged", "thrown": "Ranged"}
ATTRIBUTES = {
    label: label.replace(" ", "_") for label in (
        "mana", "health", "agility", "strength", "intellect", "spirit", "stamina", "dodge rating", "parry rating",
        "block rating", "hit rating", "crit rating", "spell hit rating", "spell crit rating", "spell haste rating",
        "ranged hit rating", "ranged crit rating", "ranged haste rating", "resilience rating", "haste rating",
        "expertise rating", "attack power", "ranged attack power", "feral attack power", "spell damage", "spell power",
        "spell penetration", "block value", "armor", "fire resistance", "frost resistance", "nature resistance",
        "shadow resistance", "arcane resistance", "holy resistance", "weapon damage", "holy damage", "fire damage",
        "nature damage", "frost damage", "shadow damage", "arcane damage", "all resistances",
    )
} | {"mana per 5 sec": "mp5", "health per 5 sec": "hp5", "healing": "healing_power", "defense rating": "defense_rating",
     "melee hit rating": "melee_hit_rating", "melee crit rating": "melee_crit_rating", "melee haste rating": "melee_haste_rating",
     "armor penetration": "armor_penetration"}
WEAPON_LINE = re.compile(r"(\d+) - (\d+) damage, speed (\d+(?:\.\d+)?), (\d+(?:\.\d+)?) dps")
ARCHIVE_ROW = re.compile(r'^\[(\d+)\]="([^"\n]*)",$')
ARCHIVE_STATS = {
    "ITEM_MOD_DAMAGE_PER_SECOND_SHORT": "dps", "RESISTANCE0_NAME": "armor", "ITEM_MOD_BLOCK_VALUE_SHORT": "block_value",
    **{f"ITEM_MOD_{key.upper()}_SHORT": key for key in ("strength", "agility", "stamina", "intellect", "spirit", "attack_power")},
}
ARMOR_TABLES = {"ItemSparse": "ID", "ItemArmorTotal": "ItemLevel", "ItemArmorQuality": "ID", "ArmorLocation": "ID",
                "ItemArmorShield": "ItemLevel"}


def publication_key(snapshot: dict) -> tuple:
    return (snapshot.get("publication", ""), snapshot.get("hotfix_count", 0), snapshot.get("fetched_at", ""), snapshot.get("url", ""))


def wowsims_build(raw: bytes) -> str:
    state = json.loads(raw)
    build = state["version"]
    if (not re.fullmatch(r"1\.60\.\d+\.\d+", build) or state["build"] != int(build.rsplit(".", 1)[1])
            or type(state["pushes"]) is not int or state["pushes"] < 0
            or not state["folder"].startswith(f"patches/{build}/") or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", state["date"])):
        raise ValueError("Invalid WoWSims Forever export revision")
    return build


def _wowsims_item(identifier: int, name: str, fields: dict) -> dict | None:
    quality, _, tail = fields["item"].partition(", ")
    subtype, separator, location = tail.rpartition(", ")
    if not separator or quality.upper() not in QUALITY or NON_PLAYER.search(name) or subtype in {"Cosmetic", "Fishing Pole"}:
        return None
    slot = subtype if location == "relic" and subtype in RELIC_TYPES else SLOTS.get(location)
    if not slot:
        return None
    if slot in {"One Hand", "Two Hand", "Main Hand", "Ranged"} and subtype not in WEAPON_TYPES:
        return None
    level = re.fullmatch(r"ilvl (\d+)(?:, requires level (\d+))?", fields["level"])
    if not level:
        raise ValueError(f"Malformed WoWSims item level for {identifier}")
    required = int(level[2] or 0)
    if required > 60:
        return None
    row = {"id": identifier, "name": name, "slot": slot, "required_level": required,
           "item_level": int(level[1]), "quality": quality, "stats": {}}
    if subtype in ARMOR_TYPES and slot != "Back":
        row["armor_type"] = subtype
    if subtype in WEAPON_TYPES:
        row["weapon_subtype"] = subtype
    if fields.get("classes"):
        classes = sorted(FOREVER_CLASSES & {key.title() for key in fields["classes"].split(", ")})
        if not classes:
            return None
        if set(classes) != FOREVER_CLASSES:
            row["restrictions"] = {"classes": classes}
    if fields.get("unique") == "yes":
        row["max_equipped"] = 1
    for attribute in fields["stats"].split(", ") if fields.get("stats") else ():
        match = re.fullmatch(r"([+-]?\d+(?:\.\d+)?) (.+)", attribute)
        if not match or match[2] not in ATTRIBUTES:
            row.setdefault("unparsed_attributes", []).append(attribute)
            continue
        stat = ATTRIBUTES[match[2]]
        if stat == "armor":
            row["bonus_armor"] = row.get("bonus_armor", 0) + float(match[1])
        else:
            row["stats"][stat] = row["stats"].get(stat, 0) + float(match[1])
    if fields.get("weapon"):
        match = WEAPON_LINE.fullmatch(fields["weapon"])
        if match:
            low, high, speed = int(match[1]), int(match[2]), float(match[3])
            if not 0 <= low <= high or speed <= 0 or abs((low + high) / (2 * speed) - float(match[4])) > 0.051:
                raise ValueError(f"Inconsistent WoWSims weapon damage for {identifier}")
            row.update(weapon_min_damage=low, weapon_max_damage=high, weapon_speed=speed,
                       dps=round((low + high) / (2 * speed), 2))
        elif not re.fullmatch(r"speed \d+\.\d+", fields["weapon"]):
            raise ValueError(f"Malformed WoWSims weapon damage for {identifier}")
    if fields.get("effect") or fields.get("set"):
        # Spell labels are evidence of an effect, with its text and mechanics still to verify.
        row["effect_leads"] = fields.get("effect", []) + ([f"Set: {fields['set']}"] if fields.get("set") else [])
    return row


def normalize_wowsims(url: str, raw: bytes, state: bytes, collected_at: str) -> dict:
    build = wowsims_build(state)
    items, previous, count = [], 0, 0
    for card in raw.decode("utf-8-sig").strip().split("\n=======\n"):
        heading, *lines = card.splitlines()
        match = re.fullmatch(r"([1-9]\d*) (.+)", heading)
        if not match or int(match[1]) <= previous:
            raise ValueError("Malformed or out-of-order WoWSims item card")
        previous = int(match[1])
        count += 1
        fields = {}
        for line in lines:
            key, _, value = line.partition(" ")
            if key == "effect":
                fields.setdefault(key, []).append(value.strip())
            elif key in {"item", "level", "classes", "stats", "weapon", "set", "unique"}:
                if key in fields:
                    raise ValueError(f"Repeated WoWSims item field {key} for {previous}")
                fields[key] = value.strip()
        row = _wowsims_item(previous, match[2], fields)
        if row:
            items.append(row)
    if count < 10000 or len(items) < 5000:
        raise ValueError("Incomplete WoWSims Forever equipment export")
    receipt = json.loads(state)
    return {"url": url, "flavor": "forever", "provider": "wowsims_gamedata", "page_type": "equipment_facts",
            "confidence": "client_equipment_export", "client_build": build, "fetched_at": collected_at,
            "source_content_digest": sha256(raw).hexdigest(), "state_digest": sha256(state).hexdigest(),
            "publication": receipt["date"], "hotfix_count": receipt["pushes"], "record_count": count, "items": items,
            "attribution": [{"credit": "WoWSims Forever Game Data", "source": "https://github.com/wowsims/gamedata"}]}


def client_armor(tables: dict, equipment: dict, build: str, url: str, collected_at: str) -> dict:
    parsed = {}
    for name, key in ARMOR_TABLES.items():
        rows = list(csv.DictReader(StringIO(tables[name].decode("utf-8-sig"))))
        parsed[name] = {int(row[key]): row for row in rows}
        if not rows or len(parsed[name]) != len(rows):
            raise ValueError(f"Invalid Forever {name} export")
    slots = {number: slot for number, slot, _ in LOCATIONS.values()}
    result = []
    for identifier, sparse in parsed["ItemSparse"].items():
        item = equipment.get(identifier)
        if not item:
            continue
        inventory = int(sparse["InventoryType"])
        level, quality = int(sparse["ItemLevel"]), int(sparse["OverallQualityID"])
        if (slots.get(inventory) != item["slot"] or level != item["item_level"] or quality != QUALITY[item["quality"].upper()]
                or sparse["Display_lang"].casefold() != item["name"].casefold()):
            continue
        material = "Cloth" if item["slot"] == "Back" else item.get("armor_type")
        if material == "Shield":
            shield = parsed["ItemArmorShield"].get(level)
            if not shield:
                continue
            base = int(shield[f"Quality_{quality}"])
        elif material in ARMOR:
            total, modifier = parsed["ItemArmorTotal"].get(level), parsed["ItemArmorQuality"].get(level)
            location = parsed["ArmorLocation"].get(5 if inventory == 20 else inventory)
            if not (total and modifier and location):
                continue
            base = float(total[material]) * float(modifier[f"Qualitymod_{quality}"]) * float(location[f"{ARMOR[material]}modifier"])
        else:
            continue
        modifier = float(sparse["QualityModifier"])
        bonus = item.get("bonus_armor", 0)
        # Some revisions represent the same armor bonus as a quality modifier
        # and as a stat allocation. Conflicting amounts require a tooltip.
        if modifier and bonus and modifier != bonus:
            continue
        armor = floor(base + (bonus or modifier) + 0.5)
        if armor > 0:
            row = {key: item[key] for key in ("id", "slot", "name", "armor_type") if key in item}
            result.append({**row, "armor": armor})
    return {"url": url, "flavor": "forever", "provider": "wago", "page_type": "equipment_facts",
            "confidence": "client_armor_tables", "client_build": build, "fetched_at": collected_at,
            "input_sources": [{"url": f"https://wago.tools/db2/{name}/csv?build={build}", "digest": sha256(raw).hexdigest()}
                              for name, raw in sorted(tables.items())],
            "items": sorted(result, key=lambda item: item["id"]),
            "attribution": [{"credit": "Build-pinned Forever armor tables via wago.tools", "source": "https://wago.tools/"}]}


def normalize_libitemdb(raw: bytes, collected_at: str) -> dict:
    if sha256(raw).hexdigest() != LIBITEMDB_DIGEST:
        raise ValueError("LibItemDB archive does not match its pinned release")
    items, interfaces, builds = {}, set(), set()
    with ZipFile(BytesIO(raw)) as archive:
        for kind in ("Armor", "Weapon"):
            entry = archive.getinfo(f"ItemDB/Data/Forever/_core/{kind}.lua")
            if entry.file_size > 4 * 1024 * 1024:
                raise ValueError("Unexpected LibItemDB equipment table size")
            heading, *lines = archive.read(entry).decode("utf-8-sig").splitlines()
            declared = next((re.fullmatch(r"-- client build ([\d.]+) - (\d+) items", line)
                             for line in lines if line.startswith("-- client build ")), None)
            if heading != f"-- LibItemDB core - WoW Forever, {kind} (locale-independent)" or not declared:
                raise ValueError("Unexpected LibItemDB Forever equipment format")
            (interfaces if declared[1].isdigit() else builds).add(declared[1])
            records = [ARCHIVE_ROW.fullmatch(line) for line in lines if line.startswith("[")]
            if len(records) != int(declared[2]) or not all(records):
                raise ValueError("Incomplete LibItemDB equipment table")
            for record in records:
                quality, _, location, level, text = record[2].split(r"\031")
                location = location.removeprefix("INVTYPE_")
                location = LOCATIONS.get("TWOHWEAPON" if location == "2HWEAPON" else location)
                if not location:
                    continue
                stats = {}
                for entry in text.split(",") if text else ():
                    key, value = entry.split("=", 1)
                    if key in ARCHIVE_STATS:
                        stats[ARCHIVE_STATS[key]] = round(float(value), 2)
                if stats:
                    identifier = int(record[1])
                    if identifier in items:
                        raise ValueError("Duplicate LibItemDB equipment ID")
                    items[identifier] = {"id": identifier, "slot": location[1], "item_level": int(level),
                                         "quality_index": int(quality), "stats": stats}
    if len(builds) > 1 or (builds and interfaces) or interfaces - {"16001"}:
        raise ValueError("Inconsistent Forever LibItemDB build provenance")
    # An interface number is shared by many builds. Those readings corroborate
    # exact IDs and expose discrepancies without authorizing a current value.
    return {"url": LIBITEMDB_URL, "flavor": "forever", "provider": "libitemdb", "page_type": "equipment_facts",
            "confidence": "equipment_scan", "fetched_at": collected_at, "source_content_digest": LIBITEMDB_DIGEST,
            **({"client_build": next(iter(builds))} if builds else {"interface": int(next(iter(interfaces)))}),
            "items": [items[key] for key in sorted(items)],
            "attribution": [{"credit": "LibItemDB (MIT)", "source": "https://www.curseforge.com/wow/addons/libitemdb/files/9633029"}]}
