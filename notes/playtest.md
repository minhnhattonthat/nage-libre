# Scripted playtest (sub-project 5)

## Tools

- **`scripts/tour.py` + `scripts/mesen/scene_hook.lua`: forced-scene tour.**
  - From state `stage1`, route `tour_base.txt` reaches the first scene-loader call (`8380DB`, frame 590). The hook replaces A with the wanted scene.
  - It screenshots 6 frames after every op 06 (wait, `83859C`), i.e. one shot per text page, and presses A 8 frames later.
  - A keep-alive A press fires every 120 idle frames. The run ends after 900 frames without a wait.
- **Japanese reference:** the identity build (`build.build(clean)`): relocated scene buffer, Japanese text, 2b font, so hiragana show as Latin letters. The original ROM's small scene buffer crashes on scenes forced out of context.
- **`scripts/mesen/redirect.lua`:** jumps to a routine when another is entered, with the same stack.
- **`scripts/mesen/pc_hits.lua`, `ret_addr.lua`:** execution and return-address probes.

## Deeper screens

The main loop (`8093DD…`) calls the after-stage menu `87CA0F` right before the stage routine `828000` (call site `8093E5`). Redirecting `828000` → `87CA0F` on its first execution (from `stage1`, route `work/run/to828.txt`) opens the menu with a consistent stack. The state is saved as `menu_f2`.

| Screen | How (from `menu_f2`) | Screenshot | Result |
|---|---|---|---|
| After-stage menu | — | `menu_f2_00260.png` | "What now?" Shop / Clubs / Save / Start: English |
| Shop | A | `am_shop_final.png` | "Switch characters" prompt (system 281), card prices G100-G700, gold: English |
| Club select | down, A | `am_club2_final.png` | stat panel LV/AT/AG/HP/DF/MT (graphics, English); club name "Student" (system 242) |
| Save | down×2, A | `am_save_final.png` | "Save to which file?" File 1-3 / none: English |
