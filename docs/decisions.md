# Decisions

The user's rulings on scope, style and trade-offs, newest last. Read before asking the user anything; if a later
decision replaces one, mark the old one "replaced by D<n>" instead of deleting it. Binding term spellings live in
`glossary.md`; this file holds the why.

| # | Date | Question | Options offered | Decision and reason |
|---|---|---|---|---|
| D1 | 2026-10-08 | Specs and plans | need approval, pre-approved | Pre-approved: write them, execute, merge to main, continue to the next sub-project. The user wants progress without gate-by-gate check-ins. |
| D2 | 2026-10-08 | Honorifics and name order | keep (-san), drop; JP or Western order | Dropped; Western order, Hepburn without macrons. |
| D3 | 2026-10-08 | Credits (scene_447) | stay Japanese, translate | Stay kanji: several glyphs are unmapped, and guessing real people's names is worse than leaving them. Kana nicknames romanized. |
| D4 | 2026-10-08 | Playtest | user plays, Claude scripts it | Claude scripts the playtest (tour, printcheck, debug warps); the user does not play. |
| D5 | 2026-10-08 | Abbreviations / overflow | engine work first, abbreviate | Full names and terms; English must fit the boxes with no extra paging (build enforces). |
| D6 | 2026-10-19 | Names in battle | given names only, full names | Battle HUD shows full names in a narrow proportional font (scripts/namevwf.py); messages use given names only (shared 10-column name buffer). |
| D7 | 2026-10-15 | Graphics text left in Japanese | none, list | None: every deferred label resolved (docs/re/graphics.md). |
