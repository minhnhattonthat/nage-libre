"""Build the patched ROM: rebuild + recompress every scene block into an expanded 2 MB ROM, write a BPS patch.

    python -I scripts/build.py [--en script/en] [--out build]
"""
import argparse, glob, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bps, compress, decompress, dump, entable, fontgen, layout, rom, romimage, syslayout, sysrefs, syswidth, wrap
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
BLANK = bytes([0xFE, 0x03])                        # full-width blank glyph 03FE
FONT_AT = 0x28000 + 0x20 * 0x20                    # glyphs for codes 0x20-0x7F (English = ASCII)
NAME_HOOKS = [0x81BACC, 0x81BB2A]                  # ldy #$0040 in the name builder's glyph copy loops
NAME_HELPER = 0x81F1B0                             # free space in bank $81
# ldy #$0040 / cpx #$1000 / bcs +3 / ldy #$0020 / rts : half-width codes (< 0x80, X = code<<5 < 0x1000) copy 0x20 bytes
NAME_HELPER_BYTES = bytes([0xA0, 0x40, 0x00, 0xE0, 0x00, 0x10, 0xB0, 0x03, 0xA0, 0x20, 0x00, 0x60])
SYSTEM_EN = "system.txt"


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
    font = fontgen.font_bytes(fontgen.load())
    p.append((FONT_AT, bytes(clean[FONT_AT:FONT_AT + len(font)]), font))
    return p


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


def system_texts(path, entries, table):
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
        syswidth.check_names(out)
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
    texts = system_texts(path, entries, Table.load(EN_TBL)) if path and os.path.exists(path) else {}
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
    p += [(rom.lorom_to_pc(h), bytes([0xA0, 0x40, 0x00]), bytes([0x20, 0xB0, 0xF1])) for h in NAME_HOOKS]
    h = rom.lorom_to_pc(NAME_HELPER)
    p.append((h, bytes([0xFF]) * len(NAME_HELPER_BYTES), NAME_HELPER_BYTES))
    return p


def build(clean, en_dir=None):
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
    img = romimage.expand(clean, SIZE)
    free, over = FREE_START, []
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
        packed = compress.compress(new)
        if free // 0x8000 != (free + len(packed) - 1) // 0x8000:
            free = (free // 0x8000 + 1) * 0x8000
        if free + len(packed) > SIZE:
            raise BuildError("expanded ROM is out of space")
        img[free:free + len(packed)] = packed
        img[at:at + 3] = rom.pc_to_lorom(free).to_bytes(3, "little")
        free += len(packed)
    if over:
        raise BuildError("blocks exceed the WRAM window (shorten text or relocate the buffer):\n  " + "\n  ".join(over))
    if free > syslayout.BASE_FILE:
        raise BuildError("scene blocks overlap the system text bank (file 0x1F8000)")
    for off, old, new in relocation_patches(WRAM_BASE) + english_patches(clean) + system_patches(clean, en_dir, img):
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
        img = build(clean, a.en if a.en is not None else (default_en if os.path.isdir(default_en) else None))
    except BuildError as e:
        print("BUILD FAILED:", e)
        sys.exit(1)
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "nage_en.sfc"), "wb") as f:
        f.write(img)
    patch = bps.create(clean, img)
    with open(os.path.join(a.out, "nage_en.bps"), "wb") as f:
        f.write(patch)
    print(f"built {a.out}/nage_en.sfc ({len(img):#x} bytes), nage_en.bps ({len(patch)} bytes)")


if __name__ == "__main__":
    main()
