"""Render SNES planar tiles as a labelled PNG sheet.

    python -I scripts/render_font.py SRC OFFSET COUNT --bpp 2 --size 16 --layout col
           --base 0x00 --step 1 --scale 3 -o font/jp_font.png
SRC is any binary (ROM or work/mem/*_vram.bin). OFFSET/COUNT accept 0x.. .
Row labels show the code of the row's first glyph: base + row * 16 * step.
"""
import argparse, struct, zlib

TILE_BYTES = {1: 8, 2: 16, 4: 32}
# 3x5 hex digits, rows top->bottom, 3 bits each
DIGITS = {c: rows for c, rows in zip("0123456789ABCDEF", [
    (7, 5, 5, 5, 7), (2, 6, 2, 2, 7), (7, 1, 7, 4, 7), (7, 1, 7, 1, 7), (5, 5, 7, 1, 1), (7, 4, 7, 1, 7),
    (7, 4, 7, 5, 7), (7, 1, 1, 1, 1), (7, 5, 7, 5, 7), (7, 5, 7, 1, 7), (7, 5, 7, 5, 5), (6, 5, 6, 5, 6),
    (7, 4, 4, 4, 7), (6, 5, 5, 5, 6), (7, 4, 6, 4, 7), (7, 4, 6, 4, 4)])}


def decode_tile(data, off, bpp):
    px = [[0] * 8 for _ in range(8)]
    for y in range(8):
        for plane in range(bpp):
            if bpp == 1:
                b = data[off + y]
            else:
                b = data[off + (plane // 2) * 16 + y * 2 + (plane % 2)]
            for x in range(8):
                if b & (0x80 >> x):
                    px[y][x] |= 1 << plane
    return px


def glyph(data, off, index, bpp, size, layout):
    tb = TILE_BYTES[bpp]
    if size == 8:
        return decode_tile(data, off + index * tb, bpp)
    if layout == "seq":                       # TL, TR, BL, BR
        tiles = [index * 4 + k for k in range(4)]
    elif layout == "col":                     # TL, BL, TR, BR (Nage Libre font)
        tiles = [index * 4 + k for k in (0, 2, 1, 3)]
    else:
        t0 = (index // 8) * 32 + (index % 8) * 2
        tiles = [t0, t0 + 1, t0 + 16, t0 + 17]
    q = [decode_tile(data, off + t * tb, bpp) for t in tiles]
    return [q[0][y] + q[1][y] for y in range(8)] + [q[2][y] + q[3][y] for y in range(8)]


def write_png(path, rgb_rows):
    w, h = len(rgb_rows[0]) // 3, len(rgb_rows)
    def chunk(tag, body):
        return struct.pack(">I", len(body)) + tag + body + struct.pack(">I", zlib.crc32(tag + body))
    raw = b"".join(b"\x00" + bytes(r) for r in rgb_rows)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def render(data, off, count, bpp, size, layout, base, scale, step=1):
    per_row, cell, label_w = 16, size + 1, 4 * 4 + 2           # 4 hex digits of 3px + gaps
    rows = (count + per_row - 1) // per_row
    W, H = label_w + per_row * cell + 1, max(rows * cell + 1, 6)
    img = [[(0, 0, 0)] * W for _ in range(H)]
    maxv = (1 << bpp) - 1
    for r in range(rows):
        y0 = r * cell
        for i, ch in enumerate("%04X" % ((base + r * per_row * step) & 0xFFFF)):
            for dy, bits in enumerate(DIGITS[ch]):
                for dx in range(3):
                    if bits & (4 >> dx) and y0 + 1 + dy < H:
                        img[y0 + 1 + dy][i * 4 + dx] = (255, 255, 0)
        for c in range(per_row):
            idx = r * per_row + c
            if idx >= count:
                break
            g = glyph(data, off, idx, bpp, size, layout)
            for y in range(size):
                for x in range(size):
                    v = g[y][x] * 255 // maxv
                    img[y0 + 1 + y][label_w + c * cell + 1 + x] = (v, v, v)
    for y in range(H):
        for x in range(label_w, W):
            if y % cell == 0 or (x - label_w) % cell == 0:
                img[y][x] = (160, 0, 0)
    out = []
    for row in img:
        line = bytearray()
        for p in row:
            line += bytes(p) * scale
        out += [bytes(line)] * scale
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("offset"); ap.add_argument("count")
    ap.add_argument("--bpp", type=int, default=2, choices=(1, 2, 4))
    ap.add_argument("--size", type=int, default=16, choices=(8, 16))
    ap.add_argument("--layout", default="seq", choices=("seq", "col", "vram"))
    ap.add_argument("--base", default="0")
    ap.add_argument("--step", default="1")
    ap.add_argument("--scale", type=int, default=3)
    ap.add_argument("-o", required=True)
    a = ap.parse_args()
    with open(a.src, "rb") as f:
        data = f.read()
    write_png(a.o, render(data, int(a.offset, 0), int(a.count, 0), a.bpp, a.size, a.layout,
                          int(a.base, 0), a.scale, int(a.step, 0)))
