import os, string, unittest
import namevwf, syswidth


def enc(s):
    return b"".join(ord(c).to_bytes(2, "little") for c in s) + b"\xff\xff"


def full_set(surname="Aoi", given="Yui"):
    return {i: enc(surname if i < 100 else given) for i in namevwf.NAMES}


class NameVwf(unittest.TestCase):
    @unittest.skipUnless(os.path.exists(namevwf.ASAR), "asar not installed")
    def test_code_matches_asm(self):
        self.assertEqual(namevwf.assemble(), namevwf.CODE)

    def test_font_covers_letters(self):
        for c in string.ascii_letters + " -.'":
            self.assertLessEqual(namevwf.stroke(ord(c)), 6, c)       # stroke + outline columns fit 8 px

    def test_font_records(self):
        font = namevwf.font_bytes()
        self.assertEqual(len(font), (namevwf.LAST - namevwf.FIRST + 1) * namevwf.RECORD)
        a = (ord("a") - namevwf.FIRST) * namevwf.RECORD
        self.assertEqual(font[a], namevwf.stroke(ord("a")) + 1)

    def test_width(self):
        self.assertEqual(namevwf.width([]), 0)
        self.assertEqual(namevwf.width([ord("l")]), 3)                # 1 px stroke + outline on both sides
        self.assertEqual(namevwf.width([ord("l"), ord("l")]), 5)

    def test_full_names_field(self):
        self.assertFalse(syswidth.full_names({0: enc("Aoi")}))
        syswidth.check_names(full_set())
        syswidth.check_names(full_set(surname="Tsukishima", given="Tsukiyomi"))   # exactly 80 px
        with self.assertRaisesRegex(ValueError, "px > 80"):
            syswidth.check_names(full_set(surname="Tsukishimaa", given="Tsukiyomi"))
        with self.assertRaisesRegex(ValueError, "no name-font glyph"):
            syswidth.check_names(full_set(surname="Aoi!"))
