# Text inventory

Encoding everywhere: 16-bit glyph codes (`nage.tbl`), `FFFF`-terminated (see `docs/re/text-engine.md`).

| Category | Screen | Storage | ROM location | Size | Notes |
|---|---|---|---|---|---|
| Dialogue, narration, event text | cutscenes, map talk (portrait box), stage intros | **script**, compressed scene blocks | resource table `0x50000`, resources `0x30F-0x45B` (banks `$A5`+) → `script/jp/scene_XXX.txt` | 333 blocks, 5537 entries (2646 non-empty) | ~354 entries are data tables, not text |
| Victory conditions (勝利条件：…) | stage start | script, scene blocks | same | — | inside scene files |
| Staff credits | ending | script, scene block | `scene_447` | — | several staff names use unresolved glyphs |
| Enemy name pools (surnames, given names) | battle (e.g. 梨田静子) | **script**, raw list | `0x38077-0x385C6` (`$878077`) → `script/jp/system.txt` | ~150 + ~110 names | enemy names are composed surname + given name |
| Boss / special names (ナージュ アリア サティ ツキヨミ ミスティ シャドウ) | battle, map | script, raw list | `0x385C7-0x385FE` | 6 | |
| Club names (バスケ部 … 一般生徒 ボス) | club select, status | script, raw list | `0x385FF-0x38696` | 17 | |
| Battle messages (の攻撃‼ のダメージ‼ 逃げろぉ‼ …) | battle | script, raw list | `0x386DF-0x3886B` | ~25 | assembled with names, e.g. `<name>の攻撃‼` |
| Yes/No, level-up, super move | various | script, raw list | `0x38879-0x388A6` | | |
| Save/load/shop/birthday prompts | file, shop, birthday screens | script, raw list | `0x388A7-0x389EB` | ~15 | |
| Birthstone names (JP) | birthday / status | script, raw list | `0x389F1-0x38AAF` | 12 | fixed width, padded with blanks |
| After-stage menu (どうしますか？ 買い物 部活選択 セーブ スタート ＥＸ) | between stages | script, raw list | `0x38AB1-0x38AEA` | 6 | |
| Jewel names (「リ」の宝玉 …) | items | script, raw list | `0x38AEB-0x38B3E` | 6 | |
| Dates / numbers (7月18日, HP 40/40) | birthday, battle | composed at runtime from font glyphs (digits, 月, 日) | code | — | not strings |
| Battle HUD: birthstone labels (SAPPHIRE…), HP, card faces (ATK DEF HP ESC SP CHG COS ???) | battle | **graphics** (8×8 English font tiles) | not located (sub-project 4) | — | already English |
| Map HUD (TIME SPEED, character romaji names YUI…) | map | **graphics**, English | not located | — | already English |
| Title screen (NAGE LIBRE logo, PUSH BUTTON, NEW GAME / SOUND / 3rd item), © VARIE 1995 | title | **graphics**, English | not located | — | already English |
| Map command menu (Stand by, Attack, Item, Exchange, Pocketbell, Anime, Save per guide) | map, unit turn | **graphics** (no matching text strings anywhere; 交 isn't even in the font) | not located | — | not reached by route (needs TIME gauge); verify in sub-project 4 |

Bank `$87` after `0x38B3F` holds tilemap rows (`FFFF`-terminated tile words), not text.
Only this one raw text block exists outside the scene resources: a full-ROM scan for runs of table codes ending in `FFFF` found nothing else, apart from noise in compressed data.
