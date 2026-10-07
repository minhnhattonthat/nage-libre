import os, struct, tempfile, unittest, zlib
import render_font as rf

class Tiles(unittest.TestCase):
    def test_2bpp_planes(self):
        t = bytes([0x80, 0x80] + [0] * 14)            # row 0: plane0 bit7, plane1 bit7
        px = rf.decode_tile(t, 0, 2)
        self.assertEqual(px[0][0], 3)
        self.assertEqual(px[0][1], 0)

    def test_4bpp_high_planes_at_16(self):
        t = bytearray(32); t[16] = 0x80               # plane2, row 0, pixel 0
        self.assertEqual(rf.decode_tile(bytes(t), 0, 4)[0][0], 4)

    def test_1bpp(self):
        t = bytes([0x01] + [0] * 7)
        self.assertEqual(rf.decode_tile(t, 0, 1)[0][7], 1)

    def test_16x16_seq_vs_vram(self):
        # tile k: plane0 all set when k is odd -> pixel value k % 2
        data = b"".join(bytes([0xFF if k % 2 else 0x00, 0] * 8) for k in range(18))
        seq = rf.glyph(data, 0, 0, 2, 16, "seq")      # tiles 0,1,2,3
        vram = rf.glyph(data, 0, 0, 2, 16, "vram")    # tiles 0,1,16,17
        self.assertEqual((seq[0][0], seq[0][8], seq[8][0], seq[8][8]), (0, 1, 0, 1))
        self.assertEqual((vram[8][0], vram[8][8]), (0, 1))

    def test_16x16_col_major(self):
        # tiles 0..3 with plane0 = k%2 set: col layout is TL=0, BL=1, TR=2, BR=3
        data = b"".join(bytes([0xFF if k % 2 else 0x00, 0] * 8) for k in range(4))
        g = rf.glyph(data, 0, 0, 2, 16, "col")
        self.assertEqual((g[0][0], g[8][0], g[0][8], g[8][8]), (0, 1, 0, 1))

    def test_png_is_valid(self):
        fd, p = tempfile.mkstemp(suffix=".png"); os.close(fd)
        rf.write_png(p, [bytes([255, 0, 0, 0, 255, 0])] * 3)   # 2x3 px
        with open(p, "rb") as f:
            raw = f.read()
        self.assertEqual(raw[:8], b"\x89PNG\r\n\x1a\n")
        w, h = struct.unpack(">II", raw[16:24])
        self.assertEqual((w, h), (2, 3))
        idat = raw[raw.index(b"IDAT") + 4: raw.index(b"IEND") - 8]
        self.assertEqual(len(zlib.decompress(idat)), 3 * (1 + 6))

    def test_row_label_uses_code_step(self):
        data = bytes(0x40 * 32)
        a = rf.render(data, 0, 32, 2, 16, "seq", 0, 1, step=1)
        b = rf.render(data, 0, 32, 2, 16, "seq", 0, 1, step=2)
        self.assertEqual(a[:17], b[:17])               # row 0 label "0000" in both
        self.assertNotEqual(a[17:34], b[17:34])        # row 1: "0010" vs "0020"
