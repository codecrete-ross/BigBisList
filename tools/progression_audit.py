"""Audit endgame recommendation coverage and acquisition evidence without writes.

Successful retrieval, verified phase guidance, and unchanged/general fallback
recommendations are separate facts.  The report contains no generated timestamp
and is deterministic for a given canonical/evidence tree.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import json
from pathlib import Path
import re
import sys
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.project import PHASE_KEYS
from tools.sources import item_has_pre_raid_route, source_is_phase_available


ROOT = Path(__file__).resolve().parents[1]
FAMILIES = ("bis_lists", "gems", "enchants", "consumables")
ROW_KEYS = {"bis_lists": "lists", "gems": "gems", "enchants": "enchants", "consumables": "consumables"}
SOURCE_CHILDREN = ("recipe_sources", "token_sources", "quest_starter_sources")
BAD_PHASE_UPDATES = {"no_distinct_update", "unverified_phase"}


def _read(path: Path, default: Any = None) -> Any:
    if not path.is_file():
        return deepcopy(default)
    return json.loads(path.read_text(encoding="utf-8"))


def _stable(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _entity_key(url: str) -> tuple[str, int] | None:
    match = re.search(r"/(item|spell)(?:=|%3[Dd])(\d+)", url)
    return (match[1], int(match[2])) if match else None


def _row_entities(family: str, row: dict) -> set[tuple[str, int]]:
    if family == "bis_lists":
        return {("item", entry["item_id"]) for entry in row.get("items", []) if isinstance(entry.get("item_id"), int)}
    if family == "consumables":
        return {("item", item_id) for item_id in row.get("items", []) if isinstance(item_id, int)}
    return {(row.get("type", "item") if family == "enchants" else "item", row["id"])} if isinstance(row.get("id"), int) else set()


def _family_registered(source: dict, family: str) -> bool:
    return source.get("data_family") == family or family in source.get("data_families", [])


def _covers_phase(source: dict, phase: str) -> bool:
    phases = source.get("phases")
    return source.get("phase") == phase or phases == "*" or isinstance(phases, list) and phase in phases


def _has_rankings(snapshot: dict, family: str) -> bool:
    if family == "gems" and snapshot.get("page_type") == "phase_gem_guide":
        return any(entry.get("gem_ids") for entry in snapshot.get("gem_guidance", []))
    if family == "enchants" and snapshot.get("page_type") == "phase_enchant_guide":
        return any(entry.get("applications") for entry in snapshot.get("enchant_guidance", []))
    for container, child_key in (("tables", "rows"), ("sections", "entries")):
        for section in snapshot.get(container, []):
            if section.get("data_family") == family and section.get(child_key):
                return True
    return False


def _bis_evidence_item_ids(snapshot: dict) -> set[int]:
    ids = set()
    for table in snapshot.get("tables", []):
        if table.get("data_family") != "bis_lists":
            continue
        for row in table.get("rows", []):
            if isinstance(row.get("item_id"), int):
                ids.add(row["item_id"])
            # A guide cell may contain both faction alternatives. Both remain
            # historical evidence even when only one is the row's primary ID.
            ids.update(entity["id"] for entity in row.get("entities", [])
                       if entity.get("type") == "item" and isinstance(entity.get("id"), int))
    return ids


def _pre_raid_evidence(evidence: dict, manifest: list[dict]) -> tuple[dict, dict]:
    """Resolve frozen identities and choose the importer's newest spec/phase path."""
    from tools.scrape_wowhead import manifest_source_urls, stable_json_sort_key

    by_url: dict[str, list[dict]] = defaultdict(list)
    for source in manifest:
        for url in manifest_source_urls(source):
            by_url[url].append(source)
    observations: dict[tuple[str, str], list[dict]] = defaultdict(list)
    winners: dict[tuple[str, str, str], tuple[tuple[str, str], dict]] = {}
    for snapshots in evidence["guides"].values():
        for snapshot in snapshots:
            bindings = snapshot.get("manifest_bindings") if snapshot.get("historical_pre_raid") else None
            if not bindings:
                bindings = by_url.get(snapshot.get("url"), [])
            bound_specs = {(str(source.get("class")), str(source.get("spec"))) for source in bindings
                           if source.get("phase") == "PR" and _family_registered(source, "bis_lists")}
            # The importer's tie-break compares the original normalized payload;
            # audit-only path annotations must not influence which revision wins.
            rank = (str(snapshot.get("fetched_at", "")),
                    stable_json_sort_key({key: value for key, value in snapshot.items() if key != "snapshot_path"}))
            for spec in bound_specs:
                observations[spec].append(snapshot)
                if snapshot.get("recommendation_status") in BAD_PHASE_UPDATES:
                    continue
                key = (*spec, str(snapshot.get("content_phase", "PR")))
                if key not in winners or rank > winners[key][0]:
                    winners[key] = (rank, snapshot)
    selected: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for (cls, spec, _), (_, snapshot) in sorted(winners.items()):
        if _has_rankings(snapshot, "bis_lists"):
            selected[(cls, spec)].append(snapshot)
    return observations, selected


