# Nage Libre: Seijaku no Suishin English translation

Unofficial English fan translation of **Nage Libre: Seijaku no Suishin** (Super Famicom, Varie, 1995): the source text
and tools that build the patch.

**No game data is included.** Patches are published on the [Releases](../../releases) page when available; apply the
BPS to your own unheadered dump of the Japanese ROM (1,572,864 bytes). The release README lists the hashes and
patching steps. The patched ROM is 2 MB LoROM.

## What is translated
- All story text: 2257 dialogue and narration entries in 333 scenes, plus the opening and the ending.
- System text: battle messages, names, clubs, birthstones, prompts and menus.
- Graphics labels: the map command menu, the WHO window, the status screen, the "Rest?" prompt, the terrain panel and
  the Trade window's card types.
- The staff credits stay in their original Japanese.

`guide.txt` has a short game guide and cheat codes.

## Building from source
You need your own ROM under `rom/` (gitignored). See `CLAUDE.md` for the commands (`python -X utf8 -I scripts/build.py`,
the unittest suite, `scripts/release.py`) and `notes/` for the text engine, font and graphics research.

- `script/`: Japanese dump (`jp/`) and English scenes and system text (`en/`)
- `scripts/`: dump, insertion, layout, font, graphics, tour/QA and release tools (with tests)
- `font/`, `gfx/`: English font and graphics label edits
- `nage.tbl`, `en.tbl`: text tables
- `notes/glossary.md`: names, style and rulings

## Support

If you enjoy this translation, you can support my work on Ko-fi:

[![Support me on Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/minhnhattonthat)

Translation, tools and patch were produced with AI assistance (Claude, Anthropic) under the direction of the project
owner. Original game (c) 1995 Varie; this project is not affiliated with Varie. Do not share patched ROMs.
