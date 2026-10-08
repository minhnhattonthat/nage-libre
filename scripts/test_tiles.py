import os, unittest
import resources, rom, tiles


@unittest.skipUnless(os.path.exists(rom.ROM_PATH), "ROM not present")
class Tiles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = rom.load()
        cls.menu = resources.load(cls.d, 0x27B)

    def test_menu_resource_size(self):
        self.assertEqual(len(self.menu), 2048)

    def test_encode_decode_roundtrip_2bpp(self):
        self.assertEqual(tiles.encode(tiles.decode(self.menu, 2), 2), self.menu)

    def test_encode_decode_roundtrip_4bpp(self):
        self.assertEqual(tiles.encode(tiles.decode(self.menu, 4), 4), self.menu)

    def test_known_pixels(self):
        t = tiles.decode(self.menu, 2)[0x10]            # 待 top-left: stroke 1, outline 2, shade 3
        self.assertEqual(t[2][2:5], [2, 3, 1])           # row 2: "+#." starting at column 2
        self.assertEqual(t[1][3:6], [2, 2, 2])           # row 1: "+++"; row 0 is blank
        self.assertEqual(t[0], [0] * 8)

    def test_sheet_is_png(self):
        self.assertTrue(tiles.sheet(tiles.decode(self.menu, 2)).startswith(b"\x89PNG"))
