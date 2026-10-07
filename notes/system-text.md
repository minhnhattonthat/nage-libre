# System text (2c)

## Routes and coverage of screens

- Cheats via `goto.lua`/`oldreads.lua` param `CHEATS` (Pro Action Replay): `7E10CCFF` invincible, `7E10D163` death hit, `7E17790F`/`7E177A27` infinite gold.
- `stage1_clear.txt` (from `stage1b`) wins several battles automatically: names and the attack/damage/defeat/gold messages are on screen.
- **Stage clear / after-stage menu not reached** (time box, ~10 route iterations):
  - The tactical map needs cursor-driven moves to the remaining enemies, and random input traps the map command menu ("WHO" window).
  - Shop / club select / save / after-stage menu are therefore verified by full static reference coverage plus old-block reads on the reachable screens only, and are **flagged for playtest**. A savestate at the after-stage menu (Mesen GUI, copied into `work/states/`) would enable the visual check (`accept.py system` picks up states `shop`/`club`/`save` if present).