def _source_walk(sources: list[dict]):
    for source in sources:
        if not isinstance(source, dict):
            continue
        yield source
        for key in SOURCE_CHILDREN:
            yield from _source_walk(source.get(key, []))


def _concrete_route(entity: dict | None, entities: dict, phase: str | None = None,
                    seen: frozenset[tuple[str, int]] = frozenset()) -> bool:
    if not entity:
        return False
    for source in entity.get("sources", []):
        if phase and not source_is_phase_available(source, phase):
            continue
        source_type = source.get("type")
        if source_type in {None, "unknown"}:
            continue
        if source_type == "taught_by_item":
            key = ("item", source.get("item_id", source.get("entity_id")))
            if key not in seen and _concrete_route(entities.get(key), entities, phase, seen | {key}):
                return True
            continue
        if source_type == "token_turnin" and not source.get("token_sources"):
            costs = [cost for cost in source.get("costs", []) if isinstance(cost.get("item_id"), int)]
            if costs and not all(("item", cost["item_id"]) not in seen and _concrete_route(
                    entities.get(("item", cost["item_id"])), entities, phase, seen | {("item", cost["item_id"])})
                                 for cost in costs):
                continue
        missing_child = False
        for child_key in SOURCE_CHILDREN:
            if child_key in source and source[child_key] and not _concrete_route(
                    {"sources": source[child_key]}, entities, phase, seen):
                missing_child = True
                break
        if not missing_child:
            return True
    return False


def _merge_entity(existing: dict | None, incoming: dict) -> dict:
    if not existing:
        return deepcopy(incoming)
    result = deepcopy(existing)
    for field, value in incoming.items():
        if field != "sources" and field not in result:
            result[field] = deepcopy(value)
    known = {_stable(source) for source in result.get("sources", [])}
    for source in incoming.get("sources", []):
        if _stable(source) not in known:
            result.setdefault("sources", []).append(deepcopy(source))
            known.add(_stable(source))
    return result


def _load_evidence(raw_dir: Path, required_entities: set[tuple[str, int]]) -> dict:
    guides: dict[str, list[dict]] = defaultdict(list)
    items: dict[tuple[str, int], list[dict]] = defaultdict(list)
    phase_gems = []
    phase_enchants = []
    parse_errors = []
    directories = sorted({*raw_dir.glob("full_*"), raw_dir / "progression_items", raw_dir / "phase_gems", raw_dir / "phase_enchants"})
    for directory in directories:
        for path in sorted(directory.glob("*.json")):
            snapshot = _read(path, {})
            kind = snapshot.get("page_type")
            relative = "data/raw/wowhead/" + path.relative_to(raw_dir).as_posix()
            if kind == "guide":
                guides[snapshot.get("url", "")].append({**snapshot, "snapshot_path": relative})
            elif kind == "phase_gem_guide":
                phase_gems.append({**snapshot, "snapshot_path": relative})
                parse_errors.extend({"snapshot_path": relative, **error} for error in snapshot.get("parse_errors", []))
            elif kind == "phase_enchant_guide":
                phase_enchants.append({**snapshot, "snapshot_path": relative})
                parse_errors.extend({"snapshot_path": relative, "data_family": "enchants", **error}
                                    for error in snapshot.get("parse_errors", []))
            elif kind in {"item", "spell"}:
                entity_id = snapshot.get(kind + "_id")
                key = (kind, entity_id)
                if key in required_entities:
                    # Keep acquisition evidence, not unused leveling stats or
                    # complete related tables from the large shared corpus.
                    items[key].append({
                        "snapshot_path": relative, "url": snapshot.get("url", ""),
                        "fetched_at": snapshot.get("fetched_at", ""),
                        "has_routes": bool(snapshot.get("normalized_sources")),
                        "route_count": len(snapshot.get("normalized_sources", [])),
                        "tooltip_only": snapshot.get("fetch_method") == "tooltip_endpoint" or
                                        snapshot.get("item_stats", {}).get("parse_confidence") == "tooltip_endpoint",
                        "fresh_dependency_directory": directory.name == "progression_items",
                    })
    # Identical guides exist in both full_gems and full_enchants. Keep each
    # evidence path visible, but a duplicate does not count as another refresh.
    return {"guides": guides, "entities": items, "phase_gems": phase_gems,
            "phase_enchants": phase_enchants, "parse_errors": parse_errors}


