import unittest
import labels


class Labels(unittest.TestCase):
    def test_wait_fits_40px(self):
        self.assertTrue(labels.fits("Wait", 40))
        self.assertTrue(labels.fits("Attack", 40))

    def test_long_word_does_not_fit(self):
        self.assertFalse(labels.fits("Pocketbellxx", 40))
        with self.assertRaises(ValueError):
            labels.render("Pocketbellxx", 40)

    def test_render_uses_only_given_indices(self):
        g = labels.render("Save", 40, ink=1, outline=2)
        self.assertEqual(len(g), 16)
        self.assertEqual(len(g[0]), 40)
        self.assertEqual({v for row in g for v in row}, {0, 1, 2})

    def test_to_tiles_shape(self):
        t = labels.to_tiles(labels.render("Item", 40))
        self.assertEqual(len(t), 10)                         # 5 wide x 2 high
        self.assertTrue(all(len(x) == 8 and len(x[0]) == 8 for x in t))

    def test_too_short_area_raises(self):
        with self.assertRaisesRegex(ValueError, "13 px tall"):
            labels.render("Wait", 40, 8)

    def test_blank_label(self):
        self.assertEqual({v for row in labels.render("", 16) for v in row}, {0})

    def test_condensed_spacing_for_one_cell_names(self):
        # 舞 / 唯 are single 16-px cells in the WHO window: fall back to 0 px letter spacing
        self.assertEqual(labels.width("Mai"), 17)
        self.assertTrue(labels.fits("Mai", 16))
        g = labels.render("Yui", 16)
        self.assertEqual(len(g[0]), 16)
        self.assertEqual(g[0][0], 0)
