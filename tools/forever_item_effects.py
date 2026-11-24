"""Normalize and audit the effects carried by Forever gear."""

from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256
import re

from tools.forever_effect_benchmarks import compile_rule, extra_rule, missing_reason


VERSION = "forever-item-effects-2"
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
EXPERTISE = re.compile(r"Equip: Reduces (?:your )?chance (?:for your (?:melee )?attacks )?to be Dodged or Parried by (\d+(?:\.\d+)?)%\.?", re.I)
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
    ("equip: +", " weapon damage", "weapon_damage"),
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
    if match := EXPERTISE.fullmatch(text):
        return "expertise", float(match[1])
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
    parsed = extra_rule(label)
    return {**identity, **parsed} if parsed else None


def attach_rules(item: dict) -> dict:
    lines = unresolved_lines(item)
    facts = effect_lines(item)
    leads = defaultdict(set)
    for lead in item.get("effect_leads", []):
        if match := re.fullmatch(r"(chance on hit|equip|use): (\d+) ([^(]+?)(?: \(([^)]+)\))?", lead, re.I):
            leads[match[1].lower()].add((int(match[2]), match[3], match[4] or ""))
    rules, seen = [], {}
    charged = {re.sub(r" \d+ Charges?$", "", line, flags=re.I) for line in lines if re.search(r" \d+ Charges?$", line, re.I)}
    for label in lines:
        clean = label.split(' "', 1)[0]
        if clean in seen:
            seen[clean].setdefault("aliases", []).append(label)
            continue
        if rule := effect_rule(clean):
            rule = {**rule, "label": label}
            if not rule.get("bonus_targets") and re.search(r"\b(?:doubled|tripled|if there is|against|times as much)\b", clean, re.I):
                rule["secondary"] = True
            trigger = clean.partition(":")[0].lower()
            spells = leads[trigger]
            if spell_id := facts[label].get("spell_id"):
                rule["spell_id"] = spell_id
                spells = {s for s in spells if s[0] == spell_id}
            same_trigger = {line.split(' "', 1)[0] for line in lines if line.partition(":")[0].lower() == trigger}
            if len(spells) == 1 and (rule.get("spell_id") or len(same_trigger) == 1 or clean in charged):
                rule["spell_id"], rule["spell_name"], timers = next(iter(spells))
                if timer := re.search(r"(?:^|, )(\d+) s shared cooldown", timers):
                    rule["shared_cooldown"] = int(timer[1])
                if timer := re.search(r"(?:^|, )(\d+) s cooldown", timers):
                    rule.setdefault("cooldown", int(timer[1]))
                if re.search(r"\b\d+ charges?\b", timers, re.I):
                    charged.add(clean)
            if clean in charged and rule["kind"] != "situational":
                rule["gap"] = "Limited charges and replacement or recharge frequency"
            else:
                rule = compile_rule(rule, item)
            seen[clean] = rule
            rules.append(rule)
    return {"effect_rules": rules} if rules else {}


def tooltip_sets(observations: dict, items: list[dict]) -> dict:
    """Bind a set to the full, linked member list printed in a Forever tooltip."""
    names = {row["id"]: [s[5:] for s in row.get("effect_leads", []) if s.startswith("Set: ")] for row in items}
    sets, conflicts = {}, set()
    for identifier, rows in sorted(observations.items()):
        for row in sorted(rows, key=lambda r: r["evidence_url"]):
            bonuses = row.get("item_stats", {}).get("set_bonuses")
            if not bonuses or any(not b.get("spell_id") or not b.get("text") for b in bonuses):
                continue
            match = re.search(r"\(0/(\d+)\)\s*(.*?)\s*\(\d+\)\s*Set\s*:", row.get("description", ""))
            if not match:
                continue
            members = sorted({e["id"] for e in row.get("linked_entities", []) if e.get("type") == "item"
                              and e.get("name") and e["name"] in match[2]})
            if len(members) != int(match[1]) or identifier not in members:
                continue
            key = ",".join(map(str, members))
            if key in sets:
                if sets[key]["bonuses"] != bonuses:
                    conflicts.add(key)
                continue
            labels = {s for i in members for s in names.get(i, []) if s + " (0/" in row["description"]}
            sets[key] = {"name": next(iter(labels)) if len(labels) == 1 else row["name"] + " set",
                         "members": members, "bonuses": bonuses, "source": row["evidence_url"]}
    return {key: row for key, row in sets.items() if key not in conflicts}


def set_stat(text: str) -> dict | None:
    stats = {s.replace("_", " "): s for s in ("strength", "agility", "intellect", "spirit", "stamina", "armor",
             "attack_power", "ranged_attack_power", "defense", "block_value", "spell_power",
             "shadow_resistance", "nature_resistance", "frost_resistance", "fire_resistance", "arcane_resistance")}
    if match := re.fullmatch(r"\+(\d+) ([\w ]+)\.?", text, re.I):
        amount, stat = int(match[1]), match[2].casefold()
        if stat == "all resistances":
            return {key: amount for key in stats.values() if key.endswith("_resistance")}
        if stat in stats:
            return {stats[stat]: amount}
    if parsed := permanent_stat("Equip: " + text):
        return {parsed[0]: parsed[1]}
    if match := re.fullmatch(r"Restores (\d+) (mana|health) per (\d+) sec\.", text, re.I):
        return {"mp5" if match[2].lower() == "mana" else "hp5": 5 * int(match[1]) / int(match[3])}
    if match := re.fullmatch(r"Increases healing done by spells and effects by up to (\d+)\.", text, re.I):
        return {"healing_power": int(match[1])}
    if match := re.fullmatch(r"Improves your chance to get a critical strike with melee attacks by ([\d.]+)%\.", text, re.I):
        return {"melee_crit_percent": float(match[1])}
    rule = extra_rule("Equip: " + text)
    if rule and rule["kind"] == "passive_stats" and not rule.get("secondary") and not rule.get("requires_form"):
        return rule["stats"]
    return None


