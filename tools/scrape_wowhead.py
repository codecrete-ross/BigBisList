from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.manifest_coverage import build_manifest_coverage
from tools.project import CANONICAL_DIR, PHASE_KEYS, RAW_WOWHEAD_DIR, SLOT_NAMES, canonical_json, write_text
from tools.sources import derive_primary_source, summarize_sources
from tools.validate_data import validate

PARSER_VERSION = "wowhead-scraper-0.4.0"
USER_AGENT = "BigBiSListScraper/0.4 (+https://github.com/codecrete-dev/BigBisList)"

CURRENCY_NAMES = {
    1900: "Arena Points",
    1901: "Honor Points",
    29434: "Badge of Justice",
}

ZONE_ID_NAMES = {
    440: "Tanaris",
    2017: "Stratholme",
    3457: "Karazhan",
    3518: "Nagrand",
    3520: "Shadowmoon Valley",
    3522: "Blade's Edge Mountains",
    3523: "Netherstorm",
    3606: "Hyjal Summit",
    3607: "Serpentshrine Cavern",
    3703: "Shattrath City",
    3836: "Magtheridon's Lair",
    3845: "Tempest Keep",
    3923: "Gruul's Lair",
    3959: "Black Temple",
    4075: "Sunwell Plateau",
}

SLOT_PATTERNS = [
    ("Head", r"\bheads?\b|\bhelm"),
    ("Neck", r"\bnecks?\b"),
    ("Shoulder", r"\bshoulders?\b"),
    ("Back", r"\bbacks?\b|\bcloaks?\b"),
    ("Chest", r"\bchests?\b"),
    ("Wrist", r"\bwrists?\b|\bbracers?\b"),
    ("Main Hand", r"\bmain[- ]hand\b"),
    ("Off Hand", r"\boff[- ]hand\b"),
    ("Two Hand", r"\btwo[- ]hand\b|\b2h\b"),
    ("Dual Wield", r"\bdual wield\b"),
    ("Hands", r"\bhands?\b|\bgloves?\b"),
    ("Waist", r"\bwaists?\b|\bbelts?\b"),
    ("Legs", r"\blegs?\b|\bleggings?\b"),
    ("Feet", r"\bfeet\b|\bboots?\b"),
    ("Ring", r"\brings?\b"),
    ("Trinket", r"\btrinkets?\b"),
    ("Ranged", r"\branged\b|\bwands?\b"),
    ("Idol", r"\bidols?\b"),
    ("Totem", r"\btotems?\b"),
    ("Libram", r"\blibrams?\b"),
    ("Relic", r"\brelics?\b"),
]


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def snapshot_name(url: str) -> str:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    slug = re.sub(r"[^a-z0-9]+", "-", url.lower()).strip("-")[-80:]
    return f"{slug}-{digest}.json"


