"""Compile ordinary-target item effects and their encounter estimates before packaging."""
from __future__ import annotations

import math
import re
from functools import lru_cache

from tools.project import dataset_json


@lru_cache(maxsize=1)
def policy() -> dict:
    return dataset_json("forever", "effect_benchmarks")


@lru_cache(maxsize=1)
def presets() -> tuple[dict, ...]:
    data = policy()
    rows = tuple(dict(zip(data["fields"], row, strict=True), index=i) for i, row in enumerate(data["presets"], 1))
    expected = {(role, mode) for role in ("caster", "healer", "melee", "ranged", "tank")
                for mode in ("leveling", "pre_raid")}
    if len(rows) != len(expected) or {(r["role"], r["mode"]) for r in rows} != expected:
        raise ValueError("Missing or duplicate Forever effect benchmark")
    for row in rows:
        for field in data["fields"][2:]:
            if not math.isfinite(row[field]) or row[field] < 0:
                raise ValueError(f"Invalid Forever effect benchmark {field}")
        if row["swing_seconds"] <= 0 or any(row[k] > 1 for k in (
                "melee", "ranged", "use_fraction", "physical", "magic", "useful_healing", "periodic_fraction")):
            raise ValueError("Invalid Forever encounter fraction or attack period")
    modes = ("leveling", "pre_raid")
    for row in rows:
        row["helpful_casts"] = data["helpful_casts"].get(row["role"], (0, 0))[modes.index(row["mode"])]
    contexts = list(rows)
    for spec, (role, leveling, pre_raid) in sorted(data["hybrid_harmful_casts"].items()):
        for mode, casts in zip(modes, (leveling, pre_raid)):
            base = next(r for r in rows if r["mode"] == mode and r["role"] == role)
            if not math.isfinite(casts) or casts < 0:
                raise ValueError(f"Invalid hybrid cast rate for {spec}")
            contexts.append({**base, "spec": spec, "casts": casts, "index": len(contexts) + 1})
    return tuple(contexts)


def preset(role: str, mode: str, spec: str | None = None) -> dict:
    variant = spec if spec in policy()["hybrid_harmful_casts"] else None
    return next(row for row in presets() if row["role"] == role and row["mode"] == mode and row.get("spec") == variant)


AMOUNT = r"(\d+)(?: to (\d+))?"
SCHOOL = r"(Physical|Fire|Frost|Nature|Shadow|Arcane|Holyfire|Holy)"
DAMAGE = re.compile(AMOUNT + r"(?: total)? " + SCHOOL + r" damage\b", re.I)
DIRECT = re.compile(r"(?:Blasts? |Sends? |Deal|Rend earth and stone|Hurl|Discipline |Pummel |Smite |Fire[ s]|Strike |"
                    r"Launch|Venom Shot|Ignite the target|Delivers a fatal wound|Flick the lighter|Calls down a meteor|"
                    r"Creates a mobile bomb|Flings a magical boomerang|Chance on hit to |Chance to strike |"
                    r"Grants a chance on striking |Melee and Ranged attacks have a chance|Chance on harmful spell cast|"
                    r"Harmful spell casts sear|When struck in combat|Melee attacks with this weapon deal)", re.I)
COOLDOWN = re.compile(r"\((?:(\d+) Hours?,? ?)?(?:(\d+) Min,? ?)?(?:(\d+) Sec)?\s*Cooldown\)", re.I)
TARGET_BONUS = re.compile(r"(?:Deals?|Restore) (\d+) times as much(?: damage)? (?:to|against) ([^.]+)|"
                          r"Damage is (doubled|tripled) against ([^.]+)|([A-Za-z ]+) targets take (\d+)x damage", re.I)
TIMED_STATS = {
    "attack power": "attack_power", "spell power": "spell_power", "armor": "armor", "defense": "defense",
    "attack speed": "haste_percent", "melee attack speed": "haste_percent", "stamina": "stamina",
    "spirit": "spirit", "strength": "strength", "agility": "agility", "intellect": "intellect",
    "damage and healing done by magical spells and effects": "spell_power", "healing done by spells and effects": "healing_power",
    "damage of your spells and effects": "spell_power", "spell damage and healing": "spell_power",
}


def average(low: str, high: str | None) -> float:
    return (int(low) + int(high or low)) / 2


