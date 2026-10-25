# Nage Libre (SNES, Varie 1995) English translation

Skill: translate-retro-game (Claude Code: plugin, enabled in .claude/settings.json; other agents: `<SKILL_DIR>/SKILL.md`; `$SKILL` = the directory holding its SKILL.md, default `~/.claude/plugins/marketplaces/retro-translation/skills/translate-retro-game`). Read it before ROM, text or QA work.

## Commands (repo root; `-I` ignores PYTHONUTF8, so always pass `-X utf8`)
- Build:  `python -X utf8 -I scripts/build.py` -> build/nage_en.sfc + .bps (checks the dump against `rom.sha1` first; fails on box overflow; prints `awkward wrap` warnings)
- Check:  `python -X utf8 -I -m unittest discover -s scripts` (212 tests, ~25 s; the pre-commit hook runs this)
- Smoke:  `python -X utf8 $SKILL/scripts/emu.py build/nage_en.sfc --out work/qa/smoke --frames 900 --smoke`
- Accept: `python -X utf8 -I scripts/accept.py identity|growth|english` (identity: clean vs identity-build screens must match)
- Tour:   `python -X utf8 -I scripts/tour.py ref` (JP ref -> work/tour/jp.sfc) | `run TAG ROM FIRST LAST` (hex scene idx 00-14C = scene_30F-45B) | `run-timed TAG ROM 032,033,..` | `strips FIRST LAST` (index.txt en=/jp= page counts) | `sheets FIRST LAST` -> work/tour/review/
- Printcheck: `python -X utf8 -I scripts/tour.py printcheck en|jp <timed list>` (after run-timed; CUT = cut mid-typing, <30 f = short)
- Mesen:  `python -X utf8 -I scripts/mesen.py scripts/mesen/goto.lua ROUTE=scripts/mesen/routes/X.txt SAVE=name [FROM=state] [ROM=build/nage_en.sfc]` -> work/{shots,states,trace}
- Debug:  `python -X utf8 -I scripts/debug_screens.py [--rom R --tag T] [status stats terrain rest pager trade menu shop club save]` -> work/shots/<tag>_debug_sheet.png (cold boot; FORCE=PC:reg=hex in goto/until_pc fakes conditions)
- Review page: `python -X utf8 -I scripts/review.py` -> build/review.html
- Release: `python -X utf8 -I scripts/release.py --version X.Y` -> release/ (local, gitignored; never publish without the user)
- Clean:  `python -X utf8 tools/clean.py` (published projects: lists rebuildable/downloadable files; `--yes` deletes)

## QA order (after text/engine changes; cold boot, savestates carry old code/VRAM)
1. Tour page counts: `run` en + jp, `strips`; per-scene EN page count must equal JP. 28 timed scenes (list in docs/playtest.md) via `run-timed`.
2. `printcheck` en + jp on the timed scenes: no CUT pages, short pages only where JP has them.
3. Visual review only of flagged scenes (`sheets`). Garbage portraits/op-13 slot tiles also on JP = forced-scene artifacts, not bugs.

## Paths
- Original ROM: `rom/Nage Libre - Seijaku no Suishin (Japan).sfc` (gitignored; SHA-1 in `rom.sha1`, checked by `tools/check_rom.py`). Emulator: this repo's own copy in `tools/mesen2/Mesen.exe` (gitignored); asar: `tools/asar/`. Runs/shots/states/traces: work/.
- Text: script/jp/ (dump), script/en/ (scene_30F..45B.txt + system.txt). Tables: nage.tbl (JP), en.tbl. Font: font/. Graphics label edits: gfx/edits.json. Code and tests: scripts/.
- Lua: scripts/mesen/ (lib.lua, goto.lua, scene_hook.lua, redirect.lua, routes/). Specs/plans: docs/superpowers/. Release README template: docs/README.release.txt.
- Glossary: `glossary.md` (names, style, rulings; authoritative). docs/: characters.md (voices) | speakers.json (speaker ids) | translation.md | routes.md | playtest.md (tour, printcheck, deeper screens). Fonts and their licences: `docs/fonts.md`.
- RE notes index: `docs/re/README.md`: text-engine.md (font, opcodes, encoding) | text-inventory.md | insertion.md (2a pipeline) | english.md (8x16 font, wrap) | system-text.md (bank $87 -> $BF8000) | wram.md (scene buffer) | graphics.md (labels, deferred list)

## Quirks
- Mesen callbacks give CPU addresses: convert with `L.rom_off(a)` (scripts/mesen/lib.lua) before comparing to file offsets.
- Font glyph tiles are column-major (TL, BL, TR, BR); font offset = 0x28000 + code*0x20.
- `…` is 2 columns; indent = `<$FE03>`. Indent after a full line shows one blank less: engine quirk, pinned by test; a wrap.fit fix broke 76 scenes, don't retry.
- nage.tbl mislabels B401=科 (not 料), 8204=大 (not 太).

## Rulings
- Edit source files (.py .lua .asm .tbl .json) only with the file-edit tool; scripts here read and analyse, never `.replace()` and write back.
- The user's decisions, with the options and reasons: `docs/decisions.md`. Read it before asking the user anything; add each new ruling there the same session.
- Player bug reports: GitHub issues (`gh issue list --label bug`). Copy the attached save into `work/states/`, reproduce in the emulator, fix, commit with `Fixes #N`, and update `docs/status.md`.
- Staff credits (scene_447) stay kanji. Names: Western order, Hepburn without macrons, honorifics dropped; battle HUD shows full names in a narrow font (scripts/namevwf.py), messages given names only.
- Full names, no abbreviations. English must fit boxes, no extra paging (build enforces).
- Specs/plans pre-approved: write them, execute, merge to master, continue. Claude scripts the playtest; the user does not play.

## Status
`docs/status.md`: done, next, open bugs. Update it at the end of every session.
