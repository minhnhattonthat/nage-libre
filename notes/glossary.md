# Glossary and style

Authoritative for every English entry. Speakers by id: `notes/speakers.json`. Voices: `notes/characters.md`.

## Style

- Natural, lively English. Localize meaning, keep jokes and each speaker's tone.
- Names: Western order (given name, then surname), Hepburn without macrons. Honorifics dropped.
- `‼` → `!` (or `!!` when shouting). `…` stays (2 columns). 「」 → `"`. Japanese blank padding dropped.
- Leading blank line in the Japanese → English starts with `<BR>` (build enforces).
- Op-13 placeholder slots (`…` only) → `…`.
- Stage banner: `Stage N Start`. Victory condition: `Goal: Defeat <name>`.
- Layout in 30×4 narration boxes (op 0B): consecutive prints share the box, so keep the Japanese line structure.
  - Indent with `<$FE03>` (full-width blank, 2 columns). A literal `　` or spaces collapse.
  - A trailing blank line is `<BR><BR>`. Verified in the emulator: `Stage 1 Start` / blank / `Goal: Defeat Tomomi!`.
- 💧 (sweat drop) is `<$D203>`. ♥ ♪ … are typed directly.
- Op-13 filler slots for absent members often hold the enemy's line or the chest narration, not `…`. Translate by content.

## Names and terms

| Japanese | English | Avoid |
|---|---|---|
| 霧島唯 / 唯 | Yui Kirishima / Yui | Yuki |
| 桜井彩香 / 彩香 | Ayaka Sakurai / Ayaka | Ayka |
| 姫ノ木舞 / 舞 | Mai Himenogi / Mai | |
| 美姫 | Miki (surname per guide: Shizumoto; not seen in script yet) | |
| 嶺子 | Ryoko (surname per guide: Aoi; not seen in script yet) | Ryouko |
| 愛 | Ai | |
| ナージュ | Nage | Naju |
| ニンフ | nymph | |
| 部活 | club | |
| 宝玉 | jewel | |
| 誕生石 | birthstone | |
| ATK DEF HP ESC SP CHG COS カード | ATK / DEF / HP / ESC / SP / CHG / COS card | |
| 「リ」「ベ」「ラ」「シ」「オ」「ン」の宝玉 | "LI" / "BE" / "RA" / "TI" / "O" / "N" Jewel (spells LIBERATION; JP リベラシオン) | Ri Jewel |
| ともみ | Tomomi (stage 1 boss) | |
| 弓香 | Yumika (stage 2 boss) | |
| 姫香 | Himeka (stage 3 boss) | |
| 霧香 | Kirika (stage 4 boss) | |
| 中和剤１／２ | Neutralizer 1 / 2 | |
| スーパーバリアー | Super Barrier | |
| 武道館 | martial arts hall | Budokan |
| 〜が仲間になった‼ | X joined the party! | |
| ステージＮ・クリア‼ | Stage N Clear! | |

## Compromises

(entries where box size forced a loss of meaning: `file index`: what was lost)

## Needs user check

(uncertain readings or interpretations: `file index`: question)
