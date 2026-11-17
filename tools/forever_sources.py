"""Forever source discovery and evidence normalization; no implicit approvals."""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urljoin, urlsplit

from tools.project import FOREVER_CANONICAL_DIR, ROOT, load_json, write_text


WOWHEAD_ROOT = "https://www.wowhead.com/forever/"
ENTITY_TYPES = {"item", "npc", "quest", "spell", "zone", "faction", "currency", "skill", "object"}
PROVIDER_RAW_DIR = ROOT / "data" / "raw" / "forever"
PROVIDER_HOSTS = {
    "blizzard": {"worldofwarcraft.blizzard.com"},
    "blizzard_forums": {"us.forums.blizzard.com"},
    "bindonforever": {"bindonforever.com"},
    "daybreak": {"daybreakforever.com"},
    "eg_link": {"guide.wow4ever.se", "raw.githubusercontent.com"},
    "eternadex": {"eternadex.com"},
    "senseos": {"senseos.gg"},
    "ahledger": {"ahledger.com", "api.ahledger.com"},
    "azeroth_wiki": {"azeroth.wiki"},
    "everloot": {"everloot.app"},
    "forever_item_finder": {"forever-item-finder.pages.dev"},
    "foreverchanges": {"foreverchanges.pro"},
    "foreverdb": {"foreverdb.net"},
    "foreverera": {"theforeverera.com"},
    "hearthproof": {"hearthproof.com"},
    "howtovideogame": {"howtovideogame.com"},
    "icyveins": {"db.icy-veins.com"},
    "method": {"www.method.gg"},
    "polestar": {"polestar.guide"},
    "questiedb": {"github.com", "raw.githubusercontent.com"},
    "questing_wiki": {"questing.wiki"},
    "raidbots": {"storage.googleapis.com"},
    "sixtytools": {"www.60.tools"},
    "timbers_field_guide": {"raw.githubusercontent.com"},
    "reddit": {"www.reddit.com"},
    "att": {"api.github.com"},
    "wago": {"wago.tools"},
    "warcraftdb": {"forever.warcraftdb.com"},
    "warcraft_wiki": {"warcraft.wiki.gg"},
    "wow4ever_quest": {"wow4ever.quest"},
    "wow_professions": {"www.wow-professions.com"},
    "wowf": {"wowf.io"},
    "wowforeverguides": {"wowforeverguides.com"},
    "wowforeverinfo": {"wowforeverinfo.com"},
    "wowseer": {"wowseer.gg"},
    "wowsims_gamedata": {"raw.githubusercontent.com"},
    "wowtbc": {"wowtbc.gg"},
    "zephras": {"zephras.com"},
}
ZEPHRAS_UNREVEALED = "https://zephras.com/forever/enUS/item/not-revealed/"
PROVIDER_EXACT_PATHS = {
    "azeroth_wiki": {
        "/forever/dungeons/blackrock-depths", "/forever/dungeons/dire-maul",
        "/forever/dungeons/scholomance", "/forever/dungeons/stratholme",
    },
    "daybreak": {"/blog/molten-core-loot-at-level-30", "/static/forever/datamine.json"},
    "forever_item_finder": {"/api/finds", "/data/index.json"},
    "hearthproof": {"/classes/hunter/leveling/", "/classes/rogue/leveling/"},
    "howtovideogame": {"/wow-forever-learn-fishing-fast-night-elf/"},
    "method": {
        "/wow-forever/dungeons/razorfen-kraul",
        "/wow-forever/how-to-get-malignant-root-powerful-rare-ring-in-wow-forever",
        "/wow-forever/how-to-get-to-all-starting-zones-in-wow-forever-and-best-starting-zones",
    },
    "polestar": {
        "/guides/class/rogue/the-horn-of-xelthos",
        "/guides/class/shaman/call-of-air-alliance", "/guides/class/shaman/call-of-air-horde",
    },
    "warcraft_wiki": {
        "/wiki/Ancient_Heirloom", "/wiki/Befouled_Water_Globe_(Forever)",
        "/wiki/Fishing_pole", "/wiki/Forever_fishing_techniques", "/wiki/Slydris",
    },
    "wow_professions": {"/forever/how-to-fish"},
    "wowf": {"/en/professions/fishing/ranks"},
    "wowforeverguides": {"/dungeons/upper-blackrock-spire"},
    "wowforeverinfo": {"/guides/wailing-caverns/", "/guides/razorfen-kraul/"},
    "wow4ever_quest": {"/en/library-books"},
    "wowseer": {"/guides/fishing"},
    "wowtbc": {"/warcraftforever/loot-tables/dungeons/the-drowned-city/"},
}


def entity_key(url: str) -> tuple[str, int] | None:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.netloc != "www.wowhead.com":
        return None
    match = re.fullmatch(r"/forever/([a-z]+)=(\d+)(?:/[^?#]*)?", parsed.path)
    if not match or match[1] not in ENTITY_TYPES or int(match[2]) <= 0:
        return None
    return match[1], int(match[2])


def canonical_url(url: str) -> str:
    key = entity_key(url)
    return f"{WOWHEAD_ROOT}{key[0]}={key[1]}" if key else url