def html_cache_name(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest() + ".html"


def absolute_tbc_url(href: str) -> str:
    if href.startswith("https://www.wowhead.com/tbc/"):
        return href
    if href.startswith("/tbc/"):
        return "https://www.wowhead.com" + href
    return href


def page_type_for_url(url: str) -> str:
    if "/guide/" in url:
        return "guide"
    if "/item=" in url:
        return "item"
    if "/spell=" in url:
        return "spell"
    return "unknown"


def item_id_from_href(href: str) -> int | None:
    match = re.search(r"/item=(\d+)", href)
    return int(match.group(1)) if match else None


def spell_id_from_href(href: str) -> int | None:
    match = re.search(r"/spell=(\d+)", href)
    return int(match.group(1)) if match else None


def entity_id_from_href(href: str, entity: str) -> int | None:
    match = re.search(rf"/{re.escape(entity)}=(\d+)", href)
    return int(match.group(1)) if match else None


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def element_text(element: Any) -> str:
    return clean_text(element.get_text(" ", strip=True))


def item_tooltip_text(item_id: int | None, html: str) -> str:
    if not item_id:
        return ""
    match = re.search(rf"g_items\[{item_id}\]\.tooltip_enus\s*=\s*\"((?:\\.|[^\"])*)\";", html)
    if not match:
        return ""
    try:
        tooltip_html = json.loads(f"\"{match.group(1)}\"")
    except json.JSONDecodeError:
        return ""
    return element_text(BeautifulSoup(tooltip_html, "html.parser"))


def parse_binding_from_text(text: str) -> tuple[str, bool | None]:
    lowered = text.lower()
    if "binds when equipped" in lowered:
        return "bind_on_equip", True
    if "binds when picked up" in lowered:
        return "bind_on_pickup", False
    if "binds when used" in lowered:
        return "bind_on_use", None
    if re.search(r"\bquest item\b", lowered):
        return "quest", False
    return "unknown", None


def slot_from_heading(heading: str) -> str | None:
    normalized = heading.lower()
    for slot, pattern in SLOT_PATTERNS:
        if re.search(pattern, normalized):
            return slot
    return None


def data_family_from_heading(heading: str) -> str:
    normalized = heading.lower()
    if slot_from_heading(heading):
        return "bis_lists"
    if "gem" in normalized or "socket" in normalized:
        return "gems"
    if "enchant" in normalized or "enchantment" in normalized:
        return "enchants"
    if any(token in normalized for token in ["consumable", "flask", "elixir", "potion", "food", "weapon buff"]):
        return "consumables"
    if any(token in normalized for token in ["leveling", "rotation", "talent", "stat priority"]):
        return "leveling"
    return "unknown"


def nearest_heading(table: Any) -> str:
    for previous in table.find_all_previous(["h2", "h3", "h4"]):
        text = element_text(previous)
        if text:
            return text
    return ""


def entity_from_link(link: Any) -> dict[str, Any] | None:
    href = link.get("href", "")
    item_id = item_id_from_href(href)
    if item_id:
        return {
            "type": "item",
            "id": item_id,
            "name": element_text(link),
            "url": absolute_tbc_url(href),
        }
    spell_id = spell_id_from_href(href)
    if spell_id:
        return {
            "type": "spell",
            "id": spell_id,
            "name": element_text(link),
            "url": absolute_tbc_url(href),
        }
    return None


def unique_entities(links: list[Any]) -> list[dict[str, Any]]:
    entities: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for link in links:
        entity = entity_from_link(link)
        if not entity:
            continue
        key = (entity["type"], entity["id"])
        if key in seen:
            continue
        seen.add(key)
        entities.append(entity)
    return entities


def parse_guide_html(url: str, html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    title = element_text(soup.title) if soup.title else ""
    tables: list[dict[str, Any]] = []

    for table in soup.find_all("table"):
        heading = nearest_heading(table)
        slot = slot_from_heading(heading)
        data_family = data_family_from_heading(heading)
        rows: list[dict[str, Any]] = []

        for tr in table.find_all("tr"):
            cells = tr.find_all(["td", "th"])
            if len(cells) < 2:
                continue
            if any(cell.name == "th" for cell in cells):
                continue

            entities = unique_entities(tr.find_all("a", href=True))
            if not entities:
                continue

            primary_entity = entities[0]
            primary_item = next((entity for entity in entities if entity["type"] == "item"), None)
            primary_spell = next((entity for entity in entities if entity["type"] == "spell"), None)
            source_cell = cells[2] if len(cells) > 2 else cells[-1]
            source_links = [
                {
                    "href": absolute_tbc_url(link["href"]),
                    "text": element_text(link),
                }
                for link in source_cell.find_all("a", href=True)
            ]
            row = {
                "rank_label": element_text(cells[0]),
                "entity_type": primary_entity["type"],
                "entity_id": primary_entity["id"],
                "entity_name": primary_entity["name"],
                "entity_url": primary_entity["url"],
                "entities": entities,
                "cells": [element_text(cell) for cell in cells],
                "source_text": element_text(source_cell),
                "source_links": source_links,
            }
            if primary_item:
                row["item_id"] = primary_item["id"]
                row["item_name"] = primary_item["name"]
                row["item_url"] = primary_item["url"]
            if primary_spell:
                row["spell_id"] = primary_spell["id"]
                row["spell_name"] = primary_spell["name"]
                row["spell_url"] = primary_spell["url"]
            rows.append(row)

        if rows:
            tables.append({"heading": heading, "slot": slot, "data_family": data_family, "rows": rows})

    return {
        "parser_version": PARSER_VERSION,
        "url": url,
        "fetched_at": now_utc(),
        "page_type": "guide",
        "title": title,
        "tables": tables,
    }


def extract_balanced_json_array(text: str, start: int) -> str | None:
    array_start = text.find("[", start)
    if array_start < 0:
        return None

    depth = 0
    in_string = False
    escape = False
    for index in range(array_start, len(text)):
        char = text[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                return text[array_start : index + 1]
    return None


def extract_listview_data(html: str, listview_id: str) -> list[dict[str, Any]]:
    id_match = re.search(rf"id:\s*['\"]{re.escape(listview_id)}['\"]", html)
    if not id_match:
        return []
    data_match = re.search(r"data:\s*", html[id_match.end() :])
    if not data_match:
        return []
    array_text = extract_balanced_json_array(html, id_match.end() + data_match.end())
    if not array_text:
        return []
    try:
        data = json.loads(array_text)
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def first_zone_name(row: dict[str, Any]) -> str | None:
    locations = row.get("location")
    if isinstance(locations, list) and locations:
        return ZONE_ID_NAMES.get(int(locations[0]))
    category = row.get("category")
    if isinstance(category, int):
        return ZONE_ID_NAMES.get(category)
    return None


def parse_costs(raw_cost: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_cost, list):
        return []
    costs: list[dict[str, Any]] = []

    cost_groups = raw_cost
    if raw_cost and isinstance(raw_cost[0], (int, float)):
        cost_groups = [raw_cost]

    for cost_group in cost_groups:
        if not isinstance(cost_group, list):
            continue
        for bucket in cost_group[1:]:
            if not isinstance(bucket, list):
                continue
            for entry in bucket:
                if not isinstance(entry, list) or len(entry) < 2:
                    continue
                cost_id = int(entry[0])
                amount = int(entry[1])
                cost: dict[str, Any] = {"amount": amount, "name": CURRENCY_NAMES.get(cost_id, f"Item {cost_id}")}
                if cost_id in CURRENCY_NAMES:
                    cost["currency_id"] = cost_id
                else:
                    cost["item_id"] = cost_id
                costs.append(cost)
    return costs


def pct_from_row(row: dict[str, Any]) -> float | None:
    count = row.get("count")
    out_of = row.get("outof") or row.get("out_of")
    if isinstance(count, (int, float)) and isinstance(out_of, (int, float)) and out_of:
        return round(100.0 * float(count) / float(out_of), 2)
    return None


def normalize_item_sources(url: str, tables: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []

    for row in tables.get("dropped-by", []):
        source = {
            "type": "drop",
            "entity_id": row.get("id"),
            "entity_name": row.get("name"),
            "zone": first_zone_name(row),
            "count": row.get("count"),
            "out_of": row.get("outof"),
            "drop_percent": pct_from_row(row),
            "source_url": url,
            "confidence": "wowhead_item",
        }
        sources.append({key: value for key, value in source.items() if value is not None})

    for row in tables.get("reward-from-q", []):
        side = row.get("side")
        source = {
            "type": "quest",
            "entity_id": row.get("id"),
            "entity_name": row.get("name"),
            "quest_id": row.get("id"),
            "zone": first_zone_name(row),
            "side": {1: "Alliance", 2: "Horde"}.get(side),
            "source_url": url,
            "confidence": "wowhead_item",
        }
        sources.append({key: value for key, value in source.items() if value is not None})

    for row in tables.get("sold-by", []):
        costs = parse_costs(row.get("cost"))
        source_type = "pvp" if any(cost.get("currency_id") in {1900, 1901} for cost in costs) else "vendor"
        source = {
            "type": source_type,
            "entity_id": row.get("id"),
            "entity_name": row.get("name"),
            "vendor_id": row.get("id"),
            "zone": first_zone_name(row),
            "costs": costs,
            "source_url": url,
            "confidence": "wowhead_item",
        }
        sources.append({key: value for key, value in source.items() if value not in (None, [])})

    for row in tables.get("created-by", []):
        source = {
            "type": "crafted",
            "entity_id": row.get("id"),
            "entity_name": row.get("name"),
            "profession": row.get("skill"),
            "source_url": url,
            "confidence": "wowhead_item",
        }
        sources.append({key: value for key, value in source.items() if value is not None})

    if len(sources) > 8 and all(source.get("type") == "drop" for source in sources):
        max_drop = max((float(source.get("drop_percent") or 0) for source in sources), default=0)
        if max_drop < 1:
            return [
                {
                    "type": "world_drop",
                    "entity_name": "World Drop",
                    "world_drop": True,
                    "source_url": url,
                    "confidence": "wowhead_item",
                }
            ]

    return sources


def parse_quality_from_description(description: str) -> str:
    lowered = description.lower()
    if " epic " in f" {lowered} ":
        return "epic"
    if " blue " in f" {lowered} ":
        return "rare"
    if " green " in f" {lowered} ":
        return "uncommon"
    if " white " in f" {lowered} ":
        return "common"
    if " legendary " in f" {lowered} ":
        return "legendary"
    return "unknown"


def parse_item_html(url: str, html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    title = element_text(soup.title) if soup.title else ""
    name = re.sub(r"\s+-\s+Item\s+-\s+TBC Classic.*$", "", title).strip()
    meta = soup.find("meta", attrs={"name": "description"})
    description = meta.get("content", "") if meta else ""
    item_id = item_id_from_href(url)
    binding, boe = parse_binding_from_text(item_tooltip_text(item_id, html) or description)
    listview_ids = ["dropped-by", "sold-by", "reward-from-q", "created-by"]
    related_tables = {listview_id: extract_listview_data(html, listview_id) for listview_id in listview_ids}
    sources = normalize_item_sources(url, related_tables)

    return {
        "parser_version": PARSER_VERSION,
        "url": url,
        "fetched_at": now_utc(),
        "page_type": "item",
        "item_id": item_id,
        "name": name,
        "quality": parse_quality_from_description(description),
        "binding": binding,
        "boe": boe,
        "description": clean_text(description),
        "related_tables": related_tables,
        "normalized_sources": sources,
    }


def normalize_spell_sources(url: str, tables: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []

    for row in tables.get("taught-by-item", []):
        source = {
            "type": "taught_by_item",
            "item_id": row.get("id"),
            "entity_id": row.get("id"),
            "entity_name": row.get("name"),
            "source_url": url,
            "confidence": "wowhead_spell",
        }
        sources.append({key: value for key, value in source.items() if value is not None})

    for row in tables.get("sold-by", []):
        source = {
            "type": "vendor",
            "vendor_id": row.get("id"),
            "entity_id": row.get("id"),
            "entity_name": row.get("name"),
            "zone": first_zone_name(row),
            "costs": parse_costs(row.get("cost")),
            "source_url": url,
            "confidence": "wowhead_spell",
        }
        sources.append({key: value for key, value in source.items() if value not in (None, [])})

    for row in tables.get("reward-from-q", []):
        source = {
            "type": "quest",
            "quest_id": row.get("id"),
            "entity_id": row.get("id"),
            "entity_name": row.get("name"),
            "zone": first_zone_name(row),
            "source_url": url,
            "confidence": "wowhead_spell",
        }
        sources.append({key: value for key, value in source.items() if value is not None})

    return sources


def parse_spell_html(url: str, html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    title = element_text(soup.title) if soup.title else ""
    name = re.sub(r"\s+-\s+Spell\s+-\s+TBC Classic.*$", "", title).strip()
    listview_ids = ["taught-by-item", "sold-by", "reward-from-q", "created-by"]
    related_tables = {listview_id: extract_listview_data(html, listview_id) for listview_id in listview_ids}
    return {
        "parser_version": PARSER_VERSION,
        "url": url,
        "fetched_at": now_utc(),
        "page_type": "spell",
        "spell_id": spell_id_from_href(url),
        "name": name,
        "related_tables": related_tables,
        "normalized_sources": normalize_spell_sources(url, related_tables),
    }


def normalize_html(url: str, html: str) -> dict[str, Any]:
    page_type = page_type_for_url(url)
    if page_type == "guide":
        return parse_guide_html(url, html)
    if page_type == "item":
        return parse_item_html(url, html)
    if page_type == "spell":
        return parse_spell_html(url, html)
    return {
        "parser_version": PARSER_VERSION,
        "url": url,
        "fetched_at": now_utc(),
        "page_type": "unknown",
    }


def fetch_url(url: str, cache_dir: Path, retries: int = 3, delay: float = 0.75) -> str:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / html_cache_name(url)
    if cache_path.is_file():
        return cache_path.read_text(encoding="utf-8")

    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            request = Request(url, headers={"User-Agent": USER_AGENT})
            with urlopen(request, timeout=30) as response:
                html = response.read().decode("utf-8", errors="replace")
            write_text(cache_path, html)
            if delay:
                time.sleep(delay)
            return html
        except URLError as exc:
            last_error = exc
            time.sleep(delay * (attempt + 1))
    raise RuntimeError(f"failed to fetch {url}: {last_error}")


def write_snapshot(snapshot: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / snapshot_name(snapshot["url"])
    write_text(output_path, json.dumps(snapshot, indent=2, sort_keys=True) + "\n")
    return output_path


def manifest_urls() -> list[str]:
    manifest = canonical_json("scrape_manifest")
    return sorted({source["url"] for source in manifest.get("sources", []) if source.get("url")})


def manifest_sources_by_url() -> dict[str, list[dict[str, Any]]]:
    manifest = canonical_json("scrape_manifest")
    sources_by_url: dict[str, list[dict[str, Any]]] = {}
    for source in manifest.get("sources", []):
        if source.get("url"):
            sources_by_url.setdefault(source["url"], []).append(source)
    return sources_by_url


def manifest_sources_for_snapshot(snapshot: dict[str, Any], data_family: str) -> list[dict[str, Any]]:
    sources = manifest_sources_by_url().get(snapshot.get("url"), [])
    matches: list[dict[str, Any]] = []
    for source in sources:
        families = source.get("data_families")
        if isinstance(families, list) and data_family in families:
            matches.append(source)
        elif source.get("data_family") == data_family:
            matches.append(source)
    return matches


def manifest_source_for_snapshot(snapshot: dict[str, Any], data_family: str) -> dict[str, Any]:
    matches = manifest_sources_for_snapshot(snapshot, data_family)
    return matches[0] if matches else {}


def canonical_item_urls() -> list[str]:
    return [item["wowhead_url"] for item in canonical_json("items").get("items", []) if item.get("wowhead_url")]


def item_url_for_id(item_id: int) -> str:
    return f"https://www.wowhead.com/tbc/item={item_id}"


def discover_entity_urls(snapshots: list[dict[str, Any]], entity_type: str | None = None) -> list[str]:
    urls: set[str] = set()
    for snapshot in snapshots:
        if snapshot.get("page_type") != "guide":
            continue
        for table in snapshot.get("tables", []):
            for row in table.get("rows", []):
                for entity in row.get("entities", []):
                    if entity_type and entity.get("type") != entity_type:
                        continue
                    if entity.get("url"):
                        urls.add(entity["url"])
    return sorted(urls)


def discover_item_urls(snapshots: list[dict[str, Any]]) -> list[str]:
    return discover_entity_urls(snapshots, "item")


def item_cost_ids_from_sources(sources: list[dict[str, Any]]) -> set[int]:
    item_ids: set[int] = set()
    for source in sources:
        for cost in source.get("costs", []):
            item_id = cost.get("item_id")
            if isinstance(item_id, int) and item_id > 0:
                item_ids.add(item_id)
    return item_ids


def discover_token_item_urls(snapshots: list[dict[str, Any]]) -> list[str]:
    item_ids: set[int] = set()
    for snapshot in snapshots:
        if snapshot.get("page_type") != "item":
            continue
        item_ids.update(item_cost_ids_from_sources(snapshot.get("normalized_sources", [])))
    return [item_url_for_id(item_id) for item_id in sorted(item_ids)]


def command_fetch(args: argparse.Namespace) -> int:
    output_dir = args.output_dir
    cache_dir = output_dir / "html_cache"
    urls = sorted(set(args.url or manifest_urls()))
    seen_urls: set[str] = set()
    snapshots: list[dict[str, Any]] = []
    queue = list(urls)

    while queue:
        url = queue.pop(0)
        if url in seen_urls:
            continue
        seen_urls.add(url)
        html = fetch_url(url, cache_dir, retries=args.retries, delay=args.delay)
        snapshot = normalize_html(url, html)
        write_snapshot(snapshot, output_dir)
        snapshots.append(snapshot)
        print(f"snapshot {snapshot['page_type']}: {url}")

        if not args.no_discover:
            discovered = sorted(set(discover_entity_urls(snapshots) + canonical_item_urls() + discover_token_item_urls(snapshots)) - seen_urls - set(queue))
            queue.extend(discovered)

    return 0


def load_snapshots(input_dir: Path) -> list[dict[str, Any]]:
    snapshots = []
    for path in sorted(input_dir.glob("*.json")):
        if path.name == "last_snapshot.json":
            continue
        with path.open("r", encoding="utf-8") as handle:
            snapshot = json.load(handle)
        if isinstance(snapshot, dict) and snapshot.get("parser_version"):
            snapshots.append(snapshot)
    return snapshots


def rank_group_from_label(label: str) -> str:
    lowered = label.lower()
    if "bis" in lowered and "(" in lowered:
        return "situational_bis"
    if lowered == "bis":
        return "bis"
    if "option" in lowered or "alternative" in lowered or "viable" in lowered:
        return "option"
    if "pvp" in lowered:
        return "pvp"
    if re.search(r"\d", lowered):
        return "ranked"
    return "option"


def context_from_rank_label(label: str) -> str:
    lowered = label.lower()
    if "personal" in lowered:
        return "personal_dps"
    if "raid" in lowered:
        return "raid_dps"
    if "threat" in lowered and "jewel" in lowered:
        return "threat_jewelcrafting"
    if "threat" in lowered:
        return "threat"
    if "jewel" in lowered:
        return "jewelcrafting"
    if "world boss" in lowered:
        return "world_boss"
    if "expensive" in lowered:
        return "expensive"
    if "unrealistic" in lowered and ("alternative" in lowered or "option" in lowered or "viable" in lowered):
        return "unrealistic_option"
    if "unrealistic" in lowered:
        return "unrealistic"
    if "pvp" in lowered:
        return "pvp"
    if "option" in lowered or "alternative" in lowered or "viable" in lowered:
        return "option"
    return "standard"


def import_bis_lists_from_snapshots(snapshots: list[dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []

    for snapshot in snapshots:
        if snapshot.get("page_type") != "guide":
            continue
        for source_meta in manifest_sources_for_snapshot(snapshot, "bis_lists"):
            class_name = source_meta.get("class")
            spec_name = source_meta.get("spec")
            if not class_name or not spec_name:
                continue

            for table in snapshot.get("tables", []):
                if table.get("data_family") not in (None, "bis_lists", "unknown"):
                    continue
                slot = table.get("slot")
                if not slot:
                    continue
                items_by_phase: dict[str, list[dict[str, Any]]] = {}
                seen_by_phase: dict[str, set[tuple[int, str]]] = {}
                for row in table.get("rows", []):
                    item_id = row.get("item_id")
                    phase = phase_from_row(source_meta, table, row)
                    if not phase:
                        continue
                    rank_label = row.get("rank_label") or "Option"
                    context = context_from_rank_label(rank_label)
                    key = (item_id, context)
                    seen = seen_by_phase.setdefault(phase, set())
                    if not item_id or key in seen:
                        continue
                    seen.add(key)
                    items_by_phase.setdefault(phase, []).append(
                        {
                            "item_id": item_id,
                            "rank_label": rank_label,
                            "rank_group": rank_group_from_label(rank_label),
                            "context": context,
                        }
                    )
                for phase, items in items_by_phase.items():
                    rows.append(
                        {
                            "class": class_name,
                            "spec": spec_name,
                            "phase": phase,
                            "slot": slot,
                            "source_url": snapshot["url"],
                            "items": items,
                        }
                    )

    if not rows:
        return canonical_json("bis_lists")
    return {"coverage": "scraped_snapshot", "lists": rows}


def text_for_phase_detection(source_meta: dict[str, Any], table: dict[str, Any], row: dict[str, Any]) -> str:
    values = [
        str(source_meta.get("phase") or ""),
        str(source_meta.get("phase_name") or ""),
        str(table.get("heading") or ""),
        str(row.get("rank_label") or ""),
        str(row.get("source_text") or ""),
        " ".join(str(cell) for cell in row.get("cells", [])),
    ]
    return " ".join(values)


def phase_from_row(source_meta: dict[str, Any], table: dict[str, Any], row: dict[str, Any]) -> str | None:
    if source_meta.get("phase") in PHASE_KEYS:
        return str(source_meta["phase"])
    phases = source_meta.get("phases")
    if isinstance(phases, list) and len(phases) == 1 and phases[0] in PHASE_KEYS:
        return str(phases[0])

    normalized = text_for_phase_detection(source_meta, table, row).lower()
    aliases = {
        "PR": ["pr", "pre-raid", "pre raid", "phase 0"],
        "T4": ["t4", "tier 4", "phase 1"],
        "T5": ["t5", "tier 5", "phase 2"],
        "T6": ["t6", "tier 6", "phase 3", "phase 4"],
        "ZA": ["za", "zul'aman", "zulaman"],
        "SWP": ["swp", "sunwell", "phase 5"],
    }
    for phase in PHASE_KEYS:
        if any(re.search(rf"\b{re.escape(alias)}\b", normalized) for alias in aliases[phase]):
            return phase
    return None


def row_item_ids(row: dict[str, Any]) -> list[int]:
    return [int(entity["id"]) for entity in row.get("entities", []) if entity.get("type") == "item" and entity.get("id")]


def first_row_entity(row: dict[str, Any]) -> dict[str, Any] | None:
    entities = row.get("entities", [])
    return entities[0] if entities else None


def quality_from_row(row: dict[str, Any]) -> int | None:
    normalized = " ".join(str(cell) for cell in row.get("cells", [])).lower()
    if "legendary" in normalized:
        return 5
    if "epic" in normalized:
        return 4
    if "rare" in normalized or "blue" in normalized:
        return 3
    if "uncommon" in normalized or "green" in normalized:
        return 2
    if "common" in normalized or "white" in normalized:
        return 1
    return None


def compact_cells(row: dict[str, Any]) -> str:
    return " | ".join(cell for cell in row.get("cells", []) if cell)


def slot_from_row(table: dict[str, Any], row: dict[str, Any]) -> str | None:
    if table.get("slot") in SLOT_NAMES:
        return str(table["slot"])
    text = compact_cells(row).lower()
    for slot in sorted(SLOT_NAMES, key=len, reverse=True):
        if re.search(rf"\b{re.escape(slot.lower())}\b", text):
            return slot
    return None


def table_matches_family(source_meta: dict[str, Any], table: dict[str, Any], data_family: str) -> bool:
    if not source_meta:
        return False
    table_family = table.get("data_family")
    return table_family in (data_family, "unknown", None)


def import_gems_from_snapshots(snapshots: list[dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, int]] = set()

    for snapshot in snapshots:
        if snapshot.get("page_type") != "guide":
            continue
        source_meta = manifest_source_for_snapshot(snapshot, "gems")
        class_name = source_meta.get("class")
        spec_name = source_meta.get("spec")
        if not class_name or not spec_name:
            continue

        for table in snapshot.get("tables", []):
            if not table_matches_family(source_meta, table, "gems"):
                continue
            for row in table.get("rows", []):
                item_ids = row_item_ids(row)
                phase = phase_from_row(source_meta, table, row)
                if not item_ids or not phase:
                    continue
                key = (str(class_name), str(spec_name), phase, item_ids[0])
                if key in seen:
                    continue
                seen.add(key)
                gem_row: dict[str, Any] = {
                    "class": class_name,
                    "spec": spec_name,
                    "phase": phase,
                    "id": item_ids[0],
                    "name": row.get("item_name"),
                    "meta": "meta" in compact_cells(row).lower() or str(row.get("item_name", "")).lower().endswith("diamond"),
                    "source_url": snapshot["url"],
                }
                quality = quality_from_row(row)
                if quality is not None:
                    gem_row["quality"] = quality
                rows.append(gem_row)

    if not rows:
        return canonical_json("gems")
    return {"gems": rows}


def import_enchants_from_snapshots(snapshots: list[dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str, int, str]] = set()

    for snapshot in snapshots:
        if snapshot.get("page_type") != "guide":
            continue
        source_meta = manifest_source_for_snapshot(snapshot, "enchants")
        class_name = source_meta.get("class")
        spec_name = source_meta.get("spec")
        if not class_name or not spec_name:
            continue

        for table in snapshot.get("tables", []):
            if not table_matches_family(source_meta, table, "enchants"):
                continue
            for row in table.get("rows", []):
                entity = first_row_entity(row)
                phase = phase_from_row(source_meta, table, row)
                slot = slot_from_row(table, row)
                if not entity or not phase or not slot:
                    continue
                key = (str(class_name), str(spec_name), phase, slot, int(entity["id"]), str(entity["type"]))
                if key in seen:
                    continue
                seen.add(key)
                rows.append(
                    {
                        "class": class_name,
                        "spec": spec_name,
                        "phase": phase,
                        "slot": slot,
                        "id": entity["id"],
                        "name": entity["name"],
                        "type": entity["type"],
                        "source_url": snapshot["url"],
                    }
                )

    if not rows:
        return canonical_json("enchants")
    return {"enchants": rows}


def consumable_category(table: dict[str, Any], row: dict[str, Any]) -> str:
    first_cell = str(row.get("cells", [""])[0]).strip() if row.get("cells") else ""
    if first_cell and not re.fullmatch(r"\d+|bis|option", first_cell, flags=re.IGNORECASE):
        return first_cell
    heading = str(table.get("heading") or "").strip()
    return heading or "Consumables"


def import_consumables_from_snapshots(snapshots: list[dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, tuple[int, ...]]] = set()

    for snapshot in snapshots:
        if snapshot.get("page_type") != "guide":
            continue
        source_meta = manifest_source_for_snapshot(snapshot, "consumables")
        class_name = source_meta.get("class")
        spec_name = source_meta.get("spec")
        if not class_name or not spec_name:
            continue

        for table in snapshot.get("tables", []):
            if not table_matches_family(source_meta, table, "consumables"):
                continue
            for row in table.get("rows", []):
                item_ids = row_item_ids(row)
                if not item_ids:
                    continue
                category = consumable_category(table, row)
                key = (str(class_name), str(spec_name), category, tuple(item_ids))
                if key in seen:
                    continue
                seen.add(key)
                consumable_row: dict[str, Any] = {
                    "class": class_name,
                    "spec": spec_name,
                    "category": category,
                    "items": item_ids,
                    "source_url": snapshot["url"],
                }
                phase = phase_from_row(source_meta, table, row)
                if phase:
                    consumable_row["phase"] = phase
                rows.append(consumable_row)

    if not rows:
        return canonical_json("consumables")
    return {"consumables": rows}


def import_leveling_from_snapshots(snapshots: list[dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str, str]] = set()

    for snapshot in snapshots:
        if snapshot.get("page_type") != "guide":
            continue
        source_meta = manifest_source_for_snapshot(snapshot, "leveling")
        class_name = source_meta.get("class")
        spec_name = source_meta.get("spec")
        if not class_name or not spec_name:
            continue

        for table in snapshot.get("tables", []):
            if not table_matches_family(source_meta, table, "leveling"):
                continue
            for row in table.get("rows", []):
                text = compact_cells(row)
                if not text:
                    continue
                section = str(table.get("heading") or "Leveling")
                phase = phase_from_row(source_meta, table, row) or str(source_meta.get("phase") or "PR")
                key = (str(class_name), str(spec_name), phase, section, text)
                if key in seen:
                    continue
                seen.add(key)
                rows.append(
                    {
                        "class": class_name,
                        "spec": spec_name,
                        "phase": phase,
                        "section": section,
                        "label": row.get("rank_label") or "",
                        "text": text,
                        "entities": row.get("entities", []),
                        "source_url": snapshot["url"],
                    }
                )

    if not rows:
        return canonical_json("leveling")
    return {"leveling": rows}


def import_entity_sources_from_snapshots(
    snapshots: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    output_key: str,
) -> dict[str, Any]:
    wanted_item_ids = {row.get("id") for row in rows if row.get("id") and row.get("type", "item") != "spell"}
    wanted_item_ids.update(item_id for row in rows for item_id in row.get("items", []))
    wanted_spell_ids = {row.get("id") for row in rows if row.get("type") == "spell" and row.get("id")}
    item_snapshots = {snapshot.get("item_id"): snapshot for snapshot in snapshots if snapshot.get("page_type") == "item"}
    spell_snapshots = {snapshot.get("spell_id"): snapshot for snapshot in snapshots if snapshot.get("page_type") == "spell"}
    source_rows: list[dict[str, Any]] = []

    for item_id in sorted(item_id for item_id in wanted_item_ids if item_id in item_snapshots):
        snapshot = item_snapshots[item_id]
        sources = snapshot.get("normalized_sources", [])
        source_rows.append(
            {
                "id": item_id,
                "type": "item",
                "name": snapshot.get("name"),
                "sources": sources,
                "primary_source": derive_primary_source(sources),
                "source_summary": summarize_sources(sources),
                "source_url": snapshot["url"],
            }
        )

    for spell_id in sorted(spell_id for spell_id in wanted_spell_ids if spell_id in spell_snapshots):
        snapshot = spell_snapshots[spell_id]
        source_rows.append(
            {
                "id": spell_id,
                "type": "spell",
                "name": snapshot.get("name"),
                "sources": snapshot.get("normalized_sources", []),
                "source_url": snapshot["url"],
            }
        )

    if not source_rows:
        return canonical_json(output_key)
    return {output_key: source_rows}


def token_sources_for_cost(cost: dict[str, Any], token_snapshot: dict[str, Any] | None) -> list[dict[str, Any]]:
    item_id = cost.get("item_id")
    if not isinstance(item_id, int) or item_id <= 0 or not token_snapshot:
        return []

    token_name = token_snapshot.get("name") or cost.get("name") or f"Item {item_id}"
    token_sources: list[dict[str, Any]] = []
    for source in token_snapshot.get("normalized_sources", []):
        enriched = dict(source)
        enriched["token_item_id"] = item_id
        enriched["token_name"] = token_name
        enriched["token_count"] = int(cost.get("amount") or 1)
        enriched["token_source_url"] = token_snapshot.get("url")
        token_sources.append(enriched)
    return token_sources


def attach_token_turnins_to_sources(
    sources: list[dict[str, Any]],
    item_snapshots: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    resolved_sources: list[dict[str, Any]] = []

    for source in sources:
        resolved = dict(source)
        costs = [dict(cost) for cost in source.get("costs", [])]
        token_sources: list[dict[str, Any]] = []
        has_item_cost = False

        for cost in costs:
            item_id = cost.get("item_id")
            if not isinstance(item_id, int) or item_id <= 0:
                continue
            has_item_cost = True
            token_snapshot = item_snapshots.get(item_id)
            if token_snapshot and token_snapshot.get("name"):
                cost["name"] = token_snapshot["name"]
            token_sources.extend(token_sources_for_cost(cost, token_snapshot))

        if costs:
            resolved["costs"] = costs
        if source.get("type") == "vendor" and has_item_cost and token_sources:
            resolved["type"] = "token_turnin"
            resolved["token_sources"] = token_sources
            resolved["confidence"] = f"{source.get('confidence', 'wowhead_item')}+token"
        resolved_sources.append(resolved)

    return resolved_sources


def guide_item_refs(snapshots: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    refs: dict[int, dict[str, Any]] = {}
    for snapshot in snapshots:
        if snapshot.get("page_type") != "guide":
            continue
        for table in snapshot.get("tables", []):
            for row in table.get("rows", []):
                item_id = row.get("item_id")
                if not isinstance(item_id, int) or item_id <= 0:
                    continue
                refs[item_id] = {
                    "id": item_id,
                    "name": row.get("item_name") or row.get("entity_name") or f"Item {item_id}",
                    "wowhead_url": row.get("item_url") or item_url_for_id(item_id),
                }
    return refs


def guide_item_source_hints(snapshots: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    hints: dict[int, list[dict[str, Any]]] = {}
    for snapshot in snapshots:
        if snapshot.get("page_type") != "guide":
            continue
        for table in snapshot.get("tables", []):
            for row in table.get("rows", []):
                item_id = row.get("item_id")
                if not isinstance(item_id, int) or item_id <= 0:
                    continue
                source_text = clean_text(str(row.get("source_text") or ""))
                if not source_text:
                    continue
                hints.setdefault(item_id, []).append(
                    {
                        "source_text": source_text,
                        "source_links": row.get("source_links", []),
                        "source_url": snapshot["url"],
                    }
                )
    return hints


def source_name_and_zone_from_text(text: str, prefix_pattern: str) -> tuple[str, str | None]:
    cleaned = clean_text(re.sub(prefix_pattern, "", text, flags=re.IGNORECASE).strip(" :-"))
    zone = None
    paren_match = re.search(r"^(.*?)\s*\(([^()]+)\)\s*$", cleaned)
    if paren_match:
        cleaned = clean_text(paren_match.group(1))
        zone = clean_text(paren_match.group(2))
    else:
        dash_match = re.search(r"^(.*?)\s+-\s+(.+)$", cleaned)
        if dash_match:
            cleaned = clean_text(dash_match.group(1))
            zone = clean_text(dash_match.group(2))
    return cleaned or text, zone


def guide_fallback_source(hint: dict[str, Any]) -> dict[str, Any]:
    text = clean_text(str(hint.get("source_text") or ""))
    lowered = text.lower()
    source_url = str(hint.get("source_url") or "")
    source: dict[str, Any] = {
        "source_url": source_url,
        "confidence": "wowhead_guide_fallback",
        "raw_source_text": text,
    }

    if "world drop" in lowered:
        return {
            **source,
            "type": "world_drop",
            "entity_name": "World Drop",
            "world_drop": True,
        }

    if lowered.startswith("conjured"):
        return {
            **source,
            "type": "crafted",
            "entity_name": "Conjured",
            "profession": "Warlock",
        }

    if "apexis shard" in lowered and "depleted" in lowered:
        entity_name, zone = source_name_and_zone_from_text(text, r"^(zone drop|drop):")
        zone = zone or ("Blade's Edge Mountains" if "blade" in lowered else None)
        parsed_source = {
            **source,
            "type": "vendor",
            "entity_name": "Apexis Shard turn-in",
            "costs": [{"amount": 50, "name": "Apexis Shard"}],
        }
        if zone:
            parsed_source["zone"] = zone
        depleted_match = re.search(r"\b(depleted [a-z' -]+)", entity_name, flags=re.IGNORECASE)
        if depleted_match:
            parsed_source["costs"].append({"amount": 1, "name": clean_text(depleted_match.group(1)).title()})
        return parsed_source

    if lowered.startswith("zone drop:"):
        entity_name, zone = source_name_and_zone_from_text(text, r"^zone drop:")
        if zone:
            source["zone"] = zone
        return {**source, "type": "drop", "entity_name": entity_name}

    professions = [
        "alchemy",
        "blacksmithing",
        "engineering",
        "jewelcrafting",
        "leatherworking",
        "tailoring",
        "enchanting",
    ]
    profession = next((name.title() for name in professions if name in lowered), None)
    if lowered.startswith("boe crafted") and "jewelcrafter" in lowered:
        profession = "Jewelcrafting"
    if lowered.startswith("profession:") or lowered.startswith("crafted") or lowered.startswith("boe crafted") or profession:
        entity_name, zone = source_name_and_zone_from_text(text, r"^(profession|crafted|drop):")
        if profession:
            entity_name = profession
        if zone:
            source["zone"] = zone
        return {
            **source,
            "type": "crafted",
            "entity_name": entity_name,
            "profession": profession or entity_name,
        }

    if lowered.startswith("quest:"):
        entity_name, zone = source_name_and_zone_from_text(text, r"^quest:")
        if zone:
            source["zone"] = zone
        return {**source, "type": "quest", "entity_name": entity_name}

    if lowered.startswith("vendor:") or "arena point" in lowered or "honor point" in lowered:
        entity_name, zone = source_name_and_zone_from_text(text, r"^vendor:")
        if zone:
            source["zone"] = zone
        return {
            **source,
            "type": "pvp" if "arena point" in lowered or "honor point" in lowered else "vendor",
            "entity_name": entity_name,
        }

    if lowered.startswith("drop:"):
        entity_name, zone = source_name_and_zone_from_text(text, r"^drop:")
        if zone:
            source["zone"] = zone
        return {**source, "type": "drop", "entity_name": entity_name}

    if re.search(r"\([^()]+\)\s*$", text) or " - " in text:
        entity_name, zone = source_name_and_zone_from_text(text, r"")
        if zone:
            source["zone"] = zone
        return {**source, "type": "drop", "entity_name": entity_name}

    return {**source, "type": "unknown", "entity_name": text or "Unknown"}


def guide_fallback_sources(hints: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for hint in hints:
        source = guide_fallback_source(hint)
        key = (str(source.get("type")), str(source.get("entity_name")), str(source.get("zone") or ""))
        if key in seen:
            continue
        seen.add(key)
        sources.append(source)
    if any(source.get("type") != "unknown" for source in sources):
        sources = [source for source in sources if source.get("type") != "unknown"]
    return sources


def reviewed_overrides() -> list[dict[str, Any]]:
    return canonical_json("overrides").get("overrides", [])


def target_matches(row: dict[str, Any], target: dict[str, Any]) -> bool:
    return all(row.get(key) == value for key, value in target.items())


def refresh_item_derived_fields(item: dict[str, Any]) -> dict[str, Any]:
    refreshed = deepcopy(item)
    sources = refreshed.get("sources", [])
    refreshed["primary_source"] = derive_primary_source(sources)
    refreshed["source_summary"] = summarize_sources(sources)
    return refreshed


def apply_item_overrides(imported_items: dict[str, Any]) -> dict[str, Any]:
    items = [deepcopy(item) for item in imported_items.get("items", [])]
    by_id = {item.get("id"): item for item in items}
    existing_items = {item["id"]: item for item in canonical_json("items").get("items", [])}

    for override in reviewed_overrides():
        target = override.get("target", {})
        item_id = target.get("item_id")
        if not isinstance(item_id, int):
            continue

        item = by_id.get(item_id)
        if not item:
            continue

        if override.get("type") == "item_sources" and isinstance(override.get("sources"), list):
            item["sources"] = deepcopy(override["sources"])
            by_id[item_id] = refresh_item_derived_fields(item)
            continue

        if override.get("type") == "source_gap":
            current = existing_items.get(item_id)
            current_sources = current.get("sources", []) if current else []
            imported_sources = item.get("sources", [])
            needs_source_fix = not imported_sources or all(source.get("type") == "unknown" for source in imported_sources)
            if current_sources and needs_source_fix:
                item["sources"] = deepcopy(current_sources)
                by_id[item_id] = refresh_item_derived_fields(item)

    return {"items": [refresh_item_derived_fields(by_id[item["id"]]) for item in items]}


def apply_bis_overrides(imported_bis_lists: dict[str, Any]) -> dict[str, Any]:
    rows = [deepcopy(row) for row in imported_bis_lists.get("lists", [])]
    existing_rows = canonical_json("bis_lists").get("lists", [])

    for override in reviewed_overrides():
        if override.get("type") != "bis_context":
            continue
        target = override.get("target", {})
        replacement = next((deepcopy(row) for row in existing_rows if target_matches(row, target)), None)
        if not replacement:
            continue

        replaced = False
        for index, row in enumerate(rows):
            if target_matches(row, target):
                rows[index] = replacement
                replaced = True
                break
        if not replaced:
            rows.append(replacement)

    return {"coverage": imported_bis_lists.get("coverage", "scraped_snapshot"), "lists": rows}


def import_items_from_snapshots(snapshots: list[dict[str, Any]]) -> dict[str, Any]:
    existing_items = {item["id"]: item for item in canonical_json("items").get("items", []) if item.get("sources")}
    item_snapshots = {snapshot.get("item_id"): snapshot for snapshot in snapshots if snapshot.get("page_type") == "item"}
    item_refs = guide_item_refs(snapshots)
    item_source_hints = guide_item_source_hints(snapshots)
    item_ids = sorted(set(existing_items) | set(item_refs))

    items: list[dict[str, Any]] = []
    for item_id in item_ids:
        current = existing_items.get(item_id, {})
        ref = item_refs.get(item_id, {})
        snapshot = item_snapshots.get(item_id)
        raw_sources = snapshot.get("normalized_sources") if snapshot else current.get("sources", [])
        if not raw_sources:
            raw_sources = guide_fallback_sources(item_source_hints.get(item_id, []))
        sources = attach_token_turnins_to_sources(raw_sources, item_snapshots)
        item = {
            "id": item_id,
            "name": snapshot.get("name") if snapshot and snapshot.get("name") else current.get("name") or ref.get("name") or f"Item {item_id}",
            "quality": snapshot.get("quality") if snapshot and snapshot.get("quality") != "unknown" else current.get("quality", "unknown"),
            "binding": snapshot.get("binding") if snapshot and snapshot.get("binding") != "unknown" else current.get("binding", "unknown"),
            "boe": snapshot.get("boe") if snapshot and snapshot.get("boe") is not None else current.get("boe"),
            "wowhead_url": current.get("wowhead_url") or ref.get("wowhead_url") or item_url_for_id(item_id),
            "sources": sources,
            "primary_source": derive_primary_source(sources),
            "source_summary": summarize_sources(sources),
        }
        items.append(item)

    return apply_item_overrides({"items": items})


def command_import(args: argparse.Namespace) -> int:
    snapshots = load_snapshots(args.input_dir)
    imported_items = import_items_from_snapshots(snapshots)
    imported_bis_lists = apply_bis_overrides(import_bis_lists_from_snapshots(snapshots))
    imported_gems = import_gems_from_snapshots(snapshots)
    imported_gem_sources = import_entity_sources_from_snapshots(snapshots, imported_gems["gems"], "gem_sources")
    imported_enchants = import_enchants_from_snapshots(snapshots)
    imported_enchant_sources = import_entity_sources_from_snapshots(snapshots, imported_enchants["enchants"], "enchant_sources")
    imported_consumables = import_consumables_from_snapshots(snapshots)
    imported_leveling = import_leveling_from_snapshots(snapshots)

    if args.dry_run:
        print(
            json.dumps(
                {
                    "bis_lists": len(imported_bis_lists["lists"]),
                    "coverage": imported_bis_lists["coverage"],
                    "consumables": len(imported_consumables["consumables"]),
                    "enchant_sources": len(imported_enchant_sources["enchant_sources"]),
                    "enchants": len(imported_enchants["enchants"]),
                    "gem_sources": len(imported_gem_sources["gem_sources"]),
                    "gems": len(imported_gems["gems"]),
                    "items": len(imported_items["items"]),
                    "leveling": len(imported_leveling["leveling"]),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    write_text(CANONICAL_DIR / "items.json", json.dumps(imported_items, indent=2, sort_keys=True) + "\n")
    write_text(CANONICAL_DIR / "bis_lists.json", json.dumps(imported_bis_lists, indent=2, sort_keys=True) + "\n")
    write_text(CANONICAL_DIR / "gems.json", json.dumps(imported_gems, indent=2, sort_keys=True) + "\n")
    write_text(CANONICAL_DIR / "gem_sources.json", json.dumps(imported_gem_sources, indent=2, sort_keys=True) + "\n")
    write_text(CANONICAL_DIR / "enchants.json", json.dumps(imported_enchants, indent=2, sort_keys=True) + "\n")
    write_text(CANONICAL_DIR / "enchant_sources.json", json.dumps(imported_enchant_sources, indent=2, sort_keys=True) + "\n")
    write_text(CANONICAL_DIR / "consumables.json", json.dumps(imported_consumables, indent=2, sort_keys=True) + "\n")
    write_text(CANONICAL_DIR / "leveling.json", json.dumps(imported_leveling, indent=2, sort_keys=True) + "\n")
    for file_name in [
        "items.json",
        "bis_lists.json",
        "gems.json",
        "gem_sources.json",
        "enchants.json",
        "enchant_sources.json",
        "consumables.json",
        "leveling.json",
    ]:
        print(f"Wrote {CANONICAL_DIR / file_name}")
    return 0


def source_has_item_cost(source: dict[str, Any]) -> bool:
    return any(isinstance(cost.get("item_id"), int) for cost in source.get("costs", []))


def manifest_urls_for_family(data_family: str) -> set[str]:
    urls: set[str] = set()
    for source in canonical_json("scrape_manifest").get("sources", []):
        families = source.get("data_families")
        if isinstance(families, list):
            source_families = set(families)
        else:
            source_families = {source.get("data_family")}
        if data_family in source_families and source.get("url"):
            urls.add(source["url"])
    return urls


def raw_bis_rows_from_snapshots(snapshots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for snapshot in snapshots:
        if snapshot.get("page_type") != "guide":
            continue
        for source_meta in manifest_sources_for_snapshot(snapshot, "bis_lists"):
            class_name = source_meta.get("class")
            spec_name = source_meta.get("spec")
            if not class_name or not spec_name:
                continue
            for table in snapshot.get("tables", []):
                if table.get("data_family") not in (None, "bis_lists", "unknown"):
                    continue
                slot = table.get("slot")
                if not slot:
                    continue
                for row in table.get("rows", []):
                    item_id = row.get("item_id")
                    phase = phase_from_row(source_meta, table, row)
                    if not item_id or not phase:
                        continue
                    rank_label = row.get("rank_label") or "Option"
                    rows.append(
                        {
                            "class": class_name,
                            "spec": spec_name,
                            "phase": phase,
                            "slot": slot,
                            "item_id": item_id,
                            "context": context_from_rank_label(rank_label),
                            "rank_label": rank_label,
                            "source_text": clean_text(str(row.get("source_text") or "")),
                            "source_url": snapshot.get("url"),
                            "table_heading": table.get("heading") or "",
                        }
                    )
    return rows


def reviewed_unknown_source_item_ids() -> set[int]:
    item_ids: set[int] = set()
    for override in reviewed_overrides():
        target = override.get("target", {})
        item_id = target.get("item_id")
        if isinstance(item_id, int) and override.get("type") in {"source_gap", "item_sources", "unknown_source"}:
            item_ids.add(item_id)
    return item_ids


def source_audit_errors(item_id: int, sources: list[dict[str, Any]], reviewed_unknown_item_ids: set[int]) -> list[str]:
    errors: list[str] = []
    if not sources:
        return [f"BiS item {item_id} has no structured acquisition source"]
    for source in sources:
        source_type = source.get("type")
        if source_type == "unknown" and item_id not in reviewed_unknown_item_ids:
            errors.append(f"BiS item {item_id} has unreviewed unknown acquisition source")
        if source_type == "token_turnin" and not source.get("token_sources"):
            errors.append(f"BiS item {item_id} has unresolved token_turnin source")
        if source_type == "vendor" and source_has_item_cost(source):
            errors.append(f"BiS item {item_id} has unresolved item-cost vendor source")
        for token_source in source.get("token_sources", []):
            if token_source.get("type") == "unknown" and item_id not in reviewed_unknown_item_ids:
                errors.append(f"BiS item {item_id} has unreviewed unknown token source")
    return errors


def build_snapshot_audit(input_dir: Path, data_family: str, guide_only: bool = False) -> dict[str, Any]:
    snapshots = load_snapshots(input_dir)
    errors: list[str] = []
    warnings: list[str] = []
    guide_snapshots = [snapshot for snapshot in snapshots if snapshot.get("page_type") == "guide"]
    item_snapshots = {snapshot.get("item_id"): snapshot for snapshot in snapshots if snapshot.get("page_type") == "item"}

    manifest_guide_urls = manifest_urls_for_family(data_family)
    fetched_guide_urls = {snapshot.get("url") for snapshot in guide_snapshots}
    for url in sorted(manifest_guide_urls - fetched_guide_urls):
        errors.append(f"Missing guide snapshot: {url}")

    if data_family != "bis_lists":
        return {
            "ok": not errors,
            "errors": errors,
            "warnings": warnings,
            "summary": {
                "family": data_family,
                "guides": len(guide_snapshots),
                "items": len(item_snapshots),
                "snapshots": len(snapshots),
            },
        }

    raw_rows = raw_bis_rows_from_snapshots(snapshots)
    if guide_snapshots and not raw_rows:
        errors.append("No BiS item rows found in guide snapshots")

    seen: dict[tuple[str, str, str, str, int, str], tuple[str, str, str, str]] = {}
    for row in raw_rows:
        key = (
            str(row.get("class")),
            str(row.get("spec")),
            str(row.get("phase")),
            str(row.get("slot")),
            int(row.get("item_id")),
            str(row.get("context")),
        )
        signature = (
            str(row.get("rank_label") or ""),
            str(row.get("source_text") or ""),
            str(row.get("source_url") or ""),
            str(row.get("table_heading") or ""),
        )
        if key in seen:
            message = f"Duplicate BiS item/context in snapshots: {row['class']}/{row['spec']}/{row['phase']}/{row['slot']}: {row['item_id']}/{row['context']}"
            same_guide_rank = seen[key][0] == signature[0] and seen[key][2] == signature[2] and seen[key][3] == signature[3]
            if seen[key] == signature or same_guide_rank:
                warnings.append(message)
            else:
                errors.append(message)
        else:
            seen[key] = signature

    if guide_only:
        return {
            "ok": not errors,
            "errors": errors,
            "warnings": warnings,
            "summary": {
                "family": data_family,
                "guide_only": True,
                "guides": len(guide_snapshots),
                "raw_bis_rows": len(raw_rows),
                "snapshots": len(snapshots),
            },
        }

    referenced_item_ids = {int(row["item_id"]) for row in raw_rows}
    for item_id in sorted(referenced_item_ids - {item_id for item_id in item_snapshots if isinstance(item_id, int)}):
        errors.append(f"Missing item snapshot for BiS item {item_id}: {item_url_for_id(item_id)}")

    imported_items = {item["id"]: item for item in import_items_from_snapshots(snapshots).get("items", [])}
    reviewed_unknown_item_ids = reviewed_unknown_source_item_ids()
    for item_id in sorted(referenced_item_ids):
        item = imported_items.get(item_id)
        if not item:
            errors.append(f"BiS item {item_id} was not imported")
            continue
        errors.extend(source_audit_errors(item_id, item.get("sources", []), reviewed_unknown_item_ids))

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "family": data_family,
            "guide_only": False,
            "guides": len(guide_snapshots),
            "items": len(item_snapshots),
            "raw_bis_rows": len(raw_rows),
            "referenced_items": len(referenced_item_ids),
            "snapshots": len(snapshots),
        },
    }


def command_snapshot_audit(args: argparse.Namespace) -> int:
    audit = build_snapshot_audit(args.input_dir, args.family, guide_only=args.guide_only)
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["ok"] else 1


def build_audit() -> dict[str, Any]:
    result = validate()
    items = {item["id"]: item for item in canonical_json("items").get("items", [])}
    bis_doc = canonical_json("bis_lists")
    audit_errors = list(result.errors)
    duplicate_warnings: list[str] = []
    reviewed_unknown_item_ids = reviewed_unknown_source_item_ids()

    for row in bis_doc.get("lists", []):
        seen_by_id: dict[int, set[str]] = {}
        for entry in row.get("items", []):
            item_id = entry.get("item_id")
            item = items.get(item_id)
            if not item:
                audit_errors.append(f"BiS item {item_id} has no structured acquisition source")
                continue
            audit_errors.extend(source_audit_errors(int(item_id), item.get("sources", []), reviewed_unknown_item_ids))
            contexts = seen_by_id.setdefault(item_id, set())
            context = str(entry.get("context"))
            if context in contexts:
                audit_errors.append(f"Duplicate BiS item/context: {item_id}/{context}")
            elif contexts:
                duplicate_warnings.append(f"BiS item {item_id} appears multiple times with distinct contexts")
            contexts.add(context)

    return {
        "ok": not audit_errors,
        "errors": audit_errors,
        "warnings": duplicate_warnings,
        "summary": result.summary,
    }


def command_audit(args: argparse.Namespace) -> int:
    audit = build_audit()
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["ok"] else 1


def command_coverage(args: argparse.Namespace) -> int:
    coverage = build_manifest_coverage(include_missing=not args.summary, family_filter=args.family)
    print(json.dumps(coverage, indent=2, sort_keys=True))
    return 0 if coverage["ok"] or not args.strict else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Wowhead scraper for Big BiS List.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_parser = subparsers.add_parser("fetch", help="Fetch URLs from the manifest and write normalized snapshots.")
    fetch_parser.add_argument("--url", action="append", help="Specific Wowhead TBC URL to fetch instead of the manifest.")
    fetch_parser.add_argument("--output-dir", type=Path, default=RAW_WOWHEAD_DIR)
    fetch_parser.add_argument("--no-discover", action="store_true", help="Do not fetch item pages discovered from guide snapshots.")
    fetch_parser.add_argument("--retries", type=int, default=3)
    fetch_parser.add_argument("--delay", type=float, default=0.75)
    fetch_parser.set_defaults(func=command_fetch)

    import_parser = subparsers.add_parser("import", help="Import canonical data from normalized snapshots.")
    import_parser.add_argument("--input-dir", type=Path, default=RAW_WOWHEAD_DIR)
    import_parser.add_argument("--dry-run", action="store_true")
    import_parser.set_defaults(func=command_import)

    audit_parser = subparsers.add_parser("audit", help="Audit canonical scraped data.")
    audit_parser.set_defaults(func=command_audit)

    snapshot_audit_parser = subparsers.add_parser("snapshot-audit", help="Audit normalized raw snapshots before import.")
    snapshot_audit_parser.add_argument("--input-dir", type=Path, default=RAW_WOWHEAD_DIR)
    snapshot_audit_parser.add_argument("--family", choices=["bis_lists", "gems", "enchants", "consumables", "leveling"], default="bis_lists")
    snapshot_audit_parser.add_argument("--guide-only", action="store_true", help="Only require guide snapshots and parsable guide rows.")
    snapshot_audit_parser.set_defaults(func=command_snapshot_audit)

    coverage_parser = subparsers.add_parser("coverage", help="Report offline manifest coverage without fetching.")
    coverage_parser.add_argument("--family", choices=["bis_lists", "gems", "enchants", "consumables", "leveling", "classes", "phases"])
    coverage_parser.add_argument("--summary", action="store_true", help="Omit the full missing-unit list.")
    coverage_parser.add_argument("--strict", action="store_true", help="Fail if the manifest does not cover every expected unit.")
    coverage_parser.set_defaults(func=command_coverage)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "url", None):
        for url in args.url:
            if not url.startswith("https://www.wowhead.com/tbc/"):
                parser.error("expected https://www.wowhead.com/tbc/ URLs")
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
