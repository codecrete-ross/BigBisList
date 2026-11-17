"""Collect exact-build scoring facts from the public client tables and hotfixes."""
from __future__ import annotations

import csv
import io
import json
import math
import re
import struct
from pathlib import Path

from tools.forever_hotfix import DBDEFS, RAIDBOTS_INDEX, decode_row, latest_rows, table_layout
from tools.forever_refresh_http import RefreshHTTP, workspace_lock, write_json
from tools.forever_sources import PROVIDER_RAW_DIR, source_provider
from tools.project import FOREVER_CANONICAL_DIR, ROOT, load_json


TABLES = ("TraitNode", "TraitNodeEntry", "TraitNodeXTraitNodeEntry", "TraitDefinition",
          "TraitDefinitionEffectPoints", "CurvePoint", "Spell", "SpellName", "SpellEffect", "SpellItemEnchantment")
TABLE_MANIFEST = DBDEFS.rsplit("/", 1)[0] + "/manifest.json"
ROW_LAYOUT_FILES = {"TraitDefinition": 4420327, "SpellEffect": 1140088}
HOTFIX_NOTE = "https://worldofwarcraft.blizzard.com/en-us/news/24315281/wow-forever-hotfixes-november-13-2026"
HOTFIX_TEXT = re.compile(r"Judgement of Command now activates on-hit effects and counts as a melee attack", re.I)
CURVE_POINT = struct.Struct("<ffffIII")
NODE_ENTRY = struct.Struct("<IIIbI")
EFFECT_POINTS = struct.Struct("<IIIII")
NODE_LINK = struct.Struct("<IIII")
STAT_AURAS = ("strength", "agility", "stamina", "intellect", "spirit")
ITEM_MODS = {3: "agility", 4: "strength", 5: "intellect", 6: "spirit", 7: "stamina",
             12: "defense", 38: "attack_power", 43: "mp5", 45: "spell_power"}


def edited_row(hotfix: dict, table: str, row_id: int) -> dict | None:
    rows = hotfix.get(table, {}).get(str(row_id), [])
    if not rows:
        return None
    push = max(row["pushId"] for row in rows)
    latest = [row for row in rows if row["pushId"] == push]
    if len({(row.get("status"), row.get("data")) for row in latest}) != 1 or latest[0].get("status") != "valid":
        raise ValueError(f"Unresolved {table} hotfix for row {row_id}")
    return latest[0]


def csv_rows(data: bytes) -> dict[int, dict]:
    rows = list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"))))
    result = {int(row["ID"]): row for row in rows}
    if len(result) != len(rows) or not result:
        raise ValueError("Duplicate or empty mechanics table")
    return result


def flat_enchants(client: dict, hotfix: dict) -> dict:
    """Exact persistent stats only. Leave conditional and scaling enchants unscored."""
    spell_effects = {}
    for effect_id, row in client["SpellEffect"].items():
        spell_effects.setdefault(int(row["SpellID"]), []).append((effect_id, row))
    enchants = {}
    for identifier, row in client["SpellItemEnchantment"].items():
        if (int(row["Condition_ID"]) or int(row["ScalingClass"]) or int(row["Duration"])
                or hotfix.get("SpellItemEnchantment", {}).get(str(identifier))):
            continue
        stats, evidence = {}, []

        def add(stat, amount):
            stats[stat] = stats.get(stat, 0) + amount

        for index in range(3):
            kind, argument, amount = (int(row[f"{field}_{index}"])
                                       for field in ("Effect", "EffectArg", "EffectPointsMin"))
            if float(row[f"EffectScalingPoints_{index}"]):
                break
            if kind == 0:
                continue
            if kind == 4:
                add("armor", amount)
            elif kind == 5 and argument in ITEM_MODS:
                add(ITEM_MODS[argument], amount)
            elif kind == 3 and (effects := spell_effects.get(argument)):
                resolved = []
                for effect_id, aura in effects:
                    if (int(aura["Effect"]) != 6 or int(aura["EffectAura"]) not in {13, 29, 30, 135}
                            or hotfix.get("SpellEffect", {}).get(str(effect_id))):
                        break
                    aura_id, selector = int(aura["EffectAura"]), int(aura["EffectMiscValue_0"])
                    if aura_id == 29 and -1 <= selector < len(STAT_AURAS):
                        names = STAT_AURAS if selector == -1 else (STAT_AURAS[selector],)
                    elif aura_id == 30 and selector == 95:
                        names = ("defense",)
                    elif aura_id in {13, 135} and selector == 126:
                        names = ("spell_damage" if aura_id == 13 else "healing_power",)
                    else:
                        break
                    resolved.append(effect_id)
                    for name in names:
                        add(name, float(aura["EffectBasePointsF"]))
                if len(resolved) != len(effects):
                    break
                evidence.extend(resolved)
            else:
                break
        else:
            if stats:
                enchants[str(identifier)] = {"stats": stats, "spell_effect_ids": evidence, "name": row["Name_lang"]}
    return enchants