def source_provider(url: str) -> str | None:
    if not isinstance(url, str):
        return None
    if re.fullmatch(r"capture://forever/[a-f0-9]{64}", url):
        return "local_capture"
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port:
        return None
    if parsed.netloc == "www.wowhead.com" and parsed.path.startswith("/forever/"):
        return "wowhead"
    if (parsed.netloc == "nether.wowhead.com" and not parsed.query and not parsed.fragment
            and re.fullmatch(r"/forever/tooltip/(?:item|quest|npc|spell)/[1-9]\d*", parsed.path)):
        return "wowhead"
    for provider, hosts in PROVIDER_HOSTS.items():
        if parsed.netloc in hosts:
            paths = PROVIDER_EXACT_PATHS.get(provider)
            if paths is not None and parsed.path not in paths:
                continue
            if (provider == "daybreak" and parsed.path == "/static/forever/datamine.json"
                    and (parsed.query or not re.fullmatch(r"/live_items/\d+", parsed.fragment))):
                continue
            if provider == "questiedb" and not parsed.path.startswith("/Questie/QuestieDB/"):
                continue
            if (provider == "questing_wiki" and (parsed.query or parsed.fragment
                    or not re.fullmatch(r"/wow-forever/quests/[1-9]\d*/", parsed.path))):
                continue
            if (provider == "raidbots" and (parsed.query or parsed.fragment or not re.fullmatch(
                    r"/raidbots-static/wow%2F[1-9]\d*%2FenUS%2FDBCache-[A-Za-z0-9_-]+\.bin", parsed.path))):
                continue
            if (provider == "sixtytools" and (parsed.query or parsed.fragment
                    or not re.fullmatch(r"/quests/[1-9]\d*-[a-z0-9-]+", parsed.path))):
                continue
            if (provider == "timbers_field_guide" and (parsed.query or parsed.fragment or not re.fullmatch(
                    r"/timbers-addons/timbers-field-guide/[0-9a-f]{40}/CHANGELOG\.md", parsed.path))):
                continue
            if provider == "att" and not re.fullmatch(r"/repos/ATTWoWAddon/AllTheThings/git/blobs/[0-9a-f]{40}", parsed.path):
                continue
            if provider == "blizzard_forums" and not re.fullmatch(r"/en/wow/t/[a-z0-9-]+/\d+(?:/\d+)?", parsed.path):
                continue
            if (provider == "bindonforever" and (parsed.query or parsed.fragment
                    or not re.fullmatch(r"/quest/[1-9]\d*", parsed.path))):
                continue
            if provider == "eg_link":
                if parsed.netloc == "guide.wow4ever.se":
                    path_pattern = r"/en/(?:quests/[1-9]\d*|npc/255887)"
                else:
                    path_pattern = (r"/JIVESCORP/eg-link-output-wowf/[0-9a-f]{40}/data/wowf/1\.60\.\d+\.\d+/"
                                    r"(?:quests\.enUS|turn_ins|loot|vendors|trainers|quest_prerequisites|quest_scan|"
                                    r"item_hotfixes\.enUS|hotfixes\.enUS)\.json")
                    if parsed.path.endswith("/loot.json"):
                        fragment_pattern = r"/sources/npc:[1-9]\d*\|group"
                    else:
                        fragment_pattern = r"/quests/[1-9]\d*"
                    if parsed.query or (parsed.fragment and not re.fullmatch(fragment_pattern, parsed.fragment)):
                        continue
                    if parsed.fragment and parsed.path.endswith(("/quest_scan.json", "/item_hotfixes.enUS.json")):
                        continue
                    if parsed.path.endswith("/turn_ins.json") and not parsed.fragment:
                        continue
                if not re.fullmatch(path_pattern, parsed.path):
                    continue
            if (provider == "foreverchanges" and parsed.path != "/rares"
                    and not re.fullmatch(r"/(?:item|quest)/[1-9]\d*/[a-z0-9-]+", parsed.path)):
                continue
            if provider == "forever_item_finder":
                if parsed.fragment or (parsed.path == "/data/index.json" and parsed.query):
                    continue
                if parsed.path == "/api/finds" and not re.fullmatch(r"id=[1-9]\d{0,6}", parsed.query):
                    continue
            if provider == "foreverera" and not re.fullmatch(r"/en/(?:items|quests)/[1-9]\d*/", parsed.path):
                continue
            if (provider == "warcraftdb" and (parsed.query or parsed.fragment
                    or not re.fullmatch(r"/api/data/node/quest/[1-9]\d*", parsed.path))):
                continue
            if provider == "icyveins" and not (re.fullmatch(r"/wow-forever/quests/[1-9]\d*", parsed.path)
                    or (parsed.path == "/wow-forever/items/" and not parsed.query
                        and re.fullmatch(r"inventory-type-(?:1|3|11|12|13|14|22|23|28)", parsed.fragment))):
                continue
            if provider == "eternadex":
                scopes = {"kopf/": {"1"}, "schultern/": {"3"}, "finger/": {"11"}, "schmuck/": {"12"},
                          "schilde/": {"14"}, "nebenhand/": {"23"}, "": {"13", "22"}}
                prefix = "/en/datenbank/items/"
                if (parsed.query or not parsed.path.startswith(prefix) or not parsed.fragment.startswith("inventory-type-")
                        or parsed.fragment.removeprefix("inventory-type-") not in scopes.get(parsed.path[len(prefix):], ())):
                    continue
            if provider == "reddit" and not re.fullmatch(r"/r/wowforever/comments/[a-z0-9]+/[a-z0-9_]+/?", parsed.path):
                continue
            if provider == "wowsims_gamedata" and not re.fullmatch(
                r"/wowsims/gamedata/[0-9a-f]{40}/(?:items|patches/1\.60\.\d+\.\d+/hotfix-\d+(?:\+|%2B)\d+)/items\.txt",
                parsed.path,
            ):
                continue
            if provider == "zephras" and url != ZEPHRAS_UNREVEALED:
                continue
            return provider
    return None


def linked_entities_from_html(html: str, base_url: str) -> list[dict]:
    from tools.scrape_wowhead import element_text, make_soup

    found = {}
    for anchor in make_soup(html).find_all("a", href=True):
        url = urljoin(base_url, anchor["href"])
        key = entity_key(url)
        if key:
            found.setdefault(key, {"type": key[0], "id": key[1], "url": canonical_url(url), "name": element_text(anchor)})
    return [found[key] for key in sorted(found)]


def guide_relationships(snapshot: dict) -> list[dict]:
    edges = []
    for table in snapshot.get("tables", []):
        for row in table.get("rows", []):
            identifier = row.get("item_id")
            if not isinstance(identifier, int):
                continue
            text = row.get("source_text", "")
            for link in row.get("source_links", []):
                key = entity_key(link.get("href", ""))
                if not key:
                    continue
                relation = {"npc": "source_lead", "quest": "rewards", "item": "recipe_lead", "spell": "profession_lead"}.get(key[0])
                if relation:
                    edges.append({"relation": relation, "subject_type": key[0], "subject_id": key[1],
                        "object_type": "item", "object_id": identifier, "source_url": snapshot["url"],
                        "confidence": "guide_claim", "source_text": text,
                        "availability": "unverified" if re.search(r"unknown|datamined|unobtainable|not available", text, re.I) else "pending_live_review"})
    return edges


def guide_quest_facts(html: str, url: str) -> list[dict]:
    from tools.scrape_wowhead import element_text, make_soup
    if not url.endswith("/guide/dungeons/every-dungeon-quest-location"):
        return []
    soup = make_soup(html)
    if "Minimum level to pick up that quest" not in element_text(soup):
        return []
    facts = {}
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        headers = [element_text(cell) for cell in rows[0].find_all(["th", "td"])]
        if headers[:2] != ["Quest", "Level"]:
            continue
        for row in rows[1:]:
            cells = row.find_all("td")
            if len(cells) < 2 or not element_text(cells[1]).isdigit():
                continue
            anchor = cells[0].find("a", href=True)
            entity = entity_key(urljoin(url, anchor["href"])) if anchor else None
            if entity and entity[0] == "quest":
                facts[entity[1]] = {"quest_id": entity[1], "min_level": int(element_text(cells[1])),
                                    "source_url": url, "confidence": "explicit_guide_minimum"}
    return [facts[key] for key in sorted(facts)]


