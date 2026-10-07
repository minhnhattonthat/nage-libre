import os, random, unittest
import compress, decompress, rom

def rt(test, data):
    packed = compress.compress(data)
    out, used = decompress.decompress(packed, 0)
    test.assertEqual(out, data)
    test.assertEqual(used, len(packed))
    return packed

class Synthetic(unittest.TestCase):
    def test_empty(self):
        rt(self, b"")

    def test_literals_with_high_bits_across_flag_groups(self):
        rt(self, bytes([0x81, 0x02, 0xF3, 0x74, 0x95, 0x16, 0xB7, 0x48, 0xC9, 0x1A, 0xEB]))   # 11 literals

    def test_exactly_eight_literals(self):
        rt(self, bytes([0x81, 0x12, 0xA3, 0x34, 0xC5, 0x56, 0xE7, 0x78]))

    def test_specials_and_ring(self):
        rt(self, bytes([0x00, 0xFF, 0x12, 0x00, 0x12, 0xFF, 0x12]))

    def test_word_runs_short_and_long(self):
        rt(self, b"\xfe\x03" * 3 + b"\x11\x22" * 254 + b"\x11\x22" * 300 + b"\x33")

    def test_run_count_exactly_255(self):
        rt(self, b"\x41\x42" + b"\x41\x42" * 255)

    def test_fuzz(self):
        rnd = random.Random(7)
        for _ in range(200):
            n = rnd.randrange(0, 600)
            kind = rnd.randrange(3)
            if kind == 0:
                data = bytes(rnd.randrange(256) for _ in range(n))
            elif kind == 1:
                data = bytes(rnd.choice((0, 0xFF, 0x03, 0xFE)) for _ in range(n))
            else:
                word = bytes([rnd.randrange(256), rnd.randrange(256)])
                data = b"".join(word * rnd.randrange(1, 40) + bytes([rnd.randrange(256)]) for _ in range(n // 20 + 1))
            rt(self, data)

@unittest.skipUnless(os.path.exists(rom.ROM_PATH), "ROM not present")
class GameData(unittest.TestCase):
    def test_every_decompressible_resource_roundtrips(self):
        d = rom.load()
        count = 0
        for r in range(0x530):
            p = int.from_bytes(d[0x50000 + 3 * r: 0x50000 + 3 * r + 3], "little")
            if not p & 0x8000 or (p >> 16) & 0xFE == 0x7E:
                continue
            try:
                blk, _ = decompress.decompress(d, rom.lorom_to_pc(p))
            except (IndexError, ValueError):
                continue
            rt(self, blk)
            count += 1
        self.assertGreater(count, 1000)
