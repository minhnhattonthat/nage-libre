# Nage Libre (SNES, Varie 1995) English translation

Skill: translate-retro-game (H:/translation/nage-libre/.claude/skills/translate-retro-game/SKILL.md). Read it before ROM, text or QA work.

## Commands (repo root; `-I` ignores PYTHONUTF8, so always pass `-X utf8`)
- Build:  `python -X utf8 -I scripts/build.py` -> build/nage_en.sfc + .bps (fails on box overflow; prints `awkward wrap` warnings)
- Check:  `python -X utf8 -I -m unittest discover -s scripts` (206 tests, ~25 s; the pre-commit hook runs this)
- Smoke:  `python -X utf8 H:/translation/nage-libre/.claude/skills/translate-retro-game/scripts/emu.py build/nage_en.sfc --out work/qa/smoke --frames 900 --smoke`
- Accept: `python -X utf8 -I scripts/accept.py identity|growth|english` (identity: clean vs identity-build screens must match)
- Tour:   `python -X utf8 -I scripts/tour.py ref` (JP ref -> work/tour/jp.sfc) | `run TAG ROM FIRST LAST` (hex scene idx 00-14C = scene_30F-45B) | `run-timed TAG ROM 032,033,..` | `strips FIRST LAST` (index.txt en=/jp= page counts) | `sheets FIRST LAST` -> work/tour/review/
- Printcheck: `python -X utf8 -I scripts/tour.py printcheck en|jp <timed list>` (after run-timed; CUT = cut mid-typing, <30 f = short)
- Mesen:  `python -X utf8 -I scripts/mesen.py scripts/mesen/goto.lua ROUTE=scripts/mesen/routes/X.txt SAVE=name [FROM=state] [ROM=build/nage_en.sfc]` -> work/{shots,states,trace}
- Debug:  `python -X utf8 -I scripts/debug_screens.py [--rom R --tag T] [status stats terrain rest pager trade menu shop club save]` -> work/shots/<tag>_debug_sheet.png (cold boot; FORCE=PC:reg=hex in goto/until_pc fakes conditions)
- Review page: `python -X utf8 -I scripts/review.py` -> build/review.html
- Release: `python -X utf8 -I scripts/release.py --version 1.1` -> release/ (local, gitignored; never publish without the user)

## QA order (after text/engine changes; cold boot, savestates carry old code/VRAM)
1. Tour page counts: `run` en + jp, `strips`; per-scene EN page count must equal JP. 28 timed scenes (list in notes/playtest.md) via `run-timed`.
2. `printcheck` en + jp on the timed scenes: no CUT pages, short pages only where JP has them.
3. Visual review only of flagged scenes (`sheets`). Garbage portraits/op-13 slot tiles also on JP = forced-scene artifacts, not bugs.

## Paths
- ROM: `rom/Nage Libre - Seijaku no Suishin (Japan).sfc` (gitignored). Mesen2: tools/mesen2/Mesen.exe. Runs/shots/states/traces: work/.
- Text: script/jp/ (dump), script/en/ (scene_30F..45B.txt + system.txt). Tables: nage.tbl (JP), en.tbl. Font: font/. Graphics label edits: gfx/edits.json.
- Lua: scripts/mesen/ (lib.lua, goto.lua, scene_hook.lua, redirect.lua, routes/). Specs/plans: docs/superpowers/. Release README template: docs/README.release.txt.
- notes/: glossary.md (names, style, rulings; authoritative) | characters.md (voices) | speakers.json (speaker ids) | translation.md | text-engine.md (font, opcodes, encoding) | text-inventory.md | insertion.md (2a pipeline) | english.md (8x16 font, wrap) | system-text.md (bank $87 -> $BF8000) | wram.md (scene buffer) | graphics.md (labels, deferred list) | routes.md | playtest.md (tour, printcheck, deeper screens)

## Quirks
- Mesen callbacks give CPU addresses: convert with `L.rom_off(a)` (scripts/mesen/lib.lua) before comparing to file offsets.
- Font glyph tiles are column-major (TL, BL, TR, BR); font offset = 0x28000 + code*0x20.
- `…` is 2 columns; indent = `<$FE03>`. Indent after a full line shows one blank less: engine quirk, pinned by test; a wrap.fit fix broke 76 scenes, don't retry.
- nage.tbl mislabels B401=科 (not 料), 8204=大 (not 太).

## Rulings
- Staff credits (scene_447) stay kanji. Names: Western order, Hepburn without macrons, honorifics dropped; surnames empty (shared name buffer).
- Full names, no abbreviations. English must fit boxes, no extra paging (build enforces).
- Specs/plans pre-approved: write them, execute, merge to master, continue. Claude scripts the playtest; the user does not play.

## Status
- Done: SP1-5 (dump, insertion, English rendering, system text, translation 2572/2572, graphics, 333-scene tour, v1.1 BPS in release/). Public repo: github.com/nathantonsoniq/nage-libre (master); the BPS release itself is not published.
- Debug pass: every hard-to-reach screen reached and English (notes/playtest.md, Debug screens); release/ v1.1 includes it.
- Open: indent quirk (README known issues).
