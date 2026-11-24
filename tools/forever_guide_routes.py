"""Reconcile individual Forever acquisition routes against both Gear Guide modes."""
from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

from tools.forever import read_snapshots, valid_source
from tools.forever_sources import route_leads
from tools.forever_route_intake import SKILLS as SKILL_NAMES
from tools.project import FOREVER_CANONICAL_DIR, FOREVER_RAW_DIR, ROOT, dataset_json, write_text
from tools.sources import summarize_sources


WOW = "https://www.wowhead.com/forever/"
CLASS_BITS = dict(Warrior=0, Paladin=1, Hunter=2, Rogue=3, Priest=4, Shaman=6, Mage=7, Warlock=8, Druid=10)
ZONE_NAMES = {"Deadmines": "The Deadmines", "Stormwind Stockade": "The Stockade",
              "The Temple of Atal'Hakkar": "Sunken Temple", "Temple of Atal'Hakkar": "Sunken Temple"}
BINDINGS = {0: "unbound", 1: "bind_on_pickup", 2: "bind_on_equip", 3: "bind_on_use", 4: "quest_item"}
RELATIONS = {"drops": "drop", "sells": "vendor", "creates": "crafted", "reward_choice": "quest", "rewards": "quest",
             "contains": "container"}


def entity(source):
    return source.get("quest_id") or source.get("spell_id") or source.get("entity_id")


def name_key(value):
    return (value or "").casefold().replace("’", "'").strip()


def equipment_records(inventory):
    by_id = {r["id"]: r for r in dataset_json("forever", "comparison_item_stats")["items"]}
    by_id.update((r[0], dict(zip(inventory["fields"], r))) for r in inventory["items"])
    return by_id


def route_keys(source):
    kind = source["type"]
    if entity(source):
        yield kind, entity(source)
    if source.get("entity_name"):
        yield kind, (ZONE_NAMES.get(source.get("zone"), source.get("zone")), name_key(source["entity_name"]))


def quest_branch(source):
    rule = source.get("eligibility", {})
    return (source.get("side"), tuple(sorted(rule.get("classes", []))), tuple(sorted(rule.get("races", []))),
            source.get("quest_starter_item_id"), tuple(sorted(step["quest_id"] for step in source.get("quest_steps", [])
                                                              if step["kind"] == "prerequisite")))


def add_catalog_routes(items, catalog, inventory):
    rows = {row["id"]: row for row in items}
    equipment = equipment_records(inventory)
    additions = defaultdict(list)
    for group in catalog["routes"]:
        source = group["source"]
        if not valid_source(source):
            raise ValueError(f"Invalid Forever Guide source {source}")
        for i in group["items"]:
            if (i not in equipment and i not in rows) or source in additions[i]:
                raise ValueError(f"Unknown or duplicate Forever route membership for {i}")
            additions[i].append(source)
    for i, extra in additions.items():
        base = rows.get(i)
        if base:
            row = dict(base)
        else:
            item = equipment[i]
            binding = catalog["bindings"].get(str(i), "unknown")
            row = {"id": i, "name": item["name"], "inventory_slot": item["slot"], "quality": item.get("quality"),
                   "binding": binding, "boe": None if binding == "unknown" else binding == "bind_on_equip",
                   "wowhead_url": WOW + f"item={i}", "acquisition_phase": "PR"}
        sources = [*row.get("sources", []), *extra]
        row.update(primary_source=sources[0], sources=sources, source_summary=summarize_sources(sources))
        rows[i] = row
    return [rows[i] for i in sorted(rows)]