def discover_sources(snapshots: dict[str, dict], registered: set[str]) -> list[dict]:
    known = {canonical_url(url) for url in registered}
    discovered: dict[str, dict] = {}

    def add(link: dict, origin: str) -> None:
        url = link.get("url") or link.get("href")
        if not isinstance(url, str) or not entity_key(url):
            return
        url = canonical_url(url)
        if url in known:
            return
        row = discovered.setdefault(url, {
            "url": url, "provider": "wowhead", "data_family": "acquisition", "status": "pending_live_review",
            "entity_type": entity_key(url)[0], "entity_id": entity_key(url)[1], "discovered_from": [],
        })
        if origin not in row["discovered_from"]:
            row["discovered_from"].append(origin)

    for url, snapshot in sorted(snapshots.items()):
        if snapshot.get("page_type") == "guide":
            for link in snapshot.get("linked_entities", []):
                add(link, url)
        for table in snapshot.get("tables", []):
            for row in table.get("rows", []):
                for link in row.get("source_links", []):
                    add(link, url)
        if snapshot.get("page_type") == "guide" and "dungeon-overview" in url:
            for link in snapshot.get("npc_refs", []):
                add(link, url)
        # Entity pages expose many unrelated items. Follow only typed acquisition
        # edges; tooltips also expose recipe results and item-started quests.
        if snapshot.get("page_type") == "item":
            for link in snapshot.get("linked_entities", []):
                if snapshot.get("item_kind") in {"recipe", "quest_starter"}:
                    add(link, url)
        for edge in snapshot.get("relationships", []):
            for prefix in ("subject", "object"):
                kind, identifier = edge.get(prefix + "_type"), edge.get(prefix + "_id")
                if kind in ENTITY_TYPES and type(identifier) is int and identifier > 0:
                    add({"url": f"{WOWHEAD_ROOT}{kind}={identifier}"}, url)
    for row in discovered.values():
        row["discovered_from"].sort()
    return [discovered[url] for url in sorted(discovered)]


# Only listviews with a defined relationship establish an edge. Arbitrary links
# elsewhere on the page remain leads, never proof of acquisition or a map pin.
LISTVIEW_RELATIONS = {
    "npc": {"drops": ("drops", "item"), "sells": ("sells", "item"), "starts": ("starts", "quest"),
            "ends": ("ends", "quest"), "teaches": ("teaches", "spell")},
    "quest": {"rewards": ("rewards", "item"), "choice-of": ("reward_choice", "item"),
              "reward-items": ("rewards", "item")},
    "spell": {"creates": ("creates", "item"), "created-item": ("creates", "item"),
              "taught-by-npc": ("taught_by", "npc"), "taught-by-item": ("taught_by", "item")},
    "zone": {}, "faction": {}, "currency": {}, "skill": {}, "object": {"contains": ("contains", "item")},
}


def parse_entity_html(url: str, html: str) -> dict:
    from tools.scrape_wowhead import PARSER_VERSION, element_text, extract_listview_data, make_soup, now_utc

    key = entity_key(url)
    if not key or key[0] == "item":
        raise ValueError(f"Unsupported acquisition URL: {url}")
    soup = make_soup(html)
    title = element_text(soup.title) if soup.title else ""
    name = re.split(r"\s+-\s+(?:NPC|Quest|Spell|Zone|Faction|Currency|Skill|Object)\s+-", title, maxsplit=1)[0]
    if not name or any(word in title.lower() for word in ("just a moment", "access denied", "page not found")):
        raise ValueError(f"Missing or blocked acquisition page: {url}")
    description = soup.find("meta", attrs={"name": "description"})
    relationships = []
    for table_id, (relation, target_type) in LISTVIEW_RELATIONS.get(key[0], {}).items():
        for row in extract_listview_data(html, table_id):
            identifier = row.get("id")
            if type(identifier) is not int or identifier <= 0:
                continue
            edge = {
                "relation": relation, "subject_type": key[0], "subject_id": key[1],
                "object_type": target_type, "object_id": identifier,
                "object_name": str(row.get("name", "")).lstrip("0123456789"),
                "source_url": url, "confidence": "wowhead_listview",
            }
            for field in ("side", "cost", "reqlevel", "level", "count", "outof", "percent", "stock", "restock"):
                if field in row:
                    edge[field] = row[field]
            relationships.append(edge)
    return {
        "parser_version": PARSER_VERSION, "flavor": "forever", "provider": "wowhead", "url": url,
        "fetched_at": now_utc(), "page_type": key[0], "entity_id": key[1], "name": name,
        "description": description.get("content", "") if description else "",
        "linked_entities": linked_entities_from_html(html, url), "relationships": relationships,
    }


def parse_entity_tooltip(url: str, payload_text: str) -> dict:
    from tools.scrape_wowhead import PARSER_VERSION, element_text, make_soup, now_utc, parse_spell_tooltip_endpoint

    key = entity_key(url)
    payload = json.loads(payload_text)
    if not key or key[0] not in {"quest", "npc", "spell"} or not isinstance(payload, dict) or not payload.get("name") or not payload.get("tooltip"):
        raise ValueError(f"Invalid Forever acquisition tooltip: {url}")
    snapshot = parse_spell_tooltip_endpoint(url, payload_text) if key[0] == "spell" else {}
    relationships = []
    if key[0] == "spell":
        for anchor in make_soup(payload["tooltip"]).select("span > a[href]"):
            target = entity_key(urljoin(url, anchor["href"]))
            if target and target[0] == "item" and element_text(anchor) == payload["name"]:
                relationships.append({"relation": "creates", "subject_type": "spell", "subject_id": key[1],
                    "object_type": "item", "object_id": target[1], "source_url": url, "confidence": "tooltip_endpoint"})
    return {
        **snapshot, "parser_version": PARSER_VERSION, "flavor": "forever", "provider": "wowhead", "url": url,
        "fetched_at": now_utc(), "page_type": key[0], "entity_id": key[1], "name": payload["name"],
        "description": element_text(make_soup(payload["tooltip"])), "fetch_method": "tooltip_endpoint",
        "linked_entities": linked_entities_from_html(payload["tooltip"], url),
        **({"map_observation": payload["map"]} if payload.get("map") else {}),
        "relationships": relationships, "confidence": "tooltip_endpoint",
    }


