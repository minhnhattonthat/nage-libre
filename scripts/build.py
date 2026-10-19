"""Build the patched ROM: rebuild + recompress every scene block into an expanded 2 MB ROM, write a BPS patch.

    python -I scripts/build.py [--en script/en] [--out build]
"""
import argparse, glob, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bps, compress, decompress, dump, entable, fontgen, labels, layout, namevwf, resources, rom, romimage, syslayout, sysrefs, syswidth, tiles, wrap
from tbl import Table

CLEAN_CHECKSUM = 0xC895
SIZE = 0x200000
FREE_START = 0x180000
RES_TABLE = 0x50000
FIRST, LAST = 0x30F, 0x45B
WRAM_BASE = 0x64C0          # scene buffer $7F:WRAM_BASE (notes/wram.md)
WRAM_WINDOW = 0x1340        # max decompressed block size (notes/wram.md)
ADC_SITES = [0x83840D, 0x838463, 0x838755, 0x8388E9, 0x838C13, 0x8396A9, 0x83978F, 0x839BAD]
LOADER = 0x8380F0           # lda #$C0 / sta $06 / lda #$64 / sta $07
EN_TBL = entable.OUT
THRESHOLD_SITES = [0x80F3AE, 0x80F3C7, 0x80F426]   # operand of cmp #$0010 (half-width glyph threshold)
SECOND_WAIT = 0x80F5F4      # string printer's 2nd per-glyph frame wait: NOPed so English (2x the glyphs) types at JP speed
PORTRAIT_FRAMES = 0x80F581  # talking-portrait printer: lda #6 frames per glyph -> 3, same reason
BLANK = bytes([0xFE, 0x03])                        # full-width blank glyph 03FE
FONT_AT = 0x28000 + 0x20 * 0x20                    # glyphs for codes 0x20-0x7F (English = ASCII)
NAME_HOOKS = [0x81BACC, 0x81BB2A]                  # ldy #$0040 in the name builder's glyph copy loops
NAME_HELPER = 0x81F1B0                             # free space in bank $81
# ldy #$0040 / cpx #$1000 / bcs +3 / ldy #$0020 / rts : half-width codes (< 0x80, X = code<<5 < 0x1000) copy 0x20 bytes
NAME_HELPER_BYTES = bytes([0xA0, 0x40, 0x00, 0xE0, 0x00, 0x10, 0xB0, 0x03, 0xA0, 0x20, 0x00, 0x60])
# Birthstone bonus (system 0258): JP appends it to "<name>'s attack!" on line 1, which English overflows (wraps over
# the window border, leaves tiles the line clear never reaches). The two damage routines' `jsl $80F4A7` that print
# it jump to BONUS_HELPER instead: bonus on line 2, BONUS_FRAMES wait, clear line 2; the routine then prints the
# damage line there as before. Applied when 0258 is translated (identity builds stay byte-exact).
BONUS_SITES = [0x819988, 0x819A20]                 # damage to player / to enemy
BONUS_HELPER = 0x81F1C0                            # free space in bank $81, after NAME_HELPER
BONUS_FRAMES = 60
LINE_CLEAR = 244                                   # 28 blanks: the battle window's line clear (819D93)
# Save/load file rows: 290 at column 9, slot number at $11, stage number at $15 then 291 (JP 面). English reads
# "File 1  Stage 2": the slot number moves to $0E (after "File", 4 columns vs JP 8), the stage (or "none"/"EX") to $11,
# and STAGE_HELPER prints 291 before the number; the routine's own 291 print after it is NOPed.
# Sites: lda #$rrCC / sta $1141, rows 0A/0C/0E, save then load menu.
SLOT_COL_SITES = [0x87E882, 0x87E88F, 0x87E89C, 0x87EC8D, 0x87EC9A, 0x87ECA7]
STAGE_COL_SITES = [0x87E8AE, 0x87E911, 0x87E974, 0x87ECB4, 0x87ED17, 0x87ED7A]
SLOT_COL, STAGE_COL = 0x0E, 0x11
STAGE_NUM_SITES = [0x87E8C4, 0x87E927, 0x87E98A, 0x87ECCA, 0x87ED2D, 0x87ED90]   # ldx #2 / jsl $80F6E8; +25: 291 print
STAGE_HELPER = 0x81F200                            # free space in bank $81, after BONUS_HELPER