def quest_routes(facts, races, dungeons):
    @lru_cache(None)
    def chain(i, seen=()):
        q = facts.get(str(i), {})
        if not q or q.get("gate") or i in seen or not q.get("level"):
            return None
        ids = []
        for parent in q.get("prerequisites", []):
            branch = chain(parent, (*seen, i))
            if not branch:
                return None
            ids.extend(branch)
        return tuple(dict.fromkeys([*ids, i]))

    def route(i, choice, url):
        ids = chain(i)
        if not ids:
            return None
        allowed, classes = {r["id"] for r in races}, set(CLASS_BITS)
        rules = [facts[str(n)] for n in ids]
        instances = {ZONE_NAMES.get(q.get("zone"), q.get("zone")) for q in rules if q.get("dungeon")}
        if not instances.issubset(dungeons):
            return None
        for q in rules:
            mask = q.get("races", 0)
            server = int(q.get("server_races", "ffffffffffffffff"), 16)
            for r in races:
                bit = {95: 32, 96: 33}.get(r["id"], r["id"] - 1)
                if (mask and not mask & (1 << bit)) or (server and not server & (1 << bit)):
                    allowed.discard(r["id"])
            if q.get("classes"):
                classes.intersection_update(k for k, bit in CLASS_BITS.items() if q["classes"] & (1 << bit))
        eligible = [r for r in races if r["id"] in allowed and classes.intersection(r["classes"])]
        sides = {r["faction"] for r in eligible}
        minimum = max([q["level"] for q in rules] + [dungeons[z] for z in instances])
        maximum = min(q.get("max", 60) for q in rules)
        if not sides or not 1 <= minimum <= maximum <= 60:
            return None
        rule = {"min_level": minimum}
        if maximum < 60:
            rule["max_level"] = maximum
        if len(classes) < len(CLASS_BITS):
            rule["classes"] = sorted(classes)
        q = rules[-1]
        source = {"type": "quest", "entity_name": q["name"], "quest_id": i, "reward_type": choice,
                  "side": next(iter(sides)) if len(sides) == 1 else "Both", "eligibility": rule, "source_url": url}
        if q.get("zone"):
            source["zone"] = q["zone"]
        if instances:
            source.update(content_type="dungeon", difficulty="Normal", activity_zones=sorted(instances))
        if len(ids) > 1:
            source["quest_steps"] = [{"quest_id": n, "name": facts[str(n)]["name"],
                "kind": "reward" if n == i else "prerequisite", "source_url": WOW + f"quest={n}",
                "reviewer": "Forever route reconciliation", "reviewed_at": "2026-11-20", "client_build": "1.60.1.70959",
                "reason": "Server quest acceptance and corrected Forever quest prerequisites."} for n in ids]
        # Skyborne has two client race IDs and one name. A faction-specific
        # mask must not remove the other faction's eligible Skyborne persona.
        names = {r["name"] for r in eligible}
        ambiguous = any(r["name"] in names and r["id"] not in allowed and r["faction"] in sides
                        and classes.intersection(r["classes"]) for r in races)
        branches = []
        for side in sorted(sides) if ambiguous else [source["side"]]:
            branch = dict(rule)
            if len(allowed) < len(races):
                branch["races"] = sorted({r["name"] for r in eligible if side in ("Both", r["faction"])})
            branches.append({**source, "side": side, "eligibility": branch})
        return branches
    return route


