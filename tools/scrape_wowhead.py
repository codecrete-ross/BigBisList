from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
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

try:
    from bs4 import BeautifulSoup
except ModuleNotFoundError:
    BeautifulSoup = None

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.manifest_coverage import build_manifest_coverage
from tools.project import CANONICAL_DIR, PHASE_KEYS, RAW_WOWHEAD_DIR, SLOT_NAMES, canonical_json, write_text
from tools.recommend_leveling import build_recommendation_documents
from tools.reputations import normalize_reputation_names
from tools.sources import (
    classify_source,
    classify_sources,
    derive_acquisition_phase,
    derive_primary_source,
    normalize_source_zone,
    source_text_has_heroic,
    summarize_sources,
)
from tools.validate_data import validate

PARSER_VERSION = "wowhead-scraper-0.9.0"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36 BigBiSListScraper/0.4"

CURRENCY_NAMES = {
    1900: "Arena Points",
    1901: "Honor Points",
    29434: "Badge of Justice",
}

PROFESSION_SKILL_NAMES = {
    164: "Blacksmithing",
    165: "Leatherworking",
    171: "Alchemy",
    197: "Tailoring",
    202: "Engineering",
    333: "Enchanting",
    755: "Jewelcrafting",
}

PROFESSION_NAMES = tuple(sorted(PROFESSION_SKILL_NAMES.values()))

REPUTATION_STANDING_RANKS = {
    "Neutral": 4,
    "Friendly": 5,
    "Honored": 6,
    "Revered": 7,
    "Exalted": 8,
}

REQUIREMENT_TYPES = {
    "reputation",
    "profession",
    "profession_specialization",
    "recipe_known",
    "faction_choice",
    "source_access",
    "unknown_text",
}

REQUIREMENT_SCOPES = {
    "vendor_purchase",
    "quest_reward",
    "self_craft",
    "learn_recipe",
    "cast_enchant",
    "equip_or_use",
    "source_access",
}

REQUIREMENT_CONFIDENCES = {
    "wowhead_item",
    "wowhead_spell_recipe",
    "parsed_source_text",
    "manual_review",
}


def make_soup(markup: str) -> Any:
    if BeautifulSoup is None:
        raise ModuleNotFoundError("beautifulsoup4 is required for Wowhead HTML parsing")
    return BeautifulSoup(markup, "html.parser")

PROFESSION_SPECIALIZATION_PROFESSIONS = {
    "Armorsmith": "Blacksmithing",
    "Master Axesmith": "Blacksmithing",
    "Master Hammersmith": "Blacksmithing",
    "Master Swordsmithing": "Blacksmithing",
    "Weaponsmith": "Blacksmithing",
    "Dragonscale Leatherworking": "Leatherworking",
    "Elemental Leatherworking": "Leatherworking",
    "Tribal Leatherworking": "Leatherworking",
    "Gnomish Engineer": "Engineering",
    "Goblin Engineer": "Engineering",
    "Mooncloth Tailoring": "Tailoring",
    "Shadoweave Tailoring": "Tailoring",
    "Spellfire Tailoring": "Tailoring",
    "Elixir Master": "Alchemy",
    "Potion Master": "Alchemy",
    "Transmutation Master": "Alchemy",
}

ZONE_ID_NAMES = {
    440: "Tanaris",
    1377: "Silithus",
    1583: "Blackrock Spire",
    1584: "Blackrock Depths",
    1941: "Caverns of Time",
    1977: "Zul'Gurub",
    2017: "Stratholme",
    2057: "Scholomance",
    2366: "The Black Morass",
    2367: "Old Hillsbrad Foothills",
    2557: "Dire Maul",
    2677: "Blackwing Lair",
    2717: "Molten Core",
    3428: "Ahn'Qiraj",
    3429: "Ruins of Ahn'Qiraj",
    3456: "Naxxramas",
    3457: "Karazhan",
    3483: "Hellfire Peninsula",
    3518: "Nagrand",
    3519: "Terokkar Forest",
    3520: "Shadowmoon Valley",
    3521: "Zangarmarsh",
    3522: "Blade's Edge Mountains",
    3523: "Netherstorm",
    3562: "Hellfire Ramparts",
    3606: "Hyjal Summit",
    3607: "Serpentshrine Cavern",
    3688: "Auchindoun",
    3703: "Shattrath City",
    3713: "The Blood Furnace",
    3714: "The Shattered Halls",
    3715: "The Steamvault",
    3716: "The Underbog",
    3717: "The Slave Pens",
    3789: "Shadow Labyrinth",
    3790: "Auchenai Crypts",
    3791: "Sethekk Halls",
    3792: "Mana-Tombs",
    3805: "Zul'Aman",
    3836: "Magtheridon's Lair",
    3845: "Tempest Keep",
    3847: "The Botanica",
    3848: "The Arcatraz",
    3849: "The Mechanar",
    3923: "Gruul's Lair",
    3959: "Black Temple",
    4075: "Sunwell Plateau",
    4080: "Isle of Quel'Danas",
    4131: "Magisters' Terrace",
}

CAVERNS_OF_TIME_ENTITY_IDS = {
    19932,  # Andormu
    20080,  # Galgrom
    21643,  # Alurmi
    25177,  # Evee Copperspring
    25178,  # Ecton Brasstumbler
}

RECIPE_ITEM_PREFIXES = ("design:", "formula:", "pattern:", "plans:", "recipe:", "schematic:", "manual:")

SLOT_PATTERNS = [
    ("Head", r"\bheads?\b|\bhelm"),
    ("Neck", r"\bnecks?\b"),
    ("Shoulder", r"\bshoulders?\b"),
    ("Back", r"\bbacks?\b|\bcloaks?\b"),
    ("Chest", r"\bchests?\b"),
    ("Wrist", r"\bwrists?\b|\bbracers?\b"),
    ("Off Hand", r"\boff[- ]?hands?\b|\boffhands?\b|\bshields?\b"),
    ("Two Hand", r"\btwo[- ]?hand(?:ed)?\b|\b2h\b"),
    ("Main Hand", r"\bmain[- ]?hand(?:ed)?\b|\bone[- ]?hand(?:ed)?\b"),
    ("Dual Wield", r"\bdual wield\b"),
    ("Hands", r"\bhands?\b|\bgloves?\b"),
    ("Waist", r"\bwaists?\b|\bbelts?\b"),
    ("Legs", r"\blegs?\b|\bleggings?\b"),
    ("Feet", r"\bfeet\b|\bboots?\b"),
    ("Ring", r"\brings?\b"),
    ("Trinket", r"\btrinkets?\b"),
    ("Quiver", r"\bquivers?\b|\bammo pouches?\b"),
    ("Ammo", r"\bammunition\b|\bammo\b|\barrows?\b|\bbullets?\b"),
    ("Ranged", r"\branged\b|\bwands?\b|\bwandss\b"),
    ("Weapon", r"\bweapons?\b|\bmelee\b"),
    ("Idol", r"\bidols?\b"),
    ("Totem", r"\btotems?\b"),
    ("Libram", r"\blibrams?\b"),
    ("Relic", r"\brelics?\b"),
]

QUALITY_RANKS = {
    "common": 1,
    "uncommon": 2,
    "rare": 3,
    "blue": 3,
    "epic": 4,
    "legendary": 5,
}

