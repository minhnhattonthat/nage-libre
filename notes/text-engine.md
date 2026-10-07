# Text engine — findings

Traces: `trace.lua` from `dialogue1` (NAME=print, 600 frames, A every 45) vs `dialogue1_idle` (NAME=idle, 120 frames).
Tools: `python -I scripts/trace_diff.py work/trace/idle_rom.csv work/trace/print_rom.csv`.

## Font

- Dialogue glyphs are **DMA'd straight from ROM to VRAM**, one glyph per DMA, by `808E13` (channel 6, B-bus `$18`), size `$40`.
  - `$40` bytes = 16×16 glyph at 2bpp (4 tiles × 16 bytes).
  - Sources seen: `$85FFC0` (1st char, 遠), `$86EB40`, `$858540`, `$858D00`, … all in banks `$85`-`$86`.
  - Font region (file offsets) ≈ `0x28000`-`0x37FFF` → up to 1024 glyphs. ROM reader `808E16` covers `0x28480-0x36B7F` during printing.
  - VRAM destination: word `$5800`, `$5820`, … (+`$20` words per glyph).
- A second VRAM upload path exists: `808C8B` DMAs `$40` bytes from WRAM (`$7E....`) 200 times. Possibly another font (e.g. the "AM6:12" timestamp line) or the box border. Checked in Task 4.
- Tile layout inside a glyph: tile order still to confirm when rendering (Task 5).

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

## Possible compression

Glyphs come straight from ROM, not composed in WRAM. Whether script bytes are read raw is answered in Task 4 by watching `80F4B3`.
