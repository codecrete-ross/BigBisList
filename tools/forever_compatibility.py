"""Verify the exact mechanics and random-property scopes shared by client builds."""
from __future__ import annotations

from tools.project import ROOT, dataset_json, load_json


MECHANICS_FIELDS = ("traits", "enchants", "flat_sets", "racial_scaling", "ability_triggers")


def roll_scope(catalog: dict) -> dict:
    families = []
    for row in catalog["items"]:
        item = dict(zip(catalog["fields"], row))
        group = item.pop("group", None)
        if group:
            families.append([item, sorted(catalog["groups"][group - 1])])
    return {"templates": catalog["templates"], "families": families}


def supported_builds(snapshot: dict | None = None, catalog: dict | None = None) -> list[int]:
    from tools.forever import digest
    from tools.forever_mechanics import snapshot_path

    proof = dataset_json("forever", "runtime_compatibility")
    if snapshot is not None:
        source = {key: snapshot.get(key) for key in MECHANICS_FIELDS}
        if snapshot["client_build"] != proof["mechanics_source_build"] or digest(source) != proof["mechanics_digest"]:
            raise ValueError("Recheck target-client compatibility after changing scoring mechanics")
        target = load_json(snapshot_path(proof["target_mechanics_url"]))
        if target["client_build"] != proof["target_client"] or source != {key: target.get(key) for key in MECHANICS_FIELDS}:
            raise ValueError("Target client has different talent, enchant, set or racial mechanics")
    if catalog is not None:
        target = load_json(ROOT / proof["target_roll_snapshot"])
        scope = roll_scope(catalog)
        original = {row[0]: dict(zip(catalog["fields"], row)).get("classes") for row in catalog["items"]}
        restrictions = {str(row[0]): item["classes"] for row in target["items"]
                        if (item := dict(zip(target["fields"], row))).get("classes")
                        and item["classes"] != original.get(row[0])}
        if (digest(target) != proof["target_catalog_digest"]
                or catalog["client_build"] != proof["roll_source_build"] or digest(scope) != proof["roll_digest"]
                or scope != roll_scope(target) or target["client_build"] != proof["target_client"]
                or restrictions != proof["class_restrictions"]):
            raise ValueError("Recheck target-client random-property compatibility")
    return [int(proof["target_client"].rsplit(".", 1)[1])]


def target_class_restrictions() -> dict:
    return dataset_json("forever", "runtime_compatibility")["class_restrictions"]
