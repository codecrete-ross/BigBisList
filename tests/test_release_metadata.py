import re
import unittest

from tools.generate_release_notes import parse_changelog, render_release_notes
from tools.project import ROOT
from tools.validate_data import validate


README_COUNT_KEYS = {
    "classes": "classes",
    "specs": "specs",
    "phases": "phases",
    "BiS slot lists": "bis_lists",
    "item records": "items",
    "item stat records": "item_stats",
    "gem rows": "gems",
    "enchant rows": "enchants",
    "consumable rows": "consumables",
    "leveling rows": "leveling",
    "guide-backed leveling gear rows": "leveling_gear",
    "computed leveling recommendations": "leveling_recommendations",
}


class ReleaseMetadataTests(unittest.TestCase):
    def test_changelog_history_and_generated_notes_match_fallback_version(self):
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        config = (ROOT / "Config.lua").read_text(encoding="utf-8")
        config_match = re.search(r'^\s*version\s*=\s*"(?P<version>\d+\.\d+\.\d+)"\s*$', config, re.MULTILINE)
        self.assertIsNotNone(config_match)
        releases = parse_changelog(changelog)
        self.assertEqual(releases[0].version, config_match["version"])
        notes = (ROOT / "RELEASE_NOTES.md").read_text(encoding="utf-8")
        self.assertEqual(notes, render_release_notes(releases, config_match["version"]))

    def test_pkgmeta_and_publish_use_generated_notes(self):
        pkgmeta = (ROOT / ".pkgmeta").read_text(encoding="utf-8")
        self.assertRegex(
            pkgmeta,
            r"(?m)^manual-changelog:\s*$\n^\s+filename:\s+RELEASE_NOTES\.md\s*$\n^\s+markup-type:\s+markdown\s*$",
        )
        self.assertIn("  - CHANGELOG.md", pkgmeta.splitlines())
        self.assertNotIn("  - RELEASE_NOTES.md", pkgmeta.splitlines())
        for internal in ("AGENTS.md", "CLAUDE.md", "docs", "tools", "tests"):
            self.assertIn(f"  - {internal}", pkgmeta.splitlines())
        release_process = (ROOT / "docs/internal/release-process.md").read_text(encoding="utf-8")
        self.assertIn("--notes-file RELEASE_NOTES.md", release_process)
        self.assertNotIn("--notes-file CHANGELOG.md", release_process)
        gate = (ROOT / "scripts/check-release.ps1").read_text(encoding="utf-8")
        self.assertIn('"tools/generate_release_notes.py", "--version", $Version, "--check"', gate)

    def test_changelog_policy_documents_source_generation_and_player_impact(self):
        for path in ("AGENTS.md", "docs/internal/release-process.md", "README.md"):
            with self.subTest(path=path):
                text = (ROOT / path).read_text(encoding="utf-8")
                self.assertIn("CHANGELOG.md", text)
                self.assertIn("RELEASE_NOTES.md", text)
                self.assertIn("generate_release_notes.py", text)
                self.assertIn("behavior", text)
        governance = " ".join((ROOT / "AGENTS.md").read_text(encoding="utf-8").split())
        self.assertIn("only player-observable addon behavior", governance)
        self.assertIn("Exclude development-only work", governance)
        self.assertIn("- No addon behavior changes.", governance)

    def test_curseforge_ingestion_is_documented_as_automatic_only(self):
        governance = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        release_process = (
            ROOT / "docs" / "internal" / "release-process.md"
        ).read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("CurseForge ingestion is automatic", governance)
        self.assertRegex(
            release_process,
            r"there is\s+no manual CurseForge follow-up step",
        )
        self.assertIn("Do not manually upload generated zip files", release_process)
        self.assertIn("The release process has no manual CurseForge", readme)

    def test_readme_generated_counts_match_canonical_validation_summary(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        match = re.search(
            r"Current generated data includes:\s*(?P<rows>(?:\n- [^\n]+)+)",
            readme,
        )
        self.assertIsNotNone(match, "README is missing its generated-data count list")

        published = {}
        for count, label in re.findall(r"^- ([\d,]+) (.+)$", match.group("rows"), re.MULTILINE):
            published[label] = int(count.replace(",", ""))

        result = validate()
        self.assertTrue(result.ok, result.errors)
        for label, summary_key in README_COUNT_KEYS.items():
            self.assertIn(label, published, f"README is missing the published {label} count")
            self.assertEqual(
                published[label],
                result.summary[summary_key],
                f"README {label} count is stale; update it from validate_data.py --json",
            )

    def test_ci_runs_the_authoritative_full_release_gate_for_pull_requests_and_tags(self):
        workflow = (ROOT / ".github" / "workflows" / "release-check.yml").read_text(encoding="utf-8")

        self.assertIn("fetch-depth: 0", workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("pull_request:", workflow)
        self.assertIn("tags:", workflow)
        self.assertIn("scripts/check-release.ps1", workflow)
        self.assertIn("-FullData", workflow)
        self.assertIn("GITHUB_REF_NAME", workflow)
        self.assertIn("luaVersion: \"5.1.5\"", workflow)
        self.assertIn(".lua/", (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines())
        self.assertIn("  - .github", (ROOT / ".pkgmeta").read_text(encoding="utf-8").splitlines())


if __name__ == "__main__":
    unittest.main()