def collect(snapshots, inventory, existing, races):
    inventory_names = {i: r["name"] for i, r in equipment_records(inventory).items()}
    inventory_names.update((r["id"], r["name"]) for r in existing)
    equipment = set(inventory_names)
    context, = (s for s in snapshots.values() if s.get("page_type") == "guide_route_context")
    npcs, sparse = context["npcs"], context["item_access"]
    runtime = {r["id"]: r for r in existing}
    present = {i: {key for s in row["sources"] for key in route_keys(s)} for i, row in runtime.items()}
    quest_branches = defaultdict(set)
    for i, row in runtime.items():
        for s in row["sources"]:
            if s["type"] == "quest":
                quest_branches[i, entity(s)].add(quest_branch(s))
    templates = defaultdict(list)
    names = defaultdict(set)
    for row in existing:
        for s in row["sources"]:
            for key in route_keys(s):
                if s not in templates[key]:
                    templates[key].append(s)
    for nid, (name, zone, _, _) in npcs.items():
        names[name_key(name)].add(int(nid))
    for s in snapshots.values():
        if s.get("page_type") == "npc" and s.get("name") and s.get("entity_id"):
            names[name_key(s["name"])].add(s["entity_id"])
    leads = route_leads(snapshots, include_guide=True)
    groups, bindings, outcomes, added = {}, {}, {}, defaultdict(set)
    drops, recipes = {}, {}
    recipes_by_item = defaultdict(set)
    for url, s in sorted(snapshots.items()):
        if s.get("page_type") == "guide_dungeon_loot":
            zone = ZONE_NAMES.get(s["zone"], s["zone"])
            for name, members in s["groups"].items():
                matches = names[name_key(name)]
                zone_ids = {n for n in matches if (npcs.get(str(n)) or [None, None])[1] == zone}
                nid = next(iter(zone_ids)) if len(zone_ids) == 1 else next(iter(matches)) if len(matches) == 1 else None
                for i in equipment.intersection(members):
                    drops[i, zone, name] = (nid, url, s["min_level"])
        elif s.get("page_type") == "guide_recipes":
            for rec in s["recipes"]:
                if rec["item"] in equipment:
                    recipes[rec["item"], rec["spell"]] = (rec, url, s["profession"])
                    recipes_by_item[rec["item"]].add(rec["spell"])

    def binding(i):
        item = snapshots.get(WOW + f"item={i}", {})
        return (runtime.get(i, {}).get("binding") or item.get("binding") or
                BINDINGS.get((sparse.get(str(i)) or [None])[0], "unknown"))

    def admit(i, source, credit):
        keys = list(route_keys(source))
        already = (quest_branch(source) in quest_branches[i, entity(source)] if source["type"] == "quest" else
                   any(key in present.get(i, ()) for key in keys))
        if already:
            return "already indexed"
        source = {"available_from_phase": "PR", "confidence": "reviewed", **source, "attribution": credit}
        if not valid_source(source):
            raise ValueError(f"Invalid catalog route for {i}: {source}")
        key = json.dumps(source, sort_keys=True, separators=(",", ":"))
        groups.setdefault(key, set()).add(i)
        added[i].update(keys)
        bindings[str(i)] = binding(i)
        return "indexed"

    def current_credit(url):
        return snapshots[url].get("attribution") or [{"credit": "Wowhead Forever", "source": url}]

    play_credit = [{"credit": "Playfulls Forever loot and recipe tables", "source": "https://playfulls.com"}]
    quest_credit = context.get("attribution") or [{"credit": "QuestieDB corrected Forever data", "source": context["url"]}]
    dungeon_levels = {ZONE_NAMES.get(s["zone"], s["zone"]): s["min_level"] for s in snapshots.values()
                      if s.get("page_type") == "guide_dungeon_loot"}
    quest = quest_routes(context["quests"], races, dungeon_levels)
    for (i, zone, name), (nid, url, minimum) in drops.items():
        source = {"type": "drop", "zone": zone, "content_type": "dungeon", "difficulty": "Normal",
                  "entity_name": "Trash mobs" if name == "Trash" else name, "side": "Both",
                  "source_url": url, "eligibility": {"min_level": minimum}}
        if nid:
            source["entity_id"] = nid
        prior = templates.get(("drop", nid), [])
        if prior:
            # Encounter keys, summoning instructions and already reviewed access gates belong to the boss.
            ref = max(prior, key=lambda r: (bool(r.get("location_note")), bool(r.get("eligibility"))))
            for field in ("side", "requirements", "location_note", "destination"):
                if field in ref:
                    source[field] = ref[field]
            if ref.get("eligibility"):
                source["eligibility"] = {**ref["eligibility"], "min_level": max(minimum, ref["eligibility"]["min_level"])}
        outcomes[i, "drop", nid or (zone, name)] = admit(i, source, play_credit)

    for i in sorted(equipment):
        by_edge = defaultdict(list)
        raw = leads.get(i, [])
        tooltip_names = {name_key(e.get("entity_name")) for e in raw if e.get("confidence") == "wowhead_tooltip"
                         and e.get("type") == "drop"}
        for e in raw:
            kind = RELATIONS.get(e.get("relation"))
            n = e.get("subject_id")
            if not kind or not isinstance(n, int):
                if e.get("confidence") == "guide_lead" and e.get("entity_type") in ("npc", "quest", "spell"):
                    outcomes[i, "guide", (e["entity_type"], e.get("entity_id"))] = "guide association needs corroboration"
                continue
            by_edge[kind, n].append(e)
        for name in tooltip_names:
            if not any(("drop", n) in by_edge or ("drop", n) in present.get(i, ()) or ("drop", n) in added[i]
                       for n in names[name]):
                known = set(present.get(i, ())) | added[i]
                covered = any(kind == "drop" and isinstance(target, tuple) and target[1] == name for kind, target in known)
                outcomes[i, "drop", name] = "already indexed" if covered else "named drop location or encounter unconfirmed"
        for n in recipes_by_item.get(i, ()):
            by_edge.setdefault(("crafted", n), [])
        for (kind, n), edges in sorted(by_edge.items()):
            key = i, kind, n
            if key in outcomes:
                continue
            npc = npcs.get(str(n))
            template = templates.get((kind, n), [])
            if (kind, n) in present.get(i, ()) or (kind, n) in added[i]:
                if kind != "quest" or all(quest_branch(t) in quest_branches[i, n] for t in template):
                    outcomes[key] = "already indexed"
                    continue
            if kind == "drop":
                # Outdoor random loot observed on one creature is not a farm target.
                npc_page = snapshots.get(WOW + f"npc={n}", {})
                exact_name = npc and name_key(npc[0]) in tooltip_names
                observed = any(e.get("confidence") in {"corroborated_observation", "eg_link_observation",
                               "current_forever_drop", "observed_forever_loot"} and e.get("subject_type") == "npc" for e in edges)
                if npc and npc[1] and exact_name and ("(Rare" in npc_page.get("description", "") or template):
                    source = {"type": "drop", "entity_name": npc[0], "entity_id": n, "content_type": "other",
                              "zone": npc[1], "side": "Both", "eligibility": {"min_level": max(1, min(npc[3] or 1, 60))}}
                    if template:
                        source.update({k: v for k, v in template[0].items() if k in
                            {"zone", "side", "difficulty", "content_type", "eligibility", "requirements", "location_note"}})
                    url = WOW + f"item={i}"
                    outcomes[key] = admit(i, {**source, "source_url": url}, current_credit(url))
                else:
                    outcomes[key] = "raid or historical source" if any(e.get("subject_type") == "raid" or
                        e.get("availability") in {"retired_legacy_route", "phase_gated"} for e in edges) else (
                        "named target or access unconfirmed" if exact_name or observed else "uncorroborated drop")
            elif kind == "quest":
                confirmed = [e for e in edges if e.get("confidence") in {"eg_link_observation", "wowhead_rendered_quest",
                             "published_forever_server_observation", "observed_forever_server_quest", "server_quest_cache"}]
                if not confirmed or len({e["relation"] for e in confirmed}) != 1:
                    outcomes[key] = "reward or choice unconfirmed"
                    continue
                e = confirmed[0]
                url = e["evidence_url"]
                choice = "choice" if e["relation"] == "reward_choice" else "guaranteed"
                if template:
                    # Keep separately reviewed faction/entry branches of the same exact quest.
                    for t in template:
                        admit(i, {**t, "reward_type": choice}, t.get("attribution") or current_credit(url))
                    outcomes[key] = "indexed"
                else:
                    branches = quest(n, choice, WOW + f"quest={n}")
                    if branches:
                        for source in branches:
                            outcomes[key] = admit(i, source, [*quest_credit, *current_credit(url)])
                    else:
                        outcomes[key] = context["quests"].get(str(n), {}).get("gate") or "quest chain access unconfirmed"
            elif kind == "vendor":
                price, standing = None, None
                for e in edges:
                    stock = e.get("stock", {})
                    if e.get("confidence") == "wowhead_rendered_listview" and e.get("price_copper", 0) > 0:
                        price = e["price_copper"]
                    elif stock and not stock.get("costItems") and not stock.get("bartered"):
                        # Preserve the standing at which this particular price was observed.
                        for rank, label in (("4", None), ("5", "Friendly"), ("6", "Honored"), ("7", "Revered"), ("8", "Exalted")):
                            if stock.get("costs", {}).get(rank, 0) > 0:
                                price, standing = stock["costs"][rank], label
                                break
                    if price:
                        break
                side = {"AH": "Both", "A": "Alliance", "H": "Horde"}.get(npc[2]) if npc else None
                access = sparse.get(str(i))
                if price and side and npc[1] and access and not any(access[3:]):
                    url = e["evidence_url"]
                    source = {"type": "vendor", "entity_id": n, "entity_name": npc[0], "zone": npc[1], "side": side,
                              "price_copper": price, "eligibility": {"min_level": 1}, "source_url": url}
                    notes = []
                    if standing:
                        notes.append(f"Price recorded at {standing} standing.")
                    if stock.get("limited"):
                        notes.append("Limited vendor stock.")
                    if notes:
                        source["location_note"] = " ".join(notes)
                    if stock.get("stack", 1) > 1:
                        source["purchase_quantity"] = stock["stack"]
                    outcomes[key] = admit(i, source, current_credit(url))
                else:
                    outcomes[key] = "vendor access, stock or cost unconfirmed"
            elif kind == "crafted":
                recipe = recipes.get((i, n))
                if not recipe:
                    outcomes[key] = "recipe learning source unconfirmed"
                    continue
                rec, url, profession = recipe
                known_pattern = any(any(e.get("confidence") in {"wowhead_rendered_listview", "eg_link_observation",
                    "observed_auction_listing", "corroborated_observation"} for e in leads.get(pattern, []))
                    for pattern in rec["patterns"])
                learnable = rec["learn"] in ("trainer", "auto") or (rec["learn"] in ("vendor", "drop") and known_pattern)
                transferable = binding(i) in ("bind_on_equip", "unbound", "bind_on_use")
                access = sparse.get(str(i))
                if not learnable or not transferable or (access and any(access[3:])):
                    outcomes[key] = "recipe, binding or personal crafting gates unconfirmed"
                    continue
                source = {"type": "crafted", "entity_name": inventory_names[i], "profession": profession,
                          "spell_id": n, "side": "Both", "eligibility": {"min_level": 1}, "source_url": url}
                if access and access[1]:
                    if access[1] not in SKILL_NAMES:
                        outcomes[key] = "wearer profession unconfirmed"
                        continue
                    source["requirements"] = [{"type": "profession", "scope": "equip_or_use", "skill": access[2],
                                               "profession": SKILL_NAMES[access[1]]}]
                outcomes[key] = admit(i, source, play_credit)
            else:
                outcomes[key] = "container access unconfirmed"
    catalog = {"routes": [{"source": json.loads(key), "items": sorted(ids)} for key, ids in sorted(groups.items())],
               "bindings": bindings}
    return catalog, outcomes


