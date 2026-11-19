"""Normalize and audit the effects carried by Forever gear."""

from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256
import re


VERSION = "forever-item-effects-1"
CHANCE_STATS = {
    "hit": "hit_percent",
    "dodge": "dodge_percent",
    "dodge an attack": "dodge_percent",
    "parry": "parry_percent",
    "parry an attack": "parry_percent",
    "block": "block_percent",
    "block an attack": "block_percent",
    "critically strike": "crit_percent",
    "get a critical strike": "crit_percent",
    "get a critical strike with spells": "spell_crit_percent",
    "get a critical strike with melee and ranged attacks": "physical_crit_percent",
}
CHANCE = re.compile(r"Equip: (?:Improves|Increases) your chance to (.+) by (\d+(?:\.\d+)?)%\.?", re.I)
TRAVEL = re.compile(r"(?:Equip:\s*)?Increases mount speed by \d+%\.?", re.I)
EXTRA_ATTACK = re.compile(r"Chance on hit: Grants (an?|\d+) extra attacks? on your next swing\.?", re.I)
MANA_COST = re.compile(r"Equip: Reduces the mana cost of your Seal spells by (\d+)%\.", re.I)
ALL_STATS = re.compile(r"Equip: Has a (\d+)% chance when struck in combat of increasing all stats by (\d+) for 1 min\. \(Proc chance: \1%, (\d+)m cooldown\)", re.I)
MANA_TICKS = re.compile(r"Use: Restores (\d+) Mana every 1 sec for (\d+) sec\.( This effect is doubled in Mountainous areas\.)? \((\d+) Min Cooldown\)", re.I)
SPELL_HIT = re.compile(r"Use: Increases your Spell Hit chance by (\d+)% for (\d+) sec\. \((\d+) Min Cooldown\)", re.I)
MAX_HEALTH = re.compile(r"Use: Increases maximum health by (\d+) for (\d+) sec\. This effect is doubled in Strongholds and Cities\. \((\d+) Min Cooldown\)", re.I)
TARGET_CRIT = re.compile(r"Use: Marks your target, increasing your Critical Strike chance against them by (\d+)% for (\d+) sec\. This effect is doubled against Orcs and Ogres\. \((\d+) Min Cooldown\)", re.I)
USE_STAT = re.compile(r"Use: Increases (?:your )?(attack power|spell power|armor) by (\d+) for (\d+) sec\. \((\d+) (Min|Sec) Cooldown\)", re.I)
USE_RESTORE = re.compile(r"Use: Restores (\d+)(?: to (\d+))? (health|mana)\. \((\d+) (Min|Sec) Cooldown\)", re.I)
WEAPON_DAMAGE = re.compile(r"Chance on hit: (?:Blasts a target for|Sends a shadowy bolt at the enemy causing) (\d+) (Fire|Shadow) damage\.", re.I)
STRUCK_DAMAGE = re.compile(r"Equip: When struck in combat has a (\d+)% chance of inflicting (\d+) to (\d+) (Shadow|Nature) damage to the attacker\. \(Proc chance: \1%\)", re.I)
BLOCK_DAMAGE = re.compile(r"Equip: Deals (\d+) to (\d+) (\w+) damage every time you block\.", re.I)
STRUCK_ARMOR = re.compile(r"Equip: When struck in combat has a (\d+)% chance to encase the caster in bone, increasing armor by (\d+) for (\d+) sec\. \(Proc chance: \1%\)", re.I)
POWER_AND_SPEED = re.compile(r"Chance on hit: Increases Attack Power by (\d+) and melee attack speed by (\d+)% for (\d+) sec\.", re.I)
PROC_STAT = {"attack power": "attack_power", "spell power": "spell_power", "armor": "armor"}

