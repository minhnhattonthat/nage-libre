import glob, os, unittest
import bytecode, dump, rom

def blocks():
    d, m = rom.load(), dump.load_map()
    for p in sorted(glob.glob(os.path.join(dump.OUT, "scene_*.txt"))):
        name = os.path.splitext(os.path.basename(p))[0]
        yield name, dump.source(d, name, m), dump.parse_block(dump.read_text(p))

class Synthetic(unittest.TestCase):
    T = {0x2B: {"words": 2, "offsets": [1]}, 0x20: {"words": 1, "offsets": []}}

    def test_parse_simple(self):
        blk = bytes.fromhex("2b00" "0a00" "2000" "ffff" "1000ffff")
        ops = bytecode.parse(blk, self.T)
        self.assertEqual([(o.pos, o.opcode, o.operands, o.offset_operands) for o in ops],
                         [(0, 0x2B, [0x000A], [1]), (4, 0x20, [], [])])
        self.assertEqual(bytecode.code_end(blk), 8)

    def test_unknown_opcode_reports_position(self):
        with self.assertRaisesRegex(ValueError, "unknown opcode 0077 at 0x2"):
            bytecode.parse(bytes.fromhex("2000" "7700" "ffff"), self.T)

    def test_zero_word_entry_rejected_not_looping(self):
        with self.assertRaisesRegex(ValueError, "words"):
            bytecode.parse(bytes.fromhex("2900" "ffff"), {0x29: {"words": 0, "offsets": []}})

    def test_parse_end_matches_first_ffff(self):
        # operand FFFF before the real terminator: parse ends later than the first-FFFF scan -> error
        with self.assertRaisesRegex(ValueError, "terminator"):
            bytecode.parse(bytes.fromhex("2b00" "ffff" "2000" "ffff"), self.T)

@unittest.skipUnless(os.path.exists(rom.ROM_PATH), "ROM not present")
class GameBlocks(unittest.TestCase):
    def test_all_scene_blocks_parse_and_offsets_hit_entries(self):
        failures, refs = [], 0
        for name, blk, entries in blocks():
            starts = {e.offset for e in entries}
            try:
                ops = bytecode.parse(blk)
            except ValueError as e:
                failures.append(f"{name}: {e}")
                continue
            for op in ops:
                for k in op.offset_operands:
                    refs += 1
                    if op.operands[k - 1] not in starts:
                        failures.append(f"{name}: op {op.opcode:02X} at {op.pos:#x} operand {k} = "
                                        f"{op.operands[k - 1]:#x} is not an entry start")
        self.assertEqual(failures[:20], [])
        self.assertGreater(refs, 2900)          # ~2617 text + ~351 data references measured

    def test_narration_print_op(self):
        d, m = rom.load(), dump.load_map()
        ops = bytecode.parse(dump.source(d, "scene_341", m))
        self.assertIn((0x2B, [0x0124]), [(o.opcode, o.operands) for o in ops])
