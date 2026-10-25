# Fonts

Every font or glyph sheet the build reads ends up inside the released patch, so its licence must allow that. One row
per file; a font with no known licence doesn't go into a release.

| File | Source (URL, version) | Licence | Redistributable in a patch | Used for | Changes made |
|---|---|---|---|---|---|
| font/en_glyphs.txt | drawn for this project | MIT, same as repo | yes | dialogue and system text (6x13, outlined by scripts/fontgen.py) | - |
| font/name_glyphs.txt | drawn for this project | MIT, same as repo | yes | battle HUD full names (scripts/namevwf.py) | - |
| font/glyphs.txt, font/jp_font_*.png | transcription of the game's own font | Varie's; not shipped | no (read only to build nage.tbl) | JP table | - |