def hotfix_tables(build: str, exports: dict[str, bytes], url: str) -> tuple[dict, dict]:
    if source_provider(url) == "raidbots":
        index = json.loads(exports["verified_index"])["data"]
        if not any(row["url"] == url and row["verified"] is True and row["version"] == "forever"
                   and row["build"] == int(build.rsplit(".", 1)[1]) for row in index):
            raise ValueError("Expected a verified Forever Raidbots cache for the selected build")
        names = set(TABLES) | (exports.keys() & {"ItemSet", "ItemSetSpell", "SkillLineAbility"})
        hashes = {row["tableName"]: int(row["tableHash"], 16)
                  for row in json.loads(exports["table_manifest"]) if row.get("tableName") in names}
        if set(hashes) != names or len(set(hashes.values())) != len(names):
            raise ValueError("The table manifest does not identify all mechanics tables")
        latest = latest_rows(exports["hotfixes"], build, set(hashes.values()))
        tables = {name: {str(i): [{"pushId": version[0], "status": "valid" if state == 1 and data else "invalid",
                                  "data": data.hex()}]
                         for i, (version, state, data) in latest[table].items()}
                  for name, table in hashes.items()}
        return tables, {"credit": "Blizzard game data, public enUS cache archived by Raidbots",
                        "source": RAIDBOTS_INDEX}

    overlay = json.loads(exports["hotfixes"])
    meta = overlay["meta"]
    if source_provider(url) != "eg_link" or (meta["clientBuild"], meta["product"], meta["license"]) != (build, "wowf", "CC BY 4.0"):
        raise ValueError("Expected an attributed Forever hotfix export for the selected build")
    return {entry["name"]: entry["rows"] for entry in overlay["tables"].values()}, {
        "credit": "EG Link observations by Efficient Games (CC BY 4.0)", "source": "https://efficient.games",
        "licence": "CC BY 4.0", "licenceUrl": "https://creativecommons.org/licenses/by/4.0/"}


def normalized_set_bonuses(requests, client, read_row):
    bonuses = []
    for request in requests:
        set_id, spell_id, pieces = (request[key] for key in ("set_id", "spell_id", "pieces"))
        definition, _ = read_row("ItemSet", set_id)
        links = [identifier for identifier, row in client["ItemSetSpell"].items()
                 if int(row["ItemSetID"]) == set_id and int(row["Threshold"]) == pieces
                 and int(row["SpellID"]) == spell_id]
        if len(links) != 1:
            raise ValueError(f"Expected a unique bonus for item set {set_id}")
        link, _ = read_row("ItemSetSpell", links[0])
        if tuple(int(link[field]) for field in ("ItemSetID", "SpellID", "Threshold")) != (set_id, spell_id, pieces):
            raise ValueError(f"Item set bonus {set_id} has changed")
        if any(int(link[field]) for field in ("ChrSpecID", "TraitSubTreeID")) or any(
                int(definition[field]) for field in ("RequiredSkill", "RequiredSkillRank", "SetFlags")):
            raise ValueError(f"Conditional item set bonus {set_id} requires its own review")
        effects = [read_row("SpellEffect", identifier)[0] for identifier, row in client["SpellEffect"].items()
                   if int(row["SpellID"]) == spell_id]
        values = {int(row["EffectAura"]): float(row["EffectBasePointsF"]) for row in effects}
        selectors = {int(row["EffectMiscValue_0"]) for row in effects}
        if len(values) != len(effects) or any(int(row["Effect"]) != 6 for row in effects):
            raise ValueError(f"Expected static stat auras for item set {set_id}")
        if values.keys() == {13, 135} and values[13] == values[135] and selectors == {126}:
            stats = {"spell_power": values[13]}
        elif values.keys() == {29} and selectors == {0}:
            stats = {"strength": values[29]}
        else:
            raise ValueError(f"Unsupported static stat aura for item set {set_id}")
        bonuses.append({**request, "name": definition["Name_lang"], "stats": stats, "set_bonus_id": links[0],
                        "item_ids": sorted(int(v) for k, v in definition.items() if k.startswith("ItemID_") and int(v))})
    return bonuses