def set_catalog(document: dict) -> tuple[dict, dict]:
    definitions, members = {}, defaultdict(list)
    for key, row in document.get("effect_sets", {}).items():
        bonuses = []
        for bonus in row["bonuses"]:
            stats = set_stat(bonus["text"])
            reason = missing_reason("Equip: " + bonus["text"]) if not stats else None
            bonuses.append({**bonus, **({"stats": stats} if stats else {"reason": reason}),
                            **({"situational": True} if reason and reason.startswith("Situational") else {})})
        definitions[key] = {"key": key, "name": row["name"], "bonuses": bonuses}
        for identifier in row["members"]:
            members[identifier].append(key)
    # Some classes have multiple sets with similar names. Only an unambiguous
    # exact membership can activate a threshold in a loadout.
    return definitions, {i: groups[0] for i, groups in members.items() if len(groups) == 1}


def resolve_spell_leads(rows: list[dict], set_members: dict | None = None) -> dict[str, dict]:
    """Reuse a verified description only for the exact spell, trigger and item cooldown."""
    texts = defaultdict(set)
    for row in rows:
        if not row.get("effects_known"):
            continue
        for trigger in ("chance on hit:", "equip:", "use:"):
            leads = [s for s in row.get("effect_leads", []) if s.lower().startswith(trigger)]
            labels = {s.split(' "', 1)[0] for s in row.get("effects", []) if s.lower().startswith(trigger)}
            if len(leads) == len(labels) == 1:
                texts[leads[0]].update(labels)
    resolved = {}
    for row in rows:
        set_key = (set_members or {}).get(row["id"])
        if set_key:
            row = {**row, "set_key": set_key, "effects": list(dict.fromkeys([*row.get("effects", []), "Set bonuses"]))}
        if row.get("effect_leads") and not row.get("effects_known"):
            missing, effects = [], list(row.get("effects", []))
            for lead in row["effect_leads"]:
                if set_key and lead.startswith("Set: "):
                    continue
                if len(texts.get(lead, ())) == 1:
                    label = next(iter(texts[lead]))
                    if label not in effects:
                        effects.append(label)
                else:
                    missing.append(lead)
            row = {**row, "effects": effects, "effects_known": not missing, "missing_effects": missing}
        resolved[str(row["id"])] = row
    return resolved


def catalog_coverage(data: dict) -> dict:
    """Count scored effects separately from recognized text and list every outstanding item."""
    fields = data["item_fields"]
    counts, by_kind, pending = Counter(), defaultdict(Counter), {}
    for key, packed in sorted(data["items"].items()):
        item = dict(zip(fields, packed))
        rules = {label: rule for rule in item.get("effect_rules") or []
                 for label in (rule["label"], *rule.get("aliases", []))}
        for label in item.get("effects") or []:
            if label == "Set bonuses" and (group := data.get("effect_sets", {}).get(item.get("set_key"))):
                for bonus in group["bonuses"]:
                    status = "threshold_stats" if bonus.get("stats") else "situational" if bonus.get("situational") else "unresolved"
                    counts[status] += 1
                    by_kind["set_bonus"][status] += 1
                    if bonus.get("reason"):
                        pending.setdefault(key, []).append({"effect": f"{bonus['pieces']}-piece {group['name']} · {bonus['text']}",
                                                           "spell_id": bonus["spell_id"], "reason": bonus["reason"]})
                continue
            rule = rules.get(label, {})
            if label in rule.get("aliases", []):
                continue
            reason = data["effect_gaps"].get(label)
            if rule.get("rates") or rule.get("kind") == "passive_stats":
                status = "family_estimate" if rule.get("family") else "item_mechanics"
            else:
                status = "situational" if rule.get("kind") == "situational" else "unresolved"
            kind = rule.get("kind") or classify(label)
            counts[status] += 1
            by_kind[kind][status] += 1
            if status in {"situational", "unresolved"}:
                pending.setdefault(key, []).append({"effect": label, "reason": reason,
                    **({"spell_id": rule["spell_id"]} if rule.get("spell_id") else {})})
        for lead in item.get("missing_effects") or []:
            counts["missing_description"] += 1
            by_kind["set_bonus" if lead.startswith("Set:") else "spell_link"]["missing_description"] += 1
            pending.setdefault(key, []).append({"effect": lead, "reason": "Missing verified Forever effect description"})
    return {"catalog_identities": len(data["items"]), "counts": dict(counts),
            "by_mechanic": dict(by_kind), "items_requiring_context_or_evidence": pending}


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
        parsed = {s: r for r in attach_rules({**item, "effects": list(lines)}).get("effect_rules", [])
                  for s in (r["label"], *r.get("aliases", []))}
        for label, facts in lines.items():
            kind = "set_bonus" if facts.get("type") == "set_bonus" else classify(label)
            accounted = (kind == "permanent_stat" or (facts.get("type") == "passive" and facts.get("stats"))
                         or facts.get("spell_id") in reviewed_sets)
            status = "accounted" if accounted else (
                "situational" if kind == "travel" else "needs_evidence")
            rule = parsed.get(label)
            if rule and (rule.get("rates") or rule["kind"] == "passive_stats"):
                status = "family_estimate" if rule.get("family") else "item_mechanics"
            elif rule and rule["kind"] == "situational":
                status = "situational"
            elif kind == "set_bonus" and set_stat(label.partition(" · ")[2]):
                status = "threshold_stats"
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
            if rule:
                group["rule"] = {k: v for k, v in rule.items() if k not in {"rates", "uptimes"}}
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
