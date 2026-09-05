from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools.project import RAW_WOWHEAD_DIR, write_text
from tools.refresh_progression import archive_verified_pre_raid, frozen_pre_raid_snapshot, refresh
from tools.scrape_wowhead import import_bis_lists_from_snapshots, manifest_sources_for_snapshot, select_pre_raid_snapshots, snapshot_name


def committed_guide():
    url = "https://www.wowhead.com/tbc/guide/classes/hunter/marksmanship/dps-bis-gear-pve-pre-raid"
    path = RAW_WOWHEAD_DIR / "full_bis" / snapshot_name(url)
    return json.loads(path.with_stem(path.stem + "--pr-PR").read_text(encoding="utf-8"))


class RefreshProgressionTests(unittest.TestCase):
    def test_invalid_first_capture_cannot_displace_verified_phase_history(self):
        snapshot = committed_guide()
        snapshot.update(content_phase="T6", recommendation_status="unverified_phase")
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / snapshot_name(snapshot["url"])
            self.assertIsNone(archive_verified_pre_raid(path, snapshot))
            archive = path.with_stem(path.stem + "--pr-T6")
            write_text(archive, json.dumps(snapshot))  # Legacy invalid archive.
            verified = {**snapshot, "recommendation_status": "verified_phase_update"}
            archive_verified_pre_raid(path, verified)
            original_bytes = archive.read_bytes()
            unchanged = {**verified, "recommendation_status": "no_distinct_update"}
            self.assertIsNone(archive_verified_pre_raid(path, unchanged))
            self.assertEqual(archive.read_bytes(), original_bytes)
            self.assertEqual(json.loads(original_bytes)["recommendation_status"], "verified_phase_update")
            self.assertTrue(list((Path(temporary) / "history").glob("*.json")))

    def test_same_phase_revisions_keep_original_evidence_and_import_only_latest(self):
        first = committed_guide()
        first.update(content_phase="T6", recommendation_status="verified_phase_update", fetched_at="2026-09-01T00:00:00Z")
        latest = deepcopy(first)
        latest["fetched_at"] = "2026-09-02T00:00:00Z"
        latest["tables"][0]["heading"] += " updated"
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / snapshot_name(first["url"])
            archive_verified_pre_raid(path, first)
            archive_path = archive_verified_pre_raid(path, latest)
            archive = json.loads(archive_path.read_text(encoding="utf-8"))
            self.assertEqual(archive["tables"], latest["tables"])
            history = [json.loads(p.read_text(encoding="utf-8")) for p in (Path(temporary) / "history").glob("*.json")]
            self.assertTrue(any(row["tables"] == first["tables"] for row in history))
            selected = select_pre_raid_snapshots([archive, latest, first])
            self.assertEqual(len(selected), 1)
            self.assertEqual(selected[0]["tables"], latest["tables"])

    def test_changed_manifest_url_preserves_committed_old_spec_path(self):
        historical = committed_guide()
        old_bindings = manifest_sources_for_snapshot(historical, "bis_lists")
        self.assertTrue(old_bindings)
        frozen = frozen_pre_raid_snapshot(historical)
        before = import_bis_lists_from_snapshots([frozen])
        new_url = "https://www.wowhead.com/tbc/guide/future-cycle/marksmanship-pre-raid"
        new_bindings = [{**row, "url": new_url} for row in old_bindings]
        with patch("tools.scrape_wowhead.manifest_sources_by_url", return_value={new_url: new_bindings}):
            self.assertEqual(manifest_sources_for_snapshot(frozen, "bis_lists"), old_bindings)
            after = import_bis_lists_from_snapshots([frozen])
        self.assertEqual(after, before)
        self.assertTrue(after["lists"])
        self.assertTrue(all(row["class"] == "Hunter" and row["spec"] == "Marksmanship" and row["content_phase"] == "PR"
                            for row in after["lists"]))

    def test_cached_refresh_sequence_retains_verified_path_after_unchanged_fetch(self):
        historical = committed_guide()
        url = historical["url"]
        unverified = deepcopy(historical)
        unverified["tables"][0]["heading"] = "Pre-Raid equipment with no verified phase heading"
        verified = deepcopy(historical)
        for table in verified["tables"]:
            table["heading"] = "Phase 3 Pre-Raid " + str(table.get("slot", "equipment"))
        verified["fetched_at"] = "2026-09-05T00:00:00Z"
        unchanged = deepcopy(verified)
        unchanged["fetched_at"] = "2026-09-06T00:00:00Z"
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "full_bis" / snapshot_name(url)
            write_text(path, json.dumps(historical))
            with patch("tools.refresh_progression.RAW_WOWHEAD_DIR", root), \
                 patch("tools.refresh_progression.FAMILIES", {"bis_lists": "full_bis"}), \
                 patch("tools.refresh_progression.manifest_urls", return_value=[url]), \
                 patch("tools.refresh_progression.fetch_normalized_snapshot", side_effect=[unverified, verified, unchanged]), \
                 patch("builtins.print"):
                for _ in range(3):
                    self.assertFalse(refresh("T6")["failures"])
            archive = json.loads(path.with_stem(path.stem + "--pr-T6").read_text(encoding="utf-8"))
            current = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(archive["recommendation_status"], "verified_phase_update")
            self.assertEqual(archive["previous_verified_phase"], "PR")
            self.assertEqual(current["recommendation_status"], "no_distinct_update")
            self.assertEqual(current["previous_verified_phase"], "T6")
            imported = import_bis_lists_from_snapshots([archive, current])
            self.assertTrue(imported["lists"])
            self.assertTrue(all(row["content_phase"] == "T6" for row in imported["lists"]))

    def test_shared_guide_split_selects_winning_binding_per_spec(self):
        old = committed_guide()
        bindings = manifest_sources_for_snapshot(old, "bis_lists")
        old = {**old, "historical_pre_raid": True, "fetched_at": "2026-01-01T00:00:00Z",
               "manifest_bindings": [bindings[0], {**bindings[0], "spec": "Survival"}]}
        new_url = "https://www.wowhead.com/tbc/guide/future/marksmanship-pre-raid"
        new = {**committed_guide(), "url": new_url, "fetched_at": "2026-02-01T00:00:00Z"}
        with patch("tools.scrape_wowhead.manifest_sources_by_url", return_value={new_url: [bindings[0]]}):
            selected = select_pre_raid_snapshots([old, new])
            mapped = {row["url"]: [b["spec"] for b in manifest_sources_for_snapshot(row, "bis_lists")] for row in selected}
            imported = import_bis_lists_from_snapshots(selected)["lists"]
        self.assertEqual(mapped, {old["url"]: ["Survival"], new_url: ["Marksmanship"]})
        per_spec = {spec: [row for row in imported if row["spec"] == spec] for spec in ("Marksmanship", "Survival")}
        self.assertEqual(len(per_spec["Marksmanship"]), len(per_spec["Survival"]))
        self.assertEqual({row["source_url"] for row in per_spec["Marksmanship"]}, {new_url})

    def test_refresh_uses_manifest_anniversary_phase_four_and_archives_immediately(self):
        historical = committed_guide()
        url = historical["url"]
        fresh = deepcopy(historical)
        fresh["fetched_at"] = "2026-09-07T00:00:00Z"
        for table in fresh["tables"]:
            table["heading"] = "Phase 4 Pre-Raid equipment"
        bindings = [{**row, "content_terminology": "anniversary_2026"}
                    for row in manifest_sources_for_snapshot(historical, "bis_lists")]
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "full_bis" / snapshot_name(url)
            write_text(path, json.dumps(historical))
            with patch("tools.refresh_progression.RAW_WOWHEAD_DIR", root), \
                 patch("tools.refresh_progression.FAMILIES", {"bis_lists": "full_bis"}), \
                 patch("tools.refresh_progression.manifest_urls", return_value=[url]), \
                 patch("tools.refresh_progression.manifest_sources_by_url", return_value={url: bindings}), \
                 patch("tools.refresh_progression.fetch_normalized_snapshot", return_value=fresh), \
                 patch("builtins.print"):
                self.assertFalse(refresh("SWP")["failures"])
            archive = json.loads(path.with_stem(path.stem + "--pr-SWP").read_text(encoding="utf-8"))
            self.assertEqual(archive["recommendation_status"], "verified_phase_update")
            self.assertEqual(archive["content_terminology"], "anniversary_2026")
            with patch("tools.scrape_wowhead.manifest_sources_by_url", return_value={}):
                self.assertTrue(import_bis_lists_from_snapshots([archive])["lists"])


if __name__ == "__main__":
    unittest.main()
