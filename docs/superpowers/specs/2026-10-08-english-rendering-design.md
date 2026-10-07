# Nage Libre EN — Sub-project 2b: English Rendering (scene text)

Date: 2026-10-08
Status: approved

## Context

Overall goal: a full public-release English patch; Claude translates, the user reviews.

- Done: sub-project 1 (recon & dump) and 2a (re-insertion pipeline: `scripts/build.py` rebuilds and relocates all 333 scene blocks from `script/en` overrides into a 2 MB ROM plus a BPS patch).
- This spec, **2b**: render English in the 333 scene blocks (dialogue, narration, events).
- Next, **2c**: the bank-`$87` system text (battle messages, menus, shop/save prompts, enemy name lists), which needs its own reference hunt.

Decisions taken in brainstorming (by the user):

- **Fitting:** fixed 8×16 font; translation is *written to fit*. The build word-wraps and fails on overflow. No paging, no VWF (possible later upgrade).
- **Scope:** system text goes to 2c.
- **Font:** hand-drawn letterforms in the repo; the game's outline style is applied by a generator.

### Facts this design relies on

- The put-glyph routine `$80F390` treats code `< 0x10` as half-width.
  - A half-width glyph is `0x20` bytes = an 8×16 glyph (2 tiles, column-major top/bottom), with an advance of 1 column (8 px).
  - Full-width glyphs are `0x40` bytes, advance 2.
  - The threshold appears in exactly 3 places: `cmp #$0010` at `$80F3AD`, `$80F3C6`, `$80F425` (bytes `C9 10 00`).
- Font data lives at ROM `0x28000 + code*0x20`. Codes `0x02-0x0B` are half-width digits 0-9 (used by runtime-composed numbers: dates, HP). Codes `0x10-0x7E` are hiragana, `0x80+` katakana and kanji. `03FE` is the full-width blank.
- Glyph style (2bpp): stroke colour 1, 1-px outline colour 2, occasional colour 3; background 0.
- Box geometry, from the print handlers (column start `$1141`, right limit `$1144`):
  - Ops `01`, `13` (portrait box): start column 8, limit `0x1E` → **22 half-columns**. Japanese strings are at most 44-45 glyphs (4 lines × 11).
  - Ops `0B`, `26`, `2B`, `3B` (full box): start column 1, limit `0x1F` → **30 half-columns**. Japanese strings are at most 45 glyphs (3 × 15); op `0B` reaches 61.
- The engine wraps when column + width reaches the limit, mid-word. There's no paging inside a string; overflow is drawn below the box.
- Scene string references come from `bytecode.parse()` (`offset_operands`, `data_operands`), from 2a.

## Goal and success criteria

1. With `script/en` containing English entries, `python -I scripts/build.py` produces a ROM where those entries render in a legible 8×16 English font matching the game's outlined style, word-wrapped inside their box.
2. Verified in Mesen:
   - narration `scene_341 0000`, `0002`
   - portrait box `scene_310 0012`
   - one full-capacity string per box type that exactly fills its box without spilling
3. Strings that can't fit fail the build, naming the file, entry, box and overflow.
4. Untranslated entries still render. Kanji and katakana stay correct; hiragana shows as Latin characters (expected until translated). Half-width digits (dates, HP) are unchanged.

## Components

All Python 3.12 stdlib, run with `python -I`. Tests use `unittest`.

| File | Responsibility | Interface |
|---|---|---|
| `font/en_glyphs.txt` | Hand-drawn 1-bit letterforms for ASCII `0x20-0x7E` | text data (format below) |
| `scripts/fontgen.py` | Parse glyph art, add the outline, encode 2bpp column-major `0x20`-byte glyphs, render a preview PNG | `parse(text) -> dict[int, list[str]]`, `glyph_bytes(rows) -> bytes`, `font_bytes(glyphs) -> bytes` (codes `0x20-0x7F`, `0xC00` bytes), CLI `--preview font/en_preview.png` |
| `en.tbl` | Generated English table | `HEX=text` like `nage.tbl` |
| `scripts/entable.py` | Generate `en.tbl` | `python -I scripts/entable.py` |
| `scripts/wrap.py` | Fit English text into a box | `Box(cols, lines)`, `BOXES: dict[int, Box]` per opcode, `fit(text, box) -> str` (padded text with `<END>`), raises `FitError` |
| `scripts/build.py` (modify) | Encode translated entries with `en.tbl` through `wrap.fit` using each entry's smallest referencing box; apply the threshold patch and font bytes | unchanged CLI |

### Glyph art format (`font/en_glyphs.txt`)

