import os, shutil, tempfile, unittest
import shots


def solid(path, w, h, rgb):
    shots.write_png(path, w, h, [bytes(rgb) * w for _ in range(h)])


class Shots(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, self.d)

    def test_roundtrip(self):
        p = os.path.join(self.d, "a.png"); solid(p, 4, 3, (10, 20, 30))
        w, h, bpp, rows = shots.read_png(p)
        self.assertEqual((w, h, bpp), (4, 3, 3))
        self.assertEqual(rows[2][:3], bytes([10, 20, 30]))

    def test_band_diff(self):
        a, b = os.path.join(self.d, "a.png"), os.path.join(self.d, "b.png")
        solid(a, 8, 8, (0, 0, 0)); solid(b, 8, 8, (0, 0, 0))
        self.assertEqual(shots.band_diff(a, b, 0, 8), 0.0)
        rows = [bytes(24) for _ in range(8)]; rows[6] = b"\xff" * 24
        shots.write_png(b, 8, 8, rows)
        self.assertAlmostEqual(shots.band_diff(a, b, 4, 8), 0.25)

    def test_sheet(self):
        ps = []
        for i in range(3):
            p = os.path.join(self.d, f"{i}.png"); solid(p, 4, 4, (i * 50, 0, 0)); ps.append(p)
        out = os.path.join(self.d, "s.png")
        shots.sheet(ps, 2, out)
        self.assertEqual(shots.read_png(out)[:2], (2 * 6, 2 * 6))
