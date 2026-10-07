import os, unittest
import fontgen, render_font

DOT = ["......"] * 6 + ["..#..."] + ["......"] * 6        # one stroke pixel at art (2,6) -> cell (3,8)

class Parse(unittest.TestCase):
    def test_parse_and_space_name(self):
        g = fontgen.parse("# c\nchar space\n" + "......\n" * 13 + "char A\n" + "\n".join(DOT) + "\n")
        self.assertEqual(sorted(g), [0x20, 0x41])
        self.assertEqual(g[0x41], DOT)

    def test_rows_starting_with_hash_are_art(self):
        rows = ["#....."] + ["......"] * 12
        self.assertEqual(fontgen.parse("# comment\nchar L\n" + "\n".join(rows) + "\n")[0x4C], rows)

    def test_bad_inputs_rejected(self):
        for text, msg in (("char A\n" + "......\n" * 12, "13"),
                          ("char A\n" + "......\n" * 13 + "char A\n" + "......\n" * 13, "twice"),
                          ("char A\n" + ".....\n" + "......\n" * 12, "row"),
                          ("......\n", "before")):
            with self.assertRaisesRegex(ValueError, msg):
                fontgen.parse(text)

class Pixels(unittest.TestCase):
    def test_outline_ring_around_single_pixel(self):
        px = fontgen.pixels(DOT)
        self.assertEqual(px[8][3], 1)
        ring = [px[y][x] for y in (7, 8, 9) for x in (2, 3, 4) if (y, x) != (8, 3)]
        self.assertEqual(ring, [2] * 8)
        self.assertEqual(sum(v != 0 for row in px for v in row), 9)

    def test_bytes_roundtrip_through_decoder(self):
        b = fontgen.glyph_bytes(DOT)
        self.assertEqual(len(b), 32)
        top, bottom = render_font.decode_tile(b, 0, 2), render_font.decode_tile(b, 16, 2)
        self.assertEqual(top + bottom, fontgen.pixels(DOT))

    def test_font_bytes_layout(self):
        fb = fontgen.font_bytes({0x41: DOT})
        self.assertEqual(len(fb), 0xC00)
        self.assertEqual(fb[(0x41 - 0x20) * 32:(0x42 - 0x20) * 32], fontgen.glyph_bytes(DOT))
        self.assertEqual(fb[:32], bytes(32))                     # missing code -> blank

class Art(unittest.TestCase):
    def test_all_printable_ascii_drawn(self):
        g = fontgen.load()
        self.assertEqual([c for c in range(0x20, 0x7F) if c not in g], [])
