# Translation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** English for every text entry of the 333 scene files and `system.txt`, fitting its box, consistent in names, terms and voices, reviewable side by side.

**Architecture:**
- Three small stdlib tools:
  - `context.py`: per-entry speaker, box and slot from the scene bytecode, plus a worksheet CLI
  - `coverage.py`: missing entries and glossary avoid-list violations; the gate
  - `review.py`: `build/review.html`
- Notes that carry consistency across batches: `notes/glossary.md`, `notes/characters.md`, `notes/speakers.json`.
- Nine translation batches (~250 entries each, resource order), then `system.txt`, then a final pass. The existing build enforces fit.

**Tech Stack:** Python 3.12 stdlib (`python -I`), unittest, existing `scripts/` modules (`dump`, `bytecode`, `wrap`, `rom`, `build`), Mesen2 via `scripts/accept.py`.

**Spec:** `docs/superpowers/specs/2026-10-08-translation-design.md`

## Global Constraints

- Python stdlib only; run everything with `python -I`; tests with `python -I -m unittest discover -s scripts`.
- Write Python and text containing `\x..`, `\n` or non-ASCII through the Write/Edit tools, never bash heredocs.
- Data entries (`len=… data`) are never written to `script/en`. If one is ever copied there, it must be byte-identical; the build enforces this.
- English entry format is the dump format. The header line is copied from `script/jp` (`## scene_310 0006 @0000DA len=22`); the body is plain English ending in `<END>`. Newlines inside a body count as spaces, and `<BR>` forces a line break.
- An entry whose Japanese starts with a blank line gets English starting with `<BR>`; the build enforces this.
- Names: Western order, Hepburn without macrons, honorifics dropped. Main cast: Ayaka (彩香, id 1), Mai (舞, 2), Yui (唯, 3), Miki (美姫, 4), Ryoko (嶺子, 5), Ai (愛, 6).
- System names: surnames `<END>`, given names only (2c ruling). Battle lines must fit 28 columns whole.
- ‼ → `!` / `!!`. `…` stays (2 columns). 「」 → `"`. Japanese blank padding is dropped.
- Card and HUD terms match the existing English graphics: ATK DEF HP ESC SP CHG COS, birthstones in English (Sapphire, Ruby …).
- Any translation compromise forced by box size → `notes/glossary.md` "Compromises". Any uncertain reading → "Needs user check".

## Review Focus

1. **Op-13 per-member strings** must be attributed to the right character (slot k → id k+1); a wrong mapping gives every party line the wrong voice. Test: `test_op13_slot_speaker` (Task 1).
2. **Alias, data, and blank/`…`-only entries** must not count as untranslated, and an entry "translated" by pasting Japanese must still count as missing. Tests: `test_excludes_data_alias_and_symbol_only`, `test_japanese_left_in_english_counts_missing` (Task 2).
3. **Avoid-list matching** must be whole-word and case-sensitive: "Yuki" must not match "Yukiko", or valid names get flagged. Test: `test_avoided_whole_word` (Task 2).
4. **Review page escaping:** `<BR>` / `<END>` tags and quotes must show as text, not be eaten as HTML. Test: `test_review_escapes_tags` (Task 3).
5. **Speaker carried across a print op:** an entry printed right after op `0A` (no portrait op) keeps the previous speaker; an unknown id shows `id 0x069 (?)`, not a crash. Test: `test_unknown_speaker_label` (Task 1).

---

### Task 1: Context tool and speakers map

**Files:**
- Create: `scripts/context.py`, `notes/speakers.json`
- Test: `scripts/test_context.py`

