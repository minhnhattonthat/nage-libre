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

Not reached:
- **Status screen (`0x274`).** Club select ignores X/Y/Select/Start/L/R (`cs_*_final.png`); B goes back to the menu.
- **Rest? prompt.**

Both edits are checked statically only (labels.py render + tile test).

## Forced-scene tour (all 333 scenes, EN build vs JP identity build)

- **Coverage:** 305 scenes have op-06 pages, 1614 pages on each ROM, with equal per-scene page counts. The other 28 are timed narration with no key waits (`032 033 036 03D 040 044 047 04E 052 060 065 071 076 07B 083 08B 08F 09D 0A3 0D1 0D2 0D3 0D4 12A 136 137 138 14B`) and were toured with `run-timed` (a shot every 60 frames).
- **Review:** 4 reviewers over 326 full-size 4×4 sheets (`python -I scripts/tour.py sheets FIRST LAST` → `work/tour/review/`), findings in `work/tour/issues_1..4.md`.
  - 0 text past a box edge, 0 Japanese glyphs or garbage tiles in English text, 0 pages blank where JP has text.
  - **Systemic: greedy word-wrap orphans.** A lone word on the last line, or an indented narration line spilling to the left margin. `…` is a 2-column glyph, so these lines really were too long; the engine wrapped them as `wrap.fit` laid them out.
    - **Fix:** `wrap.balance` (called by `fit`). A widow takes a word from the line above, and an indented line that spills loses its indent; the line count never grows.
    - The build prints the leftovers as `warning: … awkward wrap`: 695 before, 4 after balancing, all 4 reworded.
  - **Translation fixes:** `346 0014`, `36C 0006`, `375 0010`, `37F 0020`, `383 0000`, `391 0028`, `402 0000`, `43C-441 0002`. Jewel Shard messages `3CF-3D5 0002` now break before the item name.
- **Engine quirk, not compensated:** an indent after a full line shows one blank less than written (41B has 3 blanks, shows 2). A spare-blank fix in `wrap.fit` broke 76 scenes (blanks after a full line are drawn past the box edge, clobbering memory), so it was reverted. `test_indent_after_br_is_emitted_as_written` pins this.
- **Context artifacts (also on JP, not bugs):**
  - Garbage portrait/kanji boxes on the first page of many scenes.
  - Wrong portraits, and party-member lines as garbage tiles in about 30 sheets: a forced scene only has the stage-1 party, so op-13 slot lines can't be judged here. On EN this garbage runs a few rows further below the box, but it is the same uninitialized data.
  - "Level rose to 1!" for non-Yui members.
  - Sprites drawn over boxes.
