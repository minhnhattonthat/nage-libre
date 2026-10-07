import os, unittest
import mesen, rom

@unittest.skipUnless(os.path.exists(rom.ROM_PATH), "ROM not present")
class MesenSmoke(unittest.TestCase):
    def test_smoke(self):
        rc = mesen.run(os.path.join(rom.ROOT, "scripts", "mesen", "smoke.lua"), timeout=120)
        self.assertEqual(rc, 0)
        with open(os.path.join(mesen.WORK, "shots", "smoke.png"), "rb") as f:
            self.assertEqual(f.read(8), b"\x89PNG\r\n\x1a\n")
        with open(os.path.join(mesen.WORK, "trace", "smoke.txt"), encoding="utf-8") as f:
            vals = dict(kv.split("=") for kv in f.read().split())
        self.assertGreater(int(vals["reads"]), 0)
        self.assertLess(int(vals["maxRom"]), 0x180000)
        self.assertIn(int(vals["loadedFrame"]), range(118, 124))

@unittest.skipUnless(os.path.exists(rom.ROM_PATH), "ROM not present")
class RomPath(unittest.TestCase):
    def test_runs_another_rom(self):
        import shutil, tempfile
        d = tempfile.mkdtemp()
        copy = os.path.join(d, "copy.sfc")
        shutil.copy(rom.ROM_PATH, copy)
        self.assertEqual(mesen.run(os.path.join(rom.ROOT, "scripts", "mesen", "smoke.lua"), timeout=120, rom_path=copy), 0)
        shutil.rmtree(d)
