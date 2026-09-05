"""Content progression is independent of any particular TBC release calendar."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import re
from typing import Any

from tools.project import PHASE_KEYS, canonical_json
from tools.sources import item_has_pre_raid_route, phase_rank


def resolve_source_content(text: str, definitions: dict, terminology: str = "wowhead_classic") -> str | None:
    """Named content wins over source-specific historical phase numbering."""
    normalized = text.lower()
    for phase in definitions.get("phases", []):
        if any(re.search(rf"\b{re.escape(term)}\b", normalized)
               for term in phase.get("source_terms", [])):
            return phase["key"]
    numbers = re.findall(r"\bphase\s+(\d+(?:\.\d+)?)(?![\d.])", normalized)
    mapping = definitions.get("source_phase_numbers", {}).get(terminology, {})
    mapped = {mapping[number] for number in numbers if number in mapping}
    return next(iter(mapped)) if len(mapped) == 1 else None


def classify_pre_raid_refresh(snapshot: dict, previous: dict, target: str,
                             definitions: dict | None = None, terminology: str | None = None) -> dict:
    """A new fetch date alone does not establish a new progression path."""
    refreshed = deepcopy(snapshot)
    refreshed["content_phase"] = target
    headings = " ".join(str(table.get("heading", "")) for table in snapshot.get("tables", []))
    source_phases = set(re.findall(r"\bPhase\s+(\d+(?:\.\d+)?)\b", headings, re.IGNORECASE))
    definitions = canonical_json("phases") if definitions is None else definitions
    terminology = terminology or snapshot.get("content_terminology", "wowhead_classic")
    mapping = definitions.get("source_phase_numbers", {}).get(terminology, {})
    # "Pre-Raid" describes the recommendation family here, not the release
    # whose accessible content the article covers. Named raid content still
    # takes precedence over a publisher's phase numbering.
    named_phases = {phase["key"] for phase in definitions.get("phases", []) if phase.get("key") != "PR"
                    and any(re.search(rf"\b{re.escape(term)}\b", headings, re.IGNORECASE)
                            for term in phase.get("source_terms", []))}
    observed = named_phases or {mapping.get(number) for number in source_phases}
    if snapshot.get("tables") == previous.get("tables"):
        refreshed["recommendation_status"] = "no_distinct_update"
    elif observed == {target}:
        refreshed["recommendation_status"] = "verified_phase_update"
    else:
        refreshed["recommendation_status"] = "unverified_phase"
    if previous.get("recommendation_status") in {"no_distinct_update", "unverified_phase"}:
        refreshed["previous_verified_phase"] = previous.get("previous_verified_phase", "PR")
    else:
        refreshed["previous_verified_phase"] = previous.get("content_phase", "PR")
    return refreshed


def current_phase(phases: dict[str, Any], now: int) -> str:
    schedule = phases.get("schedules", {}).get(phases.get("active_schedule"), {})
    starts = schedule.get("phase_starts", phases.get("phases", []))
    epochs = {row["key"]: row.get("starts_at_epoch") for row in starts}
    return next((key for key in reversed(PHASE_KEYS)
                 if isinstance(epochs.get(key), int) and epochs[key] <= now), "PR")


def validate_schedules(definitions: dict) -> list[str]:
    errors = []
    schedules = definitions.get("schedules", {})
    if definitions.get("active_schedule") not in schedules:
        errors.append("Unknown active content schedule")
    for phase in definitions.get("phases", []):
        if "starts_at" in phase or "starts_at_epoch" in phase:
            errors.append(f"Stable phase {phase.get('key')} must not contain release dates")
    for schedule_id, schedule in schedules.items():
        previous_rank, previous_epoch = -1, -1
        for start in schedule.get("phase_starts", []):
            key, epoch = start.get("key"), start.get("starts_at_epoch")
            if key not in PHASE_KEYS or phase_rank(key) <= previous_rank:
                errors.append(f"Schedule {schedule_id} has unknown, duplicate, or unordered phase {key}")
            if not isinstance(epoch, int) or isinstance(epoch, bool) or epoch < 0 or epoch <= previous_epoch:
                errors.append(f"Schedule {schedule_id}/{key} has invalid or unordered epoch")
            else:
                previous_epoch = epoch
            previous_rank = phase_rank(key)
            stamp = start.get("starts_at")
            if stamp:
                try:
                    if not stamp.endswith("Z") or int(datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp()) != epoch:
                        raise ValueError("UTC mismatch")
                except (AttributeError, TypeError, ValueError):
                    errors.append(f"Schedule {schedule_id}/{key} UTC timestamp does not match its epoch")
    return errors


def expand_pre_raid_paths(rows: list[dict], items: dict[int, dict]) -> list[dict]:
    """Keep explicit historical paths; inherit only from earlier evidence."""
    result = [row for row in rows if row["phase"] != "PR"]
    by_spec: dict[tuple[str, str], dict[str, list[dict]]] = {}
    for row in rows:
        if row["phase"] == "PR" and not row.get("inherited_from_phase"):
            key = (row["class"], row["spec"])
            by_spec.setdefault(key, {}).setdefault(row.get("content_phase", "PR"), []).append(row)
    for key in sorted(by_spec):
        explicit = by_spec[key]
        for phase in PHASE_KEYS:
            origin = next((candidate for candidate in reversed(PHASE_KEYS[:phase_rank(phase) + 1])
                           if candidate in explicit), None)
            if origin is None:
                raise ValueError(f"No earlier Pre-Raid evidence for {key}/{phase}")
            for original in explicit[origin]:
                row = deepcopy(original)
                row["content_phase"] = phase
                if origin != phase:
                    row["inherited_from_phase"] = origin
                row["items"] = [entry for entry in row["items"]
                                if item_has_pre_raid_route(items.get(entry["item_id"], {}), phase)]
                if row["items"]:
                    result.append(row)
    return result


def validate_pre_raid_paths(rows: list[dict], items: dict[int, dict], specs: list[tuple[str, str]]) -> list[str]:
    errors = []
    present = set()
    verified: dict[tuple[str, str], set[str]] = {}
    for row in rows:
        if row.get("phase") != "PR":
            continue
        phase = row.get("content_phase")
        spec = row.get("class"), row.get("spec")
        if phase not in PHASE_KEYS:
            errors.append(f"Pre-Raid {spec} missing valid content_phase")
            continue
        present.add((*spec, phase))
        if not row.get("inherited_from_phase"):
            verified.setdefault(spec, set()).add(phase)
        for entry in row.get("items", []):
            if not item_has_pre_raid_route(items.get(entry.get("item_id"), {}), phase):
                errors.append(f"Pre-Raid {spec}/{phase} item {entry.get('item_id')} has no eligible non-raid route")
    for spec in specs:
        for phase in PHASE_KEYS:
            if (*spec, phase) not in present:
                errors.append(f"Missing Pre-Raid coverage: {spec}/{phase}")
    for row in rows:
        origin = row.get("inherited_from_phase")
        if row.get("phase") != "PR" or not origin:
            continue
        phase = row.get("content_phase")
        spec = row.get("class"), row.get("spec")
        candidates = [candidate for candidate in verified.get(spec, set()) if phase_rank(candidate) < phase_rank(phase)]
        nearest = max(candidates, key=phase_rank) if candidates else None
        if origin != nearest:
            errors.append(f"Pre-Raid {spec}/{phase} must inherit nearest earlier verified path {nearest}, not {origin}")
    return errors
