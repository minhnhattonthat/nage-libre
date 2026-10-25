# Insertion pipeline (2a) — results

## Build

`python -I scripts/build.py` → `build/nage_en.sfc` (2 MB) + `build/nage_en.bps` (identity build: 125130 bytes).
- Translations: `script/en/scene_XXX.txt` (same format as `script/jp`). Missing files or entries fall back to Japanese.
- All 333 scene blocks are rebuilt (`layout.rebuild`), recompressed (`compress.py`) and appended from file `0x180000` (CPU `$B08000+`), never crossing a 32 KB bank. The resource table is repointed and the header checksum fixed.
- BPS verified: `bps.apply(clean, patch) == built`.
- WRAM: buffer stays `$7F:64C0`, window `0x1340` (`docs/re/wram.md`). Relocation patches (`build.relocation_patches`) cover all 9 hard-coded sites but aren't used.

## Emulator acceptance (`python -I scripts/accept.py identity|growth`)

**Identity** (clean ROM vs identity build, same input routes; final screenshots compared byte for byte):

| Route | Result |
|---|---|
| dialogue1 | MATCH |
| dialogue1_idle | MATCH |
| stage1 (+60 idle frames, `settle60`) | MATCH |
| map1 | MATCH |

`stage1`'s own final frame differed only by fade timing. The built ROM runs a few frames behind mid-fade: the greedy recompressor emits more nibbles, so decompression takes more cycles. The text was identical, and frames re-converge (`settle60` and `map1` match).

**Growth** (`scene_341 0000` doubled):
- `work/shots/growth_narration_next_00090.png` / `00120.png`: the doubled line prints. Text past the box capacity is drawn below the frame.
- Later frames show 「この世界を全て私の物に……／心に闇を持つ者を集めて……」 and 「……　ＡＭ０６：１２　……」 intact. The strings after the grown one are repointed correctly.

## Findings for 2b

- **No paging inside a string.** The narration box shows 2 lines × 15 full-width glyphs, and overflow is drawn outside the box. English must fit each box's capacity, or the build must split long strings into extra print ops (bytecode growth). This needs designing in 2b. The 8×16 half-width font doubles capacity to 2 × 30 characters.
- Timing differs slightly between the original and recompressed data (frames). Harmless, but routes and screenshot comparisons should use settled frames.
- Untested: shop, club select, save/load, ending (their text isn't in scene blocks, apart from credits).
