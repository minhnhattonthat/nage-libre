# System Text (2c) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Relocate the bank-`$87` system text to bank `$BF` with every reference repointed, render English names half-width, enforce per-category widths, and verify it on the routes, including a cheat-assisted route to the after-stage menus.

**Architecture:**
- `sysrefs.py` scans code for the three reference kinds and records them, with manual additions, in `sysrefs.json`.
- `syslayout.py` lays out the block and generates patches. `syswidth.py` holds the category budgets.
- `build.py` places the blob at file `0x1F8000`, applies the reference patches, the helper bank patch and the name-renderer hook, and fills the old block with `■` markers.
- Mesen routes (with cheats) and an old-block read tracer prove nothing was missed.

**Tech Stack:** Python 3.12 stdlib, `unittest`, Mesen2 Lua (`scripts/mesen.py`, `goto.lua`, `accept.py`).

**Spec:** `docs/superpowers/specs/2026-10-08-system-text-design.md`

## Global Constraints

- Python 3.12 stdlib only; `python -I`. Tests: `python -I -m unittest discover -s scripts -v`. ROM tests `skipUnless(os.path.exists(rom.ROM_PATH))`. UTF-8 files with `newline="\n"`.
- **Never** write Python string literals containing `\x..` / `\n` through bash heredocs into source files; use the Write/Edit tools (escape mangling bit 2b three times).
- System block: file `0x38077-0x38B3E` (CPU `$878077-$878B3E`), 319 entries (`script/jp/system.txt`, `dump.extract` kind `list`).
- New location: file **`0x1F8000`**, CPU **`$BF8000`**, max `0x8000` bytes.
- Old block fill: `■` = code `03FC` (bytes `FC 03`), with `FFFF` at each original entry end.
- Helper `$878000`: `lda #$87` at `$878016` (bytes `A9 87`); patch the operand at `$878017` to `BF`.
- Name renderer hooks: `ldy #$0040` (`A0 40 00`) at `$81BACC` and `$81BB2A` → `jsr $F1B0` (`20 B0 F1`). Helper at `$81F1B0` (free FF run from `$81F1AD`):
  `A0 40 00 E0 00 10 B0 03 A0 20 00 60` (`ldy #$0040; cpx #$1000; bcs +3; ldy #$0020; rts`).
- Reference kinds:
  - `split`: `A9 lo 85 dp A9 hi 85 dp+1 A9 87 85 dp+2`
  - `imm16`: `A9/A2/A0 lo hi` where `hi:lo` is a string start, confirmed manually in `sysrefs.json`
  - `ptr24`: 3-byte LE `lo hi 87` in a pointer table, e.g. `$81AF58`
- Cheats (Pro Action Replay): `7E10CCFF` (invincible), `7E10D163` (death hit); infinite gold `7E17790F`, `7E177A27`.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **A reference the scanner misses** must show up as `■` on screen and as a non-zero old-block read count, never as silent stale Japanese. Pinned in Task 4 (`test_build.py::test_old_system_block_marked`) and Task 5 (old-read trace = 0).
2. **A misdecoded false positive** (e.g. `A9 87 85 0B` read as `lda #$8587`) must never be patched as a 16-bit reference. `imm16` refs come only from a manually confirmed list. Pinned in Task 2 (`test_sysrefs.py::test_imm16_only_from_confirmed_list`).
3. **A name with an odd letter count** (half cell) must render without garbage in the unused half. The buffer is cleared before rendering. Pinned in Task 5 (screenshot) and Task 3 (hook byte test).
4. **A string referenced by two different reference kinds** must have both patched to the same new address. Pinned in Task 3 (`test_syslayout.py::test_all_kinds_patched_consistently`).
5. **The system blob overflowing bank `$BF`** must fail the build. Pinned in Task 3 (`test_syslayout.py::test_overflow_rejected`).

---

### Task 1: Cheat route to the after-stage menu, old-block read tracer

**Files:**
- Modify: `scripts/mesen/goto.lua` (optional `CHEATS` param)
- Create: `scripts/mesen/oldreads.lua`, `scripts/mesen/routes/stage1_clear.txt` (+ menu routes), `notes/system-text.md`

