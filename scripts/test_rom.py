import os, unittest
import rom

class LoRom(unittest.TestCase):
    def test_bank_mirrors_map_to_same_offset(self):
        self.assertEqual(rom.lorom_to_pc(0x808000), 0)
        self.assertEqual(rom.lorom_to_pc(0x008000), 0)

    def test_bank_end(self):
        self.assertEqual(rom.lorom_to_pc(0x82FFFF), 0x17FFF)

    def test_pc_to_lorom_is_fastrom(self):
        self.assertEqual(rom.pc_to_lorom(0x17FFF), 0x82FFFF)

    def test_roundtrip(self):
        for off in (0, 0x7FFF, 0x8000, 0x123456 % 0x180000, 0x17FFFF):
            self.assertEqual(rom.lorom_to_pc(rom.pc_to_lorom(off)), off)

    def test_rejects_non_rom(self):
        for addr in (0x7E2000, 0x7FA000, 0x002000):
            with self.assertRaises(ValueError):
                rom.lorom_to_pc(addr)

    @unittest.skipUnless(os.path.exists(rom.ROM_PATH), "ROM not present")
    def test_load_size(self):
        self.assertEqual(len(rom.load()), 0x180000)
