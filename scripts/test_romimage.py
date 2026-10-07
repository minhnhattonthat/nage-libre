import os, unittest
import rom, romimage

class Checksum(unittest.TestCase):
    @unittest.skipUnless(os.path.exists(rom.ROM_PATH), "ROM not present")
    def test_clean_rom_matches_header(self):
        d = rom.load()
        self.assertEqual(romimage.checksum(d), 0xC895)
        self.assertEqual(d[0x7FDE] | d[0x7FDF] << 8, 0xC895)

    def test_power_of_two_is_plain_sum(self):
        data = bytes(range(256)) * 256          # 64 KB
        self.assertEqual(romimage.checksum(data), sum(data) & 0xFFFF)

    def test_tail_is_mirrored(self):
        data = b"\x01" * 0x10000 + b"\x02" * 0x8000      # 96 KB -> 64 KB + 32 KB tail mirrored twice
        self.assertEqual(romimage.checksum(data), (0x10000 + 2 * 2 * 0x8000) & 0xFFFF)

    def test_set_checksum_is_self_consistent(self):
        img = romimage.expand(bytes(0x8000) + b"\x07" * 0x8000, 0x20000)
        romimage.set_checksum(img)
        c = img[0x7FDE] | img[0x7FDF] << 8
        self.assertEqual(c, romimage.checksum(img))
        self.assertEqual(c ^ 0xFFFF, img[0x7FDC] | img[0x7FDD] << 8)

    def test_expand_pads_ff(self):
        img = romimage.expand(b"ab", 5)
        self.assertEqual(bytes(img), b"ab\xff\xff\xff")
