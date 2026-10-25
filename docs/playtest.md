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

## Debug screens (`python -X utf8 -I scripts/debug_screens.py [--rom R --tag T] [screen ...]`)

Cold boot → `dialogue1` → `stage1` → mash A until the unit-control loop `828BC0` runs (`until_pc.lua`, robust to text-speed changes), then one route per screen (`scripts/mesen/routes/dbg_*.txt`). Shots `work/shots/<tag>_<screen>_final.png`, sheet `<tag>_debug_sheet.png`. All 10 verified English on the final build; JP reference with `--rom "rom/…sfc" --tag jp`.

| Screen | How (map code) | Fake |
|---|---|---|
| status | Y (free look `828934`), cursor onto a unit, A (`8286CC`, gfx `0x274`) | — |
| stats | status, A again (`81BF6F`, tilemaps `0x275`/`0x276`) | — |
| terrain | Y, A on ground (`81D1F9`, gfx `0x295`) | variants: `FORCE=81D33A:a=1..5` (costume), `81D2CD:a=80/90` (heal / damage floor), `81D239:a=0` (blocked) |
| rest | X (`8288AD`) | `FORCE=828C2E:a=0`: Rest? needs 2+ awake members (`82E8F2`) |
| pager | command menu, Pager → WHO | — |
| trade | command menu, Trade → WHO → member (`81CF8F`, card types from `$027C`) | `FORCE=828263:a=1,82844D:a=1`, stock cards via `CHEATS` |
| menu / shop / club / save | `redirect.lua` 828000 → 87CA0F, mashing A until the jump | — |

- `FORCE` (goto.lua, until_pc.lua; `L.force`): "PC:reg=hex,…" sets a CPU register on every execution of PC (`pc` jumps within the bank).
- Battle message 275 ("Birthstone bonus!" on heal / DEF-up, `819A89 819AF3 819B5D 819BC7`): `until_pc.lua FROM=<tag>_ctl AT_PC=<routine>`, `FORCE=<bne>:pc=<next>` (birthstone check at routine + 0x0B) and, for DEF, `818DAD:pc=8DA6` / `818DCD:pc=8DC6` (HP card handler → DEF handler). All four verified (`b275_*`).
- Mesen's test runner stops at about 22000 frames (both ROMs); runs needing more must start from a later state.
- Fixes from this pass: status stat names left-aligned like JP (`labels.render(left=True)`, `"align": "left"`); terrain panel and Trade card types translated (docs/re/graphics.md).

## Forced-scene tour (all 333 scenes, EN build vs JP identity build)

- **Coverage:** 305 scenes have op-06 pages, 1614 pages on each ROM, with equal per-scene page counts. The other 28 are timed narration with no key waits (`032 033 036 03D 040 044 047 04E 052 060 065 071 076 07B 083 08B 08F 09D 0A3 0D1 0D2 0D3 0D4 12A 136 137 138 14B`) and were toured with `run-timed` (a shot every 60 frames).
- **Review:** 4 reviewers over 326 full-size 4×4 sheets (`python -I scripts/tour.py sheets FIRST LAST` → `work/tour/review/`), findings in `work/tour/issues_1..4.md`.
  - 0 text past a box edge, 0 Japanese glyphs or garbage tiles in English text, 0 pages blank where JP has text.
  - **Systemic: greedy word-wrap orphans.** A lone word on the last line, or an indented narration line spilling to the left margin. `…` is a 2-column glyph, so these lines really were too long; the engine wrapped them as `wrap.fit` laid them out.
    - **Fix:** `wrap.balance` (called by `fit`). A widow takes a word from the line above, and an indented line that spills loses its indent; the line count never grows.
    - The build prints the leftovers as `warning: … awkward wrap`: 695 before, 4 after balancing, all 4 reworded.
  - **Translation fixes:** `346 0014`, `36C 0006`, `375 0010`, `37F 0020`, `383 0000`, `391 0028`, `402 0000`, `43C-441 0002`. Jewel Shard messages `3CF-3D5 0002` now break before the item name.
- **Engine quirk, not compensated:** an indent after a full line shows one blank less than written (41B has 3 blanks, shows 2). A spare-blank fix in `wrap.fit` broke 76 scenes (blanks after a full line are drawn past the box edge, clobbering memory), so it was reverted. `test_indent_after_br_is_emitted_as_written` pins this.
- **Timed cutscenes (28 scenes, reviewed separately):** each page clears on a timer that runs while it types. English has about 2× the glyphs, so long lines vanished mid-typing (`341 0018` "…are gonna get wre").
  - **Fix:** halve the per-glyph waits in both typing printers: `80F5B0` (2nd frame wait at `80F5F4` NOPed) and the talking-portrait printer `80F52F` (`lda #6` at `80F581` → 3). English now types at Japanese speed per screen width, and dialogue types twice as fast.
  - **Checked:** text-pixel tracing at a 4-frame interval with no input (scenes 341, 345, 385; ad-hoc pixel counter: per page typed frames and hold frames).
    - Before the fix, EN pages typed about 200 frames and held about 12.
    - After the fix, EN typed about 100 and held about 120, like JP.
    - The remaining short holds (0-40 frames) occur on JP too: that is the original rapid-exchange pacing.
  - **Text fixes:** `439 0036` (break before "Stage 1♥"), `34F 0006`. `39A 0024` is a stage-direction string in the original data and is never displayed.
- **Context artifacts (also on JP, not bugs):**
  - Garbage portrait/kanji boxes on the first page of many scenes.
  - Wrong portraits, and party-member lines as garbage tiles in about 30 sheets: a forced scene only has the stage-1 party, so op-13 slot lines can't be judged here. On EN this garbage runs a few rows further below the box, but it is the same uninitialized data.
  - "Level rose to 1!" for non-Yui members.
  - Sprites drawn over boxes.

## Timed cutscenes: print check (final build)

`run-timed` now logs every typing-printer start/end (`PRINTLOG`). The keep-alive A press waits until typing ends, like a player reading before pressing; A held would fast-forward typing.
- `python -I scripts/tour.py printcheck en|jp <scenes>` lists pages cut off mid-typing, and pages up less than 30 frames before the next page starts.
- **Result, 28 scenes:**
  - EN and JP have the same page counts.
  - No page is cut off mid-typing. The only `CUT` is the last page of 385 on both ROMs, at the run's time limit.
  - Pages up for 12-27 frames occur at the same places on JP (continuation pages).

## Review items and disposition

| Item | Disposition |
|---|---|
| 341 0018 / 385 0034 / 345 0018 cleared mid-typing | Fixed: typing waits halved (`SECOND_WAIT`, `PORTRAIT_FRAMES`); print check clean |
| Pages "clearing early" after the fix (345 0024-0030, 385 0008, 341 0047, 34C 0006) | 60-frame sampling plus keep-alive presses; print check shows every page typed to the end |
| 385 0030 "…Meat at last!" never complete | Seen complete in a 4-frame trace (held 20 frames; JP holds its version 0) |
| 385 0062-0068 not seen | After the tour's time limit on both ROMs; checked statically (fit + coverage) |
| 341 0022 / 0032: one frame with missing letters | Transient: glyph tiles land a frame after placement; the next frame is correct |
| 345 0026 / 0032 / 0036 never seen fully typed | Print check: typed to the end (the JP shots are partial at the same moments) |
| 39A 0024 stage-direction text | In the original data, never displayed |
| 447 0010 SCENARIO credit | Not shown on JP either (unused) |
| 439 0036, 34F 0006 | Reworded |
