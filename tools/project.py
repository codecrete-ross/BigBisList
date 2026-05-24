from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ADDON_DIR = ROOT / "addon" / "BigBiSList"
CANONICAL_DIR = ROOT / "data" / "canonical"
RAW_WOWHEAD_DIR = ROOT / "data" / "raw" / "wowhead"
SCHEMA_DIR = ROOT / "data" / "schema"
REFERENCE_DIR = ROOT / "vendor" / "reference" / "BIS-TBC-1.15"

PHASE_KEYS = ["PR", "T4", "T5", "T6", "ZA", "SWP"]
SLOT_NAMES = {
    "Head",
    "Neck",
    "Shoulder",
    "Back",
    "Chest",
    "Wrist",
    "Hands",
    "Waist",
    "Legs",
    "Feet",
    "Ring",
    "Trinket",
    "Main Hand",
    "Off Hand",
    "Two Hand",
    "Dual Wield",
    "Ranged",
    "Idol",
    "Totem",
    "Libram",
    "Relic",
}

CANONICAL_FILES = {
    "classes": "classes.json",
    "phases": "phases.json",
    "bis_lists": "bis_lists.json",
    "items": "items.json",
    "gems": "gems.json",
    "gem_sources": "gem_sources.json",
    "enchants": "enchants.json",
    "enchant_sources": "enchant_sources.json",
    "consumables": "consumables.json",
    "leveling": "leveling.json",
    "credits": "credits.json",
    "overrides": "overrides.json",
    "scrape_manifest": "scrape_manifest.json",
}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def canonical_json(name: str) -> Any:
    return load_json(CANONICAL_DIR / CANONICAL_FILES[name])


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def lua_string(value: str) -> str:
    escaped = (
        value.replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace('"', '\\"')
    )
    return f'"{escaped}"'


def lua_value(value: Any, indent: int = 0) -> str:
    space = " " * indent
    next_indent = indent + 4
    next_space = " " * next_indent

    if value is None:
        return "nil"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return lua_string(value)
    if isinstance(value, list):
        if not value:
            return "{}"
        lines = ["{"]
        for item in value:
            lines.append(f"{next_space}{lua_value(item, next_indent)},")
        lines.append(f"{space}}}")
        return "\n".join(lines)
    if isinstance(value, dict):
        if not value:
            return "{}"
        lines = ["{"]
        for key in sorted(value):
            lua_key = f"[{lua_string(str(key))}]"
            lines.append(f"{next_space}{lua_key} = {lua_value(value[key], next_indent)},")
        lines.append(f"{space}}}")
        return "\n".join(lines)
    raise TypeError(f"Cannot serialize {type(value)!r} to Lua")
