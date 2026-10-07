import os, random, unittest, zlib
import bps, rom

class Bps(unittest.TestCase):
    def roundtrip(self, src, dst):
        p = bps.create(src, dst)
        self.assertEqual(p[:4], b"BPS1")
        self.assertEqual(bps.apply(src, p), dst)
        self.assertEqual(int.from_bytes(p[-8:-4], "little"), zlib.crc32(dst))
        return p

    def test_identical(self):
        self.roundtrip(b"abcdef" * 50, b"abcdef" * 50)

    def test_changes_growth_and_runs(self):
        rnd = random.Random(1)
        src = bytes(rnd.randrange(256) for _ in range(5000))
        dst = bytearray(src)
        dst[100:110] = b"XXXXXXXXXX"
        dst += b"\xff" * 4000 + bytes(rnd.randrange(256) for _ in range(300)) + b"\x00" * 50
        p = self.roundtrip(src, bytes(dst))
        self.assertLess(len(p), 1200)          # FF run must be a TargetCopy, not 4000 literals

    def test_shrink(self):
        self.roundtrip(b"0123456789" * 10, b"0123")

    def test_corrupt_patch_rejected(self):
        p = bytearray(bps.create(b"aaaa", b"abca"))
        p[5] ^= 1
        with self.assertRaises(ValueError):
            bps.apply(b"aaaa", bytes(p))

    def test_wrong_source_rejected(self):
        p = bps.create(b"aaaa", b"abca")
        with self.assertRaises(ValueError):
            bps.apply(b"aaab", p)
