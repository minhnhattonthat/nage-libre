"""Render English labels for graphics tiles from font/en_glyphs.txt: proportional glyphs, 1 px letter spacing
(0 px when that is the only way to fit), stroke = ink index, 8-neighbour outline = outline index
(the original lettering uses 1 / 2)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fontgen

_GLYPHS = None


def _glyph(ch):
    global _GLYPHS
    if _GLYPHS is None:
        _GLYPHS = fontgen.load()
    rows = _GLYPHS.get(ord(ch))
    if rows is None:
        raise ValueError(f"no English glyph for {ch!r}")
    cols = [x for x in range(len(rows[0])) if any(r[x] == "#" for r in rows)]
    if not cols:                                  # space
        return [r[:3] for r in rows]
    return [r[cols[0]: cols[-1] + 1] for r in rows]


def _strokes(text, gap=1):
    parts = [_glyph(c) for c in text]
    sep = "." * gap
    return [sep.join(p[y] for p in parts) for y in range(len(parts[0]))]


def width(text, gap=1):
    return len(_strokes(text, gap)[0]) + 2        # + outline on both sides


def _gap(text, width_px):
    for gap in (1, 0):
        if width(text, gap) <= width_px:
            return gap
    return None


def fits(text, width_px):
    try:
        return _gap(text, width_px) is not None
    except ValueError:
        return False


def render(text, width_px, height_px=16, ink=1, outline=2):
    gap = _gap(text, width_px)
    if gap is None:
        raise ValueError(f"label {text!r} is {width(text)} px, area is {width_px} px")
    rows = _strokes(text, gap)
    w = len(rows[0]) + 2
    x0 = (width_px - w) // 2 + 1
    y0 = (height_px - len(rows)) // 2
    g = [[0] * width_px for _ in range(height_px)]
    for y, row in enumerate(rows):
        for x, c in enumerate(row):
            if c == "#":
                g[y0 + y][x0 + x] = ink
    for y in range(height_px):
        for x in range(width_px):
            if g[y][x] == 0 and any(g[yy][xx] == ink for yy in range(max(0, y - 1), min(height_px, y + 2))
                                    for xx in range(max(0, x - 1), min(width_px, x + 2))):
                g[y][x] = outline
    return g


def to_tiles(grid):
    h, w = len(grid) // 8, len(grid[0]) // 8
    return [[grid[ty * 8 + y][tx * 8: tx * 8 + 8] for y in range(8)] for ty in range(h) for tx in range(w)]
