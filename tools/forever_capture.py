"""Import explicitly selected local observations as data, never by running Lua."""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from tools.forever_sources import PROVIDER_RAW_DIR, content_digest
from tools.project import FOREVER_CANONICAL_DIR, load_json, write_text


class LuaDataReader:
    """The SavedVariables literal subset, with bounded input and nesting."""

    SPACE = re.compile(r"\s+|--[^\r\n]*")
    IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")
    ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z_0-9]*\s*=")
    NUMBER = re.compile(r"-?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?")
    BYTE = re.compile(r"\d{1,3}")

    def __init__(self, text: str):
        self.text = text
        self.position = 0

    def whitespace(self):
        while True:
            match = self.SPACE.match(self.text, self.position)
            if not match:
                return
            self.position += len(match[0])

    def take(self, token: str) -> bool:
        self.whitespace()
        if self.text.startswith(token, self.position):
            self.position += len(token)
            return True
        return False

    def require(self, token: str):
        if not self.take(token):
            raise ValueError(f"Expected SavedVariables literal {token!r} at offset {self.position}")

    def identifier(self) -> str:
        self.whitespace()
        match = self.IDENTIFIER.match(self.text, self.position)
        if not match:
            raise ValueError(f"Expected a SavedVariables identifier at offset {self.position}")
        self.position += len(match[0])
        return match[0]

    def string(self) -> str:
        quote = self.text[self.position]
        self.position += 1
        result = []
        escapes = {"n": "\n", "r": "\r", "t": "\t", "a": "\a", "b": "\b", "f": "\f", "v": "\v", "\\": "\\", '"': '"', "'": "'"}
        while self.position < len(self.text):
            char = self.text[self.position]
            self.position += 1
            if char == quote:
                return "".join(result)
            if char == "\\":
                if self.position >= len(self.text):
                    break
                char = self.text[self.position]
                if char.isdigit():
                    match = self.BYTE.match(self.text, self.position)
                    if int(match[0]) > 255:
                        raise ValueError("Invalid SavedVariables byte escape")
                    result.append(chr(int(match[0])))
                    self.position += len(match[0])
                elif char in escapes:
                    result.append(escapes[char])
                    self.position += 1
                else:
                    raise ValueError("Unsupported SavedVariables escape")
            else:
                result.append(char)
        raise ValueError("Unterminated SavedVariables string")

    def value(self, depth=0):
        if depth > 64:
            raise ValueError("SavedVariables nesting exceeds 64 levels")
        self.whitespace()
        if self.position >= len(self.text):
            raise ValueError("Incomplete SavedVariables literal")
        if self.text[self.position] in {'"', "'"}:
            return self.string()
        if self.take("{"):
            result, implicit = {}, 1
            while not self.take("}"):
                if self.take("["):
                    key = self.value(depth + 1)
                    self.require("]")
                    self.require("=")
                    value = self.value(depth + 1)
                else:
                    start = self.position
                    match = self.ASSIGNMENT.match(self.text, start)
                    if match:
                        key = self.identifier()
                        self.require("=")
                        value = self.value(depth + 1)
                    else:
                        key, value = implicit, self.value(depth + 1)
                        implicit += 1
                if type(key) not in (str, int) or key in result:
                    raise ValueError("Invalid or duplicate SavedVariables table key")
                result[key] = value
                if not self.take(",") and not self.take(";"):
                    self.whitespace()
                    if not self.text.startswith("}", self.position):
                        raise ValueError("Expected a SavedVariables table separator")
            if result and set(result) == set(range(1, len(result) + 1)):
                return [result[index] for index in range(1, len(result) + 1)]
            return result
        match = self.NUMBER.match(self.text, self.position)
        if match:
            self.position += len(match[0])
            value = float(match[0]) if any(c in match[0] for c in ".eE") else int(match[0])
            if type(value) is float and not math.isfinite(value):
                raise ValueError("Non-finite SavedVariables number")
            return value
        name = self.identifier()
        if name not in {"true", "false", "nil"}:
            raise ValueError("Executable Lua is not capture data")
        return {"true": True, "false": False, "nil": None}[name]

    def read(self):
        values = {}
        while True:
            self.whitespace()
            if self.position == len(self.text):
                break
            name = self.identifier()
            if name in values:
                raise ValueError("Duplicate SavedVariables assignment")
            self.require("=")
            values[name] = self.value()
        return values


def read_capture(path: Path) -> dict:
    if path.suffix.lower() not in {".lua", ".json"}:
        raise ValueError("Select a SavedVariables .lua file or a .json capture document")
    if path.stat().st_size > 8 * 1024 * 1024:
        raise ValueError("Capture exceeds the 8 MiB import limit")
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".json":
        document = json.loads(text)
    else:
        assignments = LuaDataReader(text).read()
        account = assignments.get("BigBiSListDB", {})
        branch = account.get("forever", {}) if isinstance(account, dict) else {}
        document = branch.get("capture") if isinstance(branch, dict) else None
    if not isinstance(document, dict):
        raise ValueError("No Forever capture document in the selected file")
    return document


def positive_id(value) -> bool:
    return type(value) is int and 0 < value < 2 ** 31


