import unittest
import syswidth


def enc(s):
    return b"".join(ord(c).to_bytes(2, "little") for c in s) + b"\xff\xff"


def name_set(surname="", given="Gn", **over):
    t = {i: enc(surname) for i in range(100)}
    t.update({i: enc(given) for i in range(100, 221)})
    t.update({int(k[1:]): enc(v) for k, v in over.items()})
    return t


ORIGINAL = {i: enc("Ѐ" * 3) for i in range(319)}     # stand-in: 3 full-width glyphs (6 columns) everywhere


class Width(unittest.TestCase):
    def test_categories_cover_all_319(self):
        covered = []
        for first, last, _ in syswidth.CATEGORIES.values():
            covered += range(first, last + 1)
        self.assertEqual(sorted(covered), list(range(319)))

    def test_over_budget_names_category(self):
        first, last, cols = syswidth.CATEGORIES["surnames"]
        too_long = b"".join((0x41).to_bytes(2, "little") for _ in range(cols + 1)) + b"\xff\xff"
        with self.assertRaisesRegex(ValueError, "surnames"):
            syswidth.check(first, too_long)
        syswidth.check(first, bytes([0x41, 0x00, 0xFF, 0xFF]))

    def test_names_must_be_a_complete_set(self):
        with self.assertRaisesRegex(ValueError, "complete set"):
            syswidth.check_names({2: enc(""), 147: enc("Shizuko")})
        syswidth.check_names({})                                         # no names translated: nothing to check
        surnames_only = {i: enc("") for i in range(100)}
        syswidth.check_names({**surnames_only, 147: enc("Shizuko")}, ORIGINAL)   # untranslated given: JP 6
        with self.assertRaisesRegex(ValueError, r"given name \(entry \d+, 6\)"):        # JP given 6 + surname 5 > 10
            syswidth.check_names({**surnames_only, 0: enc("Abeno")}, ORIGINAL)

    def test_names_combined_field(self):
        syswidth.check_names(name_set(given="Shizuko"))                  # given names only
        syswidth.check_names(name_set(surname="Abe", given="Shizuko"))   # 3 + 7 = 10
        with self.assertRaisesRegex(ValueError, "surname.*given.*10"):
            syswidth.check_names(name_set(surname="Kirishima", given="Shizuko"))

    def test_battle_lines(self):
        texts = dict(name_set(given="Shizuko"))
        texts.update({248: enc("'s attack!"), 249: enc(" took "), 250: enc(" damage!"),
                      263: enc(" was defeated!"), 264: enc(" gold obtained!")})
        syswidth.check_battle(texts, ORIGINAL)                           # 7 + 6 + 5 + 8 = 26 <= 28
        texts[250] = enc(" damage dealt!!")                              # 7 + 6 + 5 + 15 = 33
        with self.assertRaisesRegex(ValueError, "battle line.*249.*250"):
            syswidth.check_battle(texts, ORIGINAL)

    def test_fullwidth_counts_two(self):
        first, last, cols = syswidth.CATEGORIES["birthstones"]
        ok = b"".join((0x0400).to_bytes(2, "little") for _ in range(cols // 2)) + b"\xff\xff"
        syswidth.check(first, ok)
        with self.assertRaises(ValueError):
            syswidth.check(first, (0x0400).to_bytes(2, "little") + ok)
