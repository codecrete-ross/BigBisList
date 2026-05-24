import unittest

from tools.project import canonical_json


def _find_list(spec):
    for row in canonical_json("bis_lists")["lists"]:
        if row["class"] == "Druid" and row["spec"] == spec and row["phase"] == "SWP" and row["slot"] == "Idol":
            return row
    raise AssertionError(f"missing Druid {spec} SWP Idol list")


class DruidIdolAuditTests(unittest.TestCase):
    def test_balance_idols_preserve_situational_bis_labels(self):
        row = _find_list("Balance")
        by_id = {item["item_id"]: item for item in row["items"]}
        self.assertEqual(by_id[32387]["rank_label"], "BiS")
        self.assertEqual(by_id[32387]["context"], "party_buff")
        self.assertEqual(by_id[27518]["rank_label"], "BiS")
        self.assertEqual(by_id[27518]["context"], "starfire")
        self.assertEqual(by_id[33510]["rank_label"], "Option")

    def test_feral_idols_keep_personal_and_raid_dps_contexts(self):
        row = _find_list("Feral dps")
        by_id = {item["item_id"]: item for item in row["items"]}
        self.assertEqual(by_id[29390]["rank_label"], "BiS (Personal DPS)")
        self.assertEqual(by_id[29390]["context"], "personal_dps")
        self.assertEqual(by_id[32387]["rank_label"], "BiS (Raid DPS)")
        self.assertEqual(by_id[32387]["context"], "raid_dps")
        self.assertEqual(by_id[33509]["rank_label"], "Option")
