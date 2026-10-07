import os, unittest
import rom, sysrefs

@unittest.skipUnless(os.path.exists(rom.ROM_PATH), "ROM not present")
class Scan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = rom.load()
        cls.refs = sysrefs.scan(cls.d)
        cls.es = sysrefs.entries(cls.d)

    def test_split_reference_to_attack_message(self):
        idx = next(e.index for e in self.es if rom.pc_to_lorom(e.offset) == 0x8786DF)
        self.assertIn(("split", rom.lorom_to_pc(0x8198AF), idx), {(r.kind, r.at, r.index) for r in self.refs})

    def test_name_table_pointers(self):
        ptr = [r for r in self.refs if r.kind == "ptr24"]
        self.assertGreaterEqual(len(ptr), 200)

    def test_imm16_only_from_confirmed_list(self):
        confirmed = {int(x["at"], 16) for x in sysrefs.load_manual()["confirmed_imm16"]}
        self.assertEqual({r.at for r in self.refs if r.kind == "imm16"}, confirmed)

    def test_full_coverage(self):
        self.assertEqual(sysrefs.coverage(self.refs, self.es, sysrefs.load_manual()), [])
