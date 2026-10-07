import os, shutil, tempfile, unittest
import review, rom, dump


@unittest.skipUnless(os.path.exists(rom.ROM_PATH), "ROM not present")
class Review(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = rom.load()

    def setUp(self):
        self.en = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, self.en)
        with open(os.path.join(self.en, "scene_310.txt"), "w", encoding="utf-8", newline="\n") as f:
            f.write('## scene_310 0006 @0000DA len=22\n…So you\'re "Yui Kirishima".<END>\n')

    def test_rows(self):
        html = review.page(self.d, dump.OUT, self.en, ["scene_310"])
        self.assertIn("あなたが霧島唯ね", html)
        self.assertIn("Yui Kirishima", html)
        self.assertIn('class="missing"', html)          # entry 0000 untranslated
        self.assertIn("22x4", html)

    def test_review_escapes_tags(self):
        html = review.page(self.d, dump.OUT, self.en, ["scene_310"])
        self.assertIn("&lt;END&gt;", html)
        self.assertIn("&quot;Yui Kirishima&quot;", html)
        self.assertNotIn("<END>", html)
