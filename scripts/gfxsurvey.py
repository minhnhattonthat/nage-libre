"""Graphics survey: render every non-scene resource as 2bpp/4bpp tile sheets; locate VRAM tiles in resources.

    python -I scripts/gfxsurvey.py [--out work/gfx]
    python -I scripts/gfxsurvey.py --find work/mem/X_vram.bin 90 91 A0      # BG3 tiles (base byte 0xA000)
"""
import functools, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import resources, rom, tiles


@functools.lru_cache(maxsize=1)
def _all(data):
    out = {}
    for rid in range(resources.COUNT):
        if rid in resources.SCENES:
            continue
        try:
            out[rid] = resources.load(data, rid)
        except Exception:
            continue
    return out


def candidates(data):
    return [(rid, len(b)) for rid, b in _all(bytes(data)).items() if b and len(b) % 16 == 0]


def find_tiles(data, tile_bytes):
    hits = []
    for rid, b in _all(bytes(data)).items():
        i = b.find(tile_bytes)
        while i >= 0:
            hits.append((rid, i))
            i = b.find(tile_bytes, i + 1)
    return hits


def main():
    d = rom.load()
    if "--find" in sys.argv:
        i = sys.argv.index("--find")
        vram = open(sys.argv[i + 1], "rb").read()
        for h in sys.argv[i + 2:]:
            t = int(h, 16)
            blob = vram[0xA000 + t * 16: 0xA000 + t * 16 + 16]
            print(f"tile {t:02X}:", [(f"{r:03X}", f"{o:#x}") for r, o in find_tiles(d, blob)] if any(blob) else "blank")
        return
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else os.path.join(rom.ROOT, "work", "gfx")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "index.txt"), "w", encoding="utf-8") as idx:
        for rid, size in candidates(d):
            b = _all(bytes(d))[rid]
            for bpp in (2, 4):
                if len(b) % tiles.TILE[bpp] == 0:
                    with open(os.path.join(out, f"res_{rid:03X}_{bpp}bpp.png"), "wb") as f:
                        f.write(tiles.sheet(tiles.decode(b, bpp)))
            idx.write(f"{rid:03X} {size}\n")
    print(out)


if __name__ == "__main__":
    main()
