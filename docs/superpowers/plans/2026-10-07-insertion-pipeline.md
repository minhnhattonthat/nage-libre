# Re-insertion Pipeline (2a) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a playable 2 MB ROM plus a BPS patch in which every scene block has been rebuilt from (optionally edited) text, recompressed and relocated, with all string/data offsets repointed.

**Architecture:** Python stdlib tools, building on sub-project 1's `decompress.py`, `tbl.py` and `dump.py`:
- `compress.py` inverts the decompressor.
- `bytecode.py` parses scene bytecode with a checked-in opcode table.
- `layout.py` rebuilds one block.
- `build.py` expands the ROM, places blocks, repoints the resource table and writes the ROM and patch (`bps.py`).
- Mesen headless runs prove the built ROM plays identically.

**Tech Stack:** Python 3.12 stdlib, `unittest`, Mesen2 2.1.1 `--testRunner` Lua (existing `scripts/mesen.py` and `scripts/mesen/lib.lua`).

**Spec:** `docs/superpowers/specs/2026-10-07-insertion-pipeline-design.md`

## Global Constraints

- Python 3.12, **stdlib only**. Run with `python -I`. CLI scripts start with `sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))`.
- Tests: `python -I -m unittest discover -s scripts -v` from project root. ROM-dependent tests use `@unittest.skipUnless(os.path.exists(rom.ROM_PATH), "ROM not present")`.
- All text I/O UTF-8 explicit. CLIs printing Japanese call `sys.stdout.reconfigure(encoding="utf-8")`.
- Clean ROM: `rom/Nage Libre - Seijaku no Suishin (Japan).sfc`, 1,572,864 bytes, header checksum `0xC895`. Never modified.
- Output: `build/nage_en.sfc` (exactly `0x200000` bytes) and `build/nage_en.bps`. Add `build/` to `.gitignore`.
- Scene resources: table at file offset `0x50000`, 3-byte little-endian FastROM pointers, resources `0x30F-0x45B`.
- New blocks go at file offsets `0x180000-0x1FFFFF` (CPU `$B08000-$BFFFFF`). **A compressed block must not cross a 32 KB bank** (the decompressor only increments the 16-bit part of `$09`).
- Scene buffer `$7F:64C0`, window **`0x1340`** bytes, unless Task 5 measures and rules otherwise.
- Header: ROM-size byte `$7FD7` is already `0x0B`. Checksum at `$7FDE`, complement at `$7FDC` (LoROM file offsets `0x7FDE`/`0x7FDC`).
- Translation input: `script/en/scene_XXX.txt`, same format as `script/jp`. Entries are matched by index, and `@offset len=` headers are ignored.
- Mesen facts (from sub-project 1): savestates only inside exec callbacks; memory callbacks report CPU addresses; callbacks must return nothing.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **Block placement across a bank boundary** (`$xxFFFF`→`$xx0000` wraps into non-ROM): the placer must start the block in the next bank. Pinned in Task 6 (`test_build.py::test_no_block_crosses_a_bank`).
2. **Translation file mistakes:** an index the block doesn't have, an edited `data` entry, text without `<END>`, a character outside the table. Each must fail the build naming file and entry, never be silently ignored. Pinned in Task 6 (`test_build.py::test_en_errors_name_file_and_entry`).
3. **An entry referenced by several operands, or by data ops (`09`/`0A`)**: every referencing operand must move together. Pinned in Task 4 (`test_layout.py::test_all_references_follow_moved_entry`).
4. **An `FFFF` word appearing as an operand before the real terminator** would make the dump's string-area start differ from the parse. Parse-driven termination must agree with the first-`FFFF` scan, or error. Pinned in Task 3 (`test_bytecode.py::test_parse_end_matches_first_ffff`).
5. **Rebuild determinism and clean-ROM safety:** building twice gives identical bytes, and the clean ROM file is never written. Pinned in Task 6 (`test_build.py::test_deterministic_and_clean_untouched`).

---

## File Structure

| Path | Responsibility |
|---|---|
| `scripts/bps.py` + `test_bps.py` | BPS create/apply |
| `scripts/romimage.py` + `test_romimage.py` | SNES checksum, set checksum, expand image |
| `scripts/compress.py` + `test_compress.py` | Nibble-format encoder |
| `scripts/opcodes.json` | Opcode table: words per op, which operand words are block offsets |
| `scripts/bytecode.py` + `test_bytecode.py` | Generate the table draft, parse blocks, `--check` CLI |
| `scripts/layout.py` + `test_layout.py` | Rebuild one scene block |
| `scripts/mesen/wram_map.lua`, `scripts/wram_free.py`, `scripts/mesen/routes/wram_tour.txt`, `notes/wram.md` | WRAM usage measurement |
| `scripts/build.py` + `test_build.py` | Whole-ROM build CLI |
| `scripts/mesen.py` (modify), `scripts/accept.py`, `scripts/mesen/routes/narration_next.txt`, `notes/insertion.md` | Emulator acceptance |

---

### Task 1: BPS patches and ROM image helpers

**Files:**
- Create: `scripts/bps.py`, `scripts/test_bps.py`, `scripts/romimage.py`, `scripts/test_romimage.py`
- Modify: `.gitignore` (add `build/`)

**Interfaces:**
- Produces:
  - `bps.create(src: bytes, dst: bytes) -> bytes`
  - `bps.apply(src: bytes, patch: bytes) -> bytes`, which raises `ValueError` on a bad magic, CRC or size
  - `romimage.checksum(data: bytes) -> int`, with the non-power-of-two tail mirrored
  - `romimage.set_checksum(img: bytearray) -> None`, which writes the complement at `0x7FDC` and the checksum at `0x7FDE`
  - `romimage.expand(data: bytes, size: int) -> bytearray`, padding with `0xFF`

- [ ] **Step 1: Add `build/` to `.gitignore`**: append the line `build/`.

- [ ] **Step 2: Write failing tests** `scripts/test_bps.py`

```python
import os, random, unittest, zlib
import bps, rom

class Bps(unittest.TestCase):
    def roundtrip(self, src, dst):
        p = bps.create(src, dst)
        self.assertEqual(p[:4], b"BPS1")
        self.assertEqual(bps.apply(src, p), dst)
        self.assertEqual(int.from_bytes(p[-8:-4], "little"), zlib.crc32(dst))
        return p

    def test_identical(self):
        self.roundtrip(b"abcdef" * 50, b"abcdef" * 50)

    def test_changes_growth_and_runs(self):
        rnd = random.Random(1)
        src = bytes(rnd.randrange(256) for _ in range(5000))
        dst = bytearray(src)
        dst[100:110] = b"XXXXXXXXXX"
        dst += b"\xff" * 4000 + bytes(rnd.randrange(256) for _ in range(300)) + b"\x00" * 50
        p = self.roundtrip(src, bytes(dst))
        self.assertLess(len(p), 1200)          # FF run must be a TargetCopy, not 4000 literals

    def test_shrink(self):
        self.roundtrip(b"0123456789" * 10, b"0123")

    def test_corrupt_patch_rejected(self):
        p = bytearray(bps.create(b"aaaa", b"abca"))
        p[5] ^= 1
        with self.assertRaises(ValueError):
            bps.apply(b"aaaa", bytes(p))

    def test_wrong_source_rejected(self):
        p = bps.create(b"aaaa", b"abca")
        with self.assertRaises(ValueError):
            bps.apply(b"aaab", p)
```

`scripts/test_romimage.py`:

