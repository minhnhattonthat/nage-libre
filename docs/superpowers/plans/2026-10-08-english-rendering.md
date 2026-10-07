# English Rendering (2b) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Translated scene text in `script/en` renders in the game as word-wrapped English with a hand-drawn 8×16 outlined font, and the build rejects text that doesn't fit its box.

**Architecture:**
- A 3-byte patch raises the half-width threshold from `0x10` to `0x80`. English codes are ASCII, and their glyphs replace ROM font slots `0x20-0x7F`.
- `fontgen.py` turns hand-drawn 1-bit art into the game's outlined 2bpp format, and `entable.py` generates `en.tbl`.
- `wrap.py` pads lines to word-wrap inside the box, which it picks per entry from the bytecode ops that print it.
- `build.py` (from 2a) wires these in.

**Tech Stack:** Python 3.12 stdlib, `unittest`, Mesen2 headless (`scripts/mesen.py`, `scripts/accept.py`).

**Spec:** `docs/superpowers/specs/2026-10-08-english-rendering-design.md`

## Global Constraints

- Python 3.12, **stdlib only**. Run with `python -I`. CLI scripts start with `sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))`. CLIs that print non-ASCII call `sys.stdout.reconfigure(encoding="utf-8")`.
- Tests: `python -I -m unittest discover -s scripts -v` from project root. ROM-dependent tests use `@unittest.skipUnless(os.path.exists(rom.ROM_PATH), "ROM not present")`.
- All text files UTF-8, written with `newline="\n"`.
- Threshold patch: `cmp #$0010` → `cmp #$0080`. Operand bytes `10 00` → `80 00` at CPU `$80F3AE`, `$80F3C7`, `$80F426`.
- Font region: file offset `0x28400-0x28FFF` (codes `0x20-0x7F`, `0x20` bytes each, an 8×16 glyph = top tile + bottom tile, 2bpp, plane 0/1 interleaved per row).
- Glyph art cell: 6 wide × 13 tall, placed at x 1-6 and y 2-14 of the 8×16 cell. Stroke = colour 1; outline = colour 2 (8-neighbour); background 0.
- English codes = ASCII `0x20-0x7E`, table key order `XX00`. Symbols: `…`→`02AA`, `♥`→`03D0`, `♪`→`03CE`, `‼`→`02E0`. `<END>`=`FFFF`. `FE03`=U+3000.
- Width: code < `0x80` → 1 half-column, else 2.
- Boxes (half-columns × lines):
  - op `01`, `13`: 22×4
  - op `0B`: 30×4
  - op `26`, `2B`, `3B`: 30×3
  - an entry referenced by ops of different widths: 22×1
  - an unreferenced entry: 30×3
- `<` and `>` cannot appear as literal characters in English text (they start tags).
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **A `<BR>` right after a line that exactly fills the box width** must not insert an extra blank line, because the engine has already wrapped. Pinned in Task 3 (`test_wrap.py::test_br_after_exact_fill_is_not_a_blank_line`).
2. **Translators writing an entry across several lines in the `.txt` file:** newlines must act as spaces, so `Hello\nthere` must not become `Hellothere`. Pinned in Task 4 (`test_build.py::test_en_newlines_are_spaces`).
3. **Untranslated Japanese pasted into an English file** must fail with a clear "no table entry" error naming file and entry, not crash or encode garbage. Pinned in Task 4 (`test_build.py::test_japanese_in_en_file_names_entry`).
4. **The half-width digits at codes `0x02-0x0B`** (dates, HP) must stay byte-identical, because the font patch starts at `0x20`. Pinned in Task 4 (`test_build.py::test_halfwidth_digits_untouched`).
5. **Multiple spaces or a leading space** in the source must not shift the layout: collapse to one space, ignore leading/trailing. Pinned in Task 3 (`test_wrap.py::test_spaces_collapsed`).

---

## File Structure

| Path | Responsibility |
|---|---|
| `font/en_glyphs.txt` | Hand-drawn 1-bit art for ASCII `0x20-0x7E` |
| `font/en_preview.png` | Generated preview for review |
| `scripts/fontgen.py` + `test_fontgen.py` | Parse art, outline, encode 2bpp, preview |
| `scripts/entable.py` + `test_entable.py`, `en.tbl` | Generated English table |
| `scripts/wrap.py` + `test_wrap.py` | Box geometry, fitting, per-entry box selection |
| `scripts/boxcheck.py` | Japanese line-count analysis per print op (confirms `BOXES`) |
| `scripts/dump.py` (modify) | `parse_block(s, joiner="")` |
| `scripts/build.py` (modify) + `test_build.py` (modify) | English encoding through `wrap.fit`; threshold and font patches |
| `scripts/accept.py` (modify), `scripts/fixtures/en_sample/*.txt`, `notes/english.md` | Emulator acceptance |

