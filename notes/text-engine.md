# Text engine — findings

Traces: `trace.lua` from `dialogue1` (NAME=print, 600 frames, A every 45) vs `dialogue1_idle` (NAME=idle, 120 frames).
Tools: `python -I scripts/trace_diff.py work/trace/idle_rom.csv work/trace/print_rom.csv`.

## Font

- Dialogue glyphs are **DMA'd straight from ROM to VRAM**, one glyph per DMA, by `808E13` (channel 6, B-bus `$18`), size `$40`.
  - `$40` bytes = 16×16 glyph at 2bpp (4 tiles × 16 bytes).
  - Sources seen: `$85FFC0` (1st char, 遠), `$86EB40`, `$858540`, `$858D00`, … all in banks `$85`-`$86`.
  - Font region (file offsets) ≈ `0x28000`-`0x37FFF` → up to 1024 glyphs. ROM reader `808E16` covers `0x28480-0x36B7F` during printing.
  - VRAM destination: word `$5800`, `$5820`, … (+`$20` words per glyph).
- **Glyph code → ROM**: `80F390` (put-glyph, A = 16-bit code) queues DMA source `v = (code << 5) + $8000`;
  `808DCD` sends `v ≥ $8000` from bank `$85`, else `v + $8000` from bank `$86`.
  ⇒ **font offset = `0x28000 + code * 0x20`**. Codes `< 0x10` are half-width (`0x20` bytes, 8×16?); others full 16×16 (`0x40` bytes).
  Examples: `0x03FE` = blank (space/padding), `0x075A` 遠, `0x002A` く, `0x0068` の, `0x033A` 世, `0x033C` 界.
- A second VRAM upload path exists: `808C8B` DMAs `$40` bytes from WRAM (`$7E....`) 200 times. Possibly another font (e.g. the "AM6:12" timestamp line) or the box border. Checked in Task 4.
- Tile order inside a 16×16 glyph: **column-major** (TL, BL, TR, BR).
- Sheets: `font/jp_font_0{0..3}.png`, 256 glyphs each, row label = code of first glyph (codes step 2):
  `python -I scripts/render_font.py "rom/Nage Libre - Seijaku no Suishin (Japan).sfc" $((0x28000 + base*0x20)) 256 --layout col --base $base --step 2 --scale 2 -o font/jp_font_0K.png` with base = K*0x200.
- Layout: codes `0x00-0x0F` half-width digits 0-9 (8×16), `0x12-0x15F` kana and full-width digits, `0x180+` kanji.

## Trace candidates

ROM readers active only while text prints (operand fetches excluded; `007FEA-007FEF` = interrupt vectors, `00B2D3` = noise):

| PC | reads | ROM range | guess |
|---|---|---|---|
| `80F4B3` | 388 | up to `0x0186D2` (`$8386D2`) | **script reader** (few hundred bytes for ~6 messages) |
| `80F49D`, `80F378`-`80F37F` | 50-160 | near `0x7378-0xB2D7` | same routine family, tables in bank `$80`/`$81` |
| `808E16` | 2688 | `0x28480-0x36B7F` | glyph DMA source (42 glyphs × 64) |
| `80FA4C` | 22157 | up to `0x17382B` | bulk reader, likely scene graphics decompression |
| `80F8FA` | 48951 | `0x7909-0x7FEF` | table inside bank `$80` code, used with `80FA4C` |
| `80876B` | 512 | `0x24CF-0x578F` | unknown |


Resolved in Task 4: `80F4B3` copies box-border tilemap words (`03FE`), `80F378` is a memory fill. Neither is the script reader.

## Encoding

- Text = **16-bit little-endian glyph codes**, terminated by **`$FFFF`**. Code = font index (see Font).
- The string printer `80F5B0` (JSL wrapper `80F5AC`) reads words from `[$09]`. It stops on `FFFF`, otherwise calls put-char `80F433`, plays blip SFX `$0B` (`jsl $81F0FF`) for non-blank glyphs, and waits every 3 glyphs.
- **No control codes inside dialogue strings.** Line breaks come from width wrapping in `80F433`: column `$1141` advances by glyph width; when `col + width ≥ $1144` (`$1F`), row `$1142` += 2. Dialogue strings pad lines with `03FE` blanks (15 full-width glyphs per line). The first narration string has 15 blanks so its text lands on line 2.
- Draw-routine family (all in `$80F342-$80F712`, each with a `jsr`+`rtl` wrapper): `80F342` (14 callers), `80F4A7` (120 callers, banks `$81`/`$83`, menus?), `80F4CA`, `80F52F`, `80F5AC` (dialogue string), `80F609`, `80F639`, `80F697`, `80F6E8`. Menu text paths are inventoried in Task 9.

