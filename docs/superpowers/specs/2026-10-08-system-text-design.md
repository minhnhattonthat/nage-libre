# Nage Libre EN — Sub-project 2c: System Text

Date: 2026-10-08
Status: approved

## Context

Overall goal: a full public-release English patch; Claude translates, the user reviews.

- Done:
  - sub-project 1 (dump)
  - 2a (scene-block rebuild/relocate pipeline, `scripts/build.py`)
  - 2b (English 8×16 font via the half-width threshold patch, `en.tbl`, box fitting)
- This spec, **2c**: the uncompressed **system text** in bank `$87`: ROM `0x38077-0x38B3E`, 319 `FFFF`-terminated strings, dumped as `script/jp/system.txt`. It covers:
  - enemy surname/given-name pools and boss names
  - club names
  - battle messages, shop/save/birthday prompts, after-stage menu
  - birthstones and jewel names

Until 2c lands, this text still prints Japanese hiragana as Latin letters (because of 2b's patch).

User decision in brainstorming: verify the menus with a **cheat-assisted route** to the after-stage menu (Mesen cheats from the guide). If automation stalls, the fallback is a user-made savestate.

### Facts this design relies on (brainstorming probes, 2026-10-08)

- **Readers:**
  - The generic string printer (`80F4A7` family, reads `[$09]`) prints most system strings.
  - The name builder (`81BA82..81BB40`) reads names through `[$09]`.
  - The helper `$878000` (A = 16-bit address; it sets `$0B = #$87` at `$878016`) builds text windows.
- **Split-immediate setups:** `lda #lo / sta dp / lda #hi / sta dp+1 / lda #$87 / sta dp+2` (8-bit). 101 sites in banks `$80-$8B` reference 62 distinct strings (indexes 244-318).
- **Name pointer table:** 3-byte long pointers at **`$81AF58`** (file `0xAF58`). Entry 0 is `$81A981` (not system text); entries 1+ are `$878077`, `$87807D`, … (surname/given-name/boss lists). The builder computes `index × 3`.
- **Name builder** (`81BAC6-81BAE8` surname, `81BB24-81BB46` given name) renders glyphs itself:
  - per code: `code << 5`; `lda $858000,X` if bit 15 is set, else `lda $860000,X`; copies `0x40` bytes (`ldy #$0040`) into a buffer `[$06]` cleared to `0x140` bytes (5 full-width cells)
  - It is the **only** direct font renderer (`lda $858000,X` / `$860000,X` occur only at `81BAD4/81BADA/81BB32/81BB38`).
- **Unknown reference mechanism:** club names (227-243), birthstones (289-300, fixed 16-byte records: 7 glyphs + `FFFF`), entry 253, and 295-306 have no split-immediate or pointer-table reference yet.
- **Cheats** work headless via `emu.addCheat(emu.cheatType.snesProActionReplay, "7E10CCFF")` (invincibility) and `"7E10D163"` (death hit). The first battle ends in one hit, showing battle messages.

## Goal and success criteria

1. Every system string is relocated to a new bank and every reference is repointed. Proven by:
   - an **identity relocation** (Japanese text moved) that renders pixel-identically to the 2b font-patched reference on the existing routes
   - a trace showing **zero reads** of the old block range on all routes, including the new cheat route
2. English system text from `script/en/system.txt` renders correctly:
   - battle names (surname + given name, half-width)
   - battle messages
   - birthday prompt
   - after-stage menu, shop, club select, save prompts

   Each is verified by screenshots on routes that reach them.
3. Strings that exceed their category's width budget fail the build with file, entry, category and limit.

## Components

| File | Responsibility | Interface |
|---|---|---|
| `scripts/sysrefs.py` | Find every reference to a system string; write/check `scripts/sysrefs.json` | `scan(rom) -> list[Ref]`; `Ref(kind, at, target_index, detail)`; `coverage(refs, entries) -> (covered, uncovered)`; CLI `--write`, `--check` |
| `scripts/sysrefs.json` | Checked-in reference list + manual entries (list bases, strides) with notes | data |
| `scripts/syslayout.py` | Lay out the English/JP system block in the new bank; produce patches for all references | `layout(entries, texts) -> (blob, new_addr: dict[index, int])`; `patches(refs, new_addr, rom) -> list[(off, old, new)]` |
| `scripts/syswidth.py` | Width budget per category | `CATEGORIES: dict[str, (first_index, last_index, max_cols)]`; `check(index, text, table) -> None` raising `ValueError` |
| `scripts/build.py` (modify) | Place the system blob at file `0x1F8000`; apply reference patches, the helper bank patch, the name-renderer patch; overwrite the old block with a marker | unchanged CLI |
| `scripts/mesen/routes/stage1_clear.txt` + cheat support | Cheat-assisted route from `stage1b` (first battle) to the after-stage menu, then shop/club/save | `goto.lua` gains a `CHEATS` param (comma-separated PAR codes) |
| `scripts/mesen/oldreads.lua` | Count reads of the old system block per route | writes `work/trace/oldreads_<NAME>.txt` |

### Reference kinds and patch rules

- **split:** the `lo`/`hi`/bank immediate bytes at the three `lda` operands become the new address bytes (bank `$BF`).
- **ptr24:** a 3-byte little-endian pointer in a table becomes the new long address.
- **imm16+helper:** a 16-bit `lda #$xxxx` feeding `jsl $878000` gets the new low 16 bits. The helper's `lda #$87` at `$878017` (operand) becomes `#$BF`. All system strings therefore live in bank `$BF`.
- **base+walk / base+stride:** discovered in the investigation task. Patch the base reference with one of the rules above. The list stays contiguous and in order. For a stride, every record is padded to the stride length (`FE03` blanks + `FFFF`).
- Each patch asserts the original bytes, like 2a/2b.

### Layout

- Entries are concatenated in original index order, starting at file `0x1F8000`. The blob must fit within the bank (≤ `0x8000` bytes).
- English for entry *i*: `en.tbl` encoding of `script/en/system.txt` entry *i* (no box wrapping; width is checked per category). Without a translation, the original bytes are used.
- The old block `0x38077-0x38B3E` is filled with marker glyph `■` (`03FC`) and `FFFF` terminators at every original entry end. A missed reference then prints `■■■` with the original lengths kept, instead of crashing.

### Name renderer patch

- In both copy loops (`81BACC` and `81BB2A`, `ldy #$0040`), the byte count becomes `0x20` when the code is < `0x80`, else `0x40`. The cell output pointer advances by the same amount.
- Implemented as a jump to a small routine in free space in bank `$81`, or the new bank if bank `$81` has none, written with **asar** (`tools/asar/asar.exe`) from `asm/name_render.asm`. The assembled bytes are inserted by `build.py` with original-byte assertions at the hook sites.
- The buffer stays `0x140` bytes = 10 half-width characters per name part. The width budget for name parts is the visible field width, measured in the battle HUD screenshot (≤ 10).

### Width budgets

Per category: max half-columns, taken from where the string is drawn.

- Names: field width in the battle HUD.
- Battle messages: battle message window width minus the longest name (messages concatenate `<name>` + suffix).
- Prompts/menus: their window width.

The values are established in a plan task from screenshots and Japanese maxima, recorded in `notes/system-text.md`, and enforced by the build.

## Error handling

The build fails, naming entry index and category, on:
- uncovered references at build time (`sysrefs --check` must be clean)
- a patch-site original-bytes mismatch
- blob overflow beyond the bank
- a width-budget violation
- an untranslatable character

## Testing

- `test_sysrefs.py`:
  - scanner finds known sites (e.g. `8198B7` → entry for `$86DF` 「の攻撃‼」; the `$81AF58` table → entries 0-226)
  - coverage reports no uncovered entries, except ones listed as unused with a reason in `sysrefs.json`
- `test_syslayout.py`:
  - layout order/contiguity; patch bytes for each kind on synthetic data
  - stride padding and overflow error
- `test_syswidth.py`: budgets per category; error names entry and category.
- `test_build.py` additions:
  - identity relocation: every reference in the built ROM resolves to a string equal to the original
  - old block is marker-filled; helper bank patched; name-renderer hook bytes present
- Emulator (`notes/system-text.md`):
  - identity relocation pixel-identical on existing routes
  - `oldreads` = 0 on all routes
  - English samples visible on battle (names + messages), birthday, after-stage menu, shop, club, save screens (cheat route)

## Out of scope

The translation of all system strings (sub-project 3; 2c ships only sample English for verification), title/HUD graphics (sub-project 4), VWF.

## Risks

- **Unlocated reference mechanisms** for clubs/birthstones/etc. Mitigation: dynamic trace on the screens that show them, plus the marker fill exposing misses.
- **Cheat route tuning cost.** Fallback: user savestate at the after-stage menu.
- **No free space in bank `$81`** for the hook. Use the new bank `$BF` with `jsl`/`rtl`.
- **Names concatenated by other code** (e.g. battle messages with `<name>の攻撃‼`) may overflow windows. Handled by budgets; verified in the battle screenshots.