```python
import os, unittest
import rom, romimage

class Checksum(unittest.TestCase):
    @unittest.skipUnless(os.path.exists(rom.ROM_PATH), "ROM not present")
    def test_clean_rom_matches_header(self):
        d = rom.load()
        self.assertEqual(romimage.checksum(d), 0xC895)
        self.assertEqual(d[0x7FDE] | d[0x7FDF] << 8, 0xC895)

    def test_power_of_two_is_plain_sum(self):
        data = bytes(range(256)) * 256          # 64 KB
        self.assertEqual(romimage.checksum(data), sum(data) & 0xFFFF)

    def test_tail_is_mirrored(self):
        data = b"\x01" * 0x10000 + b"\x02" * 0x8000      # 96 KB -> 64 KB + 32 KB tail mirrored twice
        self.assertEqual(romimage.checksum(data), (0x10000 + 2 * 2 * 0x8000) & 0xFFFF)

    def test_set_checksum_is_self_consistent(self):
        img = romimage.expand(bytes(0x8000) + b"\x07" * 0x8000, 0x20000)
        romimage.set_checksum(img)
        c = img[0x7FDE] | img[0x7FDF] << 8
        self.assertEqual(c, romimage.checksum(img))
        self.assertEqual(c ^ 0xFFFF, img[0x7FDC] | img[0x7FDD] << 8)

    def test_expand_pads_ff(self):
        img = romimage.expand(b"ab", 5)
        self.assertEqual(bytes(img), b"ab\xff\xff\xff")
```

- [ ] **Step 3: Run, expect FAIL**: `python -I -m unittest discover -s scripts -p "test_bps.py"` and `-p "test_romimage.py"` both report `ModuleNotFoundError`/`ImportError`.

- [ ] **Step 4: Implement** `scripts/bps.py`

```python
"""Minimal BPS patch create/apply (byuu's BPS1 format)."""
import zlib


def _num(n):
    out = bytearray()
    while True:
        x = n & 0x7F
        n >>= 7
        if n == 0:
            out.append(0x80 | x)
            return bytes(out)
        out.append(x)
        n -= 1


def _read(buf, i):
    data, shift = 0, 1
    while True:
        x = buf[i]
        i += 1
        data += (x & 0x7F) * shift
        if x & 0x80:
            return data, i
        shift <<= 7
        data += shift


def create(src, dst):
    """SourceRead for unchanged bytes, TargetCopy for runs of a repeated byte, TargetRead otherwise."""
    out = bytearray(b"BPS1" + _num(len(src)) + _num(len(dst)) + _num(0))
    lit, tgt_rel, i, n = bytearray(), 0, 0, len(dst)

    def flush():
        if lit:
            out.extend(_num(((len(lit) - 1) << 2) | 1) + lit)
            lit.clear()

    while i < n:
        if i < len(src) and src[i] == dst[i]:
            j = i
            while j < n and j < len(src) and src[j] == dst[j]:
                j += 1
            if j - i >= 4 or j == n:
                flush()
                out += _num(((j - i - 1) << 2) | 0)
                i = j
                continue
        if i > 0 and dst[i] == dst[i - 1]:
            j = i
            while j < n and dst[j] == dst[i - 1]:
                j += 1
            if j - i >= 8:
                flush()
                delta = (i - 1) - tgt_rel
                out += _num(((j - i - 1) << 2) | 3) + _num((abs(delta) << 1) | (delta < 0))
                tgt_rel = (i - 1) + (j - i)
                i = j
                continue
        lit.append(dst[i])
        i += 1
    flush()
    out += zlib.crc32(src).to_bytes(4, "little") + zlib.crc32(dst).to_bytes(4, "little")
    out += zlib.crc32(out).to_bytes(4, "little")
    return bytes(out)


def apply(src, patch):
    if patch[:4] != b"BPS1":
        raise ValueError("not a BPS1 patch")
    if zlib.crc32(patch[:-4]) != int.from_bytes(patch[-4:], "little"):
        raise ValueError("patch CRC mismatch (corrupt patch)")
    ssize, i = _read(patch, 4)
    tsize, i = _read(patch, i)
    msize, i = _read(patch, i)
    i += msize
    if len(src) != ssize or zlib.crc32(src) != int.from_bytes(patch[-12:-8], "little"):
        raise ValueError("source ROM does not match this patch")
    out, src_rel, tgt_rel, end = bytearray(), 0, 0, len(patch) - 12
    while i < end:
        data, i = _read(patch, i)
        action, length = data & 3, (data >> 2) + 1
        if action == 0:
            out += src[len(out):len(out) + length]
        elif action == 1:
            out += patch[i:i + length]
            i += length
        else:
            d, i = _read(patch, i)
            delta = -(d >> 1) if d & 1 else d >> 1
            if action == 2:
                src_rel += delta
                out += src[src_rel:src_rel + length]
                src_rel += length
            else:
                tgt_rel += delta
                for _ in range(length):
                    out.append(out[tgt_rel])
                    tgt_rel += 1
    if len(out) != tsize or zlib.crc32(out) != int.from_bytes(patch[-8:-4], "little"):
        raise ValueError("target CRC mismatch")
    return bytes(out)
```

`scripts/romimage.py`:

```python
"""SNES LoROM image helpers: header checksum and expansion."""


def checksum(data):
    """16-bit byte sum; a non-power-of-two tail is mirrored up to the next power of two."""
    size = 1 << (len(data) - 1).bit_length()
    if size == len(data):
        return sum(data) & 0xFFFF
    base = 1 << (len(data).bit_length() - 1)
    tail = data[base:]
    return (sum(data[:base]) + sum(tail) * ((size - base) // len(tail))) & 0xFFFF


def set_checksum(img):
    img[0x7FDC:0x7FE0] = b"\xff\xff\x00\x00"        # neutral pair contributes 0x1FE like any valid pair
    c = checksum(img)
    img[0x7FDC:0x7FE0] = (c ^ 0xFFFF).to_bytes(2, "little") + c.to_bytes(2, "little")


def expand(data, size):
    return bytearray(data) + b"\xff" * (size - len(data))
```

- [ ] **Step 5: Run, expect PASS**: `python -I -m unittest discover -s scripts -v`, all green.

- [ ] **Step 6: Commit**

```bash
git add .gitignore scripts/bps.py scripts/test_bps.py scripts/romimage.py scripts/test_romimage.py
git commit -m "Add BPS patch and ROM image helpers"
```

---

### Task 2: Recompressor

**Files:**
- Create: `scripts/compress.py`, `scripts/test_compress.py`

**Interfaces:**
- Consumes: `decompress.decompress(rom: bytes, off: int) -> (bytes, int)`.
- Produces: `compress.compress(data: bytes) -> bytes`, such that `decompress.decompress(compress(x), 0)[0] == x` and the consumed count equals `len(compress(x))`.

Format recap (from `notes/text-engine.md ## Compression`):
- **Stream start:** byte 0 is the first flag byte, then come nibbles, high nibble first.
- **Nibbles `0-7` (literal):** the byte is `(n<<4 | next)` with bit 7 taken from the flag MSB; flags `<<= 1`. After every 8th literal a new flag byte follows as 2 nibbles, even at the end.
- **Nibble `8` (run):** a count byte (2 nibbles), extended with more bytes while each count byte is `FF`. It repeats `ring[idx-2], ring[idx-1]` `count` times and doesn't update the ring.
- **Other nibbles:** `9` ends the stream; `A` writes `00`; `B` writes `FF`; `C-F` write ring slots 0-3.
- **The ring:** every single-byte write goes into `ring[idx]`, `idx = (idx+1)&3`. The ring starts as `FF FF FF FF`.

- [ ] **Step 1: Write failing test** `scripts/test_compress.py`