def extra_rule(label: str) -> dict | None:
    """Only match mechanics with an identifiable recipient, trigger and quantity."""
    text = label.split(' "', 1)[0]
    trigger, _, body = text.partition(": ")
    if trigger not in {"Chance on hit", "Equip", "Use"} or not body or re.search(r"\b\d+ Charges?\b", body, re.I):
        return None
    event = "weapon_hit"
    rule = {}
    if (re.match(r"Silences an enemy|Stuns? (?:an enemy|the target|your target)|Immune to Disarm|"
                 r"Reduces the hit chance of (?:Fear|Silence|Sleep) effects against you|"
                 r"Increases the (?:duration of your Sprint|speed of your Ghost Wolf) ability|"
                 r"Reduces the duration of all movement impairing effects", body, re.I)
            and not re.search(r"damage|heals|attack power|restores", body, re.I)):
        return {"kind": "situational", "trigger": {"Equip": "equip", "Use": "use"}.get(trigger, "weapon_hit")}
    if trigger == "Equip":
        passives = (
            (r"Increases your chance to Block attacks with a shield by ([\d.]+)%\.", "block_percent"),
            (r"Increases your attack speed and casting speed by ([\d.]+)%\.", "haste_percent"),
            (r"Increases damage and healing done by magical spells and effects by up to (\d+)\.", "spell_power"),
            (r"Improves your chance to hit by ([\d.]+)%\.", "hit_percent"),
            (r"Increases spell damage and healing by up to (\d+)\. Grants an additional \d+ spell damage against Demons\.", "spell_power"),
        )
        for pattern, stat in passives:
            if match := re.fullmatch(pattern, body, re.I):
                return {"kind": "passive_stats", "trigger": "equip", "stats": {stat: float(match[1])},
                        **({"secondary": True} if "additional" in body else {})}
        if match := re.fullmatch(
                r"Increases healing done by (?:spells and effects by )?up to (\d+) and "
                r"damage done by (?:spells and effects by )?up to (\d+)(?: for all magical spells and effects)?\.", body, re.I):
            return {"kind": "passive_stats", "trigger": "equip", "stats": {"healing_power": int(match[1]), "spell_damage": int(match[2])}}
        if match := re.fullmatch(r"\+(\d+) Attack Power in Cat, Bear, and Dire Bear forms only\.", body):
            return {"kind": "passive_stats", "trigger": "equip", "stats": {"attack_power": int(match[1])}, "requires_form": True}
        if re.match(r"(?:\+\d+ (?:Ranged )?Attack Power against |Increases damage done to (?:Undead|Demons|Beasts|Elementals|Dragonkin) by |"
                    r"Increases your damage against |Reduces all damage taken from players|Increases? (?:mount|movement) speed|Run speed increased|"
                    r"Increased (?:Mining|Skinning|Fishing)|Increases your effective stealth|Underwater Breath|Reduces damage from falling|"
                    r"Reduces (?:your damage taken|all damage taken and chance to be critically hit) in )", body, re.I):
            return {"kind": "situational", "trigger": "equip"}
    if trigger == "Use":
        if re.match(r"Allows you to look far|Weakens the servants|Slice open and gather|Finds the nearest treasure|Conjures food", body, re.I):
            return {"kind": "situational", "trigger": "use"}
        cd = COOLDOWN.search(body)
        if not cd:
            return None
        rule["cooldown"] = sum(int(value or 0) * factor for value, factor in zip(cd.groups(), (3600, 60, 1)))
        if not rule["cooldown"]:
            return None
        body, event = body[:cd.start()].strip(), "use"
        if re.match(r"Dispels? (?:all |Polymorph|Charm|Fear)|Creates? a portal|Returns you to |Gives invisibility|"
                    r"Reduces your fall speed|Removes (?:existing Immobilizing|all movement impairing)|Purifies the friendly|"
                    r"Jumper Cables|Grants water breathing|Stuns target|Increases? (?:your )?run speed", body, re.I):
            return {"kind": "situational", "trigger": "use"}
    if trigger == "Equip":
        if "when struck" in body.lower() or "who strikes you" in body.lower():
            event = "struck"
        elif re.search(r"successful spellcast", body, re.I):
            event = "spell_cast"
        elif re.search(r"harmful spell", body, re.I):
            event = "spell_hit"
        elif "ranged target" in body.lower():
            event = "ranged_hit"
        elif re.search(r"melee and ranged attacks", body, re.I):
            event = "attack_hit"
        if match := re.search(r"\(Proc chance: (\d+(?:\.\d+)?)%", body, re.I):
            rule["chance"] = float(match[1]) / 100
        if match := re.search(r"(\d+)(ms|s) cooldown\)", body, re.I):
            rule["cooldown"] = int(match[1]) / (1000 if match[2].lower() == "ms" else 1)
        if event == "struck" and not re.search(r"\bchance\b", body, re.I):
            rule["chance"] = 1
        if body.startswith(("Melee attacks with this weapon deal ", "Harmful spell casts sear ")):
            rule["chance"] = 1
    rule["trigger"] = event
    if bonus := TARGET_BONUS.search(body):
        rule["bonus_targets"] = (bonus[2] or bonus[4] or bonus[5]).strip()
        rule["bonus_multiplier"] = int(bonus[1] or bonus[6] or (3 if bonus[3].lower() == "tripled" else 2))
    if match := re.match(r"(\d+)% chance when struck in melee to gain a holy shield, absorbing (\d+) damage for \d+ sec\.", body, re.I):
        return {**rule, "kind": "instant", "trigger": "struck", "chance": int(match[1]) / 100,
                "amounts": {"proc_hps": int(match[2])}, "secondary": True}
    if match := re.match(r"When struck has a (\d+)% chance of stealing (\d+) life from the attacker over \d+ sec\.", body, re.I):
        return {**rule, "kind": "damage", "trigger": "struck", "chance": int(match[1]) / 100, "amount": int(match[2]),
                "school": "shadow", "periodic": True, "leech": True}
    if match := re.match(r"(\d+)% chance on Melee hit to gain (\d+) extra attacks?\.", body, re.I):
        return {**rule, "kind": "extra_attack", "count": int(match[2]), "chance": int(match[1]) / 100,
                **({"secondary": True} if "against" in body.casefold() else {})}
    if match := re.match(r"Attacks have a chance to grant (\d+) extra attacks?.*?(\d+) times as likely", body, re.I):
        if "chance" in rule:
            return {**rule, "kind": "extra_attack", "count": int(match[1]), "chance": rule["chance"] / int(match[2])}
    if trigger == "Use":
        if match := re.match(r"(?:Heal(?:s)? (?:yourself|your target|a friendly target) for|Absorbs?) " + AMOUNT +
                             r"(?: (?:physical )?damage)?\.(?: Lasts \d+ sec\.| Usable while Silenced\.)?$", body, re.I):
            return {**rule, "kind": "instant", "amounts": {"proc_hps": average(*match.groups())}}
        if match := re.match(r"Restores " + AMOUNT + r" (health|mana)(?: every (\d+) sec for (\d+) sec| over \d+ sec)?\."
                             r"(?: This effect is doubled in [^.]+\.)?$", body, re.I):
            amount = average(match[1], match[2]) * (int(match[5]) // int(match[4]) if match[4] else 1)
            return {**rule, "kind": "instant", "amounts": ({"mp5": 5 * amount} if match[3].lower() == "mana"
                                                            else {"proc_hps": amount})}
    if match := re.search(r"(?:Increases? (?:your |the )?|increasing (?:your )?)([A-Za-z ]+?) by (?:up to )?"
                          r"(\d+)%? for (\d+) sec\b", body, re.I):
        stat = TIMED_STATS.get(match[1].casefold())
        if stat and (trigger != "Equip" or "chance" in rule or event == "spell_hit") and not re.search(
                r"thorny shield|your target|the target's|reduces? your|stacking up to", body, re.I):
            return {**rule, "kind": "timed_stats", "stats": {stat: int(match[2])}, "duration": int(match[3])}
    if trigger == "Chance on hit" and (match := re.match(r"Restores (\d+) mana\.", body, re.I)):
        return {**rule, "kind": "instant", "amounts": {"mp5": 5 * int(match[1])}, "secondary": True}
    if match := re.match(r"(?:Wounds the target causing them to bleed for|Corrupts the target, causing) (\d+) damage over (\d+) sec\.", body, re.I):
        return {**rule, "kind": "damage", "amount": int(match[1]), "school": "bleed" if "bleed" in body else "shadow",
                "periodic": True}
    match = DAMAGE.search(body)
    if match and (DIRECT.match(body) or re.match(r"Poisons target|Inflicts \d+|Drains target", body, re.I)):
        if re.search(r"unless it explodes|damage to you or|reducing your own|thorny shield|Inflict \d+ Fire and", body, re.I):
            return None
        amount = average(match[1], match[2])
        after = body[match.end():]
        ticks = re.search(r"every (\d+) sec.*?(?:for|Lasts for) (\d+) sec", after, re.I)
        if ticks:
            amount *= int(ticks[2]) // int(ticks[1])
            rule["periodic"] = True
        elif "every " in after.lower():
            return None
        elif re.match(r" over \d+ sec", after, re.I):
            rule["periodic"] = True
        if part := re.search(r"and an additional (\d+) damage over \d+ sec", after, re.I):
            rule["periodic_amount"] = int(part[1])
        if re.search(r"\b(stun|slow|disarm|resistance|interrupt|jump|heal|transfers|additional nearby|below)\w*", after, re.I):
            rule["secondary"] = True
        return {**rule, "kind": "damage", "amount": amount, "school": match[3].casefold()}
    if trigger == "Chance on hit" and (match := re.match(r"Wounds the target for " + AMOUNT + r" damage[. ]", body, re.I)):
        return {**rule, "kind": "damage", "amount": average(*match.groups()), "school": "physical",
                **({"secondary": True} if body.count(".") > 1 or " and " in body else {})}
    return None


def missing_reason(label: str) -> str:
    lower = label.casefold()
    if lower == "set bonuses":
        return "Set membership and active bonus thresholds"
    if re.search(r"\b\d+ charges?\b", lower):
        return "Limited charges and replacement or recharge frequency"
    if re.search(r"mount speed|run speed|swim|stealth|fall|teleport|portal|water breathing|fishing|skinning|mining", lower):
        return "Situational movement, travel or profession utility"
    if re.search(r"dispel|stun|charm|fear|silence|disarm|immobil|interrupt|polymorph|invisib", lower):
        return "Situational control or encounter-specific prevention"
    if re.search(r"against|to undead|to demons|while in|wasteland|per piece|while equipped|only works", lower):
        return "Requires a specific target, location or equipment condition"
    if label.startswith("Use:"):
        return "Use frequency, effective benefit or activation conditions"
    if label.startswith("Chance on hit:") or "chance" in lower:
        return "Trigger rate, eligible events or effective result"
    return "Ability interaction or stat conversion"


def compile_rule(rule: dict, item: dict) -> dict:
    """Store the effective rates and timed uptime for each distinct role/activity preset."""
    rule = dict(rule)
    if rule["kind"] in {"passive_stats", "situational"}:
        return rule
    if rule["kind"] == "mana_cost":
        rule["trigger"] = "mana_spend"
        return rule
    event = rule["trigger"]
    speed = (item.get("stats") or {}).get("weapon_speed") or item.get("weapon_speed")
    is_weapon = bool(item.get("weapon_subtype") and speed)
    ranged = item.get("slot") == "Ranged"
    chance, ppm = rule.get("chance"), rule.get("ppm")
    if chance is None and ppm is None and event not in {"use", "block"}:
        family = policy()["family_rates"]
        if rule["kind"] == "extra_attack" and event == "weapon_hit":
            chance, rule["family"] = family["extra_attack_chance"], "extra attack"
        elif rule["kind"] == "damage" and event in {"weapon_hit", "ranged_hit"} and is_weapon:
            ppm, rule["family"] = family["weapon_damage_ppm"], "weapon damage"
        elif rule["kind"] == "damage" and event in {"weapon_hit", "ranged_hit", "attack_hit"}:
            chance, rule["family"] = family["accessory_damage_chance"], "damage on striking"
        elif rule["kind"] == "timed_stats" and event == "spell_hit" and "spell_power" in rule["stats"]:
            chance, rule["family"] = family["spell_buff_chance"], "spell power on cast"
        else:
            return rule
    if ppm is not None:
        rule["nominal_ppm"] = ppm
    elif chance is not None:
        rule["benchmark_chance"] = chance
    if event == "use" and item.get("slot") == "Trinket":
        rule["use_lockout"] = max(rule.get("shared_cooldown", policy()["shared_trinket_seconds"]), rule.get("duration", 0))
    rates, uptimes = [], []
    for row in presets():
        period = speed if is_weapon else row["swing_seconds"]
        if event == "use":
            rate = 60 * row["use_fraction"] / rule["cooldown"]
        else:
            events = (row["blocks"] if event == "block" else row["struck"] if event == "struck" else
                      row["casts"] if event == "spell_hit" else row["casts"] + row["helpful_casts"] if event == "spell_cast" else
                      60 * (row["ranged"] + row["melee"]) / period if event == "attack_hit" else
                      60 * row["ranged" if ranged or event == "ranged_hit" else "melee"] / period)
            rate = events * (min(1, ppm * period / 60) if ppm is not None else chance if chance is not None else 1)
            if rule.get("cooldown"):
                rate /= 1 + rate * rule["cooldown"] / 60
        rates.append(round(rate, 8))
        if rule["kind"] == "timed_stats":
            duration = rule["duration"]
            uptime = (min(1, rate * duration / 60) if rule.get("cooldown", 0) >= duration
                      else -math.expm1(-rate * duration / 60))
            uptimes.append(round(uptime, 8))
    rule["rates"] = rates
    if uptimes:
        rule["uptimes"] = uptimes
    return rule
