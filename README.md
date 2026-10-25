# Nage Libre: Seijaku no Suishin English translation

Unofficial English fan translation of **Nage Libre: Seijaku no Suishin** (Super Famicom, Varie, 1995): the source text
and tools that build the patch.

**Just want to play?** Download the BPS patch from the [latest release](../../releases/latest) and follow its README.
This repository holds no game data you can play; you need your own unheadered dump of the Japanese ROM
(1,572,864 bytes). The patched ROM is 2 MB LoROM.

**Found a bug?** [Report it](../../issues/new/choose): untranslated text, typos, overflow, crashes. Attaching a savestate
helps most.

## What is translated
- All story text: 2257 dialogue and narration entries in 333 scenes, plus the opening and the ending.
- System text: battle messages, names, clubs, birthstones, prompts and menus.
- Graphics labels: the map command menu, the WHO window, the status screen, the "Rest?" prompt, the terrain panel and
  the Trade window's card types.
- The staff credits stay in their original Japanese.

`guide.txt` has a short game guide and cheat codes.

## What's here

| Path | What it is |
|---|---|
| `script/` | Every text block: Japanese dump (`jp/`) and English scenes and system text (`en/`). Translation fixes go here. |
| `glossary.md` | Binding names, terms and style rules. |
| `scripts/` | Python build chain: dump, insertion, layout, font, graphics, tour/QA and release, with the unittest suite. |
| `tools/` | `check_rom.py` (dump check) and `clean.py`; emulator and assembler downloads (gitignored). |
| `font/`, `gfx/` | English fonts and graphics label edits. |
| `nage.tbl`, `en.tbl` | Text tables. |
| `docs/re/` | Reverse-engineering notes. |
| `docs/decisions.md`, `docs/status.md` | Rulings with their reasons; current progress and open bugs. |
| `docs/fonts.md` | Fonts used and their licences. |
| `AGENTS.md` | Instructions for coding agents (`CLAUDE.md` points to it). |

## Build your own patched ROM

Needs Python 3.12+, asar in `tools/asar/` and your own dump of the Japanese game.

```sh
git clone https://github.com/minhnhattonthat/nage-libre
cd nage-libre
# copy your dump to: rom/Nage Libre - Seijaku no Suishin (Japan).sfc
#   (1,572,864 bytes, SHA-1 25a013e43989870f4f3e59ff4e4c34bda7bc5c44; the build refuses any other dump, see rom.sha1)
python -X utf8 -I scripts/build.py                          # -> build/nage_en.sfc + .bps
python -X utf8 -I -m unittest discover -s scripts           # tests
```

## Support

If you enjoy this translation, you can support my work on Ko-fi:

[![Support me on Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/minhnhattonthat)

## Licence

Tools and English translation: MIT. The original Japanese text in `script/` is Varie's and is included only so the
translation can be checked against it. Nage Libre is (c) 1995 Varie; this project is not affiliated with them. Do not
share patched ROMs.

The translation was made with extensive AI assistance (Claude by Anthropic). Corrections are very welcome.
