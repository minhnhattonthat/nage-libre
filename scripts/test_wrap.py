import unittest
import entable, wrap
from tbl import Table

T = Table.parse(entable.table_text())
B = wrap.Box(10, 3)
FB = "　"                       # full-width blank: pads 2 columns in one glyph


def pad(n):
    return " " * (n % 2) + FB * (n // 2)

class Fit(unittest.TestCase):
    def test_word_wrap_pads_with_spaces(self):
        self.assertEqual(wrap.fit("hello there world<END>", B, T), "hello" + pad(5) + "there" + pad(5) + "world<END>")

    def test_exact_fill_needs_no_padding(self):
        self.assertEqual(wrap.fit("abcdefghij klm<END>", B, T), "abcdefghijklm<END>")

    def test_br_and_leading_br(self):
        self.assertEqual(wrap.fit("<BR>hi<BR>yo<END>", B, T), pad(10) + "hi" + pad(8) + "yo<END>")

    def test_br_after_exact_fill_is_not_a_blank_line(self):
        self.assertEqual(wrap.fit("abcdefghij<BR>klm<END>", B, T), "abcdefghijklm<END>")

    def test_spaces_collapsed(self):
        self.assertEqual(wrap.fit("  hi    there <END>", B, T), "hi there<END>")

    def test_fullwidth_symbol_counts_two(self):
        self.assertEqual(wrap.fit("abcdefgh… x<END>", B, T), "abcdefgh…x<END>")

    def test_overlong_word_fails(self):
        with self.assertRaisesRegex(wrap.FitError, "11 columns"):
            wrap.fit("abcdefghijk<END>", B, T)

    def test_too_many_lines_fails_with_count(self):
        with self.assertRaisesRegex(wrap.FitError, r"4 lines, box holds 3 .* 7 columns over"):
            wrap.fit("aaaa bbbbbbb cccccc ddddddd<END>", B, T)

    def test_padding_uses_fullwidth_blanks(self):
        self.assertEqual(wrap.fit("abc de<END>", wrap.Box(4, 2), T), "abc" + " " + "de<END>")
        self.assertEqual(wrap.fit("ab cd<END>", wrap.Box(4, 2), T), "ab" + FB + "cd<END>")

    def test_box_note_explains_error(self):
        with self.assertRaisesRegex(wrap.FitError, "must fit one"):
            wrap.fit("aaaa bbbb<END>", wrap.Box(5, 1, "printed by 22- and 30-column boxes: must fit one 22-column line"), T)

    def test_unknown_char_and_missing_end(self):
        with self.assertRaisesRegex(wrap.FitError, "table"):
            wrap.fit("ä<END>", B, T)
        with self.assertRaisesRegex(wrap.FitError, "<END>"):
            wrap.fit("hi", B, T)

def words(*ws):
    return b"".join(w.to_bytes(2, "little") for w in ws)

class EntryBoxes(unittest.TestCase):
    BLK = words(0x01, 0x0010, 0x2B, 0x0016, 0x0B, 0x001A, 0xFFFF, 0, 0x41, 0xFFFF, 0x42, 0xFFFF, 0x43, 0xFFFF)

    def test_box_per_entry(self):
        boxes = wrap.entry_boxes(self.BLK)
        self.assertEqual(boxes[0x10], wrap.PORTRAIT)
        self.assertEqual(boxes[0x16], wrap.FULL)
        self.assertEqual(boxes[0x1A], wrap.FULL4)

    def test_mixed_widths_get_one_line_of_the_narrower(self):
        blk = words(0x01, 0x0008, 0x2B, 0x0008, 0xFFFF, 0x41, 0xFFFF)
        box = wrap.entry_boxes(blk)[0x08]
        self.assertEqual((box.cols, box.lines), (22, 1))
        self.assertIn("22- and 30-column", box.note)
