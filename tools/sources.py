from __future__ import annotations

from copy import deepcopy
from typing import Any

SOURCE_TYPE_PRIORITY = {
    "drop": 0,
    "token_turnin": 1,
    "quest": 2,
    "vendor": 3,
    "crafted": 4,
    "pvp": 5,
    "world_drop": 6,
    "unknown": 99,
}


def _source_sort_key(source: dict[str, Any]) -> tuple:
    drop_percent = source.get("drop_percent")
    drop_rank = -float(drop_percent) if isinstance(drop_percent, (int, float)) else 0.0
    return (
        SOURCE_TYPE_PRIORITY.get(str(source.get("type", "unknown")), 99),
        drop_rank,
        str(source.get("entity_name") or ""),
        str(source.get("zone") or ""),
        int(source.get("quest_id") or source.get("vendor_id") or source.get("entity_id") or 0),
    )


def derive_primary_source(sources: list[dict[str, Any]]) -> dict[str, Any]:
    if not sources:
        return {"type": "unknown", "entity_name": "Unknown", "confidence": "missing"}
    return deepcopy(sorted(sources, key=_source_sort_key)[0])


def format_costs(costs: list[dict[str, Any]] | None) -> str:
    if not costs:
        return ""

    parts: list[str] = []
    for cost in costs:
        amount = cost.get("amount")
        name = cost.get("name") or cost.get("currency_name") or cost.get("item_name")
        if amount is None and not name:
            continue
        if amount is None:
            parts.append(str(name))
        elif name:
            parts.append(f"{amount} {name}")
        else:
            parts.append(str(amount))
    return ", ".join(parts)


def compact_source(source: dict[str, Any]) -> str:
    source_type = source.get("type")
    entity = source.get("entity_name") or source.get("profession") or "Unknown"
    zone = source.get("zone")
    costs = format_costs(source.get("costs"))

    if source_type == "drop":
        if source.get("world_drop"):
            return "World Drop"
        text = f"Drop: {entity}"
        if zone:
            text += f" ({zone})"
        if isinstance(source.get("drop_percent"), (int, float)):
            text += f" {float(source['drop_percent']):.1f}%"
        return text

    if source_type == "world_drop":
        return "World Drop"

    if source_type == "token_turnin":
        token_sources = source.get("token_sources") or []
        first_token_source = derive_primary_source(token_sources) if token_sources else {}
        token_name = (
            first_token_source.get("token_name")
            or first_token_source.get("token_item_name")
            or next((cost.get("name") for cost in source.get("costs", []) if cost.get("item_id")), None)
            or "Token"
        )
        text = f"Token: {token_name}"
        token_entity = first_token_source.get("entity_name")
        token_zone = first_token_source.get("zone")
        if token_entity:
            text += f" - {token_entity}"
            if token_zone:
                text += f" ({token_zone})"
            if isinstance(first_token_source.get("drop_percent"), (int, float)):
                text += f" {float(first_token_source['drop_percent']):.1f}%"
        elif source.get("entity_name"):
            text += f" - Turn in to {source['entity_name']}"
        if len(token_sources) > 1:
            text += f" +{len(token_sources) - 1}"
        return text

    if source_type == "quest":
        return f"Quest: {entity}"

    if source_type == "vendor":
        text = f"Vendor: {entity}"
        if costs:
            text += f" ({costs})"
        elif zone:
            text += f" ({zone})"
        return text

    if source_type == "pvp":
        text = f"PvP: {entity}"
        if costs:
            text += f" ({costs})"
        return text

    if source_type == "crafted":
        return f"Crafted: {entity}"

    return str(entity)


def summarize_sources(sources: list[dict[str, Any]]) -> str:
    primary = derive_primary_source(sources)
    text = compact_source(primary)
    extra_count = 0 if primary.get("type") == "token_turnin" else max(0, len(sources) - 1)
    if extra_count:
        text += f" +{extra_count}"
    return text