---

### Task 1: English font generator and glyph art

**Files:**
- Create: `scripts/fontgen.py`, `scripts/test_fontgen.py`, `font/en_glyphs.txt`, `font/en_preview.png`

**Interfaces:**
- Consumes: `render_font.decode_tile(data, off, bpp)`, `render_font.write_png(path, rgb_rows)`, `rom.ROOT`.
- Produces:
  - `fontgen.ART` (path), `fontgen.parse(text) -> dict[int, list[str]]`
  - `fontgen.pixels(rows) -> list[list[int]]` (16 rows × 8)
  - `fontgen.glyph_bytes(rows) -> bytes` (32)
  - `fontgen.font_bytes(glyphs) -> bytes` (`0xC00`, codes `0x20-0x7F`; missing codes are blank)
  - `fontgen.load() -> dict` (parse `ART`)
  - CLI `python -I scripts/fontgen.py --preview font/en_preview.png`

- [ ] **Step 1: Write failing tests** `scripts/test_fontgen.py`

```python
import os, unittest
import fontgen, render_font

DOT = ["......"] * 6 + ["..#..."] + ["......"] * 6        # one stroke pixel at art (2,6) -> cell (3,8)

class Parse(unittest.TestCase):
    def test_parse_and_space_name(self):
        g = fontgen.parse("# c\nchar space\n" + "......\n" * 13 + "char A\n" + "\n".join(DOT) + "\n")
        self.assertEqual(sorted(g), [0x20, 0x41])
        self.assertEqual(g[0x41], DOT)

    def test_bad_inputs_rejected(self):
        for text, msg in (("char A\n" + "......\n" * 12, "13"),
                          ("char A\n" + "......\n" * 13 + "char A\n" + "......\n" * 13, "twice"),
                          ("char A\n" + ".....\n" + "......\n" * 12, "row"),
                          ("......\n", "before")):
            with self.assertRaisesRegex(ValueError, msg):
                fontgen.parse(text)

class Pixels(unittest.TestCase):
    def test_outline_ring_around_single_pixel(self):
        px = fontgen.pixels(DOT)
        self.assertEqual(px[8][3], 1)
        ring = [px[y][x] for y in (7, 8, 9) for x in (2, 3, 4) if (y, x) != (8, 3)]
        self.assertEqual(ring, [2] * 8)
        self.assertEqual(sum(v != 0 for row in px for v in row), 9)

    def test_bytes_roundtrip_through_decoder(self):
        b = fontgen.glyph_bytes(DOT)
        self.assertEqual(len(b), 32)
        top, bottom = render_font.decode_tile(b, 0, 2), render_font.decode_tile(b, 16, 2)
        self.assertEqual(top + bottom, fontgen.pixels(DOT))

    def test_font_bytes_layout(self):
        fb = fontgen.font_bytes({0x41: DOT})
        self.assertEqual(len(fb), 0xC00)
        self.assertEqual(fb[(0x41 - 0x20) * 32:(0x42 - 0x20) * 32], fontgen.glyph_bytes(DOT))
        self.assertEqual(fb[:32], bytes(32))                     # missing code -> blank

class Art(unittest.TestCase):
    def test_all_printable_ascii_drawn(self):
        g = fontgen.load()
        self.assertEqual([c for c in range(0x20, 0x7F) if c not in g], [])
```

- [ ] **Step 2: Run, expect FAIL**: `python -I -m unittest discover -s scripts -p "test_fontgen.py"` reports `No module named 'fontgen'`.

- [ ] **Step 3: Implement** `scripts/fontgen.py`

```python
"""English 8x16 font: parse hand-drawn glyph art (font/en_glyphs.txt), add the game's outline, encode 2bpp.

    python -I scripts/fontgen.py --preview font/en_preview.png
Art: 'char X' (or 'char space') then 13 rows of 6 chars ('#' stroke, '.' empty). Baseline after art row 9.
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
        if not line.strip() or line.startswith("#"):
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
```

- [ ] **Step 4: Run the parse/pixel tests, expect PASS except `Art`**: `python -I -m unittest discover -s scripts -p "test_fontgen.py" -v`. `Parse` and `Pixels` pass; `Art` fails with a missing-file error.

