# Nage Libre EN — Sub-project 3: Translation

Date: 2026-10-08
Status: approved (standing approval: "approved for all spec and implementation plan")

## Context

Overall goal: a full public-release English patch. Claude translates and the user reviews.

Done so far:
- 1: dump
- 2a: rebuild pipeline
- 2b: English font and box fitting (`wrap.fit`; the build fails on overflow)
- 2c: system text relocated to `$BF8000`, with width checks

This sub-project writes the English: `script/en/scene_XXX.txt` (333 files) and `script/en/system.txt`.

Until an entry is translated, its Japanese still prints, and since 2b the hiragana in it show as Latin letters. So a release needs **every** text entry translated.

### Facts this design relies on (probes, 2026-10-08)

- **Size:** 2278 non-empty, non-data scene entries, about 67k characters including padding blanks. Plus 319 system entries.
  - Data entries (`len=… data` in the header) must stay byte-identical; the build already enforces this.
- **No speaker labels in the text.** The bytecode shows who is speaking:
  - op `08 <id>` and op `02 <id> <expr>` set the portrait shown before each print op (`01`/`0B`/`13`/`26`/`2B`/`3B`).
  - Ids 1-6 are the main cast. They match the given-name table, entry `99 + id`:
    1 彩香 Ayaka, 2 舞 Mai, 3 唯 Yui, 4 美姫 Miki, 5 嶺子 Ryoko, 6 愛 Ai.
  - Ids ≥ 100 are per-stage characters (`stage × 100 + n`, e.g. `0x69` = stage 1 boss Tomomi). They have no name table, so names come from context and the guide.
- **Op `13`** holds 5 per-member variants. Slot k is spoken by character id k+1: slot 2 = Yui, slot 4 = Ryoko, who has a polite ojou-sama voice (「…ありますわ」).
  - Members not yet in the party have a `…` placeholder in their slot. It still needs English (`…`).
- **Boxes:** the build already knows the box size of every entry (`wrap.BOXES`, 22×4 portrait / 30×4 / 30×3 / 22×1).
  - Japanese pads lines with full-width blanks to lay them out. English is written as plain text, and `wrap.fit` wraps it.
- **Leading blank line:** 93 entries start with a blank line that has to be kept. Their English must start with `<BR>`, and the build enforces this.
- **System names:** surnames empty, given names only, because surname and given name share one 10-column buffer (2c ruling). Battle lines are checked whole.
- **Guide romanizations are unreliable.** It gives "Yuki" for 唯 and "Ayka" for 彩香. The script is authoritative.

## Goal and success criteria

1. Every non-data text entry in all 333 scene files and all 319 system entries has English. `scripts/coverage.py --check` reports 0 untranslated.
2. `python -I scripts/build.py --en script/en` succeeds: every entry fits its box, and system widths, names and battle lines pass.
3. The translation is consistent: names, terms and character voices follow `notes/glossary.md` and `notes/characters.md`. The glossary table has an **Avoid** column of wrong spellings (e.g. "Yuki", "Ayka", "Ryouko"), and `coverage.py --check` also fails if any avoided spelling appears in `script/en`.
4. The user can review the whole translation side by side (JP | EN | speaker | box) from one generated page, `build/review.html`.
5. On the existing emulator routes (opening narration, stage 1 dialogue, birthday screen, first battle), the English renders and nothing shows as hiragana-as-Latin.

## Components

| File | Responsibility | Interface |
|---|---|---|
| `scripts/context.py` | Per-entry context from the bytecode | `context(rom, name) -> dict[index, Ctx]`; `Ctx(speaker_id, box, op, slot)`; CLI `context.py scene_310 [...]` prints a worksheet (index, speaker name, box, JP with padding blanks collapsed) |
| `notes/speakers.json` | Speaker id → English name. Ids 1-6 are fixed; ids ≥ 100 are filled in while translating, from context | `{"0x03": "Yui", "0x69": "Tomomi", …}` |
| `scripts/coverage.py` | Translated vs total non-data entries, per file and overall; glossary avoid-list check | `missing(jp_dir, en_dir) -> list[(file, index)]`; `avoided(en_dir, glossary) -> list[(file, index, word)]`; CLI prints a summary; `--check` exits 1 listing missing entries and avoided spellings |
| `scripts/review.py` | Side-by-side review page | writes `build/review.html` (gitignored): per file, rows of index / speaker / box / JP / EN, untranslated rows highlighted |
| `notes/glossary.md` | Names (Western order, given name first), places, game terms (cards, clubs, jewels, stages), punctuation rules | prose + table |
| `notes/characters.md` | Voice notes for each main character and recurring boss, written from the script | prose |
| `script/en/scene_XXX.txt`, `script/en/system.txt` | The translation | existing dump format, header lines copied from `script/jp` |

