import re
import unittest
from datetime import date

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
    def test_changelog_is_release_specific_and_matches_fallback_version(self):
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        config = (ROOT / "Config.lua").read_text(encoding="utf-8")

        config_match = re.search(
            r'^\s*version\s*=\s*"(?P<version>\d+\.\d+\.\d+)"\s*$',
            config,
            re.MULTILINE,
        )
        self.assertIsNotNone(config_match, "Config.lua is missing its fallback version")

        release_headings = list(
            re.finditer(
                r"^##\s+(?P<version>\d+\.\d+\.\d+)(?:\s+-\s+.*)?\s*$",
                changelog,
                re.MULTILINE,
            )
        )
        self.assertEqual(
            len(release_headings),
            1,
            "CHANGELOG.md must contain exactly one release section",
        )

        heading = release_headings[0]
        dated_heading = re.fullmatch(
            r"##\s+(?P<version>\d+\.\d+\.\d+)\s+-\s+(?P<date>\d{4}-\d{2}-\d{2})",
            heading.group(0).strip(),
        )
        self.assertIsNotNone(
            dated_heading,
            "the changelog release heading must use an ISO date",
        )
        date.fromisoformat(dated_heading.group("date"))
        self.assertEqual(dated_heading.group("version"), config_match.group("version"))
        self.assertTrue(
            changelog[heading.end():].strip(),
            "the changelog release section must have a non-empty body",
        )

    def test_pkgmeta_uses_the_release_specific_markdown_changelog(self):
        pkgmeta = (ROOT / ".pkgmeta").read_text(encoding="utf-8")
        self.assertRegex(
            pkgmeta,
            r"(?m)^manual-changelog:\s*$\n^\s+filename:\s+CHANGELOG\.md\s*$\n^\s+markup-type:\s+markdown\s*$",
        )

    def test_changelog_policy_is_addon_behavior_only(self):
        governance = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        release_process = (
            ROOT / "docs" / "internal" / "release-process.md"
        ).read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

        self.assertIn("only player-observable addon behavior", governance)
        self.assertIn("Exclude development-only work", governance)
        self.assertIn("only player-observable addon behavior", release_process)
        self.assertIn("Public release notes", release_process)
        self.assertIn("internal development work", readme)
        self.assertIn("- No addon behavior changes.", governance)
        self.assertIn("- No addon behavior changes.", release_process)
        self.assertNotRegex(
            changelog,
            r"(?i)\b(?:GitHub|CurseForge|CI|governance|documentation|tooling|packaging)\b"
            r"|\brelease (?:automation|gate|process|workflow)\b",
        )
        release_gate = (ROOT / "scripts" / "check-release.ps1").read_text(
            encoding="utf-8"
        )
        self.assertIn("$developmentOnlyTerms", release_gate)
        self.assertIn("must describe addon behavior only", release_gate)

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
