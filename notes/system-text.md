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