**Interfaces:**
- Consumes: `dump.source(data, name, map)`, `dump.parse_block(text)`, `dump.read_text(path)`, `dump.OUT` (= `script/jp`), `dump.load_map()`, `bytecode.parse(block)` → ops with `.opcode`, `.operands` (list of words after the opcode), `.offset_operands` (1-based operand indexes holding block offsets), `wrap.entry_boxes(block) -> {offset: Box(cols, lines)}`, `wrap.BOXES`, `rom.load()`, `rom.ROOT`.
- Produces:
  - `context.Ctx(speaker: int | None, box: wrap.Box, op: int, slot: int | None)`
  - `context.context(data, name, m=None) -> dict[int, Ctx]`, keyed by entry index; only entries referenced by a print op
  - `context.speaker_name(id) -> str`
  - `context.SPEAKERS` (path)
  - CLI `python -I scripts/context.py NAME [NAME ...]` prints the worksheet

- [ ] **Step 1: Write the failing test** (`scripts/test_context.py`)

```python
import os, unittest
import context, rom, wrap


@unittest.skipUnless(os.path.exists(rom.ROM_PATH), "ROM not present")
class Context(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = rom.load()

    def test_portrait_speaker(self):
        c = context.context(self.d, "scene_310")
        self.assertEqual(c[0].speaker, 0x03)          # なにか学校のようすが (after op 08 0003)
        self.assertEqual(c[6].speaker, 0x69)          # …あなたが霧島唯ね。 (after op 08 0069)
        self.assertEqual(c[10].speaker, 0x03)         # え？　あなた誰よ‼
        self.assertEqual(c[12].speaker, 0x69)
        self.assertEqual(c[6].box, wrap.PORTRAIT)
        self.assertEqual(c[6].op, 0x01)

    def test_op13_slot_speaker(self):
        c = context.context(self.d, "scene_319")
        slots = [x for x in c.values() if x.op == 0x13]
        self.assertTrue(slots)
        for x in slots:
            self.assertIn(x.slot, range(5))
            self.assertEqual(x.speaker, x.slot + 1)

    def test_unknown_speaker_label(self):
        self.assertEqual(context.speaker_name(0x03), "Yui")
        self.assertEqual(context.speaker_name(0x7FF), "id 0x7FF (?)")
        self.assertEqual(context.speaker_name(None), "-")
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python -I -m unittest discover -s scripts -p "test_context.py"`
Expected: ERROR `ModuleNotFoundError: No module named 'context'`

- [ ] **Step 3: Write `notes/speakers.json`**

```json
{
 "0x001": "Ayaka",
 "0x002": "Mai",
 "0x003": "Yui",
 "0x004": "Miki",
 "0x005": "Ryoko",
 "0x006": "Ai"
}
```

- [ ] **Step 4: Write `scripts/context.py`**

```python
"""Per-entry translation context from the scene bytecode: speaker (last op 08/02 id; op 13 slot k -> id k+1),
box, print op.

    python -I scripts/context.py scene_310 [scene_311 ...]     # worksheet: header, [speaker] box op, JP
"""
import json, os, re, sys
from dataclasses import dataclass
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bytecode, dump, rom, wrap

SPEAKERS = os.path.join(rom.ROOT, "notes", "speakers.json")
PORTRAIT_OPS = (0x08, 0x02)          # first operand = character id


@dataclass(frozen=True)
class Ctx:
    speaker: int | None
    box: wrap.Box
    op: int
    slot: int | None


def context(data, name, m=None):
    blk = dump.source(data, name, m or dump.load_map())
    entries = dump.parse_block(dump.read_text(os.path.join(dump.OUT, name + ".txt")))
    by_off = {e.offset: e for e in entries if e.alias is None}
    boxes = wrap.entry_boxes(blk)
    out, speaker = {}, None
    for o in bytecode.parse(blk):
        if o.opcode in PORTRAIT_OPS:
            speaker = o.operands[0]
        if o.opcode not in wrap.BOXES:
            continue
        for k in o.offset_operands:
            e = by_off.get(o.operands[k - 1])
            if e is None or e.index in out:
                continue
            slot = k - 1 if o.opcode == 0x13 else None
            out[e.index] = Ctx(slot + 1 if slot is not None else speaker, boxes.get(e.offset, wrap.FULL), o.opcode, slot)
    return out


def _speakers():
    try:
        with open(SPEAKERS, encoding="utf-8") as f:
            return {int(k, 16): v for k, v in json.load(f).items()}
    except FileNotFoundError:
        return {}


def speaker_name(sid, names=None):
    if sid is None:
        return "-"
    names = _speakers() if names is None else names
    return names.get(sid, f"id 0x{sid:03X} (?)")


def worksheet(data, name, m=None):
    ctx, names = context(data, name, m), _speakers()
    lines = []
    for e in dump.parse_block(dump.read_text(os.path.join(dump.OUT, name + ".txt"))):
        if e.alias is not None or e.data or e.text.strip() == "<END>":
            continue
        c = ctx.get(e.index)
        where = f"[{speaker_name(c.speaker, names)}] {c.box.cols}x{c.box.lines} op{c.op:02X}" if c else "[unreferenced]"
        head = f"## {name} {e.index:04d} @{e.offset:06X} len={e.length}"
        lines.append(f"{head}\n# {where}\n{re.sub('　+', ' ', e.text)}\n")
    return "\n".join(lines)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    d, m = rom.load(), dump.load_map()
    for n in sys.argv[1:]:
        print(worksheet(d, n, m))
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python -I -m unittest discover -s scripts -p "test_context.py"`
Expected: `OK` (3 tests)

