import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools import forever, forever_prerelease as gaps, forever_release as release, forever_weekly as weekly
from tools.forever_spell_evidence import audit_exports


class WeeklyReleaseTests(unittest.TestCase):
    def test_spell_evidence_reports_changed_source_new_links_and_additional_items(self):
        lead = "chance on hit: 1294430 Rage of Sul'thraze"
        new = "use: 102 Test Spell"
        catalog = {"items": [{"id": 9372, "effect_leads": [lead]}, {"id": 5, "effect_leads": [lead, new]}]}
        reviewed = {"references": {lead: {"items": [9372], "digest": "old"}}}
        refreshed = {"references": {lead: {"items": [5, 9372], "digest": "new"}}}
        report = audit_exports(catalog, reviewed, refreshed)
        self.assertEqual(report["new_references"], [new])
        self.assertEqual(report["changed_associations"], [lead])
        self.assertEqual(report["changed_sources"], [lead])
        self.assertTrue(weekly.effect_review_blocked(report))

    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name)
        release.git(self.root, "init", "-b", "main")
        self.write(forever.FOREVER_MANIFEST, "## Interface: 16001\nDataForever.lua\nGuideDataForever.lua\nGuideRanksForever.lua\nUI.lua\nConfig.lua\n")
        self.write("UI.lua", "return true\n")
        self.write("Config.lua", 'version = "0.15.0"\n')
        self.write("README.md", "Current release 0.15.0. Run -Version 0.15.0.\n")
        self.write("CHANGELOG.md", "# Changelog\n\n## 0.15.0 - 2026-11-17\n\n- Added Forever gear.\n")
        self.write("RELEASE_NOTES.md", "Initial notes\n")
        self.write(release.PAYLOAD, "return {1}\n")
        self.write(release.GUIDE_PAYLOAD, "return {}\n")
        self.write("GuideRanksForever.lua", "return {}\n")
        self.write("assets/icon.tga", "\x00icon\n")
        self.write(release.CANONICAL + "leveling_rules.json", json.dumps({"review": {"client_build": "1.60.1.70938"}}))
        self.write(release.CANONICAL + "reviewed_builds.json", json.dumps({
            "target_client": "1.60.1.71037", "leveling_sources": "1.60.1.70938", "guide_sources": "1.60.1.70959",
        }))
        for name in ("guide_equipment", "scoring_model", "effect_benchmarks"):
            self.write(release.CANONICAL + name + ".json", json.dumps({"client_build": "1.60.1.70959"}))
        self.write(release.LIVE_ACCEPTANCE, json.dumps({
            "status": "accepted", "reviewer": "Tester", "reviewed_at": "2026-11-17",
            "client_build": "1.60.1.71037", "reason": "Gameplay checks", "source_url": "https://example.com/evidence",
            "artifact_digest": forever.release_artifact_digest(self.root),
            "checks": dict.fromkeys(forever.LIVE_ACCEPTANCE_CHECKS, True),
            "performance": {"startup_ms": 12, "first_open_ms": 17},
        }))
        self.base = self.commit("First live-tested release")
        release.git(self.root, "tag", "0.15.0")

    def write(self, name, contents):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, encoding="utf-8", newline="\n")

    def commit(self, message):
        release.git(self.root, "add", "-A")
        release.git(self.root, *weekly.BOT, "commit", "-m", message)
        return release.commit_id(self.root, "HEAD")

    def data_patch(self, previous="0.15.0", *, parent=None):
        version = release.patch_version(previous)
        parent = parent or release.commit_id(self.root, "HEAD")
        self.write("Config.lua", release.with_config_version(release.blob(self.root, parent, "Config.lua").decode(), version))
        self.write("README.md", release.with_readme_version(release.blob(self.root, parent, "README.md").decode(), previous, version))
        history = release.blob(self.root, parent, "CHANGELOG.md").decode().removeprefix("# Changelog\n\n")
        self.write("CHANGELOG.md", f"# Changelog\n\n## {version} - 2026-11-18\n\n- Updated Forever gear.\n\n{history}")
        self.write("RELEASE_NOTES.md", f"Verified notes for {version}\n")
        self.write(release.PAYLOAD, f'return {{ "{version}" }}\n')
        self.write(release.GUIDE_PAYLOAD, f'return {{ "{version}" }}\n')
        self.write(release.CANONICAL + "items.json", '{"items": []}\n')
        return self.commit(f"Data patch {version}")

    def test_valid_patch_reuses_live_baseline_without_modifying_it(self):
        candidate = self.data_patch()
        changes = release.verify_patch(self.root, self.base, candidate, "0.15.0", "0.15.1")
        self.assertIn(release.PAYLOAD, changes)
        self.assertIn(release.GUIDE_PAYLOAD, changes)
        self.assertNotIn(release.LIVE_ACCEPTANCE, changes)
        receipt = weekly.validate_candidate(self.root, candidate, "0.15.0")
        self.assertEqual(receipt["status"], "scripted_data_only")
        self.assertEqual(receipt["commit"], candidate)
        self.assertEqual(receipt["baseline_commit"], self.base)

    def test_disposable_checkout_leaves_another_worktree_untouched(self):
        self.write("UI.lua", "other session edit\n")
        copy = weekly.checkout(self.root, self.root / ".git" / "staged", self.base)
        self.assertEqual((copy / "UI.lua").read_text().strip(), "return true")
        self.assertEqual((self.root / "UI.lua").read_text().strip(), "other session edit")

    def test_prepare_patch_gates_exact_clean_commit_and_keeps_source_checkout(self):
        self.write("UI.lua", "other session edit\n")
        state = self.root / ".git" / "prepared"
        candidate = weekly.checkout(self.root, state, self.base)
        log = state / "test.log"

        def build(worktree, *args, **_kwargs):
            if "tools.generate_lua" in args:
                (worktree / release.PAYLOAD).write_text("return {2}\n", encoding="utf-8")
            if "tools.generate_release_notes" in args:
                (worktree / "RELEASE_NOTES.md").write_text("Generated fixture notes\n", encoding="utf-8")

        with (patch.object(weekly, "command", side_effect=build),
              patch.object(weekly, "run_gate") as gate):
            result = weekly.prepare_patch(candidate, state, {}, "0.15.0", "0.15.0", "2026-11-18", log)
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["commit"], release.commit_id(candidate, "HEAD"))
        self.assertEqual(release.git(candidate, "status", "--porcelain").strip(), b"")
        gate.assert_called_once_with(candidate, "0.15.1", "0.15.0", log)
        self.assertEqual(release.commit_id(self.root, "HEAD"), self.base)
        self.assertEqual((self.root / "UI.lua").read_text().strip(), "other session edit")

    def test_release_delta_blocks_runtime_already_merged_before_data_pr(self):
        self.write("UI.lua", "return false\n")
        advanced = self.commit("Other work went to main")
        candidate = self.data_patch(parent=advanced)
        release.verify_patch(self.root, advanced, candidate, "0.15.0", "0.15.1")
        with self.assertRaisesRegex(ValueError, "UI.lua"):
            weekly.validate_candidate(self.root, candidate, "0.15.0")

    def test_build_assets_and_scoring_changes_require_new_live_checks(self):
        candidate = self.data_patch()
        for path, payload in (
            ("assets/icon.tga", "changed icon\n"),
            (release.CANONICAL + "scoring_model.json", '{"weights": [5]}\n'),
            (release.CANONICAL + "leveling_rules.json", '{"review":{"client_build":"1.60.1.70960"}}'),
        ):
            with self.subTest(path=path):
                self.write(path, payload)
                changed = self.commit("New baseline needed")
                self.assertFalse(release.baseline_acceptance("0.15.0", root=self.root, revision=changed)["ok"])
                self.assertTrue(release.baseline_acceptance("0.15.0", root=self.root, revision=candidate)["ok"])

    def test_guide_only_patch_and_effect_policy(self):
        self.data_patch()
        self.write(release.PAYLOAD, release.blob(self.root, self.base, release.PAYLOAD).decode())
        candidate = self.commit("Guide-only data")
        self.assertIn(release.GUIDE_PAYLOAD, release.verify_patch(self.root, self.base, candidate, "0.15.0", "0.15.1"))
        self.write(release.CANONICAL + "effect_benchmarks.json", '{"client_build":"1.60.1.70959","rules":[]}')
        changed = self.commit("Different benchmark")
        with self.assertRaisesRegex(ValueError, "effect_benchmarks"):
            release.verify_patch(self.root, self.base, changed, "0.15.0", "0.15.1")

    def test_app_author_alias_does_not_match_a_human_login(self):
        self.assertEqual(weekly.author_login("app/updates"), "updates[bot]")
        self.assertNotEqual(weekly.author_login("updates"), "updates[bot]")

    def test_non_version_config_edit_cannot_pass_scope_check(self):
        self.data_patch()
        self.write("Config.lua", 'version = "0.15.1"\nconfig = {}\n')
        candidate = self.commit("Extra config edit")
        with self.assertRaisesRegex(ValueError, "fallback version"):
            release.verify_patch(self.root, self.base, candidate, "0.15.0", "0.15.1")

    def test_uncovered_or_stale_batches_never_integrate(self):
        for bad in ({"uncovered_combinations": 1}, {"review_issues": {"leveling": [{"item_id": 3}]}},
                    {"conflicts": {"6": "an equipment gate changed"}}, {"unclassified_discoveries": 1},
                    {"unresolved": [{"item_id": 21}]}):
            self.assertTrue(weekly.review_blocked(bad))
        self.assertFalse(weekly.review_blocked({"review_issues": {"leveling": []}}))

    def test_prepare_can_export_equipment_while_release_coverage_is_open(self):
        state = self.root / ".git" / "equipment"
        candidate = weekly.checkout(self.root, state, self.base)
        report = {"build": "1.60.1.70959", "uncovered_combinations": 1}
        self.assertTrue(weekly.review_blocked(report))

        def build(worktree, *args, **_kwargs):
            if "tools.generate_lua" in args:
                (worktree / release.PAYLOAD).write_text("return {2}\n", encoding="utf-8")
                (worktree / release.GUIDE_PAYLOAD).write_text("return {2}\n", encoding="utf-8")

        with (patch.object(weekly, "apply_snapshots", return_value=1) as apply,
              patch.object(weekly, "command", side_effect=build)):
            result = weekly.prepare_evidence_patch(candidate, state, state, report, state / "test.log", equipment_only=True)
        apply.assert_called_once_with(report, state, report["build"], equipment_only=True)
        patch_text = (state / result["equipment_patch"]).read_text(encoding="utf-8")
        self.assertIn(release.PAYLOAD, patch_text)
        self.assertIn(release.GUIDE_PAYLOAD, patch_text)
        self.assertEqual(release.git(candidate, "diff", "--cached").strip(), b"")

    def test_baseline_free_dry_run_reports_changed_unchanged_and_conflicted_intake(self):
        state = self.root / ".git" / "staged"
        cache = state / "cache"
        cache.mkdir(parents=True)
        report = {"build": "1.60.1.70938", "http_attempts": 4, "new_snapshot_count": 1,
                  "uncovered_combinations": 0, "staged_snapshots": [{"file": "changed.json"}]}

        def run(updated, evidence=None):
            weekly.json_file(cache / "report.json", updated)
            with (patch.object(weekly, "fetch_main", return_value=self.base),
                  patch.object(weekly, "command", return_value=json.dumps(evidence or {}).encode()) as command,
                  patch.object(weekly, "submit") as submit):
                result = weekly.prepare(self.root, state, "", "2026-11-21", online=True, comparison=None)
            submit.assert_not_called()
            commands = [call.args for call in command.call_args_list]
            self.assertTrue(all("gh" not in args and "push" not in args for args in commands))
            return result, commands

        result, calls = run(report, {"verified_patch": "verified.patch", "verified_snapshots": 1})
        self.assertEqual((result["status"], result["verified_patch"]), ("review", "verified.patch"))
        self.assertIn("--write-patch", calls[-1])
        self.assertNotIn("--equipment-only", calls[-1])
        result, calls = run({**report, "staged_snapshots": []})
        self.assertEqual((result["status"], len(calls)), ("unchanged", 1))
        result, calls = run({**report, "conflicts": {"8": "Changed source facts"}})
        self.assertEqual((result["status"], len(calls)), ("blocked", 1))

    def test_hosted_bundle_restores_only_the_verified_commit(self):
        sha = self.data_patch()
        tree = weekly.git_text(self.root, "rev-parse", sha + "^{tree}")
        state = self.root / ".git" / "artifact"
        state.mkdir()
        receipt = {"status": "ready", "commit": sha, "tree": tree, "base": self.base}
        weekly.json_file(state / "weekly.json", receipt)
        weekly.transfer_candidate(self.root, state, restore=False)
        copy = weekly.checkout(self.root, state, self.base)
        weekly.transfer_candidate(copy, state, restore=True)
        self.assertEqual(release.commit_id(copy, "FETCH_HEAD"), sha)
        weekly.json_file(state / "weekly.json", {**receipt, "commit": self.base})
        with self.assertRaisesRegex(ValueError, "checked commit"):
            weekly.transfer_candidate(copy, state, restore=True)

    def test_interrupted_branch_push_resumes_and_checks_the_workspace_author(self):
        candidate = self.data_patch()
        remote = self.root / ".git" / "remote.git"
        release.git(self.root, "init", "--bare", str(remote))
        release.git(self.root, "remote", "add", "origin", str(remote))
        tree = weekly.git_text(self.root, "rev-parse", candidate + "^{tree}")
        branch = weekly.DATA_BRANCH + "0.15.1-" + tree[:12]
        release.git(self.root, "push", "origin", self.base + ":refs/heads/main", candidate + ":refs/heads/" + branch)
        state = self.root / ".git" / "state"
        state.mkdir()
        doc = {**weekly.validate_candidate(self.root, candidate, "0.15.0"), "base": self.base, "status": "ready"}
        weekly.json_file(state / "weekly.json", doc)
        pull = {"headRefName": branch, "headRefOid": candidate, "number": 3, "url": "review/3",
                "isCrossRepository": False, "author": {"login": "workspace-user"}}
        for existing in (None, pull, {**pull, "author": {"login": "another-user"}}):
            with (patch.object(weekly, "published", return_value={"isDraft": False}),
                  patch.object(weekly, "gh_json", side_effect=([[], pull] if existing is None else [[existing]])),
                  patch.object(weekly, "command") as command):
                if existing and existing["author"]["login"] == "another-user":
                    with self.assertRaisesRegex(ValueError, "another author"):
                        weekly.submit(self.root, state, "0.15.0", "2026-11-21", "workspace-user")
                    command.assert_not_called()
                    continue
                result = weekly.submit(self.root, state, "0.15.0", "2026-11-21", "workspace-user")
                self.assertEqual(result["status"], "submitted")
                self.assertIn("--match-head-commit", command.call_args.args)
                self.assertEqual(command.call_args.args[-1], candidate)

    def test_leveling_exception_follows_exact_cells_evidence_and_previous_release(self):
        row = {"class": "Paladin", "spec": "Holy", "race_id": 1, "faction": "Alliance", "slot": "Ring",
               "level_min": 1, "level_max": 2, "status": "unreviewed_availability", "items": [42]}
        pending = {"item_id": 42, "status": "missing_tooltip", "candidate_digest": "original", "missing_fact": "level"}
        baseline = gaps.cells([row]), gaps.reasons([pending])
        resolved = {**row, "level_max": 1}
        previous = gaps.cells([resolved]), gaps.reasons([pending])
        base_summary = {"reviewed_rules": True, "availability_inventory_complete": True, "review_issues": 0,
                        "pending_ranking_combinations": 0, "availability_pending_candidates": 1}
        with (patch.object(gaps, "recorded", side_effect=lambda root, ref: previous if ref == "last" else baseline),
              patch.object(release, "tag_commit", return_value="last")):
            def evaluate(current, candidate=pending, version="0.15.0", **extra):
                summary = {**base_summary, "uncovered_combinations": len(gaps.cells([current])), **extra}
                return gaps.evaluate(version, [current], [candidate], summary)["ok"]

            self.assertTrue(evaluate(row))
            self.assertTrue(evaluate(resolved, version="0.15.1"))
            self.assertFalse(evaluate(row, version="0.15.1"))
            self.assertFalse(evaluate({**row, "race_id": 3}))
            self.assertFalse(evaluate({**row, "items": [24]}))
            self.assertFalse(evaluate(row, {**pending, "candidate_digest": "replacement"}))
            self.assertFalse(evaluate(row, review_issues=1))
            self.assertFalse(evaluate(row, version="0.16.0"))

    def test_existing_mismatched_tag_is_never_replaced(self):
        candidate = self.data_patch()
        release.git(self.root, "tag", "0.15.1", self.base)
        state = self.root / ".git" / "receipts"
        state.mkdir()
        result = weekly.validate_candidate(self.root, candidate, "0.15.0")
        weekly.json_file(state / "publish.json", {**result, "status": "verified", "pr": 9})
        invoke_git = weekly.git_text

        def remote_tag(root, *args):
            if "ls-remote" in args:
                return "existing-tag"
            return invoke_git(root, *args)

        with (patch.object(weekly, "fetch_main", return_value=candidate),
              patch.object(weekly, "published", return_value={"isDraft": False}),
              patch.object(weekly, "git_text", side_effect=remote_tag),
              patch.object(weekly, "command") as write_remote):
            with self.assertRaisesRegex(ValueError, "different commit"):
                weekly.publish(self.root, state, "0.15.0")
            write_remote.assert_not_called()
        self.assertEqual(release.tag_commit(self.root, "0.15.1"), self.base)

    def test_retry_after_publication_verifies_regular_channel_and_notes(self):
        candidate = self.data_patch()
        release.git(self.root, "tag", "0.15.1", candidate)
        state = self.root / ".git" / "receipts"
        state.mkdir()
        result = weekly.validate_candidate(self.root, candidate, "0.15.0")
        weekly.json_file(state / "publish.json", {**result, "status": "verified", "pr": 9})
        notes = release.blob(self.root, candidate, "RELEASE_NOTES.md").decode()
        tag_info = {"tagName": "0.15.1", "isDraft": False, "isPrerelease": False, "body": notes}
        def published(_root, tag):
            return tag_info if tag == "0.15.1" else {"tagName": tag, "isDraft": False, "isPrerelease": False}
        with (patch.object(weekly, "fetch_main", return_value=candidate),
              patch.object(weekly, "published", side_effect=published),
              patch.object(weekly, "newest_tag", return_value="0.15.1"),
              patch.object(weekly, "git_text", return_value=candidate),
              patch.object(weekly, "command") as write_remote):
            self.assertEqual(weekly.publish(self.root, state, "0.15.0")["status"], "published")
            tag_info["isPrerelease"] = True
            with self.assertRaises(ValueError):
                weekly.publish(self.root, state, "0.15.0")
            write_remote.assert_not_called()

    def test_windows_checkout_line_endings_do_not_stale_receipt(self):
        def checkout_bytes(name):
            raw = (self.root / name).read_bytes()
            return raw.replace(b"\n", b"\r\n") if name.endswith((".lua", ".toc")) else raw
        same = forever.artifact_digest(checkout_bytes, ["assets/icon.tga"])
        accepted = json.loads((self.root / release.LIVE_ACCEPTANCE).read_text())
        self.assertEqual(same, accepted["artifact_digest"])
        self.write("assets/icon.tga", "changed icon")
        self.assertNotEqual(forever.release_artifact_digest(self.root), accepted["artifact_digest"])
