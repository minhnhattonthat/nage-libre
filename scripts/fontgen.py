"""English 8x16 font: parse hand-drawn glyph art (font/en_glyphs.txt), add the game's outline, encode 2bpp.

    python -I scripts/fontgen.py --preview font/en_preview.png
Comments start with "# ". Art: 'char X' (or 'char space') then 13 rows of 6 chars ('#' stroke, '.' empty). Baseline after art row 9.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rom, render_font

ART = os.path.join(rom.ROOT, "font", "en_glyphs.txt")
W, H, X0, Y0 = 6, 13, 1, 2
FIRST, LAST = 0x20, 0x7F


def parse(text):
    glyphs, cur, rows = {}, None, []

    def close():
        if cur is None:
            return
        if len(rows) != H:
            raise ValueError(f"char {chr(cur)!r}: {len(rows)} rows, expected {H}")
        if cur in glyphs:
            raise ValueError(f"char {chr(cur)!r} defined twice")
        glyphs[cur] = rows

    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.startswith("# ") or line == "#":   # art rows never contain spaces
            continue
        if line.startswith("char "):
            close()
            name = line[5:]
            if name == "space":
                cur = 0x20
            elif len(name) == 1 and FIRST <= ord(name) < LAST:
                cur = ord(name)
            else:
                raise ValueError(f"line {n}: bad char name {name!r}")
            rows = []
            continue
        if cur is None:
            raise ValueError(f"line {n}: art before any 'char' line")
        if len(line) != W or set(line) - set(".#"):
            raise ValueError(f"line {n}: char {chr(cur)!r} row must be {W} of '.'/'#'")
        rows.append(line)
    close()
    return glyphs


def load():
    with open(ART, encoding="utf-8") as f:
        return parse(f.read())


def pixels(rows):
    px = [[0] * 8 for _ in range(16)]
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch == "#":
                px[Y0 + y][X0 + x] = 1
    for y in range(16):
        for x in range(8):
            if px[y][x] == 0 and any(px[yy][xx] == 1 for yy in range(max(0, y - 1), min(16, y + 2))
                                     for xx in range(max(0, x - 1), min(8, x + 2))):
                px[y][x] = 2
    return px


def _tile(px, y0):
    out = bytearray()
    for y in range(y0, y0 + 8):
        p0 = p1 = 0
        for x in range(8):
            p0 |= (px[y][x] & 1) << (7 - x)
            p1 |= ((px[y][x] >> 1) & 1) << (7 - x)
        out += bytes([p0, p1])
    return bytes(out)


def glyph_bytes(rows):
    px = pixels(rows)
    return _tile(px, 0) + _tile(px, 8)


def font_bytes(glyphs):
    blank = ["." * W] * H
    return b"".join(glyph_bytes(glyphs.get(c, blank)) for c in range(FIRST, LAST + 1))


def preview(path, glyphs, scale=3):
    """Sheet of all glyphs (6 rows x 16) plus a sample line, palette 0 black / 1 white / 2 grey."""
    colors = {0: (0, 0, 40), 1: (255, 255, 255), 2: (90, 90, 120)}
    sample = "The quick brown fox jumps over the lazy dog. 0123456789!?"
    rows_codes = [list(range(FIRST + 16 * r, FIRST + 16 * r + 16)) for r in range(6)] + [[ord(c) for c in sample]]
    img = []
    for codes in rows_codes:
        cells = [pixels(glyphs.get(c, ["." * W] * H)) for c in codes]
        for y in range(16):
            line = []
            for px in cells:
                line += [colors[v] for v in px[y]]
            img.append(line)
        img.append([(0, 0, 0)] * len(img[-1]))
    width = max(len(r) for r in img)
    out = []
    for r in img:
        r = r + [(0, 0, 0)] * (width - len(r))
        line = b"".join(bytes(p) * scale for p in r)
        out += [line] * scale
    render_font.write_png(path, out)


if __name__ == "__main__":
    if "--preview" in sys.argv:
        preview(sys.argv[sys.argv.index("--preview") + 1], load())
