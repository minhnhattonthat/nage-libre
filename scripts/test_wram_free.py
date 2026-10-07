import unittest
import wram_free

class Spans(unittest.TestCase):
    def test_free_spans_between_used_pages(self):
        used = {0x00, 0x01, 0x10, 0x11, 0xFF}
        self.assertEqual(wram_free.free_spans(used), [(0x02, 0x10), (0x12, 0xFF)])

    def test_load_merges_runs(self):
        import tempfile, os
        d = tempfile.mkdtemp()
        for name, lines in (("a", "64 83D607\n"), ("b", "78 82BC48\n64 80F948\n")):
            with open(os.path.join(d, f"wram7f_{name}.txt"), "w", encoding="utf-8") as f:
                f.write(lines)
        self.assertEqual(wram_free.load(d), {0x64: {"83D607", "80F948"}, 0x78: {"82BC48"}})
