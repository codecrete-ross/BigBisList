"""Normalize exact item and acquisition observations from pinned EG Link exports."""
from __future__ import annotations

import re


PROJECT = "JIVESCORP/eg-link-output-wowf"
HEAD_URL = f"https://api.github.com/repos/{PROJECT}/commits?per_page=1"
ROOT = f"https://raw.githubusercontent.com/{PROJECT}"
DATASETS = ("item_hotfixes.enUS", "quests.enUS", "quest_prerequisites", "quest_scan", "vendors", "trainers", "loot")


def acquisition_ids(rows: dict) -> dict[str, set[int]]:
    entities = {kind: set() for kind in ("quest", "npc", "spell", "object", "item")}
    entities["item"].update(rows)
    for row in rows.values():
        for lead in row.get("route_leads", []):
            kind = lead.get("subject_type", lead.get("entity_type"))
            identifier = lead.get("subject_id", lead.get("entity_id"))
            if kind in entities and type(identifier) is int and identifier > 0:
                entities[kind].add(identifier)
        for fact in row.get("pending_facts", []):
            for url in fact.get("source_urls", []):
                entities["quest"].update(int(q) for q in re.findall(r"(?:quest=|quests/)([1-9]\d*)", url))
    return entities


def normalize(url: str, name: str, payload: dict, build: str, ids: dict, *, collected_at: str, digest: str) -> dict:
    meta = payload["meta"]
    if (meta["product"] != "wowf" or meta["clientBuild"] != build
            or meta["dataset"] != name.split(".", 1)[0] or type(meta["sources"]) is not int or meta["sources"] < 1
            or meta.get("license") != "CC BY 4.0"):
        raise ValueError("EG Link export is not attributed evidence for the reviewed Forever build")
    records, relationships, dependencies = [], [], []

    def edge(kind, subject, relation, item, **facts):
        relationships.append({"relation": relation, "subject_type": kind, "subject_id": subject,
                              "object_type": "item", "object_id": item, "source_url": url,
                              "confidence": "eg_link_observation", **facts})

    if name == "item_hotfixes.enUS":
        items = payload["items"]
        if not isinstance(items, dict):
            raise ValueError("Invalid EG Link item disclosure table")
        for identifier in sorted(ids["item"]):
            item = items.get(str(identifier))
            if item is None:
                continue
            if (not isinstance(item, dict) or item.get("status") not in {"valid", "invalid", "removed"}
                    or type(item.get("pushId")) is not int
                    or type(item.get("sources")) is not int or item["sources"] < 1):
                raise ValueError(f"Invalid EG Link disclosure status for item {identifier}")
            records.append({"kind": "item_disclosure", "item_id": identifier, "state": item["status"],
                            "push_id": item["pushId"], "sources": item["sources"],
                            **{key: item[key] for key in ("name", "description") if item.get(key)}})
    elif name == "quest_scan":
        described = payload["described"]
        if not isinstance(described, dict) or not isinstance(payload["noData"], list):
            raise ValueError("Invalid EG Link quest disclosure table")
        no_data = {int(identifier) for identifier in payload["noData"]}
        for identifier in sorted(ids["quest"]):
            if str(identifier) in described:
                record = described[str(identifier)]
                if not isinstance(record, dict):
                    raise ValueError(f"Invalid EG Link disclosure status for quest {identifier}")
                records.append({"kind": "quest_disclosure", "quest_id": identifier, "state": "described",
                                **{key: record[key] for key in ("title", "sources", "factions", "noDataFactions") if key in record}})
            elif identifier in no_data:
                records.append({"kind": "quest_disclosure", "quest_id": identifier, "state": "no_response"})
    elif name == "quests.enUS":
        for key, quest in payload["quests"].items():
            identifier = int(key)
            rewards = [(item["itemId"], relation) for membership, relation in (("items", "rewards"), ("choices", "reward_choice"))
                       for item in quest.get("rewards", {}).get(membership, []) if item["itemId"] in ids["item"]]
            if rewards or identifier in ids["quest"]:
                records.append({"quest_id": identifier, **quest})
                ids["quest"].add(identifier)
                dependencies.append({"entity_type": "quest", "entity_id": identifier,
                                     **{k: quest[k] for k in ("minLevel", "raceMask", "startItemId", "nextQuestId", "flags",
                                                                "objectives", "rewards") if k in quest}})
                for item, relation in rewards:
                    edge("quest", identifier, relation, item, quest_min_level=quest.get("minLevel"), race_mask=quest.get("raceMask"))
    elif name == "quest_prerequisites":
        for key, quest in payload["quests"].items():
            identifier = int(key)
            if identifier in ids["quest"]:
                records.append({"quest_id": identifier, **quest})
                dependencies.append({"entity_type": "quest", "entity_id": identifier, "prerequisites": quest})
    elif name == "vendors":
        for key, vendor in payload["vendors"].items():
            identifier = int(key)
            for entry in vendor.get("entries", {}).values():
                item = entry.get("itemId")
                if item in ids["item"]:
                    records.append({"npc_id": identifier, "name": vendor.get("name"), **entry})
                    edge("npc", identifier, "sells", item, stock=entry)
    elif name == "trainers":
        for key, trainer in payload["trainers"].items():
            for spell, entry in trainer.get("services", {}).items():
                if int(spell) in ids["spell"]:
                    records.append({"npc_id": int(key), **entry})
                    dependencies.append({"entity_type": "spell", "entity_id": int(spell), "npc_id": int(key), "service": entry})
    elif name == "loot":
        for key, bucket in payload["sources"].items():
            entity = re.fullmatch(r"(npc|object|item):([1-9]\d*)(?:\|.*)?", key)
            if not entity:
                continue
            for item, observation in bucket.get("items", {}).items():
                if int(item) in ids["item"]:
                    records.append({"source_id": key, "item_id": int(item), "observation": observation})
                    edge(entity[1], int(entity[2]), "contains" if entity[1] != "npc" else "drops", int(item),
                         observed_channel=key, observation=observation)
    else:
        raise ValueError("Unsupported EG Link export")
    return {"url": url, "provider": "eg_link", "flavor": "forever", "page_type": "observations", "client_build": build,
            "fetched_at": collected_at, "source_content_digest": digest, "confidence": "eg_link_observation",
            "records": records, "relationships": relationships, "availability_dependencies": dependencies,
            **({"publication_kind": name} if name in {"item_hotfixes.enUS", "quest_scan"} else {}),
            "attribution": [{"credit": meta["attribution"], "licence": meta["license"],
                             "licenceUrl": "https://creativecommons.org/licenses/by/4.0/", "source": f"https://github.com/{PROJECT}"}]}
