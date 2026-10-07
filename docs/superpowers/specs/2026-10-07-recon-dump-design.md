# Nage Libre EN — Sub-project 1: Recon & Script Dump

Date: 2026-10-07
Status: approved

## Context

Goal of the overall project: a **full public-release English patch** (BPS/IPS) for
*Nage Libre - Seijaku no Suishin* (Varie, 1995, SFC). Claude translates; the user reviews.

The whole project is split into sub-projects, each with its own spec → plan → implementation:

1. **Recon & dump** (this spec)
2. Insertion engine (reinsertion, repointing, ROM expansion, English font/VWF)
3. Translation (JP→EN, names/terms from `guide.txt`)
4. Graphics (title screen, text baked into tiles)
5. Patch build + playtest pipeline

This spec covers only #1. Nothing here modifies the ROM.

### Known facts

- ROM: `rom/Nage Libre - Seijaku no Suishin (Japan).sfc`, 1,572,864 bytes (12 Mbit), unheadered,
  LoROM, FastROM (map mode $30), cart type $02 (ROM+RAM+battery).
- Story-heavy: cutscenes before/after each of ~23 stages + Extra Stage; menus for shop,
  club activities, card battle (ATK/DEF/HP/ESC/SP/CHG/COS/??? cards), battle commands
  (Stand by, Attack, Item, Exchange, Pocketbell, Anime, Save).
- Character names (from guide): Yuki, Ayaka Sakurai, Mai Himenogi, Yui Kirishima,
  Miki Shizumoto, Ryoko Aoi, plus bosses listed per stage.
- Tools present: Mesen2 2.1.1 (supports `--testRunner` headless Lua with
  `emu.addMemoryCallback`, `emu.setInput`, `emu.takeScreenshot`), asar, xkas-plus,
  WLA-DX, snes2asm, superfamiconv, YY-CHR, Python 3.12.

## Approach: debugger-driven

Static relative search is skipped: the game very likely uses a kanji font and possibly
compressed text, which relative search can't handle. Instead, trace the live text engine.

1. **Reach text.** Lua script in Mesen2 `--testRunner` mode drives scripted input from boot to the
   first dialogue scene; save a savestate there so later runs start at text immediately.
   If scripted input proves too brittle, fall back to the user playing to the point in the
   Mesen2 GUI and saving the state (one-time manual step).
2. **Find the font.** Log VRAM writes while a line of dialogue prints; dump VRAM; identify
   font tile format (likely 2bpp or 4bpp, 8x8 or 16x16) and the ROM source of the font
   (DMA source address logged).
3. **Find the text stream.** Breakpoint/callback on the DMA source / tile-upload routine,
   walk back to the routine that reads script bytes; log the ROM addresses it reads.
   That yields: script location, character encoding (1- or 2-byte), control codes
   (newline, wait, page break, name, portrait, choice, end), and whether a decompressor
   sits in between.
4. **Map the structure.** Locate pointer tables for scenes/messages; determine banks
   and pointer format (16-bit in-bank vs 24-bit).
5. **Build the table.** Map each code to its glyph by rendering font tiles to PNG and
   transcribing (kana mechanically; kanji by reading the rendered sheet).
6. **Repeat for non-dialogue text**: menus, card/item names, battle text, shop, save
   screen. Classify each as script text vs graphics-baked.

## Deliverables

All paths relative to project root.

| Path | What |
|---|---|
| `notes/text-engine.md` | Findings: font location/format, encoding, control codes, compression, pointer tables, relevant routine addresses, RAM addresses |
| `notes/text-inventory.md` | Every text category (dialogue, menus, cards, items, battle, names, credits): location, size, script vs baked graphics |
| `nage.tbl` | Table file: hex code(s) → character; control codes as named tags, e.g. `<END>`, `<NL>`, `<WAIT>` |
| `scripts/mesen/*.lua` | Mesen2 recon scripts (input driver, VRAM/DMA/read loggers) |
| `scripts/dump.py` | Reads ROM + `nage.tbl`, follows pointer tables, writes the script |
| `scripts/decompress.py` | Only if text is compressed |
| `script/jp/*.txt` | Dumped script, one file per block/scene; each message tagged with pointer-table ID, ROM offset, original byte length |
| `font/jp_font.png` | Rendered font sheet used for table transcription |

Scripts: Python stdlib only. Run any Python that reads the ROM with `-I`.

## Verification

- **Round-trip test** (`scripts/test_roundtrip.py`): re-encode every dumped message with
  `nage.tbl` (and recompress if applicable) and compare byte-for-byte to the ROM. Must be
  100% identical. This proves the table, control codes and decompressor are correct, and is
  exactly what the insertion engine will build on.
- **Spot check**: for 3+ scenes, the dumped text matches a Mesen2 screenshot of that scene.
- **Coverage**: every pointer-table entry dumped; no unmapped bytes (`<$XX>` placeholders)
  remain, or any that do are listed in `notes/text-engine.md` with a reason.

## Repo hygiene

- `git init` at project root.
- `.gitignore`: `rom/`, `tools/`, `*.sfc`, `*.smc`, `*.srm`, `*.mss` (savestates). The ROM is
  never committed. Recon savestates live outside the repo or are ignored.

## Out of scope

Font hacks/VWF, translation, reinsertion, repointing, ROM expansion, graphics editing,
patch creation. Each gets its own spec once this one's findings are in.

## Risks

- **Compression**: if script is compressed (LZ variant, dictionary, Huffman), writing the
  decompressor is part of this sub-project; the matching recompressor waits for #2.
- **Kanji transcription**: several hundred glyphs may need reading off a rendered sheet;
  errors surface in the spot check and get fixed in the table.
- **Scripted input**: reaching specific scenes by input scripting may be slow; manual
  savestates from the user are the fallback.
