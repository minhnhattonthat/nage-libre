import unittest
import syslayout, sysrefs
from dump import Entry

def E(i, off, n):
    return Entry("system", i, off, n, "")

DATA = bytearray(0x100)
DATA[0x10:0x14] = bytes.fromhex("1000ffff")          # entry 0 @0x10 (len 4)
DATA[0x14:0x1A] = bytes.fromhex("12001400ffff")      # entry 1 @0x14 (len 6)
ES = [E(0, 0x10, 4), E(1, 0x14, 6)]


class Layout(unittest.TestCase):
    def test_order_and_addresses(self):
        blob, new = syslayout.layout(ES, {1: bytes.fromhex("41004200430044004500ffff")}, bytes(DATA), {})
        self.assertEqual(blob, bytes.fromhex("1000ffff") + bytes.fromhex("41004200430044004500ffff"))
        self.assertEqual(new, {0: 0xBF8000, 1: 0xBF8004})

    def test_stride_padding_and_overflow(self):
        blob, _ = syslayout.layout(ES, {0: bytes.fromhex("4100ffff")}, bytes(DATA), {0: 8})
        self.assertEqual(blob[:8], bytes.fromhex("4100fe03fe03ffff"))
        with self.assertRaisesRegex(ValueError, "stride"):
            syslayout.layout(ES, {0: bytes.fromhex("41004200430044004500ffff")}, bytes(DATA), {0: 8})

    def test_overflow_rejected(self):
        big = [E(i, 0x10, 4) for i in range(0x3000)]
        with self.assertRaisesRegex(ValueError, "bank"):
            syslayout.layout(big, {}, bytes(DATA), {})

    def test_all_kinds_patched_consistently(self):
        d = bytearray(0x100)
        d[0x40:0x4C] = bytes.fromhex("a914850 9a980850aa987850b".replace(" ", ""))   # split -> $878014
        d[0x60:0x63] = bytes.fromhex("148087")                                      # ptr24 -> $878014
        d[0x70:0x73] = bytes.fromhex("a91480")                                      # imm16 -> $8014
        refs = [sysrefs.Ref("split", 0x40, 1), sysrefs.Ref("ptr24", 0x60, 1), sysrefs.Ref("imm16", 0x70, 1)]
        p = {off: new for off, old, new in syslayout.patches(refs, {1: 0xBF8004}, bytes(d))}
        self.assertEqual(p[0x41], bytes([0x04]))
        self.assertEqual(p[0x45], bytes([0x80]))
        self.assertEqual(p[0x49], bytes([0xBF]))
        self.assertEqual(p[0x60], bytes.fromhex("0480bf"))
        self.assertEqual(p[0x71], bytes.fromhex("0480"))

    def test_marker_fill_keeps_lengths(self):
        filled = bytearray(DATA)
        for off, old, new in syslayout.marker_fill(ES, bytes(DATA)):
            filled[off:off + len(new)] = new
        self.assertEqual(bytes(filled[0x10:0x1A]), bytes.fromhex("fc03ffff" + "fc03fc03ffff"))
