import unittest

from tools.project import ADDON_DIR


class AddonShellTests(unittest.TestCase):
    def test_toc_references_existing_files(self):
        toc_path = ADDON_DIR / "BigBiSList.toc"
        toc_lines = toc_path.read_text(encoding="utf-8").splitlines()
        referenced_files = [
            line.strip()
            for line in toc_lines
            if line.strip() and not line.startswith("#") and not line.startswith("##")
        ]
        self.assertEqual(
            referenced_files,
            ["Data.lua", "Config.lua", "DataIndex.lua", "Widgets.lua", "UI.lua", "Tooltip.lua", "Minimap.lua", "Core.lua"],
        )
        for file_name in referenced_files:
            self.assertTrue((ADDON_DIR / file_name).is_file(), file_name)

    def test_addon_shell_uses_bigbislist_identity(self):
        toc_text = (ADDON_DIR / "BigBiSList.toc").read_text(encoding="utf-8")
        self.assertIn("## Title: Big BiS List", toc_text)
        self.assertIn("## SavedVariables: BigBiSListDB", toc_text)
        self.assertNotIn("BISTBCDB", toc_text)

        for path in ADDON_DIR.glob("*.lua"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("BISTBC", text, str(path))