def normalize_capture(document: dict, client_build: str) -> list[dict]:
    from tools.scrape_wowhead import parse_item_stats

    if not re.fullmatch(r"1\.60\.\d+\.\d+", client_build):
        raise ValueError("Expected the reviewed Forever client build")
    if type(document.get("version")) is not int or document["version"] != 1 or document.get("flavor") != "forever" or document.get("client_build") != client_build:
        raise ValueError("Wrong-client, stale-build, or unsupported capture document")
    observations = document.get("records")
    if observations == {}:
        observations = []
    if not isinstance(observations, list) or len(observations) > 5000:
        raise ValueError("Expected at most 5000 capture records")
    normalized = {}
    for observation in observations:
        if not isinstance(observation, dict) or observation.get("kind") not in {"tooltip", "loot", "quest_reward", "vendor", "entrance"}:
            raise ValueError("Unknown capture record kind")
        if observation.get("client_build") != client_build:
            raise ValueError("Capture contains observations from another build")
        try:
            observed_at = observation["observed_at"]
            instant = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
            if instant.utcoffset() != timezone.utc.utcoffset(instant):
                raise ValueError("Capture timestamp must be UTC")
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            raise ValueError("Invalid UTC capture timestamp") from exc
        kind = observation["kind"]
        identifier = observation.get("item_id")
        if kind != "entrance" and not positive_id(identifier):
            raise ValueError("Capture needs a positive item ID")
        row = {"flavor": "forever", "provider": "local_capture", "client_build": client_build,
               "fetched_at": observed_at, "page_type": "observations", "confidence": "local_observation", "relationships": []}
        faction = observation.get("faction")
        if faction not in {"Alliance", "Horde"}:
            raise ValueError("Capture needs the observed faction")
        row["observed_faction"] = faction
        if kind == "tooltip":
            lines, name = observation.get("lines"), observation.get("name")
            if not isinstance(name, str) or not name or not isinstance(lines, list) or not 1 <= len(lines) <= 120:
                raise ValueError("Malformed captured item tooltip")
            if not all(isinstance(line, str) and len(line) <= 1000 for line in lines):
                raise ValueError("Invalid captured tooltip line")
            # The recorder only stores public item text. Reject captures from a
            # different recorder that included creator or account information.
            if any(re.search(r"made by|crafted by|account name|character name", line, re.I) for line in lines):
                raise ValueError("Capture includes private tooltip fields")
            stats = parse_item_stats(f"https://www.wowhead.com/forever/item={identifier}", identifier, name, "", lines, None,
                                     "unknown", "unknown", None, [])
            stats["parse_confidence"] = "observed_tooltip"
            row.update({"page_type": "item", "item_id": identifier, "name": name, "item_stats": stats,
                        "inventory_slot": stats.get("slot"), "normalized_requirements": [], "normalized_sources": [],
                        "item_kind": "recipe" if re.match(r"^(?:Plans|Pattern|Recipe|Schematic|Formula):", name) else ("equipment" if stats.get("slot") else "other")})
        elif kind in {"quest_reward", "vendor", "loot"}:
            field = {"quest_reward": "quest_id", "vendor": "npc_id", "loot": "npc_id"}[kind]
            source_id = observation.get(field)
            if kind != "loot" and not positive_id(source_id):
                raise ValueError("Captured interaction needs its exact source ID")
            if positive_id(source_id):
                edge = {"relation": {"quest_reward": "reward_choice" if observation.get("choice") else "rewards", "vendor": "sells", "loot": "drops"}[kind],
                        "subject_type": "quest" if kind == "quest_reward" else "npc", "subject_id": source_id,
                        "object_type": "item", "object_id": identifier, "observed_faction": faction, "confidence": "local_observation"}
                if kind == "vendor" and type(observation.get("price_copper")) is int and observation["price_copper"] >= 0:
                    edge["price_copper"] = observation["price_copper"]
                    edge["extended_cost_unresolved"] = observation.get("extended_cost") is True
                    if type(observation.get("stock")) is int:
                        edge["stock"] = observation["stock"]
                for field in ("instance_id", "difficulty_id"):
                    if positive_id(observation.get(field)):
                        edge[field] = observation[field]
                row["relationships"] = [edge]
            else:
                row["ambiguous_loot"] = {"item_id": identifier}
        else:
            if not positive_id(observation.get("instance_id")):
                raise ValueError("Entrance observation needs its instance ID")
            row["instance_id"] = observation["instance_id"]
        point = observation.get("position")
        if point is not None:
            if not isinstance(point, dict) or not positive_id(point.get("map_id")) or not all(
                type(point.get(axis)) in {int, float} and math.isfinite(point[axis]) and 0 <= point[axis] <= 1 for axis in ("x", "y")
            ):
                raise ValueError("Invalid approximate capture position")
            row["position_observation"] = {"map_id": point["map_id"], "x": point["x"], "y": point["y"], "kind": "player"}
        # Drop unknown fields, including all character/account identifiers.
        row["url"] = "capture://forever/" + content_digest(row)
        for edge in row["relationships"]:
            edge["source_url"] = row["url"]
        normalized.setdefault(row["url"], row)
    return [normalized[url] for url in sorted(normalized)]


def import_capture(path: Path, client_build: str, *, write: bool) -> dict:
    snapshots = normalize_capture(read_capture(path), client_build)
    manifest = load_json(FOREVER_CANONICAL_DIR / "scrape_manifest.json")
    existing = {row["url"] for row in manifest["sources"]}
    additions = [row for row in snapshots if row["url"] not in existing]
    if write:
        manifest["sources"].extend({"url": row["url"], "provider": "local_capture", "data_family": "observations",
                                    "status": "pending_live_review"} for row in additions)
        write_text(FOREVER_CANONICAL_DIR / "scrape_manifest.json", json.dumps(manifest, indent=2) + "\n")
        for row in additions:
            name = row["url"].rsplit("/", 1)[-1]
            write_text(PROVIDER_RAW_DIR / "local_capture" / (name + ".json"), json.dumps(row, indent=2, sort_keys=True) + "\n")
    return {"observations": len(snapshots), "new_observations": len(additions), "written": write,
            "kinds": dict(sorted(Counter(row["page_type"] for row in snapshots).items()))}
