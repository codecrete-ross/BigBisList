import re
import unittest

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
