# Nage Libre EN — Sub-project 4: Graphics

Date: 2026-10-08
Status: approved (standing approval: "approved for all spec and implementation plan")

## Context

Overall goal: a full public-release English patch. Claude translates and the user reviews.

Done so far:
- 1: dump
- 2a: insertion pipeline (compress, relocate to `0x180000+`, repoint)
- 2b: English font and fitting
- 2c: system text
- 3: the whole script (2572/2572 entries)

What is left is Japanese drawn as **graphics**: labels baked into tiles, which the text pipeline never sees.

### Facts this design relies on (probes, 2026-10-08)

**The map command menu** (open it: state `map2` → wait 120 frames → A) is Japanese graphics: 待機 / 攻撃 / アイテム / 交換 / ポケベル / アニメ / セーブ under an English "COMMAND" header.
- **Where it lives:**
  - It is BG3 in mode 1: tilemap at VRAM word `0x7C00`, characters at `0x5000`, 2bpp.
  - Label tiles are `0x80-0xE4`. Each item is 5×2 tiles (40×16 px), header tiles are `0x80-0x85`, and the greyed items use palette 1.
- **Where it comes from:**
  - The label tiles are **resource `0x27B`**: 2048 bytes once decompressed, tile `0x80` at offset 0, compressed with the same nibble format as the scenes.
  - The tilemaps are resources `0x27C` / `0x27D` (left and right window positions).
  - The glyph shapes are copies of the 16×16 font, which is why single tiles match font glyphs.
- **Rebuild:** `compress.compress(decompress(0x27B))` round-trips, at 1369 bytes against the original 1389. The 2a pipeline already relocates compressed resources and repoints `RES_TABLE` (`0x50000`, 3-byte pointers, 1328 entries).
- **Already English** (sub-project 1 inventory and screenshots): title logo and menu, battle HUD and cards, map HUD (TIME·SPEED, names), "COMMAND", "CARD BATTLE", "TURN".
- **Not yet seen:** screens behind the command menu (Item, Exchange, Pager, Anime, Save), the "WHO" window, club select, shop, after-stage menu, status. Any of them may hold more Japanese graphics.

## Goal and success criteria

1. **Inventory:** `notes/graphics.md` lists every resource whose tiles contain Japanese lettering:
   - resource id, bpp, tile range
   - what each label says, the English
   - the screen where it appears, and whether that screen was seen in the emulator

   It is found by a **systematic survey**: every decompressible non-scene resource is rendered as 2bpp and 4bpp tile sheets and inspected, then cross-checked against emulator dumps of every reachable screen.
2. **Replacement:** every inventoried Japanese label is replaced by English rendered with the project's English glyphs (`font/en_glyphs.txt`):
   - proportional spacing, same colour indices as the original lettering, inside the original tile area
   - tiles that are not lettering stay byte-identical
3. **Build:** `build.py` rebuilds edited graphics resources (compress, place in free space, repoint the resource table). It fails if a label doesn't fit its tile area or the free space runs out.
4. **Emulator:** the command menu shows English, and so does every other replaced screen the routes reach. The build without graphics edits is unchanged from the current English build.

## Components

| File | Responsibility | Interface |
|---|---|---|
| `scripts/tiles.py` | Planar tile codec and PNG sheets | `decode(data, bpp) -> list[list[list[int]]]` (tiles of 8×8 colour indices); `encode(tiles, bpp) -> bytes`; `sheet(tiles, cols, scale, palette=None) -> png bytes` |
| `scripts/resources.py` | Resource table access | `pointer(data, rid) -> file offset`; `load(data, rid) -> bytes` (decompressed); `ids(data) -> range` |
| `scripts/gfxsurvey.py` | Survey CLI | writes `work/gfx/res_XXX_2bpp.png` / `_4bpp.png` for every decompressible non-scene resource, plus `work/gfx/index.txt` (id, size, plausible bpp) |
| `scripts/labels.py` | English label renderer | `render(text, width_px, height_px, ink, outline) -> tile pixel grid`; `fits(text, width_px) -> bool`. Glyphs come from `font/en_glyphs.txt` with blank columns trimmed and 1 px spacing |
| `gfx/edits.json` | Edit list | `[{"res": "0x27B", "bpp": 2, "labels": [{"tile": "0x90", "w": 5, "h": 2, "text": "Wait"}, …]}]` (`tile` = top-left tile index relative to the resource's first tile; `w`/`h` in tiles; tiles laid out row-major within the resource as the tilemap uses them) |
| `scripts/build.py` (modify) | Apply `gfx/edits.json`: load, render labels into the tile area, encode, compress, place, repoint | `gfx_resources(clean) -> dict[rid, bytes]` (compressed), merged into the relocation loop |
| `scripts/mesen/dump_screen.lua` | VRAM / OAM / CGRAM / PPU state of a screen | exists (written during the probe) |
| `notes/graphics.md` | Inventory and results | prose and tables |

## Label rules

- **English for the command menu**, each ≤ 40 px:
  - 待機 Wait, 攻撃 Attack, アイテム Item, 交換 Trade, ポケベル Pager, アニメ Anime, セーブ Save
  - each label vertically centred in its 16-px cell
- **Colour indices:** the dominant non-zero indices of the original label give the ink and outline colours, so greyed and highlighted palettes keep working.
- **Too-long labels:** a label that doesn't fit is a build error. The fix is a shorter word, recorded in `notes/graphics.md`.

## Survey method

1. `gfxsurvey.py` renders all resources outside the scene range `0x30F-0x45B` that decompress cleanly to a size that is a multiple of 16. Claude inspects the sheets for lettering; kana and kanji are recognisable even in greyscale.
2. **Emulator:** dump every reachable screen (`dump_screen.lua`):
   - command menu and its sub-menus via scripted input from `g_open`
   - the WHO window, the battle card menus, birthday, title
   - with cheats, as far into the after-stage flow as routes allow

   Map each Japanese label seen on screen back to its resource by searching the decompressed resources for its tiles.
3. **Inventory rows** record the screen and the "seen in emulator" column. Rows found only in the survey get "unverified, playtest".

## Error handling

- Decompression failure on a resource: the survey skips it and logs it in `index.txt`.
- A label wider than its area or taller than 16 px: `BuildError` with resource, tile and text.
- Free space exhausted: the existing build error.
- An edited resource that decompresses to a different length than the original: `BuildError` (tile count must not change).

## Testing

- `tiles.py`: decode/encode round-trips on resource `0x27B` (2bpp) and a 4bpp resource; known pixel values of tile `0x90` (the font glyph 待, top-left).
- `labels.py`: "Wait" fits in 40 px; a 12-letter word doesn't; the rendered ink uses only the given indices.
- `build.py`:
  - with an empty `gfx/edits.json` the build is byte-identical to the current English build
  - with the command menu edit, resource `0x27B` decompresses from its new location to the edited tiles, and only the label tile areas differ
- **Emulator:** command menu screenshot shows English (accept route `g_open`).

## Out of scope

- Redrawing the title logo: it is already English.
- Changing menu layouts or tilemaps. The labels must fit the existing tile areas.
- Full playtest and the release BPS: sub-project 5.
