import unittest
from tbl import Table

T = Table.parse("""# test table
00=あ
01=い
8140=亜
8141=亜
02=ます
F0=<NL>/
F2=<PORTRAIT:1>
FF=<END>!
""")

class Decode(unittest.TestCase):
    def test_basic_and_multibyte(self):
        self.assertEqual(T.decode(bytes([0x00, 0x81, 0x40, 0x01, 0xFF])), ("あ亜い<END>", 5))

    def test_stops_at_terminator(self):
        self.assertEqual(T.decode(bytes([0x00, 0xFF, 0x01])), ("あ<END>", 2))

    def test_arg_equal_to_terminator(self):
        self.assertEqual(T.decode(bytes([0xF2, 0xFF, 0x00, 0xFF])), ("<PORTRAIT:FF>あ<END>", 4))

    def test_unmapped_roundtrip(self):
        text, _ = T.decode(bytes([0x00, 0x77, 0xFF]))
        self.assertEqual(text, "あ<$77><END>")
        self.assertEqual(T.encode(text), bytes([0x00, 0x77, 0xFF]))

    def test_duplicate_glyph_roundtrip(self):
        raw = bytes([0x81, 0x40, 0x81, 0x41, 0xFF])
        text, _ = T.decode(raw)
        self.assertEqual(text, "亜<$8141><END>")
        self.assertEqual(T.encode(text), raw)
        self.assertEqual(T.duplicates, [("亜", ["8140", "8141"])])

    def test_no_stop(self):
        self.assertEqual(T.decode(bytes([0xFF, 0x00]), stop_at_end=False), ("<END>あ", 2))

    def test_end_bound(self):
        self.assertEqual(T.decode(bytes([0x00, 0x01, 0x00]), end=2, stop_at_end=False), ("あい", 2))

class Encode(unittest.TestCase):
    def test_longest_text_match_and_newlines_ignored(self):
        self.assertEqual(T.encode("ます<NL>\nあ<END>"), bytes([0x02, 0xF0, 0x00, 0xFF]))

    def test_tag_with_args(self):
        self.assertEqual(T.encode("<PORTRAIT:03>"), bytes([0xF2, 0x03]))

    def test_unknown_char_raises(self):
        with self.assertRaises(ValueError):
            T.encode("X")

    def test_break_tags(self):
        self.assertEqual(T.break_tags, {"NL"})
