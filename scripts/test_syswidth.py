import unittest
import syswidth


class Width(unittest.TestCase):
    def test_categories_cover_all_319(self):
        covered = []
        for first, last, _ in syswidth.CATEGORIES.values():
            covered += range(first, last + 1)
        self.assertEqual(sorted(covered), list(range(319)))

    def test_over_budget_names_category(self):
        first, last, cols = syswidth.CATEGORIES["names"]
        too_long = b"".join((0x41).to_bytes(2, "little") for _ in range(cols + 1)) + b"\xff\xff"
        with self.assertRaisesRegex(ValueError, "names"):
            syswidth.check(first, too_long)
        syswidth.check(first, bytes([0x41, 0x00, 0xFF, 0xFF]))

    def test_fullwidth_counts_two(self):
        first, last, cols = syswidth.CATEGORIES["birthstones"]
        ok = b"".join((0x0400).to_bytes(2, "little") for _ in range(cols // 2)) + b"\xff\xff"
        syswidth.check(first, ok)
        with self.assertRaises(ValueError):
            syswidth.check(first, (0x0400).to_bytes(2, "little") + ok)