def normalized_racial_scaling(requests, client, read_row):
    modifiers = []
    for request in requests:
        race_id, spell_id = request["race_id"], request["spell_id"]
        entry, _ = read_row("SkillLineAbility", request["skill_ability_id"])
        race_mask = (int(entry["RaceMasks_0"]) & 0xffffffff) | (int(entry["RaceMasks_1"]) & 0xffffffff) << 32
        if int(entry["Spell"]) != spell_id or race_mask != 1 << (race_id - 1) or int(entry["ClassMask"]):
            raise ValueError(f"Unexpected racial eligibility for spell {spell_id}")
        effects = [identifier for identifier, row in client["SpellEffect"].items() if int(row["SpellID"]) == spell_id]
        if len(effects) != 1:
            raise ValueError(f"Expected a single racial stat aura for spell {spell_id}")
        effect, push = read_row("SpellEffect", effects[0])
        stat = int(effect["EffectMiscValue_0"])
        if int(effect["Effect"]) != 6 or int(effect["EffectAura"]) != 137 or not 0 <= stat < len(STAT_AURAS):
            raise ValueError(f"Unexpected racial stat aura for spell {spell_id}")
        modifiers.append({**request, "stat": STAT_AURAS[stat],
                          "multiplier": 1 + float(effect["EffectBasePointsF"]) / 100,
                          "name": client["SpellName"][spell_id]["Name_lang"], "spell_effect_id": effects[0],
                          **({"push_id": push} if push else {})})
    return modifiers


