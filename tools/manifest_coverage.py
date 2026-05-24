from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from tools.project import PHASE_KEYS, canonical_json

MATRIX_FAMILIES = ["bis_lists", "gems", "enchants", "consumables", "leveling"]
GLOBAL_FAMILIES = ["classes", "phases"]
STATIC_DATA_FAMILIES = MATRIX_FAMILIES + GLOBAL_FAMILIES


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def stable_manifest_id(data_family: str, class_name: str | None = None, spec_name: str | None = None, phase: str | None = None) -> str:
    parts = [data_family]
    if class_name:
        parts.append(class_name)
    if spec_name:
        parts.append(spec_name)
    if phase:
        parts.append(phase)
    return slugify("-".join(parts))


def class_spec_pairs() -> list[dict[str, str]]:
    pairs: list[dict[str, str]] = []
    for class_data in canonical_json("classes").get("classes", []):
        class_name = class_data.get("name")
        for spec in class_data.get("specs", []):
            spec_name = spec.get("name")
            if class_name and spec_name:
                pairs.append({"class": class_name, "spec": spec_name})
    return pairs


def expected_manifest_units(family_filter: str | None = None) -> list[dict[str, str]]:
    units: list[dict[str, str]] = []
    for pair in class_spec_pairs():
        for data_family in MATRIX_FAMILIES:
            for phase in PHASE_KEYS:
                units.append(
                    {
                        "id": stable_manifest_id(data_family, pair["class"], pair["spec"], phase),
                        "data_family": data_family,
                        "class": pair["class"],
                        "spec": pair["spec"],
                        "phase": phase,
                    }
                )

    for data_family in GLOBAL_FAMILIES:
        units.append(
            {
                "id": stable_manifest_id(data_family),
                "data_family": data_family,
            }
        )
    if family_filter:
        return [unit for unit in units if unit["data_family"] == family_filter]
    return units


def unit_key(unit: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(unit.get("data_family") or ""),
        str(unit.get("class") or ""),
        str(unit.get("spec") or ""),
        str(unit.get("phase") or ""),
    )


def _source_families(source: dict[str, Any]) -> list[str]:
    families = source.get("data_families")
    if isinstance(families, list):
        return [str(family) for family in families if family]
    family = source.get("data_family")
    return [str(family)] if family else []


def _source_phases(source: dict[str, Any]) -> list[str]:
    phases = source.get("phases")
    if phases == "*" or source.get("phase") == "*" or source.get("scope") == "all_phases":
        return list(PHASE_KEYS)
    if isinstance(phases, list):
        return [str(phase) for phase in phases if phase in PHASE_KEYS]
    phase = source.get("phase")
    if phase in PHASE_KEYS:
        return [str(phase)]
    return []


def units_covered_by_source(source: dict[str, Any]) -> list[dict[str, str]]:
    units: list[dict[str, str]] = []
    for data_family in _source_families(source):
        if data_family in GLOBAL_FAMILIES:
            units.append({"data_family": data_family})
            continue
        if data_family not in MATRIX_FAMILIES:
            continue
        class_name = source.get("class")
        spec_name = source.get("spec")
        if not class_name or not spec_name:
            continue
        for phase in _source_phases(source):
            units.append(
                {
                    "data_family": data_family,
                    "class": str(class_name),
                    "spec": str(spec_name),
                    "phase": phase,
                }
            )
    return units


def build_manifest_coverage(
    manifest: dict[str, Any] | None = None,
    include_missing: bool = True,
    family_filter: str | None = None,
) -> dict[str, Any]:
    manifest = manifest or canonical_json("scrape_manifest")
    expected_units = expected_manifest_units(family_filter)
    expected_by_key = {unit_key(unit): unit for unit in expected_units}
    source_ids_by_unit: dict[tuple[str, str, str, str], list[str]] = defaultdict(list)
    unexpected_sources: list[dict[str, str]] = []

    for source in manifest.get("sources", []):
        source_id = str(source.get("id") or source.get("url") or "<missing id>")
        covered_units = units_covered_by_source(source)
        if not covered_units:
            unexpected_sources.append(
                {
                    "id": source_id,
                    "data_family": str(source.get("data_family") or source.get("data_families") or ""),
                    "url": str(source.get("url") or ""),
                }
            )
            continue
        for covered_unit in covered_units:
            key = unit_key(covered_unit)
            if key in expected_by_key:
                source_ids_by_unit[key].append(source_id)
            elif not family_filter:
                unexpected_sources.append(
                    {
                        "id": source_id,
                        "data_family": covered_unit["data_family"],
                        "class": covered_unit.get("class", ""),
                        "spec": covered_unit.get("spec", ""),
                        "phase": covered_unit.get("phase", ""),
                        "url": str(source.get("url") or ""),
                    }
                )

    missing_units = [unit for unit in expected_units if unit_key(unit) not in source_ids_by_unit]
    duplicate_units = [
        {
            **expected_by_key[key],
            "source_ids": source_ids,
        }
        for key, source_ids in sorted(source_ids_by_unit.items())
        if len(source_ids) > 1
    ]

    expected_by_family: dict[str, int] = {family: 0 for family in STATIC_DATA_FAMILIES}
    present_by_family: dict[str, int] = {family: 0 for family in STATIC_DATA_FAMILIES}
    missing_by_family: dict[str, int] = {family: 0 for family in STATIC_DATA_FAMILIES}
    for unit in expected_units:
        expected_by_family[unit["data_family"]] += 1
    for key in source_ids_by_unit:
        present_by_family[key[0]] += 1
    for unit in missing_units:
        missing_by_family[unit["data_family"]] += 1

    report: dict[str, Any] = {
        "ok": not missing_units and not duplicate_units and not unexpected_sources,
        "expected_units": len(expected_units),
        "present_units": len(source_ids_by_unit),
        "missing_units": len(missing_units),
        "duplicate_units": len(duplicate_units),
        "unexpected_sources": unexpected_sources,
        "by_family": {
            family: {
                "expected": expected_by_family[family],
                "present": present_by_family[family],
                "missing": missing_by_family[family],
            }
            for family in STATIC_DATA_FAMILIES
        },
        "notes": [
            "Matrix families require explicit coverage for each class/spec/phase unit.",
            "A manifest source may cover multiple phases by using phases or scope=all_phases; coverage is still counted per phase.",
            "Item and spell acquisition pages are discovered from registered guide snapshots and audited after snapshots exist.",
        ],
    }
    if family_filter:
        report["family"] = family_filter
    if include_missing:
        report["missing"] = missing_units
    if duplicate_units:
        report["duplicates"] = duplicate_units
    return report