- [ ] **Step 6: Smoke-test the worksheet**

Run: `python -I scripts/context.py scene_310 | head -12`
Expected:
- Headers like `## scene_310 0000 @00009A len=22`, followed by `# [Yui] 22x4 op01` and the Japanese.
- Entry 0006 shows `[id 0x069 (?)]`. That is fine: the speakers map fills in as translation goes.

- [ ] **Step 7: Commit**

```bash
git add scripts/context.py scripts/test_context.py notes/speakers.json
git commit -m "Add translation context tool (speaker, box, op-13 slot) and speakers map"
```

---

### Task 2: Coverage gate and glossary

**Files:**
- Create: `scripts/coverage.py`, `notes/glossary.md`
- Test: `scripts/test_coverage.py`

**Interfaces:**
- Consumes: `dump.parse_block`, `dump.read_text`, `dump.OUT`, `rom.ROOT`.
- Produces:
  - `coverage.needs_english(entry) -> bool`
  - `coverage.missing(jp_dir, en_dir, names=None) -> list[tuple[str, int]]`
  - `coverage.avoided(en_dir, glossary) -> list[tuple[str, int, str]]`
  - `coverage.avoid_list(glossary_path) -> list[str]`
  - CLI `python -I scripts/coverage.py [--check] [NAME | FIRST..LAST ...]`
- Glossary table format, parsed by `avoid_list`: a markdown table with header `| Japanese | English | Avoid |`. Avoid cells are comma-separated; empty cells are allowed.

- [ ] **Step 1: Write the failing test** (`scripts/test_coverage.py`)

