# System text (2c)

## Routes and coverage of screens

- Cheats via `goto.lua`/`oldreads.lua` param `CHEATS` (Pro Action Replay): `7E10CCFF` invincible, `7E10D163` death hit, `7E17790F`/`7E177A27` infinite gold.
- `stage1_clear.txt` (from `stage1b`) wins several battles automatically: names and the attack/damage/defeat/gold messages are on screen.
- **Stage clear / after-stage menu not reached by play routes** (now reached with `scripts/debug_screens.py`; history below):
  - The tactical map needs cursor-driven moves to the remaining enemies, and random input traps the map command menu ("WHO" window).
  - Shop / club select / save / after-stage menu are therefore verified by full static reference coverage plus old-block reads on the reachable screens only, and are **flagged for playtest**. A savestate at the after-stage menu (Mesen GUI, copied into `work/states/`) would enable the visual check (`accept.py system` picks up states `shop`/`club`/`save` if present).

## References (`python -I scripts/sysrefs.py --check`)

| Kind | Count | Covers |
|---|---|---|
| split (`lda #lo/sta dp; lda #hi/sta dp+1; lda #$87/sta dp+2`) | 101 sites | 62 strings: battle messages, prompts, menus, jewels (indexes 244-318 minus birthstones) |
| ptr24 table `$81AF58` (3-byte, index×3) | 244 pointers | names, bosses, clubs (0-243) |
| ptr24 table `$87DABB` (3-byte + pad, stride 4) | 12 pointers | birthstones (295-306) |
| ptr24 table `$87E346` (3-byte + pad, stride 4) | 16 pointers | club names (227-242), read by `lda $87E346,X` at `$87E32B` / `$8392B8` (club select, shop). Missed at first: per-entry coverage can't see a second table for already-covered entries. Guard: `test_every_long_read_pointer_table_is_configured` (every `lda long[,X]` that hits a pointer to a system entry must fall in a configured table) |
| list by adjacency | — | 253 (入れかえるカードを選んでね): no direct reference; follows split-referenced 252 |

- `confirmed_imm16` is empty. Every 16-bit candidate from brainstorming (`81BCCE`, `81BCE2`, `81EDAA`, `82F01D`, `87F721`) was a misdecode of 8-bit code or a club-list base already covered by the `$81AF58` table.
- The window helper `$878000` is **not** a system-text reader. Its 46 callers pass `$8B57-$8D65`: window tilemap rows after the system block, which stay in bank `$87`. Its `lda #$87` must stay unpatched (the spec assumed otherwise).

## Emulator verification (`python -I scripts/accept.py system`)

**Identity relocation** (system text moved to `$BF8000`, Japanese, vs clean + 2b font patches):

| Route | Result |
|---|---|
| dialogue1, dialogue1_idle, settle60 (birthday screen), map1 | MATCH |
| battle_a (cheats, first battle) | DIFF, timing only: a flying card sprite sits a frame apart (`sysref_battle_a_00330` vs `sysbuilt_…`). Names 霧島唯 / 梨田静子, HUD and message box identical by inspection |

**Old-block reads** (`oldreads.lua` on the identity build): **0 on every route**: dialogue1, dialogue1_idle, stage1, settle60, map1, stage1b, battle_a. Names (pointer table), battle messages (split refs) and the birthday screens (birthstone table) all read from bank `$BF`.

**English samples** (`scripts/fixtures/en_sample/system.txt`):

| Screen | Screenshot | Result |
|---|---|---|
| Birthday confirmation | `sysen_bday_00045.png` | 「Are these birthdays OK?」 fits the window (≈24 half-columns) |
| Battle HUD names | `sysen2_battle_00630.png` | `Yui` / `Shizuko`, half-width, two letters per 16-px cell |
| Battle messages | `sysen2_battle_00630.png`, `sysen_battle_a_00780.png` | 「Yui's attack! / Shizuko took 25352 damage!」, 「Shizuko was defeated! / 120 gold obtained!」 |
| Birthday entry (untranslated) | `sysen_stage1_03870.png` | birthstone ルビー and name 姫ノ木舞 still correct from the relocated block |

## Width budgets (`scripts/syswidth.py`)

- **Names:** the name builder writes surname + given name into **one** 0x140-byte buffer (`$7F2A40` player / `$7F2B80` enemy): 10 half-width letters. Overflow writes past it into WRAM. The Japanese-style pair was cut off: 「KirishimaY」, 「NashidaShi」.
  - Pairs are fixed per stage (indexes from the stage data stream at `$82934D` → enemy record +$1D/+$1E), so the bound is widest surname + widest given name ≤ 10.
  - Once any name is translated, **all surnames 0-99 must be** (an untranslated 3-kanji surname is 6 columns); untranslated given names count at their Japanese width.
  - **Recommended convention:** empty surnames (`<END>`), given names only. The fixture does this.
- **Battle lines:** messages are assembled from pieces, so the build checks whole lines against the 28-column window (the width of the line-clear string, entry 244):
  - name + 249 + number + 250/251, name + 248/263/277, number + 264, 271 + number + 274
  - name = widest given/boss name (100-226, translated or Japanese); numbers = 5 digits
  - Text past column 29 wraps onto the window border (cols 0/30-31), which the line clear (cols 2-29) never erases: leftover tiles in later messages.
  - **Birthstone bonus 258:** JP appends it to name + 248 on line 1 (damage routines `819959`/`8199F1`, only when the attacker's card jewel = birthstone). English would be 37 columns, so the build (when 258 is translated) redirects the two `jsl $80F4A7` at `819988`/`819A20` to `BONUS_HELPER` (`$81F1C0`): bonus on line 2, 60-frame wait, clear line 2, then the routine's damage line. Verified with `FORCE_BONUS` / longest names (Tsukiyomi, Sakurako) via a Lua hook (writes `$10C8`/`$10E8` = birthstone, name indexes `$1084` player / `$109C` enemy = system entry + 1).
  - **275** (heal / DEF-up routines `819A89`, `819AF3`, `819B5D`, `819BC7`): prints at line 1 start, because those actions put no text on line 1 (dispatch `81E91A`). Seen in battle for all four routines via forced birthstone checks (notes/playtest.md, Debug screens).
- **Prompts:** 24 half-columns (measured on the birthday confirmation window).
- **Other categories:** the Japanese maximum (birthstones 14, menu items 14, clubs 10). Not measured on screen; the menus weren't reached (see Routes).
