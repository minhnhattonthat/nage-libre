import os, unittest
import disasm, rom

@unittest.skipUnless(os.path.exists(rom.ROM_PATH), "ROM not present")
class Disasm(unittest.TestCase):
    def test_reset_area(self):
        lines = disasm.disassemble(0x808000, 0x10, a16=False, i16=False)
        self.assertEqual(lines[0], "808000  nop  ; EA")
        self.assertEqual(lines[3], "808003  bra  -2.b  ; 80 FE")
        self.assertEqual(lines[4], "808005  rep #$30  ; C2 30")
        # after rep #$30 the accumulator is 16-bit: 3-byte immediate
        self.assertEqual(lines[10], "80800C  lda #$0000.w  ; A9 00 00")

    def test_initial_width_flags(self):
        wide = disasm.disassemble(0x80F390, 0x08, a16=True, i16=True)
        self.assertEqual(wide[3], "80F395  ldx #$0000.w  ; A2 00 00")
        narrow = disasm.disassemble(0x80F390, 0x08, a16=True, i16=False)
        self.assertEqual(narrow[3], "80F395  ldx #$00.b  ; A2 00")