- [ ] **Step 5: Draw the glyphs** in `font/en_glyphs.txt`: all 95 printable ASCII characters `0x20-0x7E`.
  - **Grid:** 6×13 art, baseline after row 9 (rows 0-9 above it, 10-12 for descenders).
  - **Capitals and digits:** rows 1-9, 5 px wide (cols 0-4 or 1-5).
  - **Lowercase:** x-height rows 4-9. Ascenders (`b d f h k l t`) start at row 1. Descenders (`g j p q y`) end in rows 10-12.
  - **Punctuation:** `. , ! ? ' " : ;` sized to these bands. `space` is all `.`.
  - **Style:** single-pixel strokes, like a clean 5×7-style face scaled into the band; the outline adds weight.

  Example, the first lines of the file:
```
# Nage Libre English font: 6x13 art, '#' stroke, '.' empty; baseline after row 9. Outline added by fontgen.py.
char space
......
......
......
......
......
......
......
......
......
......
......
......
......
char A
......
..##..
.#..#.
.#..#.
#....#
#....#
######
#....#
#....#
#....#
......
......
......
char g
......
......
......
......
.####.
#...#.
#...#.
#...#.
.####.
....#.
#...#.
.###..
......
```

- [ ] **Step 6: Run, expect PASS**: `python -I -m unittest discover -s scripts -p "test_fontgen.py" -v`, all pass.

- [ ] **Step 7: Render and inspect the preview**: `python -I scripts/fontgen.py --preview font/en_preview.png`, then view it. Check:
  - every glyph is legible, with a consistent baseline
  - descenders don't touch the next row
  - the outline doesn't merge neighbouring strokes into blobs (e.g. `m`, `w`)

  Redraw any glyph that fails and re-render. This preview goes to the user for review in the final report.

- [ ] **Step 8: Commit**

```bash
git add scripts/fontgen.py scripts/test_fontgen.py font/en_glyphs.txt font/en_preview.png
git commit -m "Add English 8x16 font generator and glyph art"
```

---

### Task 2: English table

**Files:**
- Create: `scripts/entable.py`, `scripts/test_entable.py`, `en.tbl`

**Interfaces:**
- Consumes: `tbl.Table`.
- Produces:
  - `entable.SYMBOLS: dict[str, int]`, `entable.table_text() -> str`, `entable.OUT` (path `en.tbl`)
  - CLI `python -I scripts/entable.py` writes `en.tbl`

- [ ] **Step 1: Write failing test** `scripts/test_entable.py`

```python
import unittest
import entable
from tbl import Table

class EnTable(unittest.TestCase):
    T = Table.parse(entable.table_text())

    def test_ascii_codes(self):
        self.assertEqual(self.T.encode("Hi, Yui!<END>"),
                         bytes.fromhex("4800 6900 2c00 2000 5900 7500 6900 2100 ffff"))

    def test_symbols_use_fullwidth_glyphs(self):
        self.assertEqual(self.T.encode("…♥♪‼"), bytes.fromhex("aa02 d003 ce03 e002"))

    def test_equals_and_hash_are_characters(self):
        self.assertEqual(self.T.encode("a=b#"), bytes.fromhex("6100 3d00 6200 2300"))

    def test_no_duplicates_or_errors(self):
        self.assertEqual((self.T.duplicates, self.T.errors), ([], []))
```

- [ ] **Step 2: Run, expect FAIL** (`No module named 'entable'`).

- [ ] **Step 3: Implement** `scripts/entable.py`

```python
"""Generate en.tbl: English codes = ASCII (half-width after the 0x80 threshold patch) + a few full-width symbols.

    python -I scripts/entable.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rom

OUT = os.path.join(rom.ROOT, "en.tbl")
SYMBOLS = {"…": 0x02AA, "♥": 0x03D0, "♪": 0x03CE, "‼": 0x02E0}


def table_text():
    lines = ["# English table — GENERATED by scripts/entable.py. Codes = ASCII (ROM byte order XX00).",
             "# '<' and '>' start tags in script text and can't be used as literal characters.",
             "FFFF=<END>!", "FE03=　"]
    lines += [f"{c:02X}00={chr(c)}" for c in range(0x20, 0x7F)]
    lines += [f"{v & 0xFF:02X}{v >> 8:02X}={k}" for k, v in SYMBOLS.items()]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(table_text())
    print("wrote", OUT)
```

- [ ] **Step 4: Run, expect PASS.** Then generate: `python -I scripts/entable.py`.

- [ ] **Step 5: Commit**

```bash
git add scripts/entable.py scripts/test_entable.py en.tbl
git commit -m "Add generated English table"
```

---

### Task 3: Text fitting

**Files:**
- Create: `scripts/wrap.py`, `scripts/test_wrap.py`