```python
import os, shutil, tempfile, unittest
import coverage


def write(d, name, s):
    with open(os.path.join(d, name), "w", encoding="utf-8", newline="\n") as f:
        f.write(s)


JP = ("## scene_900 0000 @000010 len=8\nあいう<END>\n\n"
      "## scene_900 0001 @000018 len=2\n<END>\n\n"
      "## scene_900 0002 @00001A len=6 data\nあい<END>\n\n"
      "## scene_900 0003 =0000\n\n"
      "## scene_900 0004 @000020 len=6\n　…<END>\n\n"
      "## scene_900 0005 @000026 len=8\n霧島唯<END>\n")


class Coverage(unittest.TestCase):
    def setUp(self):
        self.jp, self.en = tempfile.mkdtemp(), tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.jp); self.addCleanup(shutil.rmtree, self.en)
        write(self.jp, "scene_900.txt", JP)

    def test_excludes_data_alias_and_symbol_only(self):
        self.assertEqual(coverage.missing(self.jp, self.en), [("scene_900", 0), ("scene_900", 5)])

    def test_translated_entry_counts(self):
        write(self.en, "scene_900.txt", "## scene_900 0000 @000010 len=8\nHey!<END>\n")
        self.assertEqual(coverage.missing(self.jp, self.en), [("scene_900", 5)])

    def test_japanese_left_in_english_counts_missing(self):
        write(self.en, "scene_900.txt", "## scene_900 0000 @000010 len=8\nHey!<END>\n\n"
                                        "## scene_900 0005 @000026 len=8\n霧島 Yui<END>\n")
        self.assertEqual(coverage.missing(self.jp, self.en), [("scene_900", 5)])

    def test_names_filter_and_range(self):
        write(self.jp, "scene_901.txt", JP.replace("scene_900", "scene_901"))
        self.assertEqual({n for n, _ in coverage.missing(self.jp, self.en, ["scene_901"])}, {"scene_901"})
        self.assertEqual(coverage.expand(["scene_900..scene_901"], self.jp), ["scene_900", "scene_901"])

    def test_avoided_whole_word(self):
        g = os.path.join(self.jp, "glossary.md")
        write(self.jp, "glossary.md",
              "| Japanese | English | Avoid |\n|---|---|---|\n| 唯 | Yui | Yuki, Yuui |\n| 彩香 | Ayaka | |\n")
        self.assertEqual(coverage.avoid_list(g), ["Yuki", "Yuui"])
        write(self.en, "scene_900.txt", "## scene_900 0000 @000010 len=8\nYuki? No, Yukiko.<END>\n\n"
                                        "## scene_900 0005 @000026 len=8\nyuki<END>\n")
        self.assertEqual(coverage.avoided(self.en, g), [("scene_900", 0, "Yuki")])
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python -I -m unittest discover -s scripts -p "test_coverage.py"`
Expected: ERROR `ModuleNotFoundError: No module named 'coverage'`

- [ ] **Step 3: Write `scripts/coverage.py`**

```python
"""Translation coverage: text entries still without English, and glossary avoid-list spellings in the English.

    python -I scripts/coverage.py [--check] [scene_310 | scene_30F..scene_325 | system ...]
"""
import glob, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dump, rom

EN = os.path.join(rom.ROOT, "script", "en")
GLOSSARY = os.path.join(rom.ROOT, "notes", "glossary.md")
JAPANESE = re.compile(r"[぀-ヿ一-鿿０-９Ａ-Ｚａ-ｚ]")   # kana, kanji, full-width alnum
TAG = re.compile(r"<[^>]*>")


def needs_english(e):
    return e.alias is None and not e.data and bool(JAPANESE.search(TAG.sub("", e.text)))


def _names(d):
    return sorted(os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(d, "*.txt")))


def expand(args, jp_dir=dump.OUT):
    all_names, out = _names(jp_dir), []
    for a in args:
        if ".." in a:
            lo, hi = a.split("..")
            out += [n for n in all_names if lo <= n <= hi]
        else:
            out.append(a)
    return out


def _read(path):
    return dump.parse_block(dump.read_text(path), joiner=" ") if os.path.exists(path) and dump.read_text(path).strip() else []


def missing(jp_dir, en_dir, names=None):
    out = []
    for name in names or _names(jp_dir):
        en = {e.index: e.text for e in _read(os.path.join(en_dir, name + ".txt"))}
        for e in _read(os.path.join(jp_dir, name + ".txt")):
            if needs_english(e) and (e.index not in en or JAPANESE.search(TAG.sub("", en[e.index]))):
                out.append((name, e.index))
    return out


def avoid_list(glossary):
    words, cols = [], None
    for line in dump.read_text(glossary).splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.lstrip().startswith("|") else None
        if not cells:
            cols = None
            continue
        if "Avoid" in cells:
            cols = cells.index("Avoid")
        elif cols is not None and cols < len(cells) and not set(cells[cols]) <= set("-: "):
            words += [w.strip() for w in cells[cols].split(",") if w.strip()]
    return words


def avoided(en_dir, glossary):
    words = [(w, re.compile(r"\b" + re.escape(w) + r"\b")) for w in avoid_list(glossary)]
    out = []
    for name in _names(en_dir):
        for e in _read(os.path.join(en_dir, name + ".txt")):
            out += [(name, e.index, w) for w, rx in words if rx.search(e.text)]
    return out


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    args = [a for a in sys.argv[1:] if a != "--check"]
    names = expand(args) if args else None
    miss = missing(dump.OUT, EN, names)
    bad = avoided(EN, GLOSSARY) if os.path.exists(GLOSSARY) else []
    total = sum(needs_english(e) for n in (names or _names(dump.OUT)) for e in _read(os.path.join(dump.OUT, n + ".txt")))
    print(f"translated {total - len(miss)}/{total} entries; {len(miss)} missing; {len(bad)} avoided spellings")
    if "--check" in sys.argv:
        for n, i in miss[:200]:
            print(f"missing {n} {i:04d}")
        for n, i, w in bad:
            print(f"avoid {n} {i:04d}: {w}")
        sys.exit(1 if miss or bad else 0)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -I -m unittest discover -s scripts -p "test_coverage.py"`
