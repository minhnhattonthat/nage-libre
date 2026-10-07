import os, unittest
import bytecode, dump, layout, rom
from tbl import Table

T = {0x2B: {"words": 2, "offsets": [1]}, 0x0A: {"words": 3, "offsets": [2]}, 0x20: {"words": 1, "offsets": []}}
W = Table.parse("1000=あ\n1200=い\nFFFF=<END>!\n")

def words(*ws):
    return b"".join(w.to_bytes(2, "little") for w in ws)

# bytecode (10 words = 0x14 bytes): 2B 0014 | 0A 0005 0018 | 2B 0014 | 2B 001C | FFFF
# strings @0x14: "あ" END ; data @0x18: 0001 FFFF ; @0x1C: "い" END
BLK = words(0x2B, 0x14, 0x0A, 0x05, 0x18, 0x2B, 0x14, 0x2B, 0x1C, 0xFFFF,
            0x10, 0xFFFF, 0x0001, 0xFFFF, 0x12, 0xFFFF)

def entries(blk):
    es = dump.extract_scene(blk, W, "s")
    es[1].data = True
    return es

class Layout(unittest.TestCase):
    def test_identity(self):
        self.assertEqual(layout.rebuild(BLK, entries(BLK), {}, T), BLK)

    def test_all_references_follow_moved_entry(self):
        new = layout.rebuild(BLK, entries(BLK), {0: words(0x10, 0x10, 0x10, 0xFFFF)}, T)
        ops = bytecode.parse(new, T)
        self.assertEqual([o.operands for o in ops], [[0x14], [0x05, 0x1C], [0x14], [0x20]])
        self.assertEqual(new[0x1C:0x20], words(0x0001, 0xFFFF))           # data moved intact
        self.assertEqual(new[0x20:], words(0x12, 0xFFFF))

    def test_data_entry_text_rejected(self):
        with self.assertRaisesRegex(ValueError, "data entry"):
            layout.rebuild(BLK, entries(BLK), {1: words(0x10, 0xFFFF)}, T)

    def test_operand_not_on_entry_start(self):
        bad = bytearray(BLK); bad[2:4] = (0x16).to_bytes(2, "little")   # middle of entry 0
        with self.assertRaisesRegex(ValueError, "not an entry start"):
            layout.rebuild(bytes(bad), entries(bytes(bad)), {}, T)

    def test_text_must_end_with_terminator(self):
        with self.assertRaisesRegex(ValueError, "FFFF"):
            layout.rebuild(BLK, entries(BLK), {0: words(0x10)}, T)

@unittest.skipUnless(os.path.exists(rom.ROM_PATH), "ROM not present")
class GameBlocks(unittest.TestCase):
    def test_identity_rebuild_of_every_scene_block(self):
        d, m, t = rom.load(), dump.load_map(), Table.load(dump.TBL)
        for r in range(0x30F, 0x45C):
            name = f"scene_{r:03X}"
            blk = dump.source(d, name, m)
            self.assertEqual(layout.rebuild(blk, dump.extract_scene(blk, t, name), {}), blk, name)
