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
        allowed |= {at + k for at, old, new in build.english_patches(self.clean) for k in range(len(new))}
        sysp = build.system_patches(self.clean, None, romimage.expand(self.clean, build.SIZE))
        allowed |= {at + k for at, old, new in sysp for k in range(len(new))}
        self.assertEqual([i for i in diff if i not in allowed], [])

    def test_deterministic_and_clean_untouched(self):
        before = os.path.getmtime(rom.ROM_PATH)
        self.assertEqual(build.build(self.clean), self.img)
        self.assertEqual(os.path.getmtime(rom.ROM_PATH), before)

    def test_threshold_and_font_patched(self):
        import fontgen
        for a in build.THRESHOLD_SITES:
            self.assertEqual(self.img[rom.lorom_to_pc(a):rom.lorom_to_pc(a) + 2], b"\x80\x00")
        self.assertEqual(self.img[0x28400:0x29000], fontgen.font_bytes(fontgen.load()))

    def test_halfwidth_digits_untouched(self):
        self.assertEqual(self.img[0x28000:0x28400], self.clean[0x28000:0x28400])

    def test_en_newlines_are_spaces(self):
        img = build.build(self.clean, self._en("## scene_341 0000 @000000 len=0\n<BR>In a\ndistant world<END>\n"))
        blk = decompress.decompress(img, ptr(img, 0x341))[0]
        text = dump.extract_scene(blk, Table.load(build.EN_TBL), "scene_341")[0].text
        self.assertIn("In a distant world", text)

    def test_japanese_in_en_file_names_entry(self):
        with self.assertRaisesRegex(build.BuildError, "scene_341.txt entry 0000: .*table"):
            build.build(self.clean, self._en("## scene_341 0000 @000000 len=0\n遠くの世界<END>\n"))

    def test_overflow_names_box(self):
        with self.assertRaisesRegex(build.BuildError, "scene_341.txt entry 0000: .*lines"):
            build.build(self.clean, self._en("## scene_341 0000 @000000 len=0\n" + "word " * 40 + "<END>\n"))

    def test_hidden_first_line_requires_br(self):
        # scene_341 0000's Japanese starts with a full blank line (hidden above the narration box)
        with self.assertRaisesRegex(build.BuildError, "scene_341.txt entry 0000: .*blank first line.*<BR>"):
            build.build(self.clean, self._en("## scene_341 0000 @000000 len=0\nHello<END>\n"))
        build.build(self.clean, self._en("## scene_341 0000 @000000 len=0\n<BR>Hello<END>\n"))

    def test_trailing_spaces_after_end_ok(self):
        build.build(self.clean, self._en("## scene_341 0000 @000000 len=0\n<BR>Hi<END>   \n"))

    def test_fit_error_states_box_once(self):
        with self.assertRaises(build.BuildError) as cm:
            build.build(self.clean, self._en("## scene_341 0000 @000000 len=0\n" + "word " * 40 + "<END>\n"))
        self.assertEqual(str(cm.exception).count("30"), 1, str(cm.exception))
        self.assertIn("columns over", str(cm.exception))

    def test_system_identity_relocation(self):
        import sysrefs
        es = sysrefs.entries(self.clean)
        for r in sysrefs.scan(self.clean):
            e = es[r.index]
            if r.kind == "ptr24":
                a = int.from_bytes(self.img[r.at:r.at + 3], "little")
            elif r.kind == "imm16":
                a = 0xBF0000 | int.from_bytes(self.img[r.at + 1:r.at + 3], "little")
            else:
                a = self.img[r.at + 9] << 16 | self.img[r.at + 5] << 8 | self.img[r.at + 1]
            self.assertEqual(a >> 16, 0xBF, f"ref {r}")
            off = rom.lorom_to_pc(a)
            self.assertEqual(self.img[off:off + e.length], self.clean[e.offset:e.offset + e.length], f"ref {r}")

    def test_old_system_block_marked(self):
        self.assertEqual(self.img[0x38077:0x3807D], bytes([0xFC, 0x03, 0xFC, 0x03, 0xFF, 0xFF]))   # 桜井<END> -> ■■<END>
        self.assertEqual(self.img[rom.lorom_to_pc(0x878017)], 0x87)                         # window helper untouched

    def test_name_renderer_hooked(self):
        for a in build.NAME_HOOKS:
            self.assertEqual(self.img[rom.lorom_to_pc(a):rom.lorom_to_pc(a) + 3], bytes([0x20, 0xB0, 0xF1]))
        h = rom.lorom_to_pc(build.NAME_HELPER)
        self.assertEqual(self.img[h:h + 12], build.NAME_HELPER_BYTES)

    def test_system_en_width_enforced(self):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d)
        with open(os.path.join(d, "system.txt"), "w", encoding="utf-8") as f:
            f.write("## system 0000 @000000 len=0\nAVeryLongSurnameIndeed<END>\n")
        with self.assertRaisesRegex(build.BuildError, "system.txt entry 0000"):
            build.build(self.clean, d)

    def test_system_en_text_lands(self):
        import sysrefs
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d)
        with open(os.path.join(d, "system.txt"), "w", encoding="utf-8") as f:
            f.write("## system 0248 @000000 len=0\n's attack!<END>\n")
        img = build.build(self.clean, d)
        r = next(r for r in sysrefs.scan(self.clean) if r.index == 248)
        a = img[r.at + 9] << 16 | img[r.at + 5] << 8 | img[r.at + 1]
        off = rom.lorom_to_pc(a)
        self.assertEqual(img[off:off + 22], Table.load(build.EN_TBL).encode("'s attack!<END>"))

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
        grown = "<BR>In a distant world… a voice echoes…<END>"
        img = build.build(self.clean, self._en(f"## scene_341 0000 @000000 len=0\n{grown}\n"))
        blk = decompress.decompress(img, ptr(img, 0x341))[0]
        new = dump.extract_scene(blk, Table.load(build.EN_TBL), "scene_341")
        self.assertEqual(new[0].text.replace(" ", "").replace("　", ""), "Inadistantworld…avoiceechoes…<END>")
        self.assertTrue(new[0].text.startswith("　" * 15))
        self.assertEqual(len(new), len(jp))
        ops = bytecode.parse(blk)
        starts = {e.offset for e in new}
        self.assertTrue(all(o.operands[k - 1] in starts for o in ops for k in o.offset_operands))

    def test_en_errors_name_file_and_entry(self):
        cases = [("## scene_341 9999 @000000 len=0\nHi<END>\n", "scene_341.txt entry 9999"),
                 ("## scene_341 0000 @000000 len=0\nHi\n", "<END>"),
                 ("## scene_341 0000 @000000 len=0\nä<END>\n", "scene_341.txt entry 0000")]
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