## Translation style (rulings, recorded in `notes/glossary.md`)

- **Natural, lively English** for a 1995 SNES high-school-girls fantasy. Localize meaning, not word order. Keep the jokes and the tone of each speaker.
- **Names:** Western order, Hepburn without macrons (Ryoko, Kyoko).
  - Drop honorifics. Keep "senpai" only where the relationship matters; decide once in the glossary.
  - Full names in dialogue are given name + surname (霧島唯 → "Yui Kirishima").
- **Punctuation:**
  - ‼ → "!" (or "!!" for shouting).
  - `…` stays as the full-width ellipsis glyph (2 columns).
  - Japanese quotes 「」 become "…".
  - Full-width blank padding is dropped.
- **Game terms** match the graphics already in English: ATK / DEF / HP / ESC / SP / CHG / COS cards, birthstone names (SAPPHIRE …).
- **Stage banners:** 「ステージ１・スタート」→ "Stage 1 Start". 「勝利条件：ともみを倒せ」→ "Goal: Defeat Tomomi".
- **Placeholder slots** (`…` only): "…".
- **Staff credits (`scene_447`):** romanize the names. Any reading that is uncertain (or unresolved glyph) is listed in `notes/glossary.md` under "Needs user check" and gets a best guess.
- **Fit:** if a line doesn't fit, rewrite it shorter. Never cut meaning silently. If meaning has to be lost, record it under "Compromises" in `notes/glossary.md`.

## Workflow and batches

1. **Tooling first:** context, coverage, review, the speakers map, and the glossary and characters skeletons.
2. **Batches** of scene files in resource order (≈ game order), ~250 entries each.
3. **For each batch:**
   - read the worksheet
   - write `script/en` files
   - build until it fits
   - update the speakers map, glossary and character notes
   - commit; coverage goes up
4. **`system.txt` in full:**
   - surnames `<END>`, given names romanized
   - boss and club names
   - battle and menu text within the 2c width rules
5. **Final consistency pass:**
   - glossary check (one spelling per name)
   - coverage 0 missing
   - review page
   - emulator `accept.py english` and `system` on the full translation, with screenshots

The user reviews from `build/review.html` whenever they like. Their corrections come back as normal edits; nothing in this sub-project waits on review.

## Error handling

- **Fit, `<BR>`, data-entry and width failures:** reported by the existing build with the file and entry.
- **`coverage.py --check`:** lists missing entries as `file index`.
- **`context.py`:** an unknown speaker id shows as `id 0x069 (?)`. That is not an error; the speakers map fills it in.

## Testing

- **`context.py`:**
  - `scene_310` entry 0006 → speaker `0x69`, box 22×4
  - entry 0012 → speaker `0x69`
  - an op-13 entry gets a slot and the speaker `slot + 1`
- **`coverage.py`:** counts on a temp `en` dir (one translated entry, data entries excluded); `--check` exits 1 listing the missing entries; an avoided spelling (whole word, case-sensitive) in an English entry is reported.
- **`review.py`:** the page contains the JP text, the EN text, and the "untranslated" highlight for a missing entry.
- **Translation batches:** verified by the build passing (`test_build` already covers fit enforcement) and by coverage rising. The final task requires `coverage.py --check` to pass and the emulator routes to run.

## Out of scope

- **Graphics text** (title, HUD, map command menu): sub-project 4.
- **Full playtest and release BPS:** sub-project 5. That includes the 30×4 box confirmation and the unreached menus.
