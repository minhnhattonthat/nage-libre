import glob, os, unittest
import dump, rom
from tbl import Table

@unittest.skipUnless(os.path.exists(rom.ROM_PATH) and glob.glob(os.path.join(dump.OUT, "*.txt")), "no ROM or dump")
class RoundTrip(unittest.TestCase):
    def test_every_message_reencodes_identically(self):
        data, blocks = rom.load(), dump.load_map()
        table = Table.load(dump.TBL)
        failures, count = [], 0
        for path in sorted(glob.glob(os.path.join(dump.OUT, "*.txt"))):
            name = os.path.splitext(os.path.basename(path))[0]
            src = dump.source(data, name, blocks)
            for e in dump.parse_block(dump.read_text(path)):
                if e.alias is not None:
                    continue
                count += 1
                if table.encode(e.text) != src[e.offset:e.offset + e.length]:
                    failures.append(f"{name} {e.index:04d} @{e.offset:06X}")
        self.assertGreater(count, 5000)
        self.assertEqual(failures, [], f"{len(failures)}/{count} messages differ")

    def test_scene_string_areas_fully_covered(self):
        data, blocks = rom.load(), dump.load_map()
        for path in sorted(glob.glob(os.path.join(dump.OUT, "scene_*.txt"))):
            name = os.path.splitext(os.path.basename(path))[0]
            blk = dump.source(data, name, blocks)
            entries = dump.parse_block(dump.read_text(path))
            self.assertEqual(entries[-1].offset + entries[-1].length, len(blk), name)
            self.assertEqual(dump.gaps(entries), [], name)
