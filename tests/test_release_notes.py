import contextlib
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools.generate_release_notes import (
    assert_behavior_only, main, parse_changelog, render_release_notes, validate_history,
)


def changelog(*versions):
    return "# Changelog\n\n" + "\n\n".join(
        f"## {version} - 2026-09-04\n\n- Fixed item tooltips in {version}."
        for version in versions
    ) + "\n"


class ReleaseNotesTests(unittest.TestCase):
    def test_minor_line_keeps_patch_attribution_and_original_body(self):
        source = changelog("0.12.3", "0.12.2", "0.12.1", "0.12.0", "0.11.0")
        source = source.replace("- Fixed item tooltips in 0.12.3.", "- No addon behavior changes.")
        rendered = render_release_notes(parse_changelog(source), "0.12.3")
        self.assertTrue(rendered.startswith("# Big BiS List 0.12.3\n"))
        self.assertIn("0.12.x releases, newest first", rendered)
        self.assertIn("## 0.12.3 - 2026-09-04\n\n- No addon behavior changes.", rendered)
        for version in ("0.12.2", "0.12.1", "0.12.0"):
            self.assertIn(f"## {version} - 2026-09-04\n\n- Fixed item tooltips in {version}.", rendered)
        self.assertNotIn("0.11.0", rendered)
        self.assertLess(rendered.index("## 0.12.3"), rendered.index("## 0.12.0"))

    def test_minor_and_major_bumps_start_a_fresh_view(self):
        for version, earlier in (("0.13.0", "0.12.3"), ("1.0.0", "0.13.0")):
            with self.subTest(version=version):
                rendered = render_release_notes(parse_changelog(changelog(version, earlier)), version)
                self.assertEqual(rendered.count("\n## "), 1)
                self.assertNotIn(earlier, rendered)

    def test_patch_numbers_are_sorted_numerically(self):
        releases = parse_changelog(changelog("0.12.10", "0.12.9", "0.12.0"))
        self.assertIn("## 0.12.10", render_release_notes(releases, "0.12.10"))
        with self.assertRaisesRegex(ValueError, "descending"):
            parse_changelog(changelog("0.12.9", "0.12.10", "0.12.0"))

    def test_invalid_histories_are_rejected(self):
        good = changelog("0.12.0")
        invalid = {
            "duplicate": changelog("0.12.0", "0.12.0"),
            "missing date": good.replace(" - 2026-09-04", ""),
            "invalid date": good.replace("2026-09-04", "2026-02-30"),
            "v prefix": good.replace("## 0.12.0", "## v0.12.0"),
            "leading zero": good.replace("## 0.12.0", "## 0.12.00"),
            "empty": good.replace("- Fixed item tooltips in 0.12.0.", ""),
            "heading only": good.replace("- Fixed item tooltips in 0.12.0.", "### Fixed"),
            "empty bullet": good.replace("- Fixed item tooltips in 0.12.0.", "- "),
            "comment only": good.replace("- Fixed item tooltips in 0.12.0.", "<!--\n- hidden\n-->"),
            "contradiction": good + "\n- No addon behavior changes.\n",
            "missing title": good.replace("# Changelog\n", ""),
            "bad heading": good + "\n##not-a-version\n- Fixed sorting.\n",
        }
        for case, source in invalid.items():
            with self.subTest(case=case), self.assertRaises(ValueError):
                parse_changelog(source)

    def test_missing_current_future_or_missing_base_version_is_rejected(self):
        for versions, target in (
            (("0.12.0",), "0.12.1"),
            (("0.13.0", "0.12.0"), "0.12.0"),
            (("0.12.1", "0.11.0"), "0.12.1"),
        ):
            with self.subTest(versions=versions), self.assertRaises(ValueError):
                render_release_notes(parse_changelog(changelog(*versions)), target)

    def test_line_endings_do_not_change_generation(self):
        source = changelog("0.12.0")
        self.assertEqual(parse_changelog(source), parse_changelog(source.replace("\n", "\r\n")))

    def test_development_notes_are_rejected_and_game_commands_are_allowed(self):
        for topic in ("CI", "GitHub Actions", "CurseForge", "documentation", "governance",
                      "unit tests", "test suite", "tooling", "refactoring", "packaging",
                      "release gate", "release automation", "contributor workflow"):
            with self.subTest(topic=topic), self.assertRaisesRegex(ValueError, "addon behavior only"):
                parse_changelog(changelog("0.12.0").replace("Fixed item tooltips", f"Updated {topic}"))
        assert_behavior_only("- `/bbltest` now reports missing item data.\n- Fixed item tooltip validation.")


class ReleaseNotesRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git("init", "-q")
        self.git("config", "user.name", "Release Notes Test")
        self.git("config", "user.email", "release-notes@example.invalid")
        self.git("-c", "commit.gpgsign=false", "commit", "--allow-empty", "-qm", "Initial")
        (self.root / "Config.lua").write_text('version = "1.0.0"\n', encoding="utf-8")
        (self.root / "CHANGELOG.md").write_text(changelog("1.0.0"), encoding="utf-8")

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, capture_output=True, text=True, check=True)

    def run_main(self, *args):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return main(list(args), root=self.root)

    def test_generate_and_check_are_deterministic_and_check_never_writes(self):
        self.assertEqual(self.run_main("--check"), 1)
        output = self.root / "RELEASE_NOTES.md"
        self.assertFalse(output.exists())
        self.assertEqual(self.run_main(), 0)
        generated = output.read_bytes()
        self.assertEqual(self.run_main("--check"), 0)
        self.assertEqual(self.run_main(), 0)
        self.assertEqual(output.read_bytes(), generated)
        for stale in (generated + b"\n- Fixed sorting.\n", generated + b"\n- Improved CI.\n"):
            output.write_bytes(stale)
            self.assertEqual(self.run_main("--check"), 1)
            self.assertEqual(output.read_bytes(), stale)

    def test_requested_version_must_match_config(self):
        self.assertEqual(self.run_main("--version", "1.0.1"), 1)
        self.assertFalse((self.root / "RELEASE_NOTES.md").exists())

    def test_missing_reachable_and_unreleased_historical_versions_are_rejected(self):
        self.git("tag", "0.9.0")
        with self.assertRaisesRegex(ValueError, "Missing changelog entries.*0.9.0"):
            validate_history(self.root, parse_changelog(changelog("1.0.0")), "1.0.0")
        with self.assertRaisesRegex(ValueError, "no reachable release tag.*0.8.0"):
            validate_history(self.root, parse_changelog(changelog("1.0.0", "0.9.0", "0.8.0")), "1.0.0")

    def test_shallow_history_fails_closed(self):
        with patch("tools.generate_release_notes.git_output", return_value="true"):
            with self.assertRaisesRegex(ValueError, "Full Git history"):
                validate_history(self.root, parse_changelog(changelog("1.0.0")), "1.0.0")

    def test_new_release_preserves_published_entries_before_and_after_tagging(self):
        self.assertEqual(self.run_main(), 0)
        self.git("add", "Config.lua", "CHANGELOG.md", "RELEASE_NOTES.md")
        self.git("-c", "commit.gpgsign=false", "commit", "-qm", "Release 1.0.0")
        self.git("tag", "1.0.0")
        (self.root / "Config.lua").write_text('version = "1.0.1"\n', encoding="utf-8")
        source = changelog("1.0.1", "1.0.0")
        (self.root / "CHANGELOG.md").write_text(source, encoding="utf-8")
        self.assertEqual(self.run_main(), 0)
        self.git("add", "Config.lua", "CHANGELOG.md", "RELEASE_NOTES.md")
        self.git("-c", "commit.gpgsign=false", "commit", "-qm", "Release 1.0.1")
        self.git("tag", "1.0.1")
        self.assertEqual(self.run_main("--check"), 0)
        changed = source.replace("- Fixed item tooltips in 1.0.0.", "- Fixed sorting.")
        with self.assertRaisesRegex(ValueError, "Published changelog entry 1.0.0 differs"):
            validate_history(self.root, parse_changelog(changed), "1.0.1")


if __name__ == "__main__":
    unittest.main()
