import json, os, unittest
import decompress, rom, mesen

CASES = os.path.join(mesen.WORK, "mem", "decomp_cases.json")

class Synthetic(unittest.TestCase):
    def test_literals_specials_run_end(self):
        # flag byte 0x80: first literal gets bit 7. nibbles: lit 4,1 -> 0xC1 ; lit 4,2 -> 0x42 ;
        # A -> 00 ; B -> FF ; 8 run count 02 -> repeat last two bytes (00 FF) twice ; C -> ring[0]=C1 ; 9 end
        src = bytes([0x80, 0x41, 0x42, 0xAB, 0x80, 0x2C, 0x90])
        out, used = decompress.decompress(src, 0)
        self.assertEqual(out, bytes([0xC1, 0x42, 0x00, 0xFF, 0x00, 0xFF, 0x00, 0xFF, 0xC1]))
        self.assertEqual(used, 7)

@unittest.skipUnless(os.path.exists(CASES), "no captured decompression cases")
class MatchesGame(unittest.TestCase):
    def test_matches_game(self):
        data = rom.load()
        with open(CASES, encoding="utf-8") as f:
            cases = json.load(f)
        for c in cases:
            with open(os.path.join(mesen.WORK, "mem", c["name"] + ".bin"), "rb") as f:
                want = f.read()
            got, used = decompress.decompress(data, int(c["src"], 16))
            self.assertEqual(got, want, c["name"])
            self.assertGreater(used, 0)
