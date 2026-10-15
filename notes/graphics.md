# Graphics (sub-project 4)

## Method

1. **Font-match scan.** Every non-scene resource is decompressed, and its 2bpp tiles are compared with the quarters of the 16×16 font glyphs (codes ≥ 0x80). Japanese lettering in the UI is copied from the font, so its tiles match exactly.
   - 5 resources score high: `0x295` 84 tiles, `0x28B` 80, `0x274` 35, `0x27B` 30, `0x007` 22.
   - Every other resource scores at most 1, which is noise.
2. **Visual pass.** `python -I scripts/gfxsurvey.py` writes 2bpp and 4bpp sheets of all 572 candidate resources to `work/gfx/`. The throwaway mosaics (`work/mosaic*.py`) group them for inspection.
   - No hand-drawn Japanese was found.
   - Title, intro ("THE ACTUALLY WORLD", "THE WORLD OF nage"), "Fin.", "PUSH STARTBUTTON", the Varie logo, "CARD BATTLE", the battle HUD, birthstones and the map HUD are already English.
   - Everything else is sprites, portraits and map tiles.
3. **Emulator.**
   - `scripts/mesen/dump_screen.lua` dumps VRAM, OAM, CGRAM and PPU state.
   - `python -I scripts/gfxsurvey.py --find DUMP TILES…` maps on-screen tiles to resources.
   - Menu screens use BG3 (mode 1, 2bpp; tilemap at VRAM word `0x7C00`, characters at `0x5000`, i.e. VRAM tile `0x80` = byte `0xA800`; tile 0 is at byte `0xA000`).

## Inventory