```python
import os, random, unittest
import compress, decompress, rom

def rt(test, data):
    packed = compress.compress(data)
    out, used = decompress.decompress(packed, 0)
    test.assertEqual(out, data)
    test.assertEqual(used, len(packed))
    return packed

class Synthetic(unittest.TestCase):
    def test_empty(self):
        rt(self, b"")

    def test_literals_with_high_bits_across_flag_groups(self):
        rt(self, bytes([0x81, 0x02, 0xF3, 0x74, 0x95, 0x16, 0xB7, 0x48, 0xC9, 0x1A, 0xEB]))   # 11 literals

    def test_exactly_eight_literals(self):
        rt(self, bytes([0x81, 0x12, 0xA3, 0x34, 0xC5, 0x56, 0xE7, 0x78]))

    def test_specials_and_ring(self):
        rt(self, bytes([0x00, 0xFF, 0x12, 0x00, 0x12, 0xFF, 0x12]))

    def test_word_runs_short_and_long(self):
        rt(self, b"\xfe\x03" * 3 + b"\x11\x22" * 254 + b"\x11\x22" * 300 + b"\x33")

    def test_run_count_exactly_255(self):
        rt(self, b"\x41\x42" + b"\x41\x42" * 255)

    def test_fuzz(self):
        rnd = random.Random(7)
        for _ in range(200):
            n = rnd.randrange(0, 600)
            kind = rnd.randrange(3)
            if kind == 0:
                data = bytes(rnd.randrange(256) for _ in range(n))
            elif kind == 1:
                data = bytes(rnd.choice((0, 0xFF, 0x03, 0xFE)) for _ in range(n))
            else:
                word = bytes([rnd.randrange(256), rnd.randrange(256)])
                data = b"".join(word * rnd.randrange(1, 40) + bytes([rnd.randrange(256)]) for _ in range(n // 20 + 1))
            rt(self, data)

@unittest.skipUnless(os.path.exists(rom.ROM_PATH), "ROM not present")
class GameData(unittest.TestCase):
    def test_every_decompressible_resource_roundtrips(self):
        d = rom.load()
        count = 0
        for r in range(0x530):
            p = int.from_bytes(d[0x50000 + 3 * r: 0x50000 + 3 * r + 3], "little")
            if not p & 0x8000 or (p >> 16) & 0xFE == 0x7E:
                continue
            try:
                blk, _ = decompress.decompress(d, rom.lorom_to_pc(p))
            except (IndexError, ValueError):
                continue
            rt(self, blk)
            count += 1
        self.assertGreater(count, 1000)
```

- [ ] **Step 2: Run, expect FAIL**: `python -I -m unittest discover -s scripts -p "test_compress.py"` fails with `No module named 'compress'`.

- [ ] **Step 3: Implement** `scripts/compress.py`

```python
"""Encoder for the Nage Libre nibble compression (inverse of decompress.py). Greedy; size is secondary."""


def _tokens(data):
    """Token list replaying the decoder's ring: ("lit", b), ("op", nibble), ("run", count)."""
    ring, idx, toks, i = [0xFF] * 4, 0, [], 0
    while i < len(data):
        pair = bytes([ring[(idx + 2) & 3], ring[(idx + 3) & 3]])
        k = 0
        while k < 0xFFFF and data[i + 2 * k: i + 2 * k + 2] == pair:
            k += 1
        if k >= 2:
            toks.append(("run", k))
            i += 2 * k
            continue
        b = data[i]
        if b == 0x00:
            toks.append(("op", 0xA))
        elif b == 0xFF:
            toks.append(("op", 0xB))
        elif b in ring:
            toks.append(("op", 0xC + ring.index(b)))
        else:
            toks.append(("lit", b))
        ring[idx] = b
        idx = (idx + 1) & 3
        i += 1
    return toks


def compress(data):
    toks = _tokens(bytes(data))
    bits = [v >> 7 for kind, v in toks if kind == "lit"]

    def flag(group):                           # flag byte for literals 8*group .. 8*group+7, MSB first
        g = (bits[8 * group: 8 * group + 8] + [0] * 8)[:8]
        return sum(bit << (7 - j) for j, bit in enumerate(g))

    nib, lits = [], 0

    def byte(v):
        nib.extend((v >> 4, v & 0xF))

    for kind, v in toks:
        if kind == "lit":
            nib.extend(((v >> 4) & 7, v & 0xF))
            lits += 1
            if lits % 8 == 0:
                byte(flag(lits // 8))
        elif kind == "run":
            nib.append(8)
            while v >= 0xFF:
                byte(0xFF)
                v -= 0xFF
            byte(v)
        else:
            nib.append(v)
    nib.append(9)
    if len(nib) % 2:
        nib.append(0)
    return bytes([flag(0)]) + bytes(nib[k] << 4 | nib[k + 1] for k in range(0, len(nib), 2))
```

- [ ] **Step 4: Run, expect PASS**: the same command, all green (the game-data test covers 1000+ resources and may take ~30 s).

- [ ] **Step 5: Commit**

```bash
git add scripts/compress.py scripts/test_compress.py
git commit -m "Add nibble-format recompressor"
```

---

### Task 3: Opcode table and bytecode parser

**Files:**
- Create: `scripts/bytecode.py`, `scripts/test_bytecode.py`, `scripts/opcodes.json`
- Modify: `notes/text-engine.md` (new section `## Bytecode`)

**Interfaces:**
- Consumes: `rom`, `disasm.disassemble`, `dump.load_map/source/extract_scene`, `tbl.Table`.
- Produces:
  - `bytecode.Op` (dataclass with `pos: int` = byte offset of the opcode word, `opcode: int`, `operands: list[int]`, `offset_operands: list[int]` = 1-based word indexes within the op that hold block offsets)
  - `bytecode.load_table(path=TABLE) -> dict[int, dict]`
  - `bytecode.parse(block: bytes, table=None) -> list[Op]`, which raises `ValueError` with the position on an unknown opcode or a terminator mismatch
  - `bytecode.code_end(block: bytes) -> int`, the byte offset just after the terminating `FFFF`
  - CLI `python -I scripts/bytecode.py --generate` writes a draft `opcodes.json`; `--check` reports per-block failures
- `opcodes.json` format: `{"ops": {"0x2B": {"handler": "839770", "words": 2, "offsets": [1], "note": "..."}, ...}}`. `words` includes the opcode word itself. `offsets` lists word indexes holding block offsets (text **or** data entries; spec field "string operand positions" generalized, because ops `09`/`0A` reference data tables).

Known facts:
- Dispatch is a compare chain in bank `$83`, of the form `C9 NN 00 D0 06 20 lo hi 82 xx xx` (`cmp #$00NN / bne +6 / jsr handler / brl`), covering ops `0x01-0x42`.
- Handlers are laid out in ascending address order.
- A naive rule (count `E6 06` `inc $06` bytes between consecutive handler addresses, halve for words) parses 147/333 blocks.
- Opcode `0000` occurs in blocks but isn't in the chain: it's handled before `$838105`.
- The 8 `adc #$64C0` sites `83840D 838463 838755 8388E9 838C13 8396A9 83978F 839BAD` are in the handlers of ops `01 0B 09 0A 13 26 2B 3B`.

- [ ] **Step 1: Write failing tests** `scripts/test_bytecode.py`