# Literal text around a single number keeps the same rules usable in Lua.
FLAT_PASSIVE_STATS = (
    ("equip: increased defense +", "", "defense"),
    ("equip: +", " defense", "defense"),
    ("equip: +", " attack power", "attack_power"),
    ("equip: increases attack power by ", "", "attack_power"),
    ("equip: increases your attack power by ", "", "attack_power"),
    ("equip: +", " ranged attack power", "ranged_attack_power"),
    ("equip: increases ranged attack power by ", "", "ranged_attack_power"),
    ("equip: +", " block value", "block_value"),
    ("equip: increases damage done by magical spells and effects by up to ", "", "spell_damage"),
    ("equip: increases damage done by spells and effects by up to ", "", "spell_damage"),
)


def flat_passive_stat(text: str) -> tuple[str, int] | None:
    text = text.strip().removesuffix(".").lower()
    for prefix, suffix, stat in FLAT_PASSIVE_STATS:
        if text.startswith(prefix) and text.endswith(suffix):
            amount = text[len(prefix):len(text) - len(suffix)].strip()
            if amount.isascii() and amount.isdecimal():
                return stat, int(amount)
    return None


def cooldown(amount: str, unit: str) -> int:
    return int(amount) * (60 if unit.casefold() == "min" else 1)


def permanent_chance(text: str) -> tuple[str, float] | None:
    match = CHANCE.fullmatch(text)
    if match and (stat := CHANCE_STATS.get(match[1].casefold())):
        return stat, float(match[2])
    return None


def effect_lines(item: dict) -> dict[str, dict]:
    lines = {row["raw_text"]: row for row in item.get("effect_stats", []) if row.get("raw_text")}
    for field in ("effects", "equip_effects", "use_effects"):
        for label in item.get(field, []):
            if isinstance(label, str) and label.strip():
                lines.setdefault(label, {})
    if item.get("set_bonuses"):
        lines.setdefault("Set bonuses", {})
    return lines


def permanent_stat(text: str) -> tuple[str, float] | None:
    return flat_passive_stat(text) or permanent_chance(text)


def recover_permanent_stats(stats: dict, lines: dict) -> None:
    for label in lines:
        if parsed := permanent_stat(label):
            stat, amount = parsed
            stats.setdefault(stat, amount)


def unresolved_lines(item: dict) -> list[str]:
    return [label for label, row in effect_lines(item).items()
            if not permanent_stat(label) and not (row.get("type") == "passive" and row.get("stats"))]


def classify(label: str) -> str:
    if permanent_stat(label):
        return "permanent_stat"
    if TRAVEL.fullmatch(label):
        return "travel"
    if EXTRA_ATTACK.fullmatch(label) or re.search(r"\bextra attacks?\b", label, re.I):
        return "extra_attack"
    if label == "Set bonuses":
        return "set_bonus"
    if label.startswith("Use:"):
        return "on_use"
    if re.search(r"\b(?:chance on|when struck|chance to|have a chance|every time you block)\b", label, re.I):
        return "triggered"
    return "conditional"


