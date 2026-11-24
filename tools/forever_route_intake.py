"""Normalize locally saved Forever source exports for the offline Guide route audit."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from html import unescape
from pathlib import Path

from tools.forever_sources import PROVIDER_RAW_DIR, source_provider
from tools.project import FOREVER_CANONICAL_DIR, dataset_json, write_text


QUESTIE = "https://github.com/Questie/QuestieDB/tree/80866960788084ae1592abf66a08f0d306458a95"
CONTEXT = QUESTIE + "#gear-guide-route-context"
BUILD = "1.60.1.70959"
EG = "https://raw.githubusercontent.com/JIVESCORP/eg-link-output-wowf/30c3bb9c8e792208feab362357471603dc51e12e/data/wowf/" + BUILD
ITEMS = "https://wago.tools/db2/ItemSparse/csv?build=" + BUILD
PLAYFULLS = "https://playfulls.com"
SKILLS = {164: "Blacksmithing", 165: "Leatherworking", 171: "Alchemy", 197: "Tailoring", 202: "Engineering", 333: "Enchanting"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dungeon_page(body):
    title = re.search(r"<h1[^>]*>([^<]+) Loot and Bosses</h1>", body)
    minimum = re.search(r'<meta name="description" content="[^"]*?\(levels? (\d+)', body)
    sections = re.findall(r'<section\b[^>]*\bdata-boss="([^"]+)"[^>]*>(.*?)</section>', body, re.S)
    if not title or not minimum or not sections:
        raise ValueError("Incomplete Forever dungeon table")
    groups, gear = {}, set()
    for name, markup in sections:
        # Each linked item in this particular encounter section counts once.
        ids = sorted({int(i) for i in re.findall(r'href="/item/(\d+)-', markup)})
        if ids:
            groups[unescape(name)] = ids
        for card in re.split(r'<div class="ltit"\s+', markup)[1:]:
            slot = re.match(r'[^>]*\bdata-s="([^"]+)"', card)
            link = re.search(r'<a class="ltinm" href="/item/(\d+)-', card)
            if slot and link:
                gear.add(int(link[1]))
    if not groups:
        raise ValueError("Dungeon table has no linked loot")
    return {"zone": unescape(title[1]), "min_level": int(minimum[1]), "groups": groups, "equipment_ids": sorted(gear)}


def recipe_table(payload):
    rows = []
    for entry in payload["rows"]:
        if not entry.get("out"):
            continue
        source = entry["src"]
        rows.append({"spell": entry["id"], "item": entry["out"], "skill": entry["k"][0],
                     "learn": source["t"], "patterns": sorted(entry["teach"])})
    if len(payload["rows"]) != payload["count"] or len({r["spell"] for r in rows}) != len(rows):
        raise ValueError("Incomplete or duplicate Forever recipes")
    return {"profession": payload["name"], "recipes": rows}


def quest_values(field):
    return list((field or {}).values())


def normalize_context(resolved, cache, area_table, inventory):
    requests = json.loads((cache / "state.json").read_bytes())["requests"]
    receipts = {}

    def cached(url):
        path = cache / "responses" / requests[url]["source_content_digest"]
        receipts[url] = sha(path)
        if path.name != receipts[url]:
            raise ValueError(f"Changed cached response for {url}")
        return path

    def exported(path):
        receipts[path.name] = sha(path)
        return json.loads(path.read_bytes())

    with area_table.open(encoding="utf-8-sig") as source:
        zones = {int(row["ID"]): row["AreaName_lang"] for row in csv.DictReader(source)}
    receipts[area_table.name] = sha(area_table)
    npcs = {row["id"]: [row["name"], zones.get(row.get("zoneID")), row.get("friendlyToFaction"),
                        row.get("minLevel")] for row in exported(resolved / "npcs.json") if row.get("name")}
    membership = {row["id"]: row for row in exported(resolved / "items.json") if row["id"] in inventory}
    npc_ids = {nid for row in membership.values() for key in ("npcDrops", "vendors") for nid in quest_values(row.get(key))}
    server = {}
    for url in sorted((u for u in requests if u.endswith("/" + BUILD + "/quests.enUS.json")
                       and requests[u].get("status") == 200), key=lambda u: requests[u]["collected_at"]):
        server.update(json.loads(cached(url).read_bytes())["quests"])
    server = {int(k): v for k, v in server.items()}
    profiles = sorted(resolved.glob("quests-*.json"))
    if len(profiles) != 18:
        raise ValueError("Expected both faction exports for all nine classes")
    quests = {row["id"]: row for row in exported(profiles[0])}
    differences = set()
    for path in profiles[1:]:
        other = {row["id"]: row for row in exported(path)}
        differences.update(i for i in quests.keys() | other.keys() if quests.get(i) != other.get(i))
    wanted = {i for i, v in server.items() if any(reward.get("itemId") in inventory
              for family in ("items", "choices") for reward in v.get("rewards", {}).get(family, []))}
    needed = list(wanted)
    quest_facts = {}
    while needed:
        i = needed.pop()
        if i in quest_facts or i not in quests:
            continue
        q, sv = quests[i], server.get(i, {})
        starts = [n for n in quest_values(q["startedBy"].get("1")) if n in npcs]
        prerequisite = quest_values(q.get("preQuestGroup"))
        alternatives = quest_values(q.get("preQuestSingle"))
        needed.extend(prerequisite + alternatives)
        gate = next((key for key in ("exclusiveTo", "requiredSkill", "requiredMinRep", "requiredMaxRep",
                    "requiredSpell", "parentQuest", "requiredSourceItems") if q.get(key)), None)
        if i in differences:
            gate = "character-dependent quest chain"
        if not sv or sv.get("minLevel") != q.get("requiredLevel") or sv.get("title") != q.get("name"):
            gate = "quest acceptance lacks matching server data"
        if not starts or not q["finishedBy"] or set(q["startedBy"]) != {"1"}:
            gate = "quest starter access"
        dungeon = sv.get("questInfoId") == 81
        if sv.get("questInfoId") not in (None, 1, 81) or sv.get("categoryId") in (22, 24, 41, 284, 366, 367, 374, 376):
            gate = "instance, event or PvP quest access"
        if len(alternatives) > 1 or any(n <= 0 for n in prerequisite + alternatives):
            gate = "alternative or exclusion prerequisites"
        start_zones = {npcs[n][1] for n in starts}
        npc_ids.update(starts)
        quest_facts[i] = {k: v for k, v in {
            "name": q.get("name"), "level": q["requiredLevel"], "max": q.get("requiredMaxLevel"),
            "classes": q["requiredClasses"], "races": q["requiredRaces"], "server_races": sv.get("raceMask"),
            "zone": zones.get(sv.get("zoneAreaId")) or (next(iter(start_zones)) if len(start_zones) == 1 else None),
            "dungeon": dungeon, "prerequisites": sorted(set(prerequisite + alternatives)), "gate": gate}.items() if v}
    sparse = {}
    with cached(ITEMS).open(encoding="utf-8-sig") as source:
        for row in csv.DictReader(source):
            i = int(row["ID"])
            if i in inventory:
                sparse[i] = [int(row[k] or 0) for k in ("Bonding", "RequiredSkill", "RequiredSkillRank",
                             "RequiredAbility", "MinReputation", "RequiredHoliday", "RequiredPVPRank", "MinFactionID")]
    return {"inputs": receipts, "npcs": {n: npcs[n] for n in sorted(npc_ids) if n in npcs},
            "quests": quest_facts, "item_access": sparse,
            "item_access_fields": ["bonding", "skill", "skill_rank", "ability", "reputation", "holiday", "pvp_rank", "faction"]}


def main():
    from tools.scrape_wowhead import write_snapshot

    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("pages", "resolved", "cache", "area-table"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--date", required=True)
    args = parser.parse_args()
    manifest = dataset_json("forever", "scrape_manifest")
    inventory = {row[0] for row in dataset_json("forever", "guide_equipment")["items"]}
    pages = [p for p in sorted(args.pages.glob("*.html")) if not p.name.startswith(("recipes-", "item-"))]
    if len(pages) != 28:
        raise ValueError("Expected all 28 released Forever dungeons")
    sources = []
    for p in pages:
        url = PLAYFULLS + "/loot-tables/dungeons/" + p.stem
        sources.append((url, "guide_dungeon_loot", {"content_sha256": sha(p), **dungeon_page(p.read_text(encoding="utf-8"))}))
    files = json.loads((args.pages / "boot.json").read_bytes())["files"]
    for skill, name in SKILLS.items():
        p = args.pages / f"skill-{skill}.json"
        url = PLAYFULLS + "/api/" + files[f"recipes__skill-{skill}"] + ".json"
        recipes = recipe_table(json.loads(p.read_bytes()))
        if recipes["profession"] != name:
            raise ValueError(f"Wrong recipe table for {name}")
        sources.append((url, "guide_recipes", {"content_sha256": sha(p), **recipes}))
    sources.append((CONTEXT, "guide_route_context", normalize_context(args.resolved, args.cache, args.area_table, inventory)))
    registered = {r["url"] for r in manifest["sources"]}
    for url, kind, facts in sources:
        provider = source_provider(url)
        if not provider:
            raise ValueError(f"Unregistered provider for {url}")
        if url not in registered:
            manifest["sources"].append({"url": url, "provider": provider, "data_family": "acquisition", "status": "source_reviewed"})
        write_snapshot({"url": url, "provider": provider, "flavor": "forever", "fetched_at": args.date,
                        "page_type": kind, **facts}, PROVIDER_RAW_DIR / provider)
    write_text(FOREVER_CANONICAL_DIR / "scrape_manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
