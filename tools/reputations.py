from __future__ import annotations

import re
from copy import deepcopy
from typing import Any


CANONICAL_REPUTATIONS = (
    "Ashtongue Deathsworn",
    "Cenarion Circle",
    "Cenarion Expedition",
    "Honor Hold",
    "Keepers of Time",
    "Kurenai",
    "Lower City",
    "Netherwing",
    "Ogri'la",
    "Shattered Sun Offensive",
    "The Aldor",
    "The Consortium",
    "The Mag'har",
    "The Scale of the Sands",
    "The Scryers",
    "The Sha'tar",
    "The Violet Eye",
    "Thrallmar",
)


def _key(value: str) -> str:
    cleaned = str(value or "").replace("’", "'").replace("`", "'")
    cleaned = re.sub(r"\s+", " ", cleaned).strip().lower()
    return cleaned


_CANONICAL_BY_KEY = {_key(name): name for name in CANONICAL_REPUTATIONS}

_ALIASES = {
    "classic - cenarion circle": ("Cenarion Circle",),
    "honor hold / thrallmar": ("Honor Hold", "Thrallmar"),
    "thrallmar / honor hold": ("Thrallmar", "Honor Hold"),
    "honor hold / thrallmar (boe": ("Honor Hold", "Thrallmar"),
    "keepers of time": ("Keepers of Time",),
    "the keepers of time": ("Keepers of Time",),
    "kurenai": ("Kurenai",),
    "the kurenai": ("Kurenai",),
    "scale of the sands": ("The Scale of the Sands",),
    "the scale of the sands": ("The Scale of the Sands",),
    "the scales of the sand": ("The Scale of the Sands",),
    "the mag'har / kurenai": ("The Mag'har", "Kurenai"),
    "the maghar / kurenai": ("The Mag'har", "Kurenai"),
    "the shat'tar": ("The Sha'tar",),
}


def _clean_part(value: str) -> str:
    cleaned = str(value or "").replace("’", "'").replace("`", "'")
    cleaned = re.sub(r"\s*\([^)]*$", "", cleaned)
    cleaned = re.sub(r"^classic\s*-\s*", "", cleaned, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", cleaned).strip(" .:-()")


def normalize_reputation_names(value: str | None) -> list[str]:
    raw = _clean_part(str(value or ""))
    if not raw:
        return []

    exact = _ALIASES.get(_key(raw))
    if exact:
        return list(dict.fromkeys(exact))

    names: list[str] = []
    for part in re.split(r"\s*/\s*", raw):
        cleaned = _clean_part(part)
        if not cleaned:
            continue
        key = _key(cleaned)
        if key in _ALIASES:
            canonical = _ALIASES[key]
        elif key in _CANONICAL_BY_KEY:
            canonical = (_CANONICAL_BY_KEY[key],)
        else:
            canonical = (cleaned,)
        for name in canonical:
            if name not in names:
                names.append(name)
    return names


def _requirement_key(requirement: dict[str, Any]) -> tuple[Any, ...]:
    return (
        requirement.get("type"),
        requirement.get("scope"),
        requirement.get("source_url"),
        requirement.get("confidence"),
        requirement.get("reputation"),
        requirement.get("standing"),
        requirement.get("standing_rank"),
        requirement.get("profession"),
        requirement.get("skill"),
        requirement.get("specialization"),
        requirement.get("spell_id"),
        tuple(requirement.get("choices") or []),
        requirement.get("raw_text") if requirement.get("type") not in {"reputation", "faction_choice"} else None,
    )


def normalize_requirement(requirement: dict[str, Any]) -> list[dict[str, Any]]:
    if requirement.get("type") == "reputation":
        names = normalize_reputation_names(requirement.get("reputation"))
        if not names:
            return [requirement]
        normalized = []
        for name in names:
            item = deepcopy(requirement)
            item["reputation"] = name
            normalized.append(item)
        return normalized

    if requirement.get("type") == "faction_choice":
        choices: list[str] = []
        for choice in requirement.get("choices") or []:
            for name in normalize_reputation_names(choice):
                if name not in choices:
                    choices.append(name)
        if choices:
            item = deepcopy(requirement)
            item["choices"] = choices
            return [item]

    return [requirement]


def normalize_requirements(requirements: list[dict[str, Any]] | None) -> list[dict[str, Any]] | None:
    if requirements is None:
        return None

    normalized: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for requirement in requirements:
        if not isinstance(requirement, dict):
            normalized.append(requirement)
            continue
        for item in normalize_requirement(requirement):
            key = _requirement_key(item)
            if key in seen:
                continue
            seen.add(key)
            normalized.append(item)
    return normalized
