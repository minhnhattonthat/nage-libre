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

    def test_narration_reused_as_op13_filler_keeps_op0B_box(self):
        # op 0B narration that op 13 also names in absent members' slots (scene_315 0008): the JP is 30-wide
        blk = words(0x13, 0x0010, 0x0010, 0x0016, 0x0010, 0x0016, 0x0B, 0x0010, 0xFFFF, 0x41, 0xFFFF, 0x42, 0xFFFF)
        boxes = wrap.entry_boxes(blk)
        self.assertEqual(boxes[0x10], wrap.FULL4)
        self.assertEqual(boxes[0x16], wrap.PORTRAIT)

    def test_mixed_widths_get_one_line_of_the_narrower(self):
        blk = words(0x01, 0x0008, 0x2B, 0x0008, 0xFFFF, 0x41, 0xFFFF)
        box = wrap.entry_boxes(blk)[0x08]
        self.assertEqual((box.cols, box.lines), (22, 1))
        self.assertIn("22- and 30-column", box.note)


class Orphans(unittest.TestCase):
    def test_clean_wraps_pass(self):
        self.assertEqual(wrap.orphans("hello there my<BR>ok<END>", B, T), [])


class Balance(unittest.TestCase):
    def test_widow_takes_a_word_from_the_line_above(self):
        self.assertEqual(wrap.balance("hello abc there<END>", B, T), "hello<BR>abc there<END>")

    def test_spilling_indent_is_trimmed_until_it_fits(self):
        self.assertEqual(wrap.balance("hi<BR><$FE03><$FE03>abc defg<END>", B, T), "hi<BR><$FE03>abc defg<END>")

    def test_indent_dropped_when_line_wraps_anyway(self):
        self.assertEqual(wrap.balance("<$FE03>ab cd ef gh ij<END>", B, T), "ab cd ef gh ij<END>")

    def test_fit_balances(self):
        self.assertEqual(wrap.fit("hello abc there<END>", B, T), "hello" + pad(5) + "abc there<END>")

    def test_orphans_reports_what_balance_cannot_fix(self):
        self.assertEqual(wrap.orphans("hello abc there<END>", B, T), [])
        self.assertEqual(wrap.orphans("abcdefghij k<END>", B, T), ["abcdefghij k"])


class NoExtraBlanks(unittest.TestCase):
    # The engine shows one blank less of an indent that follows a full line. Compensating with a spare
    # blank broke 76 scenes in the tour (blanks after a full line are drawn past the box edge), so fit
    # must emit an indent exactly as written.
    def test_indent_after_br_is_emitted_as_written(self):
        self.assertEqual(wrap.fit("ab<BR><$FE03>k<END>", B, T), "ab" + pad(8) + "<$FE03>k<END>")
