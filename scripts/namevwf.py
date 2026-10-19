"""Battle HUD full names: a narrow proportional font and a renderer (scripts/namevwf.asm) that draws
"given surname" into the name builder's 80-px buffer. Used once every name (system 0-226) is translated."""
import os, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fontgen, rom

ART = os.path.join(rom.ROOT, "font", "name_glyphs.txt")
ASM = os.path.join(rom.ROOT, "scripts", "namevwf.asm")
ASAR = os.path.join(rom.ROOT, "tools", "asar", "asar.exe")
NAMES = range(0, 227)          # surnames 0-99, given names 100-220, boss names 221-226
FIELD_PX = 80                  # the HUD name field: 10 half-width columns
SPACE = 3                      # advance between given name and surname (namevwf.asm !SPACE)
HOOK = 0x81BA86                # name builder body, after its jsl $80888D
HOOK_ORIG = bytes.fromhex("5aa04001a90000")                       # phy / ldy #$0140 / lda #$0000
HOOK_NEW = bytes.fromhex("2200c0bf") + bytes.fromhex("4c4ebb")    # jsl CODE_AT / jmp $BB4E (jsl $8088BB / rts)
CODE_AT, FONT_AT = 0xBFC000, 0xBFC200
CODE = bytes.fromhex(
    "08c230d400d402d404da5aa04001a9000088889706d0fa64006864042033c068a2030086042033c0688504688502688500286b85020a"
    "186502aabf58af818509e220bf5aaf81850bc220a709c9fffff026a5001865048500a709c9fffff01838e920000a85020a0a0a0a1865"
    "02aa2078c0e609e60980e160a5002907008502a50029f8ff0a0aa88a186920008504bf02c2bf29ff00ebdaa602f0044acad0fcfae220"
    "48eb17069706c2209818692000a8e2206817069706c2209838e91f00a8e8e404d0cabfe0c1bf29ff00186500850060")
FIRST, LAST, RECORD = 0x20, 0x7F, 34

_GLYPHS = None


def glyphs():
    global _GLYPHS
    if _GLYPHS is None:
        with open(ART, encoding="utf-8") as f:
            _GLYPHS = fontgen.parse(f.read())
    return _GLYPHS


def stroke(code):
    """Stroke width in px (art is left-aligned); ValueError if the font has no such glyph."""
    rows = glyphs().get(code)
    if rows is None:
        raise ValueError(f"no name-font glyph for {chr(code)!r}")
    if code == 0x20:
        return 2
    return max(r.rindex("#") for r in rows if "#" in r) + 1


def width(codes):
    """Rendered px of a name part (codes < 0x80): strokes + 1 px gaps + the outline column on each side."""
    return sum(stroke(c) for c in codes) + len(codes) + 1 if codes else 0


def font_bytes():
    out = bytearray()
    for code in range(FIRST, LAST + 1):
        if code not in glyphs():
            out += bytes(RECORD)
            continue
        g = fontgen.glyph_bytes(glyphs()[code])      # top tile then bottom tile = rows 0-15 x (plane 0, plane 1)
        out += bytes([stroke(code) + 1, 0]) + g
    return bytes(out)


def patches(img):
    """(file offset, expected original bytes, new bytes) installing the renderer and its font."""
    font = font_bytes()
    assert CODE_AT + len(CODE) <= FONT_AT and rom.lorom_to_pc(FONT_AT) + len(font) <= 0x200000
    at = [rom.lorom_to_pc(CODE_AT), rom.lorom_to_pc(FONT_AT)]
    return [(rom.lorom_to_pc(HOOK), HOOK_ORIG, HOOK_NEW),
            (at[0], bytes(img[at[0]:at[0] + len(CODE)]), CODE),
            (at[1], bytes(img[at[1]:at[1] + len(font)]), font)]


def assemble():
    """CODE from namevwf.asm with asar (tools/ is not in git; used by the test when present)."""
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "blank.sfc")
        with open(p, "wb") as f:
            f.write(b"\xff" * 0x200000)
        subprocess.run([ASAR, "--no-title-check", "--fix-checksum=off", ASM, p], check=True, capture_output=True)
        with open(p, "rb") as f:
            f.seek(rom.lorom_to_pc(CODE_AT))
            return f.read(FONT_AT - CODE_AT).rstrip(b"\xff")
