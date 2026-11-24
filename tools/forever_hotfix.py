"""Read equipment requirements from the public Forever enUS hotfix cache."""
from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
import re
from struct import Struct

from tools.forever_availability import ALWAYS_ALLOW_DUAL_WIELD, ARMOR_TYPES, INVENTORY_TYPES, WEAPON_TYPES


RAIDBOTS_INDEX = "https://www.raidbots.com/api/dbcache/verified"
DBDEFS = "https://raw.githubusercontent.com/wowdev/WoWDBDefs/86c0801007bbcb767f4bc275413d24bc6b2d486c/definitions"
TABLE_FILES = {"Item": 841626, "ItemSparse": 1572924}
QUEST_HASH = 0x3AC83109
FILE_HEADER = Struct("<4sII")
ROW_HEADER = Struct("<4siiIIiiB3x")
TABLE_HEADER = Struct("<II")
FIELD = re.compile(r"(\w+)(?:<(u?)(8|16|32|64)>)?(?:\[(\d+)\])?")
INTEGER_TYPES = {"8": "b", "16": "h", "32": "i", "64": "q"}


def table_layout(raw: bytes, definition: str) -> tuple[int, list]:
    # WDC5 puts the table and layout hashes after the signature and description.
    if len(raw) < 160 or raw[:4] != b"WDC5":
        raise ValueError("Unsupported Wago DB2 header")
    table_hash, layout_hash = TABLE_HEADER.unpack_from(raw, 152)
    heading, *blocks = re.split(r"\n[ \t]*\n", definition.replace("\r\n", "\n"))
    columns = {}
    for line in heading.splitlines()[1:]:
        kind, name, *_ = line.split()
        columns[name.rstrip("?")] = kind.split("<", 1)[0]
    matches = [block for block in blocks if any(
        line.startswith("LAYOUT ") and f"{layout_hash:08X}" in line[7:].replace(",", " ").split()
        for line in block.splitlines())]
    if len(matches) != 1:
        raise ValueError(f"Unsupported hotfix layout {layout_hash:08X}")
    layout = []
    for line in matches[0].splitlines():
        line = line.partition("//")[0].strip()
        if not line or line.startswith(("BUILD ", "LAYOUT ", "COMMENT ", "$noninline,id$")):
            continue
        field = FIELD.fullmatch(re.sub(r"^\$[^$]+\$", "", line))
        if not field or field[1] not in columns:
            raise ValueError(f"Unsupported hotfix field {line}")
        name, unsigned, width, count = field.groups()
        kind = columns[name]
        if kind in {"locstring", "string"}:
            fmt = None
        elif kind == "float":
            fmt = Struct("<f")
        elif kind == "int" and width:
            code = INTEGER_TYPES[width]
            fmt = Struct("<" + (code.upper() if unsigned else code))
        else:
            raise ValueError(f"Unsupported hotfix field type {kind}")
        layout.extend((f"{name}_{index}" if count else name, fmt) for index in range(int(count or 1)))
    return table_hash, layout


def decode_row(data: bytes, layout: list) -> dict:
    values, offset = {}, 0
    for name, fmt in layout:
        if fmt:
            if offset + fmt.size > len(data):
                raise ValueError("Truncated hotfix field")
            values[name] = fmt.unpack_from(data, offset)[0]
            offset += fmt.size
        else:
            end = data.index(b"\0", offset)
            values[name] = data[offset:end].decode("utf-8")
            offset = end + 1
    if offset != len(data):
        raise ValueError("Hotfix record does not match its DB2 layout")
    return values


def latest_rows(raw: bytes, build: str, table_hashes: set[int]) -> dict:
    """Return the latest observed state and bytes for each requested cache row."""
    if len(raw) < 44 or FILE_HEADER.unpack_from(raw) != (b"XFTH", 9, int(build.rsplit(".", 1)[1])):
        raise ValueError("Raidbots cache header does not match the reviewed build")
    latest = defaultdict(dict)
    offset = 44
    while offset < len(raw):
        if offset + ROW_HEADER.size > len(raw):
            raise ValueError("Truncated Raidbots row header")
        magic, _region, push, sequence, table, identifier, size, state = ROW_HEADER.unpack_from(raw, offset)
        start = offset + ROW_HEADER.size
        offset = start + size
        if magic != b"XFTH" or size < 0 or offset > len(raw):
            raise ValueError("Invalid Raidbots row header")
        if identifier <= 0 or table not in table_hashes:
            continue
        version = (push, sequence)
        record = (version, state, raw[start:offset])
        previous = latest[table].get(identifier)
        # If equal-version records disagree, leave the fact undisclosed.
        if previous and version == previous[0] and record != previous:
            record = (version, 0, b"")
        if not previous or version >= previous[0]:
            latest[table][identifier] = record
    return latest


def read_cache(raw: bytes, build: str, layouts: dict) -> tuple[dict, dict]:
    latest = latest_rows(raw, build, {QUEST_HASH, *(layout[0] for layout in layouts.values())})
    equipment = {}
    for name, (table, fields) in layouts.items():
        equipment[name] = {i: (decode_row(data, fields), sha256(data).hexdigest(), version[0])
                           for i, (version, state, data) in latest[table].items() if state == 1 and data}
    quests = {i: sha256(data).hexdigest() for i, (_, state, data) in latest[QUEST_HASH].items() if state == 1 and data}
    return equipment, quests


def equipment_rows(equipment: dict) -> list[dict]:
    rows = []
    for identifier, (sparse, record_digest, push) in sorted(equipment["ItemSparse"].items()):
        base, _, _ = equipment["Item"].get(identifier, ({}, None, None))
        inventory_type = sparse["InventoryType"]
        slot = INVENTORY_TYPES.get(inventory_type)
        if not slot or not sparse["Display_lang"] or base.get("InventoryType") != inventory_type:
            continue
        row = {"item_id": identifier, "name": sparse["Display_lang"], "slot": slot,
               "item_level": sparse["ItemLevel"], "required_level": sparse["RequiredLevel"],
               "required_skill": sparse["RequiredSkill"], "required_skill_rank": sparse["RequiredSkillRank"],
               "class_mask": sparse["AllowableClass"], "binding": sparse["Bonding"],
               "race_mask": ((sparse["AllowableRace_1"] & 0xffffffff) << 32) | (sparse["AllowableRace_0"] & 0xffffffff),
               "record_digest": record_digest, "hotfix_push": push}
        subclass = base["SubclassID"]
        if base["ClassID"] == 4 and subclass in ARMOR_TYPES:
            row["armor_type"] = row["subclass"] = ARMOR_TYPES[subclass]
        if base["ClassID"] == 2 and subclass in WEAPON_TYPES and inventory_type in (13, 21, 22):
            row["weapon_subtype"] = WEAPON_TYPES[subclass]
        if inventory_type in (14, 23):
            row["requires_dual_wield"] = False
        elif inventory_type in (13, 22) and base["ClassID"] == 2:
            row["requires_dual_wield"] = not bool(sparse["Flags_2"] & ALWAYS_ALLOW_DUAL_WIELD)
        rows.append(row)
    return rows