| Resource | bpp | Tiles (VRAM) | Japanese → English | Screen | Seen in emulator |
|---|---|---|---|---|---|
| `0x27B` | 2 | `0x80-0xFF` | 待機 Wait, 攻撃 Attack, アイテム Item, 交換 Trade, ポケベル Pager, アニメ Anime, セーブ Save (each 5×2 tiles); "COMMAND" header already English | Map command menu (`g_open`) | yes (`g_open_final.png`) |
| `0x28B` | 2 | `0xA0-0xBF` | 彩香 Ayaka, 舞 Mai, 唯 Yui, 美姫 Miki, 嶺子 Ryoko (舞 and 唯 are one 16-px cell: "Mai" / "Yui" at 0 px letter spacing) | Pager → WHO window (`g_item4`); "WHO" header already English | yes (`g_item4_final.png`) |
| `0x28B` | 2 | `0xC0-0xEF` | 攻撃 防御 回復 必殺 着変 移動 → Attack / Guard / Heal / Super / Change / Move (4 cells each; "Defense" / "Special" / "Costume" don't fit, and the sprite cursor sits right of the 4 cells). Rows `$87:8C77+` (top, bottom = top + 10), table `81D092` by stock-card type `$027C` | Trade window (`debug_screens.py trade`) | yes (`en_trade_final.png`) |
| `0x295` | 2 | all | スピード / 通れません / 回復します / ダメージ床 / 〈costume〉向き → Speed / Blocked / Heals HP / Hurts HP / "Best: 〈Summer uniform, Winter uniform, Gym clothes, Swimsuit, Coat〉". Japanese shares cells between words, so the labels get fresh cells (arrow `0x4E` kept) and `build.terrain_patches` rewrites the bank-$87 rows, moves the costume rows to `$87:FA0C` and skips the 向き rows | Terrain panel: map free look (Y), A on a tile (`81D1F9`) | yes, all 8 variants (`tp_*`) |
| `0x274` | 2 | `0xB0-0xE1`, さ `0x9B` | 体力 / 腕力 / 防御力 / 素早さ / 精神力 → HP / ST / DEF / SPD / SPI, left-aligned like JP. Layout from the static tilemaps `0x275`/`0x276`; 力 (`0xB2`) is shared by four words and blanked, さ blanked | Status stat page (`debug_screens.py stats`) | yes (`en_stats_final.png`) |
| `0x274` | 2 | `0x95-0x9A` | EXP 次の (next) | none: no tilemap (`0x275/276/278/279`) or immediate references these cells; unused | no (unused) |
| `0x27B` | 2 | `0xDB-0xDE`/`0xEB-0xEE` + 2×2 cells `0xF0-0xFF` | 眠りますか？ → Rest? Layout from the static tilemaps `0x285`/`0x286`, line above NO/YES; mixes stride-16 columns and 2×2 cells (`cols` schema). The window is see-through: the gate pillar shows left of "Rest?" (JP too) | Rest? prompt (`debug_screens.py rest`) | yes (`en_rest_final.png`) |
| `0x007` | 2 | row 0 (16 tiles) | small 8×8 kanji | none: rows 0-3 are a scratch area overwritten in battle VRAM (birthstone labels); never shown | no (overwritten) |

Where these tiles also occur: the WHO and command-menu blank and frame tiles also appear in `0x262` (map HUD) and `0x007` (battle HUD). The edits change only label tiles, which are unique to their resource.

## Screens reached (states in `work/states/`)

| State | How | Screen |
|---|---|---|
| `g_open` | `map2` + `run_open.txt` (wait 120, A) | Command menu |
| `g_item2` | `g_open` + down×2, A | ITEM window (English header, no items yet) |
| `g_item4` | `g_open` + down×4, A | WHO window (party names) |
| `g_item5` | `g_open` + down×5, A | Anime ON/OFF (English) |
| `g_item6` | `g_open` + down×6, A | Save NO/YES (English) |

The other screens (status, terrain panel, Rest?, Trade, after-stage menu, shop, clubs, save) are reached by `scripts/debug_screens.py` (notes/playtest.md, Debug screens). Y / X only act in the unit-control loop `828BC0` (free look / Rest?), not while the map scrolls.

## Edits applied (`gfx/edits.json`)

| Screen | Resource | Result | Screenshot |
|---|---|---|---|
| Command menu | `0x27B` | Wait / Attack / Item / Trade / Pager / Anime / Save. Greyed items stay grey (palette 1, same colour indices), the cursor highlight works, the frame is intact | `gx_open_final.png` |
| WHO window | `0x28B` | Ayaka / Mai / Yui / Miki / Ryoko. Members not on the map stay dimmed as in the original. "Mai" / "Yui" use condensed spacing in their 16-px cells | `gx_who_final.png` |

## Formerly deferred (resolved with the debug screens)

`0x295` and `0x28B` `0xC0-0xEF` are translated and seen on screen; `0x274` EXP 次の is unused and `0x007` row 0 is overwritten before display (table above). Method for any new one: state on the screen, `dump_screen.lua`, read the BG3 tilemap (word `0x7C00`, tile = resource tile + `0x80`), find the bank-$87 rows the window helper `$878000` draws, then `gfx/edits.json`.

## Final check

- 185 tests pass; the build succeeds.
- The text routes (`accept.SYS_CHAIN`, prefix `gfx_`) are compared against the pre-graphics build (`full_`):
  - dialogue1, dialogue1_idle, birthday (settle60) and map1: final frames identical.
  - battle_a: same English UI, but a different card hand. The edited resources decompress at a different speed, which shifts frame timing and the random draw. This is expected.

## Review fixes

- `labels.render` refuses an area shorter than the glyphs (it used to garble the label silently), and renders an empty text as a blank area.
- `gfx/edits.json` labels may give `cols`: one entry per 8-px column, either a top tile (rows below via `stride`) or an explicit `[top, bottom]` list. This handles words spread over non-adjacent cells (精 + 神) and mixed layouts (眠り + 2×2 kana cells).
- The status screen and the 眠りますか？ prompt were laid out from their static tilemaps (`0x275`/`0x276`, `0x285`/`0x286`). The build composite shows HP / ST / DEF / SPD / SPI and "Rest?"; both confirmed on screen later (debug screens).