def reconcile(snapshots):
    from tools.generate_lua import forever_items

    inventory = dataset_json("forever", "guide_equipment")
    base, _ = forever_items(dataset_json("forever", "items")["items"], [], include_route_catalog=False)
    new, outcomes = collect(snapshots, inventory, base, dataset_json("forever", "leveling_rules")["races"])
    published = add_catalog_routes(base, new, inventory)
    by_id = {row["id"]: row for row in published}
    dungeon_items = set()
    dungeon_pairs = set()
    for page in snapshots.values():
        if page.get("page_type") != "guide_dungeon_loot":
            continue
        zone = ZONE_NAMES.get(page["zone"], page["zone"])
        gear = set(page["equipment_ids"])
        dungeon_items.update(gear)
        for boss, members in page["groups"].items():
            name = "Trash mobs" if boss == "Trash" else boss
            for i in gear.intersection(members):
                dungeon_pairs.add((i, zone, name))
                if not any(("drop", (zone, name_key(name))) in route_keys(source)
                           for source in by_id.get(i, {}).get("sources", [])):
                    raise ValueError(f"Missing Forever dungeon equipment or route: {i}, {name}, {zone}")
    totals = Counter(outcomes.values())
    report = {"equipment": len(set(equipment_records(inventory)) | set(by_id)), "reviewed_items": len(published),
              "dungeon_equipment": len(dungeon_items), "dungeon_equipment_routes": len(dungeon_pairs),
              "additional_routes": sum(len(g["items"]) for g in new["routes"]), "additional_items": len(new["bindings"]),
              "by_type": dict(Counter(g["source"]["type"] for g in new["routes"] for _ in g["items"])),
              "dispositions": dict(sorted(totals.items()))}
    return new, outcomes, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--audit", type=Path, help="Write the disposition of every equipment/source edge.")
    parser.add_argument("--lua", help="Also check the published target pages in Lua 5.1.")
    args = parser.parse_args()
    new, outcomes, report = reconcile(read_snapshots(FOREVER_RAW_DIR))
    path = FOREVER_CANONICAL_DIR / "guide_routes.json"
    if args.write:
        bindings = json.dumps(new["bindings"], indent=2, sort_keys=True)
        groups = [json.dumps(g, ensure_ascii=False, sort_keys=True, separators=(",", ":")) for g in new["routes"]]
        write_text(path, '{\n  "bindings": ' + bindings.replace("\n", "\n  ") + ',\n  "routes": [\n    '
                   + ",\n    ".join(groups) + "\n  ]\n}\n")
    if not path.is_file() or json.loads(path.read_bytes()) != new:
        raise SystemExit("Guide route catalog is stale. Run python -m tools.forever_guide_routes --write.")
    if args.lua:
        ids = {i for group in new["routes"] for i in group["items"]}
        ids.update(i for r in dataset_json("forever", "guide_source_reviews")["routes"] for i in r["item_ids"])
        ids.update(r["id"] for r in dataset_json("forever", "guide_item_reviews")["items"])
        run = subprocess.run([args.lua, "tools/audit_forever_guide_routes.lua"], cwd=ROOT, check=True,
                             input="".join(f"{i}\n" for i in sorted(ids)), stdout=subprocess.PIPE, text=True)
        report["published_guide"] = json.loads(run.stdout)
    print(json.dumps(report, sort_keys=True))
    if args.audit:
        report["edges"] = [[*key, value] for key, value in sorted(outcomes.items(), key=lambda entry: str(entry[0]))]
        write_text(args.audit, json.dumps(report, ensure_ascii=False, separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main()