```python
import glob, os, unittest
import bytecode, dump, rom

def blocks():
    d, m = rom.load(), dump.load_map()
    for p in sorted(glob.glob(os.path.join(dump.OUT, "scene_*.txt"))):
        name = os.path.splitext(os.path.basename(p))[0]
        yield name, dump.source(d, name, m), dump.parse_block(dump.read_text(p))

class Synthetic(unittest.TestCase):
    T = {0x2B: {"words": 2, "offsets": [1]}, 0x20: {"words": 1, "offsets": []}}

    def test_parse_simple(self):
        blk = bytes.fromhex("2b00" "0a00" "2000" "ffff" "1000ffff")
        ops = bytecode.parse(blk, self.T)
        self.assertEqual([(o.pos, o.opcode, o.operands, o.offset_operands) for o in ops],
                         [(0, 0x2B, [0x000A], [1]), (4, 0x20, [], [])])
        self.assertEqual(bytecode.code_end(blk), 8)

    def test_unknown_opcode_reports_position(self):
        with self.assertRaisesRegex(ValueError, "unknown opcode 0077 at 0x2"):
            bytecode.parse(bytes.fromhex("2000" "7700" "ffff"), self.T)

    def test_parse_end_matches_first_ffff(self):
        # operand FFFF before the real terminator: parse ends later than the first-FFFF scan -> error
        with self.assertRaisesRegex(ValueError, "terminator"):
            bytecode.parse(bytes.fromhex("2b00" "ffff" "2000" "ffff"), self.T)

@unittest.skipUnless(os.path.exists(rom.ROM_PATH), "ROM not present")
class GameBlocks(unittest.TestCase):
    def test_all_scene_blocks_parse_and_offsets_hit_entries(self):
        failures, refs = [], 0
        for name, blk, entries in blocks():
            starts = {e.offset for e in entries}
            try:
                ops = bytecode.parse(blk)
            except ValueError as e:
                failures.append(f"{name}: {e}")
                continue
            for op in ops:
                for k in op.offset_operands:
                    refs += 1
                    if op.operands[k - 1] not in starts:
                        failures.append(f"{name}: op {op.opcode:02X} at {op.pos:#x} operand {k} = "
                                        f"{op.operands[k - 1]:#x} is not an entry start")
        self.assertEqual(failures[:20], [])
        self.assertGreater(refs, 2900)          # ~2617 text + ~351 data references measured

    def test_narration_print_op(self):
        d, m = rom.load(), dump.load_map()
        ops = bytecode.parse(dump.source(d, "scene_341", m))
        self.assertIn((0x2B, [0x0124]), [(o.opcode, o.operands) for o in ops])
```

- [ ] **Step 2: Run, expect FAIL**: `python -I -m unittest discover -s scripts -p "test_bytecode.py"` reports `No module named 'bytecode'`.

- [ ] **Step 3: Implement** `scripts/bytecode.py`

```python
"""Scene bytecode: opcode table (scripts/opcodes.json) and parser.

    python -I scripts/bytecode.py --generate   # draft table from the interpreter's compare chain
    python -I scripts/bytecode.py --check      # parse every scene block, report failures
"""
import json, os, sys
from dataclasses import dataclass
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rom

TABLE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "opcodes.json")
ADC_SITES = [0x83840D, 0x838463, 0x838755, 0x8388E9, 0x838C13, 0x8396A9, 0x83978F, 0x839BAD]


@dataclass
class Op:
    pos: int
    opcode: int
    operands: list
    offset_operands: list


def load_table(path=TABLE):
    with open(path, encoding="utf-8") as f:
        return {int(k, 16): v for k, v in json.load(f)["ops"].items()}


def code_end(block):
    for i in range(0, len(block) - 1, 2):
        if block[i:i + 2] == b"\xff\xff":
            return i + 2
    raise ValueError("no FFFF terminator in block")


def parse(block, table=None):
    table = load_table() if table is None else table
    ops, pos = [], 0
    while True:
        if pos + 2 > len(block):
            raise ValueError(f"ran off the block end at {pos:#x} without a terminator")
        op = int.from_bytes(block[pos:pos + 2], "little")
        if op == 0xFFFF:
            break
        if op not in table:
            raise ValueError(f"unknown opcode {op:04X} at {pos:#x}")
        n = table[op]["words"]
        words = [int.from_bytes(block[pos + 2 * k: pos + 2 * k + 2], "little") for k in range(1, n)]
        ops.append(Op(pos, op, words, list(table[op].get("offsets", []))))
        pos += 2 * n
    if pos + 2 != code_end(block):
        raise ValueError(f"terminator mismatch: parse ends at {pos:#x}, first FFFF word at {code_end(block) - 2:#x}")
    return ops


def generate():
    """Draft table: chain -> handlers; words = inc $06 pairs up to the next handler; offsets from adc #$64C0."""
    d = rom.load()
    chain = {}
    for i in range(0x18000, 0x1C000 - 11):
        if d[i] == 0xC9 and d[i + 2] == 0 and d[i + 3] == 0xD0 and d[i + 4] == 6 and d[i + 5] == 0x20 and d[i + 8] == 0x82:
            chain.setdefault(d[i + 1], 0x830000 | d[i + 6] | d[i + 7] << 8)
    hs = sorted(set(chain.values()))
    ops = {}
    for op, h in sorted(chain.items()):
        nxt = hs[hs.index(h) + 1] if hs.index(h) + 1 < len(hs) else h + 0x80
        body = d[rom.lorom_to_pc(h):rom.lorom_to_pc(nxt)]
        incs = [k for k in range(len(body) - 1) if body[k] == 0xE6 and body[k + 1] == 0x06]
        offsets = []
        for site in ADC_SITES:
            if h <= site < nxt:
                lda = body.rfind(b"\xa7\x06", 0, site - h)          # lda [$06] feeding the adc
                offsets.append(sum(1 for k in incs if k < lda) // 2)
        ops[f"0x{op:02X}"] = {"handler": f"{h:06X}", "words": len(incs) // 2, "offsets": offsets,
                              "note": "draft (naive inc $06 count)"}
    return {"ops": ops}


def check():
    import glob, dump
    d, m = rom.load(), dump.load_map()
    bad = 0
    for p in sorted(glob.glob(os.path.join(dump.OUT, "scene_*.txt"))):
        name = os.path.splitext(os.path.basename(p))[0]
        blk = dump.source(d, name, m)
        try:
            parse(blk)
        except ValueError as e:
            bad += 1
            words = [int.from_bytes(blk[i:i + 2], "little") for i in range(0, min(len(blk), 0x40), 2)]
            print(f"{name}: {e}\n    head: {' '.join(f'{w:04X}' for w in words)}")
    print(f"{333 - bad}/333 blocks parse")


if __name__ == "__main__":
    if "--generate" in sys.argv:
        with open(TABLE, "w", encoding="utf-8", newline="\n") as f:
            json.dump(generate(), f, indent=1)
    if "--check" in sys.argv:
        check()
```

- [ ] **Step 4: Generate the draft and run synthetic tests**
```
python -I scripts/bytecode.py --generate --check
python -I -m unittest discover -s scripts -p "test_bytecode.py"
```
Expected: the `Synthetic` tests PASS. `GameBlocks` FAILs, and `--check` prints about 147/333.

- [ ] **Step 5: Refine `opcodes.json` until `--check` prints `333/333 blocks parse`.** For each failing opcode (the `--check` output names the opcode and position):
  1. Read its handler: `python -I scripts/disasm.py 0x<handler> 0x80`. All handlers run 16-bit (`rep #$30`); use `--a8`/`--i8` after any `sep`.
  2. Count the words it advances `$06` on the path the game takes. Branchy handlers (e.g. op `29`, drafted as 0 words) need the real count. If the count depends on data, the op is variable-length: give it `"words": "var"` and add a branch in `parse` computing `n` from the op's first operand, with a code comment naming the handler instructions it mirrors. Add a synthetic test for that op in `test_bytecode.py` before changing `parse`.
  3. Opcode `0000` (not in the chain): find where the interpreter loop handles it, between the loop head and `$838105`, with `python -I scripts/disasm.py 0x8380E0 0x40`. Add it with its real word count.
  4. Set `note` to a short description of the handler (e.g. "print string at offset (box)"). Keep `offsets` from the adc analysis, and add an index only when the handler uses that operand as `$64C0`-relative.
  5. Re-run `--check` after each edit.

- [ ] **Step 6: Run all bytecode tests, expect PASS**: `python -I -m unittest discover -s scripts -p "test_bytecode.py" -v`. If `test_all_scene_blocks_parse_and_offsets_hit_entries` reports operands that are not entry starts, the `offsets` index for that opcode is wrong: re-read the handler. If `refs` is below 2900, an offset-bearing opcode is missing `offsets`: compare with the reviewer statistic (ops preceding text offsets: `01`, `0B`, `13`, `26`, `2B`, …; data: `09`, `0A`).

