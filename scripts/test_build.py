import os, shutil, tempfile, unittest
import build, bytecode, decompress, dump, rom, romimage
from tbl import Table

def ptr(img, r):
    return rom.lorom_to_pc(int.from_bytes(img[0x50000 + 3 * r: 0x50000 + 3 * r + 3], "little"))

@unittest.skipUnless(os.path.exists(rom.ROM_PATH), "ROM not present")
class Build(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.clean = rom.load()
        cls.img = build.build(cls.clean)

    def test_identity_blocks_decompress_to_original(self):
        for r in range(0x30F, 0x45C):
            self.assertGreaterEqual(ptr(self.img, r), 0x180000)
            self.assertEqual(decompress.decompress(self.img, ptr(self.img, r))[0],
                             decompress.decompress(self.clean, ptr(self.clean, r))[0], f"res {r:03X}")

    def test_size_and_checksum(self):
        self.assertEqual(len(self.img), 0x200000)
        self.assertEqual(self.img[0x7FDE] | self.img[0x7FDF] << 8, romimage.checksum(self.img))

    def test_no_block_crosses_a_bank(self):
        for r in range(0x30F, 0x45C):
            start = ptr(self.img, r)
            used = decompress.decompress(self.img, start)[1]
            self.assertEqual(start // 0x8000, (start + used - 1) // 0x8000, f"res {r:03X}")

    def test_only_expected_bytes_changed_below_new_area(self):
        diff = [i for i in range(0x180000) if self.img[i] != self.clean[i]]
        allowed = set(range(0x50000 + 3 * 0x30F, 0x50000 + 3 * 0x45C)) | set(range(0x7FDC, 0x7FE0))
        allowed |= {at + k for at, old, new in build.relocation_patches(build.WRAM_BASE) for k in range(len(new))}
        self.assertEqual([i for i in diff if i not in allowed], [])

    def test_deterministic_and_clean_untouched(self):
        before = os.path.getmtime(rom.ROM_PATH)
        self.assertEqual(build.build(self.clean), self.img)
        self.assertEqual(os.path.getmtime(rom.ROM_PATH), before)

    def test_rejects_non_clean_rom(self):
        bad = bytearray(self.clean); bad[0x1000] ^= 1
        with self.assertRaisesRegex(build.BuildError, "clean"):
            build.build(bytes(bad))

    def test_relocation_patch_sites_match_clean_rom(self):
        for at, old, new in build.relocation_patches(0x2000):
            self.assertEqual(self.clean[at:at + len(old)], old, f"{at:#x}")

    def _en(self, body):
        d = tempfile.mkdtemp()
        with open(os.path.join(d, "scene_341.txt"), "w", encoding="utf-8") as f:
            f.write(body)
        self.addCleanup(shutil.rmtree, d)
        return d

    def test_growth_text_lands_and_operands_follow(self):
        t = Table.load(dump.TBL)
        jp = dump.extract_scene(dump.source(self.clean, "scene_341", dump.load_map()), t, "scene_341")
        grown = jp[0].text.replace("<END>", "") * 2 + "<END>"
        img = build.build(self.clean, self._en(f"## scene_341 0000 @000000 len=0\n{grown}\n"))
        blk = decompress.decompress(img, ptr(img, 0x341))[0]
        new = dump.extract_scene(blk, t, "scene_341")
        self.assertEqual(new[0].text, grown)
        self.assertEqual([e.text for e in new[1:]], [e.text for e in jp[1:]])
        ops = bytecode.parse(blk)
        starts = {e.offset for e in new}
        self.assertTrue(all(o.operands[k - 1] in starts for o in ops for k in o.offset_operands))

    def test_en_errors_name_file_and_entry(self):
        cases = [("## scene_341 9999 @000000 len=0\nあ<END>\n", "scene_341.txt entry 9999"),
                 ("## scene_341 0000 @000000 len=0\nあ\n", "<END>"),
                 ("## scene_341 0000 @000000 len=0\nQ<END>\n", "scene_341.txt entry 0000")]
        for body, msg in cases:
            with self.assertRaisesRegex(build.BuildError, msg):
                build.build(self.clean, self._en(body))

    def test_edited_data_entry_rejected(self):
        t = Table.load(dump.TBL)
        jp = dump.extract_scene(dump.source(self.clean, "scene_310", dump.load_map()), t, "scene_310")
        data = next(e for e in jp if e.data)
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d)
        with open(os.path.join(d, "scene_310.txt"), "w", encoding="utf-8") as f:
            f.write(f"## scene_310 {data.index:04d} @000000 len=0 data\nあ<END>\n")
        with self.assertRaisesRegex(build.BuildError, "data entry"):
            build.build(self.clean, d)
