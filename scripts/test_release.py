import os, shutil, tempfile, unittest
import bps, release, rom


@unittest.skipUnless(os.path.exists(rom.ROM_PATH), "ROM not present")
class Release(unittest.TestCase):
    def test_release_bps_reproduces_build(self):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d)
        out = release.make(d, version="test")
        clean = rom.load()
        patched = bps.apply(clean, open(out["bps"], "rb").read())
        self.assertEqual(release.crc32_bytes(patched), out["patched_crc32"])
        readme = open(out["readme"], encoding="utf-8").read()
        self.assertIn(f"{release.crc32_bytes(clean):08X}", readme)
        self.assertIn("vtest", readme)
        self.assertTrue(os.path.exists(out["manifest"]))