- [ ] **Step 7: Document** in `notes/text-engine.md` a `## Bytecode` section covering:
  - the chain location
  - the table file
  - per-op notes for the string/data ops
  - any variable-length ops
  - opcode `0000`

- [ ] **Step 8: Commit**

```bash
git add scripts/bytecode.py scripts/test_bytecode.py scripts/opcodes.json notes/text-engine.md
git commit -m "Add scene bytecode opcode table and parser"
```

---

### Task 4: Block layout (rebuild one scene block)

**Files:**
- Create: `scripts/layout.py`, `scripts/test_layout.py`

**Interfaces:**
- Consumes: `bytecode.parse`, `bytecode.code_end`, `dump.Entry` (fields `index, offset, length, text, data`), `dump.extract_scene(blk, table, name)`.
- Produces: `layout.rebuild(block: bytes, entries: list[dump.Entry], texts: dict[int, bytes], table=None) -> bytes`.
  - `texts` maps an entry index to its new encoded bytes, which must end with `FF FF`.
  - `table` is an opcode table (default `bytecode.load_table()`).
  - Raises `ValueError` when an offset operand doesn't hit an entry start, or when a text for a `data` entry is supplied.

- [ ] **Step 1: Write failing tests** `scripts/test_layout.py`

```python
import os, unittest
import bytecode, dump, layout, rom
from tbl import Table

T = {0x2B: {"words": 2, "offsets": [1]}, 0x0A: {"words": 3, "offsets": [2]}, 0x20: {"words": 1, "offsets": []}}
W = Table.parse("1000=あ\n1200=い\nFFFF=<END>!\n")

def words(*ws):
    return b"".join(w.to_bytes(2, "little") for w in ws)

# bytecode (10 words = 0x14 bytes): 2B 0014 | 0A 0005 0018 | 2B 0014 | 2B 001C | FFFF
# strings @0x14: "あ" END ; data @0x18: 0001 FFFF ; @0x1C: "い" END
BLK = words(0x2B, 0x14, 0x0A, 0x05, 0x18, 0x2B, 0x14, 0x2B, 0x1C, 0xFFFF,
            0x10, 0xFFFF, 0x0001, 0xFFFF, 0x12, 0xFFFF)

def entries(blk):
    es = dump.extract_scene(blk, W, "s")
    es[1].data = True
    return es

class Layout(unittest.TestCase):
    def test_identity(self):
        self.assertEqual(layout.rebuild(BLK, entries(BLK), {}, T), BLK)

    def test_all_references_follow_moved_entry(self):
        new = layout.rebuild(BLK, entries(BLK), {0: words(0x10, 0x10, 0x10, 0xFFFF)}, T)
        ops = bytecode.parse(new, T)
        self.assertEqual([o.operands for o in ops], [[0x14], [0x05, 0x1C], [0x14], [0x20]])
        self.assertEqual(new[0x1C:0x20], words(0x0001, 0xFFFF))           # data moved intact
        self.assertEqual(new[0x20:], words(0x12, 0xFFFF))

    def test_data_entry_text_rejected(self):
        with self.assertRaisesRegex(ValueError, "data entry"):
            layout.rebuild(BLK, entries(BLK), {1: words(0x10, 0xFFFF)}, T)

    def test_operand_not_on_entry_start(self):
        bad = bytearray(BLK); bad[2:4] = (0x16).to_bytes(2, "little")   # middle of entry 0
        with self.assertRaisesRegex(ValueError, "not an entry start"):
            layout.rebuild(bytes(bad), entries(bytes(bad)), {}, T)

    def test_text_must_end_with_terminator(self):
        with self.assertRaisesRegex(ValueError, "FFFF"):
            layout.rebuild(BLK, entries(BLK), {0: words(0x10)}, T)

@unittest.skipUnless(os.path.exists(rom.ROM_PATH), "ROM not present")
class GameBlocks(unittest.TestCase):
    def test_identity_rebuild_of_every_scene_block(self):
        d, m, t = rom.load(), dump.load_map(), Table.load(dump.TBL)
        for r in range(0x30F, 0x45C):
            name = f"scene_{r:03X}"
            blk = dump.source(d, name, m)
            self.assertEqual(layout.rebuild(blk, dump.extract_scene(blk, t, name), {}), blk, name)
```

- [ ] **Step 2: Run, expect FAIL**: `python -I -m unittest discover -s scripts -p "test_layout.py"` reports `No module named 'layout'`.

- [ ] **Step 3: Implement** `scripts/layout.py`

```python
"""Rebuild one scene block: new string bytes, original order and adjacency, every block-offset operand repointed."""
import bytecode


def rebuild(block, entries, texts, table=None):
    ops = bytecode.parse(block, table)
    end = bytecode.code_end(block)
    moved, area, pos = {}, bytearray(), end
    for e in entries:
        if e.index in texts:
            if e.data:
                raise ValueError(f"entry {e.index:04d} is a data entry; it cannot be replaced")
            b = texts[e.index]
            if b[-2:] != b"\xff\xff":
                raise ValueError(f"entry {e.index:04d}: new text must end with FFFF (<END>)")
        else:
            b = block[e.offset:e.offset + e.length]
        moved[e.offset] = pos
        area += b
        pos += len(b)
    out = bytearray(block[:end])
    for op in ops:
        for k in op.offset_operands:
            at = op.pos + 2 * k
            old = int.from_bytes(out[at:at + 2], "little")
            if old not in moved:
                raise ValueError(f"op {op.opcode:02X} at {op.pos:#x}: operand {k} = {old:#x} is not an entry start")
            out[at:at + 2] = moved[old].to_bytes(2, "little")
    return bytes(out + area)
```

- [ ] **Step 4: Run, expect PASS**: `python -I -m unittest discover -s scripts -v`, all green.

- [ ] **Step 5: Commit**

```bash
git add scripts/layout.py scripts/test_layout.py
git commit -m "Add scene block rebuild with operand repointing"
```

---

### Task 5: Measure the WRAM window

**Files:**
- Create: `scripts/mesen/wram_map.lua`, `scripts/wram_free.py`, `scripts/test_wram_free.py`, `scripts/mesen/routes/wram_tour.txt`, `notes/wram.md`

**Interfaces:**
- Consumes: `mesen.run`, `L.*`, routes from sub-project 1 (`dialogue1.txt`, `stage1.txt`, `wait150.txt`).
- Produces:
  - `work/trace/wram7f_<NAME>.txt` (lines `page pc`: the 256-byte page of bank `$7F` and the first writer PC)
  - `wram_free.free_spans(used: set[int]) -> list[tuple[int, int]]` (page spans never written)
  - the WINDOW/BASE decision in `notes/wram.md`, used by Task 6

- [ ] **Step 1: Write failing test** `scripts/test_wram_free.py`

```python
import unittest
import wram_free

class Spans(unittest.TestCase):
    def test_free_spans_between_used_pages(self):
        used = {0x00, 0x01, 0x10, 0x11, 0xFF}
        self.assertEqual(wram_free.free_spans(used), [(0x02, 0x10), (0x12, 0xFF)])

    def test_load_merges_runs(self):
        import tempfile, os
        d = tempfile.mkdtemp()
        for name, lines in (("a", "64 83D607\n"), ("b", "78 82BC48\n64 80F948\n")):
            with open(os.path.join(d, f"wram7f_{name}.txt"), "w", encoding="utf-8") as f:
                f.write(lines)
        self.assertEqual(wram_free.load(d), {0x64: {"83D607", "80F948"}, 0x78: {"82BC48"}})
```

- [ ] **Step 2: Run, expect FAIL** (`No module named 'wram_free'`).

- [ ] **Step 3: Implement** `scripts/wram_free.py`

