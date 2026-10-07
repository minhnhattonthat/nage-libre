# English rendering (2b)

## Boxes

`python -I scripts/boxcheck.py`: max Japanese lines per print op, at Japanese widths:

```
op 01 box Box(cols=22, lines=4): JP lines {1: 267, 2: 287, 3: 232, 4: 209}
op 0B box Box(cols=30, lines=4): JP lines {1: 39, 2: 90, 3: 92, 4: 53}
op 13 box Box(cols=22, lines=4): JP lines {0: 2, 1: 450, 2: 467, 3: 259, 4: 135, 5: 12}
op 26 box Box(cols=30, lines=3): JP lines {1: 91, 2: 69, 3: 54}
op 2B box Box(cols=30, lines=3): JP lines {1: 18, 2: 32, 3: 51}
op 3B box Box(cols=30, lines=3): JP lines {1: 5, 2: 2, 3: 12}
```

- `wrap.BOXES`:
  - ops `01`/`13`: portrait 22×4
  - op `0B`: 30×4
  - ops `26`/`2B`/`3B`: 30×3
- Op `13`'s 12 five-line cases (`scene_315 0008`, `scene_3B9 0000`, …) are narration-style strings (a 15-blank first line). Handler `838BE8` sets column 8 / limit `0x1E` unconditionally, so they already print through the portrait geometry in the original. English keeps the stricter 22×4.
- Entries printed by ops of different widths (8 entries) must fit one line of 22 columns. Unreferenced entries use 30×3.