**Interfaces:**
- Consumes: `bytecode.parse(block) -> list[Op]` (`Op.opcode`, `Op.operands`, `Op.offset_operands`, `Op.data_operands`), `tbl.Table`.
- Produces:
  - `wrap.Box(cols, lines)` (frozen dataclass), `wrap.PORTRAIT`, `wrap.FULL`, `wrap.FULL4`, `wrap.BOXES: dict[int, Box]`
  - `wrap.FitError(ValueError)`
  - `wrap.fit(text: str, box: Box, table) -> str`: padded text ending in `<END>`
  - `wrap.entry_boxes(block: bytes, ops=None) -> dict[int, Box]`: entry offset to box

- [ ] **Step 1: Write failing tests** `scripts/test_wrap.py`

```python
import unittest
import entable, wrap
from tbl import Table

T = Table.parse(entable.table_text())
B = wrap.Box(10, 3)

class Fit(unittest.TestCase):
    def test_word_wrap_pads_with_spaces(self):
        self.assertEqual(wrap.fit("hello there world<END>", B, T), "hello     there     world<END>")

    def test_exact_fill_needs_no_padding(self):
        self.assertEqual(wrap.fit("abcdefghij klm<END>", B, T), "abcdefghijklm<END>")

    def test_br_and_leading_br(self):
        self.assertEqual(wrap.fit("<BR>hi<BR>yo<END>", B, T), " " * 10 + "hi" + " " * 8 + "yo<END>")

    def test_br_after_exact_fill_is_not_a_blank_line(self):
        self.assertEqual(wrap.fit("abcdefghij<BR>klm<END>", B, T), "abcdefghijklm<END>")

    def test_spaces_collapsed(self):
        self.assertEqual(wrap.fit("  hi    there <END>", B, T), "hi there<END>")

    def test_fullwidth_symbol_counts_two(self):
        self.assertEqual(wrap.fit("abcdefgh… x<END>", B, T), "abcdefgh…x<END>")

    def test_overlong_word_fails(self):
        with self.assertRaisesRegex(wrap.FitError, "11 columns"):
            wrap.fit("abcdefghijk<END>", B, T)

    def test_too_many_lines_fails_with_count(self):
        with self.assertRaisesRegex(wrap.FitError, "4 lines"):
            wrap.fit("aaaa bbbbbbb cccccc ddddddd<END>", B, T)

    def test_unknown_char_and_missing_end(self):
        with self.assertRaisesRegex(wrap.FitError, "table"):
            wrap.fit("ä<END>", B, T)
        with self.assertRaisesRegex(wrap.FitError, "<END>"):
            wrap.fit("hi", B, T)

def words(*ws):
    return b"".join(w.to_bytes(2, "little") for w in ws)

class EntryBoxes(unittest.TestCase):
    # 01 0010 | 2B 0010 | 2B 0016 | 13 0016 0016 0016 0016 0016 | FFFF  -> 0x10 bytes of code; strings follow
    BLK = words(0x01, 0x0010, 0x2B, 0x0016, 0x0B, 0x001A, 0xFFFF, 0, 0x41, 0xFFFF, 0x42, 0xFFFF, 0x43, 0xFFFF)

    def test_box_per_entry(self):
        boxes = wrap.entry_boxes(self.BLK)
        self.assertEqual(boxes[0x10], wrap.PORTRAIT)
        self.assertEqual(boxes[0x16], wrap.FULL)
        self.assertEqual(boxes[0x1A], wrap.FULL4)

    def test_mixed_widths_get_one_line_of_the_narrower(self):
        blk = words(0x01, 0x0008, 0x2B, 0x0008, 0xFFFF, 0x41, 0xFFFF)
        self.assertEqual(wrap.entry_boxes(blk)[0x08], wrap.Box(22, 1))
```