def normalize_mechanics(model: dict, exports: dict[str, bytes], receipts: dict, hotfix_url: str) -> dict:
    """Join the reviewed spell IDs to nodes and resolve per-rank curve points."""
    build = model["client_build"]
    names = set(TABLES) | (exports.keys() & {"ItemSet", "ItemSetSpell", "SkillLineAbility"})
    client = {name: csv_rows(exports[name]) for name in sorted(names)}
    hotfix, hotfix_credit = hotfix_tables(build, exports, hotfix_url)

    layouts = {}

    def read_row(table, identifier):
        base = client[table][identifier]
        record = edited_row(hotfix, table, identifier)
        if record is None:
            return base, None
        if table not in layouts:
            if f"{table}.db2" not in exports or f"{table}.dbd" not in exports:
                raise ValueError(f"{table} row {identifier} needs review against its hotfix")
            layouts[table] = table_layout(exports[f"{table}.db2"], exports[f"{table}.dbd"].decode("utf-8-sig"))[1]
        decoded = decode_row(bytes.fromhex(record["data"]), layouts[table])
        if decoded.get("ID", identifier) != identifier:
            raise ValueError(f"{table} hotfix row changed identity {identifier}")
        return {**base, **decoded}, record["pushId"]

    def observe(table: str, identifier: int, layout: struct.Struct):
        record = edited_row(hotfix, table, identifier)
        if record is None:
            return None, None
        value = layout.unpack(bytes.fromhex(record["data"]))
        return value, record["pushId"]

    traits = {}
    for entry_id, request in sorted(model["traits"].items(), key=lambda row: int(row[0])):
        identifier = int(entry_id)
        entry = client["TraitNodeEntry"][identifier]
        definition_id, max_rank = int(entry["TraitDefinitionID"]), int(entry["MaxRanks"])
        observed, entry_push = observe("TraitNodeEntry", identifier, NODE_ENTRY)
        if observed:
            if observed[0] != identifier:
                raise ValueError(f"Trait entry hotfix changed identity {identifier}")
            definition_id, max_rank = observed[1:3]
        definition, definition_push = read_row("TraitDefinition", definition_id)
        spell = int(definition["SpellID"])
        if spell != request["spell"]:
            raise ValueError(f"Trait entry {identifier} changed spell")
        links = []
        for link_id, link in client["TraitNodeXTraitNodeEntry"].items():
            seen_entry, seen_node = int(link["TraitNodeEntryID"]), int(link["TraitNodeID"])
            if seen_entry == identifier:
                update, _ = observe("TraitNodeXTraitNodeEntry", link_id, NODE_LINK)
                if update and update != (link_id, seen_node, seen_entry, int(link["_Index"])):
                    raise ValueError(f"Trait node mapping changed for {identifier}")
                links.append(seen_node)
        if len(links) != 1:
            raise ValueError(f"Missing or ambiguous trait node for {identifier}")
        node = client["TraitNode"][links[0]]
        rows = []
        for curve_id, curve in client["TraitDefinitionEffectPoints"].items():
            if int(curve["TraitDefinitionID"]) != definition_id:
                continue
            effect, operation, curve_number = map(int, (curve["EffectIndex"], curve["OperationType"], curve["CurveID"]))
            update, push = observe("TraitDefinitionEffectPoints", curve_id, EFFECT_POINTS)
            if update and update[:2] != (curve_id, definition_id):
                raise ValueError(f"Trait curve changed identity {curve_id}")
            if update:
                effect, operation, curve_number = update[2:]
            if effect not in request["effects"]:
                continue
            if operation != 0:
                raise ValueError(f"Expected absolute per-rank points for trait {identifier}")
            points = {}
            for point_id, point in client["CurvePoint"].items():
                if int(point["CurveID"]) != curve_number:
                    continue
                rank, value = float(point["Pos_0"]), float(point["Pos_1"])
                override, point_push = observe("CurvePoint", point_id, CURVE_POINT)
                if override:
                    if override[4:6] != (point_id, curve_number):
                        raise ValueError(f"Trait rank point {point_id} changed identity")
                    rank, value = override[:2]
                if not rank.is_integer() or not math.isfinite(value) or int(rank) in points:
                    raise ValueError(f"Invalid rank point for trait {identifier}")
                points[int(rank)] = {"value": value, "row_id": point_id, **({"push_id": point_push} if point_push else {})}
            if set(points) != set(range(1, max_rank + 1)):
                raise ValueError(f"Incomplete rank curve for trait {identifier}")
            rows.append({"effect_index": effect, "curve_id": curve_number, "row_id": curve_id,
                         "ranks": [points[rank] for rank in sorted(points)],
                         **({"push_id": push} if push else {})})
        if sorted(row["effect_index"] for row in rows) != sorted(request["effects"]):
            raise ValueError(f"Missing or duplicate reviewed effects for trait {identifier}")
        traits[entry_id] = {
            "spell_id": spell, "definition_id": definition_id, "node_id": links[0],
            "tree_id": int(node["TraitTreeID"]), "max_rank": max_rank,
            "name": client["SpellName"][spell]["Name_lang"],
            "tooltip_template": client["Spell"][spell]["Description_lang"],
            "effects": sorted(rows, key=lambda row: row["effect_index"]),
            "spell_effects": [
                {key: int(row[key]) for key in ("ID", "EffectIndex", "Effect", "EffectAura", "EffectMiscValue_0",
                                               "EffectMiscValue_1")}
                for row in client["SpellEffect"].values()
                if int(row["SpellID"]) == spell and int(row["EffectIndex"]) in request["effects"]
            ],
            **({"entry_push_id": entry_push} if entry_push else {}),
            **({"definition_push_id": definition_push} if definition_push else {}),
        }

    if not HOTFIX_TEXT.search(exports["hotfix_note"].decode("utf-8", errors="replace")):
        raise ValueError("Blizzard's Judgement of Command hotfix is missing from the source")
    return {"url": hotfix_url, "provider": source_provider(hotfix_url), "flavor": "forever", "page_type": "mechanics",
            "client_build": build, "fetched_at": max(row["collected_at"] for row in receipts.values()),
            "confidence": "build_pinned_client_and_observed_hotfix",
            "source_content_digest": receipts["hotfixes"]["source_content_digest"],
            "input_sources": {name: {key: row[key] for key in ("source_url", "source_content_digest", "collected_at")}
                              for name, row in receipts.items()},
            "attribution": [
                {"credit": "Blizzard Entertainment game data via Wago Tools", "source": "https://wago.tools"},
                hotfix_credit,
                {"credit": "Blizzard Entertainment hotfix notes", "source": HOTFIX_NOTE},
            ],
            "traits": traits, "enchants": flat_enchants(client, hotfix),
            **({"flat_sets": normalized_set_bonuses(model["flat_sets"], client, read_row)} if model.get("flat_sets") else {}),
            **({"racial_scaling": normalized_racial_scaling(model["racial_spells"], client, read_row)}
               if model.get("racial_spells") else {}),
            "ability_triggers": {"20425": {"name": "Judgement of Command", "class": "Paladin",
                                         "attack": "melee", "activates": ["melee_on_hit"], "source_url": HOTFIX_NOTE}}}


