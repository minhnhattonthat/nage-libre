import os, unittest
import gfxsurvey, resources, rom


@unittest.skipUnless(os.path.exists(rom.ROM_PATH), "ROM not present")
class Survey(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = rom.load()

    def test_candidates_include_menu_and_skip_scenes(self):
        ids = {rid for rid, _ in gfxsurvey.candidates(self.d)}
        self.assertIn(0x27B, ids)
        self.assertFalse(ids & set(resources.SCENES))

    def test_find_tiles_locates_menu_label(self):
        tile = resources.load(self.d, 0x27B)[0x110:0x120]       # 待 top-left
        self.assertIn((0x27B, 0x110), gfxsurvey.find_tiles(self.d, tile))