(`EntryBoxes.BLK`: words `01 0010`, `2B 0016`, `0B 001A`, `FFFF` = 7 words = `0xE` bytes; string area from `0xE`: `0000 0041 FFFF` … The offsets used, `0x10`/`0x16`/`0x1A`, are entry starts only by construction for this test, because `entry_boxes` doesn't check entries.)

- [ ] **Step 2: Run, expect FAIL** (`No module named 'wrap'`).

- [ ] **Step 3: Implement** `scripts/wrap.py`

```python
"""Fit English text into a dialogue box. The engine wraps mid-word and never pages, so the build
word-wraps by padding lines with spaces and rejects text that doesn't fit."""
import re
from dataclasses import dataclass
import bytecode


@dataclass(frozen=True)
class Box:
    cols: int       # half-columns (8 px) per line
    lines: int


PORTRAIT, FULL, FULL4 = Box(22, 4), Box(30, 3), Box(30, 4)
BOXES = {0x01: PORTRAIT, 0x13: PORTRAIT, 0x0B: FULL4, 0x26: FULL, 0x2B: FULL, 0x3B: FULL}


class FitError(ValueError):
    pass


_TOK = re.compile(r"<[^>]*>|.")


def _width(tok, table):
    if tok.startswith("<$"):
        code = int.from_bytes(bytes.fromhex(tok[2:-1]), "little")
    elif tok.startswith("<"):
        return 0
    else:
        b = table.enc_text.get(tok)
        if b is None:
            raise FitError(f"no table entry for {tok!r}")
        code = int.from_bytes(b, "little")
    return 1 if code < 0x80 else 2


def fit(text, box, table):
    if not text.endswith("<END>"):
        raise FitError("text must end with <END>")
    out, cur, curw, wrapped = [], "", 0, False

    def end_line(pad):
        nonlocal cur, curw
        out.append(cur + (" " * (box.cols - curw) if pad else ""))
        cur, curw = "", 0

    for word in text[:-5].replace("<BR>", " \0 ").split():
        if word == "\0":
            if curw == 0 and wrapped:          # engine already wrapped after an exactly full line
                wrapped = False
                continue
            end_line(True)
            wrapped = False
            continue
        ww = sum(_width(t, table) for t in _TOK.findall(word))
        if ww > box.cols:
            raise FitError(f"word {word!r} is {ww} columns, box line is {box.cols}")
        if curw == 0:
            cur, curw = word, ww
        elif curw + 1 + ww <= box.cols:
            cur, curw = cur + " " + word, curw + 1 + ww
        else:
            end_line(True)
            cur, curw = word, ww
        wrapped = False
        if curw == box.cols:
            end_line(False)
            wrapped = True
    if cur:
        end_line(False)
    if len(out) > box.lines:
        raise FitError(f"{len(out)} lines, box holds {box.lines} lines of {box.cols} columns")
    return "".join(out) + "<END>"


def entry_boxes(block, ops=None):
    ops = bytecode.parse(block) if ops is None else ops
    seen = {}
    for o in ops:
        box = BOXES.get(o.opcode)
        if box is None:
            continue
        for k in o.offset_operands:
            if k not in o.data_operands:
                seen.setdefault(o.operands[k - 1], set()).add(box)
    out = {}
    for off, boxes in seen.items():
        widths = {b.cols for b in boxes}
        out[off] = Box(min(widths), 1) if len(widths) > 1 else min(boxes, key=lambda b: b.lines)
    return out
```

- [ ] **Step 4: Run, expect PASS**: `python -I -m unittest discover -s scripts -p "test_wrap.py" -v`.
  - Recheck each expected string by hand against the rule if one fails. For example, `test_word_wrap_pads_with_spaces`: `hello` (5) is padded to 10, then `there` (5) padded to 10, then `world`.
  - Fix the code, not the test, unless the hand check shows the test is wrong. Ledger a ruling if so.

- [ ] **Step 5: Commit**

```bash
git add scripts/wrap.py scripts/test_wrap.py
git commit -m "Add box fitting for English text"
```

---

### Task 4: Build integration (English encoding, font and threshold patches)

**Files:**
- Modify: `scripts/dump.py` (`parse_block` gains `joiner`), `scripts/build.py`, `scripts/test_build.py`, `scripts/test_dump.py`
- Create: `scripts/boxcheck.py`

**Interfaces:**
- Consumes: `fontgen.load/font_bytes`, `entable.OUT`, `wrap.fit/entry_boxes/FULL/FitError`, `tbl.Table`.
- Produces:
  - `dump.parse_block(s: str, joiner: str = "") -> list[Entry]`
  - `build.EN_TBL` (path), `build.THRESHOLD_SITES`, `build.FONT_AT = 0x28400`
  - `build.english_patches(clean: bytes) -> list[(offset, old, new)]`
  - `build.en_texts(path, entries, table, boxes)`: new signature with `boxes: dict[int, Box]`
  - CLI `python -I scripts/boxcheck.py` prints max Japanese lines per print op

- [ ] **Step 1: Confirm the box table**: write `scripts/boxcheck.py`

```python
"""Max Japanese line count per print opcode (Japanese widths: code < 0x10 -> 1, else 2), to confirm wrap.BOXES.

    python -I scripts/boxcheck.py
"""
import collections, glob, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bytecode, dump, rom, wrap


def jp_lines(raw, cols):
    codes = [int.from_bytes(raw[i:i + 2], "little") for i in range(0, len(raw) - 2, 2)]
    while codes and codes[-1] == 0x03FE:
        codes.pop()
    col, n = 0, 1 if codes else 0
    for c in codes:
        w = 1 if c < 0x10 else 2
        if col + w > cols:
            n, col = n + 1, 0
        col += w
    return n


if __name__ == "__main__":
    d, m = rom.load(), dump.load_map()
    dist = collections.defaultdict(collections.Counter)
    for p in glob.glob(os.path.join(dump.OUT, "scene_*.txt")):
        name = os.path.splitext(os.path.basename(p))[0]
        blk = dump.source(d, name, m)
        es = {e.offset: e for e in dump.parse_block(dump.read_text(p))}
        for o in bytecode.parse(blk):
            box = wrap.BOXES.get(o.opcode)
            for k in (o.offset_operands if box else []):
                e = es[o.operands[k - 1]]
                dist[o.opcode][jp_lines(blk[e.offset:e.offset + e.length], box.cols)] += 1
    for op in sorted(dist):
        print(f"op {op:02X} box {wrap.BOXES[op]}: JP lines {dict(sorted(dist[op].items()))}")
```

Run: `python -I scripts/boxcheck.py`.
- Expected: max lines `01`→4, `0B`→4, `13`→5 (12 cases), `26`/`2B`/`3B`→3.
- For the op `13` 5-line cases (narration-style strings with a 15-blank first line, e.g. `scene_315 0008`, `scene_3B9 0000`), read the rest of handler `838BE8`:
  ```
  python -I scripts/disasm.py 0x838BE8 0x70
  ```
  If there is a branch that keeps column 1 / limit `0x1F` for some member index, those strings print in a full box. Then record in `notes/english.md` that op `13` can print in a full box, and in `wrap.BOXES` keep `PORTRAIT` (the stricter width) for op `13`. Translators keep those strings within 22 columns.
- Record the outcome in `notes/english.md ## Boxes`. Change `BOXES` only if a maximum *exceeds* its box's lines for ops other than the `13` case. Ledger the ruling.

- [ ] **Step 2: Write failing tests**. Append to `scripts/test_dump.py`:

```python
class Joiner(unittest.TestCase):
    def test_joiner_replaces_newlines(self):
        s = "## s 0000 @000000 len=0\nHello\nthere<END>\n"
        self.assertEqual(dump.parse_block(s, joiner=" ")[0].text, "Hello there<END>")
        self.assertEqual(dump.parse_block(s)[0].text, "Hellothere<END>")
```

In `scripts/test_build.py`:
- Replace the Japanese texts in the existing en-file tests with English. In `test_growth_text_lands_and_operands_follow`, replace the `grown` construction and assertion with:
  ```python
          grown = "<BR>In a distant world… a voice echoes…<END>"
          img = build.build(self.clean, self._en(f"## scene_341 0000 @000000 len=0\n{grown}\n"))
          blk = decompress.decompress(img, ptr(img, 0x341))[0]
          new = dump.extract_scene(blk, Table.load(build.EN_TBL), "scene_341")
          self.assertEqual(new[0].text.replace(" ", ""), "Inadistantworld…avoiceechoes…<END>")
          self.assertEqual(new[0].text[:30], " " * 30)
  ```
  Keep the operand-follow assertion (the `ops`/`starts` lines). Remove the `self.assertEqual([e.text for e in new[1:]], ...)` line (later entries now decode with a different table); replace it with `self.assertEqual(len(new), len(jp))`.
- In `test_en_errors_name_file_and_entry`, use the cases `("## scene_341 9999 @000000 len=0\nHi<END>\n", "scene_341.txt entry 9999")`, `("## scene_341 0000 @000000 len=0\nHi\n", "<END>")` and `("## scene_341 0000 @000000 len=0\nä<END>\n", "scene_341.txt entry 0000")`.
- In `TranslationInputValidation`:
  - `test_duplicate_index_and_foreign_header_rejected`: replace `あ<END>`/`い<END>` with `Hi<END>`/`Yo<END>`.
  - `test_odd_length_and_inner_end_rejected`: use `"a<$12><END>"` and `"a<END>b<END>"`.
- In `test_only_expected_bytes_changed_below_new_area`, add `allowed |= {at + k for at, old, new in build.english_patches(self.clean) for k in range(len(new))}`.
- Append to class `Build`:
  ```python
      def test_threshold_and_font_patched(self):
          import fontgen
          for a in build.THRESHOLD_SITES:
              self.assertEqual(self.img[rom.lorom_to_pc(a):rom.lorom_to_pc(a) + 2], b"\x80\x00")
          self.assertEqual(self.img[0x28400:0x29000], fontgen.font_bytes(fontgen.load()))

      def test_halfwidth_digits_untouched(self):
          self.assertEqual(self.img[0x28000:0x28400], self.clean[0x28000:0x28400])

      def test_en_newlines_are_spaces(self):
          img = build.build(self.clean, self._en("## scene_341 0000 @000000 len=0\nIn a\ndistant world<END>\n"))
          blk = decompress.decompress(img, ptr(img, 0x341))[0]
          text = dump.extract_scene(blk, Table.load(build.EN_TBL), "scene_341")[0].text
          self.assertIn("In a distant world", text)

      def test_japanese_in_en_file_names_entry(self):
          with self.assertRaisesRegex(build.BuildError, "scene_341.txt entry 0000: .*table"):
              build.build(self.clean, self._en("## scene_341 0000 @000000 len=0\n遠くの世界<END>\n"))

      def test_overflow_names_box(self):
          with self.assertRaisesRegex(build.BuildError, "scene_341.txt entry 0000: .*lines"):
              build.build(self.clean, self._en("## scene_341 0000 @000000 len=0\n" + "word " * 40 + "<END>\n"))
  ```

- [ ] **Step 3: Run, expect FAIL**: the new tests fail (`EN_TBL`, `THRESHOLD_SITES`, `english_patches` missing; `joiner` unknown), and the updated English tests fail because English isn't encodable yet.

- [ ] **Step 4: Implement**
  - `scripts/dump.py`:
    - Change the signature to `def parse_block(s, joiner=""):`.
    - In it, replace `body.replace("\n", "")` with `body.replace("\n", joiner)`.
  - `scripts/build.py`:
    - Imports become `import bps, compress, decompress, dump, entable, fontgen, layout, rom, romimage, wrap`.
    - Add constants after `LOADER`:
      ```python
      EN_TBL = entable.OUT
      THRESHOLD_SITES = [0x80F3AE, 0x80F3C7, 0x80F426]   # operand of cmp #$0010 (half-width glyph threshold)
      FONT_AT = 0x28000 + 0x20 * 0x20                    # glyphs for codes 0x20-0x7F (English = ASCII)


      def english_patches(clean):
          """(file offset, expected original bytes, new bytes): threshold 0x10 -> 0x80 and the English font."""
          p = [(rom.lorom_to_pc(a), b"\x10\x00", b"\x80\x00") for a in THRESHOLD_SITES]
          font = fontgen.font_bytes(fontgen.load())
          p.append((FONT_AT, bytes(clean[FONT_AT:FONT_AT + len(font)]), font))
          return p
      ```
    - In `en_texts`:
      - Change the signature to `def en_texts(path, entries, table, boxes):`.
      - Parse with `dump.parse_block(raw, joiner=" ")`.
      - Replace the encode block
        ```python
                try:
                    b = table.encode(t.text)
                except ValueError as x:
                    raise BuildError(f"{where}: {x}") from None
        ```
        with
        ```python
                box = boxes.get(e.offset, wrap.FULL)
                try:
                    b = table.encode(wrap.fit(t.text, box, table))
                except ValueError as x:
                    raise BuildError(f"{where}: {x} (box {box.cols}x{box.lines})") from None
        ```
        `FitError` is a `ValueError`, so it is caught by the same handler.
    - In `build()`:
      - Load the table with `table = Table.load(dump.TBL)` (Japanese, for `extract_scene`) and `en_table = Table.load(EN_TBL)`.
      - In the loop, call `en_texts(path, entries, en_table, wrap.entry_boxes(blk))`.
      - Replace the patch loop with:
        ```python
            for off, old, new in relocation_patches(WRAM_BASE) + english_patches(clean):
        ```
        Keep the body that asserts the original bytes and writes the new ones.

- [ ] **Step 5: Run, expect PASS**: `python -I -m unittest discover -s scripts -v`, all green.

- [ ] **Step 6: Commit**

```bash
git add scripts/dump.py scripts/build.py scripts/test_build.py scripts/test_dump.py scripts/boxcheck.py notes/english.md
git commit -m "Encode English via fitted boxes; patch half-width threshold and English font"
```

---

### Task 5: Emulator acceptance

**Files:**
- Create: `scripts/fixtures/en_sample/scene_341.txt`, `scripts/fixtures/en_sample/scene_310.txt`
- Modify: `scripts/accept.py`, `notes/english.md`

**Interfaces:**
- Consumes: `build.build`, `accept.play/write_rom/final`, routes `dialogue1`, `narration_next`, `stage1`, `map1`, `wrap.entry_boxes`.
- Produces: `python -I scripts/accept.py english` (builds with the fixtures, plays routes, prints screenshot paths); `growth` updated to English.

- [ ] **Step 1: Write fixtures.** `scripts/fixtures/en_sample/scene_341.txt` (narration, full box 30×3):
```
## scene_341 0000 @000000 len=0
<BR>In a distant world… a voice echoes…<END>

## scene_341 0002 @000000 len=0
"I will make this whole world mine… by gathering those whose hearts hold darkness…"<END>

## scene_341 0004 @000000 len=0
<BR>…  AM 6:12  …<END>
```
`scripts/fixtures/en_sample/scene_310.txt` exactly fills the portrait box (22×4): four 22-character words, each line full.
```
## scene_310 0012 @000000 len=0
AAAAAAAAAAAAAAAAAAAAA1 BBBBBBBBBBBBBBBBBBBBB2 CCCCCCCCCCCCCCCCCCCCC3 DDDDDDDDDDDDDDDDDDDDD4<END>
```
Check both fit: `python -I -c "import sys; sys.path.insert(0,'scripts'); import build, rom; build.build(rom.load(), 'scripts/fixtures/en_sample'); print('fits')"` should print `fits`. If an entry raises a fit error, shorten its text (fixture content only).

- [ ] **Step 2: Add the `english` mode** to `scripts/accept.py`, and switch `growth` to English. Replace the `growth()` function and `__main__` with:

```python
def growth():
    en = tempfile.mkdtemp()
    with open(os.path.join(en, "scene_341.txt"), "w", encoding="utf-8") as f:
        f.write("## scene_341 0000 @000000 len=0\n<BR>In a distant world, far away… a voice echoes in the dark…<END>\n")
    d, built = write_rom(build.build(rom.load(), en))
    play("growth", built, [("dialogue1", None), ("narration_next", "dialogue1")])
    shutil.rmtree(d)
    shutil.rmtree(en)
    print("review work/shots/growth_narration_next_*.png")
    return True


def english():
    fixtures = os.path.join(rom.ROOT, "scripts", "fixtures", "en_sample")
    d, built = write_rom(build.build(rom.load(), fixtures))
    try:
        play("english", built, [("dialogue1", None), ("narration_next", "dialogue1"),
                                ("stage1", "dialogue1"), ("map1", "stage1")])
    finally:
        shutil.rmtree(d)
    print("review work/shots/english_narration_next_*.png (scene_341 0000/0002/0004) and "
          "work/shots/english_map1_final.png (scene_310 0012, portrait box filled to capacity)")
    return True


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode not in ("identity", "growth", "english"):
        raise SystemExit("usage: accept.py identity|growth|english")
    ok = {"identity": identity, "growth": growth, "english": english}[mode]()
    sys.exit(0 if ok else 1)
```

- [ ] **Step 3: Run** `python -I scripts/accept.py english`, then view the screenshots. Use a contact sheet if there are many; the scratchpad `sheet.py` helper from earlier sessions, or view the PNGs individually. Confirm:
  - **Narration (`english_narration_next_*`):** line 1 blank, then "In a distant world… a voice echoes…" word-wrapped. Letters are legible, with a dark outline matching the Japanese glyph style. Next, the quote over up to 3 lines within the box, then "…  AM 6:12  …".
  - **Portrait box (`english_map1_final.png`):** four lines `AAAA…1` to `DDDD…4`, each exactly filling the box width, with nothing drawn outside the box frame.
  - If the portrait box shows only 3 lines, or text spills past the frame, the box geometry is wrong. Correct `wrap.BOXES` (and the Global Constraints value in this plan's ledger ruling), re-run the Task 4 tests, and re-check.

- [ ] **Step 4: Check the identity path still behaves**: `python -I scripts/accept.py identity`. Expected: the clean and identity-build screens now **differ** wherever hiragana appears, since the font patch is always applied. The ruling to ledger: from 2b on, identity acceptance compares only kanji/katakana-only frames or is retired. Update `CHAIN`/`COMPARE` in `accept.py` to the routes that still match (record which), or drop the identity mode if none do.

- [ ] **Step 5: Record** in `notes/english.md`:
  - the box table with evidence (boxcheck output, screenshots)
  - the font preview file
  - the acceptance screenshots and what they show
  - the known interim garbling of untranslated hiragana (system text, until 2c)
  - the rule for strings shared across box types (22×1)

- [ ] **Step 6: Commit**

```bash
git add scripts/fixtures scripts/accept.py notes/english.md
git commit -m "Add English rendering acceptance and record results"
```