Expected: `OK` (5 tests)

- [ ] **Step 5: Write `notes/glossary.md`**

```markdown
# Glossary and style

Authoritative for every English entry. Speakers by id: `notes/speakers.json`. Voices: `notes/characters.md`.

## Style

- Natural, lively English. Localize meaning, keep jokes and each speaker's tone.
- Names: Western order (given name, then surname), Hepburn without macrons. Honorifics dropped.
- `‼` → `!` (or `!!` when shouting). `…` stays (2 columns). 「」 → `"`. Japanese blank padding dropped.
- Leading blank line in the Japanese → English starts with `<BR>` (build enforces).
- Op-13 placeholder slots (`…` only) → `…`.
- Stage banner: `Stage N Start`. Victory condition: `Goal: Defeat <name>`.

## Names and terms

| Japanese | English | Avoid |
|---|---|---|
| 霧島唯 / 唯 | Yui Kirishima / Yui | Yuki |
| 彩香 / 桜井彩香 | Ayaka / Ayaka Sakurai | Ayka |
| 舞 / 姫ノ木舞 | Mai / Mai Himenogi | |
| 美姫 / 静本美姫 | Miki / Miki Shizumoto | |
| 嶺子 / 葵嶺子 | Ryoko / Ryoko Aoi | Ryouko |
| 愛 | Ai | |
| ナージュ | Nage | Naju, Nāju |
| ニンフ | nymph | |
| 部活 | club | |
| 宝玉 | jewel | |
| 誕生石 | birthstone | |
| ATK DEF HP ESC SP CHG COS カード | ATK / DEF / HP / ESC / SP / CHG / COS card | |

## Compromises

(entries where box size forced a loss of meaning: `file index`: what was lost)

## Needs user check

(uncertain readings or interpretations: `file index`: question)
```

Ruling allowed in this step: if the script shows a dumped surname reading differs (e.g. 静本 is not Shizumoto), fix the row and ledger it.

- [ ] **Step 6: Run the CLI**

Run: `python -I scripts/coverage.py`
Expected: `translated 0/N entries; N missing; 0 avoided spellings`, with N ≈ 2280 scene + system entries.

- [ ] **Step 7: Commit**

```bash
git add scripts/coverage.py scripts/test_coverage.py notes/glossary.md
git commit -m "Add translation coverage gate and glossary"
```

---

### Task 3: Review page and character notes

**Files:**
- Create: `scripts/review.py`, `notes/characters.md`
- Test: `scripts/test_review.py`

**Interfaces:**
- Consumes: `context.context`, `context.speaker_name`, `context._speakers`, `coverage.needs_english`, `coverage._read`, `coverage._names`, `coverage.JAPANESE`, `coverage.TAG`, `dump.OUT`, `rom.load`.
- Produces: `review.page(data, jp_dir, en_dir, names=None) -> str` (HTML) and CLI `python -I scripts/review.py [--out build/review.html]`.

- [ ] **Step 1: Write the failing test** (`scripts/test_review.py`)

```python
import os, shutil, tempfile, unittest
import review, rom, dump


