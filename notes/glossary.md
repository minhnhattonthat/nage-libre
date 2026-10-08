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
| 静本美姫 / 美姫 | Miki Shizumoto / Miki (profile, scene_439) | |
| 葵嶺子 / 嶺子 | Ryoko Aoi / Ryoko (profile, scene_439) | Ryouko |
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
| ……。 (ellipsis + period) | …… (drop the period) | …. |
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
| 宝玉のかけら | Jewel Shard | |
| 素早さのモト / 体力アップのくすり / 回復のくすり | Speed Booster / HP Up Potion / Healing medicine | |
| 腕力のモト / 防御力のモト | Power Booster / Defense Booster | |
| 待機 | stand by (map command) | |
| ＨＰまんたん剤 | Full HP Potion | |
| 超必殺技カード / ストックカード | SP card / stock cards | |
| 演劇部 / 手芸部 / オカルト研 | Drama Club / Crafts Club / Occult Club | |
| 隠しコマンド (scene_42D) | birthdays Jan 23 / Apr 5 / Jun 7 / Aug 9 / Oct 11 (Ayaka / Mai / Yui / Miki / Ryoko) | |
| 料学部 (really 科学部: glyph B401 is 科, mislabelled 料 in nage.tbl) | Science Club | Cooking |
| ○○ (placeholder name) | XX | |
| ■ (debug/unused text) | `<$FC03>` (■ is not in en.tbl) | |

## System text (script/en/system.txt)

- Surnames 0-99 are empty (shared 10-column name buffer). Given names come from Japanese reading order: the pool is sorted by reading, which settles ambiguous readings.
  - 紅 is used as a variant of 江 (詩紅 Utae, 静紅 Shizue, 睦紅 Mutsue).
  - `<$9002>` reads Hiro- (Hiroko, Hiromi).
  - 美`<$E405>` = Mia.
- Battle pieces are joined in Japanese order:
  - name + `:` + number + ` damage!` / ` HP healed!` / ` DEF up!`
  - stat + number + `!` (`Strength +3!`)
  - `Level rose to ` + number + `!`
  - club + line break + `is now selectable!`
- Fixed-width strings are padded with `<$FE03>` to their Japanese width so shorter text overwrites longer: birthstones 14, shop lines 24.
- Yes/No (276 `Yes  No`, 293 `No  Yes`) keep their Japanese cursor columns.
- Trailing spaces before `<END>` are stripped by the parser; use `<$2000>` for a trailing half-width space.

## Compromises

(entries where box size forced a loss of meaning: `file index`: what was lost)

## Needs user check

(uncertain readings or interpretations: `file index`: question)

- `scene_35B 0000`, `scene_35D 0002`: 「…<$FA01>の神殿」. The glyph `<$FA01>` is code 0x01FA, unmapped in nage.tbl (between 殿 and 催). Rendered from the ROM font it shows a top stroke over a 2×2 field of crosses, possibly 爾 or 爽. English avoids naming it ("the temple underground" / "the temple"). Which kanji is it?
- `scene_361 0002`: `<$F602>` around ＮＡＧＥ is unresolved; assumed to be quote marks → `"NAGE"`.
- `scene_447` (staff credits): staff names are kept in their original kanji (raw codes, they render correctly) because several glyphs are unmapped (0x0460, 0x0448, 0x058A, 0x0440, 0x0444, 0x0446, 0x044C, 0x044E, 0x0576, 0x0452, 0x0454, 0x02B4, 0x0458, 0x0292) and guessing real people's names is worse than leaving them. Hiragana/katakana nicknames are romanized (Gaku, Shichi Michihiko, Chiyou, Yonewo, Ukkii, R. Rira). Credit-heading typos fixed (IVENT → EVENT, EXECTIVE → EXECUTIVE). Romanize the names?
- `system 0291` (面 after the stage number on the save screen) → ` stg` (`12 stg`); `0285`/`0286` (月/日) → `7/18`. Check the save and birthday screens in playtest.
- `scene_384 0015` (password entry screen): only the prompt is translated. The cursor row `○` and the full-width `Ａ…Ｚ` rows are kept byte-identical (raw codes) so the cursor still lines up with the letters. Playtest: does entering LISTEN TO THE RAINDROPS still work and display correctly?
