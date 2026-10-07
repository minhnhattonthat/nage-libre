import unittest
import entable
from tbl import Table

class EnTable(unittest.TestCase):
    T = Table.parse(entable.table_text())

    def test_ascii_codes(self):
        self.assertEqual(self.T.encode("Hi, Yui!<END>"),
                         bytes.fromhex("4800 6900 2c00 2000 5900 7500 6900 2100 ffff"))

    def test_symbols_use_fullwidth_glyphs(self):
        self.assertEqual(self.T.encode("…♥♪‼"), bytes.fromhex("aa02 d003 ce03 e002"))

    def test_equals_and_hash_are_characters(self):
        self.assertEqual(self.T.encode("a=b#"), bytes.fromhex("6100 3d00 6200 2300"))

    def test_no_duplicates_or_errors(self):
        self.assertEqual((self.T.duplicates, self.T.errors), ([], []))