@unittest.skipUnless(os.path.exists(rom.ROM_PATH), "ROM not present")
class Review(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = rom.load()

    def setUp(self):
        self.en = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, self.en)
        with open(os.path.join(self.en, "scene_310.txt"), "w", encoding="utf-8", newline="\n") as f:
            f.write('## scene_310 0006 @0000DA len=22\n…So you\'re "Yui Kirishima".<END>\n')

    def test_rows(self):
        html = review.page(self.d, dump.OUT, self.en, ["scene_310"])
        self.assertIn("あなたが霧島唯ね", html)
        self.assertIn("Yui Kirishima", html)
        self.assertIn('class="missing"', html)          # entry 0000 untranslated
        self.assertIn("22x4", html)

    def test_review_escapes_tags(self):
        html = review.page(self.d, dump.OUT, self.en, ["scene_310"])
        self.assertIn("&lt;END&gt;", html)
        self.assertIn("&quot;Yui Kirishima&quot;", html)
        self.assertNotIn("<END>", html)
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python -I -m unittest discover -s scripts -p "test_review.py"`
Expected: ERROR `ModuleNotFoundError: No module named 'review'`

- [ ] **Step 3: Write `scripts/review.py`**

```python
"""Side-by-side review page: per file, index / speaker / box / Japanese / English; untranslated rows highlighted.

    python -I scripts/review.py [--out build/review.html]
"""
import html, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import context, coverage, dump, rom

STYLE = """body{font:14px sans-serif;margin:16px;background:#fff;color:#111}
table{border-collapse:collapse;width:100%;margin-bottom:24px}td,th{border:1px solid #ccc;padding:4px;vertical-align:top}
td.jp{width:38%}td.en{width:38%}tr.missing td.en{background:#fdd}h2{margin-top:32px}
@media (prefers-color-scheme:dark){body{background:#111;color:#eee}td,th{border-color:#444}tr.missing td.en{background:#522}}"""


def page(data, jp_dir, en_dir, names=None):
    m, speakers = dump.load_map(), context._speakers()
    out = [f"<!doctype html><meta charset=utf-8><title>Nage Libre review</title><style>{STYLE}</style>"]
    for name in names or coverage._names(jp_dir):
        en = {e.index: e.text for e in coverage._read(os.path.join(en_dir, name + ".txt"))}
        ctx = context.context(data, name, m) if name.startswith("scene_") else {}
        rows = []
        for e in coverage._read(os.path.join(jp_dir, name + ".txt")):
            if not coverage.needs_english(e):
                continue
            c = ctx.get(e.index)
            t = en.get(e.index)
            miss = t is None or bool(coverage.JAPANESE.search(coverage.TAG.sub("", t)))
            rows.append(f'<tr{" class=\"missing\"" if miss else ""}><td>{e.index:04d}</td>'
                        f"<td>{html.escape(context.speaker_name(c.speaker, speakers) if c else '-')}</td>"
                        f"<td>{f'{c.box.cols}x{c.box.lines}' if c else ''}</td>"
                        f'<td class="jp">{html.escape(e.text)}</td><td class="en">{html.escape(t or "")}</td></tr>')
        if rows:
            out.append(f"<h2>{name}</h2><table><tr><th>#</th><th>Speaker</th><th>Box</th><th>Japanese</th><th>English</th></tr>"
                       + "".join(rows) + "</table>")
    return "\n".join(out)