```python
"""Summarise WRAM bank $7F page usage from wram_map.lua traces.

    python -I scripts/wram_free.py work/trace
"""
import glob, os, sys


def load(trace_dir):
    used = {}
    for p in glob.glob(os.path.join(trace_dir, "wram7f_*.txt")):
        with open(p, encoding="utf-8") as f:
            for line in f:
                page, pc = line.split()
                used.setdefault(int(page, 16), set()).add(pc)
    return used


def free_spans(used):
    """[(first_free_page, first_used_page_after), ...] for page runs never written."""
    spans, start = [], None
    for page in range(0x100):
        if page not in used and start is None:
            start = page
        elif page in used and start is not None:
            spans.append((start, page))
            start = None
    if start is not None:
        spans.append((start, 0x100))
    return spans


if __name__ == "__main__":
    used = load(sys.argv[1])
    for page in sorted(used):
        print(f"$7F:{page:02X}00 written by {' '.join(sorted(used[page]))}")
    for a, b in free_spans(set(used)):
        print(f"FREE $7F:{a:02X}00-$7F:{b * 0x100 - 1:04X} ({(b - a) * 0x100:#x} bytes)")
```

- [ ] **Step 4: Run, expect PASS.**

- [ ] **Step 5: Write** `scripts/mesen/wram_map.lua`

```lua
-- Record which 256-byte pages of WRAM bank $7F are written (first writer PC) while playing ROUTE from power-on.
local pages, lastPC = {}, 0
emu.addMemoryCallback(function(a) lastPC = a end, emu.callbackType.exec, 0, 0xFFFFFF, emu.cpuType.snes, emu.memType.snesMemory)
emu.addMemoryCallback(function(a)
  local p = (a >> 8) & 0xFF
  if not pages[p] then pages[p] = lastPC end
end, emu.callbackType.write, 0x10000, 0x1FFFF, emu.cpuType.snes, emu.memType.snesWorkRam)
L.load_route(ROUTE)
local done = false
L.on_frame(function(f)
  if L.route_done() and not done then
    done = true
    local out = assert(io.open(L.path("trace/wram7f_" .. NAME .. ".txt"), "w"))
    for p, pc in pairs(pages) do out:write(string.format("%02X %06X\n", p, pc)) end
    out:close()
    L.shot("shots/wram_" .. NAME .. "_final.png")
    L.finish(0)
  end
end)
```

- [ ] **Step 6: Build the tour route**: concatenate the existing routes, which play from power-on through the narration, the birthday screen, the map and the first battle:
```
cat scripts/mesen/routes/dialogue1.txt scripts/mesen/routes/stage1.txt scripts/mesen/routes/stage1.txt scripts/mesen/routes/wait150.txt > scripts/mesen/routes/wram_tour.txt
printf '# battle: press A a few times\n' >> scripts/mesen/routes/wram_tour.txt
for i in $(seq 1 30); do printf '4 a\n56 -\n' >> scripts/mesen/routes/wram_tour.txt; done
```

- [ ] **Step 7: Run and summarise**
```
python -I scripts/mesen.py scripts/mesen/wram_map.lua ROUTE=H:/translation/nage-libre/scripts/mesen/routes/wram_tour.txt NAME=tour
python -I scripts/wram_free.py work/trace
```
Open `work/shots/wram_tour_final.png` to confirm the run reached a battle.

- [ ] **Step 8: Search for other hard-coded references** to the buffer base before trusting relocation. Print every `C0 64` byte pair in banks `$80-$83` (file `0x0-0x1FFFF`) with its disassembly context:
```
python -I -c "import sys; sys.path.insert(0,'scripts'); import rom, disasm; d=rom.load(); [print('\n'.join(disasm.disassemble(rom.pc_to_lorom(i-2),6))) for i in range(0x20000) if d[i:i+2]==b'\xc0\x64']"
```
Classify each hit: an `adc #$64C0` site (known 8), the loader at `$8380F0`, or other. Any other real reference must be added to the relocation patch list in Task 6, or relocation is ruled out.

- [ ] **Step 9: Decide and record** in `notes/wram.md`:
  - the used pages with their writers
  - the free spans
  - the decision, which is one of:
    - (a) keep `BASE=0x64C0`, `WINDOW=0x1340`, if `$7F:7800` is the first used page after `$64C0` and no larger span contains `$64C0`'s neighbourhood
    - (b) relocate to a free span ≥ `0x2000` bytes, with `BASE` = its start and `WINDOW` = its size − `0x100` margin

  State plainly that unvisited screens (shop, ending, extra stage) were not measured, and that a relocation is only adopted if the Task 7 identity acceptance passes with it.

- [ ] **Step 10: Commit**

```bash
git add scripts/mesen/wram_map.lua scripts/wram_free.py scripts/test_wram_free.py scripts/mesen/routes/wram_tour.txt notes/wram.md
git commit -m "Measure WRAM bank 7F usage for the scene buffer"
```

---

### Task 6: Whole-ROM build

**Files:**
- Create: `scripts/build.py`, `scripts/test_build.py`

**Interfaces:**
- Consumes:
  - `romimage.checksum/set_checksum/expand`, `bps.create`, `compress.compress`, `decompress.decompress`
  - `layout.rebuild`, `dump.extract_scene/parse_block/read_text/TBL`, `tbl.Table`, `rom.lorom_to_pc/pc_to_lorom/ROM_PATH/ROOT`
  - Task 5's `BASE`/`WINDOW` decision
- Produces:
  - `build.BuildError`
  - `build.build(clean: bytes, en_dir: str | None = None) -> bytes`, returning the 2 MB image
  - `build.relocation_patches(base: int) -> list[tuple[int, bytes, bytes]]`
  - `build.WRAM_BASE`, `build.WRAM_WINDOW`
  - CLI `python -I scripts/build.py [--en DIR] [--out DIR]`, which writes `nage_en.sfc` and `nage_en.bps`

- [ ] **Step 1: Write failing tests** `scripts/test_build.py`