def _phase_enchant_audit(evidence: dict, entities: dict, canonical_enchants: dict) -> dict:
    if not evidence["phase_enchants"]:
        return {"coverage": [], "parse_errors": [], "complete_phase_guidance": False}
    from tools.phase_enchants import build_phase_enchant_audit
    # Evaluate the committed guide applications against the effective canonical
    # routes which the player will receive. This preserves learned-spell aliases
    # and reviewed formula gates without re-reading the large shared corpus.
    source_snapshots = []
    for (kind, entity_id), record in sorted(entities.items()):
        snapshot = {"page_type": kind, kind + "_id": entity_id, "name": record.get("name", ""),
                    "url": record.get("source_url") or record.get("wowhead_url") or f"https://www.wowhead.com/tbc/{kind}={entity_id}",
                    "fetched_at": "", "normalized_sources": deepcopy(record.get("sources", [])),
                    "normalized_requirements": deepcopy(record.get("requirements", []))}
        for field in ("binding", "boe", "tradeable"):
            if field in record:
                snapshot[field] = record[field]
        source_snapshots.append(snapshot)
    result = build_phase_enchant_audit(source_snapshots + evidence["phase_enchants"], canonical_enchants)
    result["acquisition_basis"] = "effective_canonical_routes_and_committed_phase_guide_applications"
    return result


def _refresh_status(urls: list[str], refresh: dict) -> tuple[str, list[dict]]:
    entries = [entry for entry in refresh.get("guides", []) if entry.get("url") in urls]
    comparisons = [{key: entry[key] for key in ("url", "ranking_changed", "baseline_ref", "ranking_before_sha256", "ranking_after_sha256")
                    if key in entry} for entry in entries]
    if entries:
        changes = [entry.get("ranking_changed") for entry in entries]
        status = "refreshed_changed" if any(value is True for value in changes) else (
            "refreshed_unchanged" if all(value is False for value in changes) else "refreshed_change_unrecorded")
    elif any(failure.get("stage") == "guides" and failure.get("url") in urls for failure in refresh.get("failures", [])):
        status = "refresh_failed_retained_evidence"
    else:
        status = "retained_evidence_not_refreshed"
    return status, sorted(comparisons, key=_stable)


