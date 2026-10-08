import os, shutil, tempfile, unittest
import shots, tour


class Tour(unittest.TestCase):
    def test_select_keeps_changed_frames(self):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d)

        def img(name, box):
            rows = [bytes(256 * 3) for _ in range(224)]
            if box:
                for y in range(170, 200):
                    rows[y] = b"\xff" * (256 * 3)
            p = os.path.join(d, name); shots.write_png(p, 256, 224, rows); return p
        a, b, c = img("a_00600.png", False), img("b_00615.png", False), img("c_00630.png", True)
        self.assertEqual(tour.select([a, b, c]), [a, c])