def snapshot_path(url: str) -> Path:
    from tools.scrape_wowhead import snapshot_name

    return PROVIDER_RAW_DIR / source_provider(url) / snapshot_name(url)


def collect_mechanics(*, online: bool, write: bool, user_agent: str) -> dict:
    from tools.forever_refresh import REFRESH_DIR
    from tools.forever_refresh_http import WINDOWS_TLS_HOSTS
    from tools.forever_scoring import model_url

    model = load_json(FOREVER_CANONICAL_DIR / "scoring_model.json")
    build, hotfix_url = model["client_build"], model_url(model)
    urls = {name: f"https://wago.tools/db2/{name}/csv?build={build}" for name in TABLES}
    urls.update(hotfixes=hotfix_url, hotfix_note=HOTFIX_NOTE)
    provider = source_provider(hotfix_url)
    if provider == "raidbots":
        urls.update(table_manifest=TABLE_MANIFEST, verified_index=RAIDBOTS_INDEX)
        for table, identifier in ROW_LAYOUT_FILES.items():
            urls[f"{table}.db2"] = f"https://wago.tools/api/casc/{identifier}?version={build}"
            urls[f"{table}.dbd"] = f"{DBDEFS}/{table}.dbd"
    if model.get("flat_sets"):
        urls.update({table: f"https://wago.tools/db2/{table}/csv?build={build}" for table in ("ItemSet", "ItemSetSpell")})
    if model.get("racial_spells"):
        urls["SkillLineAbility"] = f"https://wago.tools/db2/SkillLineAbility/csv?build={build}"
    WINDOWS_TLS_HOSTS.update({"wago.tools", "worldofwarcraft.blizzard.com"})
    with workspace_lock(REFRESH_DIR):
        http = RefreshHTTP(REFRESH_DIR, online=online, user_agent=user_agent)
        payloads, receipts = {}, {}
        for name, url in urls.items():
            payloads[name], receipts[name] = http.get(url, immutable=name not in {"hotfix_note", "verified_index"})
        snapshot = normalize_mechanics(model, payloads, receipts, hotfix_url)
    target = snapshot_path(hotfix_url)
    if target.is_file():
        previous = load_json(target)
        if "equipment_compatibility" in previous and previous["source_content_digest"] == snapshot["source_content_digest"]:
            snapshot["equipment_compatibility"] = previous["equipment_compatibility"]
    staged = ROOT / "build" / "forever-scoring" / "mechanics.json"
    write_json(staged, snapshot)
    if write:
        path = FOREVER_CANONICAL_DIR / "scrape_manifest.json"
        manifest = load_json(path)
        if not any(source["url"] == hotfix_url for source in manifest["sources"]):
            manifest["sources"].append({"url": hotfix_url, "provider": provider,
                                        "data_family": "scoring_mechanics", "status": "collected"})
            write_json(path, manifest)
        write_json(target, snapshot)
    return {"source_url": hotfix_url, "staged": staged.as_posix(), "snapshot": target.as_posix() if write else None,
            "traits": len(snapshot["traits"]), "abilities": len(snapshot["ability_triggers"]),
            "http_attempts": http.request_count}
