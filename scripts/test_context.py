import os, unittest
import context, rom, wrap


@unittest.skipUnless(os.path.exists(rom.ROM_PATH), "ROM not present")
class Context(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = rom.load()

    def test_portrait_speaker(self):
        c = context.context(self.d, "scene_310")
        self.assertEqual(c[0].speaker, 0x03)          # なにか学校のようすが (after op 08 0003)
        self.assertEqual(c[6].speaker, 0x69)          # …あなたが霧島唯ね。 (after op 08 0069)
        self.assertEqual(c[10].speaker, 0x03)         # え？　あなた誰よ‼
        self.assertEqual(c[12].speaker, 0x69)
        self.assertEqual(c[6].box, wrap.PORTRAIT)
        self.assertEqual(c[6].op, 0x01)

    def test_op13_slot_speaker(self):
        c = context.context(self.d, "scene_319")
        slots = [x for x in c.values() if x.op == 0x13]
        self.assertTrue(slots)
        for x in slots:
            self.assertIn(x.slot, range(5))
            if len(x.slots) == 1:
                self.assertEqual(x.speaker, x.slot + 1)

    def test_op13_entry_shared_by_several_slots(self):
        c = context.context(self.d, "scene_37D")
        x = c[38]                                     # これでボスと戦えるわね♥: one entry in all five slots
        self.assertEqual(x.slots, (0, 1, 2, 3, 4))
        self.assertEqual(context.speaker_name(x.speaker), "any member")
        self.assertEqual(context.speaker_name((2, 5)), "Mai/Ryoko")

    def test_unknown_speaker_label(self):
        self.assertEqual(context.speaker_name(0x03), "Yui")
        self.assertEqual(context.speaker_name(0x7FF), "id 0x7FF (?)")
        self.assertEqual(context.speaker_name(None), "-")