**Interfaces:**
- Produces:
  - `goto.lua` param `CHEATS="7E10CCFF,7E10D163"` (applied with `emu.addCheat(emu.cheatType.snesProActionReplay, code)` before the route starts)
  - states `stage1_clear` (after-stage menu 「どうしますか？」), `shop`, `club`, `save` where reachable
  - `oldreads.lua` params `FROM`, `ROUTE`, `NAME`, `CHEATS`, writing `work/trace/oldreads_<NAME>.txt` with `count first_pc`

- [ ] **Step 1: Add the CHEATS param** to `scripts/mesen/goto.lua`. At the top of `begin()`, before `L.load_route(ROUTE)`:
```lua
  for code in tostring(CHEATS or ""):gmatch("[^,]+") do emu.addCheat(emu.cheatType.snesProActionReplay, code) end
```
Verify: `python -I scripts/mesen.py scripts/mesen/goto.lua FROM=stage1b ROUTE=H:/translation/nage-libre/work/run/battle_a.txt SAVE=cheatcheck CHEATS=7E10CCFF,7E10D163` exits 0. `work/shots/cheatcheck_final.png` shows the map after the won battle (as in the brainstorming probe). Create `work/run/battle_a.txt` first if missing: 60 × (`4 a` / `36 -`).

- [ ] **Step 2: Build `stage1_clear`.** With cheats on (invincible, death hit, infinite gold), drive Stage 1 from `map2` (free roam) to stage clear: defeat the enemies, then boss Tomomi Harata at the school door (guide).
  - Map control: inspect `work/shots/*` after each attempt.
  - Try D-pad moves toward the red enemy markers, with A to confirm moves/attacks. The unit walks on the tactical map, and a battle starts on contact.
  - Iterate route segments (`scripts/mesen/routes/stage1_clear.txt`, chaining from saved intermediate states) until the after-stage menu 「どうしますか？」 (買い物/部活選択/セーブ/スタート) is on screen. Save the state `stage1_clear`.
  - **Time box:** about 15 route iterations. If still not reached, record the furthest state in `notes/system-text.md`, and ledger a ruling that menus are verified by static coverage plus old-reads on reachable screens only, flagged for playtest.
- [ ] **Step 3: Menu states.** From `stage1_clear`, route into 買い物 (shop), 部活選択 (club select) and セーブ (save), saving states `shop`, `club`, `save`, with screenshots. Record the routes in `notes/routes.md`.
- [ ] **Step 4: Write** `scripts/mesen/oldreads.lua`:
```lua
-- Count reads of the ORIGINAL system block (ROM 0x38077-0x38B3E) while playing ROUTE from FROM; first reader PC.
local n, first, lastPC = 0, nil, 0
local function begin()
  for code in tostring(CHEATS or ""):gmatch("[^,]+") do emu.addCheat(emu.cheatType.snesProActionReplay, code) end
  emu.addMemoryCallback(function(a) lastPC = a end, emu.callbackType.exec, 0, 0xFFFFFF, emu.cpuType.snes, emu.memType.snesMemory)
  emu.addMemoryCallback(function(a) n = n + 1; if not first then first = lastPC end end,
    emu.callbackType.read, 0x38077, 0x38B3E, emu.cpuType.snes, emu.memType.snesPrgRom)
  L.load_route(ROUTE)
  local done = false
  L.on_frame(function()
    if L.route_done() and not done then
      done = true
      L.write_file("trace/oldreads_" .. NAME .. ".txt", string.format("%d %06X\n", n, first or 0))
      L.finish(0)
    end
  end)
end
if FROM then L.load_state(FROM, begin) else begin() end
```
- [ ] **Step 5: Commit**

```bash
git add scripts/mesen/goto.lua scripts/mesen/oldreads.lua scripts/mesen/routes notes/routes.md notes/system-text.md
git commit -m "Add cheat support, stage-clear route and old-block read tracer"
```

---

### Task 2: Reference scanner and coverage

**Files:**
- Create: `scripts/sysrefs.py`, `scripts/sysrefs.json`, `scripts/test_sysrefs.py`
- Modify: `notes/system-text.md`