if __name__ == "__main__":
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else os.path.join(rom.ROOT, "build", "review.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(page(rom.load(), dump.OUT, coverage.EN))
    print(out)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -I -m unittest discover -s scripts -p "test_review.py"`
Expected: `OK` (2 tests)

- [ ] **Step 5: Write `notes/characters.md`** (skeleton; filled in batch by batch)

```markdown
# Character voices

Filled in while translating; each line cites the scene that shows it.

## Yui Kirishima (id 3)
Protagonist. Plain, energetic speech (〜よ, 〜なぁ？). English: casual, quick, exclamatory.

## Ryoko Aoi (id 5)
Polite ojou-sama register (〜ですわ, 〜ありますわ). English: refined, formal ("Oh my", "I do believe").

## Ayaka Sakurai (id 1)

## Mai Himenogi (id 2)

## Miki Shizumoto (id 4)

## Ai (id 6)

## Bosses and recurring characters
```

- [ ] **Step 6: Generate the page and commit**

Run: `python -I scripts/review.py`
Expected: prints `…/build/review.html`. The file opens in a browser with one table per scene file, all rows red (untranslated).

```bash
git add scripts/review.py scripts/test_review.py notes/characters.md
git commit -m "Add side-by-side review page and character notes"
```

---

### Tasks 4-12: Translation batches 1-9

Every batch task has the same steps; only the range differs.

| Task | Batch | Range (inclusive) | Files | Text entries |
|---|---|---|---|---|
| 4 | 1 | `scene_30F..scene_325` | 23 | 250 |
| 5 | 2 | `scene_326..scene_344` | 31 | 254 |
| 6 | 3 | `scene_345..scene_366` | 34 | 256 |
| 7 | 4 | `scene_367..scene_385` | 31 | 251 |
| 8 | 5 | `scene_386..scene_3AA` | 37 | 257 |
| 9 | 6 | `scene_3AB..scene_3E1` | 55 | 258 |
| 10 | 7 | `scene_3E2..scene_402` | 33 | 252 |
| 11 | 8 | `scene_403..scene_42D` | 43 | 257 |
| 12 | 9 | `scene_42E..scene_45B` | 46 | 243 |

**Files (each batch):**
- Create: `script/en/scene_XXX.txt` for every file in the range that has text entries.
- Modify: `notes/speakers.json`, `notes/glossary.md`, `notes/characters.md`.
- `scripts/fixtures/en_sample/` is NOT touched: test fixtures stay independent of the real translation.

**Interfaces:**
- Consumes: `context.py` worksheet CLI, `coverage.py` CLI, `build.py --en`, the glossary and character notes.
- Produces: `script/en` files that later batches and the final pass rely on for consistency.

- [ ] **Step 1: Generate the worksheet**

Run: `python -I scripts/context.py $(python -I -c "import sys;sys.path.insert(0,'scripts');import coverage;print(' '.join(coverage.expand(['FIRST..LAST'])))") > work/batch_N.txt`
Expected: one block per text entry: header, `# [speaker] box op`, Japanese.

- [ ] **Step 2: Read the worksheet and identify unknown speakers**
  - Read the whole batch before translating.
  - For every `id 0x… (?)`, decide the character from context: who is addressed, the guide's boss for that stage, and the names in the dialogue.
  - Add those ids to `notes/speakers.json`, e.g. `"0x069": "Tomomi"`.
  - If a speaker can't be determined, put `"0x…": "?"` and a "Needs user check" line in the glossary.

- [ ] **Step 3: Write the English files**
  - One `script/en/scene_XXX.txt` per file, using the Write tool.
  - Each entry: the JP header line verbatim, then the English body ending in `<END>`.
  - Include every entry the worksheet lists. Leave out data, alias and `<END>`-only entries.
  - Respect the box shown in the worksheet: 22×4 means at most 4 lines of 22 columns. Write tight English.
  - Japanese that starts with a full blank line → English starts with `<BR>`.

- [ ] **Step 4: Build until it fits**

Run: `python -I scripts/build.py --en script/en > work/build_N.log 2>&1; tail -3 work/build_N.log`
Expected: the build succeeds.
- On `does not fit` / `<BR>` errors, rewrite the named entry shorter and re-run.
- Every rewrite that loses meaning gets a "Compromises" line in the glossary.

- [ ] **Step 5: Coverage for the batch is complete**

Run: `python -I scripts/coverage.py --check FIRST..LAST`
Expected: `… 0 missing; 0 avoided spellings`, exit 0.

- [ ] **Step 6: Update notes**
  - New names and terms → glossary table, with an Avoid column for likely misspellings.
  - Voice observations → `notes/characters.md`, citing the scene.
  - Uncertain readings → "Needs user check".

- [ ] **Step 7: Commit**

```bash
git add script/en notes/speakers.json notes/glossary.md notes/characters.md
git commit -m "Translate batch N (FIRST-LAST)"
```

Test command for the task: `python -I scripts/coverage.py --check FIRST..LAST`.

---

### Task 13: System text

**Files:**
- Create: `script/en/system.txt`
- Modify: `notes/glossary.md`

**Interfaces:**
- Consumes: the 2c width rules (`scripts/syswidth.py`: surnames + given ≤ 10, battle lines ≤ 28, prompts 24, birthstones 14, menu 14, clubs 10), names settled in batches 1-9.
- Produces: the full `system.txt` translation.

- [ ] **Step 1: Generate the system worksheet**

Run: `python -I -c "import sys;sys.path.insert(0,'scripts');sys.stdout.reconfigure(encoding='utf-8');import dump;[print(f'## system {e.index:04d} @{e.offset:06X} len={e.length}\n{e.text}\n') for e in dump.parse_block(dump.read_text('script/jp/system.txt'))]" > work/system.txt`
Expected: 319 entries.

- [ ] **Step 2: Write `script/en/system.txt`** (Write tool, all 319 entries)
  - Surnames 0-99: `<END>`.
  - Given names 100-220: Hepburn romanization, ≤ 10 columns. Names already used in dialogue keep the same spelling.
  - Bosses 221-226: ナージュ Nage, アリア Aria, サティ Saty, ツキヨミ Tsukiyomi, ミスティ Misty, シャドウ Shadow.
  - Clubs 227-243: English club names, ≤ 10 columns.
  - Battle 244-277:
    - blank-line strings keep their width as spaces or full-width blanks
    - the composed pieces read as English lines: `'s attack!`, ` took `, ` damage!`, ` was defeated!`, ` gold obtained!`, …
    - yes/no: ` Yes    No` laid out to match the Japanese cursor positions (entry 276)
  - Prompts, birthstones, menu, jewels: English within their budgets.

- [ ] **Step 3: Build until it fits**

Run: `python -I scripts/build.py --en script/en > work/build_sys.log 2>&1; tail -3 work/build_sys.log`
Expected: success. Width errors name the entry and category; shorten and re-run.

- [ ] **Step 4: Coverage**

Run: `python -I scripts/coverage.py --check system`
Expected: 0 missing, exit 0.

- [ ] **Step 5: Commit**

```bash
git add script/en/system.txt notes/glossary.md
git commit -m "Translate system text"
```

---

### Task 14: Final consistency pass and emulator check

**Files:**
- Modify: `script/en/*` (fixes only), `notes/glossary.md`, `scripts/accept.py` (only if the english mode needs the real `script/en`)
- Create: `notes/translation.md`

- [ ] **Step 1: Full coverage gate**

Run: `python -I scripts/coverage.py --check`
Expected: `translated N/N entries; 0 missing; 0 avoided spellings`, exit 0.

- [ ] **Step 2: Consistency read**
  - Generate `python -I scripts/review.py` and read `build/review.html` file by file, in order.
  - Fix: name spellings, terms differing from the glossary, a character's voice drifting, repeated lines translated differently.
  - Re-run the build and coverage after the fixes.

- [ ] **Step 3: Emulator**
  - Build `python -I scripts/build.py --en script/en`.
  - Play the existing routes against it with `accept.play("full", <built rom>, accept.SYS_CHAIN)`, the same chain the `system` mode uses.
  - Inspect the screenshots: opening narration, stage-1 dialogue and banner, birthday screens, first battle.
  - Expected: English everywhere on these screens; no hiragana-as-Latin; no text outside the box frames.

- [ ] **Step 4: Write `notes/translation.md`**
  - coverage numbers
  - the review page path
  - the screenshot table (screen / file / result)
  - the "Needs user check" and "Compromises" counts, pointing to the glossary

- [ ] **Step 5: Full test suite and commit**

Run: `python -I -m unittest discover -s scripts`
Expected: OK.

```bash
git add script/en notes
git commit -m "Translation consistency pass; emulator check"
```