```
# comment
char A
..##..
.#..#.
...      (13 rows of exactly 6 chars: '#' = stroke, '.' = empty)
```
- One block per character, introduced by `char X` (`char space` for `0x20`).
- Placement in the 8×16 cell: art columns 0-5 go to x 1-6, art rows 0-12 go to y 2-14.
  - Baseline at art row 9: capitals and digits use rows 0-9, descenders use rows 10-12.
- Outline: every empty cell 8-adjacent to a stroke cell becomes colour 2. Strokes are colour 1.
- Encoding: 8×16 → two 8×8 2bpp tiles (top, bottom), 16 bytes each, plane 0/1 interleaved per row, the same format `render_font.decode_tile` reads.

### English table (`en.tbl`)

- `XX00=<char>` for ASCII `0x20-0x7E` (code = ASCII value; ROM byte order `XX 00`). `FFFF=<END>!`. `FE03=` U+3000 (full blank, kept for Japanese-style padding).
- Symbols mapped to existing full-width glyphs: `…`→`AA02`, `♥`→`D003`, `♪`→`CE03`, `‼`→`E002`.
- `<BR>` is not a table entry; `wrap.fit` consumes it.

### Fitting (`wrap.fit`)

- **Width:** each table character is 1 half-column if its code is < `0x80`, else 2.
- **Line breaking:** split the text into words on spaces, then fill each line greedily.
  - A line break is made by padding the line with spaces (`0x20`) up to `box.cols`. A line that ends exactly at `box.cols` needs no padding.
  - `<BR>` forces a break, padding the rest of the line.
  - Consecutive spaces in the source are collapsed to one, except inside padding.
- **Errors:**
  - a single word longer than `box.cols`
  - more than `box.lines` lines
  - an unknown character
  - text not ending in `<END>`

  The error message gives the line count and overflow in characters.
- **Box per entry:** the smallest box (fewest cols × lines) among the print opcodes whose offset operands reference the entry.
  - Entries not referenced by any print op (the 29 unreferenced ones) use the full box.
  - `data` entries are never fitted (2a rejects edits).
- **Line counts:** `BOXES` starts at portrait 22×4 and full 30×3.
  - A plan task confirms them by wrap-simulating the Japanese entries per opcode (max lines at Japanese widths) and by an emulator check of a full-capacity string.
  - If op `0B` needs 4 lines, it gets its own box.

### ROM patches (in `build.py`)

| File offset | Original | New | Purpose |
|---|---|---|---|
| `lorom_to_pc($80F3AE)` | `10 00` | `80 00` | cache scan width threshold |
| `lorom_to_pc($80F3C7)` | `10 00` | `80 00` | DMA size (`0x20` vs `0x40`) threshold |
| `lorom_to_pc($80F426)` | `10 00` | `80 00` | advance width threshold |
| `0x28400-0x28FFF` | original hiragana glyphs | `fontgen.font_bytes()` | English glyphs for codes `0x20-0x7F` |

Every patch asserts the original bytes first, as 2a's mechanism does. The font region is verified against the clean ROM's hash for that range.

## Error handling

The build fails, naming the file and entry, on:
- a fit error (with box and overflow)
- an unknown English character
- a glyph-art parse error (character, line number)
- a patch site with unexpected original bytes

All 2a errors still apply.

## Testing

- `test_fontgen.py`:
  - parse (missing or duplicate chars, wrong row width or count rejected)
  - outline rule on a single pixel (3×3 ring)
  - byte encoding round-trips through `render_font.decode_tile`
  - all 95 printable ASCII characters present
- `test_entable.py`: the generated table encodes `"Hi, Yui!"` to the expected codes; `<END>` gives `FFFF`.
- `test_wrap.py`:
  - word wrap with padding; exact-fit line
  - `<BR>` and leading `<BR>`
  - overlong word and too many lines fail with the line count
  - full-width symbol widths
  - smallest-box selection for an entry referenced by two op types
- `test_build.py` additions:
  - threshold patch bytes present
  - font bytes at `0x28400` equal `fontgen.font_bytes()`
  - a translated `scene_341` entry decodes from the built block as the expected padded codes
  - an overflowing entry fails with `BuildError`
- Emulator (`notes/english.md`): screenshots of English narration, a portrait-box line, and full-capacity strings per box type. The preview PNG is reviewed by the user before glyphs are final.

## Out of scope

System text and enemy names (2c), title/HUD/graphics (sub-project 4), the translation itself (3), muting the text blip on spaces, VWF, automatic paging.

## Risks

- **Box line counts are wrong for some op**, so text spills. Mitigated by the Japanese-maximum simulation and full-capacity screenshots per box type.
- **Other code assumes hiragana codes** (e.g. composing names from code ranges). It would show as wrong letters, found in playtesting; 2c owns the system-text paths.
- **English doesn't fit even when concise.** Upgrade path: VWF or paging (a separate spec).
