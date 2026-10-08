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
   - Menu screens use BG3 (mode 1, 2bpp; tilemap at VRAM word `0x7C00`, characters at `0x5000`, i.e. VRAM tile `0x80` = byte `0xA000`).

## Inventory

| Resource | bpp | Tiles (VRAM) | Japanese → English | Screen | Seen in emulator |
|---|---|---|---|---|---|
| `0x27B` | 2 | `0x80-0xFF` | 待機 Wait, 攻撃 Attack, アイテム Item, 交換 Trade, ポケベル Pager, アニメ Anime, セーブ Save (each 5×2 tiles); "COMMAND" header already English | Map command menu (`g_open`) | yes (`g_open_final.png`) |
| `0x28B` | 2 | `0xA0-0xBF` | 彩香 Ayaka, 舞 Mai, 唯 Yui, 美姫 Miki, 嶺子 Ryoko (舞 and 唯 are one 16-px cell: "Mai" / "Yui" at 0 px letter spacing) | Pager → WHO window (`g_item4`); "WHO" header already English | yes (`g_item4_final.png`) |
| `0x28B` | 2 | `0xC0-0xFF` | 攻撃 防御 回復 必殺 着変 移動 (attack, defense, heal, special, change, move): glyph cells composed by a tilemap | not reached | no: needs screen + tilemap (playtest) |
| `0x295` | 2 | all | スピード 夏服 冬服 体操着 水着 コト 向き 連れません 回復床 ダメージ床: glyph cells shared between words (着 in 体操着 and 水着) | not reached (map info panel or costume display?) | no: needs screen + tilemap (playtest) |
| `0x274` | 2 | all | STATUS (English), HP/LV EXP (English), 次の (next), 体力 腕力 防御 素早 精神 (HP Str Def Spd Spirit) | Status screen, not reached | no: needs screen + tilemap (playtest) |
| `0x007` | 2 | row 0 (16 tiles) | small 8×8 kanji next to the battle HUD set | not identified | no: playtest |

Where these tiles also occur: the WHO and command-menu blank and frame tiles also appear in `0x262` (map HUD) and `0x007` (battle HUD). The edits change only label tiles, which are unique to their resource.

## Screens reached (states in `work/states/`)

| State | How | Screen |
|---|---|---|
| `g_open` | `map2` + `run_open.txt` (wait 120, A) | Command menu |
| `g_item2` | `g_open` + down×2, A | ITEM window (English header, no items yet) |
| `g_item4` | `g_open` + down×4, A | WHO window (party names) |
| `g_item5` | `g_open` + down×5, A | Anime ON/OFF (English) |
| `g_item6` | `g_open` + down×6, A | Save NO/YES (English) |

Not reached: status screen, club select, shop, after-stage menu, and whatever uses the `0x295` words. X / Y / Select / L / R on the map do nothing visible; X / Y in the menu do nothing.

## Edits applied (`gfx/edits.json`)

| Screen | Resource | Result | Screenshot |
|---|---|---|---|
| Command menu | `0x27B` | Wait / Attack / Item / Trade / Pager / Anime / Save. Greyed items stay grey (palette 1, same colour indices), the cursor highlight works, the frame is intact | `gx_open_final.png` |
| WHO window | `0x28B` | Ayaka / Mai / Yui / Miki / Ryoko. Members not on the map stay dimmed as in the original. "Mai" / "Yui" use condensed spacing in their 16-px cells | `gx_who_final.png` |

## Deferred to playtest (sub-project 5)

These are Japanese glyph cells composed into words by tilemaps that haven't been located, because their screens weren't reached:
- `0x295`: スピード, costumes 夏服 / 冬服 / 体操着 / 水着, コト, 向き, 連れません, 回復床 / ダメージ床
- `0x274`: status labels 次の / 体力 / 腕力 / 防御 / 素早 / 精神
- `0x28B` tiles `0xC0-0xFF`: 攻撃 防御 回復 必殺 着変 移動
- `0x007` row 0: small kanji

To finish each one:
1. Save a state on the screen.
2. Run `dump_screen.lua` on it and read its BG3 tilemap to get the cell order of each word.
3. Add the English to `gfx/edits.json` (one label per word area; shared cells may need a word-level redesign).