CONSUMABLE_CATEGORY_PATTERNS = [
    ("flask", r"\bflasks?\b"),
    ("battle_elixir", r"\bbattle elixirs?\b"),
    ("guardian_elixir", r"\bguardian elixirs?\b"),
    ("elixir", r"\belixirs?\b"),
    ("potion", r"\bpotions?\b"),
    ("food", r"\bfoods?\b|\bwell fed\b"),
    ("weapon_oil", r"\bweapon oils?\b|\bwizard oils?\b|\bmana oils?\b|\bsharpening stones?\b|\bweightstones?\b"),
    ("scroll", r"\bscrolls?\b"),
    ("drum", r"\bdrums?\b"),
    ("utility", r"\butility\b|\bmisc(?:ellaneous)?\b"),
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


def wowhead_slug(value: str | None) -> str:
    normalized = re.sub(r"['\u2019]", "", str(value or "").lower())
    return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")


def page_type_for_url(url: str) -> str:
    if "/guide/" in url:
        return "guide"
    if "/item=" in url:
        return "item"
    if "/spell=" in url:
        return "spell"
    if "/items" in url:
        return "item_list"
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


def item_tooltip_html(item_id: int | None, html: str) -> str:
    if not item_id:
        return ""
    match = re.search(rf"g_items\[{item_id}\]\.tooltip_enus\s*=\s*\"((?:\\.|[^\"])*)\";", html)
    if not match:
        return ""
    try:
        return json.loads(f"\"{match.group(1)}\"")
    except json.JSONDecodeError:
        return ""


def item_tooltip_text(item_id: int | None, html: str) -> str:
    tooltip_html = item_tooltip_html(item_id, html)
    if not tooltip_html:
        return ""
    return element_text(make_soup(tooltip_html))


def item_teaches_spell_ids(item_id: int | None, name: str, html: str) -> list[int]:
    if not name.lower().startswith(RECIPE_ITEM_PREFIXES):
        return []
    tooltip_html = item_tooltip_html(item_id, html)
    if not tooltip_html:
        return []
    spell_ids: list[int] = []
    seen: set[int] = set()
    for link in make_soup(tooltip_html).find_all("a", href=True):
        spell_id = spell_id_from_href(link["href"])
        if not spell_id or spell_id in seen:
            continue
        seen.add(spell_id)
        spell_ids.append(spell_id)
    return spell_ids


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
    if re.search(r"\bweapons?\b\s*(?:and|/)\s*\boff[- ]?hands?\b|\boff[- ]?hands?\b\s*(?:and|/)\s*\bweapons?\b", normalized):
        return "Weapon"
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
    if any(token in normalized for token in ["consumable", "flask", "elixir", "potion", "food", "weapon buff", "weapon enhancement", "scroll", "drum"]):
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


def entity_from_link(link: Any, entity_names: dict[str, dict[int, str]] | None = None) -> dict[str, Any] | None:
    entity_names = entity_names or {}
    href = link.get("href", "")
    item_id = item_id_from_href(href)
    if item_id:
        return {
            "type": "item",
            "id": item_id,
            "name": element_text(link) or entity_names.get("item", {}).get(item_id, ""),
            "url": absolute_tbc_url(href),
        }
    spell_id = spell_id_from_href(href)
    if spell_id:
        return {
            "type": "spell",
            "id": spell_id,
            "name": element_text(link) or entity_names.get("spell", {}).get(spell_id, ""),
            "url": absolute_tbc_url(href),
        }
    return None


def unique_entities(links: list[Any], entity_names: dict[str, dict[int, str]] | None = None) -> list[dict[str, Any]]:
    entities: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for link in links:
        entity = entity_from_link(link, entity_names)
        if not entity:
            continue
        key = (entity["type"], entity["id"])
        if key in seen:
            continue
        seen.add(key)
        entities.append(entity)
    return entities


def source_links_from_element(element: Any) -> list[dict[str, str]]:
    return [
        {
            "href": absolute_tbc_url(link["href"]),
            "text": element_text(link),
        }
        for link in element.find_all("a", href=True)
    ]


def element_without_nested_tables(element: Any) -> Any:
    clone_soup = make_soup(str(element))
    clone = clone_soup.find(getattr(element, "name", None))
    if clone is None:
        return element
    for nested_table in clone.find_all("table"):
        nested_table.decompose()
    return clone


def element_with_resolved_link_text(element: Any, entity_names: dict[str, dict[int, str]] | None = None) -> Any:
    clone_soup = make_soup(str(element))
    clone = clone_soup.find(getattr(element, "name", None))
    if clone is None:
        return element
    for link in clone.find_all("a", href=True):
        if element_text(link):
            continue
        entity = entity_from_link(link, entity_names)
        if entity and entity.get("name"):
            link.string = entity["name"]
    return clone


def level_range_from_text(text: str) -> str | None:
    match = re.fullmatch(r"\s*(\d{1,2})\s*", text)
    if match:
        return str(int(match.group(1)))
    match = re.search(r"\b(?:levels?\s*)?(\d{1,2})\s*[-–]\s*(\d{1,2})\b", text, flags=re.IGNORECASE)
    if match:
        return f"{int(match.group(1))}-{int(match.group(2))}"
    match = re.search(r"\blevel\s+(\d{1,2})\b", text, flags=re.IGNORECASE)
    if match:
        return str(int(match.group(1)))
    return None


def level_bounds_from_range(value: str | None) -> tuple[int | None, int | None, bool]:
    if not value:
        return None, None, False
    match = re.fullmatch(r"\s*(\d{1,2})\s*[-–]\s*(\d{1,2})\s*", str(value))
    if match:
        level_min = max(1, min(70, int(match.group(1))))
        level_max = max(1, min(70, int(match.group(2))))
        if level_max < level_min:
            level_min, level_max = level_max, level_min
        return level_min, level_max, True
    match = re.fullmatch(r"\s*(\d{1,2})\s*", str(value))
    if match:
        level = max(1, min(70, int(match.group(1))))
        return level, None, False
    return None, None, False


def leveling_level_label(level_min: int, level_max: int | None) -> str:
    if level_max and level_max > level_min:
        return f"Recommended from {level_min}-{level_max}"
    return f"Recommended at {level_min}"


def canonical_standing(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip().lower()
    for standing in REPUTATION_STANDING_RANKS:
        if standing.lower() == normalized:
            return standing
    return None


def canonical_profession(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip().lower()
    for profession in PROFESSION_NAMES:
        if profession.lower() == normalized:
            return profession
    return None


def clean_requirement_target(value: str) -> str:
    cleaned = clean_text(value)
    cleaned = re.split(
        r"\s+(?:Vendor|Quest|Drop|Profession):|\s+and\s+requires?\b|\s+requires?\b|\s+when\b",
        cleaned,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    return cleaned.strip(" .:-()")


def is_conditional_bonus_reputation_match(text: str, match_start: int) -> bool:
    context_start = max(
        text.rfind("Equip:", 0, match_start),
        text.rfind("Use:", 0, match_start),
        text.rfind(".", 0, match_start),
        text.rfind(";", 0, match_start),
    )
    context = text[context_start + 1 : match_start].lower()
    return bool(re.search(r"\b(?:if|when)\s+you(?:'re|\s+are)?\b", context))


def extract_aldor_scryer_choices(value: str) -> list[str]:
    choices: list[str] = []
    for faction in ["The Aldor", "The Scryers"]:
        if not re.search(rf"\b{re.escape(faction)}\b", value, flags=re.IGNORECASE):
            continue
        for reputation_name in normalize_reputation_names(faction):
            if reputation_name not in choices:
                choices.append(reputation_name)
    return choices


def extract_explicit_faction_choice_names(text: str) -> list[str]:
    choices: list[str] = []
    choice_patterns = [
        r"\brequires?\s+(?P<choices>(?:the aldor|the scryers)(?:\s*/\s*(?:the aldor|the scryers))*)\b(?!\s*[-–]?\s*(?:Neutral|Friendly|Honored|Revered|Exalted)\b)",
        r"\((?P<choices>(?:the aldor|the scryers)(?:\s*/\s*(?:the aldor|the scryers))*)\)",
    ]
    for pattern in choice_patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            for reputation_name in extract_aldor_scryer_choices(match.group("choices")):
                if reputation_name not in choices:
                    choices.append(reputation_name)
    return choices


def is_explicit_faction_choice_requirement(requirement: dict[str, Any]) -> bool:
    raw_text = str(requirement.get("raw_text") or "")
    if not raw_text:
        return True
    explicit_choices = extract_explicit_faction_choice_names(raw_text)
    if not explicit_choices:
        return False
    requirement_choices: list[str] = []
    for choice in requirement.get("choices") or []:
        for reputation_name in normalize_reputation_names(choice):
            if reputation_name not in requirement_choices:
                requirement_choices.append(reputation_name)
    return bool(requirement_choices) and all(choice in explicit_choices for choice in requirement_choices)


def requirement_looks_like_text(text: str | None) -> bool:
    if not text:
        return False
    lowered = text.lower()
    if re.search(r"\brequires?\s+(?:reapplying|refreshing|casting|using|switching)\b", lowered):
        return False
    return bool(
        re.search(r"\brequires?\b|\bwhen\s+(?:friendly|honored|revered|exalted)\b|\bprofession:\b", lowered)
        or re.search(r"\b(?:friendly|honored|revered|exalted)\s+(?:reputation\s+)?with\b", lowered)
        or re.search(r"\b(?:the aldor|the scryers)\b", lowered)
        or re.search(r"\bbop\b|\bboe\b", lowered)
        or any(specialization.lower() in lowered for specialization in PROFESSION_SPECIALIZATION_PROFESSIONS)
    )


def requirement_scope_from_source_text(text: str) -> str:
    lowered = text.lower()
    if "vendor:" in lowered or lowered.startswith("vendor") or "arena point" in lowered or "honor point" in lowered:
        return "vendor_purchase"
    if "quest:" in lowered or lowered.startswith("quest"):
        return "quest_reward"
    if "profession:" in lowered or "crafted" in lowered or lowered.startswith("profession"):
        if "bop" in lowered or "bind" in lowered:
            return "equip_or_use"
        return "self_craft"
    if "requires" in lowered and any(profession.lower() in lowered for profession in PROFESSION_NAMES):
        return "equip_or_use"
    return "source_access"


def make_requirement(
    requirement_type: str,
    scope: str,
    source_url: str,
    raw_text: str,
    confidence: str,
    **fields: Any,
) -> dict[str, Any]:
    requirement = {
        "type": requirement_type,
        "scope": scope,
        "source_url": source_url,
        "raw_text": clean_text(raw_text),
        "confidence": confidence,
    }
    for key, value in fields.items():
        if value not in (None, "", []):
            requirement[key] = value
    return requirement


def requirement_identity(requirement: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    keys = [
        "type",
        "scope",
        "reputation",
        "standing",
        "profession",
        "specialization",
        "skill",
        "spell_id",
        "item_id",
        "choices",
        "source_url",
        "raw_text",
        "confidence",
    ]
    return tuple(
        (key, json.dumps(requirement.get(key), sort_keys=True))
        for key in keys
        if key in requirement
    )


def dedupe_requirements(requirements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[tuple[str, str], ...]] = set()
    for requirement in requirements:
        requirement_type = requirement.get("type")
        scope = requirement.get("scope")
        if requirement_type not in REQUIREMENT_TYPES or scope not in REQUIREMENT_SCOPES:
            continue
        if requirement_type == "faction_choice" and not is_explicit_faction_choice_requirement(requirement):
            continue
        key = requirement_identity(requirement)
        if key in seen:
            continue
        seen.add(key)
        deduped.append({key: value for key, value in requirement.items() if value not in (None, "", [])})
    return deduped


def extract_reputation_requirements(text: str, source_url: str, scope: str, confidence: str) -> list[dict[str, Any]]:
    requirements: list[dict[str, Any]] = []
    standing_pattern = "|".join(REPUTATION_STANDING_RANKS)
    patterns = [
        rf"\brequires?\s+(?:level\s+\d+\s+requires?\s+)?(?P<reputation>(?:(?!\s+requires?\b).)+?)\s*[-–]\s*(?P<standing>{standing_pattern})(?=(?:\s+(?:Vendor|Quest|Drop|Profession|Use|Equip|Sell Price):|\s+and\s+requires?\b|[.;,]|$))",
        rf"\b(?:requires?|when|at|learned at)\s+(?P<standing>{standing_pattern})(?:\s+reputation)?\s+(?:with|from)\s+(?P<reputation>.+?)(?=(?:\s+(?:Vendor|Quest|Drop|Profession):|\s+and\s+requires?\b|[.;,]|$))",
        rf"\b(?P<standing>{standing_pattern})(?:\s+reputation)?\s+with\s+(?P<reputation>.+?)(?=(?:\s+(?:Vendor|Quest|Drop|Profession):|\s+and\s+requires?\b|[.;,]|$))",
        rf"\((?P<reputation>[^()]+?)\s*(?:-\s*)?(?P<standing>{standing_pattern})\)",
        rf"(?:^|[-:]\s+|\()\s*(?P<reputation>[^,().:;-]+?)\s+(?P<standing>{standing_pattern})(?=[,.)]|$)",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            if is_conditional_bonus_reputation_match(text, match.start()):
                continue
            standing = canonical_standing(match.group("standing"))
            reputation = clean_requirement_target(match.group("reputation"))
            if not standing or not reputation:
                continue
            for reputation_name in normalize_reputation_names(reputation):
                requirements.append(
                    make_requirement(
                        "reputation",
                        scope,
                        source_url,
                        text,
                        confidence,
                        reputation=reputation_name,
                        standing=standing,
                        standing_rank=REPUTATION_STANDING_RANKS[standing],
                    )
                )
    return requirements


def extract_profession_requirements(text: str, source_url: str, scope: str, confidence: str) -> list[dict[str, Any]]:
    requirements: list[dict[str, Any]] = []
    profession_pattern = "|".join(re.escape(profession) for profession in PROFESSION_NAMES)
    for match in re.finditer(
        rf"\b(?:Profession:\s*|Requires\s+)(?P<profession>{profession_pattern})(?:\s*\((?P<skill>\d+)\))?",
        text,
        flags=re.IGNORECASE,
    ):
        profession = canonical_profession(match.group("profession"))
        if not profession:
            continue
        skill = int(match.group("skill")) if match.group("skill") else None
        requirements.append(
            make_requirement(
                "profession",
                scope,
                source_url,
                text,
                confidence,
                profession=profession,
                skill=skill,
            )
        )

    for specialization, profession in PROFESSION_SPECIALIZATION_PROFESSIONS.items():
        if not re.search(rf"\b(?:requires?\s+)?{re.escape(specialization)}\b", text, flags=re.IGNORECASE):
            continue
        requirements.append(
            make_requirement(
                "profession_specialization",
                scope,
                source_url,
                text,
                confidence,
                profession=profession,
                specialization=specialization,
            )
        )

    return requirements


def extract_faction_choice_requirements(text: str, source_url: str, scope: str, confidence: str) -> list[dict[str, Any]]:
    choices = extract_explicit_faction_choice_names(text)
    if not choices:
        return []
    return [
        make_requirement(
            "faction_choice",
            scope,
            source_url,
            text,
            confidence,
            choices=choices,
        )
    ]


def extract_source_access_requirements(text: str, source_url: str, scope: str, confidence: str) -> list[dict[str, Any]]:
    if not re.search(r"\brequires?\s+(?:attun|access|key|heroic)\b", text, flags=re.IGNORECASE):
        return []
    return [make_requirement("source_access", scope, source_url, text, confidence)]


def extract_requirements_from_text(
    text: str | None,
    source_url: str,
    scope: str,
    confidence: str,
    include_unknown: bool = True,
) -> list[dict[str, Any]]:
    raw_text = clean_text(str(text or ""))
    if not raw_text or not source_url:
        return []
    requirements: list[dict[str, Any]] = []
    requirements.extend(extract_reputation_requirements(raw_text, source_url, scope, confidence))
    requirements.extend(extract_profession_requirements(raw_text, source_url, scope, confidence))
    requirements.extend(extract_faction_choice_requirements(raw_text, source_url, scope, confidence))
    requirements.extend(extract_source_access_requirements(raw_text, source_url, scope, confidence))
    if include_unknown and not requirements and requirement_looks_like_text(raw_text):
        requirements.append(make_requirement("unknown_text", scope, source_url, raw_text, confidence))
    return dedupe_requirements(requirements)


def source_requirements_from_source(source: dict[str, Any], source_url: str, default_scope: str, confidence: str) -> list[dict[str, Any]]:
    requirements: list[dict[str, Any]] = []
    source_text = clean_text(str(source.get("raw_source_text") or ""))
    if source_text:
        requirements.extend(extract_requirements_from_text(source_text, source_url, requirement_scope_from_source_text(source_text), "parsed_source_text"))

    profession = canonical_profession(str(source.get("profession") or ""))
    required_skill = source.get("required_skill")
    if profession:
        skill = int(required_skill) if isinstance(required_skill, int) else None
        requirements.append(
            make_requirement(
                "profession",
                default_scope,
                source.get("source_url") or source_url,
                source_text or profession,
                confidence,
                profession=profession,
                skill=skill,
            )
        )
    return dedupe_requirements(requirements)


def requirement_scope_for_source(source: dict[str, Any]) -> str:
    source_type = source.get("type")
    if source_type in {"vendor", "pvp", "token_turnin"}:
        return "vendor_purchase"
    if source_type == "quest":
        return "quest_reward"
    if source_type == "crafted":
        return "self_craft"
    if source_type == "trainer":
        return "learn_recipe"
    return "source_access"


def attach_requirements_to_source(source: dict[str, Any], source_url: str, default_scope: str, confidence: str) -> dict[str, Any]:
    requirements = source_requirements_from_source(source, source_url, default_scope, confidence)
    if requirements:
        source["requirements"] = requirements
    return source


def reparse_requirement_from_raw_text(requirement: dict[str, Any]) -> list[dict[str, Any]]:
    raw_text = clean_text(str(requirement.get("raw_text") or ""))
    source_url = str(requirement.get("source_url") or "")
    scope = str(requirement.get("scope") or "")
    confidence = str(requirement.get("confidence") or "")
    if not raw_text or not source_url or scope not in REQUIREMENT_SCOPES or confidence not in REQUIREMENT_CONFIDENCES:
        return [requirement]
    reparsed = extract_requirements_from_text(raw_text, source_url, scope, confidence, include_unknown=False)
    return reparsed or [requirement]


def normalize_requirement_reputation_names(requirements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for requirement in requirements:
        if not isinstance(requirement, dict):
            continue
        reparsed_requirements = reparse_requirement_from_raw_text(requirement)
        if len(reparsed_requirements) != 1 or reparsed_requirements[0] is not requirement:
            normalized.extend(reparsed_requirements)
            continue
        if requirement.get("type") == "reputation":
            reputation_names = normalize_reputation_names(requirement.get("reputation"))
            if reputation_names:
                for reputation_name in reputation_names:
                    copy = deepcopy(requirement)
                    copy["reputation"] = reputation_name
                    normalized.append(copy)
                continue
        elif requirement.get("type") == "faction_choice":
            choices: list[str] = []
            for choice in requirement.get("choices") or []:
                for reputation_name in normalize_reputation_names(choice):
                    if reputation_name not in choices:
                        choices.append(reputation_name)
            if choices:
                copy = deepcopy(requirement)
                copy["choices"] = choices
                normalized.append(copy)
                continue
        normalized.append(requirement)
    return dedupe_requirements(normalized)


def row_requirements(row: dict[str, Any], source_url: str) -> list[dict[str, Any]]:
    source_text = clean_text(str(row.get("source_text") or row.get("text") or ""))
    parsed_requirements = extract_requirements_from_text(source_text, source_url, requirement_scope_from_source_text(source_text), "parsed_source_text")
    requirements = row.get("normalized_requirements")
    if isinstance(requirements, list):
        normalized_requirements = normalize_requirement_reputation_names([requirement for requirement in requirements if isinstance(requirement, dict)])
        if parsed_requirements:
            structured_requirements = [requirement for requirement in normalized_requirements if requirement.get("type") != "unknown_text"]
            return dedupe_requirements(parsed_requirements + structured_requirements)
        return normalized_requirements
    return parsed_requirements


def parse_guide_sections(soup: BeautifulSoup, entity_names: dict[str, dict[int, str]] | None = None) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []

    for heading_node in soup.find_all(["h2", "h3", "h4"]):
        heading = element_text(heading_node)
        if not heading:
            continue
        data_family = data_family_from_heading(heading)
        if data_family not in {"consumables", "leveling"}:
            continue

        entries: list[dict[str, Any]] = []
        seen_text: set[str] = set()
        for sibling in heading_node.find_next_siblings():
            if getattr(sibling, "name", None) in {"h2", "h3", "h4"}:
                break
            if getattr(sibling, "name", None) == "table":
                continue
            if not hasattr(sibling, "find_all"):
                continue

            blocks = [sibling] if sibling.name in {"p", "li"} else sibling.find_all(["p", "li"])
            for block in blocks:
                if block.find_parent("table"):
                    continue
                clean_block = element_with_resolved_link_text(block, entity_names)
                text = element_text(clean_block)
                if len(text) < 8 or text in seen_text:
                    continue
                seen_text.add(text)
                entries.append(
                    {
                        "section": heading,
                        "text": text,
                        "level_range": level_range_from_text(f"{heading} {text}"),
                        "entities": unique_entities(clean_block.find_all("a", href=True), entity_names),
                        "source_links": source_links_from_element(clean_block),
                    }
                )

        if entries:
            sections.append({"heading": heading, "data_family": data_family, "entries": entries})

    return sections


def parse_guide_html(url: str, html: str) -> dict[str, Any]:
    soup = make_soup(html)
    title = element_text(soup.title) if soup.title else ""
    entity_names = extract_gatherer_names(html)
    tables: list[dict[str, Any]] = []
    sections = parse_guide_sections(soup, entity_names)

    for table in soup.find_all("table"):
        if table.find_parent("table"):
            continue
        heading = nearest_heading(table)
        slot = slot_from_heading(heading)
        data_family = data_family_from_heading(heading)
        rows: list[dict[str, Any]] = []

        for tr in table.find_all("tr", recursive=False):
            cells = tr.find_all(["td", "th"], recursive=False)
            if len(cells) < 2:
                continue
            if any(cell.name == "th" for cell in cells):
                continue

            clean_cells = [element_without_nested_tables(cell) for cell in cells]
            cell_entities = [unique_entities(cell.find_all("a", href=True), entity_names) for cell in clean_cells]
            entities = []
            seen_entities: set[tuple[str, int]] = set()
            for cell_entity_list in cell_entities:
                for entity in cell_entity_list:
                    key = (entity["type"], entity["id"])
                    if key in seen_entities:
                        continue
                    seen_entities.add(key)
                    entities.append(entity)
            if not entities:
                continue

            primary_entity = entities[0]
            primary_item = next((entity for entity in entities if entity["type"] == "item"), None)
            primary_spell = next((entity for entity in entities if entity["type"] == "spell"), None)
            source_cell = clean_cells[2] if len(clean_cells) > 2 else clean_cells[-1]
            row = {
                "rank_label": element_text(clean_cells[0]),
                "entity_type": primary_entity["type"],
                "entity_id": primary_entity["id"],
                "entity_name": primary_entity["name"],
                "entity_url": primary_entity["url"],
                "entities": entities,
                "cell_entities": cell_entities,
                "cells": [element_text(cell) for cell in clean_cells],
                "source_text": element_text(source_cell),
                "source_links": source_links_from_element(source_cell),
            }
            level_range = level_range_from_text(" ".join(row["cells"]))
            if not level_range and row["cells"]:
                level_range = level_range_from_text(str(row["cells"][0]))
            if level_range:
                row["level_range"] = level_range
            if primary_item:
                row["item_id"] = primary_item["id"]
                row["item_name"] = primary_item["name"]
                row["item_url"] = primary_item["url"]
            if primary_spell:
                row["spell_id"] = primary_spell["id"]
                row["spell_name"] = primary_spell["name"]
                row["spell_url"] = primary_spell["url"]
            requirements = extract_requirements_from_text(
                row["source_text"],
                url,
                requirement_scope_from_source_text(row["source_text"]),
                "parsed_source_text",
            )
            if requirements:
                row["normalized_requirements"] = requirements
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
        "sections": sections,
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


def extract_balanced_json_object(text: str, start: int) -> str | None:
    object_start = text.find("{", start)
    if object_start < 0:
        return None

    depth = 0
    in_string = False
    escape = False
    for index in range(object_start, len(text)):
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
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[object_start : index + 1]
    return None


def load_wowhead_json_array(array_text: str) -> list[Any] | None:
    try:
        data = json.loads(array_text)
    except json.JSONDecodeError:
        normalized = re.sub(r",\s*([}\]])", r"\1", array_text)
        normalized = re.sub(r"([{\[,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:", r'\1"\2":', normalized)
        normalized = re.sub(r"\bundefined\b", "null", normalized)
        try:
            data = json.loads(normalized)
        except json.JSONDecodeError:
            return None
    return data if isinstance(data, list) else None


def extract_javascript_array_variable(html: str, variable_name: str) -> list[Any] | None:
    variable_pattern = re.escape(variable_name)
    for match in re.finditer(rf"(?:var\s+)?{variable_pattern}\s*=\s*", html):
        array_text = extract_balanced_json_array(html, match.end())
        if not array_text:
            continue
        data = load_wowhead_json_array(array_text)
        if data is not None:
            return data
    return None


def listview_data_variable_name(object_text: str, data_start: int) -> str | None:
    expression = object_text[data_start : data_start + 200]
    direct = re.match(r"\s*([A-Za-z_$][A-Za-z0-9_$]*)\b", expression)
    if direct and direct.group(1) not in {"WH", "null", "true", "false"}:
        return direct.group(1)
    wrapped = re.match(r"\s*WH\.cOr\(\s*\[\]\s*,\s*([A-Za-z_$][A-Za-z0-9_$]*)\b", expression)
    if wrapped:
        return wrapped.group(1)
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
    data = load_wowhead_json_array(array_text)
    return data if isinstance(data, list) else []


def extract_all_listview_data(html: str) -> dict[str, list[dict[str, Any]]]:
    views: dict[str, list[dict[str, Any]]] = {}
    for match in re.finditer(r"new\s+Listview\s*\(", html):
        object_text = extract_balanced_json_object(html, match.end())
        if not object_text:
            continue
        id_match = re.search(r"\bid\s*:\s*['\"]([^'\"]+)['\"]", object_text)
        data_match = re.search(r"\bdata\s*:\s*", object_text)
        if not id_match or not data_match:
            continue
        array_text = extract_balanced_json_array(object_text, data_match.end())
        data = load_wowhead_json_array(array_text) if array_text else None
        if data is None:
            variable_name = listview_data_variable_name(object_text, data_match.end())
            data = extract_javascript_array_variable(html, variable_name) if variable_name else None
        if isinstance(data, list):
            views[id_match.group(1)] = data
    return views


def extract_gatherer_names(html: str) -> dict[str, dict[int, str]]:
    names: dict[str, dict[int, str]] = {"item": {}, "spell": {}}
    entity_types = {3: "item", 6: "spell"}
    for match in re.finditer(r"WH\.Gatherer\.addData\(\s*([36])\s*,\s*\d+\s*,\s*", html):
        object_text = extract_balanced_json_object(html, match.end())
        if not object_text:
            continue
        try:
            payload = json.loads(object_text)
        except json.JSONDecodeError:
            continue
        entity_type = entity_types.get(int(match.group(1)))
        if not entity_type or not isinstance(payload, dict):
            continue
        for raw_id, row in payload.items():
            if not isinstance(row, dict):
                continue
            try:
                entity_id = int(raw_id)
            except ValueError:
                continue
            name = row.get("name_enus") or row.get("name")
            if isinstance(name, str) and name:
                names[entity_type][entity_id] = name
    return names


def zone_name_for_row(zone_id: int, row: dict[str, Any]) -> str | None:
    try:
        entity_id = int(row.get("id"))
    except (TypeError, ValueError):
        entity_id = None
    if zone_id == 440 and entity_id in CAVERNS_OF_TIME_ENTITY_IDS:
        return "Caverns of Time"
    return ZONE_ID_NAMES.get(zone_id)


def append_zone_name(result: list[str], seen: set[str], zone_id: Any, row: dict[str, Any]) -> None:
    try:
        zone = zone_name_for_row(int(zone_id), row)
    except (TypeError, ValueError):
        return
    if zone and zone not in seen:
        seen.add(zone)
        result.append(zone)


def zone_names_for_row(row: dict[str, Any]) -> list[str]:
    zones: list[str] = []
    seen: set[str] = set()

    locations = row.get("location")
    if isinstance(locations, list):
        for zone_id in locations:
            append_zone_name(zones, seen, zone_id, row)

    category = row.get("category")
    if isinstance(category, int):
        append_zone_name(zones, seen, category, row)

    for source_more in row.get("sourcemore") or []:
        if not isinstance(source_more, dict):
            continue
        append_zone_name(zones, seen, source_more.get("z") or source_more.get("zone"), row)

    return zones


def first_zone_name(row: dict[str, Any]) -> str | None:
    zones = zone_names_for_row(row)
    return zones[0] if zones else None


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


def profession_from_skill(value: Any) -> str | None:
    if isinstance(value, str) and value:
        return value
    if isinstance(value, int):
        return PROFESSION_SKILL_NAMES.get(value)
    if isinstance(value, list):
        for entry in value:
            profession = profession_from_skill(entry)
            if profession:
                return profession
    return None


def recipe_source_type(row: dict[str, Any]) -> str:
    source_kinds = row.get("source")
    if isinstance(source_kinds, list):
        if 5 in source_kinds:
            return "vendor"
        if 4 in source_kinds:
            return "quest"
        if 2 in source_kinds:
            return "drop"
    return "unknown"


def recipe_sources_from_taught_by_items(rows: list[dict[str, Any]], source_url: str) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()

    for row in rows:
        if not isinstance(row, dict):
            continue
        zones = zone_names_for_row(row)
        zone_values = zones or [None]
        for zone in zone_values:
            source = {
                "type": recipe_source_type(row),
                "item_id": row.get("id"),
                "entity_id": row.get("id"),
                "entity_name": row.get("name"),
                "zone": zone,
                "source_url": source_url,
                "confidence": "wowhead_item",
            }
            cleaned = {key: value for key, value in source.items() if value not in (None, "", [])}
            key = (
                cleaned.get("type"),
                cleaned.get("item_id"),
                cleaned.get("entity_name"),
                cleaned.get("zone"),
            )
            if key in seen:
                continue
            seen.add(key)
            sources.append(cleaned)

    if any(source.get("zone") for source in sources):
        sources = [source for source in sources if source.get("zone")]

    return classify_sources(sources)


def add_recipe_sources_to_crafted_sources(
    sources: list[dict[str, Any]],
    recipe_sources: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not recipe_sources:
        return sources

    recipe_zones = sorted({source["zone"] for source in recipe_sources if source.get("zone")})
    enriched: list[dict[str, Any]] = []
    for source in sources:
        if source.get("type") != "crafted":
            enriched.append(source)
            continue
        enriched_source = deepcopy(source)
        enriched_source["recipe_sources"] = deepcopy(recipe_sources)
        if "zone" not in enriched_source and len(recipe_zones) == 1:
            enriched_source["zone"] = recipe_zones[0]
        enriched.append(enriched_source)

    return enriched


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

    for row in tables.get("created-by", []) + tables.get("created-by-spell", []):
        source = {
            "type": "crafted",
            "entity_id": row.get("id"),
            "entity_name": row.get("name"),
            "spell_id": row.get("id"),
            "profession": profession_from_skill(row.get("skill")),
            "source_url": url,
            "confidence": "wowhead_item",
        }
        sources.append({key: value for key, value in source.items() if value is not None})

    for table_name in ["contained-in-object", "gathered-from-object"]:
        for row in tables.get(table_name, []):
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

    for row in tables.get("contained-in-item", []):
        source = {
            "type": "drop",
            "entity_id": row.get("id"),
            "item_id": row.get("id"),
            "entity_name": f"Contained in: {row.get('name')}" if row.get("name") else None,
            "count": row.get("count"),
            "out_of": row.get("outof"),
            "drop_percent": pct_from_row(row),
            "source_url": url,
            "confidence": "wowhead_item",
        }
        sources.append({key: value for key, value in source.items() if value is not None})

    if len(sources) > 8 and all(source.get("type") == "drop" for source in sources):
        max_drop = max((float(source.get("drop_percent") or 0) for source in sources), default=0)
        if max_drop < 1:
            return classify_sources([
                {
                    "type": "world_drop",
                    "entity_name": "World Drop",
                    "world_drop": True,
                    "source_url": url,
                    "confidence": "wowhead_item",
                }
            ])

    sources = add_recipe_sources_to_crafted_sources(
        sources,
        recipe_sources_from_taught_by_items(tables.get("taught-by-item", []), url),
    )

    for source in sources:
        attach_requirements_to_source(source, url, requirement_scope_for_source(source), "wowhead_item")

    return classify_sources(sources)


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


def parse_inventory_slot_from_text(text: str, name: str = "") -> str | None:
    combined = clean_text(f"{name} {text}")
    match = re.search(r"goes in the \"([^\"]+)\" slot", combined, flags=re.IGNORECASE)
    if match:
        return match.group(1)
    lowered = combined.lower()
    if re.search(r"\btwo-hand\b", lowered):
        return "Two Hand"
    if re.search(r"\bmain hand\b", lowered):
        return "Main Hand"
    if re.search(r"\bone-hand\b", lowered):
        return "One Hand"
    if re.search(r"\bheld in off-hand\b|\boff hand\b|\boff-hand\b", lowered):
        return "Off Hand"
    if re.search(r"\branged\s+(?:bow|crossbow|gun|weapon)\b|\bwand\b|\bthrown\b", lowered):
        return "Ranged"
    if re.search(r"\bfinger\b", lowered):
        return "Finger"
    if re.search(r"\btrinket\b", lowered):
        return "Trinket"
    if re.search(r"\brelic\b", lowered):
        return "Relic"
    if " in the arrows category" in lowered or " in the bullets category" in lowered or " this arrow " in f" {lowered} " or " this bullet " in f" {lowered} ":
        return "Ammo"
    name_lower = name.lower()
    if "quiver" in name_lower or "ammo pouch" in name_lower or "bandolier" in name_lower or " in the quivers category" in lowered:
        return "Quiver"
    return None


def canonical_inventory_slot(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip().lower()
    aliases = {
        "finger": "Ring",
        "held in off-hand": "Off Hand",
        "held in off hand": "Off Hand",
        "off-hand": "Off Hand",
        "off hand": "Off Hand",
        "one-hand": "One Hand",
        "one hand": "One Hand",
        "main hand": "Main Hand",
        "two-hand": "Two Hand",
        "two hand": "Two Hand",
        "ranged": "Ranged",
        "wand": "Ranged",
        "thrown": "Ranged",
        "projectile": "Ammo",
        "ammo": "Ammo",
        "quiver": "Quiver",
        "relic": "Relic",
    }
    return aliases.get(normalized, value.strip())


BASE_STAT_ALIASES = {
    "Strength": "strength",
    "Agility": "agility",
    "Stamina": "stamina",
    "Intellect": "intellect",
    "Spirit": "spirit",
}

EQUIP_STAT_PATTERNS = [
    (r"\b(?:increases|improves) (?:your )?attack power by (\d+)\b", "attack_power"),
    (r"\bincreases ranged attack power by (\d+)\b", "ranged_attack_power"),
    (r"\b(?:increases|improves) (?:your )?hit rating by (\d+)\b", "hit_rating"),
    (r"\b(?:increases|improves) (?:your )?spell hit rating by (\d+)\b", "spell_hit_rating"),
    (r"\b(?:increases|improves) (?:your )?critical strike rating by (\d+)\b", "crit_rating"),
    (r"\b(?:increases|improves) (?:your )?spell critical strike rating by (\d+)\b", "spell_crit_rating"),
    (r"\b(?:increases|improves) (?:your )?haste rating by (\d+)\b", "haste_rating"),
    (r"\b(?:increases|improves) (?:your )?resilience rating by (\d+)\b", "resilience_rating"),
    (r"\b(?:increases|improves) (?:your )?defense rating by (\d+)\b", "defense_rating"),
    (r"\b(?:increases|improves) (?:your )?dodge rating by (\d+)\b", "dodge_rating"),
    (r"\b(?:increases|improves) (?:your )?parry rating by (\d+)\b", "parry_rating"),
    (r"\b(?:increases|improves) (?:your )?block rating by (\d+)\b", "block_rating"),
    (r"\b(?:increases|improves) (?:your )?expertise rating by (\d+)\b", "expertise_rating"),
    (r"\bincreases healing done by (?:magical spells and effects )?up to (\d+)\b", "healing_power"),
    (r"\bincreases damage and healing done by magical spells and effects by up to (\d+)\b", "spell_power"),
    (r"\bincreases damage done by (?:magical )?spells and effects by up to (\d+)\b", "spell_damage"),
    (r"\brestores (\d+) mana per 5 sec", "mp5"),
]

WEAPON_SUBTYPES = [
    "Axe",
    "Bow",
    "Crossbow",
    "Dagger",
    "Fist Weapon",
    "Gun",
    "Mace",
    "Polearm",
    "Staff",
    "Sword",
    "Thrown",
    "Wand",
]

ARMOR_TYPES = ["Cloth", "Leather", "Mail", "Plate", "Shield"]


def item_tooltip_lines(item_id: int | None, html: str) -> list[str]:
    tooltip_html = item_tooltip_html(item_id, html)
    if not tooltip_html:
        return []
    soup = make_soup(tooltip_html)
    return [clean_text(line) for line in soup.get_text("\n", strip=True).splitlines() if clean_text(line)]


def tooltip_html_lines(tooltip_html: str) -> list[str]:
    if not tooltip_html:
        return []
    soup = make_soup(tooltip_html)
    return [clean_text(line) for line in soup.get_text("\n", strip=True).splitlines() if clean_text(line)]


def add_stat(stats: dict[str, float], key: str, value: int | float) -> None:
    stats[key] = round(float(stats.get(key, 0)) + float(value), 4)


def parse_socket_bonus(text: str) -> dict[str, float]:
    match = re.search(r"Socket Bonus:\s*\+?(\d+)\s+([A-Za-z ]+)", text, flags=re.IGNORECASE)
    if not match:
        return {}
    stat_name = match.group(2).strip()
    key = BASE_STAT_ALIASES.get(stat_name)
    if not key:
        normalized = re.sub(r"[^a-z0-9]+", "_", stat_name.lower()).strip("_")
        key = normalized or "unknown"
    return {key: float(match.group(1))}


def parse_tooltip_stats(lines: list[str]) -> dict[str, Any]:
    stats: dict[str, float] = {}
    sockets: list[str] = []
    socket_bonus: dict[str, float] = {}
    restrictions: dict[str, list[str]] = {}
    equip_effects: list[str] = []
    use_effects: list[str] = []
    required_level: int | None = None
    item_level: int | None = None
    armor: int | None = None
    weapon_speed: float | None = None
    weapon_min_damage: int | None = None
    weapon_max_damage: int | None = None
    dps: float | None = None
    weapon_type: str | None = None
    weapon_subtype: str | None = None
    armor_type: str | None = None

    flat_text = " ".join(lines)
    match = re.search(r"\bRequires\s+Level\s+(\d{1,2})\b", flat_text, flags=re.IGNORECASE)
    if match:
        required_level = int(match.group(1))
    match = re.search(r"\bItem\s+Level\s+(\d+)\b", flat_text, flags=re.IGNORECASE)
    if match:
        item_level = int(match.group(1))
    damage_match = re.search(r"(\d+)\s*-\s*(\d+)\s+Damage\s+Speed\s+([\d.]+)", flat_text, flags=re.IGNORECASE)
    if damage_match:
        weapon_min_damage = int(damage_match.group(1))
        weapon_max_damage = int(damage_match.group(2))
        weapon_speed = float(damage_match.group(3))

    matched_equip_stat_keys: set[str] = set()
    for line in lines:
        item_level_match = re.search(r"\bItem\s+Level\s+(\d+)\b", line, flags=re.IGNORECASE)
        if item_level_match:
            item_level = int(item_level_match.group(1))

        damage_match = re.search(r"(\d+)\s*-\s*(\d+)\s+Damage\s+Speed\s+([\d.]+)", line, flags=re.IGNORECASE)
        if damage_match:
            weapon_min_damage = int(damage_match.group(1))
            weapon_max_damage = int(damage_match.group(2))
            weapon_speed = float(damage_match.group(3))

        dps_match = re.search(r"\(([\d.]+)\s+damage per second\)", line, flags=re.IGNORECASE)
        if dps_match:
            dps = float(dps_match.group(1))

        armor_match = re.fullmatch(r"(\d+)\s+Armor", line, flags=re.IGNORECASE)
        if armor_match:
            armor = int(armor_match.group(1))

        for stat_name, key in BASE_STAT_ALIASES.items():
            stat_match = re.fullmatch(rf"\+(\d+)\s+{re.escape(stat_name)}", line, flags=re.IGNORECASE)
            if stat_match:
                add_stat(stats, key, int(stat_match.group(1)))

        for pattern, key in EQUIP_STAT_PATTERNS:
            stat_match = re.search(pattern, line, flags=re.IGNORECASE)
            if stat_match:
                add_stat(stats, key, int(stat_match.group(1)))
                matched_equip_stat_keys.add(key)

        socket_match = re.fullmatch(r"(Meta|Red|Yellow|Blue|Prismatic)\s+Socket", line, flags=re.IGNORECASE)
        if socket_match:
            sockets.append(socket_match.group(1).lower())

        if line.lower().startswith("socket bonus:"):
            socket_bonus.update(parse_socket_bonus(line))

        if line.startswith("Equip:"):
            equip_effects.append(line)
        elif line.startswith("Use:"):
            use_effects.append(line)

        classes_match = re.search(r"\bClasses:\s*(.+)$", line)
        if classes_match:
            restrictions["classes"] = [clean_text(value) for value in re.split(r",|/", classes_match.group(1)) if clean_text(value)]
        races_match = re.search(r"\bRaces:\s*(.+)$", line)
        if races_match:
            restrictions["races"] = [clean_text(value) for value in re.split(r",|/", races_match.group(1)) if clean_text(value)]

        lowered = line.lower()
        for subtype in WEAPON_SUBTYPES:
            if re.search(rf"\b{re.escape(subtype.lower())}\b", lowered):
                weapon_subtype = subtype
                break
        if re.search(r"\btwo[- ]hand", lowered):
            weapon_type = "Two Hand"
        elif re.search(r"\bone[- ]hand|\bmain hand|\boff hand|\boff-hand", lowered):
            weapon_type = "One Hand"
        elif any(subtype and subtype.lower() in lowered for subtype in ["bow", "crossbow", "gun", "thrown", "wand"]):
            weapon_type = "Ranged"

        for candidate in ARMOR_TYPES:
            if re.search(rf"\b{candidate.lower()}\b", lowered):
                armor_type = candidate

    for pattern, key in EQUIP_STAT_PATTERNS:
        if key in matched_equip_stat_keys:
            continue
        stat_match = re.search(pattern, flat_text, flags=re.IGNORECASE)
        if stat_match:
            add_stat(stats, key, int(stat_match.group(1)))

    return {
        "required_level": required_level,
        "item_level": item_level,
        "weapon_type": weapon_type,
        "weapon_subtype": weapon_subtype,
        "weapon_speed": weapon_speed,
        "weapon_min_damage": weapon_min_damage,
        "weapon_max_damage": weapon_max_damage,
        "dps": dps,
        "armor": armor,
        "armor_type": armor_type,
        "stats": stats,
        "sockets": sockets,
        "socket_bonus": socket_bonus,
        "restrictions": restrictions,
        "equip_effects": equip_effects,
        "use_effects": use_effects,
    }


def parse_item_stats(url: str, item_id: int | None, name: str, description: str, tooltip_lines: list[str], inventory_slot: str | None, quality: str, binding: str, boe: bool | None, sources: list[dict[str, Any]]) -> dict[str, Any]:
    parsed = parse_tooltip_stats(tooltip_lines)
    description_level = re.search(r"\bitem level of (\d+)\b", description, flags=re.IGNORECASE)
    if parsed["item_level"] is None and description_level:
        parsed["item_level"] = int(description_level.group(1))
    if parsed["required_level"] is None:
        req_match = re.search(r"\brequires level (\d{1,2})\b", description, flags=re.IGNORECASE)
        if req_match:
            parsed["required_level"] = int(req_match.group(1))

    row = {
        "id": item_id,
        "name": name,
        "required_level": parsed["required_level"],
        "item_level": parsed["item_level"],
        "quality": quality,
        "binding": binding,
        "boe": boe,
        "slot": canonical_inventory_slot(inventory_slot),
        "armor_type": parsed["armor_type"],
        "weapon_type": parsed["weapon_type"],
        "weapon_subtype": parsed["weapon_subtype"],
        "weapon_speed": parsed["weapon_speed"],
        "weapon_min_damage": parsed["weapon_min_damage"],
        "weapon_max_damage": parsed["weapon_max_damage"],
        "dps": parsed["dps"],
        "armor": parsed["armor"],
        "stats": parsed["stats"],
        "sockets": parsed["sockets"],
        "socket_bonus": parsed["socket_bonus"],
        "restrictions": parsed["restrictions"],
        "equip_effects": parsed["equip_effects"],
        "use_effects": parsed["use_effects"],
        "source_summary": summarize_sources(sources) if sources else "",
        "primary_source": derive_primary_source(sources) if sources else None,
        "sources": sources,
        "phase": derive_acquisition_phase(sources) if sources else "PR",
        "wowhead_url": url,
        "parse_confidence": "tooltip" if tooltip_lines else "description_only",
    }
    return {key: value for key, value in row.items() if value not in (None, [], {})}


def parse_item_html(url: str, html: str) -> dict[str, Any]:
    soup = make_soup(html)
    title = element_text(soup.title) if soup.title else ""
    name = re.sub(r"\s+-\s+Item\s+-\s+TBC Classic.*$", "", title).strip()
    meta = soup.find("meta", attrs={"name": "description"})
    description = meta.get("content", "") if meta else ""
    item_id = item_id_from_href(url)
    tooltip_text = item_tooltip_text(item_id, html)
    tooltip_lines = item_tooltip_lines(item_id, html)
    inventory_slot = parse_inventory_slot_from_text(f"{tooltip_text} {description}", name)
    binding, boe = parse_binding_from_text(tooltip_text or description)
    listview_ids = [
        "dropped-by",
        "sold-by",
        "reward-from-q",
        "created-by",
        "created-by-spell",
        "taught-by-item",
        "contained-in-object",
        "contained-in-item",
        "gathered-from-object",
    ]
    related_tables = {listview_id: extract_listview_data(html, listview_id) for listview_id in listview_ids}
    sources = normalize_item_sources(url, related_tables)
    item_stats = parse_item_stats(url, item_id, name, description, tooltip_lines, inventory_slot, parse_quality_from_description(description), binding, boe, sources)
    normalized_requirements = extract_requirements_from_text(
        f"{tooltip_text} {description}",
        url,
        "equip_or_use",
        "wowhead_item",
        include_unknown=False,
    )

    return {
        "parser_version": PARSER_VERSION,
        "url": url,
        "fetched_at": now_utc(),
        "page_type": "item",
        "item_id": item_id,
        "name": name,
        "quality": parse_quality_from_description(description),
        "inventory_slot": canonical_inventory_slot(inventory_slot),
        "binding": binding,
        "boe": boe,
        "description": clean_text(description),
        "related_tables": related_tables,
        "normalized_sources": sources,
        "normalized_requirements": normalized_requirements,
        "item_stats": item_stats,
        "taught_by_items": related_tables.get("taught-by-item", []),
        "teaches_spell_ids": item_teaches_spell_ids(item_id, name, html),
    }


def parse_item_tooltip_endpoint(url: str, payload_text: str) -> dict[str, Any]:
    payload = json.loads(payload_text)
    item_id = item_id_from_href(url)
    name = str(payload.get("name") or f"Item {item_id or ''}").strip()
    tooltip_html = str(payload.get("tooltip") or "")
    tooltip_lines = tooltip_html_lines(tooltip_html)
    tooltip_text = element_text(make_soup(tooltip_html)) if tooltip_html else ""
    inventory_slot = parse_inventory_slot_from_text(tooltip_text, name)
    binding, boe = parse_binding_from_text(tooltip_text)
    quality = item_listview_quality_name(payload.get("quality")) or "unknown"
    item_stats = parse_item_stats(url, item_id, name, "", tooltip_lines, inventory_slot, quality, binding, boe, [])
    item_stats["parse_confidence"] = "tooltip_endpoint"
    normalized_requirements = extract_requirements_from_text(
        tooltip_text,
        url,
        "equip_or_use",
        "wowhead_item",
        include_unknown=False,
    )

    return {
        "parser_version": PARSER_VERSION,
        "url": url,
        "fetched_at": now_utc(),
        "page_type": "item",
        "item_id": item_id,
        "name": name,
        "quality": quality,
        "inventory_slot": canonical_inventory_slot(inventory_slot),
        "binding": binding,
        "boe": boe,
        "description": clean_text(tooltip_text),
        "related_tables": {},
        "normalized_sources": [],
        "normalized_requirements": normalized_requirements,
        "item_stats": item_stats,
        "taught_by_items": [],
        "teaches_spell_ids": [],
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

    for row in tables.get("taught-by-npc", []) + tables.get("trained-by", []):
        source = {
            "type": "trainer",
            "entity_id": row.get("id"),
            "entity_name": row.get("name"),
            "zone": first_zone_name(row),
            "source_url": url,
            "confidence": "wowhead_spell",
        }
        sources.append({key: value for key, value in source.items() if value is not None})

    for row in tables.get("taught-by-spell", []):
        source = {
            "type": "taught_by_spell",
            "spell_id": row.get("id"),
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

    for row in tables.get("recipes", []):
        if row.get("trainingcost") is None:
            continue
        source = {
            "type": "trainer",
            "entity_id": "profession_trainer",
            "entity_name": f"{profession_from_skill(row.get('skill')) or 'Profession'} Trainer",
            "profession": profession_from_skill(row.get("skill")),
            "required_skill": row.get("learnedat"),
            "source_url": url,
            "confidence": "wowhead_spell_recipe",
        }
        sources.append({key: value for key, value in source.items() if value is not None})

    for source in sources:
        confidence = "wowhead_spell_recipe" if source.get("type") == "trainer" or source.get("required_skill") else "wowhead_spell_recipe"
        attach_requirements_to_source(source, url, requirement_scope_for_source(source), confidence)

    return classify_sources(sources)


def parse_spell_html(url: str, html: str) -> dict[str, Any]:
    soup = make_soup(html)
    title = element_text(soup.title) if soup.title else ""
    name = re.sub(r"\s+-\s+Spell\s+-\s+TBC Classic.*$", "", title).strip()
    meta = soup.find("meta", attrs={"name": "description"})
    description = meta.get("content", "") if meta else ""
    listview_ids = ["taught-by-item", "taught-by-npc", "taught-by-spell", "trained-by", "sold-by", "reward-from-q", "created-by", "recipes"]
    related_tables = {listview_id: extract_listview_data(html, listview_id) for listview_id in listview_ids}
    normalized_sources = normalize_spell_sources(url, related_tables)
    normalized_requirements = extract_requirements_from_text(
        description,
        url,
        "cast_enchant",
        "wowhead_spell_recipe",
        include_unknown=False,
    )
    for source in normalized_sources:
        normalized_requirements.extend(source.get("requirements", []))
    return {
        "parser_version": PARSER_VERSION,
        "url": url,
        "fetched_at": now_utc(),
        "page_type": "spell",
        "spell_id": spell_id_from_href(url),
        "name": name,
        "description": clean_text(description),
        "related_tables": related_tables,
        "normalized_sources": normalized_sources,
        "normalized_requirements": dedupe_requirements(normalized_requirements),
    }


def parse_item_list_html(url: str, html: str) -> dict[str, Any]:
    soup = make_soup(html)
    title = element_text(soup.title) if soup.title else ""
    listviews = extract_all_listview_data(html)
    discovered: dict[int, dict[str, Any]] = {}
    truncated = bool(re.search(r"_truncated\s*:\s*1", html))
    note_match = re.search(r"note:\s*\"([\d,]+)\s+items found \(([\d,]+)\s+displayed\)", html)
    total_items = int(note_match.group(1).replace(",", "")) if note_match else None
    displayed_items = int(note_match.group(2).replace(",", "")) if note_match else None

    for listview_id, rows in listviews.items():
        for row in rows:
            item_id = row.get("id")
            if not isinstance(item_id, int) or item_id <= 0:
                continue
            name = row.get("name") or discovered.get(item_id, {}).get("name") or f"Item {item_id}"
            discovered[item_id] = {
                "id": item_id,
                "name": name,
                "url": item_url_for_row(item_id, str(name)),
                "listview_id": listview_id,
                "level": row.get("level"),
                "required_level": row.get("reqlevel"),
                "quality": row.get("quality"),
                "slot": row.get("slot"),
            }
            for optional_key in ["source", "sourcemore", "commondrop", "cost", "classs", "subclass"]:
                if row.get(optional_key) not in (None, "", []):
                    discovered[item_id][optional_key] = deepcopy(row[optional_key])

    for link in soup.find_all("a", href=True):
        item_id = item_id_from_href(link["href"])
        if not item_id:
            continue
        discovered.setdefault(
            item_id,
            {
                "id": item_id,
                "name": element_text(link) or f"Item {item_id}",
                "url": absolute_tbc_url(link["href"]) if "/tbc/item=" in link["href"] else item_url_for_row(item_id, element_text(link)),
                "listview_id": "link",
            },
        )

    return {
        "parser_version": PARSER_VERSION,
        "url": url,
        "fetched_at": now_utc(),
        "page_type": "item_list",
        "title": title,
        "item_refs": [discovered[item_id] for item_id in sorted(discovered)],
        "summary": {
            "item_refs": len(discovered),
            "listviews": sorted(listviews),
            "truncated": truncated,
            "total_items": total_items,
            "displayed_items": displayed_items,
        },
    }


def normalize_html(url: str, html: str) -> dict[str, Any]:
    page_type = page_type_for_url(url)
    if page_type == "guide":
        return parse_guide_html(url, html)
    if page_type == "item":
        return parse_item_html(url, html)
    if page_type == "spell":
        return parse_spell_html(url, html)
    if page_type == "item_list":
        return parse_item_list_html(url, html)
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
            request = Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Referer": "https://www.wowhead.com/tbc/items",
                },
            )
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


def fetch_normalized_snapshot(
    url: str,
    cache_dir: Path,
    output_dir: Path,
    *,
    retries: int,
    delay: float,
) -> dict[str, Any]:
    try:
        html = fetch_url(url, cache_dir, retries=retries, delay=delay)
        snapshot = normalize_html(url, html)
    except RuntimeError as exc:
        item_id = item_id_from_href(url)
        if not item_id or "HTTP Error 403" not in str(exc):
            raise
        tooltip_url = f"https://nether.wowhead.com/tbc/tooltip/item/{item_id}"
        payload_text = fetch_url(tooltip_url, cache_dir, retries=retries, delay=delay)
        snapshot = parse_item_tooltip_endpoint(url, payload_text)
    write_snapshot(snapshot, output_dir)
    return snapshot


def manifest_urls(data_family: str | None = None) -> list[str]:
    manifest = canonical_json("scrape_manifest")
    urls: set[str] = set()
    for source in manifest.get("sources", []):
        if data_family and data_family not in source_families(source):
            continue
        for url in manifest_source_urls(source):
            urls.add(url)
    return sorted(urls)


def manifest_source_urls(source: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    if source.get("url"):
        urls.append(str(source["url"]))
    for url in source.get("discovery_urls") or []:
        if isinstance(url, str) and url:
            urls.append(url)
    for url in source.get("seed_urls") or []:
        if isinstance(url, str) and url:
            urls.append(url)
    return urls


def item_corpus_manifest_item_ids() -> set[int]:
    item_ids: set[int] = set()
    manifest = canonical_json("scrape_manifest")
    for source in manifest.get("sources", []):
        if "item_corpus" not in source_families(source):
            continue
        for url in source.get("seed_urls") or []:
            if not isinstance(url, str):
                continue
            item_id = item_id_from_href(url)
            if item_id:
                item_ids.add(item_id)
    return item_ids


def manifest_sources_by_url() -> dict[str, list[dict[str, Any]]]:
    manifest = canonical_json("scrape_manifest")
    sources_by_url: dict[str, list[dict[str, Any]]] = {}
    for source in manifest.get("sources", []):
        for url in manifest_source_urls(source):
            sources_by_url.setdefault(url, []).append(source)
    return sources_by_url


def source_families(source: dict[str, Any]) -> set[str]:
    families = source.get("data_families")
    if isinstance(families, list):
        return {str(family) for family in families if family}
    family = source.get("data_family")
    return {str(family)} if family else set()


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


def item_url_for_row(item_id: int, name: str | None = None) -> str:
    slug = wowhead_slug(name)
    return f"{item_url_for_id(item_id)}/{slug}" if slug else item_url_for_id(item_id)


def spell_url_for_id(spell_id: int) -> str:
    return f"https://www.wowhead.com/tbc/spell={spell_id}"


def discover_entity_urls(snapshots: list[dict[str, Any]], entity_type: str | None = None) -> list[str]:
    urls: set[str] = set()
    for snapshot in snapshots:
        if snapshot.get("page_type") == "item_list" and entity_type in {None, "item"}:
            for ref in snapshot.get("item_refs", []):
                if ref.get("url"):
                    urls.add(ref["url"])
            continue
        if snapshot.get("page_type") != "guide":
            continue
        for table in snapshot.get("tables", []):
            for row in table.get("rows", []):
                for entity in row.get("entities", []):
                    if entity_type and entity.get("type") != entity_type:
                        continue
                    if entity.get("url"):
                        urls.add(entity["url"])
        for section in snapshot.get("sections", []):
            for entry in section.get("entries", []):
                for entity in entry.get("entities", []):
                    if entity_type and entity.get("type") != entity_type:
                        continue
                    if entity.get("url"):
                        urls.add(entity["url"])
    return sorted(urls)


def discover_item_urls(snapshots: list[dict[str, Any]]) -> list[str]:
    return discover_entity_urls(snapshots, "item")


ITEM_CORPUS_LISTVIEW_SLOTS = {1, 2, 3, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 21, 22, 23, 24, 25, 26, 28}
ITEM_LISTVIEW_QUALITY_NAMES = {
    0: "poor",
    1: "common",
    2: "uncommon",
    3: "rare",
    4: "epic",
    5: "legendary",
    6: "artifact",
}
ITEM_LISTVIEW_SLOT_NAMES = {
    1: "Head",
    2: "Neck",
    3: "Shoulder",
    5: "Chest",
    6: "Waist",
    7: "Legs",
    8: "Feet",
    9: "Wrist",
    10: "Hands",
    11: "Ring",
    12: "Trinket",
    13: "One Hand",
    14: "Off Hand",
    15: "Ranged",
    16: "Back",
    17: "Two Hand",
    21: "Main Hand",
    22: "Off Hand",
    23: "Off Hand",
    24: "Ammo",
    25: "Ranged",
    26: "Ranged",
    28: "Relic",
}


def item_corpus_authoritative_urls() -> set[str]:
    urls: set[str] = set()
    manifest = canonical_json("scrape_manifest")
    for source in manifest.get("sources", []):
        if "item_corpus" not in source_families(source):
            continue
        if source.get("url") and source.get("url_policy") != "bootstrap_only":
            urls.add(str(source["url"]))
        for url in source.get("discovery_urls") or []:
            if isinstance(url, str) and url:
                urls.add(url)
        for url in source.get("authoritative_urls") or []:
            if isinstance(url, str) and url:
                urls.add(url)
    return urls


def item_corpus_snapshot_is_authoritative(snapshot: dict[str, Any]) -> bool:
    if snapshot.get("page_type") != "item_list":
        return False
    return str(snapshot.get("url") or "") in item_corpus_authoritative_urls()


def item_corpus_ref_is_in_scope(ref: dict[str, Any]) -> bool:
    try:
        slot = int(ref.get("slot") or 0)
    except (TypeError, ValueError):
        slot = 0
    if slot not in ITEM_CORPUS_LISTVIEW_SLOTS:
        return False
    required_level = ref.get("required_level")
    if required_level in (None, ""):
        try:
            item_level = int(ref.get("level") or 0)
        except (TypeError, ValueError):
            return False
        return 1 <= item_level <= 70
    try:
        return int(required_level) <= 70
    except (TypeError, ValueError):
        return False


def discover_item_corpus_urls(snapshots: list[dict[str, Any]], *, authoritative_only: bool = False) -> list[str]:
    urls: set[str] = set()
    for snapshot in snapshots:
        if snapshot.get("page_type") != "item_list":
            continue
        if authoritative_only and not item_corpus_snapshot_is_authoritative(snapshot):
            continue
        for ref in snapshot.get("item_refs", []):
            if item_corpus_ref_is_in_scope(ref) and ref.get("url"):
                urls.add(ref["url"])
    return sorted(urls)


def item_listview_quality_name(value: Any) -> str | None:
    try:
        return ITEM_LISTVIEW_QUALITY_NAMES.get(int(value))
    except (TypeError, ValueError):
        return None


def item_listview_slot_name(value: Any) -> str | None:
    try:
        return ITEM_LISTVIEW_SLOT_NAMES.get(int(value))
    except (TypeError, ValueError):
        return None


def item_list_source_type(ref: dict[str, Any]) -> str:
    source_kinds = ref.get("source")
    if isinstance(source_kinds, list):
        if 5 in source_kinds:
            return "vendor"
        if 4 in source_kinds:
            return "quest"
        if 3 in source_kinds:
            return "pvp"
        if 1 in source_kinds:
            return "crafted"
        if 2 in source_kinds:
            return "world_drop" if ref.get("commondrop") and not ref.get("sourcemore") else "drop"
    return "unknown"


def item_list_sources_from_ref(ref: dict[str, Any]) -> list[dict[str, Any]]:
    source_type = item_list_source_type(ref)
    source_rows = ref.get("sourcemore") if isinstance(ref.get("sourcemore"), list) else []
    if not source_rows:
        source_rows = [{}]

    sources: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for source_row in source_rows:
        if not isinstance(source_row, dict):
            continue
        row_for_zone = {"sourcemore": [source_row]}
        source = {
            "type": source_type,
            "entity_id": source_row.get("ti") or source_row.get("id"),
            "entity_name": source_row.get("n") or source_row.get("name"),
            "zone": first_zone_name(row_for_zone),
            "source_url": ref.get("url"),
            "confidence": "wowhead_item_list",
        }
        if source_type == "world_drop":
            source["world_drop"] = True
        cleaned = {key: value for key, value in source.items() if value not in (None, "", [])}
        key = (cleaned.get("type"), cleaned.get("entity_id"), cleaned.get("entity_name"), cleaned.get("zone"))
        if key in seen:
            continue
        seen.add(key)
        sources.append(cleaned)

    return classify_sources(sources)


def item_list_metadata_by_id(snapshots: list[dict[str, Any]], *, authoritative_only: bool = False) -> dict[int, dict[str, Any]]:
    metadata: dict[int, dict[str, Any]] = {}
    for snapshot in snapshots:
        if snapshot.get("page_type") != "item_list":
            continue
        if authoritative_only and not item_corpus_snapshot_is_authoritative(snapshot):
            continue
        for ref in snapshot.get("item_refs", []):
            if not item_corpus_ref_is_in_scope(ref):
                continue
            item_id = ref.get("id")
            if not isinstance(item_id, int) or item_id <= 0:
                continue
            current = metadata.setdefault(item_id, {})
            for target_key, source_key in [("required_level", "required_level"), ("item_level", "level")]:
                value = ref.get(source_key)
                if isinstance(value, int):
                    current[target_key] = value
            quality = item_listview_quality_name(ref.get("quality"))
            if quality:
                current["quality"] = quality
            slot = item_listview_slot_name(ref.get("slot"))
            if slot:
                current["slot"] = slot
            if ref.get("name"):
                current["name"] = ref["name"]
            if ref.get("url"):
                current["wowhead_url"] = ref["url"]
            sources = item_list_sources_from_ref(ref)
            if sources:
                current["sources"] = sources
                current["primary_source"] = derive_primary_source(sources)
                current["source_summary"] = summarize_sources(sources)
    return metadata


def apply_item_list_metadata(row: dict[str, Any], metadata: dict[str, Any] | None) -> dict[str, Any]:
    if not metadata:
        return row
    enriched = deepcopy(row)
    for key in ["required_level", "item_level", "slot"]:
        if enriched.get(key) in (None, "", []):
            value = metadata.get(key)
            if value not in (None, "", []):
                enriched[key] = value
    if enriched.get("quality") in (None, "", "unknown"):
        quality = metadata.get("quality")
        if quality:
            enriched["quality"] = quality
    if not enriched.get("sources") and metadata.get("sources"):
        enriched["sources"] = deepcopy(metadata["sources"])
    if not enriched.get("primary_source") and metadata.get("primary_source"):
        enriched["primary_source"] = deepcopy(metadata["primary_source"])
    if not enriched.get("source_summary") and metadata.get("source_summary"):
        enriched["source_summary"] = metadata["source_summary"]
    if enriched.get("phase") in (None, "", "PR") and enriched.get("sources"):
        enriched["phase"] = derive_acquisition_phase(enriched["sources"])
    return enriched


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


def discover_related_source_urls(snapshots: list[dict[str, Any]]) -> list[str]:
    item_ids: set[int] = set()
    spell_ids: set[int] = set()
    urls: set[str] = set()
    spell_alias_urls = reviewed_spell_alias_urls()
    for snapshot in snapshots:
        if snapshot.get("page_type") not in {"item", "spell"}:
            continue
        if snapshot.get("page_type") == "item":
            for taught_by_item in snapshot.get("taught_by_items", []):
                item_id = taught_by_item.get("id")
                if isinstance(item_id, int) and item_id > 0:
                    item_ids.add(item_id)
            for spell_id in snapshot.get("teaches_spell_ids", []):
                if isinstance(spell_id, int) and spell_id > 0:
                    spell_ids.add(spell_id)
        if snapshot.get("page_type") == "spell":
            spell_id = snapshot.get("spell_id")
            if isinstance(spell_id, int):
                urls.update(spell_alias_urls.get(spell_id, []))
        for source in snapshot.get("normalized_sources", []):
            item_id = source.get("item_id")
            if isinstance(item_id, int) and item_id > 0:
                item_ids.add(item_id)
            spell_id = source.get("spell_id")
            if isinstance(spell_id, int) and spell_id > 0:
                spell_ids.add(spell_id)
            item_ids.update(item_cost_ids_from_sources([source]))
    urls.update(item_url_for_id(item_id) for item_id in sorted(item_ids))
    urls.update(spell_url_for_id(spell_id) for spell_id in sorted(spell_ids))
    return sorted(urls)


def reviewed_quest_starter_item_urls() -> list[str]:
    urls: set[str] = set()
    for override in reviewed_overrides():
        if override.get("type") != "quest_starter":
            continue
        data = override.get("data") if isinstance(override.get("data"), dict) else {}
        for item_id in data.get("starter_item_ids") or []:
            if isinstance(item_id, int) and item_id > 0:
                urls.add(item_url_for_id(item_id))
        for starter_item in data.get("starter_items") or []:
            if not isinstance(starter_item, dict):
                continue
            item_id = starter_item.get("id")
            if isinstance(item_id, int) and item_id > 0:
                urls.add(starter_item.get("wowhead_url") or item_url_for_id(item_id))
    return sorted(urls)


def command_fetch(args: argparse.Namespace) -> int:
    output_dir = args.output_dir
    if args.family == "item_corpus" and output_dir == RAW_WOWHEAD_DIR:
        output_dir = RAW_WOWHEAD_DIR / "full_item_corpus"
    cache_dir = output_dir / "html_cache"
    urls = sorted(set(args.url or manifest_urls(args.family)))
    seen_urls: set[str] = set()
    existing_snapshots = load_snapshots(output_dir) if output_dir.is_dir() else []
    existing_snapshot_urls = {str(snapshot.get("url") or "") for snapshot in existing_snapshots}
    existing_item_ids = {
        int(snapshot["item_id"])
        for snapshot in existing_snapshots
        if snapshot.get("page_type") == "item" and isinstance(snapshot.get("item_id"), int)
    }
    snapshots: list[dict[str, Any]] = list(existing_snapshots) if args.family == "item_corpus" else []
    queue = list(urls)
    seed_urls = set(urls)
    include_canonical_items = args.family in {None, "bis_lists"} and not args.url
    fetched = 0

    if args.family == "item_corpus" and not args.no_discover:
        queue.extend(sorted(set(discover_item_corpus_urls(snapshots, authoritative_only=True)) - set(queue)))

    def should_skip_url(url: str) -> bool:
        url_item_id = item_id_from_href(url)
        return bool(args.missing_only and (url in existing_snapshot_urls or (url_item_id is not None and url_item_id in existing_item_ids)))

    def remember_snapshot(snapshot: dict[str, Any], fallback_url: str) -> None:
        snapshots.append(snapshot)
        existing_snapshot_urls.add(str(snapshot.get("url") or fallback_url))
        if snapshot.get("page_type") == "item" and isinstance(snapshot.get("item_id"), int):
            existing_item_ids.add(int(snapshot["item_id"]))

    if args.workers > 1 and args.family == "item_corpus":
        pending_urls: list[str] = []
        while queue and (args.limit is None or len(pending_urls) < args.limit):
            url = queue.pop(0)
            if url in seen_urls:
                continue
            seen_urls.add(url)
            if should_skip_url(url):
                continue
            pending_urls.append(url)

        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(
                    fetch_normalized_snapshot,
                    url,
                    cache_dir,
                    output_dir,
                    retries=args.retries,
                    delay=args.delay,
                ): url
                for url in pending_urls
            }
            for future in as_completed(futures):
                url = futures[future]
                try:
                    snapshot = future.result()
                except RuntimeError as exc:
                    if url in seed_urls:
                        raise
                    print(f"warning: skipped optional discovered URL {url}: {exc}", file=sys.stderr)
                    continue
                remember_snapshot(snapshot, url)
                print(f"snapshot {snapshot['page_type']}: {url}")
        return 0

    while queue:
        url = queue.pop(0)
        if url in seen_urls:
            continue
        seen_urls.add(url)
        if should_skip_url(url):
            continue
        if args.limit is not None and fetched >= args.limit:
            break
        try:
            snapshot = fetch_normalized_snapshot(url, cache_dir, output_dir, retries=args.retries, delay=args.delay)
        except RuntimeError as exc:
            if url in seed_urls:
                raise
            print(f"warning: skipped optional discovered URL {url}: {exc}", file=sys.stderr)
            continue
        remember_snapshot(snapshot, url)
        fetched += 1
        print(f"snapshot {snapshot['page_type']}: {url}")

        if not args.no_discover:
            if args.family == "item_corpus":
                discovery_urls = discover_item_corpus_urls(snapshots, authoritative_only=True)
            else:
                discovery_urls = (
                    discover_entity_urls(snapshots)
                    + (canonical_item_urls() if include_canonical_items else [])
                    + reviewed_quest_starter_item_urls()
                    + discover_token_item_urls(snapshots)
                    + discover_related_source_urls(snapshots)
                )
            discovered = sorted(set(discovery_urls) - seen_urls - set(queue))
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
            snapshots.append(refresh_snapshot_normalized_sources(snapshot))
    return snapshots


def refresh_snapshot_normalized_sources(snapshot: dict[str, Any]) -> dict[str, Any]:
    related_tables = snapshot.get("related_tables")
    if not isinstance(related_tables, dict):
        return snapshot

    page_type = snapshot.get("page_type")
    url = str(snapshot.get("url") or "")
    if page_type == "item":
        refreshed = deepcopy(snapshot)
        refreshed["normalized_sources"] = normalize_item_sources(url, related_tables)
        refreshed["taught_by_items"] = related_tables.get("taught-by-item", [])
        return refreshed
    if page_type == "spell":
        refreshed = deepcopy(snapshot)
        refreshed["normalized_sources"] = normalize_spell_sources(url, related_tables)
        return refreshed
    return snapshot


def reprocess_cached_snapshots(input_dir: Path, output_dir: Path) -> dict[str, Any]:
    cache_dir = input_dir / "html_cache"
    snapshots = load_snapshots(input_dir)
    reprocessed = 0
    missing_html: list[str] = []

    for snapshot in snapshots:
        url = str(snapshot.get("url") or "")
        if not url:
            continue
        html_path = cache_dir / html_cache_name(url)
        if not html_path.is_file():
            missing_html.append(url)
            continue
        updated = normalize_html(url, html_path.read_text(encoding="utf-8", errors="replace"))
        if snapshot.get("fetched_at"):
            updated["fetched_at"] = snapshot["fetched_at"]
        write_snapshot(updated, output_dir)
        reprocessed += 1

    return {
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "snapshots": len(snapshots),
        "reprocessed": reprocessed,
        "missing_html": missing_html,
    }


def command_reprocess(args: argparse.Namespace) -> int:
    output_dir = args.output_dir or args.input_dir
    result = reprocess_cached_snapshots(args.input_dir, output_dir)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not result["missing_html"] else 1


def rank_group_from_label(label: str) -> str:
    lowered = clean_text(label).lower()
    if "pvp" in lowered and not re.search(r"\bnon[-\s]?pvp\b", lowered):
        return "pvp"
    if "unrealistic" in lowered:
        return "unrealistic"
    if lowered.startswith("best until") or re.search(r"\bbest\s+until\b|\buntil\s+t(?:ier)?\s*\d*\b", lowered):
        return "situational"
    if re.search(r"\b(?:option|optional|alternative|viable)\b", lowered):
        return "option"
    if re.search(r"\b(?:near|second|2nd|close)\s+best\b|\bclose\s+second\b", lowered):
        return "ranked" if re.search(r"\d", lowered) else "option"
    if re.search(r"\b(?:bis|best)\b", lowered):
        return "bis"
    if re.search(r"\d", lowered):
        return "ranked"
    return "option"


def normalize_rank_group_value(rank_group: str | None, rank_label: str | None = None) -> str:
    if rank_group == "situational_bis":
        return rank_group_from_label(rank_label or "BiS")
    label_group = rank_group_from_label(rank_label or "")
    if label_group == "bis" and rank_group in {"ranked", "situational", "option"}:
        return "bis"
    if rank_group in {"bis", "ranked", "situational", "pvp", "unrealistic", "option"}:
        return rank_group
    return label_group


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
    if "mitigation" in lowered or "mit skewed" in lowered:
        return "mitigation"
    if "avoidance" in lowered:
        return "avoidance"
    if "defense" in lowered or "defensive" in lowered:
        return "defense"
    if "stamina" in lowered:
        return "stamina"
    if "hit" in lowered or re.search(r"\b[69]%", lowered):
        return "hit"
    if "balanced" in lowered:
        return "balanced"
    if "overall" in lowered:
        return "overall"
    if "survivability" in lowered:
        return "survivability"
    if "main hand" in lowered or re.search(r"\bmh\b", lowered):
        return "main_hand"
    if "off hand" in lowered or "offhand" in lowered or re.search(r"\boh\b", lowered):
        return "off_hand"
    if "dagger" in lowered:
        return "dagger"
    if "set" in lowered or re.search(r"\b[246]p", lowered):
        return "set_bonus"
    if "unrealistic" in lowered and ("alternative" in lowered or "option" in lowered or "viable" in lowered):
        return "unrealistic_option"
    if "unrealistic" in lowered:
        return "unrealistic"
    if "pvp" in lowered and not re.search(r"\bnon[-\s]?pvp\b", lowered):
        return "pvp"
    if "option" in lowered or "alternative" in lowered or "viable" in lowered:
        return "option"
    return "standard"


GENERIC_BIS_LABELS = {"option", "optional", "alternative", "viable"}


def bis_item_entry_preference_key(entry: dict[str, Any]) -> tuple[int, int, int, int, int, str]:
    label = str(entry.get("rank_label") or "")
    normalized_label = clean_text(label).lower()
    rank_group = normalize_rank_group_value(str(entry.get("rank_group") or ""), label)
    rank_order = {
        "bis": 0,
        "ranked": 1,
        "pvp": 2,
        "situational": 3,
        "unrealistic": 4,
        "option": 5,
    }
    best_label_penalty = 0 if re.search(r"\b(best|bis)\b", normalized_label) else 1
    generic_label_penalty = 1 if normalized_label in GENERIC_BIS_LABELS else 0
    empty_label_penalty = 1 if not normalized_label else 0
    return (
        rank_order.get(rank_group, 99),
        best_label_penalty,
        generic_label_penalty,
        empty_label_penalty,
        int(entry.get("rank") or 999),
        normalized_label,
    )


def merge_bis_item_entries(preferred: dict[str, Any], discarded: dict[str, Any]) -> dict[str, Any]:
    merged = dict(preferred)
    if "requirements" not in merged and discarded.get("requirements"):
        merged["requirements"] = discarded["requirements"]
    return merged


def copy_imported_bis_ranks(replacement: dict[str, Any], imported: dict[str, Any] | None) -> dict[str, Any]:
    if not imported:
        return replacement

    imported_by_id: dict[int, list[dict[str, Any]]] = {}
    for item in imported.get("items", []):
        if isinstance(item.get("item_id"), int):
            imported_by_id.setdefault(item["item_id"], []).append(item)

    for item in replacement.get("items", []):
        if item.get("rank") is not None:
            continue
        candidates = imported_by_id.get(item.get("item_id"), [])
        imported_item = next((candidate for candidate in candidates if candidate.get("rank_label") == item.get("rank_label")), None)
        imported_item = imported_item or (candidates[0] if candidates else None)
        if imported_item and imported_item.get("rank") is not None:
            item["rank"] = imported_item["rank"]
    return replacement


def import_bis_lists_from_snapshots(snapshots: list[dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    item_snapshots = item_snapshots_by_id(snapshots)

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
                items_by_phase_slot: dict[tuple[str, str], dict[int, dict[str, Any]]] = {}
                for rank_index, row in enumerate(table.get("rows", []), start=1):
                    item_id = row.get("item_id")
                    phase = phase_from_row(source_meta, table, row)
                    if not item_id or not phase:
                        continue
                    slot = bis_slot_from_row(table, row, item_snapshots.get(int(item_id)))
                    if not slot:
                        continue
                    rank_label = row.get("rank_label") or "Option"
                    context = context_from_rank_label(rank_label)
                    phase_slot = (phase, slot)
                    item_entry = {
                        "item_id": item_id,
                        "rank": rank_index,
                        "rank_label": rank_label,
                        "rank_group": rank_group_from_label(rank_label),
                        "context": context,
                    }
                    requirements = row_requirements(row, snapshot["url"])
                    item_snapshot = item_snapshots.get(int(item_id))
                    requirements = normalize_tradeable_crafted_profession_requirements(
                        requirements,
                        None,
                        item_snapshot,
                        (item_snapshot or {}).get("normalized_sources", []),
                    )
                    if requirements:
                        item_entry["requirements"] = requirements
                    items_for_slot = items_by_phase_slot.setdefault(phase_slot, {})
                    existing = items_for_slot.get(int(item_id))
                    if existing:
                        if bis_item_entry_preference_key(item_entry) < bis_item_entry_preference_key(existing):
                            items_for_slot[int(item_id)] = merge_bis_item_entries(item_entry, existing)
                        else:
                            items_for_slot[int(item_id)] = merge_bis_item_entries(existing, item_entry)
                    else:
                        items_for_slot[int(item_id)] = item_entry
                for (phase, slot), items_by_id in items_by_phase_slot.items():
                    rows.append(
                        {
                            "class": class_name,
                            "spec": spec_name,
                            "phase": phase,
                            "slot": slot,
                            "source_url": snapshot["url"],
                            "items": sorted(items_by_id.values(), key=lambda item: int(item.get("rank") or 999)),
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


def phases_from_row(source_meta: dict[str, Any], table: dict[str, Any], row: dict[str, Any]) -> list[str]:
    detected = phase_from_row(source_meta, table, row)
    if detected:
        return [detected]
    phases = source_meta.get("phases")
    if phases == "*" or source_meta.get("phase") == "*" or source_meta.get("scope") == "all_phases":
        return list(PHASE_KEYS)
    if isinstance(phases, list):
        return [str(phase) for phase in phases if phase in PHASE_KEYS]
    return []


def item_inventory_slot(snapshot: dict[str, Any] | None) -> str | None:
    if not snapshot:
        return None
    slot = snapshot.get("inventory_slot")
    if isinstance(slot, str) and slot:
        return canonical_inventory_slot(slot)
    return canonical_inventory_slot(parse_inventory_slot_from_text(str(snapshot.get("description") or ""), str(snapshot.get("name") or "")))


def bis_slot_compatible(bis_slot: str, inventory_slot: str | None) -> bool:
    if not inventory_slot:
        return True
    inv_slot = canonical_inventory_slot(inventory_slot)
    if bis_slot == inv_slot:
        return True
    if bis_slot == "Ring" and inv_slot == "Finger":
        return True
    if bis_slot == "Main Hand" and inv_slot in {"Main Hand", "One Hand"}:
        return True
    if bis_slot == "Off Hand" and inv_slot in {"Off Hand", "One Hand"}:
        return True
    if bis_slot == "Dual Wield" and inv_slot in {"One Hand", "Main Hand", "Off Hand"}:
        return True
    if bis_slot == "Two Hand" and inv_slot == "Two Hand":
        return True
    if bis_slot == "Ranged" and inv_slot in {"Ranged", "Relic"}:
        return True
    if bis_slot in {"Idol", "Totem", "Libram", "Relic"} and inv_slot == "Relic":
        return True
    if bis_slot == "Ammo" and inv_slot == "Ammo":
        return True
    if bis_slot == "Quiver" and inv_slot == "Quiver":
        return True
    return False


def bis_slot_from_inventory_slot(inventory_slot: str | None) -> str | None:
    inv_slot = canonical_inventory_slot(inventory_slot)
    if inv_slot in {"Head", "Neck", "Shoulder", "Back", "Chest", "Wrist", "Hands", "Waist", "Legs", "Feet", "Trinket", "Ammo", "Quiver", "Ranged", "Off Hand", "Two Hand"}:
        return inv_slot
    if inv_slot in {"Finger", "Ring"}:
        return "Ring"
    if inv_slot in {"One Hand", "Main Hand"}:
        return "Main Hand"
    if inv_slot == "Relic":
        return "Relic"
    return None


def bis_slot_from_rank_label(rank_label: str | None, inventory_slot: str | None = None) -> str | None:
    lowered = clean_text(rank_label or "").lower()
    inv_slot = canonical_inventory_slot(inventory_slot)
    if re.search(r"\bmh\s*/\s*oh\b|\bmh\boh\b", lowered):
        if inv_slot == "Off Hand":
            return "Off Hand"
        if inv_slot in {"One Hand", "Main Hand"}:
            return "Dual Wield"
    if re.search(r"\boh\b", lowered):
        return "Off Hand"
    if re.search(r"\bmh\b", lowered):
        return "Main Hand"
    return None


def bis_slot_from_row(table: dict[str, Any], row: dict[str, Any], item_snapshot: dict[str, Any] | None = None) -> str | None:
    table_slot = table.get("slot")
    inv_slot = item_inventory_slot(item_snapshot)
    rank_slot = bis_slot_from_rank_label(row.get("rank_label"), inv_slot)
    if rank_slot and (not inv_slot or bis_slot_compatible(rank_slot, inv_slot)):
        return rank_slot
    if table_slot in SLOT_NAMES:
        if bis_slot_compatible(str(table_slot), inv_slot):
            return str(table_slot)
        return bis_slot_from_inventory_slot(inv_slot)
    if table_slot == "Weapon":
        if inv_slot == "Two Hand":
            return "Two Hand"
        if inv_slot == "Off Hand":
            return "Off Hand"
        if inv_slot in {"One Hand", "Main Hand"}:
            return "Main Hand"
        if inv_slot == "Ranged":
            return "Ranged"
    if table_slot in {"Ammo", "Quiver"}:
        return str(table_slot)
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
    parts: list[str] = []
    cell_entities = row.get("cell_entities", [])
    for index, cell in enumerate(row.get("cells", [])):
        text = str(cell or "").strip()
        if not text and index < len(cell_entities):
            names = [entity.get("name") for entity in cell_entities[index] if entity.get("name")]
            text = ", ".join(names)
        if text:
            parts.append(text)
    return " | ".join(parts)


def resolved_cell_texts(row: dict[str, Any]) -> list[str]:
    values: list[str] = []
    cell_entities = row.get("cell_entities", [])
    for index, cell in enumerate(row.get("cells", [])):
        text = str(cell or "").strip()
        if not text and index < len(cell_entities):
            text = ", ".join(entity.get("name", "") for entity in cell_entities[index] if entity.get("name"))
        values.append(text)
    return values


def leveling_text_from_row(section: str, row: dict[str, Any]) -> str:
    cells = resolved_cell_texts(row)
    section_lower = section.lower()
    if "abilities to train" in section_lower and len(cells) >= 2:
        level = cells[0].strip()
        ability = cells[1].strip()
        rank = cells[2].strip() if len(cells) > 2 else ""
        if level and ability:
            suffix = f" (Rank {rank})" if rank and rank not in {"-", "0"} else ""
            return f"Level {level}: Train {ability}{suffix}"
    text = compact_cells(row)
    if "|" in text:
        named_entities = [entity.get("name") for entity in row.get("entities", []) if entity.get("name")]
        if named_entities:
            level = cells[0].strip() if cells else ""
            prefix = f"Level {level}: " if re.fullmatch(r"\d{1,2}", level) else ""
            return prefix + ", ".join(named_entities)
    return text


def repair_empty_link_punctuation(text: str, entities: list[dict[str, Any]]) -> str:
    names = [entity.get("name") for entity in entities if entity.get("name")]
    repaired = text
    for name in names:
        repaired = re.sub(rf"{re.escape(name)}\s+\.", f"{name}.", repaired)
    if names and re.search(r"\s\.($|\s)", repaired):
        repaired = re.sub(r"\s\.", f" {names[0]}.", repaired, count=1)
    return re.sub(r"\s+([.,;:])", r"\1", repaired)


def row_context(table: dict[str, Any], row: dict[str, Any]) -> str:
    values = [str(row.get("rank_label") or ""), str(table.get("heading") or "")]
    text = " ".join(values).lower()
    if "jewel" in text:
        return "jewelcrafting"
    if "threat" in text:
        return "threat"
    if "aoe" in text:
        return "aoe"
    if "single target" in text or "single-target" in text:
        return "single_target"
    if "pvp" in text:
        return "pvp"
    if "option" in text or "alternative" in text:
        return "option"
    return "standard"


def quality_rank(value: Any) -> int | None:
    if isinstance(value, int) and 1 <= value <= 5:
        return value
    if not isinstance(value, str):
        return None
    return QUALITY_RANKS.get(value.lower())


def item_snapshots_by_id(snapshots: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    return {
        int(snapshot["item_id"]): snapshot
        for snapshot in snapshots
        if snapshot.get("page_type") == "item" and isinstance(snapshot.get("item_id"), int)
    }


def spell_snapshots_by_id(snapshots: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    return {
        int(snapshot["spell_id"]): snapshot
        for snapshot in snapshots
        if snapshot.get("page_type") == "spell" and isinstance(snapshot.get("spell_id"), int)
    }


def normalized_spell_name(value: str | None) -> str:
    if not value:
        return ""
    return clean_text(value).lower()


def spell_snapshots_by_normalized_name(snapshots: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by_name: dict[str, list[dict[str, Any]]] = {}
    for snapshot in snapshots:
        if snapshot.get("page_type") != "spell" or not isinstance(snapshot.get("spell_id"), int):
            continue
        name = normalized_spell_name(snapshot.get("name"))
        if not name:
            continue
        by_name.setdefault(name, []).append(snapshot)
    for name in by_name:
        by_name[name].sort(key=lambda snapshot: int(snapshot["spell_id"]))
    return by_name


def socket_category_from_text(text: str) -> str:
    normalized = text.lower()
    if "meta" in normalized or "diamond" in normalized:
        return "meta"
    for category in ["red", "yellow", "blue", "orange", "purple", "green", "prismatic"]:
        if re.search(rf"\b{category}\b", normalized):
            return category
    return "unknown"


def normalize_consumable_category(value: str) -> str:
    normalized = value.lower()
    for category, pattern in CONSUMABLE_CATEGORY_PATTERNS:
        if re.search(pattern, normalized):
            return category
    return "utility"


def infer_consumable_category_from_item(snapshot: dict[str, Any] | None) -> str:
    if not snapshot:
        return "utility"
    searchable = " ".join(
        str(snapshot.get(key) or "")
        for key in ["name", "description"]
    )
    return normalize_consumable_category(searchable)


def merge_consumable_categories(categories: list[str], fallback: str) -> str:
    meaningful = [category for category in categories if category and category != "utility"]
    unique = sorted(set(meaningful))
    if len(unique) == 1:
        return unique[0]
    if unique and all(category in {"battle_elixir", "guardian_elixir", "elixir"} for category in unique):
        return "elixir"
    return fallback or "utility"


def consumable_relationship(text: str, item_count: int) -> str:
    if item_count <= 1:
        return "single"
    normalized = f" {clean_text(text).lower()} "
    has_or = bool(re.search(r"\bor\b", normalized)) or "/" in normalized
    has_and = bool(re.search(r"\band\b", normalized)) or "+" in normalized
    if has_or and not has_and:
        return "or"
    return "and"


def enchant_formula_item_ids(spell_snapshot: dict[str, Any] | None) -> list[int]:
    if not spell_snapshot:
        return []
    item_ids: list[int] = []
    seen: set[int] = set()
    for source in spell_snapshot.get("normalized_sources", []):
        item_id = source.get("item_id")
        if isinstance(item_id, int) and item_id > 0 and item_id not in seen:
            seen.add(item_id)
            item_ids.append(item_id)
    return item_ids


def formula_item_ids_for_spell(spell_id: int, item_snapshots: dict[int, dict[str, Any]]) -> list[int]:
    item_ids: list[int] = []
    for item_id, snapshot in sorted(item_snapshots.items()):
        if spell_id not in snapshot.get("teaches_spell_ids", []):
            continue
        name = str(snapshot.get("name") or "").lower()
        if not name.startswith(RECIPE_ITEM_PREFIXES):
            continue
        item_ids.append(item_id)
    return item_ids


def enchant_spell_has_source_data(spell_snapshot: dict[str, Any] | None, item_snapshots: dict[int, dict[str, Any]]) -> bool:
    if not spell_snapshot:
        return False
    if spell_snapshot.get("normalized_sources"):
        return True
    spell_id = spell_snapshot.get("spell_id")
    if isinstance(spell_id, int) and formula_item_ids_for_spell(spell_id, item_snapshots):
        return True
    return bool(enchant_formula_item_ids(spell_snapshot))


def resolve_enchant_source_spell_snapshot(
    spell_id: int,
    spell_snapshot: dict[str, Any] | None,
    spell_snapshots_by_name: dict[str, list[dict[str, Any]]],
    item_snapshots: dict[int, dict[str, Any]],
) -> dict[str, Any] | None:
    if enchant_spell_has_source_data(spell_snapshot, item_snapshots):
        return spell_snapshot
    name = normalized_spell_name((spell_snapshot or {}).get("name"))
    if not name:
        return spell_snapshot
    for candidate in spell_snapshots_by_name.get(name, []):
        if candidate.get("spell_id") == spell_id:
            continue
        if enchant_spell_has_source_data(candidate, item_snapshots):
            return candidate
    return spell_snapshot


def unique_taught_by_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique_sources: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for source in sources:
        if "item_id" in source:
            key = (source.get("type"), "item_id", source["item_id"])
        elif "spell_id" in source:
            key = (source.get("type"), "spell_id", source["spell_id"])
        elif "entity_id" in source:
            key = (source.get("type"), "entity_id", source["entity_id"])
        else:
            key = tuple(sorted(source.items()))
        if key in seen:
            continue
        seen.add(key)
        unique_sources.append(source)
    return unique_sources


def slot_from_row(table: dict[str, Any], row: dict[str, Any]) -> str | None:
    if table.get("slot") in SLOT_NAMES:
        return str(table["slot"])
    for cell in row.get("cells", []):
        slot = slot_from_heading(str(cell))
        if slot:
            return slot
    text = compact_cells(row).lower()
    for slot in sorted(SLOT_NAMES, key=len, reverse=True):
        if re.search(rf"\b{re.escape(slot.lower())}\b", text):
            return slot
    return None


def enchant_slot_from_row(table: dict[str, Any], row: dict[str, Any]) -> str | None:
    slot = slot_from_row(table, row)
    if slot and slot != "Weapon":
        return slot

    exact_cells = {str(cell).strip().lower() for cell in row.get("cells", [])}
    text = compact_cells(row).lower()
    if exact_cells & {"shield", "shields"}:
        return "Off Hand"
    if slot == "Weapon" or exact_cells & {"weapon", "weapons"}:
        if re.search(r"\b(2h|2[- ]hand|two[- ]hand|2 handed|two handed)\b", text):
            return "Two Hand"
        return "Main Hand"
    return None


def summarize_enchant_spell_sources(
    source_spell_snapshot: dict[str, Any] | None,
    formula_item_ids: list[int],
    item_snapshots: dict[int, dict[str, Any]],
) -> str:
    formula_sources: list[dict[str, Any]] = []
    for item_id in formula_item_ids:
        formula_sources.extend(item_snapshots.get(item_id, {}).get("normalized_sources", []))
    if formula_sources:
        return summarize_sources(formula_sources)

    spell_sources = (source_spell_snapshot or {}).get("normalized_sources", [])
    trainer = next((source for source in spell_sources if source.get("type") == "trainer"), None)
    if trainer:
        return f"Trainer: {trainer.get('entity_name') or 'Enchanting Trainer'}"
    if spell_sources:
        return summarize_sources(spell_sources)
    return ""


def table_matches_family(source_meta: dict[str, Any], table: dict[str, Any], data_family: str) -> bool:
    if not source_meta:
        return False
    table_family = table.get("data_family")
    if table_family == data_family:
        return True
    if table_family not in ("unknown", None):
        return False
    heading = str(table.get("heading") or "")
    normalized = heading.lower()
    if data_family == "leveling":
        return any(token in normalized for token in ["leveling", "abilities to train", "rotation", "talent"])
    if data_family == "consumables":
        return any(re.search(pattern, heading, flags=re.IGNORECASE) for _, pattern in CONSUMABLE_CATEGORY_PATTERNS)
    return data_family in {"gems", "enchants"}


def import_gems_from_snapshots(snapshots: list[dict[str, Any]], fallback_to_canonical: bool = True) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, int, str, str]] = set()
    item_snapshots = item_snapshots_by_id(snapshots)

    for snapshot in snapshots:
        if snapshot.get("page_type") != "guide":
            continue
        for source_meta in manifest_sources_for_snapshot(snapshot, "gems"):
            class_name = source_meta.get("class")
            spec_name = source_meta.get("spec")
            if not class_name or not spec_name:
                continue

            for table in snapshot.get("tables", []):
                if not table_matches_family(source_meta, table, "gems"):
                    continue
                for row in table.get("rows", []):
                    item_ids = row_item_ids(row)
                    phases = phases_from_row(source_meta, table, row)
                    if not item_ids or not phases:
                        continue
                    item_id = item_ids[0]
                    cell_text = compact_cells(row)
                    socket_category = socket_category_from_text(f"{table.get('heading') or ''} {cell_text} {row.get('item_name') or ''}")
                    context = row_context(table, row)
                    item_snapshot = item_snapshots.get(item_id)
                    for phase in phases:
                        key = (str(class_name), str(spec_name), phase, item_id, socket_category, context)
                        if key in seen:
                            continue
                        seen.add(key)
                        gem_row: dict[str, Any] = {
                            "class": class_name,
                            "spec": spec_name,
                            "phase": phase,
                            "id": item_id,
                            "name": row.get("item_name"),
                            "socket_category": socket_category,
                            "socket_color": socket_category,
                            "context": context,
                            "meta": socket_category == "meta" or "meta" in cell_text.lower() or str(row.get("item_name", "")).lower().endswith("diamond"),
                            "source_url": snapshot["url"],
                        }
                        quality = quality_from_row(row) or quality_rank((item_snapshot or {}).get("quality"))
                        if quality is not None:
                            gem_row["quality"] = quality
                        sources = (item_snapshot or {}).get("normalized_sources", [])
                        if sources:
                            gem_row["source_summary"] = summarize_sources(sources)
                        requirements = row_requirements(row, snapshot["url"])
                        requirements.extend(snapshot_requirements(item_snapshot))
                        requirements = dedupe_requirements(requirements)
                        if requirements:
                            gem_row["requirements"] = requirements
                        rows.append(gem_row)

    if not rows and fallback_to_canonical:
        return canonical_json("gems")
    return {"gems": rows}


def import_enchants_from_snapshots(snapshots: list[dict[str, Any]], fallback_to_canonical: bool = True) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str, int, str, str]] = set()
    item_snapshots = item_snapshots_by_id(snapshots)
    spell_snapshots = spell_snapshots_by_id(snapshots)
    spell_snapshots_by_name = spell_snapshots_by_normalized_name(snapshots)

    for snapshot in snapshots:
        if snapshot.get("page_type") != "guide":
            continue
        for source_meta in manifest_sources_for_snapshot(snapshot, "enchants"):
            class_name = source_meta.get("class")
            spec_name = source_meta.get("spec")
            if not class_name or not spec_name:
                continue

            for table in snapshot.get("tables", []):
                if not table_matches_family(source_meta, table, "enchants"):
                    continue
                for row in table.get("rows", []):
                    entity = first_row_entity(row)
                    phases = phases_from_row(source_meta, table, row)
                    slot = enchant_slot_from_row(table, row)
                    if not entity or not phases or not slot:
                        continue
                    context = row_context(table, row)
                    entity_id = int(entity["id"])
                    entity_name = entity.get("name")
                    if not entity_name:
                        if entity["type"] == "spell":
                            entity_name = (spell_snapshots.get(entity_id) or {}).get("name")
                        else:
                            entity_name = (item_snapshots.get(entity_id) or {}).get("name")
                    for phase in phases:
                        key = (str(class_name), str(spec_name), phase, slot, entity_id, str(entity["type"]), context)
                        if key in seen:
                            continue
                        seen.add(key)
                        enchant_row: dict[str, Any] = {
                            "class": class_name,
                            "spec": spec_name,
                            "phase": phase,
                            "slot": slot,
                            "id": entity_id,
                            "name": entity_name,
                            "type": entity["type"],
                            "context": context,
                            "source_url": snapshot["url"],
                        }
                        if entity["type"] == "spell":
                            spell_snapshot = spell_snapshots.get(int(entity["id"]))
                            source_spell_snapshot = resolve_enchant_source_spell_snapshot(
                                int(entity["id"]),
                                spell_snapshot,
                                spell_snapshots_by_name,
                                item_snapshots,
                            )
                            source_spell_id = (source_spell_snapshot or {}).get("spell_id")
                            formula_spell_ids = [int(entity["id"])]
                            if isinstance(source_spell_id, int) and source_spell_id not in formula_spell_ids:
                                formula_spell_ids.append(source_spell_id)
                                enchant_row["source_spell_id"] = source_spell_id
                            formula_item_ids = sorted(
                                set(enchant_formula_item_ids(source_spell_snapshot))
                                | {
                                    item_id
                                    for formula_spell_id in formula_spell_ids
                                    for item_id in formula_item_ids_for_spell(formula_spell_id, item_snapshots)
                                }
                            )
                            if formula_item_ids:
                                enchant_row["formula_item_ids"] = formula_item_ids
                            taught_by = [
                                {
                                    key: source[key]
                                    for key in ["type", "item_id", "spell_id", "entity_id", "entity_name", "zone", "requirements"]
                                    if key in source
                                }
                                for source in (source_spell_snapshot or {}).get("normalized_sources", [])
                            ]
                            taught_by.extend(
                                {
                                    "type": "taught_by_item",
                                    "item_id": item_id,
                                    "entity_name": item_snapshots[item_id].get("name"),
                                }
                                for item_id in formula_item_ids
                                if item_id in item_snapshots
                            )
                            if taught_by:
                                enchant_row["taught_by"] = unique_taught_by_sources(taught_by)
                            source_summary = summarize_enchant_spell_sources(source_spell_snapshot, formula_item_ids, item_snapshots)
                            if source_summary:
                                enchant_row["source_summary"] = source_summary
                            requirements = enchant_requirements_for_import(
                                row,
                                snapshot["url"],
                                entity,
                                spell_snapshot,
                                source_spell_snapshot,
                                formula_item_ids,
                                item_snapshots,
                            )
                            if requirements:
                                enchant_row["requirements"] = requirements
                        else:
                            sources = item_snapshots.get(int(entity["id"]), {}).get("normalized_sources", [])
                            if sources:
                                enchant_row["source_summary"] = summarize_sources(sources)
                            requirements = enchant_requirements_for_import(
                                row,
                                snapshot["url"],
                                entity,
                                None,
                                None,
                                [],
                                item_snapshots,
                            )
                            if requirements:
                                enchant_row["requirements"] = requirements
                        rows.append(enchant_row)

    if not rows and fallback_to_canonical:
        return canonical_json("enchants")
    return {"enchants": rows}


def consumable_category(table: dict[str, Any], row: dict[str, Any]) -> str:
    first_cell = str(row.get("cells", [""])[0]).strip() if row.get("cells") else ""
    if (
        first_cell
        and len(first_cell) <= 80
        and not re.fullmatch(r"\d+|bis|best|option", first_cell, flags=re.IGNORECASE)
        and any(re.search(pattern, first_cell, flags=re.IGNORECASE) for _, pattern in CONSUMABLE_CATEGORY_PATTERNS)
    ):
        return normalize_consumable_category(first_cell)
    heading = str(table.get("heading") or "").strip()
    return normalize_consumable_category(heading or "Consumables")


def consumable_category_label(table: dict[str, Any], row: dict[str, Any]) -> str:
    first_cell = str(row.get("cells", [""])[0]).strip() if row.get("cells") else ""
    if first_cell and len(first_cell) <= 80 and any(re.search(pattern, first_cell, flags=re.IGNORECASE) for _, pattern in CONSUMABLE_CATEGORY_PATTERNS):
        return first_cell
    return str(table.get("heading") or "Consumables")


def import_consumables_from_snapshots(snapshots: list[dict[str, Any]], fallback_to_canonical: bool = True) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str, tuple[int, ...]]] = set()
    item_snapshots = item_snapshots_by_id(snapshots)

    for snapshot in snapshots:
        if snapshot.get("page_type") != "guide":
            continue
        for source_meta in manifest_sources_for_snapshot(snapshot, "consumables"):
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
                    row_text = clean_text(str(row.get("source_text") or compact_cells(row) or ""))
                    raw_category = consumable_category(table, row)
                    item_categories = [infer_consumable_category_from_item(item_snapshots.get(item_id)) for item_id in item_ids]
                    category = merge_consumable_categories(item_categories, raw_category)
                    category_label = consumable_category_label(table, row)
                    if len(category_label) > 120:
                        continue
                    relationship = consumable_relationship(row_text, len(item_ids))
                    phases = phases_from_row(source_meta, table, row) or [str(source_meta.get("phase") or "")]
                    for phase in phases:
                        key = (str(class_name), str(spec_name), phase, category, tuple(item_ids))
                        if key in seen:
                            continue
                        seen.add(key)
                        consumable_row: dict[str, Any] = {
                            "class": class_name,
                            "spec": spec_name,
                            "category": category,
                            "category_label": category_label,
                            "items": item_ids,
                            "item_names": [entity["name"] for entity in row.get("entities", []) if entity.get("type") == "item" and entity.get("id") in item_ids],
                            "item_categories": item_categories,
                            "relationship": relationship,
                            "source_url": snapshot["url"],
                        }
                        if row_text:
                            consumable_row["text"] = row_text
                        if phase:
                            consumable_row["phase"] = phase
                        source_summaries = {
                            str(item_id): summarize_sources(item_snapshots[item_id].get("normalized_sources", []))
                            for item_id in item_ids
                            if item_id in item_snapshots and item_snapshots[item_id].get("normalized_sources")
                        }
                        if source_summaries:
                            consumable_row["source_summaries"] = source_summaries
                        requirements = row_requirements(row, snapshot["url"])
                        for item_id in item_ids:
                            requirements.extend(snapshot_requirements(item_snapshots.get(item_id)))
                        requirements = dedupe_requirements(requirements)
                        if requirements:
                            consumable_row["requirements"] = requirements
                        rows.append(consumable_row)

            for section in snapshot.get("sections", []):
                if section.get("data_family") != "consumables":
                    continue
                section_title = str(section.get("heading") or "Consumables")
                if len(section_title) > 120:
                    continue
                raw_category = normalize_consumable_category(section_title)
                for entry in section.get("entries", []):
                    item_ids = row_item_ids(entry)
                    if not item_ids:
                        continue
                    entry_text = clean_text(str(entry.get("text") or ""))
                    item_categories = [infer_consumable_category_from_item(item_snapshots.get(item_id)) for item_id in item_ids]
                    category = merge_consumable_categories(item_categories, raw_category)
                    relationship = consumable_relationship(entry_text, len(item_ids))
                    phase_row = {"cells": [entry_text], "source_text": entry_text}
                    phases = phases_from_row(source_meta, {"heading": section_title}, phase_row) or [str(source_meta.get("phase") or "")]
                    for phase in phases:
                        key = (str(class_name), str(spec_name), phase, category, tuple(item_ids))
                        if key in seen:
                            continue
                        seen.add(key)
                        consumable_row = {
                            "class": class_name,
                            "spec": spec_name,
                            "category": category,
                            "category_label": section_title,
                            "items": item_ids,
                            "item_names": [entity["name"] for entity in entry.get("entities", []) if entity.get("type") == "item" and entity.get("id") in item_ids],
                            "item_categories": item_categories,
                            "relationship": relationship,
                            "source_url": snapshot["url"],
                        }
                        if entry_text:
                            consumable_row["text"] = entry_text
                        if phase:
                            consumable_row["phase"] = phase
                        source_summaries = {
                            str(item_id): summarize_sources(item_snapshots[item_id].get("normalized_sources", []))
                            for item_id in item_ids
                            if item_id in item_snapshots and item_snapshots[item_id].get("normalized_sources")
                        }
                        if source_summaries:
                            consumable_row["source_summaries"] = source_summaries
                        requirements = row_requirements(entry, snapshot["url"])
                        for item_id in item_ids:
                            requirements.extend(snapshot_requirements(item_snapshots.get(item_id)))
                        requirements = dedupe_requirements(requirements)
                        if requirements:
                            consumable_row["requirements"] = requirements
                        rows.append(consumable_row)

    if not rows and fallback_to_canonical:
        return canonical_json("consumables")
    return {"consumables": rows}


def import_leveling_from_snapshots(snapshots: list[dict[str, Any]], fallback_to_canonical: bool = True) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str, str, str]] = set()
    item_snapshots = item_snapshots_by_id(snapshots)
    spell_snapshots = spell_snapshots_by_id(snapshots)

    for snapshot in snapshots:
        if snapshot.get("page_type") != "guide":
            continue
        for source_meta in manifest_sources_for_snapshot(snapshot, "leveling"):
            class_name = source_meta.get("class")
            spec_name = source_meta.get("spec")
            if not class_name or not spec_name:
                continue

            for table in snapshot.get("tables", []):
                if not table_matches_family(source_meta, table, "leveling"):
                    continue
                for row in table.get("rows", []):
                    row = row_with_resolved_entities(row, item_snapshots, spell_snapshots)
                    text = leveling_text_from_row(str(table.get("heading") or "Leveling"), row)
                    text = repair_empty_link_punctuation(text, row.get("entities", []))
                    if not text:
                        continue
                    section = str(table.get("heading") or "Leveling")
                    phases = phases_from_row(source_meta, table, row)
                    if source_meta.get("phases") == "*" or source_meta.get("phase") == "*" or source_meta.get("scope") == "all_phases":
                        phases = [""]
                    phases = phases or [str(source_meta.get("phase") or "")]
                    level_range = row.get("level_range") or level_range_from_text(f"{section} {text}")
                    for phase in phases:
                        key = (str(class_name), str(spec_name), phase, section, str(level_range or ""), text)
                        if key in seen:
                            continue
                        seen.add(key)
                        leveling_row = {
                            "class": class_name,
                            "spec": spec_name,
                            "section": section,
                            "label": row.get("rank_label") or "",
                            "text": text,
                            "entities": row.get("entities", []),
                            "source_url": snapshot["url"],
                        }
                        if phase:
                            leveling_row["phase"] = phase
                        if level_range:
                            leveling_row["level_range"] = level_range
                        rows.append(leveling_row)

            for section in snapshot.get("sections", []):
                if section.get("data_family") != "leveling":
                    continue
                section_title = str(section.get("heading") or "Leveling")
                for entry in section.get("entries", []):
                    entry = row_with_resolved_entities(entry, item_snapshots, spell_snapshots)
                    text = clean_text(str(entry.get("text") or ""))
                    text = repair_empty_link_punctuation(text, entry.get("entities", []))
                    if not text:
                        continue
                    phase_row = {"cells": [text], "source_text": text}
                    phases = phases_from_row(source_meta, {"heading": section_title}, phase_row)
                    if source_meta.get("phases") == "*" or source_meta.get("phase") == "*" or source_meta.get("scope") == "all_phases":
                        phases = [""]
                    phases = phases or [str(source_meta.get("phase") or "")]
                    level_range = entry.get("level_range") or level_range_from_text(f"{section_title} {text}")
                    for phase in phases:
                        key = (str(class_name), str(spec_name), phase, section_title, str(level_range or ""), text)
                        if key in seen:
                            continue
                        seen.add(key)
                        leveling_row = {
                            "class": class_name,
                            "spec": spec_name,
                            "section": section_title,
                            "text": text,
                            "entities": entry.get("entities", []),
                            "source_url": snapshot["url"],
                        }
                        if phase:
                            leveling_row["phase"] = phase
                        if level_range:
                            leveling_row["level_range"] = level_range
                        rows.append(leveling_row)

    if not rows and fallback_to_canonical:
        return canonical_json("leveling")
    return {"leveling": rows}


LEVELING_GEAR_HEADING_RE = re.compile(
    r"\b(?:best\s+leveling|leveling\s+(?:weapons?|gear)|weapons?|gear|equipment)\b",
    flags=re.IGNORECASE,
)


def table_matches_leveling_gear(table: dict[str, Any]) -> bool:
    heading = str(table.get("heading") or "")
    if not LEVELING_GEAR_HEADING_RE.search(heading):
        return False
    return any(row_item_ids(row) for row in table.get("rows", []))


def leveling_gear_category_label(table: dict[str, Any]) -> str:
    heading = clean_text(str(table.get("heading") or ""))
    lowered = heading.lower()
    if "damage-focused" in lowered or "damage focused" in lowered:
        return "Damage-focused"
    if "healing-focused" in lowered or "healing focused" in lowered:
        return "Healing-focused"
    if "tanking" in lowered or "tank" in lowered:
        return "Tank pick"
    return "Recommended"


def row_item_entities(row: dict[str, Any]) -> list[dict[str, Any]]:
    entities: list[dict[str, Any]] = []
    seen: set[int] = set()
    for entity in row.get("entities", []):
        if entity.get("type") != "item" or not isinstance(entity.get("id"), int):
            continue
        item_id = int(entity["id"])
        if item_id in seen:
            continue
        seen.add(item_id)
        entities.append(entity)
    return entities


def infer_leveling_gear_ranges(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = {}
    for row in rows:
        key = (
            str(row.get("class") or ""),
            str(row.get("spec") or ""),
            str(row.get("section") or ""),
            str(row.get("slot") or ""),
            str(row.get("category_label") or ""),
        )
        grouped.setdefault(key, []).append(row)

    for group_rows in grouped.values():
        starts = sorted({int(row["level_min"]) for row in group_rows if isinstance(row.get("level_min"), int)})
        for row in group_rows:
            level_min = int(row["level_min"])
            if not row.pop("_explicit_level_max", False):
                next_start = next((start for start in starts if start > level_min), None)
                row["level_max"] = max(level_min, min(70, (next_start - 1) if next_start else 70))
            else:
                row["level_max"] = max(level_min, min(70, int(row.get("level_max") or level_min)))
            row["level_label"] = leveling_level_label(level_min, int(row["level_max"]))

    return rows


def import_leveling_gear_from_snapshots(snapshots: list[dict[str, Any]], fallback_to_canonical: bool = True) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, int, int, str, int, str, str]] = set()
    item_snapshots = item_snapshots_by_id(snapshots)

    for snapshot in snapshots:
        if snapshot.get("page_type") != "guide":
            continue
        for source_meta in manifest_sources_for_snapshot(snapshot, "leveling"):
            class_name = source_meta.get("class")
            spec_name = source_meta.get("spec")
            if not class_name or not spec_name:
                continue

            for table in snapshot.get("tables", []):
                if not table_matches_leveling_gear(table):
                    continue
                section = str(table.get("heading") or "Leveling Gear")
                category_label = leveling_gear_category_label(table)
                for row_index, row in enumerate(table.get("rows", []), start=1):
                    cells = row.get("cells", [])
                    level_range = row.get("level_range") or level_range_from_text(" ".join(str(cell) for cell in cells))
                    if not level_range and cells:
                        level_range = level_range_from_text(str(cells[0]))
                    level_min, level_max, explicit_level_max = level_bounds_from_range(level_range)
                    if not level_min:
                        continue
                    source_note = clean_text(str(row.get("source_text") or ""))
                    for entity_index, entity in enumerate(row_item_entities(row), start=1):
                        item_id = int(entity["id"])
                        item_snapshot = item_snapshots.get(item_id)
                        item_row = deepcopy(row)
                        item_row["item_id"] = item_id
                        item_row["item_name"] = entity.get("name") or row.get("item_name")
                        slot = bis_slot_from_row(table, item_row, item_snapshot)
                        if not slot:
                            slot = bis_slot_from_inventory_slot(item_inventory_slot(item_snapshot))
                        if not slot:
                            continue

                        key = (
                            str(class_name),
                            str(spec_name),
                            int(level_min),
                            int(level_max or 0),
                            slot,
                            item_id,
                            section,
                            source_note,
                        )
                        if key in seen:
                            continue
                        seen.add(key)

                        requirements = row_requirements(row, snapshot["url"])
                        requirements.extend(snapshot_requirements(item_snapshot))
                        requirements = normalize_tradeable_crafted_profession_requirements(
                            requirements,
                            None,
                            item_snapshot,
                            (item_snapshot or {}).get("normalized_sources", []),
                        )
                        leveling_row: dict[str, Any] = {
                            "class": class_name,
                            "spec": spec_name,
                            "level_min": level_min,
                            "level_max": level_max or level_min,
                            "_explicit_level_max": explicit_level_max,
                            "level_label": leveling_level_label(level_min, level_max or level_min),
                            "slot": slot,
                            "item_id": item_id,
                            "rank": (row_index * 10) + entity_index,
                            "category_label": category_label,
                            "section": section,
                            "source_note": source_note,
                            "source_url": snapshot["url"],
                        }
                        if requirements:
                            leveling_row["requirements"] = requirements
                        rows.append(leveling_row)

    if not rows and fallback_to_canonical:
        return canonical_json("leveling_gear")
    rows = infer_leveling_gear_ranges(rows)
    rows.sort(
        key=lambda row: (
            str(row["class"]),
            str(row["spec"]),
            int(row["level_min"]),
            str(row["slot"]),
            int(row["rank"]),
            int(row["item_id"]),
        )
    )
    return {"leveling_gear": rows}


def import_entity_sources_from_snapshots(
    snapshots: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    output_key: str,
) -> dict[str, Any]:
    wanted_item_ids = {row.get("id") for row in rows if row.get("id") and row.get("type", "item") != "spell"}
    wanted_item_ids.update(item_id for row in rows for item_id in row.get("items", []))
    wanted_item_ids.update(item_id for row in rows for item_id in row.get("formula_item_ids", []))
    wanted_spell_ids = {row.get("id") for row in rows if row.get("type") == "spell" and row.get("id")}
    item_snapshots = {snapshot.get("item_id"): snapshot for snapshot in snapshots if snapshot.get("page_type") == "item"}
    spell_snapshots = {snapshot.get("spell_id"): snapshot for snapshot in snapshots if snapshot.get("page_type") == "spell"}
    source_rows: list[dict[str, Any]] = []

    for item_id in sorted(item_id for item_id in wanted_item_ids if item_id in item_snapshots):
        snapshot = item_snapshots[item_id]
        sources = snapshot.get("normalized_sources", [])
        requirements = dedupe_requirements(snapshot_requirements(snapshot) + source_list_requirements(sources))
        source_row = {
            "id": item_id,
            "type": "item",
            "name": snapshot.get("name"),
            "sources": sources,
            "primary_source": derive_primary_source(sources),
            "source_summary": summarize_sources(sources),
            "source_url": snapshot["url"],
        }
        if requirements:
            source_row["requirements"] = requirements
        source_rows.append(source_row)

    for spell_id in sorted(spell_id for spell_id in wanted_spell_ids if spell_id in spell_snapshots):
        snapshot = spell_snapshots[spell_id]
        sources = snapshot.get("normalized_sources", [])
        requirements = dedupe_requirements(snapshot_requirements(snapshot) + source_list_requirements(sources))
        source_row = {
            "id": spell_id,
            "type": "spell",
            "name": snapshot.get("name"),
            "sources": sources,
            "source_url": snapshot["url"],
        }
        if requirements:
            source_row["requirements"] = requirements
        source_rows.append(source_row)

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

    return classify_sources(resolved_sources)


def guide_item_refs(snapshots: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    refs: dict[int, dict[str, Any]] = {}
    for snapshot in snapshots:
        if snapshot.get("page_type") != "guide":
            continue
        for table in snapshot.get("tables", []):
            for row in table.get("rows", []):
                entities_by_id = {
                    entity.get("id"): entity
                    for entity in row.get("entities", [])
                    if entity.get("type") == "item" and isinstance(entity.get("id"), int)
                }
                for item_id in row_item_ids(row):
                    entity = entities_by_id.get(item_id, {})
                    refs[item_id] = {
                        "id": item_id,
                        "name": entity.get("name") or row.get("item_name") or row.get("entity_name") or f"Item {item_id}",
                        "wowhead_url": entity.get("url") or row.get("item_url") or item_url_for_id(item_id),
                    }
    return refs


def guide_item_source_hints(snapshots: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    hints: dict[int, list[dict[str, Any]]] = {}
    for snapshot in snapshots:
        if snapshot.get("page_type") != "guide":
            continue
        for table in snapshot.get("tables", []):
            for row in table.get("rows", []):
                item_ids = row_item_ids(row)
                if not item_ids:
                    continue
                source_text = clean_text(str(row.get("source_text") or ""))
                if not source_text:
                    continue
                for item_id in item_ids:
                    hints.setdefault(item_id, []).append(
                        {
                            "source_text": source_text,
                            "source_links": row.get("source_links", []),
                            "source_url": snapshot["url"],
                        }
                    )
    return hints


def source_hint_matches_source(source: dict[str, Any], hint: dict[str, Any]) -> bool:
    if source.get("type") != "drop" or not source_text_has_heroic(hint.get("source_text")):
        return False

    source_text = clean_text(str(hint.get("source_text") or ""))
    source_text_lower = source_text.lower()

    entity_id = source.get("entity_id")
    if isinstance(entity_id, int):
        for link in hint.get("source_links", []):
            if isinstance(link, dict) and entity_id_from_href(str(link.get("href") or ""), "npc") == entity_id:
                return True

    entity_name = source.get("entity_name")
    if isinstance(entity_name, str) and entity_name and entity_name.lower() in source_text_lower:
        return True

    _, hint_zone = source_name_and_zone_from_text(source_text, r"^(drop|zone drop):")
    hint_zone, _ = normalize_source_zone(hint_zone)
    source_zone, _ = normalize_source_zone(source.get("zone"))
    return bool(hint_zone and source_zone and hint_zone == source_zone)


def heroic_zone_from_hint(hint: dict[str, Any]) -> str | None:
    source_text = clean_text(str(hint.get("source_text") or ""))
    _, zone = source_name_and_zone_from_text(source_text, r"^(drop|zone drop):")
    zone, _ = normalize_source_zone(zone)
    return zone


def apply_source_hints_to_sources(sources: list[dict[str, Any]], hints: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not hints:
        return sources

    enriched_sources: list[dict[str, Any]] = []
    for source in sources:
        enriched = deepcopy(source)
        heroic_hint = next((hint for hint in hints if source_hint_matches_source(source, hint)), None)
        if heroic_hint:
            enriched["difficulty"] = "heroic"
            if not enriched.get("zone"):
                zone = heroic_zone_from_hint(heroic_hint)
                if zone:
                    enriched["zone"] = zone
        enriched_sources.append(enriched)
    return enriched_sources


def snapshot_requirements(snapshot: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not snapshot:
        return []
    requirements = snapshot.get("normalized_requirements", [])
    return normalize_requirement_reputation_names([requirement for requirement in requirements if isinstance(requirement, dict)])


def source_list_requirements(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    requirements: list[dict[str, Any]] = []
    for source in sources:
        for requirement in source.get("requirements", []):
            if isinstance(requirement, dict):
                requirements.append(requirement)
    return dedupe_requirements(requirements)


def guide_hint_requirements(hints: list[dict[str, Any]]) -> list[dict[str, Any]]:
    requirements: list[dict[str, Any]] = []
    for hint in hints:
        source_text = clean_text(str(hint.get("source_text") or ""))
        source_url = str(hint.get("source_url") or "")
        requirements.extend(
            extract_requirements_from_text(
                source_text,
                source_url,
                requirement_scope_from_source_text(source_text),
                "parsed_source_text",
            )
        )
    return dedupe_requirements(requirements)


def is_tradeable_item(item: dict[str, Any] | None, snapshot: dict[str, Any] | None = None) -> bool:
    for candidate in (snapshot, item):
        if not isinstance(candidate, dict):
            continue
        if candidate.get("boe") is True or candidate.get("binding") == "bind_on_equip":
            return True
    return False


def has_crafted_source(sources: list[dict[str, Any]] | None) -> bool:
    return any(isinstance(source, dict) and source.get("type") == "crafted" for source in sources or [])


def normalize_tradeable_crafted_profession_requirements(
    requirements: list[dict[str, Any]],
    item: dict[str, Any] | None,
    snapshot: dict[str, Any] | None,
    sources: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    if not is_tradeable_item(item, snapshot) or not has_crafted_source(sources):
        return dedupe_requirements(requirements)

    normalized: list[dict[str, Any]] = []
    for requirement in requirements:
        if (
            requirement.get("type") == "profession"
            and requirement.get("scope") == "equip_or_use"
            and requirement.get("confidence") == "parsed_source_text"
        ):
            requirement = {**requirement, "scope": "self_craft"}
        normalized.append(requirement)
    return dedupe_requirements(normalized)


def item_requirements_for_import(
    item_id: int,
    item: dict[str, Any],
    snapshot: dict[str, Any] | None,
    sources: list[dict[str, Any]],
    hints: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    requirements: list[dict[str, Any]] = []
    if not snapshot and not hints:
        requirements.extend(item.get("requirements", []))
    requirements.extend(snapshot_requirements(snapshot))
    requirements.extend(guide_hint_requirements(hints))

    is_bind_on_pickup = item.get("binding") == "bind_on_pickup" or (snapshot and snapshot.get("binding") == "bind_on_pickup")
    if is_bind_on_pickup:
        for source in sources:
            if source.get("type") != "crafted":
                continue
            profession = canonical_profession(str(source.get("profession") or ""))
            if profession:
                requirements.append(
                    make_requirement(
                        "profession",
                        "self_craft",
                        source.get("source_url") or (snapshot or {}).get("url") or item.get("wowhead_url") or item_url_for_id(item_id),
                        str(source.get("raw_source_text") or profession),
                        "wowhead_item" if source.get("confidence") == "wowhead_item" else "parsed_source_text",
                        profession=profession,
                    )
                )
    return normalize_tradeable_crafted_profession_requirements(requirements, item, snapshot, sources)


def recipe_known_requirement(spell_snapshot: dict[str, Any] | None, spell_id: int, spell_name: str | None) -> dict[str, Any]:
    source_url = (spell_snapshot or {}).get("url") or spell_url_for_id(spell_id)
    return make_requirement(
        "recipe_known",
        "cast_enchant",
        source_url,
        spell_name or f"Spell {spell_id}",
        "wowhead_spell_recipe",
        spell_id=spell_id,
        spell_name=spell_name,
    )


def enchant_requirements_for_import(
    row: dict[str, Any],
    guide_url: str,
    entity: dict[str, Any],
    spell_snapshot: dict[str, Any] | None,
    source_spell_snapshot: dict[str, Any] | None,
    formula_item_ids: list[int],
    item_snapshots: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    requirements = row_requirements(row, guide_url)
    if entity.get("type") == "spell":
        spell_id = int(entity["id"])
        requirements.append(recipe_known_requirement(source_spell_snapshot or spell_snapshot, spell_id, entity.get("name")))
        requirements.extend(snapshot_requirements(spell_snapshot))
        if source_spell_snapshot is not spell_snapshot:
            requirements.extend(snapshot_requirements(source_spell_snapshot))
        for formula_item_id in formula_item_ids:
            requirements.extend(snapshot_requirements(item_snapshots.get(formula_item_id)))
    else:
        requirements.extend(snapshot_requirements(item_snapshots.get(int(entity["id"]))))
    return dedupe_requirements(requirements)


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
    if zone and requirement_looks_like_text(zone):
        zone = None
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
    requirements = extract_requirements_from_text(
        text,
        source_url,
        requirement_scope_from_source_text(text),
        "parsed_source_text",
    )

    def with_requirements(parsed_source: dict[str, Any]) -> dict[str, Any]:
        if requirements:
            parsed_source["requirements"] = requirements
        return classify_source(parsed_source)

    if "world drop" in lowered:
        return with_requirements({
            **source,
            "type": "world_drop",
            "entity_name": "World Drop",
            "world_drop": True,
        })

    if lowered.startswith("conjured"):
        return with_requirements({
            **source,
            "type": "crafted",
            "entity_name": "Conjured",
            "profession": "Warlock",
        })

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
        return with_requirements(parsed_source)

    if lowered.startswith("zone drop:"):
        entity_name, zone = source_name_and_zone_from_text(text, r"^zone drop:")
        if zone:
            source["zone"] = zone
        return with_requirements({**source, "type": "drop", "entity_name": entity_name})

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
        return with_requirements({
            **source,
            "type": "crafted",
            "entity_name": entity_name,
            "profession": profession or entity_name,
        })

    if lowered.startswith("quest:"):
        entity_name, zone = source_name_and_zone_from_text(text, r"^quest:")
        if zone:
            source["zone"] = zone
        return with_requirements({**source, "type": "quest", "entity_name": entity_name})

    if lowered.startswith("vendor:") or "arena point" in lowered or "honor point" in lowered:
        entity_name, zone = source_name_and_zone_from_text(text, r"^vendor:")
        if zone:
            source["zone"] = zone
        return with_requirements({
            **source,
            "type": "pvp" if "arena point" in lowered or "honor point" in lowered else "vendor",
            "entity_name": entity_name,
        })

    if lowered.startswith("drop:"):
        entity_name, zone = source_name_and_zone_from_text(text, r"^drop:")
        if zone:
            source["zone"] = zone
        return with_requirements({**source, "type": "drop", "entity_name": entity_name})

    if re.search(r"\([^()]+\)\s*$", text) or " - " in text:
        entity_name, zone = source_name_and_zone_from_text(text, r"")
        if zone:
            source["zone"] = zone
        return with_requirements({**source, "type": "drop", "entity_name": entity_name})

    return with_requirements({**source, "type": "unknown", "entity_name": text or "Unknown"})


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


def reviewed_spell_alias_urls() -> dict[int, list[str]]:
    aliases: dict[int, list[str]] = {}
    for override in reviewed_overrides():
        if override.get("type") != "spell_alias":
            continue
        target = override.get("target", {})
        spell_id = target.get("spell_id")
        source_url = override.get("source_url")
        if not isinstance(spell_id, int) or not isinstance(source_url, str):
            continue
        if "/spell=" not in source_url:
            continue
        aliases.setdefault(spell_id, []).append(source_url)
    return aliases


def reviewed_quest_starter_overrides() -> list[dict[str, Any]]:
    return [
        override
        for override in reviewed_overrides()
        if override.get("type") == "quest_starter" and isinstance(override.get("data"), dict)
    ]


def reviewed_quest_starter_items() -> dict[int, dict[str, Any]]:
    starter_items: dict[int, dict[str, Any]] = {}
    for override in reviewed_quest_starter_overrides():
        for starter_item in (override.get("data") or {}).get("starter_items") or []:
            if not isinstance(starter_item, dict):
                continue
            item_id = starter_item.get("id")
            if isinstance(item_id, int) and item_id > 0:
                starter_items[item_id] = deepcopy(starter_item)
    return starter_items


def reviewed_quest_starter_item_ids() -> set[int]:
    item_ids: set[int] = set()
    for override in reviewed_quest_starter_overrides():
        data = override.get("data") or {}
        for item_id in data.get("starter_item_ids") or []:
            if isinstance(item_id, int) and item_id > 0:
                item_ids.add(item_id)
        for starter_item in data.get("starter_items") or []:
            if not isinstance(starter_item, dict):
                continue
            item_id = starter_item.get("id")
            if isinstance(item_id, int) and item_id > 0:
                item_ids.add(item_id)
    return item_ids


def reviewed_quest_starter_overrides_for_item(item_id: int) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for override in reviewed_quest_starter_overrides():
        reward_item_ids = (override.get("data") or {}).get("reward_item_ids") or []
        if item_id in reward_item_ids:
            matches.append(override)
    return matches


def quest_starter_item_data(
    starter_item_id: int,
    item_snapshots: dict[int, dict[str, Any]],
    existing_items: dict[int, dict[str, Any]],
    starter_item_overrides: dict[int, dict[str, Any]],
) -> dict[str, Any] | None:
    snapshot = item_snapshots.get(starter_item_id)
    if snapshot:
        return {
            "id": starter_item_id,
            "name": snapshot.get("name") or f"Item {starter_item_id}",
            "wowhead_url": snapshot.get("url") or item_url_for_id(starter_item_id),
            "sources": snapshot.get("normalized_sources", []),
        }

    if starter_item_id in existing_items:
        return existing_items[starter_item_id]

    if starter_item_id in starter_item_overrides:
        return starter_item_overrides[starter_item_id]

    return None


def quest_starter_sources_for_override(
    override: dict[str, Any],
    item_snapshots: dict[int, dict[str, Any]],
    existing_items: dict[int, dict[str, Any]],
    starter_item_overrides: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    data = override.get("data") or {}
    relationship = data.get("relationship") or "direct_starter"
    starter_sources: list[dict[str, Any]] = []

    for starter_item_id in data.get("starter_item_ids") or []:
        if not isinstance(starter_item_id, int) or starter_item_id <= 0:
            continue

        starter_item = quest_starter_item_data(starter_item_id, item_snapshots, existing_items, starter_item_overrides)
        if not starter_item:
            continue

        raw_sources = [source for source in starter_item.get("sources", []) if isinstance(source, dict)]
        if not raw_sources:
            continue

        primary_starter_source = derive_primary_source(classify_sources(deepcopy(raw_sources)))
        if primary_starter_source.get("type") != "drop":
            continue

        enriched = deepcopy(primary_starter_source)
        enriched["quest_starter_item_id"] = starter_item_id
        enriched["quest_starter_name"] = starter_item.get("name") or f"Item {starter_item_id}"
        enriched["quest_starter_relationship"] = relationship
        enriched["quest_starter_source_url"] = starter_item.get("wowhead_url") or item_url_for_id(starter_item_id)
        starter_sources.append(enriched)

    return classify_sources(starter_sources)


def attach_quest_starters_to_sources(
    item_id: int,
    sources: list[dict[str, Any]],
    item_snapshots: dict[int, dict[str, Any]],
    existing_items: dict[int, dict[str, Any]],
    starter_item_overrides: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    overrides = reviewed_quest_starter_overrides_for_item(item_id)
    if not overrides:
        return sources

    enriched_sources: list[dict[str, Any]] = []
    for source in sources:
        enriched = deepcopy(source)
        if enriched.get("type") == "quest":
            matching_starter_sources: list[dict[str, Any]] = []
            for override in overrides:
                quest_ids = (override.get("data") or {}).get("quest_ids") or []
                if quest_ids and enriched.get("quest_id") not in quest_ids:
                    continue
                matching_starter_sources.extend(
                    quest_starter_sources_for_override(override, item_snapshots, existing_items, starter_item_overrides)
                )
            if matching_starter_sources:
                enriched["quest_starter_sources"] = matching_starter_sources
                enriched["confidence"] = f"{enriched.get('confidence', 'wowhead_item')}+quest_starter"
        enriched_sources.append(enriched)

    return classify_sources(enriched_sources)


def target_matches(row: dict[str, Any], target: dict[str, Any]) -> bool:
    return all(row.get(key) == value for key, value in target.items())


def bis_row_matches_target(row: dict[str, Any], target: dict[str, Any]) -> bool:
    row_keys = {"class", "spec", "phase", "slot", "source_url"}
    return all(row.get(key) == value for key, value in target.items() if key in row_keys)


def bis_item_matches_target(item: dict[str, Any], target: dict[str, Any]) -> bool:
    item_keys = {"item_id", "context", "rank_group", "rank_label"}
    matched_item_key = False
    for key, value in target.items():
        if key not in item_keys:
            continue
        matched_item_key = True
        if item.get(key) != value:
            return False
    return matched_item_key


def refresh_item_derived_fields(item: dict[str, Any]) -> dict[str, Any]:
    refreshed = deepcopy(item)
    sources = classify_sources(refreshed.get("sources", []))
    refreshed["sources"] = sources
    refreshed["primary_source"] = derive_primary_source(sources)
    refreshed["source_summary"] = summarize_sources(sources)
    refreshed["acquisition_phase"] = derive_acquisition_phase(sources)
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
        imported_row = next((row for row in rows if target_matches(row, target)), None)
        replacement = copy_imported_bis_ranks(replacement, imported_row)

        replaced = False
        for index, row in enumerate(rows):
            if target_matches(row, target):
                rows[index] = replacement
                replaced = True
                break
        if not replaced:
            rows.append(replacement)

    for override in reviewed_overrides():
        if override.get("type") != "bis_exclusion":
            continue

        target = override.get("target", {})
        filtered_rows: list[dict[str, Any]] = []
        for row in rows:
            if not bis_row_matches_target(row, target):
                filtered_rows.append(row)
                continue

            filtered_items = [
                item
                for item in row.get("items", [])
                if not bis_item_matches_target(item, target)
            ]
            if filtered_items:
                filtered = deepcopy(row)
                filtered["items"] = filtered_items
                filtered_rows.append(filtered)
        rows = filtered_rows

    for row in rows:
        for item in row.get("items", []):
            item["rank_group"] = normalize_rank_group_value(item.get("rank_group"), item.get("rank_label"))

    return {"coverage": imported_bis_lists.get("coverage", "scraped_snapshot"), "lists": rows}


def import_items_from_snapshots(snapshots: list[dict[str, Any]]) -> dict[str, Any]:
    existing_items = {item["id"]: item for item in canonical_json("items").get("items", []) if item.get("sources")}
    item_snapshots = {snapshot.get("item_id"): snapshot for snapshot in snapshots if snapshot.get("page_type") == "item"}
    item_refs = guide_item_refs(snapshots)
    item_source_hints = guide_item_source_hints(snapshots)
    starter_item_overrides = reviewed_quest_starter_items()
    base_item_ids = set(existing_items) | set(item_refs)
    starter_item_ids: set[int] = set()
    for override in reviewed_quest_starter_overrides():
        data = override.get("data") or {}
        if not any(item_id in base_item_ids for item_id in data.get("reward_item_ids") or []):
            continue
        for item_id in data.get("starter_item_ids") or []:
            if item_id in existing_items or item_id in item_snapshots or item_id in starter_item_overrides:
                starter_item_ids.add(item_id)
    item_ids = sorted(base_item_ids | starter_item_ids)

    items: list[dict[str, Any]] = []
    for item_id in item_ids:
        current = existing_items.get(item_id, {}) or starter_item_overrides.get(item_id, {})
        ref = item_refs.get(item_id, {})
        snapshot = item_snapshots.get(item_id)
        source_hints = item_source_hints.get(item_id, [])
        raw_sources = snapshot.get("normalized_sources") if snapshot else current.get("sources", [])
        if not raw_sources:
            raw_sources = guide_fallback_sources(source_hints)
        raw_sources = apply_source_hints_to_sources(raw_sources, source_hints)
        if snapshot:
            raw_sources = add_recipe_sources_to_crafted_sources(
                deepcopy(raw_sources),
                recipe_sources_from_taught_by_items(
                    (snapshot.get("related_tables") or {}).get("taught-by-item", []),
                    str(snapshot.get("url") or item_url_for_id(item_id)),
                ),
            )
        sources = attach_token_turnins_to_sources(raw_sources, item_snapshots)
        sources = attach_quest_starters_to_sources(
            item_id,
            sources,
            item_snapshots,
            existing_items,
            starter_item_overrides,
        )
        item = {
            "id": item_id,
            "name": snapshot.get("name") if snapshot and snapshot.get("name") else current.get("name") or ref.get("name") or f"Item {item_id}",
            "quality": snapshot.get("quality") if snapshot and snapshot.get("quality") != "unknown" else current.get("quality", "unknown"),
            "inventory_slot": item_inventory_slot(snapshot) or current.get("inventory_slot"),
            "binding": snapshot.get("binding") if snapshot and snapshot.get("binding") != "unknown" else current.get("binding", "unknown"),
            "boe": snapshot.get("boe") if snapshot and snapshot.get("boe") is not None else current.get("boe"),
            "wowhead_url": current.get("wowhead_url") or ref.get("wowhead_url") or item_url_for_id(item_id),
            "sources": sources,
            "primary_source": derive_primary_source(sources),
            "source_summary": summarize_sources(sources),
            "acquisition_phase": derive_acquisition_phase(sources),
        }
        if current.get("requirements"):
            item["requirements"] = deepcopy(current["requirements"])
        requirements = item_requirements_for_import(item_id, item, snapshot, sources, source_hints)
        if requirements:
            item["requirements"] = requirements
        else:
            item.pop("requirements", None)
        items.append(item)

    return apply_item_overrides({"items": items})


def item_stats_from_snapshot(snapshot: dict[str, Any]) -> dict[str, Any] | None:
    if snapshot.get("page_type") != "item":
        return None
    item_id = snapshot.get("item_id")
    if not isinstance(item_id, int) or item_id <= 0:
        return None
    stats = snapshot.get("item_stats")
    if isinstance(stats, dict) and stats.get("id"):
        return deepcopy(stats)

    sources = snapshot.get("normalized_sources") or []
    row = {
        "id": item_id,
        "name": snapshot.get("name") or f"Item {item_id}",
        "required_level": None,
        "item_level": None,
        "quality": snapshot.get("quality", "unknown"),
        "binding": snapshot.get("binding", "unknown"),
        "boe": snapshot.get("boe"),
        "slot": item_inventory_slot(snapshot),
        "stats": {},
        "sockets": [],
        "socket_bonus": {},
        "restrictions": {},
        "source_summary": summarize_sources(sources) if sources else "",
        "primary_source": derive_primary_source(sources) if sources else None,
        "sources": sources,
        "phase": derive_acquisition_phase(sources) if sources else "PR",
        "wowhead_url": snapshot.get("url") or item_url_for_id(item_id),
        "parse_confidence": "legacy_snapshot",
    }
    description = str(snapshot.get("description") or "")
    item_level_match = re.search(r"\bitem level of (\d+)\b", description, flags=re.IGNORECASE)
    if item_level_match:
        row["item_level"] = int(item_level_match.group(1))
    required_level_match = re.search(r"\brequires level (\d{1,2})\b", description, flags=re.IGNORECASE)
    if required_level_match:
        row["required_level"] = int(required_level_match.group(1))
    return {key: value for key, value in row.items() if value not in (None, [], {})}


def import_item_stats_from_snapshots(snapshots: list[dict[str, Any]]) -> dict[str, Any]:
    rows: dict[int, dict[str, Any]] = {}
    list_metadata = item_list_metadata_by_id(snapshots, authoritative_only=True)
    restrict_to_list = bool(list_metadata)
    allowed_item_ids = set(list_metadata)
    if restrict_to_list:
        allowed_item_ids.update(item_corpus_manifest_item_ids())
    for snapshot in snapshots:
        row = item_stats_from_snapshot(snapshot)
        if not row:
            continue
        item_id = int(row["id"])
        if restrict_to_list and item_id not in allowed_item_ids:
            continue
        row = apply_item_list_metadata(row, list_metadata.get(int(row["id"])))
        rows[item_id] = row
    return {"item_stats": [rows[item_id] for item_id in sorted(rows)]}


def import_item_variants_from_snapshots(snapshots: list[dict[str, Any]]) -> dict[str, Any]:
    variants: dict[tuple[int, int], dict[str, Any]] = {}
    for snapshot in snapshots:
        for variant in snapshot.get("item_variants", []) or []:
            item_id = variant.get("item_id")
            suffix_id = variant.get("random_suffix_id")
            if not isinstance(item_id, int) or not isinstance(suffix_id, int):
                continue
            variants[(item_id, suffix_id)] = deepcopy(variant)
    return {"item_variants": [variants[key] for key in sorted(variants)]}


def item_corpus_report(item_stats_doc: dict[str, Any]) -> dict[str, Any]:
    by_level_band = {"no_required_level": 0, "1-19": 0, "20-39": 0, "40-57": 0, "58-70": 0, "above_70": 0}
    by_slot: dict[str, int] = {}
    by_quality: dict[str, int] = {}
    by_source_type: dict[str, int] = {}
    parse_confidence: dict[str, int] = {}
    complete = 0

    for item in item_stats_doc.get("item_stats", []):
        required_level = item.get("required_level")
        if required_level is None:
            by_level_band["no_required_level"] += 1
        elif isinstance(required_level, int) and required_level <= 19:
            by_level_band["1-19"] += 1
        elif isinstance(required_level, int) and required_level <= 39:
            by_level_band["20-39"] += 1
        elif isinstance(required_level, int) and required_level <= 57:
            by_level_band["40-57"] += 1
        elif isinstance(required_level, int) and required_level <= 70:
            by_level_band["58-70"] += 1
        else:
            by_level_band["above_70"] += 1

        by_slot[str(item.get("slot") or "unknown")] = by_slot.get(str(item.get("slot") or "unknown"), 0) + 1
        by_quality[str(item.get("quality") or "unknown")] = by_quality.get(str(item.get("quality") or "unknown"), 0) + 1
        source_type = str((item.get("primary_source") or {}).get("type") or "unknown") if isinstance(item.get("primary_source"), dict) else "unknown"
        by_source_type[source_type] = by_source_type.get(source_type, 0) + 1
        confidence = str(item.get("parse_confidence") or "unknown")
        parse_confidence[confidence] = parse_confidence.get(confidence, 0) + 1
        if item.get("slot") and (item.get("stats") or item.get("dps") or item.get("armor") or item.get("sockets")):
            complete += 1

    return {
        "items": len(item_stats_doc.get("item_stats", [])),
        "complete": complete,
        "by_level_band": by_level_band,
        "by_slot": dict(sorted(by_slot.items())),
        "by_quality": dict(sorted(by_quality.items())),
        "by_source_type": dict(sorted(by_source_type.items())),
        "parse_confidence": dict(sorted(parse_confidence.items())),
    }


def build_item_corpus_audit(input_dir: Path) -> dict[str, Any]:
    snapshots = load_snapshots(input_dir)
    item_stats_doc = import_item_stats_from_snapshots(snapshots)
    errors: list[str] = []
    warnings: list[str] = []
    authoritative_list_snapshots = [snapshot for snapshot in snapshots if item_corpus_snapshot_is_authoritative(snapshot)]
    authoritative_urls = item_corpus_authoritative_urls()
    fetched_authoritative_urls = {str(snapshot.get("url") or "") for snapshot in authoritative_list_snapshots}
    for url in sorted(authoritative_urls - fetched_authoritative_urls):
        errors.append(f"Missing authoritative item list snapshot: {url}")
    if not authoritative_list_snapshots:
        errors.append("No authoritative item list snapshots found for item corpus")
    for snapshot in authoritative_list_snapshots:
        summary = snapshot.get("summary") if isinstance(snapshot.get("summary"), dict) else {}
        if len(snapshot.get("item_refs", [])) == 1000 or summary.get("truncated"):
            total = summary.get("total_items")
            displayed = summary.get("displayed_items") or len(snapshot.get("item_refs", []))
            suffix = f" ({displayed} displayed of {total} total)" if total else ""
            errors.append(f"Truncated item list snapshot for corpus source: {snapshot.get('url')}{suffix}")
    item_list_ids = {
        int(ref["id"])
        for snapshot in authoritative_list_snapshots
        for ref in snapshot.get("item_refs", [])
        if isinstance(ref.get("id"), int) and item_corpus_ref_is_in_scope(ref)
    }
    seed_item_ids = item_corpus_manifest_item_ids()
    expected_item_ids = item_list_ids | seed_item_ids
    item_snapshot_ids = {
        int(snapshot["item_id"])
        for snapshot in snapshots
        if snapshot.get("page_type") == "item" and isinstance(snapshot.get("item_id"), int)
    }

    for item_id in sorted(expected_item_ids - item_snapshot_ids):
        errors.append(f"Missing item page snapshot for corpus item {item_id}: {item_url_for_id(item_id)}")
    for item in item_stats_doc.get("item_stats", []):
        label = f"{item.get('id')} {item.get('name')}"
        if not item.get("slot"):
            errors.append(f"Unsupported or missing slot for item corpus row: {label}")
        required_level = item.get("required_level")
        if required_level is not None and (not isinstance(required_level, int) or required_level < 1 or required_level > 70):
            errors.append(f"Invalid required level for item corpus row: {label}")
        if not item.get("source_summary"):
            warnings.append(f"Missing source summary for item corpus row: {label}")
        if not (item.get("stats") or item.get("dps") or item.get("armor") or item.get("sockets")):
            warnings.append(f"Missing tooltip stats for item corpus row: {label}")

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "summary": item_corpus_report(item_stats_doc),
    }


def build_suffix_audit(input_dir: Path) -> dict[str, Any]:
    variants = import_item_variants_from_snapshots(load_snapshots(input_dir)).get("item_variants", [])
    errors: list[str] = []
    seen: set[tuple[int, int]] = set()
    for variant in variants:
        item_id = variant.get("item_id")
        suffix_id = variant.get("random_suffix_id")
        key = (int(item_id) if isinstance(item_id, int) else 0, int(suffix_id) if isinstance(suffix_id, int) else 0)
        if key in seen:
            errors.append(f"Duplicate suffix variant: {key}")
        seen.add(key)
        if not variant.get("suffix_name"):
            errors.append(f"Missing suffix name for variant: {key}")
        if not variant.get("stats") and not variant.get("stat_delta"):
            errors.append(f"Missing suffix stats for variant: {key}")
        if not str(variant.get("source_url", "")).startswith("https://www.wowhead.com/tbc/"):
            errors.append(f"Missing suffix evidence URL for variant: {key}")
    return {
        "ok": not errors,
        "errors": errors,
        "warnings": [],
        "summary": {"variants": len(variants)},
    }


def build_recommendation_audit() -> dict[str, Any]:
    recommendations = canonical_json("leveling_recommendations").get("leveling_recommendations", [])
    item_stats_ids = {item.get("id") for item in canonical_json("item_stats").get("item_stats", [])}
    guide_rows = canonical_json("leveling_gear").get("leveling_gear", [])
    guide_keys = {
        (row.get("class"), row.get("spec"), row.get("slot"), row.get("item_id"))
        for row in guide_rows
    }
    errors: list[str] = []
    warnings: list[str] = []
    warning_seen: set[str] = set()

    def add_warning(message: str) -> None:
        if message in warning_seen:
            return
        warning_seen.add(message)
        warnings.append(message)

    for row in recommendations:
        item_id = row.get("item_id")
        label = f"{row.get('class')}/{row.get('spec')}/{row.get('race')}/{row.get('slot')} {item_id}"
        if item_id not in item_stats_ids:
            errors.append(f"Recommendation references item without stat corpus row: {label}")
        if not str(row.get("source_url", "")).startswith("https://www.wowhead.com/tbc/"):
            errors.append(f"Recommendation lacks source evidence: {label}")
        guide_key = (row.get("class"), row.get("spec"), row.get("slot"), item_id)
        if guide_key not in guide_keys and (row.get("rank") == 1 or float(row.get("score_delta_pct") or 999) <= 5):
            add_warning(f"Strong computed candidate absent from guide rows: {label}")
        if any(tag for tag in row.get("reason_tags", []) if "racial" in str(tag) or str(tag).startswith(("human_", "orc_", "draenei_", "dwarf_", "troll_"))):
            add_warning(f"Race-specific recommendation disagreement candidate: {label}")

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "recommendations": len(recommendations),
            "guide_rows": len(guide_rows),
            "warnings": len(warnings),
        },
    }


def command_item_corpus_report(args: argparse.Namespace) -> int:
    item_stats_doc = import_item_stats_from_snapshots(load_snapshots(args.input_dir))
    print(json.dumps(item_corpus_report(item_stats_doc), indent=2, sort_keys=True))
    return 0


def command_item_corpus_audit(args: argparse.Namespace) -> int:
    audit = build_item_corpus_audit(args.input_dir)
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["ok"] else 1


def command_suffix_audit(args: argparse.Namespace) -> int:
    audit = build_suffix_audit(args.input_dir)
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["ok"] else 1


def command_recommendation_audit(args: argparse.Namespace) -> int:
    audit = build_recommendation_audit()
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["ok"] else 1


IMPORT_OUTPUT_FILES = {
    "items.json": "items",
    "bis_lists.json": "bis_lists",
    "gems.json": "gems",
    "gem_sources.json": "gem_sources",
    "enchants.json": "enchants",
    "enchant_sources.json": "enchant_sources",
    "consumables.json": "consumables",
    "leveling.json": "leveling",
    "leveling_gear.json": "leveling_gear",
    "item_stats.json": "item_stats",
    "item_variants.json": "item_variants",
    "leveling_recommendations.json": "leveling_recommendations",
    "recommendation_audit.json": "recommendation_audit",
}

IMPORT_FILES_BY_FAMILY = {
    "bis_lists": ["items.json", "bis_lists.json"],
    "gems": ["items.json", "gems.json", "gem_sources.json"],
    "enchants": ["items.json", "enchants.json", "enchant_sources.json"],
    "consumables": ["items.json", "consumables.json"],
    "leveling": ["items.json", "leveling.json", "leveling_gear.json"],
    "item_corpus": ["item_stats.json", "item_variants.json", "leveling_recommendations.json", "recommendation_audit.json"],
}


def import_dry_run_counts(output_docs: dict[str, dict[str, Any]], family: str | None) -> dict[str, Any]:
    file_names = IMPORT_FILES_BY_FAMILY.get(family, list(output_docs))
    default_docs = {
        "item_stats": {"item_stats": []},
        "item_variants": {"item_variants": []},
        "leveling_recommendations": {"leveling_recommendations": []},
        "recommendation_audit": {"recommendation_audit": {"rows": [], "summary": {}}},
    }
    counted_docs = {}
    for file_name, canonical_name in IMPORT_OUTPUT_FILES.items():
        counted_docs[file_name] = output_docs[file_name] if file_name in file_names else canonical_doc_or_default(canonical_name, default_docs.get(canonical_name, {}))

    bis_lists_doc = counted_docs["bis_lists.json"]
    counts = {
        "bis_lists": len(bis_lists_doc["lists"]),
        "coverage": bis_lists_doc["coverage"],
        "consumables": len(counted_docs["consumables.json"]["consumables"]),
        "enchant_sources": len(counted_docs["enchant_sources.json"]["enchant_sources"]),
        "enchants": len(counted_docs["enchants.json"]["enchants"]),
        "gem_sources": len(counted_docs["gem_sources.json"]["gem_sources"]),
        "gems": len(counted_docs["gems.json"]["gems"]),
        "items": len(counted_docs["items.json"]["items"]),
        "leveling": len(counted_docs["leveling.json"]["leveling"]),
        "leveling_gear": len(counted_docs["leveling_gear.json"]["leveling_gear"]),
        "item_stats": len(counted_docs["item_stats.json"]["item_stats"]),
        "item_variants": len(counted_docs["item_variants.json"]["item_variants"]),
        "leveling_recommendations": len(counted_docs["leveling_recommendations.json"]["leveling_recommendations"]),
    }
    if family:
        counts["family"] = family
    return counts


def canonical_doc_or_default(name: str, default: dict[str, Any]) -> dict[str, Any]:
    try:
        return canonical_json(name)
    except (KeyError, FileNotFoundError):
        return deepcopy(default)


def command_import(args: argparse.Namespace) -> int:
    if args.family == "item_corpus" and args.input_dir == RAW_WOWHEAD_DIR:
        args.input_dir = RAW_WOWHEAD_DIR / "full_item_corpus"
    snapshots = load_snapshots(args.input_dir)
    imported_items = import_items_from_snapshots(snapshots)
    imported_bis_lists = apply_bis_overrides(import_bis_lists_from_snapshots(snapshots))
    imported_gems = import_gems_from_snapshots(snapshots)
    imported_gem_sources = import_entity_sources_from_snapshots(snapshots, imported_gems["gems"], "gem_sources")
    imported_enchants = import_enchants_from_snapshots(snapshots)
    imported_enchant_sources = import_entity_sources_from_snapshots(snapshots, imported_enchants["enchants"], "enchant_sources")
    imported_consumables = import_consumables_from_snapshots(snapshots)
    imported_leveling = import_leveling_from_snapshots(snapshots)
    imported_leveling_gear = import_leveling_gear_from_snapshots(snapshots)
    imported_item_stats = import_item_stats_from_snapshots(snapshots)
    imported_item_variants = import_item_variants_from_snapshots(snapshots)
    if args.family in {None, "item_corpus"}:
        imported_recommendations = build_recommendation_documents(
            imported_item_stats,
            imported_item_variants,
            canonical_json("racial_modifiers"),
            canonical_json("scoring_profiles"),
        )
        imported_leveling_recommendations = {"leveling_recommendations": imported_recommendations["leveling_recommendations"]}
        imported_recommendation_audit = {"recommendation_audit": imported_recommendations["recommendation_audit"]}
    else:
        imported_leveling_recommendations = canonical_doc_or_default("leveling_recommendations", {"leveling_recommendations": []})
        imported_recommendation_audit = canonical_doc_or_default("recommendation_audit", {"recommendation_audit": {"rows": [], "summary": {}}})

    output_docs = {
        "items.json": imported_items,
        "bis_lists.json": imported_bis_lists,
        "gems.json": imported_gems,
        "gem_sources.json": imported_gem_sources,
        "enchants.json": imported_enchants,
        "enchant_sources.json": imported_enchant_sources,
        "consumables.json": imported_consumables,
        "leveling.json": imported_leveling,
        "leveling_gear.json": imported_leveling_gear,
        "item_stats.json": imported_item_stats,
        "item_variants.json": imported_item_variants,
        "leveling_recommendations.json": imported_leveling_recommendations,
        "recommendation_audit.json": imported_recommendation_audit,
    }

    if args.dry_run:
        counts = import_dry_run_counts(output_docs, args.family)
        print(json.dumps(counts, indent=2, sort_keys=True))
        return 0

    file_names = IMPORT_FILES_BY_FAMILY.get(args.family, list(output_docs))
    for file_name in file_names:
        write_text(CANONICAL_DIR / file_name, json.dumps(output_docs[file_name], indent=2, sort_keys=True) + "\n")
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
        if data_family in source_families:
            urls.update(manifest_source_urls(source))
    return urls


def raw_bis_rows_from_snapshots(snapshots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    item_snapshots = item_snapshots_by_id(snapshots)
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
                for row in table.get("rows", []):
                    item_id = row.get("item_id")
                    phase = phase_from_row(source_meta, table, row)
                    if not item_id or not phase:
                        continue
                    slot = bis_slot_from_row(table, row, item_snapshots.get(int(item_id)))
                    if not slot:
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


BIS_RELEVANT_HEADING_RE = re.compile(
    r"\b(best in slot|bis|weapons?|one[- ]?hand(?:ed)?|two[- ]?hand(?:ed)?|off ?hands?|offhands?|shields?|quivers?|ammo pouches?|ammunition|arrows?|bullets?)\b",
    flags=re.IGNORECASE,
)


def bis_snapshot_semantic_errors(snapshots: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    item_snapshots = item_snapshots_by_id(snapshots)
    for snapshot in snapshots:
        if snapshot.get("page_type") != "guide":
            continue
        if not manifest_sources_for_snapshot(snapshot, "bis_lists"):
            continue
        for table in snapshot.get("tables", []):
            heading = str(table.get("heading") or "")
            table_slot = table.get("slot")
            table_family = table.get("data_family")
            if table_family in {"unknown", None} and BIS_RELEVANT_HEADING_RE.search(heading):
                errors.append(f"BiS-relevant table was not classified: {snapshot.get('url')} / {heading}")
                continue
            if table_family not in {"bis_lists", "unknown", None}:
                continue
            for row in table.get("rows", []):
                item_id = row.get("item_id")
                if not isinstance(item_id, int):
                    continue
                item_snapshot = item_snapshots.get(item_id)
                inv_slot = item_inventory_slot(item_snapshot)
                derived_slot = bis_slot_from_row(table, row, item_snapshot)
                row_label = f"{snapshot.get('url')} / {heading} / {row.get('item_name') or item_id}"
                if table_slot in SLOT_NAMES and inv_slot and not derived_slot and not bis_slot_compatible(str(table_slot), inv_slot):
                    errors.append(f"BiS row slot mismatch: {row_label} imported as {table_slot}, item slot is {inv_slot}")
                elif table_slot in {"Weapon", "Ammo", "Quiver"} and not derived_slot:
                    errors.append(f"BiS row slot could not be derived: {row_label} from table slot {table_slot}, item slot is {inv_slot or 'unknown'}")
    return errors


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


def import_rows_for_family(snapshots: list[dict[str, Any]], data_family: str) -> list[dict[str, Any]]:
    if data_family == "gems":
        return import_gems_from_snapshots(snapshots, fallback_to_canonical=False)["gems"]
    if data_family == "enchants":
        return import_enchants_from_snapshots(snapshots, fallback_to_canonical=False)["enchants"]
    if data_family == "consumables":
        return import_consumables_from_snapshots(snapshots, fallback_to_canonical=False)["consumables"]
    if data_family == "leveling":
        return import_leveling_from_snapshots(snapshots, fallback_to_canonical=False)["leveling"]
    return []


def guide_entries_for_family(snapshots: list[dict[str, Any]], data_family: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for snapshot in snapshots:
        if snapshot.get("page_type") != "guide":
            continue
        for source_meta in manifest_sources_for_snapshot(snapshot, data_family):
            for table in snapshot.get("tables", []):
                if not table_matches_family(source_meta, table, data_family):
                    continue
                for row in table.get("rows", []):
                    entries.append(
                        {
                            "source_meta": source_meta,
                            "snapshot": snapshot,
                            "table": table,
                            "row": row,
                            "entities": row.get("entities", []),
                            "source_url": snapshot.get("url"),
                        }
                    )
            if data_family in {"consumables", "leveling"}:
                for section in snapshot.get("sections", []):
                    if section.get("data_family") != data_family:
                        continue
                    for entry in section.get("entries", []):
                        entries.append(
                            {
                                "source_meta": source_meta,
                                "snapshot": snapshot,
                                "section": section,
                                "row": entry,
                                "entities": entry.get("entities", []),
                                "source_url": snapshot.get("url"),
                            }
                        )
    return entries


def referenced_entity_ids(entries: list[dict[str, Any]]) -> tuple[set[int], set[int]]:
    item_ids: set[int] = set()
    spell_ids: set[int] = set()
    for entry in entries:
        for entity in entry.get("entities", []):
            entity_id = entity.get("id")
            if not isinstance(entity_id, int) or entity_id <= 0:
                continue
            if entity.get("type") == "item":
                item_ids.add(entity_id)
            elif entity.get("type") == "spell":
                spell_ids.add(entity_id)
    return item_ids, spell_ids


def imported_entity_ids(rows: list[dict[str, Any]]) -> tuple[set[int], set[int], set[int]]:
    item_ids: set[int] = set()
    spell_ids: set[int] = set()
    formula_item_ids: set[int] = set()
    for row in rows:
        row_id = row.get("id")
        if row.get("type", "item") == "spell" and isinstance(row_id, int):
            spell_ids.add(row_id)
        elif isinstance(row_id, int):
            item_ids.add(row_id)
        item_ids.update(item_id for item_id in row.get("items", []) if isinstance(item_id, int))
        formula_item_ids.update(item_id for item_id in row.get("formula_item_ids", []) if isinstance(item_id, int))
        for entity in row.get("entities", []):
            entity_id = entity.get("id")
            if not isinstance(entity_id, int):
                continue
            if entity.get("type") == "item":
                item_ids.add(entity_id)
            elif entity.get("type") == "spell":
                spell_ids.add(entity_id)
    return item_ids, spell_ids, formula_item_ids


def resolve_entity_names(entities: list[dict[str, Any]], item_snapshots: dict[int, dict[str, Any]], spell_snapshots: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    resolved: list[dict[str, Any]] = []
    for entity in entities:
        if not isinstance(entity, dict):
            continue
        copy = deepcopy(entity)
        if not copy.get("name"):
            entity_id = copy.get("id")
            if copy.get("type") == "item" and isinstance(entity_id, int):
                copy["name"] = item_snapshots.get(entity_id, {}).get("name", "")
            elif copy.get("type") == "spell" and isinstance(entity_id, int):
                copy["name"] = spell_snapshots.get(entity_id, {}).get("name", "")
        resolved.append(copy)
    return resolved


def row_with_resolved_entities(row: dict[str, Any], item_snapshots: dict[int, dict[str, Any]], spell_snapshots: dict[int, dict[str, Any]]) -> dict[str, Any]:
    resolved = deepcopy(row)
    resolved["entities"] = resolve_entity_names(row.get("entities", []), item_snapshots, spell_snapshots)
    if isinstance(row.get("cell_entities"), list):
        resolved["cell_entities"] = [
            resolve_entity_names(cell_entities, item_snapshots, spell_snapshots)
            for cell_entities in row.get("cell_entities", [])
        ]
    return resolved


def non_gear_row_errors(row: dict[str, Any], data_family: str) -> list[str]:
    errors: list[str] = []
    row_label = f"{data_family} row from {row.get('source_url') or '<unknown source>'}"
    if not row.get("class") or not row.get("spec"):
        errors.append(f"{row_label} is missing class/spec context")
    if not str(row.get("source_url", "")).startswith("https://www.wowhead.com/tbc/"):
        errors.append(f"{row_label} is missing a Wowhead source URL")

    if data_family == "gems":
        if not isinstance(row.get("id"), int) or row.get("id") <= 0:
            errors.append(f"{row_label} has invalid item id")
        if not row.get("name"):
            errors.append(f"Gem {row.get('id')} is missing a name")
        if row.get("phase") not in PHASE_KEYS:
            errors.append(f"Gem {row.get('id')} has invalid phase: {row.get('phase')}")
        if row.get("socket_category") in {None, "", "unknown"}:
            errors.append(f"Gem {row.get('id')} is missing socket color/category")
        if not isinstance(row.get("meta"), bool):
            errors.append(f"Gem {row.get('id')} meta flag must be boolean")

    if data_family == "enchants":
        if row.get("slot") not in SLOT_NAMES:
            errors.append(f"Enchant {row.get('id')} has invalid target slot: {row.get('slot')}")
        if not isinstance(row.get("id"), int) or row.get("id") <= 0:
            errors.append(f"{row_label} has invalid enchant id")
        if not row.get("name"):
            errors.append(f"Enchant {row.get('id')} is missing a name")
        if row.get("type") not in {"item", "spell"}:
            errors.append(f"Enchant {row.get('id')} has invalid type: {row.get('type')}")
        if row.get("phase") not in PHASE_KEYS:
            errors.append(f"Enchant {row.get('id')} has invalid phase: {row.get('phase')}")

    if data_family == "consumables":
        if not row.get("category"):
            errors.append(f"{row_label} is missing a normalized category")
        if len(str(row.get("category_label") or row.get("category") or "")) > 120:
            errors.append(f"{row_label} has a prose-sized consumable category label")
        if not isinstance(row.get("items"), list) or not row.get("items"):
            errors.append(f"{row_label} has no item ids")
        for item_id in row.get("items", []):
            if not isinstance(item_id, int) or item_id <= 0:
                errors.append(f"{row_label} has invalid item id: {item_id}")

    if data_family == "leveling":
        if not row.get("section"):
            errors.append(f"{row_label} is missing section title")
        if not row.get("text"):
            errors.append(f"{row_label} has empty narrative/table text")
        text = str(row.get("text") or "")
        if "|" in text:
            errors.append(f"{row_label} contains table pipe artifacts")
        if re.search(r"\s\.($|\s)", text):
            errors.append(f"{row_label} contains broken empty-link punctuation")
        for entity in row.get("entities", []):
            if isinstance(entity, dict) and not entity.get("name"):
                errors.append(f"{row_label} has linked entity {entity.get('type')}={entity.get('id')} without a name")

    return errors


def duplicate_key_for_family(row: dict[str, Any], data_family: str) -> tuple[Any, ...]:
    if data_family == "gems":
        return (row.get("class"), row.get("spec"), row.get("phase"), row.get("id"), row.get("socket_category"), row.get("context"))
    if data_family == "enchants":
        return (row.get("class"), row.get("spec"), row.get("phase"), row.get("slot"), row.get("type"), row.get("id"), row.get("context"))
    if data_family == "consumables":
        return (row.get("class"), row.get("spec"), row.get("phase"), row.get("category"), tuple(row.get("items", [])))
    if data_family == "leveling":
        return (row.get("class"), row.get("spec"), row.get("phase"), row.get("section"), row.get("level_range"), row.get("text"))
    return tuple(sorted(row.items()))


def duplicate_row_errors(rows: list[dict[str, Any]], data_family: str) -> list[str]:
    errors: list[str] = []
    seen: dict[tuple[Any, ...], str] = {}
    for row in rows:
        key = duplicate_key_for_family(row, data_family)
        source_url = str(row.get("source_url") or "")
        if key in seen:
            errors.append(f"Duplicate {data_family} row without distinct context: {key}")
        else:
            seen[key] = source_url
    return errors


KNOWN_RANK_GROUPS = {"bis", "ranked", "situational", "pvp", "unrealistic", "option"}


def has_tradeable_crafted_profession_gate(requirements: list[dict[str, Any]] | None) -> bool:
    return any(
        isinstance(requirement, dict)
        and requirement.get("type") == "profession"
        and requirement.get("scope") == "equip_or_use"
        and requirement.get("confidence") == "parsed_source_text"
        for requirement in requirements or []
    )


def canonical_semantic_errors() -> list[str]:
    errors: list[str] = []
    items_by_id = {item.get("id"): item for item in canonical_json("items").get("items", [])}
    for item_id, item in items_by_id.items():
        if (
            is_tradeable_item(item)
            and has_crafted_source(item.get("sources", []))
            and has_tradeable_crafted_profession_gate(item.get("requirements"))
        ):
            errors.append(f"BoE crafted item {item_id} has guide-derived equip profession gate")

    for row in canonical_json("bis_lists").get("lists", []):
        slot = row.get("slot")
        if slot not in SLOT_NAMES:
            errors.append(f"BiS list has invalid slot: {row.get('class')}/{row.get('spec')}/{row.get('phase')}/{slot}")
        for item in row.get("items", []):
            item_id = item.get("item_id")
            rank_group = normalize_rank_group_value(item.get("rank_group"), item.get("rank_label"))
            if rank_group not in KNOWN_RANK_GROUPS:
                errors.append(f"BiS item {item_id} has unsupported rank group: {item.get('rank_group')}")
            if str(item.get("rank_label") or "").strip().lower() == "best" and rank_group == "option":
                errors.append(f"BiS item {item_id} label Best was normalized as option")
            item_data = items_by_id.get(item_id, {})
            inventory_slot = item_data.get("inventory_slot")
            if inventory_slot and slot and not bis_slot_compatible(str(slot), str(inventory_slot)):
                errors.append(f"BiS item {item_id} slot mismatch: list slot {slot}, item slot {inventory_slot}")
            if (
                is_tradeable_item(item_data)
                and has_crafted_source(item_data.get("sources", []))
                and has_tradeable_crafted_profession_gate(item.get("requirements"))
            ):
                errors.append(f"BiS item {item_id} has guide-derived equip profession gate in {row.get('class')}/{row.get('spec')}/{row.get('phase')}/{slot}")

    for row in canonical_json("consumables").get("consumables", []):
        if len(str(row.get("category_label") or row.get("category") or "")) > 120:
            errors.append(f"Consumable row has prose-sized category label: {row.get('class')}/{row.get('spec')}/{row.get('phase')}")

    for row in canonical_json("leveling").get("leveling", []):
        text = str(row.get("text") or "")
        row_label = f"{row.get('class')}/{row.get('spec')}/{row.get('section')}"
        if "|" in text:
            errors.append(f"Leveling row contains table pipe artifacts: {row_label}")
        if re.search(r"\s\.($|\s)", text):
            errors.append(f"Leveling row contains broken empty-link punctuation: {row_label}")
        for entity in row.get("entities", []):
            if isinstance(entity, dict) and not entity.get("name"):
                errors.append(f"Leveling row has unnamed entity {entity.get('type')}={entity.get('id')}: {row_label}")
    return errors


def item_acquisition_errors(
    label: str,
    item_id: int,
    snapshot: dict[str, Any] | None,
    reviewed_unknown_item_ids: set[int],
    item_snapshots: dict[int, dict[str, Any]] | None = None,
) -> list[str]:
    if not snapshot:
        return []
    sources = snapshot.get("normalized_sources", [])
    if not sources:
        return [f"{label} item {item_id} has no structured acquisition source"]
    errors: list[str] = []
    for source in sources:
        source_type = source.get("type")
        if source_type == "unknown" and item_id not in reviewed_unknown_item_ids:
            errors.append(f"{label} item {item_id} has unreviewed unknown acquisition source")
        if source_type == "vendor" and source_has_item_cost(source):
            missing_cost_ids = [
                cost["item_id"]
                for cost in source.get("costs", [])
                if isinstance(cost.get("item_id"), int) and (not item_snapshots or cost["item_id"] not in item_snapshots)
            ]
            if missing_cost_ids:
                errors.append(f"{label} item {item_id} has unresolved item-cost vendor source")
    return errors


def enchant_spell_source_errors(
    spell_id: int,
    spell_snapshot: dict[str, Any] | None,
    spell_snapshots_by_name: dict[str, list[dict[str, Any]]],
    item_snapshots: dict[int, dict[str, Any]],
    reviewed_unknown_item_ids: set[int],
) -> list[str]:
    if not spell_snapshot:
        return []
    source_spell_snapshot = resolve_enchant_source_spell_snapshot(
        spell_id,
        spell_snapshot,
        spell_snapshots_by_name,
        item_snapshots,
    )
    source_spell_id = (source_spell_snapshot or {}).get("spell_id")
    formula_spell_ids = [spell_id]
    if isinstance(source_spell_id, int) and source_spell_id not in formula_spell_ids:
        formula_spell_ids.append(source_spell_id)
    sources = (source_spell_snapshot or {}).get("normalized_sources", [])
    formula_item_ids = {
        item_id
        for formula_spell_id in formula_spell_ids
        for item_id in formula_item_ids_for_spell(formula_spell_id, item_snapshots)
    }
    formula_item_ids.update(enchant_formula_item_ids(source_spell_snapshot))
    if not sources and not formula_item_ids:
        return [f"Enchant spell {spell_id} has no formula, trainer, vendor, or quest source"]
    errors: list[str] = []
    for formula_item_id in sorted(formula_item_ids):
        formula_snapshot = item_snapshots.get(formula_item_id)
        if not formula_snapshot:
            errors.append(f"Enchant spell {spell_id} is missing formula item snapshot {formula_item_id}: {item_url_for_id(formula_item_id)}")
            continue
        errors.extend(item_acquisition_errors(f"Enchant formula for spell {spell_id}", formula_item_id, formula_snapshot, reviewed_unknown_item_ids, item_snapshots))
    for source in sources:
        source_type = source.get("type")
        if source_type == "unknown":
            errors.append(f"Enchant spell {spell_id} has unreviewed unknown acquisition source")
        if source_type == "taught_by_item":
            formula_item_id = source.get("item_id")
            if not isinstance(formula_item_id, int) or formula_item_id <= 0:
                errors.append(f"Enchant spell {spell_id} has unresolved taught-by item relationship")
                continue
            formula_snapshot = item_snapshots.get(formula_item_id)
            if not formula_snapshot:
                errors.append(f"Enchant spell {spell_id} is missing formula item snapshot {formula_item_id}: {item_url_for_id(formula_item_id)}")
                continue
            errors.extend(item_acquisition_errors(f"Enchant formula for spell {spell_id}", formula_item_id, formula_snapshot, reviewed_unknown_item_ids, item_snapshots))
    return errors


def requirement_records_from_snapshots(snapshots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for snapshot in snapshots:
        snapshot_url = snapshot.get("url")
        if snapshot.get("page_type") in {"item", "spell"}:
            for requirement in snapshot_requirements(snapshot):
                records.append({"snapshot": snapshot, "requirement": requirement, "source_url": snapshot_url})
            for source in snapshot.get("normalized_sources", []):
                for requirement in source.get("requirements", []):
                    if isinstance(requirement, dict):
                        records.append({"snapshot": snapshot, "source": source, "requirement": requirement, "source_url": snapshot_url})
        if snapshot.get("page_type") != "guide":
            continue
        for table in snapshot.get("tables", []):
            for row in table.get("rows", []):
                for requirement in row_requirements(row, str(snapshot_url or "")):
                    records.append({"snapshot": snapshot, "table": table, "row": row, "requirement": requirement, "source_url": snapshot_url})
        for section in snapshot.get("sections", []):
            for entry in section.get("entries", []):
                for requirement in row_requirements(entry, str(snapshot_url or "")):
                    records.append({"snapshot": snapshot, "section": section, "row": entry, "requirement": requirement, "source_url": snapshot_url})
    return records


def requirement_text_audit_errors(snapshots: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for snapshot in snapshots:
        if snapshot.get("page_type") != "guide":
            continue
        for table in snapshot.get("tables", []):
            for row in table.get("rows", []):
                source_text = clean_text(str(row.get("source_text") or ""))
                if requirement_looks_like_text(source_text) and not row.get("normalized_requirements"):
                    item_label = row.get("entity_name") or row.get("item_name") or row.get("spell_name") or "row"
                    errors.append(f"Requirement-looking source text without normalized requirement for {item_label}: {source_text} ({snapshot.get('url')})")
        for section in snapshot.get("sections", []):
            for entry in section.get("entries", []):
                text = clean_text(str(entry.get("text") or ""))
                if requirement_looks_like_text(text) and not entry.get("normalized_requirements"):
                    errors.append(f"Requirement-looking section text without normalized requirement: {text} ({snapshot.get('url')})")
    return errors


def requirement_zone_audit_errors(snapshots: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for snapshot in snapshots:
        for source in snapshot.get("normalized_sources", []):
            zone = source.get("zone")
            if isinstance(zone, str) and requirement_looks_like_text(zone):
                label = snapshot.get("name") or snapshot.get("url")
                errors.append(f"Source zone is requirement text for {label}: {zone} ({snapshot.get('url')})")
    return errors


def requirement_missing_urls(
    snapshots: list[dict[str, Any]],
    data_family: str | None = None,
) -> list[str]:
    item_snapshots = item_snapshots_by_id(snapshots)
    spell_snapshots = spell_snapshots_by_id(snapshots)
    item_ids: set[int] = set()
    spell_ids: set[int] = set()

    for record in requirement_records_from_snapshots(snapshots):
        requirement = record.get("requirement", {})
        item_id = requirement.get("item_id")
        spell_id = requirement.get("spell_id")
        if isinstance(item_id, int) and item_id > 0:
            item_ids.add(item_id)
        if isinstance(spell_id, int) and spell_id > 0:
            spell_ids.add(spell_id)

    families = [data_family] if data_family else ["gems", "enchants", "consumables"]
    for family in families:
        if family == "bis_lists":
            item_ids.update(int(row["item_id"]) for row in raw_bis_rows_from_snapshots(snapshots) if isinstance(row.get("item_id"), int))
            continue
        if family == "leveling":
            continue
        imported_rows = import_rows_for_family(snapshots, family)
        imported_item_ids, imported_spell_ids, formula_item_ids = imported_entity_ids(imported_rows)
        item_ids.update(imported_item_ids)
        spell_ids.update(imported_spell_ids)
        item_ids.update(formula_item_ids)

    missing_urls: set[str] = set()
    for item_id in sorted(item_ids):
        if item_id not in item_snapshots:
            missing_urls.add(item_url_for_id(item_id))
    for spell_id in sorted(spell_ids):
        if spell_id not in spell_snapshots:
            missing_urls.add(spell_url_for_id(spell_id))
    return sorted(missing_urls)


def build_requirements_audit(input_dir: Path, data_family: str | None = None) -> dict[str, Any]:
    snapshots = load_snapshots(input_dir)
    errors = requirement_text_audit_errors(snapshots)
    errors.extend(requirement_zone_audit_errors(snapshots))
    missing_urls = requirement_missing_urls(snapshots, data_family)
    for url in missing_urls:
        errors.append(f"Missing snapshot needed for requirements: {url}")
    records = requirement_records_from_snapshots(snapshots)
    return {
        "ok": not errors,
        "errors": errors,
        "missing_urls": missing_urls,
        "summary": {
            "family": data_family or "all",
            "snapshots": len(snapshots),
            "requirements": len(records),
            "missing_urls": len(missing_urls),
        },
    }


def command_requirements_audit(args: argparse.Namespace) -> int:
    audit = build_requirements_audit(args.input_dir, args.family)
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["ok"] else 1


def build_snapshot_audit(input_dir: Path, data_family: str, guide_only: bool = False, source_urls: set[str] | None = None) -> dict[str, Any]:
    snapshots = [
        snapshot
        for snapshot in load_snapshots(input_dir)
        if not source_urls or snapshot.get("page_type") != "guide" or snapshot.get("url") in source_urls
    ]
    errors: list[str] = []
    warnings: list[str] = []
    guide_snapshots = [snapshot for snapshot in snapshots if snapshot.get("page_type") == "guide"]
    item_snapshots = item_snapshots_by_id(snapshots)
    spell_snapshots = spell_snapshots_by_id(snapshots)
    spell_snapshots_by_name = spell_snapshots_by_normalized_name(snapshots)

    manifest_guide_urls = manifest_urls_for_family(data_family)
    if source_urls:
        manifest_guide_urls = manifest_guide_urls & source_urls
    fetched_guide_urls = {snapshot.get("url") for snapshot in guide_snapshots}
    for url in sorted(manifest_guide_urls - fetched_guide_urls):
        errors.append(f"Missing guide snapshot: {url}")

    if data_family != "bis_lists":
        guide_entries = guide_entries_for_family(snapshots, data_family)
        imported_rows = import_rows_for_family(snapshots, data_family)
        if guide_snapshots and not guide_entries:
            errors.append(f"No {data_family} rows found in guide snapshots")
        if guide_entries and not imported_rows:
            errors.append(f"No importable {data_family} rows found in guide snapshots")
        for row in imported_rows:
            errors.extend(non_gear_row_errors(row, data_family))
        errors.extend(duplicate_row_errors(imported_rows, data_family))

        referenced_item_ids, referenced_spell_ids = referenced_entity_ids(guide_entries)
        imported_item_ids, imported_spell_ids, formula_item_ids = imported_entity_ids(imported_rows)
        referenced_item_ids.update(imported_item_ids)
        referenced_spell_ids.update(imported_spell_ids)

        if guide_only:
            return {
                "ok": not errors,
                "errors": errors,
                "warnings": warnings,
                "summary": {
                    "family": data_family,
                    "guide_only": True,
                    "guides": len(guide_snapshots),
                    "raw_rows": len(guide_entries),
                    "imported_rows": len(imported_rows),
                    "snapshots": len(snapshots),
                },
            }

        if data_family != "leveling":
            for item_id in sorted(referenced_item_ids - set(item_snapshots)):
                errors.append(f"Missing item snapshot for linked {data_family} item {item_id}: {item_url_for_id(item_id)}")
            for spell_id in sorted(referenced_spell_ids - set(spell_snapshots)):
                errors.append(f"Missing spell snapshot for linked {data_family} spell {spell_id}: {spell_url_for_id(spell_id)}")

        reviewed_unknown_item_ids = reviewed_unknown_source_item_ids()
        if data_family in {"gems", "consumables"}:
            for item_id in sorted(referenced_item_ids):
                errors.extend(item_acquisition_errors(data_family.rstrip("s").title(), item_id, item_snapshots.get(item_id), reviewed_unknown_item_ids, item_snapshots))
        if data_family == "enchants":
            enchant_item_ids = {row["id"] for row in imported_rows if row.get("type") == "item" and isinstance(row.get("id"), int)}
            for item_id in sorted(enchant_item_ids):
                errors.extend(item_acquisition_errors("Enchant", item_id, item_snapshots.get(item_id), reviewed_unknown_item_ids, item_snapshots))
            for spell_id in sorted(referenced_spell_ids):
                errors.extend(enchant_spell_source_errors(spell_id, spell_snapshots.get(spell_id), spell_snapshots_by_name, item_snapshots, reviewed_unknown_item_ids))
            for item_id in sorted(formula_item_ids - set(item_snapshots)):
                errors.append(f"Missing item snapshot for enchant formula {item_id}: {item_url_for_id(item_id)}")

        return {
            "ok": not errors,
            "errors": errors,
            "warnings": warnings,
            "summary": {
                "family": data_family,
                "guide_only": False,
                "guides": len(guide_snapshots),
                "items": len(item_snapshots),
                "spells": len(spell_snapshots),
                "raw_rows": len(guide_entries),
                "imported_rows": len(imported_rows),
                "referenced_items": len(referenced_item_ids),
                "referenced_spells": len(referenced_spell_ids),
                "formula_items": len(formula_item_ids),
                "snapshots": len(snapshots),
            },
        }

    raw_rows = raw_bis_rows_from_snapshots(snapshots)
    errors.extend(bis_snapshot_semantic_errors(snapshots))
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
            if seen[key] != signature and not same_guide_rank:
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
    audit = build_snapshot_audit(args.input_dir, args.family, guide_only=args.guide_only, source_urls=set(args.url or []))
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["ok"] else 1


def canonical_zone_audit_errors() -> list[str]:
    errors: list[str] = []

    def walk(value: Any, path: str) -> None:
        if isinstance(value, dict):
            zone = value.get("zone")
            if zone == "Unknown":
                errors.append(f"Synthetic Unknown zone emitted at {path}")

            raw_entity_id = value.get("entity_id") or value.get("vendor_id")
            try:
                entity_id = int(raw_entity_id)
            except (TypeError, ValueError):
                entity_id = None
            if zone == "Tanaris" and entity_id in CAVERNS_OF_TIME_ENTITY_IDS:
                errors.append(f"Caverns of Time source {entity_id} is mislabeled Tanaris at {path}")

            for key, child in value.items():
                walk(child, f"{path}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{path}[{index}]")

    for name in ["items", "enchants", "enchant_sources"]:
        walk(canonical_json(name), name)

    return errors


def build_audit() -> dict[str, Any]:
    result = validate()
    items = {item["id"]: item for item in canonical_json("items").get("items", [])}
    bis_doc = canonical_json("bis_lists")
    audit_errors = list(result.errors)
    audit_errors.extend(canonical_semantic_errors())
    audit_errors.extend(canonical_zone_audit_errors())
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
                all_contexts = ", ".join(sorted(contexts | {context}))
                audit_errors.append(f"Duplicate BiS item with distinct contexts: {item_id} ({all_contexts})")
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
    fetch_parser.add_argument("--family", choices=["bis_lists", "gems", "enchants", "consumables", "leveling", "classes", "phases", "item_corpus"])
    fetch_parser.add_argument("--output-dir", type=Path, default=RAW_WOWHEAD_DIR)
    fetch_parser.add_argument("--no-discover", action="store_true", help="Do not fetch item pages discovered from guide snapshots.")
    fetch_parser.add_argument("--missing-only", action="store_true", help="Skip URLs that already have normalized snapshots in the output directory.")
    fetch_parser.add_argument("--limit", type=int, help="Maximum number of snapshots to fetch or reprocess in this run.")
    fetch_parser.add_argument("--workers", type=int, default=1, help="Parallel fetch workers for item_corpus batches.")
    fetch_parser.add_argument("--retries", type=int, default=3)
    fetch_parser.add_argument("--delay", type=float, default=0.75)
    fetch_parser.set_defaults(func=command_fetch)

    import_parser = subparsers.add_parser("import", help="Import canonical data from normalized snapshots.")
    import_parser.add_argument("--input-dir", type=Path, default=RAW_WOWHEAD_DIR)
    import_parser.add_argument("--family", choices=["bis_lists", "gems", "enchants", "consumables", "leveling", "item_corpus"])
    import_parser.add_argument("--dry-run", action="store_true")
    import_parser.set_defaults(func=command_import)

    reprocess_parser = subparsers.add_parser("reprocess", help="Rebuild normalized snapshots from the local html_cache without network fetches.")
    reprocess_parser.add_argument("--input-dir", type=Path, default=RAW_WOWHEAD_DIR)
    reprocess_parser.add_argument("--output-dir", type=Path)
    reprocess_parser.set_defaults(func=command_reprocess)

    audit_parser = subparsers.add_parser("audit", help="Audit canonical scraped data.")
    audit_parser.set_defaults(func=command_audit)

    requirements_audit_parser = subparsers.add_parser("requirements-audit", help="Audit normalized prerequisite extraction and missing prerequisite snapshots.")
    requirements_audit_parser.add_argument("--input-dir", type=Path, default=RAW_WOWHEAD_DIR)
    requirements_audit_parser.add_argument("--family", choices=["bis_lists", "gems", "enchants", "consumables", "leveling"])
    requirements_audit_parser.set_defaults(func=command_requirements_audit)

    snapshot_audit_parser = subparsers.add_parser("snapshot-audit", help="Audit normalized raw snapshots before import.")
    snapshot_audit_parser.add_argument("--input-dir", type=Path, default=RAW_WOWHEAD_DIR)
    snapshot_audit_parser.add_argument("--family", choices=["bis_lists", "gems", "enchants", "consumables", "leveling"], default="bis_lists")
    snapshot_audit_parser.add_argument("--url", action="append", help="Restrict guide snapshot checks to a specific manifest URL, useful for pilots.")
    snapshot_audit_parser.add_argument("--guide-only", action="store_true", help="Only require guide snapshots and parsable guide rows.")
    snapshot_audit_parser.set_defaults(func=command_snapshot_audit)

    item_corpus_report_parser = subparsers.add_parser("item-corpus-report", help="Summarize parsed item corpus stats without writing canonical data.")
    item_corpus_report_parser.add_argument("--input-dir", type=Path, default=RAW_WOWHEAD_DIR / "full_item_corpus")
    item_corpus_report_parser.set_defaults(func=command_item_corpus_report)

    item_corpus_audit_parser = subparsers.add_parser("item-corpus-audit", help="Audit item corpus snapshots and parse completeness.")
    item_corpus_audit_parser.add_argument("--input-dir", type=Path, default=RAW_WOWHEAD_DIR / "full_item_corpus")
    item_corpus_audit_parser.set_defaults(func=command_item_corpus_audit)

    suffix_audit_parser = subparsers.add_parser("suffix-audit", help="Audit random suffix item variants.")
    suffix_audit_parser.add_argument("--input-dir", type=Path, default=RAW_WOWHEAD_DIR / "full_item_corpus")
    suffix_audit_parser.set_defaults(func=command_suffix_audit)

    recommendation_audit_parser = subparsers.add_parser("recommendation-audit", help="Audit generated leveling recommendations against guide rows and source evidence.")
    recommendation_audit_parser.set_defaults(func=command_recommendation_audit)

    coverage_parser = subparsers.add_parser("coverage", help="Report offline manifest coverage without fetching.")
    coverage_parser.add_argument("--family", choices=["bis_lists", "gems", "enchants", "consumables", "leveling", "classes", "phases", "item_corpus"])
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
