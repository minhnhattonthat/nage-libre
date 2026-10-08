# Translation (sub-project 3)

## Coverage

`python -I scripts/coverage.py --check` → **2572/2572 entries translated, 0 missing, 0 avoided spellings**:
- 2257 scene entries across 333 files
- 315 system entries

Data, alias and symbol-only entries are excluded by design.

## Review

- `python -I scripts/review.py` writes `build/review.html`: every file as a table of index / speaker / box / Japanese / English. Untranslated rows are highlighted; there are none now.
- `python -I scripts/context.py scene_XXX` prints the translator worksheet (speaker, box, op).
- Speaker names: `notes/speakers.json`.
- Terms and style: `notes/glossary.md`.
- Voices: `notes/characters.md`.

## Emulator check (final `script/en` build, `accept.SYS_CHAIN`, prefix `full_`)

| Screen | Screenshot | Result |
|---|---|---|
| Opening narration | `full_stage1_00090.png` | "In a distant world…… a voice echoes……", 30×3 box |
| Morning monologues | `full_stage1_00660.png` (Ayaka, dojo), `full_stage1_03750.png` (Yui) | English, correct speakers, fits the box |
| Birthday entry | `full_settle60_final.png` | "Tell me your birthday", "7/18 Ruby", name "Ayaka" |
| Stage-1 map dialogue and banner | `full_map1_*`, `b1_banner_00200.png` | English; banner "Stage 1 Start" / blank line / "Goal: Defeat Tomomi!" |
| First battle | `full_battle_a_00900.png`, `full_battle_a_01020.png` | "Yui's attack! / Shizuko: 25353 damage!", "Shizuko was defeated! / 120 gold obtained!", HUD names Yui / Shizuko |

No hiragana-as-Latin appeared on any of these screens. The title menu (NEW GAME / SOUND) is graphics, which belong to sub-project 4.

## Open items for the user and for playtest

These are under "Needs user check" in `notes/glossary.md`:
- **Unresolved glyph `0x01FA`:** 「…の神殿」 (the temple name).
- **Staff credits:** names are kept in the original kanji. Should they be romanized?
- **Password entry screen:** the layout is kept; check that it works.
- **Save screen:** 「面」 is rendered as ` stg`; check how it looks.
- **Date format:** 「月/日」 is rendered as `7/18`.
- **Menus not reached by the routes:** shop, club select, after-stage menu, 30×4 stage banners beyond stage 1. Check them in the sub-project 5 playtest.
