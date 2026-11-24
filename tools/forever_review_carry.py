"""Carry exact Forever availability proofs across bulk catalog revisions."""
from __future__ import annotations

from tools import forever_availability as availability
from tools.forever_sources import check_evidence_refs, evidence_index, evidence_ref


def referenced_evidence(value):
    if isinstance(value, list):
        for member in value:
            yield from referenced_evidence(member)
    elif isinstance(value, dict):
        if set(value) == {"evidence_id", "content_digest"}:
            yield value
        else:
            for member in value.values():
                yield from referenced_evidence(member)


def scoped_reviews(reviews: dict, baseline: dict, rules: dict) -> dict:
    """Migrate only approvals valid against their original evidence."""
    document = reviews.get("availability", {})
    if document.get("proof_version") == availability.SCOPED_PROOFS or not document.get("decisions"):
        return reviews

    records = evidence_index(baseline)
    previous = availability.build_inventory(baseline, document, rules, records)
    if previous["decision_issues"] or previous["source_issues"]:
        raise ValueError("Original Forever availability reviews must validate before migrating proofs")
    candidate_hashes = {row["item_id"]: availability.candidate_proof(
        {key: value for key, value in row.items() if key != "candidate_digest"}, scoped=True, client_build=document["client_build"])
        for row in previous["candidates"]}
    route_hashes = availability.item_acquisition_digests(baseline, records, scoped=True)
    source_hashes = availability.scoped_source_digests(baseline)
    decisions = []
    for decision in document["decisions"]:
        item_id = decision["item_id"]
        rechecked = {**decision, "candidate_digest": candidate_hashes[item_id],
                     "prior_proof": {k: decision[k] for k in ("candidate_digest", "item_acquisition_digest", "acquisition_evidence_digest")
                                     if k in decision}}
        if decision.get("exclusion") in {"acquisition_minimum", "unavailable"}:
            rechecked.pop("acquisition_evidence_digest", None)
            rechecked["item_acquisition_digest"] = route_hashes.get(item_id, availability.EMPTY_SUPPORT_DIGEST)
        exact = {}
        for ref in referenced_evidence(decision):
            record = records.get(ref["evidence_id"])
            if record and (checksum := source_hashes.get((record["source_url"], item_id))):
                if record["content_digest"] != ref["content_digest"]:
                    raise ValueError("Original scoped evidence digest did not validate")
                exact[ref["evidence_id"]] = checksum
        if exact:
            rechecked["scoped_evidence_refs"] = exact
        decisions.append(rechecked)
    return {**reviews, "availability": {**document, "proof_version": availability.SCOPED_PROOFS, "decisions": decisions}}


def carry_additive_catalogs(reviews: dict, baseline: dict, current: dict) -> dict:
    """Reverify the exact coverage of additive, complete AHledger revisions."""
    document = reviews.get("availability", {})
    if not document.get("source_reviews"):
        return reviews

    updated, history = [], list(document.get("source_review_history", []))
    records = None
    for review in document["source_reviews"]:
        url = review["source_url"]
        old, new = baseline.get(url), current.get(url)
        if review["kind"] != "ahledger_catalog" or not old or not new or old == new:
            updated.append(review)
            continue
        old_scope, new_scope = (snapshot.get("catalog_coverage", {}) for snapshot in (old, new))
        old_rows, new_rows = ({row["item_id"]: row for row in snapshot["records"]} for snapshot in (old, new))
        unchanged = all(new_rows.get(identifier) == row for identifier, row in old_rows.items())
        if (not unchanged or new.get("catalog_kind") != "ahledger_catalog"
                or old_scope.get("complete") is not True or new_scope.get("complete") is not True
                or new_scope.get("total") != len(new_rows) or len(new_rows) != len(new["records"])
                or {k: v for k, v in new_scope.items() if k != "total"} != {k: v for k, v in old_scope.items() if k != "total"}
                or any(new.get(k) != old.get(k) for k in ("provider", "client_build", "confidence", "attribution"))):
            updated.append(review)
            continue
        if records is None:
            records = evidence_index(baseline)
        support = check_evidence_refs(review, records)
        if len(support) != 1 or support[0]["source_url"] != url or review.get("record_count") != len(old_rows):
            updated.append(review)
            continue
        history.append({"reason": "Counted additive catalog revision with identical original rows", "review": review})
        updated.append({**review, "record_count": len(new_rows), "evidence_refs": [evidence_ref(url, current)]})
    return {**reviews, "availability": {**document, "source_reviews": updated, "source_review_history": history}}
