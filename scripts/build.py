"""Build the patched ROM: rebuild + recompress every scene block into an expanded 2 MB ROM, write a BPS patch.

    python -I scripts/build.py [--en script/en] [--out build]
"""
import argparse, glob, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bps, compress, decompress, dump, layout, rom, romimage
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


class BuildError(Exception):
    pass


def relocation_patches(base):
    """(file offset, expected original bytes, new bytes) moving the scene buffer to $7F:base."""
    if base == 0x64C0:
        return []
    lo, hi = base & 0xFF, base >> 8
    p = [(rom.lorom_to_pc(a), b"\x69\xc0\x64", bytes([0x69, lo, hi])) for a in ADC_SITES]
    p.append((rom.lorom_to_pc(LOADER), bytes.fromhex("a9c08506a9648507"), bytes([0xA9, lo, 0x85, 0x06, 0xA9, hi, 0x85, 0x07])))
    return p


def en_texts(path, entries, table):
    """{index: encoded bytes} for one translated scene file, validated against the JP entries."""
    fname = os.path.basename(path)
    block = os.path.splitext(fname)[0]
    raw = dump.read_text(path)
    if not raw.strip():
        return {}
    try:
        parsed = dump.parse_block(raw)
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
        if not t.text.endswith("<END>"):
            raise BuildError(f"{where}: text must end with <END>")
        try:
            b = table.encode(t.text)
        except ValueError as x:
            raise BuildError(f"{where}: {x}") from None
        if len(b) % 2:
            raise BuildError(f"{where}: encodes to an odd number of bytes (a raw <$..> code is 1 byte short)")
        if any(b[i:i + 2] == dump.END for i in range(0, len(b) - 2, 2)):
            raise BuildError(f"{where}: <END> before the end of the text (text after it would never show)")
        out[t.index] = b
    return out


def build(clean, en_dir=None):
    if len(clean) != 0x180000 or romimage.checksum(clean) != CLEAN_CHECKSUM:
        raise BuildError("input is not the clean 1.5 MB Nage Libre ROM (size/checksum mismatch)")
    table = Table.load(dump.TBL)
    if en_dir:
        if not os.path.isdir(en_dir):
            raise BuildError(f"translation directory not found: {en_dir}")
        for p in glob.glob(os.path.join(en_dir, "*.txt")):
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
        texts = en_texts(path, entries, table) if path and os.path.exists(path) else {}
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
    for off, old, new in relocation_patches(WRAM_BASE):
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
