import os, shutil, tempfile, unittest
import coverage


def write(d, name, s):
    with open(os.path.join(d, name), "w", encoding="utf-8", newline="\n") as f:
        f.write(s)


JP = ("## scene_900 0000 @000010 len=8\nあいう<END>\n\n"
      "## scene_900 0001 @000018 len=2\n<END>\n\n"
      "## scene_900 0002 @00001A len=6 data\nあい<END>\n\n"
      "## scene_900 0003 =0000\n\n"
      "## scene_900 0004 @000020 len=6\n　…<END>\n\n"
      "## scene_900 0005 @000026 len=8\n霧島唯<END>\n")


class Coverage(unittest.TestCase):
    def setUp(self):
        self.jp, self.en = tempfile.mkdtemp(), tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.jp); self.addCleanup(shutil.rmtree, self.en)
        write(self.jp, "scene_900.txt", JP)

    def test_excludes_data_alias_and_symbol_only(self):
        self.assertEqual(coverage.missing(self.jp, self.en), [("scene_900", 0), ("scene_900", 5)])

    def test_translated_entry_counts(self):
        write(self.en, "scene_900.txt", "## scene_900 0000 @000010 len=8\nHey!<END>\n")
        self.assertEqual(coverage.missing(self.jp, self.en), [("scene_900", 5)])

    def test_japanese_left_in_english_counts_missing(self):
        write(self.en, "scene_900.txt", "## scene_900 0000 @000010 len=8\nHey!<END>\n\n"
                                        "## scene_900 0005 @000026 len=8\n霧島 Yui<END>\n")
        self.assertEqual(coverage.missing(self.jp, self.en), [("scene_900", 5)])

    def test_names_filter_and_range(self):
        write(self.jp, "scene_901.txt", JP.replace("scene_900", "scene_901"))
        self.assertEqual({n for n, _ in coverage.missing(self.jp, self.en, ["scene_901"])}, {"scene_901"})
        self.assertEqual(coverage.expand(["scene_900..scene_901"], self.jp), ["scene_900", "scene_901"])

    def test_avoided_whole_word(self):
        g = os.path.join(self.jp, "glossary.md")
        write(self.jp, "glossary.md",
              "| Japanese | English | Avoid |\n|---|---|---|\n| 唯 | Yui | Yuki, Yuui |\n| 彩香 | Ayaka | |\n")
        self.assertEqual(coverage.avoid_list(g), ["Yuki", "Yuui"])
        write(self.en, "scene_900.txt", "## scene_900 0000 @000010 len=8\nYuki? No, Yukiko.<END>\n\n"
                                        "## scene_900 0005 @000026 len=8\nyuki<END>\n")
        self.assertEqual(coverage.avoided(self.en, g), [("scene_900", 0, "Yuki")])

    def test_avoided_punctuation(self):
        g = os.path.join(self.jp, "glossary.md")
        write(self.jp, "glossary.md", "| Japanese | English | Avoid |\n|---|---|---|\n| ……。 | …… | …. |\n")
        write(self.en, "scene_900.txt", "## scene_900 0000 @000010 len=8\nWho knows….<END>\n\n"
                                        "## scene_900 0005 @000026 len=8\nWait… what?<END>\n")
        self.assertEqual(coverage.avoided(self.en, g), [("scene_900", 0, "….")])