def effect_rule(label: str) -> dict | None:
    """Extract exact mechanics. Encounter observations supply the realized value."""
    identity = {"key": sha256(label.encode()).hexdigest()[:16], "label": label}
    if match := EXTRA_ATTACK.fullmatch(label):
        count = 1 if match[1].casefold() in {"a", "an"} else int(match[1])
        return {**identity, "kind": "extra_attack", "count": count, "trigger": "weapon_hit"}
    if match := ALL_STATS.fullmatch(label):
        return {**identity, "kind": "timed_stats", "trigger": "struck", "chance": int(match[1]) / 100,
                "duration": 60, "cooldown": 60 * int(match[3]),
                "stats": dict.fromkeys(("strength", "agility", "stamina", "intellect", "spirit"), int(match[2]))}
    if match := MANA_TICKS.fullmatch(label):
        return {**identity, "kind": "instant", "trigger": "use", "cooldown": 60 * int(match[4]),
                "duration": int(match[2]), "amounts": {"mp5": 5 * int(match[1]) * int(match[2])},
                **({"terrain_multiplier": {"mountainous": 2}} if match[3] else {})}
    if match := SPELL_HIT.fullmatch(label):
        return {**identity, "kind": "timed_stats", "trigger": "use", "duration": int(match[2]),
                "cooldown": 60 * int(match[3]), "stats": {"spell_hit_percent": int(match[1])}}
    if match := MANA_COST.fullmatch(label):
        return {**identity, "kind": "mana_cost", "ability": "seal", "fraction": int(match[1]) / 100}
    if match := MAX_HEALTH.fullmatch(label):
        return {**identity, "kind": "timed_stats", "trigger": "use", "duration": int(match[2]),
                "cooldown": 60 * int(match[3]), "stats": {"health": int(match[1])},
                "terrain_multiplier": {"stronghold": 2, "city": 2}}
    if match := TARGET_CRIT.fullmatch(label):
        return {**identity, "kind": "timed_stats", "trigger": "use", "duration": int(match[2]),
                "cooldown": 60 * int(match[3]), "stats": {"physical_crit_percent": int(match[1])},
                "target_multiplier": {"orc": 2, "ogre": 2}, "requires_target_fraction": True}
    if match := USE_STAT.fullmatch(label):
        return {**identity, "kind": "timed_stats", "trigger": "use", "duration": int(match[3]),
                "cooldown": cooldown(match[4], match[5]), "stats": {PROC_STAT[match[1].casefold()]: int(match[2])}}
    if match := USE_RESTORE.fullmatch(label):
        stat = "hp5" if match[3].casefold() == "health" else "mp5"
        return {**identity, "kind": "instant", "trigger": "use", "cooldown": cooldown(match[4], match[5]),
                "amounts": {stat: 5 * (int(match[1]) + int(match[2] or match[1])) / 2}}
    if match := WEAPON_DAMAGE.fullmatch(label):
        return {**identity, "kind": "damage", "trigger": "weapon_hit",
                "amount": int(match[1]), "school": match[2].casefold()}
    if match := STRUCK_DAMAGE.fullmatch(label):
        return {**identity, "kind": "damage", "trigger": "struck", "chance": int(match[1]) / 100,
                "amount": (int(match[2]) + int(match[3])) / 2, "school": match[4].casefold()}
    if match := BLOCK_DAMAGE.fullmatch(label):
        return {**identity, "kind": "damage", "trigger": "block", "chance": 1,
                "amount": (int(match[1]) + int(match[2])) / 2, "school": match[3].casefold()}
    if match := STRUCK_ARMOR.fullmatch(label):
        return {**identity, "kind": "timed_stats", "trigger": "struck", "chance": int(match[1]) / 100,
                "duration": int(match[3]), "stats": {"armor": int(match[2])}}
    if match := POWER_AND_SPEED.fullmatch(label):
        return {**identity, "kind": "timed_stats", "trigger": "weapon_hit", "duration": int(match[3]),
                "stats": {"attack_power": int(match[1]), "melee_haste_percent": int(match[2])}}
    return None


def attach_rules(item: dict) -> dict:
    rules = [rule for label in unresolved_lines(item) if (rule := effect_rule(label))]
    return {"effect_rules": rules} if rules else {}


