# Nage Libre EN — Sub-project 2a: Re-insertion Pipeline

Date: 2026-10-07
Status: approved

## Context

Overall goal: a full public-release English patch; Claude translates, the user reviews.
Sub-project 1 (recon & dump) is done: see `notes/text-engine.md`, `notes/text-inventory.md`, `script/jp/`.
Sub-project 2 is split:

- **2a (this spec):** re-insertion pipeline. Edited scene text goes back into a playable ROM plus a BPS patch. Proven with Japanese text.
- **2b (next spec):** English rendering: 8×16 font via the half-width threshold patch, English table codes, per-box auto-wrap, relocation of the bank-`$87` system text.

### Facts this design relies on (from sub-project 1 and 2a brainstorming)

- Scene text lives in 333 compressed blocks, resources `0x30F-0x45B` of the resource table at ROM `0x50000` (3-byte LoROM pointers).
  - Decompressor `$80F8DC` is transcribed in `scripts/decompress.py`.
  - Blocks are decompressed to **`$7F:64C0`**. Each block is 16-bit bytecode up to the first `FFFF` word, then the string area (`FFFF`-terminated entries; 354 entries are flagged `data`).
- The bytecode interpreter dispatches through a compare chain at **`$838255`**: `cmp #$00NN / bne +6 / jsr handler / brl next` per opcode.
  - Handlers consume operand words with `inc $06` pairs.
  - String operands are offsets from `$64C0`: **8 handlers** do `adc #$64C0` (`83840D 838463 838755 8388E9 838C13 8396A9 83978F 839BAD`).
- The block loader at `$8380DB` sets the destination with 8-bit immediates at `$8380F0` (`lda #$C0 … #$64 … #$7F`).
- WRAM `$7F:7800-$7F:869F` is used by other code (`82BC48`, `82BEC7`…). Known window for a scene block: `$7F:64C0-$7F:77FF` = **`0x1340` bytes**. The largest Japanese block is `0xBD8` bytes.
- Free ROM space in the 1.5 MB ROM is only ~70 KB, scattered. Scene blocks total `0x1EBF0` bytes compressed.
- 2617 non-empty text entries have a matching bytecode word; 29 have none (unreferenced, or reached by adjacency).

## Goal and success criteria

`python -I scripts/build.py` produces `build/nage_en.sfc` and `build/nage_en.bps` from the clean ROM, `script/jp/`, and optional `script/en/` overrides, such that:

1. **Identity build** (no `script/en/`): every scene block is rebuilt, recompressed and relocated, and decompresses to exactly its original bytes. In Mesen, the existing routes show the same text at the spot-check frames.
2. **Growth build:** with `scene_341 0000` lengthened to ~2× (Japanese glyphs), the narration shows the new text, and the following strings in that scene still display correctly.
3. Applying `build/nage_en.bps` to the clean ROM reproduces `build/nage_en.sfc` byte for byte.

## Components

All Python 3.12 stdlib, in `scripts/`, run with `python -I`. Tests use `unittest` (`python -I -m unittest discover -s scripts`).

| File | Responsibility | Interface |
|---|---|---|
| `compress.py` | Greedy encoder for the nibble format. Only exact decompression matters, not size. | `compress(data: bytes) -> bytes` |
| `opcodes.json` | Opcode table generated from the compare chain, then checked in: per opcode the handler address, operand word count, and indexes of operands that are string offsets | data |
| `bytecode.py` | Generate `opcodes.json` (`--generate`); parse a block | `parse(block: bytes) -> list[Op]`, `Op(pos, opcode, operands, string_operand_positions)`; `code_end(block) -> int` |
| `layout.py` | Rebuild one scene block from its bytecode, ordered entries and new texts | `rebuild(block: bytes, entries: list[Entry], texts: dict[int, bytes]) -> bytes` |
| `bps.py` | Create and apply BPS patches | `create(src, dst) -> bytes`, `apply(src, patch) -> bytes` |
| `build.py` | CLI: whole-ROM build | `python -I scripts/build.py [--en script/en] [--out build]` |

### Opcode table derivation

- Walk the compare chain from `$838255` and collect `(opcode, handler)` pairs.
- For each handler, count `inc $06` pairs on its straight-line path, disassembling with `scripts/disasm.py`. Mark an operand as a string offset when the handler loads it and adds `$64C0`.
- Handlers with branches or variable-length operands get a manual entry in `opcodes.json` with a comment explaining the reading.
- The table is accepted only when the validation test passes (see Testing).

### Block rebuild (`layout.rebuild`)

- Keep the bytecode bytes; only string-operand words change.
- Strings keep their **original order and adjacency**: the new string area is the concatenation of each entry's bytes in index order. A translated entry uses its new encoded bytes, anything else uses its original bytes. `data` entries **always** use original bytes.
- Map old offset to new offset for every entry start. Rewrite every string operand through that map.