**Interfaces:**
- Consumes: `rom`, `dump.extract` (system block via `dump.load_map()`), `tbl.Table`.
- Produces:
  - `sysrefs.Ref(kind: str, at: int, index: int)`, where `at` is the file offset of the patch site: for `split` the first `A9`, for `imm16` the opcode, for `ptr24` the pointer
  - `sysrefs.entries(rom) -> list[dump.Entry]`
  - `sysrefs.scan(rom) -> list[Ref]` (split + ptr24 automatically, plus `imm16` from `sysrefs.json` `confirmed_imm16`)
  - `sysrefs.load_manual() -> dict`
  - `sysrefs.coverage(refs, entries, manual) -> list[int]`: uncovered indexes not listed in `manual["unused"]` and not inside a `manual["lists"]` range
  - CLI `--check` (exit 1 when anything is uncovered)

`sysrefs.json` format:
```json
{"confirmed_imm16": [{"at": "0xBCCE", "note": "lda #$8715 entry 253, 81BCCE"}],
 "ptr24_tables": [{"at": "0xAF58", "count": 227, "note": "name pools, index*3 (81BAA5)"}],
 "lists": [{"first": 227, "last": 243, "base_index": 227, "note": "club names walked from $85FF (81EDAA)"}],
 "unused": [{"index": 999, "reason": "..."}]}
```

- [ ] **Step 1: Write failing tests** `scripts/test_sysrefs.py`

