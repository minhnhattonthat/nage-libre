"""SNES planar tiles (2bpp / 4bpp) <-> 8x8 colour-index grids, and greyscale PNG sheets."""
import struct, zlib

TILE = {2: 16, 4: 32}


def _plane_pair(b, off, y):
    return b[off + 2 * y], b[off + 2 * y + 1]


def decode(data, bpp):
    size, out = TILE[bpp], []
    for t in range(len(data) // size):
        base, tile = t * size, []
        for y in range(8):
            lo0, lo1 = _plane_pair(data, base, y)
            hi0, hi1 = _plane_pair(data, base + 16, y) if bpp == 4 else (0, 0)
            tile.append([((lo0 >> (7 - x)) & 1) | (((lo1 >> (7 - x)) & 1) << 1)
                         | (((hi0 >> (7 - x)) & 1) << 2) | (((hi1 >> (7 - x)) & 1) << 3) for x in range(8)])
        out.append(tile)
    return out


def encode(tiles, bpp):
    out = bytearray()
    for tile in tiles:
        planes = [bytearray(8) for _ in range(bpp)]
        for y in range(8):
            for x in range(8):
                for p in range(bpp):
                    planes[p][y] |= ((tile[y][x] >> p) & 1) << (7 - x)
        out += bytes(b for y in range(8) for b in (planes[0][y], planes[1][y]))
        if bpp == 4:
            out += bytes(b for y in range(8) for b in (planes[2][y], planes[3][y]))
    return bytes(out)


def sheet(tiles, cols=16, scale=2):
    rows = (len(tiles) + cols - 1) // cols
    w, h = cols * 8 * scale, rows * 8 * scale
    top = max((v for t in tiles for r in t for v in r), default=1) or 1
    raw = bytearray()
    for py in range(h):
        raw.append(0)
        ty, y = divmod(py // scale, 8)
        for px in range(w):
            tx, x = divmod(px // scale, 8)
            i = ty * cols + tx
            raw.append(tiles[i][y][x] * 255 // top if i < len(tiles) else 40)

    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(raw))) + chunk(b"IEND", b""))
