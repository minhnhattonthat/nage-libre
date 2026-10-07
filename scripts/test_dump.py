import os, tempfile, unittest
import dump
from tbl import Table

T = Table.parse("00=あ\n01=い\nF0=<NL>/\nFF=<END>!\n")

def rom_with(table_off, ptrs, blob_off, blob, size=0x200):
    d = bytearray(size)
    for i, p in enumerate(ptrs):
        d[table_off + i * 2: table_off + i * 2 + 2] = p.to_bytes(2, "little")
    d[blob_off:blob_off + len(blob)] = blob
    return bytes(d)

# bank $80: CPU $808000 + x == file offset x
BLOCK = {"name": "t", "kind": "ptr16", "table": "0x0", "count": 3, "bank": "0x80"}

class Extract(unittest.TestCase):
    def setUp(self):
        blob = bytes([0x00, 0xF0, 0x01, 0xFF, 0x01, 0xFF])          # msg A at 0x100, msg B at 0x104
        self.data = rom_with(0, [0x8100, 0x8104, 0x8100], 0x100, blob)

    def test_ptr16(self):
        e = dump.extract(self.data, T, BLOCK)
        self.assertEqual((e[0].offset, e[0].length, e[0].text), (0x100, 4, "あ<NL>い<END>"))
        self.assertEqual((e[1].offset, e[1].text), (0x104, "い<END>"))

    def test_alias_pointer(self):
        e = dump.extract(self.data, T, BLOCK)
        self.assertEqual(e[2].alias, 0)
        back = dump.parse_block(dump.format_block(e, T))
        self.assertEqual([(x.index, x.offset, x.length, x.text, x.alias) for x in back],
                         [(x.index, x.offset, x.length, x.text, x.alias) for x in e])

    def test_format_breaks_lines(self):
        s = dump.format_block(dump.extract(self.data, T, BLOCK), T)
        self.assertIn("## t 0000 @000100 len=4\nあ<NL>\nい<END>\n", s)
        self.assertIn("## t 0002 =0000\n", s)

    def test_fixed(self):
        d = bytes([0x00, 0x01, 0x01, 0x00])
        e = dump.extract(d, T, {"name": "f", "kind": "fixed", "start": "0x0", "count": 2, "size": 2})
        self.assertEqual([x.text for x in e], ["あい", "いあ"])

    def test_gaps(self):
        data = rom_with(0, [0x8100, 0x8108], 0x100, bytes([0x00, 0xFF, 0, 0, 0, 0, 0, 0, 0x01, 0xFF]))
        e = dump.extract(data, T, dict(BLOCK, count=2))
        self.assertEqual(dump.gaps(e), [(0x102, 0x108)])

    def test_utf8_roundtrip_file(self):
        s = dump.format_block(dump.extract(self.data, T, BLOCK), T)
        fd, p = tempfile.mkstemp(suffix=".txt"); os.close(fd)
        dump.write_text(p, s)
        self.assertEqual(dump.read_text(p), s)

W = Table.parse("1000=あ\n0200=1\nFE03=　\nFFFF=<END>!\n")   # 16-bit codes like the game

def words(*ws):
    return b"".join(w.to_bytes(2, "little") for w in ws)

class Scene(unittest.TestCase):
    # bytecode: 002B 0008 FFFF | strings @6: あ あ END, END(empty), 1 END
    BLK = words(0x2B, 0x08, 0xFFFF, 0x10, 0x10, 0xFFFF, 0xFFFF, 0x02, 0xFFFF)

    def test_strings_after_bytecode(self):
        e = dump.extract_scene(self.BLK, W, "scene_341")
        self.assertEqual([(x.offset, x.length, x.text) for x in e],
                         [(6, 6, "ああ<END>"), (12, 2, "<END>"), (14, 4, "1<END>")])

    def test_no_terminator_means_no_strings(self):
        self.assertEqual(dump.extract_scene(words(0x2B, 0x08), W, "s"), [])

    def test_scene_lines_wrap_at_15_full_glyphs_for_display(self):
        blk = words(0xFFFF, *([0x10] * 16), 0xFFFF)
        e = dump.extract_scene(blk, W, "s")
        s = dump.format_block(e, W, wrap=30)
        self.assertIn("あ" * 15 + "\nあ<END>", s)
        self.assertEqual(dump.parse_block(s)[0].text, "あ" * 16 + "<END>")

    def test_wrap_counts_half_width_as_one(self):
        self.assertEqual(dump.wrap_text("1" * 31, W, 30), "1" * 30 + "\n1")

class ListKind(unittest.TestCase):
    def test_consecutive_strings_in_range(self):
        data = bytes(4) + words(0x10, 0xFFFF, 0x02, 0x10, 0xFFFF) + words(0x10, 0xFFFF)
        e = dump.extract(data, W, {"name": "sys", "kind": "list", "start": "0x4", "end": "0xE"})
        self.assertEqual([(x.offset, x.length, x.text) for x in e], [(4, 4, "あ<END>"), (8, 6, "1あ<END>")])

class LineEndings(unittest.TestCase):
    def test_crlf_file_parses_like_lf(self):
        s = dump.format_block(dump.extract_scene(Scene.BLK, W, "scene_341"), W)
        fd, p = tempfile.mkstemp(suffix=".txt"); os.close(fd)
        with open(p, "w", encoding="utf-8", newline="\r\n") as f:     # what a Windows checkout/editor produces
            f.write(s)
        self.assertEqual(dump.parse_block(dump.read_text(p)), dump.parse_block(s))
