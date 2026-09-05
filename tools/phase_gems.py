"""Phase-specific gem evidence from Wowhead's published BiS loadouts.

The gear-planner encoding is documented by Wowhead's own implementation at
https://wow.zamimg.com/js/WH/Wow/GearPlannerTbc.js.  Only gem fields in a fully
decoded planner are recommendations; scanning its bytes for familiar item IDs
would accidentally turn equipment, enchantments, or talents into gems.

The normalized evidence deliberately retains the planner token and its decoded
slots.  Imports and audits therefore never depend on an uncommitted HTML cache.
"""

from __future__ import annotations

import argparse
import base64
from copy import deepcopy
import json
from pathlib import Path
import re
import sys
from typing import Any

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.project import PHASE_KEYS, RAW_WOWHEAD_DIR


PARSER_VERSION = "phase-gems-1"
PLANNER_FORMAT_SOURCE = "https://wow.zamimg.com/js/WH/Wow/GearPlannerTbc.js"
GEM_COLORS = {
    "crimson spinel": "red", "living ruby": "red", "blood garnet": "red",
    "empyrean sapphire": "blue", "star of elune": "blue", "azure moonstone": "blue",
    "lionseye": "yellow", "dawnstone": "yellow", "golden draenite": "yellow",
    "pyrestone": "orange", "noble topaz": "orange", "flame spessarite": "orange",
    "shadowsong amethyst": "purple", "nightseye": "purple", "shadow draenite": "purple",
    "seaspray emerald": "green", "talasite": "green", "deep peridot": "green",
    "earthstorm diamond": "meta", "skyfire diamond": "meta",
    "void sphere": "prismatic", "prismatic sphere": "prismatic",
}
GEM_NAME_PATTERN = re.compile(
    r"\b(?:" + "|".join(re.escape(name) for name in GEM_COLORS) + r")$", re.I
)


def decode_tbc_planner(path: str) -> dict[str, Any]:
    """Decode a TBC planner strictly, rejecting unsupported/truncated payloads."""
    match = re.fullmatch(r"([a-z-]+)/([a-z-]+)/([A-Za-z0-9_-]+)", path)
    if not match:
        raise ValueError("Invalid TBC gear-planner path")
    token = match[3]
    try:
        payload = base64.b64decode(token + "=" * (-len(token) % 4), altchars=b"-_", validate=True)
    except Exception as exc:
        raise ValueError("Invalid TBC gear-planner base64") from exc
    cursor = 0

    def read(count: int) -> bytes:
        nonlocal cursor
        if count < 0 or cursor + count > len(payload):
            raise ValueError("Truncated TBC gear-planner payload")
        value = payload[cursor:cursor + count]
        cursor += count
        return value

    version = read(1)[0]
    if version > 3:
        raise ValueError(f"Unsupported TBC gear-planner version {version}")
    level = read(1)[0] if version else 70
    if not 1 <= level <= 70:
        raise ValueError(f"Invalid TBC gear-planner level {level}")
    if version >= 2:
        read(read(1)[0])
    slots = []
    seen_slots: set[int] = set()
    while cursor < len(payload):
        flags = read(1)[0]
        slot = flags & 63
        # Wowhead includes the hunter ammunition slot as slot zero.
        if not 0 <= slot <= 23 or slot in seen_slots:
            raise ValueError(f"Invalid or duplicate TBC gear-planner slot {slot}")
        seen_slots.add(slot)
        high = read(1)[0] if version >= 3 else 0
        gem_count = high >> 5
        item_id = ((high & 31) << 16) | int.from_bytes(read(2), "big")
        entry: dict[str, Any] = {"slot": slot, "item_id": item_id}
        if flags & 128:
            entry["enchant_id"] = int.from_bytes(read(2), "big")
        if flags & 64:
            entry["random_enchant_id"] = int.from_bytes(read(2), "big", signed=True)
        gems = []
        seen_positions: set[int] = set()
        for _ in range(gem_count):
            gem_high = read(1)[0]
            position = gem_high >> 5
            if position in seen_positions:
                raise ValueError("Duplicate TBC gear-planner gem position")
            seen_positions.add(position)
            gems.append({"position": position, "item_id": ((gem_high & 31) << 16) | int.from_bytes(read(2), "big")})
        if gems:
            entry["gems"] = gems
        slots.append(entry)
    return {"version": version, "level": level, "class_slug": match[1], "race_slug": match[2], "slots": slots}