## Control codes

None in strings (see Encoding). Pacing, pages, portraits etc. are **event-script opcodes** (16-bit words) in the same block as the strings. E.g. opcode `0x002B` at `$7F64C6`, handler `839770`, operand `0x0124` → prints the string at block offset `0x0124` (`$7F:64C0 + operand`), set up by `839773-8397A0`.

## Compression

Scene blocks are **compressed** (string bytes are not in ROM raw). Decompressor `80F8DC` (JSL `80F8D8`, 27 callers, also used for non-text data):
- Pointers: source long `[$09]`, destination long `[$06]`.
- Header: first source byte = flag byte (`$02DB`). After that the stream is **4-bit nibbles**, high nibble first (`80FA42`).
- Loop: read nibble `n`, dispatch via jump table `$80F909`:
  - `0-7` **literal**: `b = (n << 4) | next_nibble` (7 bits). Bit 7 = top bit of flag byte; flag byte `<<= 1`. Every 8 literals a new flag byte is read from 2 nibbles.
  - `8` **word run**: `count = sum of bytes` (each byte from 2 nibbles; keep reading while byte == `FF`). Repeats the last two output bytes (`ring[idx-2]`, `ring[idx-1]`) `count` times (count 0 → 65536). Ring not updated.
  - `9` end.
  - `A` write `00`.
  - `B` write `FF`.
  - `C-F` write `ring[0..3]` (absolute slots `$02DF-$02E2`).
  - Every single-byte write (literal, A-F) also stores into the 4-byte ring `$02DF[$02DD]`, `$02DD = (idx+1) & 3`. Ring initialised to `FF FF FF FF`, idx 0.
- Narration block example: src `$A5ED8A` (ROM `0x12ED8A`) → dst `$7F64C0`.

## Pointers

- Loader `8380DB`: A = scene number. Resource id = scene + `0x030F` → `808843` sets `[$09]` from the **resource table at `$8A:8000` (ROM `0x50000`)**. Entries are 3-byte long pointers, index × 3 (via the `$211B/$211C` multiplier). 1328 (`0x530`) valid entries, ending at `0x50F8F`.
- Decompressed into `$7F:64C0`. Block begins with event-script words; string operands are offsets from `$7F:64C0`.
- Opening narration = resource `0x341` = scene `0x32`.
- Not every resource is a scene script. Text-bearing range is determined in Task 8 by decompressing and checking blocks.

## Uncertain glyphs

75 font slots still marked 〓 in `font/glyphs.txt` (they decode as raw `<$XXXX>`). After context resolution only **20 codes / 36 uses** remain unresolved in real text, mostly staff-credit names (`0440-0460`, `0576`, `058A`, `05A6`) plus `02F6` (decorative mark in "ＴＨＩＳＩＳ〓ＮＡＧＥ〓"), `01FA` ("地下にある〓の神殿"), `053C`. Unused slots never appear in the script.

Resolved by context and image (Task 8). Corrections to first readings: `0330` 私 (not 秘), `0266` 誰 (not 証), `0394` 嶺 (Ryoko = 葵 嶺子), `03D2` = sweat-drop emote (dumped as 💧). Another 91 codes resolved, e.g. `0308` 倒, `0372` 負, `051A` 後, `01F6` 塔, `039A` 唯, `071E` 迷 (雪迷宮).

## Table

`nage.tbl` is generated: `python -I scripts/build_tbl.py` from `font/glyphs.txt`. Glyphs that appear twice in the font get an invisible variation selector (U+FE01…) so every code stays unique and round-trips.

## Script dump

`scripts/textmap.json` kind `scene`: resources `0x30F-0x45B` (333 compressed event blocks) → `script/jp/scene_XXX.txt`.
Each block = 16-bit bytecode up to the first `FFFF` word, then the string area; every `FFFF`-terminated unit is one entry (offset relative to the decompressed block).
Dialogue strings are usually followed by an empty `<END>` entry (double `FFFF`). Display lines are wrapped every 15 full-width glyphs (encoder ignores newlines).
~354 entries in the string area are **non-text data** (small words like `0000`/`0001`/`0063`, digits). They round-trip but aren't for translation.
Known bytecode ops: `002B off` / `0026 off` print the string at block offset `off`; `0020`, `0024 a b c`, `0025 a b`, `0027`, `0029 n`, `002C`, `003A` (meaning TBD, sub-project 2).