@unittest.skipUnless(os.path.exists(rom.ROM_PATH), "ROM not present")
class TranslationInputValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.clean = rom.load()

    def en(self, files):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        for name, body in files.items():
            with open(os.path.join(d, name), "w", encoding="utf-8") as f:
                f.write(body)
        return d

    def fails(self, files, msg):
        with self.assertRaisesRegex(build.BuildError, msg):
            build.build(self.clean, self.en(files))

    def test_data_op_target_digits_entry_rejected(self):
        # scene_310 0025 decodes as "012<END>" but is a data table read by op 09/0A
        self.fails({"scene_310.txt": "## scene_310 0025 @000000 len=0\n111<END>\n"}, "scene_310.txt entry 0025: data entry")

    def test_malformed_en_files_name_the_file(self):
        self.fails({"scene_341.txt": "## scene_341 x\nあ<END>\n"}, "scene_341.txt")
        self.fails({"scene_341.txt": "あ<END>\n## scene_341 0000 @000000 len=0\nあ<END>\n"}, "scene_341.txt")

    def test_empty_en_file_is_identity(self):
        self.assertEqual(build.build(self.clean, self.en({"scene_341.txt": ""})), build.build(self.clean))

    def test_bad_filenames_rejected(self):
        for name in ("scene_0341.txt", "scene_zz.txt", "scene_300.txt", "notes.txt"):
            self.fails({name: ""}, name)

    def test_duplicate_index_and_foreign_header_rejected(self):
        self.fails({"scene_341.txt": "## scene_341 0000 @0 len=0\n<BR>Hi<END>\n\n## scene_341 0000 @0 len=0\n<BR>Yo<END>\n"}, "duplicate")
        self.fails({"scene_341.txt": "## scene_342 0000 @000000 len=0\nあ<END>\n"}, "scene_342")

    def test_missing_en_dir_rejected(self):
        with self.assertRaisesRegex(build.BuildError, "no-such-dir"):
            build.build(self.clean, os.path.join(tempfile.gettempdir(), "no-such-dir"))

    def test_odd_length_and_inner_end_rejected(self):
        self.fails({"scene_341.txt": "## scene_341 0000 @000000 len=0\na<$12><END>\n"}, "odd")
        self.fails({"scene_341.txt": "## scene_341 0000 @000000 len=0\na<END>b<END>\n"}, "<END> before")
