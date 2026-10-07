# System text (2c)

## Routes and coverage of screens

- Cheats via `goto.lua`/`oldreads.lua` param `CHEATS` (Pro Action Replay): `7E10CCFF` invincible, `7E10D163` death hit, `7E17790F`/`7E177A27` infinite gold.
- `stage1_clear.txt` (from `stage1b`) wins several battles automatically: names and the attack/damage/defeat/gold messages are on screen.
- **Stage clear / after-stage menu not reached** (time box, ~10 route iterations):
  - The tactical map needs cursor-driven moves to the remaining enemies, and random input traps the map command menu ("WHO" window).
  - Shop / club select / save / after-stage menu are therefore verified by full static reference coverage plus old-block reads on the reachable screens only, and are **flagged for playtest**. A savestate at the after-stage menu (Mesen GUI, copied into `work/states/`) would enable the visual check (`accept.py system` picks up states `shop`/`club`/`save` if present).

## References (`python -I scripts/sysrefs.py --check`)

| Kind | Count | Covers |
|---|---|---|
| split (`lda #lo/sta dp; lda #hi/sta dp+1; lda #$87/sta dp+2`) | 101 sites | 62 strings: battle messages, prompts, menus, jewels (indexes 244-318 minus birthstones) |
| ptr24 table `$81AF58` (3-byte, index×3) | 244 pointers | names, bosses, clubs (0-243) |
| ptr24 table `$87DABB` (3-byte + pad, stride 4) | 12 pointers | birthstones (295-306) |
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

- **Names:** the name builder writes surname + given name into **one** 5-cell buffer (10 half-width letters). The Japanese-style surname+given pair was cut off: 「KirishimaY」, 「NashidaShi」.
  - Enemy names pair a random surname with a random given name, so the build enforces **widest translated surname + widest translated given name ≤ 10**.
  - **Recommended convention:** empty surnames (`<END>`), given names only. That's what the fixture uses.
- **Prompts:** 24 half-columns (measured on the birthday confirmation window).
- **Other categories:** the Japanese maximum (battle 28, birthstones 14, menu items 14, clubs 10). Not yet measured on screen; the menus weren't reached (see Routes).