def glossary(snapshots: dict | None, items: list[dict], *, mechanics: dict | None = None, limit: int = 20) -> dict:
    """Group exact linked effect descriptions for a bounded evidence review."""
    from tools.forever import item_observations, snapshot_digest

    linked = defaultdict(set)
    evidence = defaultdict(set)
    observed_lines = defaultdict(dict)
    reviewed_sets = {row["spell_id"] for row in (mechanics or {}).get("flat_sets", [])}
    if snapshots:
        digests = {}
        for identifier, observations in item_observations(snapshots).items():
            for observed in observations:
                if observed.get("item_kind") != "equipment":
                    continue
                url = observed["evidence_url"]
                if url not in digests:
                    digests[url] = snapshot_digest(snapshots[url])
                for label, facts in effect_lines(observed.get("item_stats", {})).items():
                    if facts.get("stats") or label not in observed_lines[identifier]:
                        observed_lines[identifier][label] = facts
                    evidence[(identifier, label)].add((url, digests[url]))
                for bonus in observed.get("item_stats", {}).get("set_bonuses", []):
                    label = f"{bonus['pieces']} pieces · {bonus['text']}"
                    observed_lines[identifier][label] = {"type": "set_bonus", "spell_id": bonus.get("spell_id")}
                    evidence[(identifier, label)].add((url, digests[url]))
                for spell in observed.get("linked_entities", []):
                    if spell.get("type") == "spell" and isinstance(spell.get("name"), str):
                        linked[(identifier, spell["name"].strip().rstrip("."))].add(spell["id"])

    groups = {}
    counts = Counter()
    variants = {(item["id"], item.get("variant_id") or str(item["id"])): item for item in items}
    for identifier in observed_lines:
        variants.setdefault((identifier, str(identifier)), {"id": identifier})
    for (identifier, variant), item in variants.items():
        lines = effect_lines(item)
        if variant == str(identifier):
            for label, facts in observed_lines.get(identifier, {}).items():
                if facts or label not in lines:
                    lines[label] = facts
        for bonus in item.get("set_bonuses", []):
            label = f"{bonus['pieces']} pieces · {bonus['text']}"
            lines[label] = {"type": "set_bonus", "spell_id": bonus.get("spell_id")}
        lines.pop("Set bonuses", None)

        for label, facts in lines.items():
            kind = "set_bonus" if facts.get("type") == "set_bonus" else classify(label)
            accounted = (kind == "permanent_stat" or (facts.get("type") == "passive" and facts.get("stats"))
                         or facts.get("spell_id") in reviewed_sets)
            status = "accounted" if accounted else (
                "situational" if kind == "travel" else "needs_evidence")
            normalized = label.removeprefix("Equip: ").removeprefix("Use: ").removeprefix("Chance on hit: ").strip().rstrip(".")
            spell_ids = tuple(sorted(linked[(identifier, normalized)] | ({facts["spell_id"]} if facts.get("spell_id") else set())))
            signature = (kind, spell_ids, label)
            group = groups.setdefault(signature, {"kind": kind, "spell_ids": spell_ids, "label": label,
                "items": set(), "variants": set(), "slots": set(), "evidence": set()})
            group["items"].add(identifier)
            group["variants"].add(variant)
            group["slots"].add(item.get("slot", "Unknown"))
            group["evidence"].update(evidence[(identifier, label)])
            if status == "needs_evidence" or "status" not in group:
                group["status"] = status
            if rule := effect_rule(label):
                group["rule"] = rule
            counts[status] += 1

    unresolved = [row for row in groups.values() if row["status"] == "needs_evidence"]
    unresolved.sort(key=lambda row: (-len(row["items"]), min(row["items"]), row["label"]))
    for row in unresolved[:limit]:
        for key in ("items", "variants", "slots", "evidence"):
            row[key] = sorted(row[key])
        row["signature"] = sha256(repr((row["kind"], row["spell_ids"], row["label"])).encode()).hexdigest()
    return {"version": VERSION, "items_with_effects": len({identifier for row in groups.values() for identifier in row["items"]}),
            "effect_groups": len(groups), "effect_rows_by_status": dict(sorted(counts.items())),
            "recognized_rule_groups": sum("rule" in row for row in groups.values()),
            "reviewed_flat_set_spells": len(reviewed_sets),
            "reviewed_flat_enchants": len((mechanics or {}).get("enchants", {})),
            "unresolved_groups": len(unresolved), "review_queue": unresolved[:limit]}
