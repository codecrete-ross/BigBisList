import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools import forever, forever_release as release, forever_weekly as weekly


class WeeklyReleaseTests(unittest.TestCase):
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
        self.write("assets/icon.tga", "icon\n")
        self.write(release.CANONICAL + "leveling_rules.json", json.dumps({"review": {"client_build": "1.60.1.70959"}}))
        self.write(release.LIVE_ACCEPTANCE, json.dumps({
            "status": "accepted", "reviewer": "Tester", "reviewed_at": "2026-11-17",
            "client_build": "1.60.1.70959", "reason": "Gameplay checks", "source_url": "https://example.com/evidence",
            "artifact_digest": forever.artifact_digest(lambda name: (self.root / name).read_bytes()),
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
            result = weekly.prepare_equipment_patch(candidate, state, state, report, state / "test.log")
        apply.assert_called_once_with(report, state, report["build"], equipment_only=True)
        patch_text = (state / result["equipment_patch"]).read_text(encoding="utf-8")
        self.assertIn(release.PAYLOAD, patch_text)
        self.assertIn(release.GUIDE_PAYLOAD, patch_text)
        self.assertEqual(release.git(candidate, "diff", "--cached").strip(), b"")

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

    def test_windows_checkout_line_endings_do_not_stale_receipt(self):
        same = forever.artifact_digest(lambda name: (self.root / name).read_bytes().replace(b"\n", b"\r\n"))
        accepted = json.loads((self.root / release.LIVE_ACCEPTANCE).read_text())
        self.assertEqual(same, accepted["artifact_digest"])
