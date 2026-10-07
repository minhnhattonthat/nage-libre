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
| 部活 / 〜部のシンボル | club / X Club emblem (バスケ部 Basketball Club, 空手部 Karate Club) | |
| 着がえカード | costume card | |
| 腕力 / 防御力 / 素早さ / 精神力 / 体力 | Strength / Defense / Speed / Spirit / HP (matches the battle HUD) | |
| 心に闇を持つ者 | those with darkness in their hearts / dark hearts | |
| ＳＯＲＲＹ…… ＧＡＭＥ ＯＶＥＲ ……ＰＵＳＨ ＲＥＳＥＴ…… | SORRY…… GAME OVER ……PUSH RESET…… (kept in English, 4-line layout) | |
| ステージＮ・クリア‼ | Stage N Clear! | |
| 喜久子 / 姫神一族 / 姫神の森 | Kikuko / the Himegami clan / Himegami Forest | |
| りか / 紗羅 / アリア | Rika / Sara / Aria (stage 10/11/12-13 bosses) | |
| 典子 / 美由紀 / 智恵子 | Noriko / Miyuki / Chieko (stage 9 rooftop girls) | |
| 赤のジュエル / 緑のジュエル | Red Jewel / Green Jewel | |
| 反重力ゾーン | anti-gravity zone | |
| 体育館 / プール | Gym / Pool | |
| バスケ部部隊６人衆 | Basketball Squad Six | |
| ベルベット・ボイス | Velvet Voice | |
| 現実世界 | the real world | |
| 美夕 / 紗夜子 / 京子 | Miyu / Sayoko / Kyoko (stage 14/15/16 bosses) | |
| 創造神 | creator god | |
| 結界 | barrier | |
| 水の神殿 | Water Temple | |
| ＬＩＳＴＥＮ ＴＯ ＴＨＥ ＲＡＩＮＤＯＲＯＰＳ | LISTEN TO THE RAINDROPS (password; kept in English) | |
| 図書館 | library | |
| まみ / サティ / 弓子 / ミスティ | Mami / Saty / Yumiko / Misty (stage 18-19 / 20 / 21 / 22) | Misti |
| 雪迷宮 / 雪女 | Snow Labyrinth / snow woman | |
| クリスタルパレス | Crystal Palace | |
| 光の壁 | wall of light | |
| 回復剤 | Restorative | |
| あの方 / あの人 (Misty) | that person / that woman | |
| エコエコアザラク プリリンパ | Eko Eko Azarak, Pirilimpa (Mami's spell) | |
| ステージ２２・再スタート / 再々スタート | Stage 22 Restart / Re-Restart | |
| ■ (debug/unused text) | `<$FC03>` (■ is not in en.tbl) | |

## Compromises

(entries where box size forced a loss of meaning: `file index`: what was lost)

## Needs user check

(uncertain readings or interpretations: `file index`: question)

- `scene_35B 0000`, `scene_35D 0002`: 「…<$FA01>の神殿」. The glyph `<$FA01>` is code 0x01FA, unmapped in nage.tbl (between 殿 and 催). Rendered from the ROM font it shows a top stroke over a 2×2 field of crosses, possibly 爾 or 爽. English avoids naming it ("the temple underground" / "the temple"). Which kanji is it?
- `scene_361 0002`: `<$F602>` around ＮＡＧＥ is unresolved; assumed to be quote marks → `"NAGE"`.
- `scene_384 0015` (password entry screen): only the prompt is translated. The cursor row `○` and the full-width `Ａ…Ｚ` rows are kept byte-identical (raw codes) so the cursor still lines up with the letters. Playtest: does entering LISTEN TO THE RAINDROPS still work and display correctly?