def normalize_zephras_disclosures(html: str, build: str, pending_ids: set[int], *, collected_at: str, digest: str) -> dict:
    """Compare pending IDs with the complete same-build unrevealed registry."""
    from tools.scrape_wowhead import element_text, make_soup

    page = make_soup(html)
    main = page.find("main")
    builds = set(re.findall(r"Current build · (1\.60\.\d+\.\d+)(?![\d.])", element_text(main))) if main else set()
    for badge in page.select('a.build-stamp[href="/builds/"]'):
        match = re.fullmatch(r"Build (1\.60\.\d+\.\d+)", element_text(badge))
        if match:
            builds.add(match[1])
    if not main or builds != {build}:
        raise ValueError("Zephras unrevealed registry has the wrong client build")
    totals = [int(match[1].replace(",", "")) for heading in main.find_all("h2")
              if (match := re.fullmatch(r"Not revealed yet ([\d,]+)", element_text(heading)))]
    identifiers = set()
    rows = main.select("table tr[data-id]")
    for row in rows:
        identifier = row["data-id"]
        label = row.select_one("td .loot-item")
        if (not re.fullmatch(r"[1-9][0-9]*", identifier) or not label or element_text(label) != f"Item {identifier}"
                or int(identifier) in identifiers):
            raise ValueError("Invalid or duplicate Zephras unrevealed item ID")
        identifiers.add(int(identifier))
    if totals != [len(identifiers)] or not rows:
        raise ValueError("Zephras unrevealed registry does not reconcile to its count")
    return {"url": ZEPHRAS_UNREVEALED, "flavor": "forever", "provider": "zephras", "page_type": "observations",
            "confidence": "publisher_disclosure_status", "publication_kind": "unrevealed_registry", "client_build": build,
            "fetched_at": collected_at, "source_content_digest": digest, "advertised_total": totals[0],
            "records": [{"kind": "item_disclosure", "item_id": identifier,
                         "state": "unrevealed" if identifier in identifiers else "not_on_unrevealed_list"}
                        for identifier in sorted(pending_ids)], "relationships": [],
            "attribution": [{"credit": "Zephras WoW Forever database", "source": ZEPHRAS_UNREVEALED}]}


def normalize_foreverchanges_requirement(url: str, html: str, *, collected_at: str) -> dict:
    """Capture an explicit equip requirement from a published Forever server tooltip."""
    from tools.scrape_wowhead import element_text, make_soup

    if source_provider(url) != "foreverchanges":
        raise ValueError("Invalid ForeverChanges item URL")
    item_id = int(urlsplit(url).path.split("/")[2])
    page = make_soup(html)
    badge = page.select_one(".it-beta")
    if not badge or "Confirmed in game" not in element_text(badge) or "Sent by Blizzard's server to players" not in element_text(badge):
        raise ValueError("Equip requirement needs a tooltip observed on the Forever server")

    observed = []
    for tip in page.select(".it-tip.it-labelled"):
        label = tip.select_one(".it-label")
        build = re.fullmatch(r"Forever (1\.60\.\d+\.\d+)", element_text(label)) if label else None
        if build:
            observed.append((tip, build[1]))
    if len(observed) != 1:
        raise ValueError("Expected one build-labeled Forever tooltip")

    tip, client_build = observed[0]
    name = tip.select_one(".it-name")
    identifier = tip.select_one(".it-itemid")
    if not name or not identifier or not re.search(rf"\bitem\s+{item_id}$", element_text(identifier)):
        raise ValueError("ForeverChanges tooltip item ID does not match its URL")
    lines = [element_text(line) for line in tip.select(".it-body > .it-plain")]
    levels = [int(match[1]) for line in lines if (match := re.fullmatch(r"Requires Level (\d+)", line))]
    slots = [match[1] for line in lines if (match := re.fullmatch(r"(Head|Shoulder)(?: (?:Cloth|Leather|Mail|Plate))?", line))]
    slots.extend("Ring" for line in lines if line == "Finger")
    if len(levels) != 1 or not 1 <= levels[0] <= 60 or len(slots) != 1:
        raise ValueError("ForeverChanges tooltip needs an explicit equipment slot and level requirement")

    return {"url": url, "flavor": "forever", "provider": "foreverchanges", "page_type": "catalog",
            "catalog_kind": "server_equip_requirement", "confidence": "server_observed_equip_requirement",
            "client_build": client_build, "fetched_at": collected_at,
            "source_content_digest": hashlib.sha256(html.encode()).hexdigest(),
            "attribution": [{"credit": "ForeverChanges", "source": url}],
            "records": [{"item_id": item_id, "name": element_text(name), "slot": slots[0], "required_level": levels[0]}]}


