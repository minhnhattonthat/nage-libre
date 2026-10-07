import unittest
import build_tbl

class Build(unittest.TestCase):
    def test_rows_to_le_entries(self):
        lines = build_tbl.entries("# c\n0758 底遠\n0000/1 01\n0012 ＿あ〓い\n")
        self.assertEqual(lines, ["5807=底", "5A07=遠", "0000=0", "0100=1", "1400=あ", "1800=い"])
        self.assertEqual(build_tbl.unknown("0012 ＿あ〓い\n"), [0x16])

    def test_duplicates_get_variation_selectors(self):
        lines = build_tbl.entries("0010 野野\n0100 野\n")
        self.assertEqual(lines, ["1000=野", "1200=野︁", "0001=野︂"])
