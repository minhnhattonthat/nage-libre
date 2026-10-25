# English rendering (2b)

## Boxes

`python -I scripts/boxcheck.py`: max Japanese lines per print op, at Japanese widths:

```
op 01 box Box(cols=22, lines=4): JP lines {1: 267, 2: 287, 3: 232, 4: 209}
op 0B box Box(cols=30, lines=4): JP lines {1: 39, 2: 90, 3: 92, 4: 53}
op 13 box Box(cols=22, lines=4): JP lines {0: 2, 1: 450, 2: 467, 3: 259, 4: 135, 5: 12}
op 26 box Box(cols=30, lines=3): JP lines {1: 91, 2: 69, 3: 54}
op 2B box Box(cols=30, lines=3): JP lines {1: 18, 2: 32, 3: 51}
op 3B box Box(cols=30, lines=3): JP lines {1: 5, 2: 2, 3: 12}
```

- `wrap.BOXES`:
  - ops `01`/`13`: portrait 22×4
  - op `0B`: 30×4
  - ops `26`/`2B`/`3B`: 30×3
- Op `13`'s 12 five-line cases (`scene_315 0008`, `scene_3B9 0000`, …) are narration-style strings (a 15-blank first line). Handler `838BE8` sets column 8 / limit `0x1E` unconditionally, so they already print through the portrait geometry in the original. English keeps the stricter 22×4.
- Entries printed by ops of different widths (8 entries) must fit one line of 22 columns. Unreferenced entries use 30×3.

## Font

- `font/en_glyphs.txt`: 95 hand-drawn glyphs (6×13 art). `python -I scripts/fontgen.py --preview font/en_preview.png` renders the review sheet.
- In-game look: white strokes with the dark outline, matching the Japanese glyphs (screenshots below).

## Emulator acceptance (`python -I scripts/accept.py english`, fixtures in `scripts/fixtures/en_sample/`)

| Entry | Box | Screenshot | Result |
|---|---|---|---|
| `scene_341 0000` `<BR>In a distant world… a voice echoes…` | full 30×3 | `english_narration_next_00120.png` | word-wrapped at "voice / echoes…"; leading blank line sits above the visible area of the black-screen narration box (same as the Japanese convention) |
| `scene_341 0002` 3-line quote | full 30×3 | `english_narration_next_00390.png` | exactly 3 full lines, ends at the box edge |
| `scene_341 0004` `<BR>…  AM 6:12  …` | full 30×3 | `english_narration_next_00570.png` | correct; doubled spaces collapse to one (by design) |
| `scene_310 0012` four 22-char lines | portrait 22×4 | `english_settle240_final.png` (map1 + 240 idle frames, route `settle240`, part of `accept.py english`) | exactly fills the portrait box, nothing outside the frame |

Untranslated lines show hiragana as Latin letters (e.g. the boss's previous line in `english_map1_01050.png`). Expected until those lines are translated; kanji and katakana are unaffected.

## Identity acceptance after 2b

`accept.py identity` now compares the identity build against **clean ROM + the same font patches** (no block relocation): 4/4 MATCH. The font patch changes hiragana rendering, so comparing against the untouched clean ROM would differ wherever hiragana appears (3 of 4 routes).

## Notes for translators

- Write plain English per entry; newlines inside an entry count as spaces. `<BR>` forces a line break.
- Black-screen narration (`scene_341`-style) keeps a leading `<BR>` like the Japanese blank first line.
- Literal `<`/`>` can't be used. `… ♥ ♪ ‼` are available as full-width symbols (2 columns each).
- The build fails with file, entry, box and line count when text doesn't fit.

## Review fixes (2b final review)

- **Hidden / spacer first line:** 93 entries' Japanese starts with a full blank line (84 in op-`0B` 30×4 boxes, 9 in 30×3). On the black-screen narration that line sits above the visible area. The build now fails unless the English for such an entry starts with `<BR>`, so the layout is kept and a line can't silently disappear.
- **30×4 box (op `0B`):** not yet confirmed in the emulator. Its entries (e.g. `scene_310 0014`/`0016`, the stage-start banner and victory condition) don't display on the current routes. The capacity rests on the Japanese: 52 op-`0B` entries without a leading blank line use all 4 lines. Confirm on the first playtest that reaches a stage-start banner.
- **Padding** uses the full-width blank `03FE` (2 columns per glyph) plus at most one space. That halves padding bytes, which matters for the 0x1340 WRAM window, and padding glyphs don't blip.
- **Fit errors** report the columns over and why a box applies (e.g. the 22×1 rule for entries printed by both 22- and 30-column boxes). Trailing spaces after `<END>` are allowed.