def stage_helper_bytes(label):
    """65816 for STAGE_HELPER (jsl, A = stage): print `label` (CPU address of 291), then the number, no padding."""
    return (bytes([0x08, 0xC2, 0x30, 0x48])                                   # php / rep #$30 / pha
            + bytes([0xA9, label & 0xFF, (label >> 8) & 0xFF, 0x85, 0x09])    # lda #label / sta $09
            + bytes([0xE2, 0x20, 0xA9, label >> 16, 0x85, 0x0B, 0xC2, 0x20])  # sep #$20 / lda #bank / sta $0B / rep #$20
            + bytes([0x22, 0xA7, 0xF4, 0x80, 0x68])                           # jsl $80F4A7 / pla
            + bytes([0xA2, 0x01, 0x00, 0x22, 0xE8, 0xF6, 0x80, 0x28, 0x6B]))  # ldx #1 / jsl $80F6E8 / plp / rtl


def bonus_helper_bytes(clear):
    """65816 for BONUS_HELPER (entered by jsl, $09-$0B -> bonus string); `clear` = CPU address of LINE_CLEAR."""
    line2 = bytes([0xA2, 0x02, 0x17, 0x8E, 0x41, 0x11])                    # ldx #$1702 / stx $1141 (col 2, row $17)
    draw = bytes([0x22, 0xA7, 0xF4, 0x80])                                  # jsl $80F4A7 (draw string [$09])
    return (bytes([0x08, 0xC2, 0x30, 0xDA]) + line2 + draw                  # php / rep #$30 / phx
            + bytes([0xA2, BONUS_FRAMES, 0x00])                             # ldx #frames
            + bytes([0x22, 0xB6, 0x85, 0x80, 0xCA, 0xD0, 0xF9])             # -: jsl $8085B6 (1 frame) / dex / bne -
            + bytes([0xA9, clear & 0xFF, (clear >> 8) & 0xFF, 0x85, 0x09])  # lda #clear / sta $09
            + bytes([0xE2, 0x20, 0xA9, clear >> 16, 0x85, 0x0B, 0xC2, 0x20])  # sep #$20 / lda #bank / sta $0B / rep #$20
            + line2 + draw + bytes([0xFA, 0x28, 0x6B]))                     # plx / plp / rtl


SYSTEM_EN = "system.txt"
GFX_EDITS = os.path.join(rom.ROOT, "gfx", "edits.json")    # graphics label edits (notes/graphics.md)


class BuildError(Exception):
    pass


def relocation_patches(base):
    """(file offset, expected original bytes, new bytes) moving the scene buffer to $7F:base."""
    if base == 0x64C0:
        return []
    lo, hi = base & 0xFF, base >> 8
    p = [(rom.lorom_to_pc(a), bytes([0x69, 0xC0, 0x64]), bytes([0x69, lo, hi])) for a in ADC_SITES]
    p.append((rom.lorom_to_pc(LOADER), bytes.fromhex("a9c08506a9648507"), bytes([0xA9, lo, 0x85, 0x06, 0xA9, hi, 0x85, 0x07])))
    return p


def english_patches(clean):
    """(file offset, expected original bytes, new bytes): threshold 0x10 -> 0x80 and the English font."""
    p = [(rom.lorom_to_pc(a), bytes([0x10, 0x00]), bytes([0x80, 0x00])) for a in THRESHOLD_SITES]
    p.append((rom.lorom_to_pc(SECOND_WAIT), bytes.fromhex("22b68580"), bytes.fromhex("eaeaeaea")))
    p.append((rom.lorom_to_pc(PORTRAIT_FRAMES), bytes.fromhex("a90600"), bytes.fromhex("a90300")))
    font = fontgen.font_bytes(fontgen.load())
    p.append((FONT_AT, bytes(clean[FONT_AT:FONT_AT + len(font)]), font))
    return p