def build_progression_audit(canonical_dir: Path | None = None, raw_dir: Path | None = None,
                            *, expected_spec_count: int = 28, reviewed_sources: dict | None = None) -> dict:
    canonical_dir = canonical_dir or ROOT / "data/canonical"
    raw_dir = raw_dir or ROOT / "data/raw/wowhead"
    documents = {family: _read(canonical_dir / (family + ".json"), {}) for family in FAMILIES}
    rows_by_family = {family: documents[family].get(ROW_KEYS[family], []) for family in FAMILIES}
    classes = _read(canonical_dir / "classes.json", {}).get("classes", [])
    specs = sorted((cls["name"], spec["name"]) for cls in classes for spec in cls.get("specs", []))
    manifest = _read(canonical_dir / "scrape_manifest.json", {}).get("sources", [])
    refresh = _read(raw_dir / "refresh_report.json", {})
    errors: list[dict] = []
    warnings: list[dict] = []

    def issue(code: str, message: str, *, warning: bool = False, **details):
        (warnings if warning else errors).append({"code": code, "message": message, **details})

    if len(specs) != expected_spec_count or len(set(specs)) != len(specs):
        issue("invalid_spec_registry", "The canonical spec registry must contain every supported spec exactly once.",
              expected=expected_spec_count, actual=len(specs))
    if not refresh:
        issue("missing_refresh_report", "No committed refresh report records the requested source refresh.")
    entities: dict[tuple[str, int], dict] = {}
    for filename, key, default_kind in (("items", "items", "item"), ("gem_sources", "gem_sources", "item"),
                                        ("enchant_sources", "enchant_sources", "item")):
        for entity in _read(canonical_dir / (filename + ".json"), {}).get(key, []):
            identity = (entity.get("type", default_kind) if filename == "enchant_sources" else default_kind, entity["id"])
            entities[identity] = _merge_entity(entities.get(identity), entity)
    references: dict[tuple[str, int], set[tuple]] = defaultdict(set)
    indexed_rows: dict[tuple[str, str, str, str], list[dict]] = defaultdict(list)
    for family, rows in rows_by_family.items():
        for row in rows:
            context = (row.get("class"), row.get("spec"), row.get("phase"), family)
            indexed_rows[context].append(row)
            for entity in _row_entities(family, row):
                references[entity].add(context)
    evidence = _load_evidence(raw_dir, set(references))
    pre_raid_observations, pre_raid_snapshots = _pre_raid_evidence(evidence, manifest)
    phase_enchant_report = _phase_enchant_audit(evidence, entities, documents["enchants"])
    phase_enchant_contexts = {(row["class"], row["spec"], row["phase"]): row for row in phase_enchant_report["coverage"]}
    coverage = []
    for cls, spec in specs:
        for phase in PHASE_KEYS:
            for family in FAMILIES:
                key = (cls, spec, phase, family)
                rows = indexed_rows[key]
                registered = [source for source in manifest if source.get("class") == cls and source.get("spec") == spec
                              and _family_registered(source, family) and _covers_phase(source, phase)]
                urls = sorted({source["url"] for source in registered if source.get("url")})
                snapshots = [snapshot for url in urls for snapshot in evidence["guides"].get(url, [])
                             if _has_rankings(snapshot, family)]
                if family == "bis_lists" and phase == "PR":
                    snapshots = pre_raid_snapshots[(cls, spec)]
                phase_family_snapshots = evidence["phase_gems"] if family == "gems" else evidence["phase_enchants"] if family == "enchants" else []
                phase_guides = [snapshot for snapshot in phase_family_snapshots
                                if snapshot.get("recommendation_status") not in BAD_PHASE_UPDATES
                                and {"class": cls, "spec": spec, "phase": phase} in snapshot.get("bindings", [])
                                and _has_rankings(snapshot, family)]
                generic = bool(registered) and all(source.get("phases") == "*" for source in registered)
                evidence_urls = sorted(set(urls + [snapshot["url"] for snapshot in snapshots + phase_guides]))
                refresh_urls = sorted({snapshot["url"] for snapshot in phase_guides}) if phase_guides else urls
                fresh_status, comparisons = _refresh_status(refresh_urls, refresh)
                if not registered:
                    status = "missing_registered_coverage"
                    issue(status, "The spec/phase/family has no manifest registration.", **dict(zip(("class", "spec", "phase", "family"), key)))
                elif not rows:
                    status = "missing_recommendations"
                    issue(status, "Registered coverage has no canonical recommendations.", **dict(zip(("class", "spec", "phase", "family"), key)))
                elif not snapshots and not phase_guides:
                    status = "missing_ranking_evidence"
                    issue(status, "No committed parsed guide evidence supports the registered family.", **dict(zip(("class", "spec", "phase", "family"), key)))
                elif generic and not phase_guides:
                    status = "general_guide_fallback"
                elif family == "bis_lists" and phase == "PR":
                    status = "phase_scoped_pre_raid_paths"
                elif fresh_status == "refreshed_unchanged":
                    status = "refreshed_unchanged"
                elif fresh_status.startswith("refreshed_"):
                    status = "verified_refreshed_rankings"
                else:
                    status = "retained_phase_specific_evidence"
                ids = set().union(*(_row_entities(family, row) for row in rows)) if rows else set()
                missing = sorted(identity for identity in ids if not _concrete_route(entities.get(identity), entities))
                unavailable = sorted(identity for identity in ids if identity not in missing and not _concrete_route(entities.get(identity), entities, phase))
                if ids and not missing and len(unavailable) == len(ids):
                    issue("empty_phase_available_coverage", "All registered recommendations are unavailable in this phase.",
                          **dict(zip(("class", "spec", "phase", "family"), key)))
                phase_item_ids = sorted({item_id for snapshot in phase_guides for entry in snapshot.get("gem_guidance", []) for item_id in entry.get("gem_ids", [])})
                available_phase_gems = [item_id for item_id in phase_item_ids if ("item", item_id) in ids
                                        and _concrete_route(entities.get(("item", item_id)), entities, phase)]
                enchant_context = phase_enchant_contexts.get((cls, spec, phase), {}) if family == "enchants" else {}
                available_phase_enchants = [entry for entry in enchant_context.get("verified_recommendations", [])
                                           if (entry[1], entry[2]) in ids]
                if phase_guides and generic and not (available_phase_gems or available_phase_enchants):
                    status = "phase_guidance_unavailable_general_fallback"
                elif family == "enchants" and enchant_context.get("status") == "partial_phase_guidance":
                    status = "partial_phase_guidance_with_general_fallback"
                coverage.append({"class": cls, "spec": spec, "phase": phase, "family": family,
                                 "status": status, "refresh_status": fresh_status,
                                 "registration_ids": sorted(source.get("id", "") for source in registered),
                                 "row_count": len(rows), "entity_count": len(ids),
                                 "phase_available_entity_count": len(ids) - len(missing) - len(unavailable),
                                 "missing_acquisition": [{"type": kind, "id": entity_id} for kind, entity_id in missing],
                                 "phase_unavailable_entities": [{"type": kind, "id": entity_id} for kind, entity_id in unavailable],
                                 "source_urls": evidence_urls,
                                 "snapshot_paths": sorted({snapshot["snapshot_path"] for snapshot in snapshots + phase_guides}),
                                 "phase_specific_gem_ids": phase_item_ids,
                                 "available_phase_specific_gem_ids": available_phase_gems,
                                 "general_fallback_gem_ids": sorted(entity_id for kind, entity_id in ids
                                                                    if family == "gems" and entity_id not in available_phase_gems),
                                 "phase_enchant_guidance": enchant_context,
                                 "ranking_comparisons": comparisons})

    pre_raid = []
    for cls, spec in specs:
        registered = [source for source in manifest if source.get("class") == cls and source.get("spec") == spec
                      and _family_registered(source, "bis_lists") and source.get("phase") == "PR"]
        urls = sorted({source["url"] for source in registered if source.get("url")})
        snapshots = pre_raid_snapshots[(cls, spec)]
        observations = pre_raid_observations[(cls, spec)]
        explicit = {snapshot.get("content_phase", "PR") for snapshot in snapshots}
        valid_registered = {phase for source in registered for phase in source.get("content_phases", [])}
        rows = indexed_rows[(cls, spec, "PR", "bis_lists")]
        for row in rows:
            if row.get("content_phase") not in PHASE_KEYS:
                issue("invalid_pre_raid_context", "Pre-Raid recommendations require a stable content_phase.",
                      **{"class": cls, "spec": spec}, slot=row.get("slot"), content_phase=row.get("content_phase"))
        for phase in PHASE_KEYS:
            context_rows = [row for row in rows if row.get("content_phase") == phase]
            candidates = [candidate for candidate in PHASE_KEYS[:PHASE_KEYS.index(phase) + 1] if candidate in explicit]
            nearest = candidates[-1] if candidates else None
            inherited = sorted({row.get("inherited_from_phase") for row in context_rows if row.get("inherited_from_phase")})
            expected_origin = None if nearest == phase else nearest
            ids = set().union(*(_row_entities("bis_lists", row) for row in context_rows)) if context_rows else set()
            ineligible = sorted(entity_id for _, entity_id in ids if not item_has_pre_raid_route(entities.get(("item", entity_id), {}), phase))
            details = {"class": cls, "spec": spec, "content_phase": phase}
            if phase not in valid_registered:
                issue("missing_pre_raid_registration", "The manifest does not register this Pre-Raid content context.", **details)
            if not context_rows or not ids:
                issue("missing_pre_raid_coverage", "The Pre-Raid context has no eligible recommendations.", **details)
            if nearest is None:
                issue("missing_pre_raid_evidence", "No verified same-phase or earlier Pre-Raid snapshot exists.", **details)
            if any(row.get("inherited_from_phase") != expected_origin for row in context_rows):
                issue("invalid_pre_raid_inheritance", "Pre-Raid must use its own verified snapshot or inherit the nearest earlier verified path.",
                      **details, expected_origin=expected_origin, actual_origins=inherited)
            if expected_origin and not any(source.get("inheritance_policy") == "nearest_earlier_verified" for source in registered):
                issue("unapproved_pre_raid_inheritance", "The manifest does not authorize nearest-earlier Pre-Raid inheritance.", **details)
            if ineligible:
                issue("ineligible_pre_raid_routes", "Included Pre-Raid items require a route without personal raid participation.", **details, item_ids=ineligible)
            selected_snapshots = [snapshot for snapshot in snapshots if snapshot.get("content_phase", "PR") == nearest]
            origin_items = set().union(*(_bis_evidence_item_ids(snapshot) for snapshot in selected_snapshots)) if selected_snapshots else set()
            unsupported = sorted(entity_id for _, entity_id in ids if entity_id not in origin_items)
            if expected_origin and unsupported:
                issue("invalid_pre_raid_lineage", "Inherited items must occur in the selected earlier snapshot; later lists cannot backfill it.",
                      **details, inherited_from_phase=expected_origin, item_ids=unsupported)
            fresh_observations = sorted({(snapshot.get("content_phase", "PR"), snapshot.get("recommendation_status", "verified_historical"))
                                         for snapshot in observations if snapshot.get("recommendation_status")})
            pre_raid.append({**details, "status": "missing_evidence" if nearest is None else "inherited_earlier_verified_path" if expected_origin else "verified_phase_path",
                             "inherited_from_phase": expected_origin, "row_count": len(context_rows),
                             "entity_count": len(ids), "eligible_entity_count": len(ids) - len(ineligible),
                             "ineligible_item_ids": ineligible,
                             "source_urls": sorted({snapshot["url"] for snapshot in selected_snapshots}),
                             "registered_source_urls": urls,
                             "unsupported_inherited_item_ids": unsupported if expected_origin else [],
                             "snapshot_paths": sorted({snapshot["snapshot_path"] for snapshot in selected_snapshots}),
                             "refresh_observations": [{"content_phase": content, "status": status} for content, status in fresh_observations]})

    acquisition = []
    refreshed_entity_ids = {_entity_key(entry.get("url", "")) for entry in refresh.get("dependencies", [])}
    failed_entity_ids = {_entity_key(entry.get("url", "")) for entry in refresh.get("failures", [])}
    for identity in sorted(references):
        kind, entity_id = identity
        entity = entities.get(identity)
        observations = evidence["entities"].get(identity, [])
        latest = max(observations, key=lambda item: (item["fetched_at"], item["snapshot_path"])) if observations else None
        rich = sorted((item for item in observations if item["has_routes"]), key=lambda item: (item["fetched_at"], item["snapshot_path"]))
        reviewed = bool(entity and any(source.get("reviewed_override_id") or source.get("confidence") in {"reviewed_override", "manual_review"}
                                      for source in _source_walk(entity.get("sources", []))))
        concrete = _concrete_route(entity, entities)
        if not entity:
            status = "missing_canonical_entity"
        elif not concrete:
            status = "missing_acquisition_evidence"
        elif identity in refreshed_entity_ids and latest:
            if latest["has_routes"] and not latest["tooltip_only"]:
                status = "refreshed_item_page_acquisition"
            elif rich:
                status = "tooltip_refreshed_with_retained_routes" if latest["tooltip_only"] else "refreshed_without_tables_retained_routes"
            elif reviewed:
                status = "tooltip_refreshed_with_reviewed_routes" if latest["tooltip_only"] else "refreshed_with_reviewed_routes"
            else:
                status = "refreshed_without_acquisition_tables"
        elif identity in failed_entity_ids:
            status = "refresh_failed_retained_acquisition"
        elif rich:
            status = "retained_item_page_acquisition"
        elif reviewed:
            status = "reviewed_acquisition_evidence"
        else:
            status = "guide_acquisition_fallback"
        if status.startswith("missing_"):
            issue(status, "An included recommendation lacks required canonical acquisition data.", entity_type=kind, entity_id=entity_id,
                  families=sorted({context[3] for context in references[identity]}))
        acquisition.append({"type": kind, "id": entity_id, "name": entity.get("name") if entity else None,
                            "status": status, "reviewed_corrections": reviewed,
                            "recommendation_context_count": len(references[identity]),
                            "families": sorted({context[3] for context in references[identity]}),
                            "latest_snapshot": latest,
                            "retained_rich_snapshot": rich[-1] if rich and (not latest or rich[-1] != latest) else None})
    for error in evidence["parse_errors"]:
        issue("phase_enhancement_parse_error", "A published phase-specific enhancement loadout could not be decoded.", **error)
    if refresh.get("failures"):
        issue("incomplete_source_refresh", "Some fresh source requests failed; retained evidence is reported separately.",
              warning=True, failures=sorted(refresh["failures"], key=_stable))
    if reviewed_sources is None:
        from tools.phase_source_overrides import source_review_audit
        reviewed_sources = source_review_audit()
    errors = sorted({_stable(error): error for error in errors}.values(), key=_stable)
    warnings = sorted({_stable(warning): warning for warning in warnings}.values(), key=_stable)
    return {
        "schema_version": 1,
        "policy": {"phases": list(PHASE_KEYS), "expected_specs": expected_spec_count,
                   "general_guide_fallback_allowed": True, "pre_raid_inheritance": "nearest_earlier_verified",
                   "fresh_retrieval_is_not_verified_ranking_change": True,
                   "acquisition_freshness_is_separate_from_retained_validity": True},
        "refresh_content_phase": refresh.get("content_phase"),
        "refresh_capture_summary": {
            "evidence_path": "data/raw/wowhead/refresh_report.json",
            "guide_url_count": len({entry.get("url") for entry in refresh.get("guides", [])}),
            "guide_comparison_counts": dict(sorted(Counter(
                "changed" if entry.get("ranking_changed") is True else "unchanged" if entry.get("ranking_changed") is False else "unrecorded"
                for entry in refresh.get("guides", [])).items())),
            "dependency_url_count": len({entry.get("url") for entry in refresh.get("dependencies", [])}),
            "dependency_fetch_method_counts": dict(sorted(Counter(entry.get("fetch_method", "unrecorded")
                                                                  for entry in refresh.get("dependencies", [])).items())),
            "dependencies_with_fresh_acquisition_tables": sum(entry.get("acquisition_tables") is True
                                                             for entry in refresh.get("dependencies", [])),
            "failed_requests": sorted(refresh.get("failures", []), key=_stable),
        },
        "summary": {"passed": not errors, "spec_count": len(specs), "coverage_context_count": len(coverage),
                    "pre_raid_context_count": len(pre_raid), "error_count": len(errors), "warning_count": len(warnings),
                    "coverage_status_counts": dict(sorted(Counter(row["status"] for row in coverage).items())),
                    "pre_raid_status_counts": dict(sorted(Counter(row["status"] for row in pre_raid).items())),
                    "acquisition_status_counts": dict(sorted(Counter(row["status"] for row in acquisition).items()))},
        "coverage": coverage, "pre_raid": pre_raid, "acquisition": acquisition,
        "phase_enchants": phase_enchant_report,
        "reviewed_source_limitations": reviewed_sources, "errors": errors, "warnings": warnings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", nargs="?", const="-", metavar="PATH", help="Write JSON to PATH, or stdout when omitted.")
    parser.add_argument("--check", action="store_true", help="Return nonzero for missing coverage or invalid acquisition/progression.")
    args = parser.parse_args(argv)
    report = build_progression_audit()
    if args.json:
        payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        if args.json == "-":
            print(payload, end="")
        else:
            Path(args.json).write_text(payload, encoding="utf-8")
    else:
        summary = report["summary"]
        print(f"Progression audit: {summary['coverage_context_count']} family contexts, {summary['pre_raid_context_count']} Pre-Raid contexts; "
              f"{summary['error_count']} errors, {summary['warning_count']} warnings")
        for error in report["errors"][:20]:
            print(_stable(error))
    return int(bool(args.check and report["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
