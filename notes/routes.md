# Routes

Run any route: `python -I scripts/mesen.py scripts/mesen/goto.lua ROUTE=H:/translation/nage-libre/scripts/mesen/routes/<route>.txt SAVE=<name> [FROM=<state>] [SHOT_EVERY=60]`
States land in `work/states/<name>.mss`, screenshots in `work/shots/<name>_*.png`.

| State | Route | From | Frames | Final screen |
|---|---|---|---|---|
| dialogue1 | `dialogue1.txt` | power-on | 1688 | Black, just before the opening narration box opens (NEW GAME chosen) |
| dialogue1_idle | `dialogue1_idle.txt` | dialogue1 | 400 | Box shows 「遠くの世界で……声が響く……」 fully printed, waiting |

Notes:
- Boot: Varie logo, attract intro (island map, characters, no text). START at ~900 skips to title.
- Title menu items (top to bottom): NEW GAME, SOUND, ?? (3rd item). A on NEW GAME starts narration on a black screen.
| title_menu | `title_menu.txt` | power-on | 1608 | Title menu, cursor on NEW GAME (before A) |
| stage1 | `stage1.txt` | dialogue1 | 4000 | Birthday confirmation screen 「これで誕生日はいいかな？」 |
| stage1b | `stage1.txt` | stage1 | 4000 | Black transition into first battle |
| battle1 | `wait150.txt` | stage1b | 150 | Battle: 霧島唯 vs 梨田静子, card row ATK/DEF/HP/CHG |
| map1 | `map1.txt` | stage1 | 2420 | Stage 1 map, boss dialogue 「問答無用‼行くわよ‼」 |
| map2 | `map2.txt` | stage1 | 3480 | Stage 1 map, free roam (TIME SPEED panel) |
| s1c | `stage1_clear.txt` (cheats `7E10CCFF,7E10D163,7E17790F,7E177A27`) | stage1b | 12000 | Several battles won; party at the school door (boss not yet present). Stage clear NOT reached (see notes/system-text.md) |
| — | `battle_a.txt` (cheats) | stage1b | 2400 | First battle(s) won in one hit; victory messages |
| g_open | `work/run_open.txt` (120 -, a, 40 -) | map2 | 164 | Stage 1 map, command menu open (graphics labels 待機…セーブ) |
| g_item2/4/5/6 | `work/run_itemK.txt` (down×K, a) | g_open | ~100 | ITEM window / WHO window / Anime ON-OFF / Save NO-YES |