```python
import os, shutil, tempfile, unittest
import build, bytecode, decompress, dump, rom, romimage
from tbl import Table

def ptr(img, r):
    return rom.lorom_to_pc(int.from_bytes(img[0x50000 + 3 * r: 0x50000 + 3 * r + 3], "little"))

@unittest.skipUnless(os.path.exists(rom.ROM_PATH), "ROM not present")
class Build(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.clean = rom.load()
        cls.img = build.build(cls.clean)

    def test_identity_blocks_decompress_to_original(self):
        for r in range(0x30F, 0x45C):
            self.assertGreaterEqual(ptr(self.img, r), 0x180000)
            self.assertEqual(decompress.decompress(self.img, ptr(self.img, r))[0],
                             decompress.decompress(self.clean, ptr(self.clean, r))[0], f"res {r:03X}")

    def test_size_and_checksum(self):
        self.assertEqual(len(self.img), 0x200000)
        self.assertEqual(self.img[0x7FDE] | self.img[0x7FDF] << 8, romimage.checksum(self.img))

    def test_no_block_crosses_a_bank(self):
        for r in range(0x30F, 0x45C):
            start = ptr(self.img, r)
            used = decompress.decompress(self.img, start)[1]
            self.assertEqual(start // 0x8000, (start + used - 1) // 0x8000, f"res {r:03X}")

    def test_only_expected_bytes_changed_below_new_area(self):
        diff = [i for i in range(0x180000) if self.img[i] != self.clean[i]]
        allowed = set(range(0x50000 + 3 * 0x30F, 0x50000 + 3 * 0x45C)) | set(range(0x7FDC, 0x7FE0))
        allowed |= {at + k for at, old, new in build.relocation_patches(build.WRAM_BASE) for k in range(len(new))}
        self.assertEqual([i for i in diff if i not in allowed], [])

    def test_deterministic_and_clean_untouched(self):
        before = os.path.getmtime(rom.ROM_PATH)
        self.assertEqual(build.build(self.clean), self.img)
        self.assertEqual(os.path.getmtime(rom.ROM_PATH), before)

    def test_rejects_non_clean_rom(self):
        bad = bytearray(self.clean); bad[0x1000] ^= 1
        with self.assertRaisesRegex(build.BuildError, "clean"):
            build.build(bytes(bad))

    def test_relocation_patch_sites_match_clean_rom(self):
        for at, old, new in build.relocation_patches(0x2000):
            self.assertEqual(self.clean[at:at + len(old)], old, f"{at:#x}")

    def _en(self, body):
        d = tempfile.mkdtemp()
        with open(os.path.join(d, "scene_341.txt"), "w", encoding="utf-8") as f:
            f.write(body)
        self.addCleanup(shutil.rmtree, d)
        return d

    def test_growth_text_lands_and_operands_follow(self):
        t = Table.load(dump.TBL)
        jp = dump.extract_scene(dump.source(self.clean, "scene_341", dump.load_map()), t, "scene_341")
        grown = jp[0].text.replace("<END>", "") * 2 + "<END>"
        img = build.build(self.clean, self._en(f"## scene_341 0000 @000000 len=0\n{grown}\n"))
        blk = decompress.decompress(img, ptr(img, 0x341))[0]
        new = dump.extract_scene(blk, t, "scene_341")
        self.assertEqual(new[0].text, grown)
        self.assertEqual([e.text for e in new[1:]], [e.text for e in jp[1:]])
        ops = bytecode.parse(blk)
        starts = {e.offset for e in new}
        self.assertTrue(all(o.operands[k - 1] in starts for o in ops for k in o.offset_operands))

    def test_en_errors_name_file_and_entry(self):
        cases = [("## scene_341 9999 @000000 len=0\nあ<END>\n", "scene_341.txt entry 9999"),
                 ("## scene_341 0000 @000000 len=0\nあ\n", "<END>"),
                 ("## scene_341 0000 @000000 len=0\nQ<END>\n", "scene_341.txt entry 0000")]
        for body, msg in cases:
            with self.assertRaisesRegex(build.BuildError, msg):
                build.build(self.clean, self._en(body))

    def test_edited_data_entry_rejected(self):
        t = Table.load(dump.TBL)
        jp = dump.extract_scene(dump.source(self.clean, "scene_310", dump.load_map()), t, "scene_310")
        data = next(e for e in jp if e.data)
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d)
        with open(os.path.join(d, "scene_310.txt"), "w", encoding="utf-8") as f:
            f.write(f"## scene_310 {data.index:04d} @000000 len=0 data\nあ<END>\n")
        with self.assertRaisesRegex(build.BuildError, "data entry"):
            build.build(self.clean, d)
```

- [ ] **Step 2: Run, expect FAIL** (`No module named 'build'`).

- [ ] **Step 3: Implement** `scripts/build.py` (set `WRAM_BASE`/`WRAM_WINDOW` from `notes/wram.md`; the code shows decision (a))

```python
"""Build the patched ROM: rebuild + recompress every scene block into an expanded 2 MB ROM, write a BPS patch.

    python -I scripts/build.py [--en script/en] [--out build]
"""
import argparse, glob, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bps, compress, decompress, dump, layout, rom, romimage
from tbl import Table

CLEAN_CHECKSUM = 0xC895
SIZE = 0x200000
FREE_START = 0x180000
RES_TABLE = 0x50000
FIRST, LAST = 0x30F, 0x45B
WRAM_BASE = 0x64C0          # scene buffer $7F:WRAM_BASE (notes/wram.md)
WRAM_WINDOW = 0x1340        # max decompressed block size (notes/wram.md)
ADC_SITES = [0x83840D, 0x838463, 0x838755, 0x8388E9, 0x838C13, 0x8396A9, 0x83978F, 0x839BAD]
LOADER = 0x8380F0           # lda #$C0 / sta $06 / lda #$64 / sta $07


class BuildError(Exception):
    pass


def relocation_patches(base):
    """(file offset, expected original bytes, new bytes) moving the scene buffer to $7F:base."""
    if base == 0x64C0:
        return []
    lo, hi = base & 0xFF, base >> 8
    p = [(rom.lorom_to_pc(a), b"\x69\xc0\x64", bytes([0x69, lo, hi])) for a in ADC_SITES]
    p.append((rom.lorom_to_pc(LOADER), bytes.fromhex("a9c08506a9648507"), bytes([0xA9, lo, 0x85, 0x06, 0xA9, hi, 0x85, 0x07])))
    return p


def en_texts(path, entries, table):
    """{index: encoded bytes} for one translated scene file, validated against the JP entries."""
    by_index = {e.index: e for e in entries}
    out = {}
    for t in dump.parse_block(dump.read_text(path)):
        where = f"{os.path.basename(path)} entry {t.index:04d}"
        e = by_index.get(t.index)
        if e is None:
            raise BuildError(f"{where}: the block has no such entry")
        if e.data:
            if t.text != e.text:
                raise BuildError(f"{where}: data entry was edited (data entries must stay exactly as dumped)")
            continue
        if not t.text.endswith("<END>"):
            raise BuildError(f"{where}: text must end with <END>")
        try:
            out[t.index] = table.encode(t.text)
        except ValueError as x:
            raise BuildError(f"{where}: {x}") from None
    return out


def build(clean, en_dir=None):
    if len(clean) != 0x180000 or romimage.checksum(clean) != CLEAN_CHECKSUM:
        raise BuildError("input is not the clean 1.5 MB Nage Libre ROM (size/checksum mismatch)")
    table = Table.load(dump.TBL)
    if en_dir:
        for p in glob.glob(os.path.join(en_dir, "*.txt")):
            name = os.path.splitext(os.path.basename(p))[0]
            if not (name.startswith("scene_") and FIRST <= int(name[6:], 16) <= LAST):
                raise BuildError(f"{p}: not a scene file (expected scene_30F..scene_45B)")
    img = romimage.expand(clean, SIZE)
    free, over = FREE_START, []
    for r in range(FIRST, LAST + 1):
        name = f"scene_{r:03X}"
        at = RES_TABLE + 3 * r
        blk, _ = decompress.decompress(clean, rom.lorom_to_pc(int.from_bytes(clean[at:at + 3], "little")))
        entries = dump.extract_scene(blk, table, name)
        path = os.path.join(en_dir, name + ".txt") if en_dir else None
        texts = en_texts(path, entries, table) if path and os.path.exists(path) else {}
        try:
            new = layout.rebuild(blk, entries, texts)
        except ValueError as e:
            raise BuildError(f"{name}: {e}") from None
        if len(new) > WRAM_WINDOW:
            over.append(f"{name}: {len(new):#x} bytes > window {WRAM_WINDOW:#x}")
            continue
        packed = compress.compress(new)
        if free // 0x8000 != (free + len(packed) - 1) // 0x8000:
            free = (free // 0x8000 + 1) * 0x8000
        if free + len(packed) > SIZE:
            raise BuildError("expanded ROM is out of space")
        img[free:free + len(packed)] = packed
        img[at:at + 3] = rom.pc_to_lorom(free).to_bytes(3, "little")
        free += len(packed)
    if over:
        raise BuildError("blocks exceed the WRAM window (shorten text or relocate the buffer):\n  " + "\n  ".join(over))
    for off, old, new in relocation_patches(WRAM_BASE):
        if img[off:off + len(old)] != old:
            raise BuildError(f"patch at {off:#x}: unexpected original bytes {img[off:off + len(old)].hex()}")
        img[off:off + len(new)] = new
    romimage.set_checksum(img)
    return bytes(img)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--en", default=os.path.join(rom.ROOT, "script", "en"))
    ap.add_argument("--out", default=os.path.join(rom.ROOT, "build"))
    a = ap.parse_args()
    clean = rom.load()
    try:
        img = build(clean, a.en if os.path.isdir(a.en) else None)
    except BuildError as e:
        print("BUILD FAILED:", e)
        sys.exit(1)
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "nage_en.sfc"), "wb") as f:
        f.write(img)
    patch = bps.create(clean, img)
    with open(os.path.join(a.out, "nage_en.bps"), "wb") as f:
        f.write(patch)
    print(f"built {a.out}/nage_en.sfc ({len(img):#x} bytes), nage_en.bps ({len(patch)} bytes)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run, expect PASS**: `python -I -m unittest discover -s scripts -v`, all green. If `test_identity_blocks_decompress_to_original` fails for a block, `layout.rebuild` changed bytes, which the Task 4 identity test should already have caught; debug there first.

- [ ] **Step 5: Build and check the patch**
```
python -I scripts/build.py
python -I -c "import sys; sys.path.insert(0,'scripts'); import bps, rom; c=rom.load(); b=open('build/nage_en.sfc','rb').read(); assert bps.apply(c, open('build/nage_en.bps','rb').read())==b; print('bps ok')"
```
Expected: `built …`, then `bps ok`. With no `script/en/` directory, the build is the identity build.

- [ ] **Step 6: Commit**

```bash
git add scripts/build.py scripts/test_build.py
git commit -m "Add whole-ROM build with relocation, checksum and BPS"
```

---

### Task 7: Emulator acceptance

**Files:**
- Modify: `scripts/mesen.py` (optional `rom_path`; CLI `ROM=` param), `scripts/test_mesen.py`
- Create: `scripts/accept.py`, `scripts/mesen/routes/narration_next.txt`, `notes/insertion.md`

**Interfaces:**
- Consumes: `build.build`, `bps`, route files `dialogue1.txt`, `dialogue1_idle.txt`, `stage1.txt`, `map1.txt`, and `goto.lua` (params `ROUTE`, `SAVE`, `FROM`, `SHOT_EVERY`).
- Produces:
  - `mesen.run(script, params=None, timeout=600, rom_path=None) -> int`
  - CLI `python -I scripts/accept.py identity|growth` (exit 0 on pass) and `notes/insertion.md`

- [ ] **Step 1: Write failing test** (append to `scripts/test_mesen.py`)

```python
@unittest.skipUnless(os.path.exists(rom.ROM_PATH), "ROM not present")
class RomPath(unittest.TestCase):
    def test_runs_another_rom(self):
        import shutil, tempfile
        d = tempfile.mkdtemp()
        copy = os.path.join(d, "copy.sfc")
        shutil.copy(rom.ROM_PATH, copy)
        self.assertEqual(mesen.run(os.path.join(rom.ROOT, "scripts", "mesen", "smoke.lua"), timeout=120, rom_path=copy), 0)
        shutil.rmtree(d)
