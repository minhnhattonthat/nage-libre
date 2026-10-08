"""Screenshot PNG helpers: read/write 8-bit RGB(A) PNGs, contact sheets, band differences."""
import struct, zlib


def read_png(path):
    d = open(path, "rb").read()
    pos, idat, w, h, ct = 8, b"", 0, 0, 0
    while pos < len(d):
        ln, = struct.unpack(">I", d[pos:pos + 4])
        tag, body = d[pos + 4:pos + 8], d[pos + 8:pos + 8 + ln]
        pos += 12 + ln
        if tag == b"IHDR":
            w, h, _, ct = struct.unpack(">IIBB", body[:10])
        elif tag == b"IDAT":
            idat += body
    bpp = {2: 3, 6: 4}[ct]
    raw, stride, rows, prev, i = zlib.decompress(idat), w * bpp, [], bytearray(w * bpp), 0
    for _ in range(h):
        f, line = raw[i], bytearray(raw[i + 1:i + 1 + stride])
        i += 1 + stride
        for x in range(stride):
            a = line[x - bpp] if x >= bpp else 0
            b = prev[x]
            c = prev[x - bpp] if x >= bpp else 0
            if f == 1:
                line[x] = (line[x] + a) & 255
            elif f == 2:
                line[x] = (line[x] + b) & 255
            elif f == 3:
                line[x] = (line[x] + (a + b) // 2) & 255
            elif f == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[x] = (line[x] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        rows.append(bytes(line))
        prev = line
    return w, h, bpp, rows


def write_png(path, w, h, rows):
    def chunk(t, b):
        return struct.pack(">I", len(b)) + t + b + struct.pack(">I", zlib.crc32(t + b))
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(b"".join(b"\0" + r for r in rows))) + chunk(b"IEND", b""))


def sheet(paths, cols, out, div=1):
    imgs = [read_png(p) for p in paths]
    w, h = imgs[0][0] // div, imgs[0][1] // div
    r = (len(imgs) + cols - 1) // cols
    W, H = cols * (w + 2), r * (h + 2)
    canvas = [bytearray(b"\x40\x00\x40" * W) for _ in range(H)]
    for k, (_, _, bpp, rows) in enumerate(imgs):
        ox, oy = (k % cols) * (w + 2), (k // cols) * (h + 2)
        for y in range(h):
            src = rows[y * div]
            for x in range(w):
                p = x * div * bpp
                canvas[oy + y][(ox + x) * 3:(ox + x) * 3 + 3] = src[p:p + 3]
    write_png(out, W, H, [bytes(c) for c in canvas])
    return out


def band_diff(a, b, y0, y1):
    wa, ha, pa, ra = read_png(a) if isinstance(a, str) else a
    wb, hb, pb, rb = read_png(b) if isinstance(b, str) else b
    n = diff = 0
    for y in range(y0, min(y1, ha, hb)):
        for x in range(min(wa, wb)):
            n += 1
            if ra[y][x * pa:x * pa + 3] != rb[y][x * pb:x * pb + 3]:
                diff += 1
    return diff / n if n else 0.0