WARNINGS = []      # non-fatal text-layout findings of the last build (orphan words after a wrap)


def en_texts(path, entries, table, boxes, jp_block=b""):
    """{index: encoded bytes} for one translated scene file, validated against the JP entries."""
    fname = os.path.basename(path)
    block = os.path.splitext(fname)[0]
    raw = dump.read_text(path)
    if not raw.strip():
        return {}
    try:
        parsed = dump.parse_block(raw, joiner=" ")
    except ValueError as x:
        raise BuildError(f"{fname}: {x}") from None
    by_index = {e.index: e for e in entries}
    out, seen = {}, set()
    for t in parsed:
        where = f"{fname} entry {t.index:04d}"
        if t.block != block:
            raise BuildError(f"{where}: header names {t.block}, expected {block}")
        if t.index in seen:
            raise BuildError(f"{where}: duplicate entry index")
        seen.add(t.index)
        e = by_index.get(t.index)
        if e is None:
            raise BuildError(f"{where}: the block has no such entry")
        if e.data:
            if t.text != e.text:
                raise BuildError(f"{where}: data entry was edited (data entries must stay exactly as dumped)")
            continue
        text = t.text.rstrip()
        if not text.endswith("<END>"):
            raise BuildError(f"{where}: text must end with <END>")
        box = boxes.get(e.offset, wrap.FULL)
        try:
            b = table.encode(wrap.fit(text, box, table))
        except wrap.FitError as x:                   # message already names the box
            raise BuildError(f"{where}: {x}") from None
        except ValueError as x:
            raise BuildError(f"{where}: {x} (box {box.cols}x{box.lines})") from None
        WARNINGS.extend(f"{where}: awkward wrap: {seg}" for seg in wrap.orphans(text, box, table))
        if len(b) % 2:
            raise BuildError(f"{where}: encodes to an odd number of bytes (a raw <$..> code is 1 byte short)")
        if any(b[i:i + 2] == dump.END for i in range(0, len(b) - 2, 2)):
            raise BuildError(f"{where}: <END> before the end of the text (text after it would never show)")
        blank_line = BLANK * (box.cols // 2)
        if box.lines > 1 and jp_block[e.offset:e.offset + len(blank_line)] == blank_line and not text.startswith("<BR>"):
            raise BuildError(f"{where}: the Japanese starts with a blank first line (hidden/spacer line in this box); "
                             f"start the English with <BR>")
        out[t.index] = b
    return out


def system_texts(path, entries, table, original):
    """{index: encoded bytes} from script/en/system.txt (no box wrapping; per-category width check)."""
    raw = dump.read_text(path)
    if not raw.strip():
        return {}
    try:
        parsed = dump.parse_block(raw, joiner=" ")
    except ValueError as x:
        raise BuildError(f"{SYSTEM_EN}: {x}") from None
    out = {}
    for t in parsed:
        where = f"{SYSTEM_EN} entry {t.index:04d}"
        if t.block != "system" or not 0 <= t.index < len(entries):
            raise BuildError(f"{where}: no such system entry")
        if t.index in out:
            raise BuildError(f"{where}: duplicate entry index")
        text = t.text.rstrip()
        if not text.endswith("<END>"):
            raise BuildError(f"{where}: text must end with <END>")
        try:
            b = table.encode(text)
            if len(b) % 2 or any(b[i:i + 2] == dump.END for i in range(0, len(b) - 2, 2)):
                raise ValueError("bad encoding (odd length or <END> inside the text)")
            syswidth.check(t.index, b)
        except ValueError as x:
            raise BuildError(f"{where}: {x}") from None
        out[t.index] = b
    try:
        syswidth.check_names(out, original)
        syswidth.check_battle(out, original)
    except ValueError as x:
        raise BuildError(f"{SYSTEM_EN}: {x}") from None
    return out


def system_patches(clean, en_dir, img):
    """Relocate the bank-$87 system text to bank $BF: blob, reference patches, old-block markers, name-renderer hook."""
    entries, refs = sysrefs.entries(clean), sysrefs.scan(clean)
    missing = sysrefs.coverage(refs, entries, sysrefs.load_manual())
    if missing:
        raise BuildError(f"system text entries without a known reference: {missing} (run scripts/sysrefs.py)")
    path = os.path.join(en_dir, SYSTEM_EN) if en_dir else None
    original = {e.index: clean[e.offset:e.offset + e.length] for e in entries}
    texts = system_texts(path, entries, Table.load(EN_TBL), original) if path and os.path.exists(path) else {}
    strides = {i: lst["stride"] for lst in sysrefs.load_manual()["lists"] if "stride" in lst
               for i in range(lst["first"], lst["last"] + 1)}
    try:
        blob, new = syslayout.layout(entries, texts, clean, strides)
    except ValueError as x:
        raise BuildError(str(x)) from None
    at = syslayout.BASE_FILE
    p = [(at, bytes(img[at:at + len(blob)]), blob)]
    p += syslayout.patches(refs, new, clean)
    p += syslayout.marker_fill(entries, clean)
    if syswidth.full_names(texts):
        p += namevwf.patches(img)
    else:
        p += [(rom.lorom_to_pc(h), bytes([0xA0, 0x40, 0x00]), bytes([0x20, 0xB0, 0xF1])) for h in NAME_HOOKS]
        h = rom.lorom_to_pc(NAME_HELPER)
        p.append((h, bytes([0xFF]) * len(NAME_HELPER_BYTES), NAME_HELPER_BYTES))
    if 291 in texts:
        p += [(rom.lorom_to_pc(s) + 1, bytes([0x11]), bytes([SLOT_COL])) for s in SLOT_COL_SITES]
        p += [(rom.lorom_to_pc(s) + 1, bytes([0x15]), bytes([STAGE_COL])) for s in STAGE_COL_SITES]
        jsl = bytes([0x22]) + STAGE_HELPER.to_bytes(3, "little") + bytes([0xEA] * 3)
        for s in STAGE_NUM_SITES:
            p.append((rom.lorom_to_pc(s), bytes.fromhex("a2020022e8f680"), jsl))
            p.append((rom.lorom_to_pc(s) + 25, bytes.fromhex("22a7f480"), bytes([0xEA] * 4)))
        code = stage_helper_bytes(new[291])
        p.append((rom.lorom_to_pc(STAGE_HELPER), bytes([0xFF]) * len(code), code))
    if 258 in texts:
        jsl = bytes([0x22]) + BONUS_HELPER.to_bytes(3, "little")
        p += [(rom.lorom_to_pc(s), bytes([0x22, 0xA7, 0xF4, 0x80]), jsl) for s in BONUS_SITES]
        code = bonus_helper_bytes(new[LINE_CLEAR])
        p.append((rom.lorom_to_pc(BONUS_HELPER), bytes([0xFF]) * len(code), code))
    return p


def gfx_resources(clean, edits):
    """{rid: new uncompressed bytes} for every resource with label edits (notes/graphics.md)."""
    out = {}
    for ed in edits:
        rid, bpp, stride = int(ed["res"], 16), ed["bpp"], ed.get("stride", 16)
        data = out.get(rid) or resources.load(clean, rid)
        ts = tiles.decode(data, bpp)
        for lb in ed["labels"]:
            # columns: "tile" + "w" (consecutive tiles), or "cols": each a top tile (rows below via stride)
            # or an explicit [top, bottom, ...] list, for words spread over non-adjacent cells
            cols = lb.get("cols") or [f"{int(lb['tile'], 16) + c:#x}" for c in range(lb["w"])]
            w, h = len(cols), lb["h"]
            where = lb.get("tile") or cols[0] if isinstance(cols[0], str) else cols[0][0]
            try:
                grid = labels.render(lb["text"], 8 * w, 8 * h, lb.get("ink", 1), lb.get("outline", 2),
                                     lb.get("align") == "left")
            except ValueError as x:
                raise BuildError(f"graphics resource {ed['res']} tile {where}: {x}") from None
            for i, tile in enumerate(labels.to_tiles(grid)):
                spec, row = cols[i % w], i // w
                ts[int(spec[row], 16) if isinstance(spec, list) else int(spec, 16) + stride * row] = tile
        new = tiles.encode(ts, bpp)
        if len(new) != len(data):
            raise BuildError(f"graphics resource {ed['res']}: size changed")
        out[rid] = new
    return out


# Terrain panel (map free look: Y, then A on a tile; builder 81D1F9). Its words are rows of BG3 tilemap words
# 0x2000 | (0x80 + tile of resource 0x295) in bank $87, drawn by the window helper $878000. Japanese shares glyph
# cells between words, so the English labels (gfx/edits.json) get their own cells and the rows are rewritten.
# (top row, bottom row, top tiles; bottom tile = top + 0x10): rewritten in place, never longer than the original.
TERRAIN_ROWS = [(0x8D2B, 0x8D3D, range(0x00, 0x04)),                       # スピード -> Speed
                (0x8D4F, 0x8D65, range(0x04, 0x0A)),                       # 通れません -> Blocked
                (0x8DCB, 0x8DE1, range(0x68, 0x6E)),                       # 回復します -> Heals HP
                (0x8DF7, 0x8E0D, [0x0E, 0x0F, 0x2F, 0x4D, 0x4F, 0x6E])]    # ダメージ床 -> Hurts HP
# "<costume> 向き" -> "Best: <costume>" in one row (13 cells, the panel's inner width after the 1-cell margin):
# new rows in free bank-$87 space, repointed in the costume table (index 1-5), and the 向き rows skipped (rts).
TERRAIN_BEST = [0x0A, 0x0B, 0x0C, 0x0D]
TERRAIN_COSTUMES = [range(0x20, 0x29), range(0x40, 0x49), range(0x60, 0x68), range(0x29, 0x2F), range(0x49, 0x4D)]
TERRAIN_COSTUME_TABLE = 0x81D3B4                   # (top, bottom) row pointers for costumes 1-5
TERRAIN_FREE = 0x87FA0C                            # 0xFF padding to the end of bank $87
TERRAIN_SUFFIX = 0x81D373                          # pha after the costume rows -> rts (no 向き rows)


def terrain_patches(clean):
    def words(tops, dy):
        return b"".join((0x2000 | 0x80 + t + dy).to_bytes(2, "little") for t in tops) + b"\xff\xff"
    p = []
    for top, bottom, tops in TERRAIN_ROWS:
        for a, dy in ((top, 0), (bottom, 0x10)):
            new, at = words(tops, dy), rom.lorom_to_pc(0x870000 | a)
            end = next(i for i in range(at, at + 0x40, 2) if clean[i:i + 2] == b"\xff\xff") + 2
            if len(new) > end - at:
                raise BuildError(f"terrain row ${a:04X}: English row is longer than the original")
            p.append((at, bytes(clean[at:at + len(new)]), new))
    rows, ptrs, a = b"", b"", TERRAIN_FREE & 0xFFFF
    for name in TERRAIN_COSTUMES:
        for dy in (0, 0x10):
            r = words(TERRAIN_BEST + list(name), dy)
            ptrs += a.to_bytes(2, "little")
            rows, a = rows + r, a + len(r)
    at = rom.lorom_to_pc(TERRAIN_FREE)
    p.append((at, b"\xff" * len(rows), rows))
    at = rom.lorom_to_pc(TERRAIN_COSTUME_TABLE)
    p.append((at, bytes(clean[at:at + len(ptrs)]), ptrs))
    p.append((rom.lorom_to_pc(TERRAIN_SUFFIX), b"\x48", b"\x60"))
    return p


def build(clean, en_dir=None, gfx=None):
    if len(clean) != 0x180000 or romimage.checksum(clean) != CLEAN_CHECKSUM:
        raise BuildError("input is not the clean 1.5 MB Nage Libre ROM (size/checksum mismatch)")
    table = Table.load(dump.TBL)            # Japanese: splits the original blocks
    en_table = Table.load(EN_TBL)
    if en_dir:
        if not os.path.isdir(en_dir):
            raise BuildError(f"translation directory not found: {en_dir}")
        for p in glob.glob(os.path.join(en_dir, "*.txt")):
            if os.path.basename(p) == SYSTEM_EN:
                continue
            m = re.fullmatch(r"scene_([0-9A-F]{3})\.txt", os.path.basename(p))
            if not (m and FIRST <= int(m.group(1), 16) <= LAST):
                raise BuildError(f"{os.path.basename(p)}: not a scene file name (expected scene_30F.txt .. scene_45B.txt)")
    WARNINGS.clear()
    img = romimage.expand(clean, SIZE)
    state, over = {"free": FREE_START}, []

    def place(at, packed):          # pack into free space (never across a 32 KB bank), repoint resource-table entry `at`
        free = state["free"]
        if free // 0x8000 != (free + len(packed) - 1) // 0x8000:
            free = (free // 0x8000 + 1) * 0x8000
        if free + len(packed) > SIZE:
            raise BuildError("expanded ROM is out of space")
        img[free:free + len(packed)] = packed
        img[at:at + 3] = rom.pc_to_lorom(free).to_bytes(3, "little")
        state["free"] = free + len(packed)
    for r in range(FIRST, LAST + 1):
        name = f"scene_{r:03X}"
        at = RES_TABLE + 3 * r
        blk, _ = decompress.decompress(clean, rom.lorom_to_pc(int.from_bytes(clean[at:at + 3], "little")))
        entries = dump.extract_scene(blk, table, name)
        path = os.path.join(en_dir, name + ".txt") if en_dir else None
        texts = en_texts(path, entries, en_table, wrap.entry_boxes(blk), blk) if path and os.path.exists(path) else {}
        try:
            new = layout.rebuild(blk, entries, texts)
        except ValueError as e:
            raise BuildError(f"{name}: {e}") from None
        if len(new) > WRAM_WINDOW:
            over.append(f"{name}: {len(new):#x} bytes > window {WRAM_WINDOW:#x}")
            continue
        place(at, compress.compress(new))
    edits = []
    if gfx:
        with open(gfx, encoding="utf-8") as f:
            edits = json.load(f)
        for rid, new in sorted(gfx_resources(clean, edits).items()):
            place(RES_TABLE + 3 * rid, compress.compress(new))
    free = state["free"]
    if over:
        raise BuildError("blocks exceed the WRAM window (shorten text or relocate the buffer):\n  " + "\n  ".join(over))
    if free > syslayout.BASE_FILE:
        raise BuildError("scene blocks overlap the system text bank (file 0x1F8000)")
    patches = relocation_patches(WRAM_BASE) + english_patches(clean) + system_patches(clean, en_dir, img)
    if any(int(ed["res"], 16) == 0x295 for ed in edits):      # the 0x295 labels need their re-allocated rows
        patches += terrain_patches(clean)
    for off, old, new in patches:
        if img[off:off + len(old)] != old:
            raise BuildError(f"patch at {off:#x}: unexpected original bytes {img[off:off + len(old)].hex()}")
        img[off:off + len(new)] = new
    romimage.set_checksum(img)
    return bytes(img)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--en", default=None, help="translation dir (default: script/en if it exists)")
    ap.add_argument("--out", default=os.path.join(rom.ROOT, "build"))
    a = ap.parse_args()
    clean = rom.load()
    try:
        default_en = os.path.join(rom.ROOT, "script", "en")
        img = build(clean, a.en if a.en is not None else (default_en if os.path.isdir(default_en) else None),
                    gfx=GFX_EDITS if os.path.exists(GFX_EDITS) else None)
    except BuildError as e:
        print("BUILD FAILED:", e)
        sys.exit(1)
    for w in WARNINGS:
        print("warning:", w)
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "nage_en.sfc"), "wb") as f:
        f.write(img)
    patch = bps.create(clean, img)
    with open(os.path.join(a.out, "nage_en.bps"), "wb") as f:
        f.write(patch)
    print(f"built {a.out}/nage_en.sfc ({len(img):#x} bytes), nage_en.bps ({len(patch)} bytes)")


if __name__ == "__main__":
    main()