```

- [ ] **Step 2: Run, expect FAIL**: `TypeError: run() got an unexpected keyword argument 'rom_path'`.

- [ ] **Step 3: Implement** in `scripts/mesen.py`:
  - Change the signature to `def run(script, params=None, timeout=600, rom_path=None):`.
  - Pass `rom_path or rom.ROM_PATH` to the subprocess instead of `rom.ROM_PATH`.
  - In `__main__`, pop `ROM` from params: `rom_path = params.pop("ROM", None)` and `rc = run(sys.argv[1], params, rom_path=rom_path)`.

- [ ] **Step 4: Run, expect PASS.**

- [ ] **Step 5: Write** `scripts/accept.py`

```python
"""Emulator acceptance for the built ROM.

    python -I scripts/accept.py identity   # clean vs identity build: final screens of each route must match
    python -I scripts/accept.py growth     # build with scene_341 0000 doubled; screenshots for review
"""
import os, shutil, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build, dump, mesen, rom
from tbl import Table

ROUTES = os.path.join(rom.ROOT, "scripts", "mesen", "routes")
GOTO = os.path.join(rom.ROOT, "scripts", "mesen", "goto.lua")
CHAIN = [("dialogue1", None), ("dialogue1_idle", "dialogue1"), ("stage1", "dialogue1"), ("map1", "stage1")]


def play(tag, rom_path, chain=CHAIN):
    for route, src in chain:
        params = {"ROUTE": os.path.join(ROUTES, route + ".txt").replace("\\", "/"), "SAVE": f"{tag}_{route}", "SHOT_EVERY": 30}
        if src:
            params["FROM"] = f"{tag}_{src}"
        if mesen.run(GOTO, params, rom_path=rom_path) != 0:
            raise SystemExit(f"{tag}: route {route} failed")


def final(tag, route):
    with open(os.path.join(mesen.WORK, "shots", f"{tag}_{route}_final.png"), "rb") as f:
        return f.read()


def write_rom(img):
    d = tempfile.mkdtemp()
    p = os.path.join(d, "built.sfc")
    with open(p, "wb") as f:
        f.write(img)
    return d, p


def identity():
    d, built = write_rom(build.build(rom.load()))
    play("clean", rom.ROM_PATH)
    play("built", built)
    shutil.rmtree(d)
    ok = True
    for route, _ in CHAIN:
        same = final("clean", route) == final("built", route)
        ok &= same
        print(f"{route}: {'MATCH' if same else 'DIFF'}")
    return ok


def growth():
    clean = rom.load()
    t = Table.load(dump.TBL)
    jp = dump.extract_scene(dump.source(clean, "scene_341", dump.load_map()), t, "scene_341")
    en = tempfile.mkdtemp()
    with open(os.path.join(en, "scene_341.txt"), "w", encoding="utf-8") as f:
        f.write(f"## scene_341 0000 @000000 len=0\n{jp[0].text.replace('<END>', '') * 2}<END>\n")
    d, built = write_rom(build.build(clean, en))
    play("growth", built, [("dialogue1", None), ("narration_next", "dialogue1")])
    shutil.rmtree(d)
    shutil.rmtree(en)
    print("review work/shots/growth_narration_next_*.png: doubled line 0000, then 0002 and 0004 must read correctly")
    return True


if __name__ == "__main__":
    ok = identity() if sys.argv[1] == "identity" else growth()
    sys.exit(0 if ok else 1)
```

- [ ] **Step 6: Write the route** `scripts/mesen/routes/narration_next.txt`. From `dialogue1`, press A every 45 frames for 600 frames (the same pacing as the sub-project 1 `print` trace, which showed lines 0000, 0002 and 0004):
```
python -I -c "open('scripts/mesen/routes/narration_next.txt','w',newline='\n').write('# from dialogue1: advance narration (A every 45 frames)\n' + '43 -\n2 a\n' * 14)"
```

- [ ] **Step 7: Run identity acceptance**: `python -I scripts/accept.py identity`. Expected: four `MATCH` lines, exit 0.
  - If a route shows `DIFF`, view both final screenshots (`work/shots/clean_<route>_final.png`, `work/shots/built_<route>_final.png`). Recompressed blocks decompress in a different number of cycles, which can shift timing by a frame.
  - If the images differ only in timing (same text, different animation frame), extend that route by 60 idle frames for both ROMs, and record the ruling.
  - If the text differs, the build is wrong: stop and debug.

- [ ] **Step 8: Run growth acceptance**: `python -I scripts/accept.py growth`, then view `work/shots/growth_narration_next_*.png` (build a contact sheet if there are many). Confirm:
  - the doubled narration line shows across more box lines, without garbage
  - the later lines 「この世界を全て私の物に……」 and 「……　ＡＭ０６：１２　……」 appear intact

- [ ] **Step 9: Record** in `notes/insertion.md`:
  - the build command and outputs
  - the BPS size
  - identity results per route
  - growth screenshots reviewed (file names) and what they showed
  - the WRAM decision in effect
  - known limits (window, untested screens)

- [ ] **Step 10: Commit**

```bash
git add scripts/mesen.py scripts/test_mesen.py scripts/accept.py scripts/mesen/routes/narration_next.txt notes/insertion.md
git commit -m "Add emulator acceptance for built ROM; record results"
```