def content_digest(snapshot: dict) -> str:
    content = {key: value for key, value in snapshot.items() if key not in {"fetched_at", "collected_at"}}
    return hashlib.sha256(json.dumps(content, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def evidence_index(snapshots: dict[str, dict]) -> dict[str, dict]:
    records = {}
    for url, snapshot in sorted(snapshots.items()):
        provider = snapshot.get("provider") or source_provider(url)
        if not provider or source_provider(url) != provider:
            raise ValueError(f"Unrecognized Forever evidence provider: {url}")
        digest = content_digest(snapshot)
        evidence_id = f"{provider}:{hashlib.sha256(url.encode()).hexdigest()[:24]}"
        records[evidence_id] = {
            "evidence_id": evidence_id, "provider": provider, "source_url": url, "content_digest": digest,
            "collected_at": snapshot.get("fetched_at") or snapshot.get("collected_at"),
            "observed_build": snapshot.get("client_build"),
            "confidence": snapshot.get("confidence") or snapshot.get("item_stats", {}).get("parse_confidence") or "source_snapshot",
            **({"attribution": snapshot["attribution"]} if snapshot.get("attribution") else {}),
        }
    return records


def evidence_ref(url: str, snapshots: dict[str, dict]) -> dict:
    for record in evidence_index({url: snapshots[url]}).values():
        return {"evidence_id": record["evidence_id"], "content_digest": record["content_digest"]}
    raise ValueError(f"Missing evidence: {url}")


def check_evidence_refs(row: dict, records: dict[str, dict]) -> list[dict]:
    refs = row.get("evidence_refs")
    if not isinstance(refs, list) or not refs:
        raise ValueError("Missing evidence_refs on Forever approval")
    resolved, seen = [], set()
    for ref in refs:
        if not isinstance(ref, dict) or not isinstance(ref.get("evidence_id"), str):
            raise ValueError("Invalid Forever evidence reference")
        record = records.get(ref["evidence_id"])
        if not record or record["content_digest"] != ref.get("content_digest") or ref["evidence_id"] in seen:
            raise ValueError(f"Stale, missing, or duplicate Forever evidence: {ref['evidence_id']}")
        seen.add(ref["evidence_id"])
        resolved.append(record)
    return resolved


def route_leads(snapshots: dict[str, dict]) -> dict[int, list[dict]]:
    leads = defaultdict(list)
    for url, snapshot in sorted(snapshots.items()):
        if snapshot.get("page_type") == "item" and type(snapshot.get("item_id")) is int:
            for source in snapshot.get("normalized_sources", []):
                leads[snapshot["item_id"]].append({**source, "evidence_url": url})
        for table in snapshot.get("tables", []):
            for row in table.get("rows", []):
                if type(row.get("item_id")) is int:
                    for link in row.get("source_links", []):
                        key = entity_key(link.get("href", ""))
                        if key:
                            leads[row["item_id"]].append({"entity_type": key[0], "entity_id": key[1],
                                "entity_name": link.get("text", ""), "source_url": canonical_url(link["href"]),
                                "evidence_url": url, "confidence": "guide_lead"})
        for edge in snapshot.get("relationships", []):
            if edge.get("object_type") == "item" and edge.get("relation") in {"drops", "sells", "rewards", "reward_choice", "creates", "contains", "offered_for_trade"}:
                leads[edge["object_id"]].append({**edge, "evidence_url": url})
    return dict(leads)


def provider_snapshots(registered: set[str]) -> dict[str, dict]:
    snapshots = {}
    for path in sorted(PROVIDER_RAW_DIR.glob("*/*.json")):
        row = load_json(path)
        url = row.get("url", "")
        if row.get("flavor") != "forever" or url not in registered or source_provider(url) != path.parent.name:
            raise ValueError(f"Unregistered or cross-flavor provider evidence: {path}")
        if url in snapshots:
            raise ValueError(f"Duplicate provider snapshot: {url}")
        snapshots[url] = row
    return snapshots


def public_observation(value):
    private = {"installId", "eventId", "characterName", "accountName", "playerName", "sourceGuid", "playerGuid", "characterGuid"}
    if isinstance(value, dict):
        return {key: public_observation(member) for key, member in value.items() if key not in private}
    if isinstance(value, list):
        return [public_observation(member) for member in value]
    return value


def validate_everloot_pages(pages: list[dict]) -> None:
    if not pages or any(not isinstance(page, dict) for page in pages):
        raise ValueError("Invalid Everloot page collection")
    if not any("offset" in page for page in pages):
        return
    for field in ("total", "dataAsOf", "kinds"):
        if any(page.get(field) != pages[0].get(field) for page in pages):
            raise ValueError("Everloot snapshot changed during pagination; previous evidence must be preserved")
    expected = 0
    for index, page in enumerate(pages):
        if (type(page.get("offset")) is not int or page["offset"] != expected
                or type(page.get("limit")) is not int or page["limit"] <= 0
                or type(page.get("total")) is not int or page["total"] < 0):
            raise ValueError("Missing, duplicate, or out-of-order Everloot page")
        collections = [page[key] for key in ("records", "items", "edges", "rates") if key in page]
        if len(collections) != 1 or not isinstance(collections[0], list) or len(collections[0]) > page["limit"]:
            raise ValueError("Malformed paginated Everloot collection")
        expected += len(collections[0])
        if index == len(pages) - 1 and (page.get("next") is not None or expected != page["total"]):
            raise ValueError("Incomplete Everloot pagination; previous evidence must be preserved")
        if index < len(pages) - 1 and not page.get("next"):
            raise ValueError("Unexpected data after the final Everloot page")


def normalize_everloot(url: str, pages: list[dict], *, collected_at: str) -> dict:
    if source_provider(url) != "everloot":
        raise ValueError("Expected an Everloot evidence URL")
    validate_everloot_pages(pages)
    records, attributions, builds = [], [], set()
    for page in pages:
        if not isinstance(page, dict):
            raise ValueError("Invalid Everloot page")
        if page.get("unreachable") or page.get("ok") is False:
            raise ValueError("Everloot data is unavailable, not an empty observation")
        attribution = page.get("attribution")
        if attribution:
            if not isinstance(attribution, dict) or not all(isinstance(attribution.get(key), str) and attribution[key] for key in ("credit", "licence", "licenceUrl", "source")):
                raise ValueError("Incomplete Everloot attribution")
            if attribution not in attributions:
                attributions.append(attribution)
        game_data = page.get("gameData") or {}
        if not isinstance(game_data, dict):
            raise ValueError("Invalid Everloot game-data notice")
        build = game_data.get("build")
        if build:
            builds.add(str(build))
        for kind in ("rates", "items", "records", "edges"):
            members = page.get(kind, [])
            if not isinstance(members, list) or any(not isinstance(record, dict) for record in members):
                raise ValueError("Malformed Everloot record collection")
            for record in members:
                # Public feeds may still carry pseudonymous uploader IDs. They
                # are not item/source evidence and must not enter our corpus.
                records.append({**public_observation(record), "record_type": kind})
    # Game-file items are identity leads. Observed feeds must keep their credit.
    if any(row["record_type"] in {"rates", "records", "edges"} for row in records) and not attributions:
        raise ValueError("Missing Everloot observation attribution")
    relationships = []
    for row in records:
        if row["record_type"] == "edges":
            targets = {"dropped_by": ("drops", "npc"), "sold_by": ("sells", "npc"), "reward_from": ("rewards", "quest")}
            relation = targets.get(row.get("rel"))
            if relation and row.get("evidence") == "observed" and type(row.get("installs")) is int and row["installs"] >= 3 and row.get("fromKind") == "item" and row.get("toKind") == relation[1] and all(type(row.get(key)) is int and row[key] > 0 for key in ("fromId", "toId")):
                relationships.append({"relation": relation[0], "subject_type": relation[1], "subject_id": row["toId"],
                    "object_type": "item", "object_id": row["fromId"], "source_url": url,
                    "confidence": "corroborated_observation", "reporters": row["installs"], "observed_build": row.get("build")})
            continue
        if row["record_type"] != "rates" or row.get("public") is not True or type(row.get("reporters")) is not int or row["reporters"] < 3:
            continue
        kind, identifier = ("npc", row.get("sourceNpcId")) if row.get("sourceNpcId") else ("object", row.get("sourceObjectId"))
        if type(identifier) is int and identifier > 0 and type(row.get("itemId")) is int and row["itemId"] > 0:
            relationships.append({"relation": "drops" if kind == "npc" else "contains", "subject_type": kind,
                "subject_id": identifier, "object_type": "item", "object_id": row["itemId"],
                "source_url": url, "confidence": "corroborated_observation", "reporters": row["reporters"],
                "count": row.get("drops"), "outof": row.get("kills"), "rate": row.get("rate")})
    return {
        "flavor": "forever", "provider": "everloot", "url": url, "fetched_at": collected_at,
        "page_type": "observations", "confidence": "provider_observations", "records": records,
        "attribution": attributions, "client_build": next(iter(builds)) if len(builds) == 1 else None,
        "data_as_of": [page.get("dataAsOf") for page in pages],
        "pagination_consistent_as_of": len({page.get("dataAsOf") for page in pages}) == 1,
        "collection_scope": dict(parse_qsl(urlsplit(url).query)),
        "page_digests": [hashlib.sha256(json.dumps(page, sort_keys=True, separators=(",", ":")).encode()).hexdigest() for page in pages],
        "relationships": relationships,
    }


def normalize_everloot_client_layer(url: str, payload: dict, *, collected_at: str) -> dict:
    """Client relations identify recipes; they do not prove player acquisition."""
    if (url != "https://everloot.app/api/edges/client-layer" or not isinstance(payload,dict)
            or payload.get("schema")!="everloot.client-layer/2"
            or not isinstance(payload.get("build"),dict)
            or not re.fullmatch(r"1\.60\.\d+\.\d+",str(payload["build"].get("version","")))
            or not isinstance(payload.get("credit"),str) or not payload["credit"]):
        raise ValueError("Invalid Forever client-relation export")
    items=payload.get("items")
    edges=payload.get("edges")
    if (not isinstance(items,list) or not isinstance(edges,list)
            or any(not isinstance(row,list) or len(row)!=5 or type(row[0]) is not int or row[0]<=0 for row in items)
            or len({row[0] for row in items})!=len(items)
            or any(not isinstance(edge,list) or len(edge)!=5 or type(edge[1]) is not int
                   or type(edge[4]) is not int or edge[1]<=0 or edge[4]<=0 for edge in edges)):
        raise ValueError("Malformed client item or relation rows")
    relationships=[{"relation":"creates","subject_type":"spell","subject_id":edge[4],"object_type":"item","object_id":edge[1],
                    "source_url":url,"confidence":"client_metadata_only"}
                   for edge in edges if edge[0]=="item" and edge[2]=="created_by" and edge[3]=="spell"]
    return {"url":url,"flavor":"forever","provider":"everloot","page_type":"reference","confidence":"client_metadata_only",
            "fetched_at":collected_at,"client_build":payload["build"]["version"],"build_metadata":payload["build"],
            "label":payload.get("label"),"client_items":items,"records":[],"relationships":relationships,
            "source_content_digest":hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest(),
            "attribution":[{"credit":payload["credit"],"source":url,"licence":"Blizzard game-file data; WoWDBDefs column names CC BY-SA 4.0"}]}


def collect_everloot(url: str, fetch_page, *, collected_at: str) -> dict:
    pages, seen = [], set()
    next_url = url
    origin = urlsplit(url)

    def query_filters(query):
        return sorted((key, ",".join(sorted(value.split(","))) if key == "kinds" else value)
                      for key, value in parse_qsl(query, keep_blank_values=True) if key != "offset")

    filters = query_filters(origin.query)
    while next_url:
        parsed = urlsplit(next_url)
        if (source_provider(next_url) != "everloot" or next_url in seen or parsed.path != origin.path
                or query_filters(parsed.query) != filters):
            raise ValueError("Invalid or repeated Everloot pagination URL")
        seen.add(next_url)
        page = fetch_page(next_url)
        if not isinstance(page, dict):
            raise ValueError("Invalid Everloot page")
        if url=="https://everloot.app/api/edges/client-layer":
            return normalize_everloot_client_layer(url,page,collected_at=collected_at)
        if pages and "offset" in pages[0] and any(page.get(key) != pages[0].get(key) for key in ("total", "dataAsOf", "kinds")):
            raise ValueError("Everloot snapshot changed during pagination; previous evidence must be preserved")
        pages.append(page)
        next_url = page.get("next")
    return normalize_everloot(url, pages, collected_at=collected_at)


def normalize_ahledger(url: str, payload: dict, *, collected_at: str) -> dict:
    """A catalog verifies identity fields, not stats or acquisition."""
    if source_provider(url) != "ahledger" or not isinstance(payload, dict) or not isinstance(payload.get("rows"), list):
        raise ValueError("Invalid AHledger catalog")
    records = []
    seen = set()
    for row in payload["rows"]:
        if not isinstance(row, list) or len(row) < 8 or type(row[0]) is not int or row[0] <= 0 or row[0] in seen:
            raise ValueError("Invalid or duplicate AHledger item row")
        seen.add(row[0])
        records.append(dict(zip(("item_id", "name", "quality", "subclass", "item_level", "required_level", "icon", "slot"), row)))
    from tools.forever_availability import INVENTORY_SLOTS
    from urllib.parse import parse_qs
    parsed = urlsplit(url)
    query = parse_qs(parsed.query, keep_blank_values=True)
    armor = query.get("class") == ["armor"]
    whole_class_export = parsed.path == "/api/catalog" and query in ({"class":["armor"]}, {"class":["weapon"]})
    total = payload.get("total", len(records))
    complete = whole_class_export and total == len(records) and not payload.get("next") and not payload.get("truncated")
    return {"flavor": "forever", "provider": "ahledger", "url": url, "fetched_at": collected_at,
            "page_type": "catalog", "confidence": "catalog_metadata", "records": sorted(records, key=lambda row: row["item_id"]),
            "catalog_kind": "ahledger_catalog",
            "catalog_coverage": {"slots": sorted(INVENTORY_SLOTS) if armor else ["Off Hand"],
                "inventory_types": [1, 3, 11, 12, 14, 23, 28] if armor else [13, 22],
                "level_min": 1, "level_max": 59, "qualities": list(range(8)),
                "total": total, "complete": complete, "truncated": bool(payload.get("truncated"))},
            "relationships": [], "attribution": [{"credit": "Prices from AHledger (ahledger.com)",
                "licence": "AHledger data terms", "licenceUrl": "https://ahledger.com/developers", "source": "https://ahledger.com"}]}


def normalize_ahledger_pricetable(url: str, text: str, *, collected_at: str) -> dict:
    """Observed trade availability; neither item stats nor faction exclusivity."""
    if source_provider(url) != "ahledger" or not isinstance(text, str):
        raise ValueError("Invalid AHledger price table")
    lines = text.splitlines()
    header = lines[0].split("|") if lines else []
    if len(header) != 4 or header[0] != "AHL1" or not re.fullmatch(
            r"forever/(?:normal|pvp|rp|rp-pvp|rppvp)/(?:alliance|horde)/(?:us|eu|cn)", header[1]):
        raise ValueError("Invalid or cross-flavor AHledger market")
    if not header[2].isdigit() or not header[3].isdigit() or int(header[2]) <= 0:
        raise ValueError("Missing AHledger observation time or count")
    if urlsplit(url).path.rsplit("/", 1)[-1] != header[1].replace("/", "."):
        raise ValueError("AHledger response belongs to another market")
    from datetime import datetime, timezone
    observed = datetime.fromtimestamp(int(header[2]), timezone.utc).isoformat()
    records, seen = [], set()
    fields = ("item_id", "median_copper", "minimum_buyout_copper", "quantity", "median_7d_copper",
              "median_30d_copper", "low_30d_copper", "high_30d_copper", "estimated_daily_sales_tenths")
    for line in lines[1:]:
        parts = line.split(":")
        if len(parts) != len(fields) or any(value and not value.isdigit() for value in parts):
            raise ValueError("Malformed AHledger price row")
        row = dict(zip(fields, (int(value) if value else None for value in parts)))
        identifier = row["item_id"]
        if not identifier or identifier in seen:
            raise ValueError("Missing or duplicate AHledger trade item")
        seen.add(identifier)
        records.append(row)
    if len(records) != int(header[3]):
        raise ValueError("Incomplete AHledger price table")
    return {"flavor":"forever", "provider":"ahledger", "url":url, "fetched_at":collected_at,
            "page_type":"observations", "confidence":"observed_auction_listing", "market":header[1],
            "observed_at":observed, "observed_faction":header[1].split("/")[2].title(), "records":records,
            "relationships":[{"relation":"offered_for_trade", "subject_type":"market", "subject_id":header[1],
                              "object_type":"item", "object_id":row["item_id"], "source_url":url,
                              "confidence":"observed_auction_listing", "observed_at":observed}
                             for row in records if (row["quantity"] or 0) > 0 and (row["minimum_buyout_copper"] or 0) > 0],
            "attribution":[{"credit":"Prices from AHledger (ahledger.com)", "licence":"AHledger data terms",
                            "licenceUrl":"https://ahledger.com/developers", "source":"https://ahledger.com"}]}


def normalize_ahledger_item_price(url: str, payload: dict, *, collected_at: str) -> dict:
    """Keep the latest listing for one exact item and auction market."""
    request = urlsplit(url)
    match = re.fullmatch(
        r"/v1/prices/(forever\.(?:normal|pvp|rp|rppvp)\.(alliance|horde)\.(?:us|eu|cn))/([1-9]\d*)",
        request.path,
    )
    if source_provider(url) != "ahledger" or request.netloc != "api.ahledger.com" or not match or not isinstance(payload, dict):
        raise ValueError("Expected a public Forever item price endpoint")
    market, faction, identifier = match.groups()
    identifier = int(identifier)
    item = payload.get("item")
    if payload.get("market") != market or not isinstance(item, dict) or type(item.get("id")) is not int or item["id"] != identifier:
        raise ValueError("AHledger price response belongs to another item or market")
    venue = market.replace(".", "/")
    latest = payload.get("latest")
    records, relationships = [], []
    observed_at = None
    if latest is not None:
        if not isinstance(latest, dict) or not isinstance(latest.get("observedAt"), str):
            raise ValueError("AHledger price response is missing the scan time")
        when = datetime.fromisoformat(latest["observedAt"].replace("Z", "+00:00"))
        if when.tzinfo is None:
            raise ValueError("AHledger scan time needs a timezone")
        observed_at = when.astimezone(timezone.utc).isoformat()
        quantity, buyout = latest.get("quantity"), latest.get("minBuyout")
        if type(quantity) is not int or quantity < 0 or (buyout is not None and (type(buyout) is not int or buyout < 0)):
            raise ValueError("Invalid AHledger listing quantity or buyout")
        records.append({"item_id": identifier, "quantity": quantity, "minimum_buyout_copper": buyout})
        if quantity > 0 and buyout and buyout > 0:
            relationships.append({"relation": "offered_for_trade", "subject_type": "market", "subject_id": venue,
                                  "object_type": "item", "object_id": identifier, "source_url": url,
                                  "confidence": "observed_auction_listing", "observed_at": observed_at})
    return {"flavor": "forever", "provider": "ahledger", "url": url, "fetched_at": collected_at,
            "page_type": "observations", "confidence": "observed_auction_listing", "market": venue,
            "observed_faction": faction.title(), "observed_at": observed_at,
            "records": records, "relationships": relationships,
            "source_content_digest": hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
            "attribution": [{"credit": "Prices from AHledger (ahledger.com)", "licence": "AHledger data terms",
                             "licenceUrl": "https://ahledger.com/developers", "source": "https://ahledger.com"}]}


def normalize_ahledger_text(url: str, text: str, catalog: list[dict], *, collected_at: str) -> dict:
    if source_provider(url) != "ahledger" or not text.startswith("# AHledger:") or "## Quests (" not in text:
        raise ValueError("Invalid AHledger public text export")
    by_name = defaultdict(set)
    for row in catalog:
        by_name[row["name"].casefold()].add(row["item_id"])
    records, relationships, seen = [], [], set()
    for line in text.splitlines():
        fields = line.removeprefix("- ").split(" | ")
        if len(fields) != 8:
            continue
        match = re.fullmatch(r"https://ahledger.com/wow-forever/quests/(\d+)-[^\s]+", fields[-1])
        if not match:
            continue
        identifier = int(match[1])
        if identifier in seen:
            raise ValueError("Duplicate AHledger observed quest")
        seen.add(identifier)
        observed_level = int(fields[1]) if fields[1].isdigit() else None
        record = {"quest_id": identifier, "name": fields[0].removesuffix(" (new)"), "observed_quest_level": observed_level,
                  "zone": None if fields[2] == "-" else fields[2], "giver_name": None if fields[3] == "-" else fields[3],
                  "quest_url": fields[-1], "reward_leads": []}
        for reward in fields[4].split(", "):
            if reward == "-":
                continue
            name = reward.removesuffix(" (choice)")
            item_match = re.fullmatch(r"item (\d+)", name)
            ids = {int(item_match[1])} if item_match else by_name.get(name.casefold(), set())
            record["reward_leads"].append({"name": name, "candidate_item_ids": sorted(ids), "choice": reward.endswith(" (choice)")})
            if len(ids) == 1:
                relationships.append({"relation": "reward_choice" if reward.endswith(" (choice)") else "rewards",
                    "subject_type": "quest", "subject_id": identifier, "object_type": "item", "object_id": next(iter(ids)),
                    "source_url": url, "confidence": "provider_observation", "observed_quest_level": observed_level})
        records.append(record)
    if not records:
        raise ValueError("AHledger export contained no observed quests")
    return {"flavor": "forever", "provider": "ahledger", "url": url, "fetched_at": collected_at,
            "page_type": "observations", "confidence": "provider_observations", "records": records, "relationships": relationships,
            "attribution": [{"credit": "Prices from AHledger (ahledger.com)", "licence": "AHledger data terms",
                             "licenceUrl": "https://ahledger.com/developers", "source": "https://ahledger.com"}]}


def normalize_questiedb_leads(url: str, text: str, *, collected_at: str) -> dict:
    """Parse the literal raw payload, not executable providers or quest prose.

    Raw inputs precede static/dynamic corrections. These are discovery leads,
    never a claim that the complete public provider resolved the same facts.
    """
    from tools.forever_capture import LuaDataReader
    if source_provider(url) != "questiedb" or not re.search(r"/[a-f0-9]{40}/data/Forever/", url):
        raise ValueError("QuestieDB leads must reference a pinned Forever input")
    kind = "quest" if url.endswith("foreverQuestDB.lua") else "item" if url.endswith("foreverItemDB.lua") else None
    match = re.search(r"QuestieDB\." + str(kind) + r"Data\s*=\s*\[\[return\s*(\{.*\})\s*\]\]", text, re.S)
    if not kind or not match:
        raise ValueError("Unrecognized QuestieDB literal payload")
    reader = LuaDataReader(match[1])
    table = reader.value()
    reader.whitespace()
    if reader.position != len(reader.text) or not isinstance(table, dict):
        raise ValueError("Invalid QuestieDB literal table")
    records, relationships = [], []
    for identifier, row in sorted(table.items()):
        if type(identifier) is not int or not isinstance(row, list):
            raise ValueError("Invalid QuestieDB entity row")
        def get(position):
            return row[position - 1] if len(row) >= position else None
        if kind == "quest":
            records.append({"quest_id": identifier, "name": get(1), "minimum_level_lead": get(4),
                "maximum_level_lead": get(32),
                "required_races_mask_lead": get(6), "required_classes_mask_lead": get(7),
                "prerequisite_group_leads": get(12), "prerequisite_alternative_leads": get(13),
                "starter_leads": get(2), "finish_leads": get(3)})
        else:
            if get(12) not in {2, 4, 6, 11}:
                continue
            records.append({"item_id": identifier, "name": get(1), "required_level_lead": get(10)})
            for position, relation, entity in ((2,"drops","npc"),(6,"rewards","quest"),(14,"sells","npc")):
                for source_id in get(position) or []:
                    relationships.append({"relation":relation,"subject_type":entity,"subject_id":source_id,
                        "object_type":"item","object_id":identifier,"source_url":url,"confidence":"questiedb_raw_lead"})
    return {"flavor":"forever","provider":"questiedb","url":url,"fetched_at":collected_at,
            "page_type":"leads","confidence":"questiedb_raw_lead","corrections_applied":False,
            "records":records,"relationships":relationships,
            "attribution":[{"credit":"QuestieDB source leads","licence":"QuestieDB licensing terms",
                "licenceUrl":"https://github.com/Questie/QuestieDB/blob/master/LICENSE.md","source":"https://github.com/Questie/QuestieDB"}]}


def write_evidence_index(snapshots: dict[str, dict]) -> None:
    document = {"evidence": list(evidence_index(snapshots).values())}
    write_text(FOREVER_CANONICAL_DIR / "evidence.json", json.dumps(document, indent=2, sort_keys=True) + "\n")


def enrich_retry_metadata(snapshots: dict[str, dict]) -> int:
    """Attach attributed identity observations without promoting them to stats."""
    path = FOREVER_CANONICAL_DIR / "retry_ledger.json"
    if not path.is_file():
        return 0
    catalog = defaultdict(list)
    for url, snapshot in sorted(snapshots.items()):
        if snapshot.get("provider") != "ahledger" or snapshot.get("confidence") != "catalog_metadata":
            continue
        reference = evidence_ref(url, snapshots)
        for record in snapshot.get("records", []):
            if type(record.get("item_id")) is int:
                catalog[record["item_id"]].append({"source_url": url, "evidence_ref": reference,
                    "collected_at": snapshot.get("fetched_at"), "attribution": snapshot.get("attribution", []),
                    "confidence": "catalog_metadata", "record": record})
    document = load_json(path)
    changed = 0
    for row in document["entries"]:
        identity = entity_key(row["url"])
        if row.get("status") != "pending" or not identity or identity[0] != "item":
            continue
        for observation in catalog.get(identity[1], []):
            observations = row.setdefault("metadata_observations", [])
            if observation not in observations:
                observations.append(observation)
                changed += 1
    if changed:
        write_text(path, json.dumps(document, indent=2, sort_keys=True) + "\n")
    return changed


def record_attempt(url: str, error: str | None) -> None:
    record_attempts([(url, error)])


def record_attempts(attempts: list[tuple[str, str | None]]) -> None:
    """Commit a coordinated batch without discarding older metadata or attempts."""
    if not attempts:
        return
    path = FOREVER_CANONICAL_DIR / "retry_ledger.json"
    document = load_json(path) if path.is_file() else {"flavor": "forever", "entries": []}
    entries = {row["url"]: row for row in document["entries"]}
    for url, error in attempts:
        row = entries.setdefault(url, {"url": url, "retry_after": "provider_or_build_change"})
        history = row.setdefault("history", [])
        if row.get("last_attempt_at") and not history:
            history.append({"at": row["last_attempt_at"], "status": row.get("status"), "error": row.get("last_error")})
        row["last_attempt_at"] = datetime.now(timezone.utc).isoformat(timespec="microseconds")
        row["status"] = "pending" if error else "collected"
        if error:
            row["last_error"] = error
        else:
            row.pop("last_error", None)
        attempt = {"at": row["last_attempt_at"], "status": row["status"], "error": error}
        history.append(attempt)
    document["entries"] = [entries[key] for key in sorted(entries)]
    write_text(path, json.dumps(document, indent=2, sort_keys=True) + "\n")