### ROM build (`build.py`)

1. Load the clean ROM and verify its size and checksum (`0xC895`).
2. Expand to 2 MB (pad `0xFF`). The header ROM-size byte `$7FD7` is already `0x0B` (2 MB). After expansion the checksum is the plain 16-bit byte sum of 2 MB; write the checksum and its complement at the end of the build.
3. For each scene resource:
   - Decompress, apply overrides through `layout.rebuild`, and check the size against the WRAM window.
   - Compress, append in the free area starting at `0x180000`, and write the new 3-byte FastROM pointer into the resource table.
   - Never let a compressed block cross a 32 KB LoROM bank boundary: the decompressor increments only the 16-bit part of `$09`.
4. Apply byte patches. Each patch is `(address, expected_original_bytes, new_bytes)` and is skipped with an error if the original bytes don't match. 2a needs patches only if the WRAM buffer moves.
5. Fix the checksum, write `build/nage_en.sfc`, and write `build/nage_en.bps` with `bps.create(clean, built)`.

### Translation input

- `script/en/scene_XXX.txt`, same format as `script/jp/`. Entries are matched by (block, index); their `@offset len=` headers are ignored.
- A missing file or entry falls back to Japanese.
- Text encodes through `nage.tbl` (2b adds English codes).

## WRAM window

- A measurement task traces WRAM writes to `$7F:0000-$7F:FFFF` across the routes for cutscenes, map, battle, menus, shop and the birthday screen. It records which spans other code uses, in `notes/wram.md`.
- Default limit: `0x1340` bytes per decompressed block. Exceeding it fails the build with a report of the offending blocks.
- If measurement shows a larger contiguous free span, `build.py` relocates the buffer by patching 11 bytes: the 8 `adc #$64C0` immediates plus the loader's three immediates at `$8380F0-$8380F9`. The base is one constant in `build.py`.
  - The relocation is verified by the identity build plus route screenshots.
  - If no larger span exists, the limit stands and 2b/translation must respect it, with the build report naming the blocks over it.

## Error handling

Each error fails the build, names the file, block and entry, and suggests a fix:

- the bytecode parse doesn't end exactly at the first `FFFF`
- a string operand doesn't land on an entry start
- an `en` file has an index the block doesn't have
- untranslatable characters (`tbl.encode` error, with position)
- a decompressed block exceeds the WRAM window
- the expanded ROM is out of space
- a byte patch finds unexpected original bytes
- the clean ROM checksum doesn't match

## Testing

- `test_compress.py`: decompress(compress(x)) == x for all 333 scene blocks, all other resources that decompress, empty input, and 200 seeded random inputs (including long `00`/`FF` runs and repeated words).
- `test_bytecode.py`: every scene block parses to exactly its `FFFF`. Every string operand hits a dumped entry start. Known ops (e.g. `002B 0124` in `scene_341`) parse as expected.
- `test_layout.py`:
  - On synthetic blocks: a growing string shifts later operands, `data` entries stay byte-identical, and an operand pointing at a later entry is repointed.
  - On real blocks: an identity rebuild of all 333 blocks reproduces the original bytes.
- `test_bps.py`: apply(src, create(src, dst)) == dst on synthetic data and on a built ROM. Header and CRC32 fields are checked.
- `test_build.py` (needs the ROM):
  - The identity build decompresses every relocated block back to the original.
  - The header size byte and checksum are valid, and the clean ROM is untouched.
- Emulator acceptance, recorded in `notes/insertion.md`:
  - **Identity build:** Mesen headless on `build/nage_en.sfc` replays routes `dialogue1`, `stage1` and `map1` and compares screenshots with the clean-ROM screenshots at the same frames. They must be pixel-identical.
  - **Growth build:** `scene_341 0000` is lengthened and shown via a screenshot, and `0002`/`0004` still show correctly afterwards.
  - `scripts/mesen.py` gains a `ROM=` parameter so routes can run against the built ROM.

## Out of scope

English font and table codes, auto-wrap, system text (bank `$87`) relocation, graphics, the translation itself.

## Risks

- **Variable-length opcodes** (e.g. choice menus) may need manual table entries. The parse-to-`FFFF` test catches mistakes.
- **WRAM window too small** with no free span to move to. Fallback for 2b: shorten text, or keep strings in ROM and patch the 8 string handlers to read through a pointer table (a bigger ASM change, specced in 2b only if needed).
- **Hidden extra references** to string offsets (the 29 unreferenced entries, arithmetic on offsets). Mitigated by preserving order and adjacency and by the route screenshot comparison.