def gem_color(name: str) -> str | None:
    name = name.lower().strip()
    return next((color for suffix, color in GEM_COLORS.items() if name.endswith(suffix)), None)


def item_gem_color(item: dict[str, Any]) -> str | None:
    color = gem_color(item.get("name", ""))
    if color:
        return color
    text = str(item.get("description", "")).lower()
    match = re.search(r"matches (?:a |an |any )?(.*?)(?:socket|$)", text)
    if not match:
        return None
    colors = {color for color in ("red", "yellow", "blue", "meta") if color in match[1]}
    return {frozenset({"red"}): "red", frozenset({"yellow"}): "yellow", frozenset({"blue"}): "blue",
            frozenset({"red", "blue"}): "purple", frozenset({"red", "yellow"}): "orange",
            frozenset({"yellow", "blue"}): "green", frozenset({"red", "yellow", "blue"}): "prismatic",
            frozenset({"meta"}): "meta"}.get(frozenset(colors))


def _guide_markup(html: str) -> str:
    # Decode only the article's printHtml argument, never user comments or nav.
    for match in re.finditer(r'WH\.markup\.printHtml\(\s*(?=")', html):
        value, _ = json.JSONDecoder().raw_decode(html[match.end():])
        if isinstance(value, str):
            return value
    return ""


def _planner_context(markup: str, position: int) -> str:
    prior = markup[:position]
    tabs = list(re.finditer(r'\[tab\s+name=(?:"([^"]+)"|([^\]\s]+))', prior, re.I))
    if tabs and prior.rfind("[/tab]") < tabs[-1].start():
        return (tabs[-1][1] or tabs[-1][2]).strip()
    headings = list(re.finditer(r"\[h[1-6][^\]]*\](.*?)\[/h[1-6]\]", prior, re.S | re.I))
    return re.sub(r"\[[^\]]+\]", "", headings[-1][1]).strip() if headings else ""


def normalize_phase_gem_guide(snapshot: dict[str, Any], html: str,
                             bindings: list[dict[str, Any]]) -> dict[str, Any]:
    """Keep published loadouts and linked gem prose with explicit phase metadata."""
    from tools.scrape_wowhead import make_soup

    markup = _guide_markup(html)
    guidance = []
    errors = []
    for match in re.finditer(r"\[gear-planner=([^\]\s]+)[^\]]*\]", markup):
        planner = match[1].lstrip("#")
        try:
            decoded = decode_tbc_planner(planner)
        except ValueError as exc:
            errors.append({"planner": planner, "error": str(exc)})
            continue
        gem_ids = sorted({gem["item_id"] for slot in decoded["slots"] for gem in slot.get("gems", []) if gem["item_id"]})
        if gem_ids:
            guidance.append({"kind": "gear_planner", "planner": planner,
                             "label": _planner_context(markup, match.start()),
                             "gem_ids": gem_ids, "decoded": decoded})

    soup = make_soup(html)
    article = soup.select_one(".guide-content noscript") or soup.select_one(".guide-content")
    if article:
        # Many old Wowhead articles use BR-separated prose instead of P nodes.
        # Remove tables first: an item cited as a source is not gem guidance.
        for table in article.find_all("table"):
            table.decompose()
        for block_html in re.split(r"(?:<br\s*/?>\s*){2,}|</p>|</li>|</h[1-6]>", str(article), flags=re.I):
            block = make_soup(block_html)
            gems = []
            for link in block.find_all("a", href=True):
                match = re.search(r"/tbc/item=(\d+)(?:/|$)", link["href"])
                name = link.get_text(" ", strip=True)
                if match and GEM_NAME_PATTERN.search(name):
                    gems.append({"item_id": int(match[1]), "name": name})
            if gems:
                text = " ".join(block.get_text(" ", strip=True).split())
                # Preserve concise recommendation context, not the article.
                guidance.append({"kind": "linked_prose", "gem_ids": sorted({gem["item_id"] for gem in gems}),
                                 "gems": gems, "text": text[:3000]})
    unique_bindings = sorted({(b["class"], b["spec"],
                              snapshot.get("content_phase", "PR") if b.get("phase") == "PR" else b["phase"])
                             for b in bindings if b.get("phase") in PHASE_KEYS})
    result: dict[str, Any] = {
        "parser_version": PARSER_VERSION, "page_type": "phase_gem_guide",
        "url": snapshot["url"], "fetched_at": snapshot["fetched_at"],
        "title": snapshot.get("title", ""),
        "bindings": [{"class": cls, "spec": spec, "phase": phase} for cls, spec, phase in unique_bindings],
        "gem_guidance": guidance,
    }
    if snapshot.get("recommendation_status"):
        result["recommendation_status"] = snapshot["recommendation_status"]
    if errors:
        result["parse_errors"] = errors
    return result


