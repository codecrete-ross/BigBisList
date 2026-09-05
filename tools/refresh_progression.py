"""Refresh registered endgame evidence without overwriting historical Pre-Raid guides."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.project import PHASE_KEYS, RAW_WOWHEAD_DIR, canonical_json, write_text
from tools.progression import classify_pre_raid_refresh
from tools.scrape_wowhead import (
    fetch_normalized_snapshot, load_snapshots, manifest_urls, snapshot_name,
    discover_entity_urls, discover_token_item_urls, discover_related_source_urls,
    html_cache_name, parse_item_tooltip_endpoint, parse_spell_tooltip_endpoint,
    manifest_sources_by_url,
)

FAMILIES = {"bis_lists": "full_bis", "gems": "full_gems",
            "enchants": "full_enchants", "consumables": "full_consumables"}


def frozen_pre_raid_snapshot(snapshot: dict) -> dict:
    """Keep source identity with the evidence when a manifest URL later changes."""
    frozen = deepcopy(snapshot)
    frozen.setdefault("content_phase", "PR")
    frozen["historical_pre_raid"] = True
    if not frozen.get("manifest_bindings"):
        frozen["manifest_bindings"] = deepcopy(manifest_sources_by_url().get(snapshot.get("url"), []))
    return frozen


def archive_verified_pre_raid(path: Path, snapshot: dict | None = None) -> Path | None:
    """Archive verified paths; preserve superseded revisions outside active imports."""
    previous = snapshot if snapshot is not None else json.loads(path.read_text(encoding="utf-8"))
    if previous.get("page_type") != "guide" or previous.get("recommendation_status") in {"no_distinct_update", "unverified_phase"}:
        return None
    frozen = frozen_pre_raid_snapshot(previous)
    archive = path.with_stem(path.stem + "--pr-" + frozen["content_phase"])
    if archive.exists():
        original = json.loads(archive.read_text(encoding="utf-8"))
        original_frozen = frozen_pre_raid_snapshot(original)
        if original_frozen.get("tables") == frozen.get("tables") and original_frozen.get("recommendation_status") not in {"no_distinct_update", "unverified_phase"}:
            if original != original_frozen:
                write_text(archive, json.dumps(original_frozen, indent=2, sort_keys=True) + "\n")
            return archive
        # An invalid first capture must not occupy this phase forever. Keep
        # its evidence, and every superseded verified revision, in history.
        serialized = json.dumps(original_frozen, indent=2, sort_keys=True) + "\n"
        digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]
        history = archive.parent / "history" / f"{archive.stem}--{digest}.json"
        if not history.exists():
            write_text(history, serialized)
        if original_frozen.get("recommendation_status") not in {"no_distinct_update", "unverified_phase"} and str(original_frozen.get("fetched_at", "")) > str(frozen.get("fetched_at", "")):
            serialized = json.dumps(frozen, indent=2, sort_keys=True) + "\n"
            digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]
            write_text(archive.parent / "history" / f"{archive.stem}--{digest}.json", serialized)
            return archive
    write_text(archive, json.dumps(frozen, indent=2, sort_keys=True) + "\n")
    return archive


def reprocess_dependencies() -> int:
    """Reparse saved public tooltip payloads without changing capture dates."""
    count = 0
    cache_dirs = sorted((RAW_WOWHEAD_DIR / "html_cache").glob("refresh-*"), reverse=True)
    for path in sorted((RAW_WOWHEAD_DIR / "progression_items").glob("*.json")):
        original = json.loads(path.read_text(encoding="utf-8"))
        if original.get("fetch_method") != "tooltip_endpoint" and original.get("item_stats", {}).get("parse_confidence") != "tooltip_endpoint":
            continue
        kind = original["page_type"]
        endpoint = f"https://nether.wowhead.com/tbc/tooltip/{kind}/{original[kind + '_id']}"
        cached = next((directory / html_cache_name(endpoint) for directory in cache_dirs
                       if (directory / html_cache_name(endpoint)).is_file()), None)
        if cached is None:
            raise ValueError(f"Missing cached endpoint for {original['url']}")
        parser = parse_item_tooltip_endpoint if kind == "item" else parse_spell_tooltip_endpoint
        refreshed = parser(original["url"], cached.read_text(encoding="utf-8"))
        refreshed["fetched_at"] = original["fetched_at"]
        write_text(path, json.dumps(refreshed, indent=2, sort_keys=True) + "\n")
        count += 1
    return count


def refresh(content_phase: str, dependencies: bool = False) -> dict:
    run_date = datetime.now(timezone.utc).date().isoformat()
    cache = RAW_WOWHEAD_DIR / "html_cache" / ("refresh-" + run_date)
    report_path = RAW_WOWHEAD_DIR / "refresh_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8")) if dependencies and report_path.exists() else {
        "content_phase": content_phase, "started_at": datetime.now(timezone.utc).isoformat(),
        "guides": [], "dependencies": [], "failures": [],
    }
    if not dependencies:
        destinations: dict[str, list[str]] = {}
        for family, directory in FAMILIES.items():
            for url in manifest_urls(family):
                destinations.setdefault(url, []).append(directory)
        for url, directories in destinations.items():
            if "pre-raid" not in url:
                continue
            for directory in directories:
                path = RAW_WOWHEAD_DIR / directory / snapshot_name(url)
                if path.exists():
                    archive_verified_pre_raid(path)
        jobs = sorted(destinations)
    else:
        snapshots = [snap for directory in set(FAMILIES.values())
                     for snap in load_snapshots(RAW_WOWHEAD_DIR / directory)]
        snapshots.extend(load_snapshots(RAW_WOWHEAD_DIR / "progression_items"))
        jobs = sorted(set(discover_entity_urls(snapshots) + discover_token_item_urls(snapshots)
                          + discover_related_source_urls(snapshots)))
        done = {entry["url"] for entry in report["dependencies"]}
        jobs = [url for url in jobs if url not in done]
        destinations = {url: ["progression_items"] for url in jobs}
    output = RAW_WOWHEAD_DIR / ("progression_items" if dependencies else "refresh_staging")
    results_key = "dependencies" if dependencies else "guides"
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {executor.submit(fetch_normalized_snapshot, url, cache, output,
                                   retries=1, delay=0.5): url for url in jobs}
        for number, future in enumerate(as_completed(futures), 1):
            url = futures[future]
            try:
                snapshot = future.result()
                if not dependencies:
                    if snapshot.get("page_type") != "guide" or not snapshot.get("tables"):
                        raise ValueError("Guide did not produce parsed tables")
                    if "pre-raid" in url:
                        old_path = RAW_WOWHEAD_DIR / destinations[url][0] / snapshot_name(url)
                        previous = json.loads(old_path.read_text(encoding="utf-8")) if old_path.exists() else {}
                        bindings = manifest_sources_by_url().get(url, [])
                        terminology = {binding.get("content_terminology", "wowhead_classic") for binding in bindings
                                       if binding.get("phase") == "PR"}
                        if len(terminology) > 1:
                            raise ValueError(f"Conflicting Pre-Raid source terminology for {url}")
                        snapshot["content_terminology"] = next(iter(terminology), "wowhead_classic")
                        snapshot = classify_pre_raid_refresh(snapshot, previous, content_phase,
                                                           terminology=snapshot["content_terminology"])
                        snapshot = frozen_pre_raid_snapshot(snapshot)
                for directory in destinations[url]:
                    destination = RAW_WOWHEAD_DIR / directory / snapshot_name(url)
                    if not dependencies and "pre-raid" in url:
                        archive_verified_pre_raid(destination, snapshot)
                    write_text(destination,
                               json.dumps(snapshot, indent=2, sort_keys=True) + "\n")
                report[results_key].append({"url": url, "fetched_at": snapshot.get("fetched_at"),
                                           "page_type": snapshot.get("page_type"),
                                           "fetch_method": snapshot.get("fetch_method", "page"),
                                           "acquisition_tables": bool(snapshot.get("normalized_sources")),
                                           "tables": len(snapshot.get("tables", []))})
                report["failures"] = [failure for failure in report["failures"] if failure["url"] != url]
            except Exception as exc:
                report["failures"].append({"url": url, "stage": results_key, "error": str(exc)})
            if number % 20 == 0 or number == len(jobs):
                write_text(report_path, json.dumps(report, indent=2, sort_keys=True) + "\n")
                print(f"{results_key}: {number}/{len(jobs)}; failures: {len(report['failures'])}", flush=True)
    write_text(report_path, json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--content-phase", choices=PHASE_KEYS, required=True)
    parser.add_argument("--dependencies", action="store_true")
    parser.add_argument("--reprocess", action="store_true")
    args = parser.parse_args()
    if args.reprocess:
        print(f"Reprocessed {reprocess_dependencies()} cached dependency snapshots")
        return 0
    report = refresh(args.content_phase, args.dependencies)
    return 1 if report["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