```python
import os, unittest
import rom, sysrefs

@unittest.skipUnless(os.path.exists(rom.ROM_PATH), "ROM not present")
class Scan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = rom.load()
        cls.refs = sysrefs.scan(cls.d)
        cls.es = sysrefs.entries(cls.d)

    def test_split_reference_to_attack_message(self):
        idx = next(e.index for e in self.es if rom.pc_to_lorom(e.offset) == 0x8786DF)
        self.assertIn(("split", rom.lorom_to_pc(0x8198A9), idx),
                      {(r.kind, r.at, r.index) for r in self.refs if r.at == rom.lorom_to_pc(0x8198A9)})

    def test_name_table_pointers(self):
        ptr = [r for r in self.refs if r.kind == "ptr24"]
        self.assertGreaterEqual(len(ptr), 200)
        self.assertTrue(all(0xAF58 <= r.at < 0xAF58 + 3 * 0x200 for r in ptr if r.at < 0xB600))

    def test_imm16_only_from_confirmed_list(self):
        confirmed = {int(x["at"], 16) for x in sysrefs.load_manual()["confirmed_imm16"]}
        self.assertEqual({r.at for r in self.refs if r.kind == "imm16"}, confirmed)

    def test_full_coverage(self):
        self.assertEqual(sysrefs.coverage(self.refs, self.es, sysrefs.load_manual()), [])
```
(`0x8198A9` is the first `A9` of the split setup for `$86DF`: the context of hit `8198B7` showed `lda #$DF / sta $09 / lda #$86 / sta $0A / lda #$87 / sta $0B`. The scanner reports the exact site; adjust the test's address to the scanner-reported `A9` if it differs by the 2-byte decode offset, and ledger that.)

- [ ] **Step 2: Run, expect FAIL** (`No module named 'sysrefs'`).

- [ ] **Step 3: Implement** `scripts/sysrefs.py` (write with the Write tool):

```python
"""Find every reference to the bank-$87 system text (file 0x38077-0x38B3E).

    python -I scripts/sysrefs.py --check
Kinds: split (8-bit lda/sta lo,hi,#$87 into dp..dp+2), imm16 (manually confirmed), ptr24 (3-byte table entries).
"""
import json, os, re, sys
from dataclasses import dataclass
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dump, rom
from tbl import Table

MANUAL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sysrefs.json")
CODE_END = 0x60000                      # code banks $80-$8B
SPLIT = re.compile(rb"\xa9(.)\x85(.)\xa9(.)\x85(.)\xa9\x87\x85(.)", re.S)


@dataclass(frozen=True)
class Ref:
    kind: str
    at: int
    index: int


def entries(data):
    block = next(b for b in dump.load_map() if b["name"] == "system")
    return dump.extract(data, Table.load(dump.TBL), block)


def load_manual():
    with open(MANUAL, encoding="utf-8") as f:
        return json.load(f)


def scan(data):
    es = entries(data)
    start = {rom.pc_to_lorom(e.offset): e.index for e in es}        # CPU $87xxxx -> index
    manual = load_manual()
    refs = []
    for m in SPLIT.finditer(data[:CODE_END]):
        lo, dp, hi, dp1, dp2 = (m.group(k)[0] for k in range(1, 6))
        addr = 0x870000 | hi << 8 | lo
        if dp1 == dp + 1 and dp2 == dp + 2 and addr in start:
            refs.append(Ref("split", m.start(), start[addr]))
    for t in manual["ptr24_tables"]:
        base = int(t["at"], 16)
        for k in range(t["count"]):
            p = int.from_bytes(data[base + 3 * k: base + 3 * k + 3], "little")
            if p in start:
                refs.append(Ref("ptr24", base + 3 * k, start[p]))
    for x in manual["confirmed_imm16"]:
        at = int(x["at"], 16)
        addr = 0x870000 | data[at + 1] | data[at + 2] << 8
        if addr not in start:
            raise ValueError(f"confirmed imm16 at {at:#x} does not point at a system string ({addr:06X})")
        refs.append(Ref("imm16", at, start[addr]))
    return refs


def coverage(refs, es, manual):
    covered = {r.index for r in refs}
    for lst in manual["lists"]:
        if lst["base_index"] in covered:
            covered |= set(range(lst["first"], lst["last"] + 1))
    covered |= {u["index"] for u in manual["unused"]}
    return [e.index for e in es if e.index not in covered]


if __name__ == "__main__":
    d = rom.load()
    refs = scan(d)
    missing = coverage(refs, entries(d), load_manual())
    kinds = {k: sum(r.kind == k for r in refs) for k in ("split", "imm16", "ptr24")}
    print(f"refs {kinds}; uncovered entries: {missing}")
    sys.exit(1 if missing and "--check" in sys.argv else 0)
```

Create `scripts/sysrefs.json` with the name table and the confirmed `imm16` sites found in brainstorming (`81BCCE` → entry 253, `81BCE2` → 252, `81EDAA`/`82F01D` → 227 the club-list base, `87F721` `ldx #$87F7` → 264), all as file offsets. Add `lists` for clubs 227-243 with `base_index` 227.

- [ ] **Step 4: Investigate the uncovered entries.** Run `python -I scripts/sysrefs.py`, and for each uncovered range:
  1. Trace reads on a screen that shows it, using `oldreads.lua`-style per-PC aggregation (copy the brainstorming `sysreaders` approach into the ad-hoc command). Use the `stage1` birthday screen for birthstones, `club` for clubs, battle for messages.
  2. Disassemble the reader's caller to classify the reference as split, imm16, ptr24 table, or base + walk/stride. Add it to `sysrefs.json` with a note.
  3. Strided records (e.g. birthstones, 7 glyphs + `FFFF` = 16 bytes): add `"stride": 16` to that list entry. Task 3 pads those records.
  4. Entries proven unreferenced go under `unused`, with the evidence (reader trace shows none, no code reference).

  Repeat until `--check` exits 0.
- [ ] **Step 5: Run tests, expect PASS.** Document the reference inventory (counts per kind, lists, unused) in `notes/system-text.md ## References`.
- [ ] **Step 6: Commit**

```bash
git add scripts/sysrefs.py scripts/sysrefs.json scripts/test_sysrefs.py notes/system-text.md
git commit -m "Add system-text reference scanner with full coverage"
```

---

### Task 3: Layout, patches and width budgets

**Files:**
- Create: `scripts/syslayout.py`, `scripts/test_syslayout.py`, `scripts/syswidth.py`, `scripts/test_syswidth.py`

**Interfaces:**
- Consumes: `sysrefs.Ref`, `sysrefs.load_manual()`, `dump.Entry`.
- Produces:
  - `syslayout.BASE_FILE = 0x1F8000`, `syslayout.BASE_CPU = 0xBF8000`, `syslayout.MAX = 0x8000`
  - `syslayout.layout(entries, texts: dict[int, bytes], data: bytes, strides: dict[int, int]) -> (blob: bytes, new: dict[int, int])`, where `new[index]` is the CPU address
  - `syslayout.patches(refs, new, data) -> list[(off, old, new)]`
  - `syslayout.marker_fill(entries, data) -> list[(off, old, new)]`
  - `syswidth.CATEGORIES: dict[str, tuple[int, int, int]]` (first, last, max_cols)
  - `syswidth.check(index, encoded: bytes) -> None` (raises `ValueError` naming category and limit)

- [ ] **Step 1: Write failing tests** `scripts/test_syslayout.py`:

```python
import unittest
import syslayout, sysrefs
from dump import Entry

def E(i, off, n):
    return Entry("system", i, off, n, "")

DATA = bytearray(0x100)
DATA[0x10:0x14] = bytes.fromhex("1000ffff")          # entry 0 @0x10 (len 4)
DATA[0x14:0x1A] = bytes.fromhex("12001400ffff")      # entry 1 @0x14 (len 6)
ES = [E(0, 0x10, 4), E(1, 0x14, 6)]

class Layout(unittest.TestCase):
    def test_order_and_addresses(self):
        blob, new = syslayout.layout(ES, {1: bytes.fromhex("41004200430044004500ffff")}, bytes(DATA), {})
        self.assertEqual(blob, bytes.fromhex("1000ffff") + bytes.fromhex("41004200430044004500ffff"))
        self.assertEqual(new, {0: 0xBF8000, 1: 0xBF8004})

    def test_stride_padding_and_overflow(self):
        blob, _ = syslayout.layout(ES, {0: bytes.fromhex("4100ffff")}, bytes(DATA), {0: 8})
        self.assertEqual(blob[:8], bytes.fromhex("4100fe03fe03ffff")[:8])
        with self.assertRaisesRegex(ValueError, "stride"):
            syslayout.layout(ES, {0: bytes.fromhex("41004200430044004500ffff")}, bytes(DATA), {0: 8})

    def test_overflow_rejected(self):
        big = [E(i, 0x10, 4) for i in range(0x3000)]
        with self.assertRaisesRegex(ValueError, "bank"):
            syslayout.layout(big, {}, bytes(DATA), {})

    def test_all_kinds_patched_consistently(self):
        d = bytearray(0x100)
        d[0x40:0x4C] = bytes.fromhex("a914 8509 a980 850a a987 850b")      # split -> $878014
        d[0x60:0x63] = bytes.fromhex("148087")                          # ptr24 -> $878014
        d[0x70:0x73] = bytes.fromhex("a91480")                          # imm16 -> $8014
        refs = [sysrefs.Ref("split", 0x40, 1), sysrefs.Ref("ptr24", 0x60, 1), sysrefs.Ref("imm16", 0x70, 1)]
        p = {off: new for off, old, new in syslayout.patches(refs, {1: 0xBF8004}, bytes(d))}
        self.assertEqual(p[0x41], b"\x04"); self.assertEqual(p[0x45], b"\x80"); self.assertEqual(p[0x49], b"\xbf")
        self.assertEqual(p[0x60], bytes.fromhex("0480bf"))
        self.assertEqual(p[0x71], bytes.fromhex("0480"))

    def test_marker_fill_keeps_lengths(self):
        p = syslayout.marker_fill(ES, bytes(DATA))
        filled = bytearray(DATA)
        for off, old, new in p:
            filled[off:off + len(new)] = new
        self.assertEqual(bytes(filled[0x10:0x1A]), bytes.fromhex("fc03ffff fc03fc03ffff".replace(" ", "")))
```

`scripts/test_syswidth.py`:

```python
import unittest
import syswidth

class Width(unittest.TestCase):
    def test_categories_cover_all_319(self):
        covered = set()
        for first, last, _ in syswidth.CATEGORIES.values():
            covered |= set(range(first, last + 1))
        self.assertEqual(covered, set(range(319)))

    def test_over_budget_names_category(self):
        name, (first, last, cols) = next(iter(syswidth.CATEGORIES.items()))
        too_long = b"".join((0x41).to_bytes(2, "little") for _ in range(cols + 1)) + b"\xff\xff"
        with self.assertRaisesRegex(ValueError, name):
            syswidth.check(first, too_long)
        syswidth.check(first, b"\x41\x00\xff\xff")
```

- [ ] **Step 2: Run, expect FAIL.**

- [ ] **Step 3: Implement** `scripts/syslayout.py` (Write tool):

```python
"""Lay out the system text block in bank $BF and build the reference patches."""
BASE_FILE, BASE_CPU, MAX = 0x1F8000, 0xBF8000, 0x8000
BLANK, END, MARK = bytes([0xFE, 0x03]), bytes([0xFF, 0xFF]), bytes([0xFC, 0x03])


def layout(entries, texts, data, strides):
    blob, new = bytearray(), {}
    for e in entries:
        b = texts.get(e.index, bytes(data[e.offset:e.offset + e.length]))
        stride = strides.get(e.index)
        if stride:
            if len(b) > stride:
                raise ValueError(f"system entry {e.index}: {len(b)} bytes > stride {stride}")
            b = b[:-2] + BLANK * ((stride - len(b)) // 2) + END
        new[e.index] = BASE_CPU + len(blob)
        blob += b
    if len(blob) > MAX:
        raise ValueError(f"system text is {len(blob):#x} bytes, more than one bank ({MAX:#x})")
    return bytes(blob), new


def patches(refs, new, data):
    out = []
    for r in refs:
        a = new[r.index]
        if r.kind == "split":
            for k, v in ((1, a & 0xFF), (5, (a >> 8) & 0xFF), (9, a >> 16)):
                out.append((r.at + k, bytes(data[r.at + k:r.at + k + 1]), bytes([v])))
        elif r.kind == "ptr24":
            out.append((r.at, bytes(data[r.at:r.at + 3]), a.to_bytes(3, "little")))
        elif r.kind == "imm16":
            out.append((r.at + 1, bytes(data[r.at + 1:r.at + 3]), (a & 0xFFFF).to_bytes(2, "little")))
        else:
            raise ValueError(f"unknown reference kind {r.kind}")
    return out


def marker_fill(entries, data):
    return [(e.offset, bytes(data[e.offset:e.offset + e.length]), MARK * (e.length // 2 - 1) + END) for e in entries]
```

(`split` operand offsets: `A9 lo` lo is at +1; `85 dp` ends at +3; `A9 hi` hi is at +5; `A9 87` bank is at +9.)

`scripts/syswidth.py`: start from the Japanese maxima per category (glyph count × 2 half-columns, from `script/jp/system.txt`). Task 5 raises them to the measured on-screen widths.

```python
"""Width budget (half-columns) per system-text category; English must fit where the string is drawn."""
CATEGORIES = {
    # name: (first index, last index, max half-columns) -- initial values = Japanese maxima; Task 5 measures screens
    "surname": (0, 119, 10),
    "given_name": (120, 220, 10),
    "boss_name": (221, 226, 10),
    "club": (227, 243, 10),
    "battle_message": (244, 288, 26),
    "birthstone": (289, 300, 14),
    "menu_prompt": (301, 318, 26),
}


def check(index, encoded):
    for name, (first, last, cols) in CATEGORIES.items():
        if first <= index <= last:
            width = sum(1 if int.from_bytes(encoded[i:i + 2], "little") < 0x80 else 2
                        for i in range(0, len(encoded) - 2, 2))
            if width > cols:
                raise ValueError(f"system entry {index} ({name}): {width} columns > {cols}")
            return
    raise ValueError(f"system entry {index}: no width category")
```

Before trusting the category boundaries above, print the entry ranges with `python -I -c` over `script/jp/system.txt` (surnames end where given names begin, etc.). Correct the indexes to the dump, keeping the test's 0-318 coverage, and ledger the boundaries chosen.

- [ ] **Step 4: Run, expect PASS.**
- [ ] **Step 5: Commit**

```bash
git add scripts/syslayout.py scripts/test_syslayout.py scripts/syswidth.py scripts/test_syswidth.py
git commit -m "Add system text layout, reference patches and width budgets"
```

---

### Task 4: Build integration

**Files:**
- Modify: `scripts/build.py`, `scripts/test_build.py`

**Interfaces:**
- Consumes: Tasks 2-3, `wrap`/`en.tbl` (English encoding), existing patch loop.
- Produces:
  - `build.system_patches(clean, en_dir) -> (blob_patch: tuple, patches: list)`
  - constants `HELPER_BANK_AT = lorom_to_pc(0x878017)`, `NAME_HOOKS = [0x81BACC, 0x81BB2A]`, `NAME_HELPER = 0x81F1B0`, `NAME_HELPER_BYTES`
  - `script/en/system.txt` support: same file format, entries matched by index; data entries are not applicable

- [ ] **Step 1: Write failing tests** (append to class `Build` in `scripts/test_build.py`, using the Edit tool):

```python
    def test_system_identity_relocation(self):
        import sysrefs
        es = sysrefs.entries(self.clean)
        for r in sysrefs.scan(self.clean):
            e = es[r.index]
            if r.kind == "ptr24":
                a = int.from_bytes(self.img[r.at:r.at + 3], "little")
            elif r.kind == "imm16":
                a = 0xBF0000 | int.from_bytes(self.img[r.at + 1:r.at + 3], "little")
            else:
                a = self.img[r.at + 9] << 16 | self.img[r.at + 5] << 8 | self.img[r.at + 1]
            off = rom.lorom_to_pc(a)
            self.assertEqual(self.img[off:off + e.length], self.clean[e.offset:e.offset + e.length], f"ref {r}")

    def test_old_system_block_marked(self):
        self.assertEqual(self.img[0x38077:0x38079], bytes([0xFC, 0x03]))
        self.assertEqual(self.img[rom.lorom_to_pc(0x878017)], 0xBF)

    def test_name_renderer_hooked(self):
        for a in build.NAME_HOOKS:
            self.assertEqual(self.img[rom.lorom_to_pc(a):rom.lorom_to_pc(a) + 3], bytes([0x20, 0xB0, 0xF1]))
        h = rom.lorom_to_pc(build.NAME_HELPER)
        self.assertEqual(self.img[h:h + 12], build.NAME_HELPER_BYTES)

    def test_system_en_width_enforced(self):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d)
        with open(os.path.join(d, "system.txt"), "w", encoding="utf-8") as f:
            f.write("## system 0000 @000000 len=0\nAVeryLongSurnameIndeed<END>\n")
        with self.assertRaisesRegex(build.BuildError, "system.txt entry 0000"):
            build.build(self.clean, d)
```

- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement** in `scripts/build.py` with the Edit tool:
  - **Name helper constants:** `NAME_HELPER_BYTES = bytes([0xA0, 0x40, 0x00, 0xE0, 0x00, 0x10, 0xB0, 0x03, 0xA0, 0x20, 0x00, 0x60])`, `NAME_HELPER = 0x81F1B0`, `NAME_HOOKS = [0x81BACC, 0x81BB2A]`.
  - **`system_patches(clean, en_dir)`:**
    1. Get `entries = sysrefs.entries(clean)` and `refs = sysrefs.scan(clean)`, and require `sysrefs.coverage(...) == []` (`BuildError` otherwise).
    2. Read `texts` from `<en_dir>/system.txt` if present, parsed with `dump.parse_block(raw, joiner=" ")`. Validate the index exists, encode with the `en.tbl` Table (no wrap), check `<END>`, check even length, and run `syswidth.check`, raising `BuildError(f"system.txt entry {i:04d}: ...")`.
    3. Set `strides` from `sysrefs.json` lists with a `stride`.
    4. Call `blob, new = syslayout.layout(...)`.
    5. Return the patches:
       - `(syslayout.BASE_FILE, img_bytes_there, blob)`
       - `syslayout.patches(refs, new, clean)`
       - `syslayout.marker_fill(entries, clean)`
       - the helper bank patch `(lorom_to_pc(0x878017), b"\x87", b"\xbf")`, using `bytes([...])` literals
       - the name hooks `(lorom_to_pc(h), bytes([0xA0, 0x40, 0x00]), bytes([0x20, 0xB0, 0xF1]))`
       - the helper `(lorom_to_pc(NAME_HELPER), bytes(clean[...12]), NAME_HELPER_BYTES)`, asserting the helper's original bytes are all `0xFF`
  - **Filename check:** the scene-file name check must allow `system.txt`: adjust the glob validation to skip `system.txt`.
  - **`build()`:** after the scene blocks, extend the patch loop with `system_patches(clean, en_dir)`. The blob patch's "old" is the expanded image's bytes at `0x1F8000` (`0xFF` fill), so take it from `img` rather than `clean`. The scene blocks must never reach `0x1F8000`: assert `free <= 0x1F8000` (`BuildError` "scene blocks overlap system text bank").
- [ ] **Step 4: Run, expect PASS.** The full suite must be green, including the 2a/2b build tests (`test_only_expected_bytes_changed_below_new_area` must allow the new patch sites: add `system_patches` offsets to `allowed`).
- [ ] **Step 5: Commit**

```bash
git add scripts/build.py scripts/test_build.py
git commit -m "Relocate system text to bank BF; hook name renderer for half-width"
```

---

### Task 5: Emulator verification and width budgets

**Files:**
- Create: `scripts/fixtures/en_sample/system.txt`
- Modify: `scripts/accept.py` (mode `system`), `scripts/syswidth.py` (measured budgets), `notes/system-text.md`

**Interfaces:**
- Consumes: routes and states from Task 1, `build.build`, `oldreads.lua`.
- Produces: `python -I scripts/accept.py system`. It:
  1. Runs identity-relocation screenshots against the font-patched reference.
  2. Runs `oldreads` on every route chain (`dialogue1`, `stage1`, `map1`, battle, the cheat route, menus).
  3. Builds with the fixtures and screenshots the English samples.
  4. Prints a summary.

- [ ] **Step 1: Fixtures** `scripts/fixtures/en_sample/system.txt` with English for:
  - the enemy surname/given name used in the first battle (`梨田`/`静子` entries)
  - 「の攻撃‼」 → `'s attack!`, 「のダメージ‼」 → ` damage!`, 「を倒した‼」 → ` defeated!`, 「ゴールド手に入れた‼」 → `Got gold!`
  - the birthday prompt 「これで誕生日はいいかな？」 → `Are these birthdays OK?`
  - the after-stage menu entries (どうしますか？/買い物/部活選択/セーブ/スタート) → `What now?`/`Shop`/`Clubs`/`Save`/`Start`

  Find the indexes in `script/jp/system.txt`. Keep within the Task 3 budgets.
- [ ] **Step 2: Add mode `system`** to `scripts/accept.py`:
  - identity: build without en, compare against the font-patched reference over `CHAIN` plus the battle (`stage1b` + `battle_a`) and menu routes from Task 1. All must MATCH. Note in the code comment that the old-block marker can't appear in identity frames unless a reference was missed.
  - oldreads: for every route, run `oldreads.lua` against the identity build; every count must be 0.
  - english: build with the fixtures, play the battle and menu routes, print the screenshot paths.
- [ ] **Step 3: Run** `python -I scripts/accept.py system`. If any oldreads count is non-zero, the reported first PC is the missed reader: return to Task 2 Step 4 for it, then re-run. If any identity route is DIFF, view both screenshots, find the string, and fix the reference.
- [ ] **Step 4: View the English screenshots:**
  - battle names: half-width letters, two per 16-px cell, nothing garbled in the half cell
  - battle messages, birthday prompt, menu items

  Measure each category's visible width (characters that fit before the window edge) and set `syswidth.CATEGORIES` max columns to those measurements. Re-run tests, and ledger each budget with its screenshot.
- [ ] **Step 5: Record** in `notes/system-text.md`:
  - reference inventory, identity results, oldreads per route
  - English screenshots, budgets with evidence
  - unreached screens (if the cheat route stalled), flagged for playtest
- [ ] **Step 6: Commit**

```bash
git add scripts/fixtures scripts/accept.py scripts/syswidth.py notes/system-text.md
git commit -m "Verify system text relocation and English rendering in emulator"
```