def _evidence_recommendations(snapshots: list[dict[str, Any]]) -> dict[tuple[str, str, str], list[tuple[int, dict[str, Any], dict[str, Any]]]]:
    by_context: dict[tuple[str, str, str], list[tuple[int, dict[str, Any], dict[str, Any]]]] = {}
    for snapshot in snapshots:
        if snapshot.get("page_type") != "phase_gem_guide":
            continue
        if snapshot.get("recommendation_status") in {"no_distinct_update", "unverified_phase"}:
            continue
        for binding in snapshot.get("bindings", []):
            key = (binding["class"], binding["spec"], binding["phase"])
            for entry in snapshot.get("gem_guidance", []):
                for item_id in entry.get("gem_ids", []):
                    by_context.setdefault(key, []).append((item_id, snapshot, entry))
    return by_context


def reviewed_gem_items(snapshots: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    """Merge observed fields and apply the same canonical source reviews everywhere."""
    from tools.scrape_wowhead import item_snapshots_by_id, reviewed_overrides
    from tools.phase_source_overrides import apply_source_rule_overrides

    items = item_snapshots_by_id(snapshots)
    overrides = reviewed_overrides()
    for item_id, item in items.items():
        source_record = {"id": item_id, "sources": item.get("normalized_sources", [])}
        for key in ("binding", "boe", "tradeable"):
            if key in item:
                source_record[key] = item[key]
        reviewed = apply_source_rule_overrides(source_record, overrides)
        item["normalized_sources"] = reviewed["sources"]
        for key in ("binding", "boe", "tradeable"):
            if key in reviewed:
                item[key] = reviewed[key]
    return items


def import_phase_gems(snapshots: list[dict[str, Any]], base_gems: dict[str, Any]) -> dict[str, Any]:
    """Enrich only explicitly evidenced phases, retaining rare budget options.

    A fresh guide with no parsed guidance leaves the general recommendation
    intact and is reported as fallback by build_phase_gem_audit.  It cannot
    silently count as a phase-specific refresh.
    """
    from tools.sources import summarize_sources, source_is_phase_available
    from tools.scrape_wowhead import row_context

    items = reviewed_gem_items(snapshots)
    evidence = _evidence_recommendations(snapshots)
    rows = deepcopy(base_gems.get("gems", []))
    known = {(row["class"], row["spec"], row["phase"], row["id"]): row for row in rows}
    epic_context_colors: set[tuple[str, str, str, str]] = set()
    for key, recommendations in sorted(evidence.items()):
        for item_id, snapshot, entry in recommendations:
            item = items.get(item_id)
            if not item or not item.get("name"):
                continue
            color = item_gem_color(item)
            if not color:
                continue
            sources = item.get("normalized_sources", [])
            if not sources or not any(source_is_phase_available(source, key[2]) for source in sources):
                continue
            quality = item.get("quality")
            if isinstance(quality, str):
                quality = {"poor": 0, "common": 1, "uncommon": 2, "rare": 3, "epic": 4, "legendary": 5}.get(quality.lower())
            if quality == 4:
                epic_context_colors.add((*key, color))
            row_key = (*key, item_id)
            if row_key in known:
                known[row_key]["name"] = item["name"]
                continue
            context = row_context({"heading": entry.get("label", "")}, {})
            if re.search(r"mitigation|surviv|safety", entry.get("label", ""), re.I):
                context = "mitigation"
            if any(r.get("type") == "profession" and r.get("scope") == "equip_or_use" for r in item.get("normalized_requirements", [])):
                context = "jewelcrafting"
            row: dict[str, Any] = {"class": key[0], "spec": key[1], "phase": key[2], "id": item_id,
                                   "name": item["name"], "socket_category": color, "socket_color": color,
                                   "meta": color == "meta", "context": context, "source_url": snapshot["url"]}
            if quality is not None:
                row["quality"] = quality
            if item.get("normalized_sources"):
                row["source_summary"] = summarize_sources(item["normalized_sources"])
            if item.get("normalized_requirements"):
                row["requirements"] = deepcopy(item["normalized_requirements"])
            rows.append(row)
            known[row_key] = row
    for row in rows:
        item = items.get(row["id"])
        if item and item.get("name"):
            row["name"] = item["name"]
        key = (row["class"], row["spec"], row["phase"], row.get("socket_color", row.get("socket_category", "")))
        if key in epic_context_colors and row.get("quality") == 3 and not row.get("meta") and row.get("context") == "standard":
            row["context"] = "budget"
    return {"gems": rows}


def build_phase_gem_audit(snapshots: list[dict[str, Any]], base_gems: dict[str, Any]) -> dict[str, Any]:
    from tools.sources import source_is_phase_available

    evidence = _evidence_recommendations(snapshots)
    items = reviewed_gem_items(snapshots)
    item_ids = {item_id for item_id, item in items.items() if item.get("name") and item.get("normalized_sources")}
    contexts = sorted({(r["class"], r["spec"], r["phase"]) for r in base_gems.get("gems", [])})
    coverage = []
    for key in contexts:
        rows = evidence.get(key, [])
        ids = sorted({entry[0] for entry in rows})
        missing = sorted(set(ids) - item_ids)
        unavailable = [item_id for item_id in ids if item_id in item_ids and not any(
            source_is_phase_available(source, key[2]) for source in items[item_id]["normalized_sources"])]
        available = sorted(set(ids) - set(missing) - set(unavailable))
        coverage.append({"class": key[0], "spec": key[1], "phase": key[2],
                         "status": "missing_acquisition_evidence" if missing else "verified_phase_guidance" if available else "phase_guidance_unavailable" if ids else "general_guide_fallback",
                         "gem_ids": ids, "available_gem_ids": available, "missing_item_ids": missing, "phase_unavailable_gem_ids": unavailable,
                         "source_urls": sorted({entry[1]["url"] for entry in rows})})
    errors = [{"url": s["url"], **e} for s in snapshots for e in s.get("parse_errors", [])]
    return {"coverage": coverage, "parse_errors": errors,
            "unverified_guide_updates": [{"url": s["url"], "status": s["recommendation_status"], "bindings": s.get("bindings", [])}
                                         for s in snapshots if s.get("page_type") == "phase_gem_guide" and s.get("recommendation_status") in {"no_distinct_update", "unverified_phase"}],
            "missing_item_ids": sorted({item for row in coverage for item in row["missing_item_ids"]}),
            "complete_phase_guidance": all(row["status"] == "verified_phase_guidance" for row in coverage) and not errors}


def reviewed_gem_source_overrides() -> list[dict[str, Any]]:
    """Return reviewed recipe/cut routes for canonical overrides, never raw HTML.

    Unbound cuts can be purchased from other players.  Their BoP recipes and
    self-craft requirements stay on the crafting route instead of becoming
    requirements to socket a purchased gem.
    """
    path = RAW_WOWHEAD_DIR / "phase_gems" / "reviewed_acquisition.json"
    evidence = json.loads(path.read_text(encoding="utf-8"))
    overrides = []
    for fact in evidence["recipe_facts"]:
        phase = fact["available_from_phase"]
        url = fact["source_url"]
        skill = fact.get("skill", 375)
        profession = {"type": "profession", "scope": "self_craft", "profession": "Jewelcrafting", "skill": skill,
                      "source_url": url, "confidence": "manual_review", "raw_text": f"Requires Jewelcrafting ({skill})"}
        requirements = []
        if fact.get("reputation"):
            standing = fact["reputation"]
            reputation = fact.get("reputation_name", "The Scale of the Sands")
            requirements.append({"type": "reputation", "scope": "learn_recipe", "reputation": reputation,
                                 "standing": standing, "standing_rank": {"Friendly": 5, "Honored": 6, "Revered": 7, "Exalted": 8}[standing],
                                 "source_url": url, "confidence": "manual_review", "raw_text": f"Requires {reputation} - {standing}"})
        routes = fact.get("recipe_routes") or [{"type": fact["source_type"],
                   "entity_name": fact.get("vendor_name") or "Hyjal Summit bosses", "zone": fact["zone"],
                   **({"vendor_id": fact["vendor_id"], "entity_id": fact["vendor_id"]} if fact.get("vendor_id") else {})}]
        recipe_sources = []
        for route in routes:
            recipe_source = {**deepcopy(route), "item_id": fact["recipe_item_id"], "available_from_phase": phase,
                             "confidence": "reviewed_override", "source_url": url}
            if requirements:
                recipe_source["requirements"] = deepcopy(requirements)
            recipe_sources.append(recipe_source)
        crafted = {"type": "crafted", "entity_name": fact["gem_name"], "entity_id": fact["spell_id"],
                   "spell_id": fact["spell_id"], "profession": "Jewelcrafting", "available_from_phase": phase,
                   "requirements": [profession, {"type": "recipe_known", "scope": "self_craft", "spell_id": fact["spell_id"],
                                                  "spell_name": fact["gem_name"], "source_url": url,
                                                  "confidence": "manual_review", "raw_text": fact["recipe_name"]}],
                   "recipe_sources": recipe_sources, "source_url": url, "confidence": "reviewed_override"}
        tradeable = fact.get("tradeable", True)
        for item_id, sources, fields, reason in [
            (fact["gem_item_id"], [crafted], {"tradeable": True} if tradeable else {},
             "The complete cut tooltip verifies binding and use requirements; the recipe verifies the taught cut and crafting skill. Recipe acquisition gates apply to self-crafting. Unbound cuts can be purchased, while bound Jewelcrafter-only cuts retain their use restriction."),
            (fact["recipe_item_id"], recipe_sources, {},
             "The recipe tooltip verifies the taught cut, Jewelcrafting skill, and reputation where required. The reviewed acquisition guide identifies its seller or drop category; source windows retain the content unlock."),
        ]:
            overrides.append({"id": f"anniversary-gem-acquisition-{item_id}", "type": "source_rules", "target": {"item_id": item_id},
                              "reason": reason, "reviewer": "codex-source-review", "reviewed_at": "2026-09-05", "source_url": url,
                              "data": {"set_fields": fields, "rules": [{"match": {}, "set": {"available_from_phase": phase}}],
                                       "append_sources": sources, "evidence_path": "data/raw/wowhead/phase_gems/reviewed_acquisition.json"}})
    for fact in evidence.get("supplemental_source_facts", []):
        phase = fact["available_from_phase"]
        sources = [{**deepcopy(source), "available_from_phase": phase, "confidence": "reviewed_override",
                    "source_url": fact["source_url"]} for source in fact["sources"]]
        overrides.append({"id": f"anniversary-gem-acquisition-{fact['item_id']}", "type": "source_rules",
                          "target": {"item_id": fact["item_id"]}, "reason": fact["review_note"],
                          "reviewer": "codex-source-review", "reviewed_at": "2026-09-05", "source_url": fact["source_url"],
                          "data": {"set_fields": {"tradeable": True} if fact.get("tradeable") else {},
                                   "rules": [{"match": {}, "set": {"available_from_phase": phase}}],
                                   "append_sources": sources, "evidence_path": "data/raw/wowhead/phase_gems/reviewed_acquisition.json"}})
    return overrides


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--input-dir", type=Path, default=RAW_WOWHEAD_DIR / "full_bis")
    parser.add_argument("--output-dir", type=Path, default=RAW_WOWHEAD_DIR / "phase_gems")
    args = parser.parse_args()
    from tools.scrape_wowhead import html_cache_name, manifest_sources_for_snapshot, snapshot_name
    args.output_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for path in sorted(args.input_dir.glob("*.json")):
        snapshot = json.loads(path.read_text(encoding="utf-8"))
        if snapshot.get("page_type") != "guide" or "--pr-" in path.stem:
            continue
        html_path = args.cache_dir / html_cache_name(snapshot["url"])
        if not html_path.exists():
            continue
        normalized = normalize_phase_gem_guide(snapshot, html_path.read_text(encoding="utf-8"), manifest_sources_for_snapshot(snapshot, "bis_lists"))
        (args.output_dir / snapshot_name(snapshot["url"])).write_text(json.dumps(normalized, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        count += 1
    print(f"Normalized phase gem guidance for {count} guide snapshots")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
