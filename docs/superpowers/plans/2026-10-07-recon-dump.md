# Recon & Script Dump Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Find out how *Nage Libre* stores and draws its text, then dump every piece of Japanese script to editable UTF-8 files that re-encode byte-identically to the ROM.

**Architecture:** Mesen2 runs headless (`--testRunner`) with Lua scripts that drive input, save/load states, and log DMA, ROM reads and WRAM writes. A Python runner glues a shared `lib.lua` onto each script. Python stdlib tools then disassemble (via the bundled snes2asm), render the font, parse a table file, dump the script, and verify the round-trip.

**Tech Stack:** Mesen2 2.1.1 Lua API, Python 3.12 stdlib, snes2asm (in `tools/snes2asm`), `unittest`.

**Spec:** `docs/superpowers/specs/2026-10-07-recon-dump-design.md`

## Global Constraints

- ROM: `rom/Nage Libre - Seijaku no Suishin (Japan).sfc`, 1,572,864 bytes, LoROM, FastROM, unheadered. Never modified, never committed.
- Python: 3.12, **stdlib only**. Run every script with `python -I`. Because `-I` drops the script's own directory from `sys.path`, every CLI script in `scripts/` starts with `sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))`.
- Tests: `python -I -m unittest discover -s scripts -v` from project root. Tests that need the ROM use `@unittest.skipUnless(os.path.exists(rom.ROM_PATH), "ROM not present")`.
- All text files are read and written as **UTF-8 explicitly** (`encoding="utf-8"`). Windows' default codepage can't hold Japanese.
- Generated binaries, savestates, screenshots and traces go in `work/` (gitignored). Code, routes, notes, table, and the `script/jp` dump are committed.
- Mesen2 facts (verified 2026-10-07 by probe):
  - `tools/mesen2/Mesen.exe --testRunner <rom> <script.lua>`; process exit code = `emu.stop(code)`.
  - `emu.createSavestate()` / `emu.loadSavestate()` only work **inside an exec memory callback**. Elsewhere they fail (createSavestate fails silently).
  - The game runs in banks `$80+`. Exec callbacks must cover `0x000000-0xFFFFFF`.
  - Memory callbacks on `snesVideoRam` **never fire**. Track VRAM through writes to `$420B` (DMA), `$2116/7` (VMADD) and `$2118/9` instead.
  - Hardware registers: hook both the bank `$00` and bank `$80` mirrors (e.g. `0x002116` and `0x802116`).
  - `emu.read(addr, emu.memType.snesDebug)` reads registers without side effects.
  - `emu.getState()` keys: `cpu.pc cpu.k cpu.a cpu.x cpu.y cpu.ps cpu.dbr cpu.d cpu.sp ppu.frameCount`.
  - Memory callbacks must **return nothing**: a returned value can override the memory access.
  - Headless emulation runs at well over 1000 fps.
- Table file format (`nage.tbl`, UTF-8): `HEX=text` per line, `#` comments. Tags: `HEX=<NAME>`; `HEX=<NAME:n>` takes `n` argument bytes and renders as `<NAME:0310>`; a trailing `!` (`FF=<END>!`) marks a terminator. Unmapped bytes render as `<$XX>`.
- Script file format (`script/jp/<block>.txt`): `## <block> <index:04d> @<offset:06X> len=<n>` header, then the text. A real newline follows each break tag. Aliases use `## <block> <index> =<other index>`.

## Review Focus

1. **Japanese text written on Windows**: script files must survive write → read with no `UnicodeEncodeError` and no mojibake. Pinned in Task 8 (`test_dump.py::test_utf8_roundtrip_file`).
2. **Terminator value inside an argument byte** (e.g. `<PORTRAIT:FF>` where `FF` is also `<END>`): args must be consumed before the terminator check. Pinned in Task 6 (`test_tbl.py::test_arg_equal_to_terminator`).
3. **Unmapped bytes** must decode to `<$XX>` and re-encode to the same byte. Pinned in Task 6 (`test_tbl.py::test_unmapped_roundtrip`).
4. **Duplicate glyphs** (two codes, same character): the encoder can only pick one, so the second must decode to a raw `<$XXXX>` to keep the round-trip exact. Pinned in Task 6 (`test_tbl.py::test_duplicate_glyph_roundtrip`).
5. **Several pointers to the same message**: dump the text once, write the others as aliases, and the round-trip must still pass. Pinned in Task 8 (`test_dump.py::test_alias_pointer`).

---

## File Structure

| Path | Responsibility |
|---|---|
| `.gitignore` | add `work/` |
| `scripts/rom.py` | ROM path + LoROM ⇄ file-offset conversion |
| `scripts/mesen.py` | Run a Lua script in Mesen2 headless with params; CLI + `run()` |
| `scripts/mesen/lib.lua` | Shared Lua helpers: files, screenshots, savestates, input queue, frame hooks |
| `scripts/mesen/smoke.lua` | Self-check for lib.lua |
| `scripts/mesen/goto.lua` | Play a route file, screenshot as it goes, save a state at the end |
| `scripts/mesen/routes/*.txt` | Input routes (`<frames> <buttons>` per line) |
| `scripts/mesen/trace.lua` | Per-PC aggregate of ROM reads / WRAM writes, VRAM DMA log, memory dumps |
| `scripts/mesen/watch.lua` | Raw per-access log for chosen PCs / code range / WRAM range, with registers |
| `scripts/mesen/dump_mem.lua` | Dump a memory range when execution hits a PC |
| `scripts/trace_diff.py` | Diff two per-PC aggregates (what runs only while text prints) |
| `scripts/disasm.py` | Disassemble a ROM range (wraps snes2asm) |
| `scripts/render_font.py` | Render planar tiles to a labelled PNG sheet |
| `scripts/tbl.py` | Table file parse / decode / encode / check |
| `scripts/dump.py` | Follow `scripts/textmap.json`, write `script/jp/*.txt`, parse them back, gap report |
| `scripts/textmap.json` | Text block locations (filled from findings) |
| `scripts/test_roundtrip.py` | Real-ROM round-trip of every dumped message |
| `scripts/test_*.py` | Unit tests per module |
| `notes/text-engine.md`, `notes/text-inventory.md` | Findings |
| `nage.tbl`, `font/*.png`, `script/jp/*.txt` | Data deliverables |

---

### Task 1: ROM helpers, Mesen runner, Lua lib

**Files:**
- Modify: `.gitignore`
- Create: `scripts/rom.py`, `scripts/test_rom.py`, `scripts/mesen.py`, `scripts/mesen/lib.lua`, `scripts/mesen/smoke.lua`, `scripts/test_mesen.py`

**Interfaces:**
- Produces: `rom.ROOT`, `rom.ROM_PATH`, `rom.load() -> bytes`, `rom.lorom_to_pc(addr:int) -> int`, `rom.pc_to_lorom(off:int) -> int`; `mesen.run(script:str, params:dict|None=None, timeout:int=600) -> int`, `mesen.WORK`; CLI `python -I scripts/mesen.py <script.lua> KEY=VALUE ...`.
- Lua globals from `lib.lua`: `WORK` (absolute path with trailing `/`), `L.frame`, `L.path(rel)`, `L.write_file(rel, data)`, `L.read_file(rel)`, `L.shot(rel)`, `L.fail(msg)`, `L.safe(fn)`, `L.save_state(name, done)`, `L.load_state(name, done)`, `L.press(spec, frames)`, `L.load_route(abs_path)`, `L.route_done()`, `L.on_frame(fn(frame))`, `L.on_reg_write(reg16, fn(addr, value))`, `L.dump_mem(memType, size, rel)`, `L.finish(code)`. The runner creates `work/{run,shots,states,trace,mem}`. Lua writes only into those, with name prefixes (no `mkdir` from Lua).

- [ ] **Step 1: Ignore work dir**

Append to `.gitignore`:
```
work/
```

- [ ] **Step 2: Write failing ROM-helper tests** — `scripts/test_rom.py`

```python
import os, unittest
import rom

class LoRom(unittest.TestCase):
    def test_bank_mirrors_map_to_same_offset(self):
        self.assertEqual(rom.lorom_to_pc(0x808000), 0)
        self.assertEqual(rom.lorom_to_pc(0x008000), 0)

    def test_bank_end(self):
        self.assertEqual(rom.lorom_to_pc(0x82FFFF), 0x17FFF)

    def test_pc_to_lorom_is_fastrom(self):
        self.assertEqual(rom.pc_to_lorom(0x17FFF), 0x82FFFF)

    def test_roundtrip(self):
        for off in (0, 0x7FFF, 0x8000, 0x123456 % 0x180000, 0x17FFFF):
            self.assertEqual(rom.lorom_to_pc(rom.pc_to_lorom(off)), off)

    def test_rejects_non_rom(self):
        for addr in (0x7E2000, 0x7FA000, 0x002000):
            with self.assertRaises(ValueError):
                rom.lorom_to_pc(addr)

    @unittest.skipUnless(os.path.exists(rom.ROM_PATH), "ROM not present")
    def test_load_size(self):
        self.assertEqual(len(rom.load()), 0x180000)
```

- [ ] **Step 3: Run, expect FAIL** — `python -I -m unittest discover -s scripts -v` → `ModuleNotFoundError: No module named 'rom'`.

- [ ] **Step 4: Implement** `scripts/rom.py`

```python
"""ROM location and LoROM address helpers."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROM_PATH = os.path.join(ROOT, "rom", "Nage Libre - Seijaku no Suishin (Japan).sfc")


def load():
    with open(ROM_PATH, "rb") as f:
        return f.read()


def lorom_to_pc(addr):
    """CPU address ($00-$7D / $80-$FF banks, $8000-$FFFF) -> file offset."""
    if addr & 0x8000 == 0 or (addr >> 16) & 0xFE == 0x7E:
        raise ValueError(f"${addr:06X} is not a LoROM ROM address")
    return ((addr & 0x7F0000) >> 1) | (addr & 0x7FFF)


def pc_to_lorom(off):
    """File offset -> FastROM CPU address (bank $80+)."""
    return 0x800000 | ((off << 1) & 0x7F0000) | 0x8000 | (off & 0x7FFF)
```

- [ ] **Step 5: Run, expect PASS** — same command; `test_rom` 6 tests OK.

- [ ] **Step 6: Write the runner** `scripts/mesen.py`

```python
"""Run a Mesen2 Lua script headless.

    python -I scripts/mesen.py scripts/mesen/goto.lua ROUTE=... SAVE=dialogue1

lib.lua is prepended, preceded by WORK=<abs work dir> and the KEY=VALUE params
(numbers/0x.. stay numbers, anything else becomes a Lua string).
"""
import os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rom

MESEN = os.path.join(rom.ROOT, "tools", "mesen2", "Mesen.exe")
WORK = os.path.join(rom.ROOT, "work")
LIB = os.path.join(rom.ROOT, "scripts", "mesen", "lib.lua")
SUBDIRS = ("run", "shots", "states", "trace", "mem")


def lua_value(v):
    v = str(v)
    if v.lstrip("-").isdigit() or v.lower().startswith("0x"):
        return v
    return '"' + v.replace("\\", "/").replace('"', '\\"') + '"'


def run(script, params=None, timeout=600):
    for d in SUBDIRS:
        os.makedirs(os.path.join(WORK, d), exist_ok=True)
    name = os.path.splitext(os.path.basename(script))[0]
    head = ['WORK = "%s/"' % WORK.replace("\\", "/")]
    head += ["%s = %s" % (k, lua_value(v)) for k, v in (params or {}).items()]
    with open(LIB, encoding="utf-8") as f:
        lib = f.read()
    with open(script, encoding="utf-8") as f:
        body = f.read()
    combined = os.path.join(WORK, "run", name + ".lua")
    with open(combined, "w", encoding="utf-8") as f:
        f.write("\n".join(head) + "\n" + lib + "\n" + body)
    err = os.path.join(WORK, "lua_error.txt")
    if os.path.exists(err):
        os.remove(err)
    p = subprocess.run([MESEN, "--testRunner", rom.ROM_PATH, combined], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=timeout)
    with open(os.path.join(WORK, "run", name + ".out"), "w", encoding="utf-8") as f:
        f.write(p.stdout + p.stderr)
    if os.path.exists(err):
        with open(err, encoding="utf-8") as f:
            raise RuntimeError("Lua error: " + f.read())
    return p.returncode


if __name__ == "__main__":
    params = dict(a.split("=", 1) for a in sys.argv[2:])
    rc = run(sys.argv[1], params)
    print("exit", rc)
    sys.exit(rc)
```

- [ ] **Step 7: Write** `scripts/mesen/lib.lua`

```lua
-- Shared helpers. The runner prepends WORK (abs path, trailing /) and params.
L = { frame = 0 }
local snes, cpuMem = emu.cpuType.snes, emu.memType.snesMemory

function L.path(rel) return WORK .. rel end
function L.write_file(rel, data) local f = assert(io.open(WORK .. rel, "wb")); f:write(data); f:close() end
function L.read_file(rel) local f = assert(io.open(WORK .. rel, "rb")); local d = f:read("a"); f:close(); return d end
function L.shot(rel) L.write_file(rel, emu.takeScreenshot()) end
function L.finish(code) emu.stop(code or 0) end
function L.fail(msg)
  local f = io.open(WORK .. "lua_error.txt", "a"); f:write(tostring(msg) .. "\n"); f:close()
  emu.stop(2)
end
-- Wrap a callback so Lua errors stop the run and land in work/lua_error.txt. Returns nothing.
function L.safe(fn) return function(...) local ok, e = pcall(fn, ...); if not ok then L.fail(e) end end end

-- Register writes: hook bank $00 and $80 mirrors.
function L.on_reg_write(reg, fn)
  for _, bank in ipairs({0x000000, 0x800000}) do
    emu.addMemoryCallback(L.safe(fn), emu.callbackType.write, bank + reg, bank + reg, snes, cpuMem)
  end
end

function L.dump_mem(mem, size, rel)
  local t = {}
  for i = 0, size - 1 do t[#t + 1] = string.char(emu.read(i, mem)) end
  L.write_file(rel, table.concat(t))
end

-- Savestates only work inside an exec callback: queue jobs, run them on the next instruction.
local jobs, execId = {}, nil
local function service()
  local job = table.remove(jobs, 1)
  if not job then return end
  if job.op == "save" then
    L.write_file("states/" .. job.name .. ".mss", emu.createSavestate())
  else
    emu.loadSavestate(L.read_file("states/" .. job.name .. ".mss"))
  end
  if #jobs == 0 then
    emu.removeMemoryCallback(execId, emu.callbackType.exec, 0, 0xFFFFFF, snes, cpuMem)
    execId = nil
  end
  if job.done then job.done() end
end
local function schedule(job)
  jobs[#jobs + 1] = job
  if not execId then
    execId = emu.addMemoryCallback(L.safe(service), emu.callbackType.exec, 0, 0xFFFFFF, snes, cpuMem)
  end
end
function L.save_state(name, done) schedule({ op = "save", name = name, done = done }) end
function L.load_state(name, done) schedule({ op = "load", name = name, done = done }) end

-- Input queue: entries {buttons, frames}. spec is "-" or "a+start+up".
local queue = {}
function L.press(spec, frames)
  local b = {}
  if spec ~= "-" then for name in spec:gmatch("[^+]+") do b[name] = true end end
  queue[#queue + 1] = { buttons = b, frames = frames }
end
function L.load_route(path)
  for line in io.lines(path) do
    local l = line:gsub("#.*", ""):match("^%s*(.-)%s*$")
    if l ~= "" then
      local n, spec = l:match("^(%d+)%s+(%S+)$")
      if not n then error("bad route line: " .. line) end
      L.press(spec, tonumber(n))
    end
  end
end
function L.route_done() return #queue == 0 end
emu.addEventCallback(L.safe(function()
  local q = queue[1]
  if q then emu.setInput(q.buttons, 0) end
end), emu.eventType.inputPolled)

local frameFns = {}
function L.on_frame(fn) frameFns[#frameFns + 1] = fn end
emu.addEventCallback(L.safe(function()
  L.frame = L.frame + 1
  local q = queue[1]
  if q then q.frames = q.frames - 1; if q.frames <= 0 then table.remove(queue, 1) end end
  for _, fn in ipairs(frameFns) do fn(L.frame) end
end), emu.eventType.endFrame)
```

- [ ] **Step 8: Write the self-check** `scripts/mesen/smoke.lua`

```lua
-- lib.lua self-check: ROM read callbacks give file offsets; save then load restores the frame.
local reads, maxRom = 0, 0
emu.addMemoryCallback(function(a) reads = reads + 1; if a > maxRom then maxRom = a end end,
  emu.callbackType.read, 0, 0x17FFFF, emu.cpuType.snes, emu.memType.snesPrgRom)
L.press("-", 200)
local loading = false
L.on_frame(function(f)
  if f == 120 then L.save_state("smoke") end
  if f == 160 and not loading then
    loading = true
    L.load_state("smoke", function()
      L.shot("shots/smoke.png")
      L.write_file("trace/smoke.txt", string.format("reads=%d maxRom=%d loadedFrame=%d\n",
        reads, maxRom, emu.getState()["ppu.frameCount"]))
      L.finish(0)
    end)
  end
end)
```

- [ ] **Step 9: Write the integration test** `scripts/test_mesen.py`

```python
import os, unittest
import mesen, rom

@unittest.skipUnless(os.path.exists(rom.ROM_PATH), "ROM not present")
class MesenSmoke(unittest.TestCase):
    def test_smoke(self):
        rc = mesen.run(os.path.join(rom.ROOT, "scripts", "mesen", "smoke.lua"), timeout=120)
        self.assertEqual(rc, 0)
        with open(os.path.join(mesen.WORK, "shots", "smoke.png"), "rb") as f:
            self.assertEqual(f.read(8), b"\x89PNG\r\n\x1a\n")
        with open(os.path.join(mesen.WORK, "trace", "smoke.txt"), encoding="utf-8") as f:
            vals = dict(kv.split("=") for kv in f.read().split())
        self.assertGreater(int(vals["reads"]), 0)
        self.assertLess(int(vals["maxRom"]), 0x180000)
        self.assertIn(int(vals["loadedFrame"]), range(118, 124))
```

- [ ] **Step 10: Run all tests, expect PASS** — `python -I -m unittest discover -s scripts -v`. If `test_smoke` fails, read `work/run/smoke.out` and `work/lua_error.txt` first. If `removeMemoryCallback` inside its own callback crashes, keep the exec callback registered and early-return when `#jobs == 0`.

- [ ] **Step 11: Commit**

```bash
git add .gitignore scripts/rom.py scripts/test_rom.py scripts/mesen.py scripts/mesen/lib.lua scripts/mesen/smoke.lua scripts/test_mesen.py
git commit -m "Add ROM helpers and headless Mesen2 runner"
```

---

### Task 2: Route to the first dialogue

**Files:**
- Create: `scripts/mesen/goto.lua`, `scripts/mesen/routes/dialogue1.txt`, `notes/routes.md`

**Interfaces:**
- Consumes: Task 1 `L.*`, `mesen.py` CLI.
- Produces: savestate `work/states/dialogue1.mss`, paused where a dialogue line is printing. Later tasks load it with `FROM=dialogue1`. Also produces the route format and `goto.lua` params: `ROUTE` (abs path), `SAVE` (name), optional `FROM` (state name), `SHOT_EVERY` (default 60).

- [ ] **Step 1: Write** `scripts/mesen/goto.lua`

```lua
-- Play ROUTE, screenshot every SHOT_EVERY frames to shots/<SAVE>_NNNNN.png, save state <SAVE> at the end.
local every = SHOT_EVERY or 60
local function begin()
  local start, saving = L.frame, false
  L.load_route(ROUTE)
  L.on_frame(function(f)
    local n = f - start
    if n % every == 0 then L.shot(string.format("shots/%s_%05d.png", SAVE, n)) end
    if L.route_done() and not saving then
      saving = true
      L.shot("shots/" .. SAVE .. "_final.png")
      L.save_state(SAVE, function() L.finish(0) end)
    end
  end)
end
if FROM then L.load_state(FROM, begin) else begin() end
```

- [ ] **Step 2: Write the starting route** `scripts/mesen/routes/dialogue1.txt`. The probe on 2026-10-07 reached the title ("PUSH BUTTON") by about frame 900. Pressing START every 60 frames from boot reached an intro cutscene by frame 600.

```
# boot -> title screen
900 -
4 start
# title -> (menu / intro)
120 -
4 start
240 -
```

- [ ] **Step 3: Run it and look**

Run: `python -I scripts/mesen.py scripts/mesen/goto.lua ROUTE=H:/translation/nage-libre/scripts/mesen/routes/dialogue1.txt SAVE=dialogue1 SHOT_EVERY=30`
Expected: `exit 0`. Then open `work/shots/dialogue1_*.png` in order (Read tool shows images).

- [ ] **Step 4: Iterate the route until `dialogue1_final.png` shows a dialogue box mid-print or freshly printed.** Each round, append lines: `N -` to wait, `4 a` / `4 start` to press, `8 down` to move a cursor. Re-run Step 3. A new game should start a story scene soon after "Start" (guide: "There is a scene" opens Stage 1). Keep waits generous; the run is fast.
  - Fallback if 10 rounds don't get there: ask the user to play to a dialogue in the Mesen2 GUI and save a state. Copy the `.mss` from `tools/mesen2/SaveStates/` to `work/states/dialogue1.mss`. Verify it loads with an empty route: create `scripts/mesen/routes/empty.txt` containing `2 -`, run `goto.lua FROM=dialogue1 ROUTE=.../empty.txt SAVE=check`, and confirm `work/shots/check_final.png` shows the dialogue.

- [ ] **Step 5: Record** in `notes/routes.md`: the route file, frame count, what the final screenshot shows, and how to reproduce (the Step 3 command). Use the same format for every route added later.

- [ ] **Step 6: Commit**

```bash
git add scripts/mesen/goto.lua scripts/mesen/routes notes/routes.md
git commit -m "Add route player and route to first dialogue"
```

---

### Task 3: Trace the text print (font + candidate reader PCs)

**Files:**
- Create: `scripts/mesen/trace.lua`, `scripts/trace_diff.py`, `scripts/test_trace_diff.py`, `notes/text-engine.md`

**Interfaces:**
- Consumes: `work/states/dialogue1.mss`.
- Produces: `trace.lua` params `FROM`, `NAME`, `FRAMES` (default 600), `ADVANCE` (press A every N frames, 0 = never). Outputs in `work/trace/`: `<NAME>_rom.csv` and `<NAME>_wram.csv` (`pc,n,lo,hi`, hex), `<NAME>_dma.csv` (`frame,pc,ch,bbus,src,size,vmadd`). Outputs in `work/mem/`: `<NAME>_vram.bin` (64 KiB), `<NAME>_wram.bin` (128 KiB), `<NAME>_cgram.bin` (512 B). Screenshots `work/shots/<NAME>_tNNNNN.png`.
- Produces: `trace_diff.load(path) -> dict[int pc, (n, lo, hi)]`, `trace_diff.diff(base, active, ratio=4.0) -> list[(pc, n_active, n_base, lo, hi)]`. Rows are PCs absent from `base`, or with `n_active >= ratio * n_base`, sorted by pc. CLI: `python -I scripts/trace_diff.py BASE.csv ACTIVE.csv`.

- [ ] **Step 1: Write** `scripts/mesen/trace.lua`

```lua
-- Aggregate ROM reads and WRAM writes per PC, log VRAM DMAs, dump memories at the end.
local frames, adv, name = FRAMES or 600, ADVANCE or 0, NAME or FROM
local snes, T = emu.cpuType.snes, emu.callbackType
local lastPC, vmadd = 0, 0
local romBy, wramBy = {}, {}
local function bump(t, a)
  local e = t[lastPC]
  if not e then t[lastPC] = { n = 1, lo = a, hi = a }
  else e.n = e.n + 1; if a < e.lo then e.lo = a end; if a > e.hi then e.hi = a end end
end
local function writeAgg(t, rel)
  local f = assert(io.open(L.path(rel), "w")); f:write("pc,n,lo,hi\n")
  for pc, e in pairs(t) do f:write(string.format("%06X,%d,%06X,%06X\n", pc, e.n, e.lo, e.hi)) end
  f:close()
end
local function begin()
  local start = L.frame
  local dma = assert(io.open(L.path("trace/" .. name .. "_dma.csv"), "w"))
  dma:write("frame,pc,ch,bbus,src,size,vmadd\n")
  emu.addMemoryCallback(function(a) lastPC = a end, T.exec, 0, 0xFFFFFF, snes, emu.memType.snesMemory)
  emu.addMemoryCallback(function(a) bump(romBy, a) end, T.read, 0, 0x17FFFF, snes, emu.memType.snesPrgRom)
  emu.addMemoryCallback(function(a) bump(wramBy, a) end, T.write, 0, 0x1FFFF, snes, emu.memType.snesWorkRam)
  L.on_reg_write(0x2116, function(a, v) vmadd = (vmadd & 0xFF00) | v end)
  L.on_reg_write(0x2117, function(a, v) vmadd = (vmadd & 0x00FF) | (v << 8) end)
  L.on_reg_write(0x420B, function(a, v)
    local dbg = emu.memType.snesDebug
    for ch = 0, 7 do
      if v & (1 << ch) ~= 0 then
        local b = 0x4300 + ch * 16
        local bbus = emu.read(b + 1, dbg)
        local src = emu.read(b + 2, dbg) | (emu.read(b + 3, dbg) << 8) | (emu.read(b + 4, dbg) << 16)
        local size = emu.read(b + 5, dbg) | (emu.read(b + 6, dbg) << 8)
        dma:write(string.format("%d,%06X,%d,%02X,%06X,%04X,%04X\n", L.frame - start, lastPC, ch, bbus, src, size, vmadd))
      end
    end
  end)
  L.on_frame(function(f)
    local n = f - start
    if adv > 0 and n % adv == 0 then L.press("a", 2) end
    if n % 30 == 0 then L.shot(string.format("shots/%s_t%05d.png", name, n)) end
    if n == frames then
      dma:close()
      writeAgg(romBy, "trace/" .. name .. "_rom.csv")
      writeAgg(wramBy, "trace/" .. name .. "_wram.csv")
      L.dump_mem(emu.memType.snesVideoRam, 0x10000, "mem/" .. name .. "_vram.bin")
      L.dump_mem(emu.memType.snesWorkRam, 0x20000, "mem/" .. name .. "_wram.bin")
      L.dump_mem(emu.memType.snesCgRam, 0x200, "mem/" .. name .. "_cgram.bin")
      L.finish(0)
    end
  end)
end
L.load_state(FROM, begin)
```

- [ ] **Step 2: Write failing test** `scripts/test_trace_diff.py`

```python
import os, tempfile, unittest
import trace_diff

def write(rows):
    fd, p = tempfile.mkstemp(suffix=".csv")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("pc,n,lo,hi\n" + "".join(rows))
    return p

class Diff(unittest.TestCase):
    def test_new_and_grown_pcs(self):
        base = trace_diff.load(write(["808000,100,000000,000010\n", "81A000,10,010000,010004\n"]))
        act = trace_diff.load(write(["808000,110,000000,000010\n", "81A000,50,010000,010040\n",
                                     "82B000,7,0A0000,0A0006\n"]))
        self.assertEqual(trace_diff.diff(base, act),
                         [(0x81A000, 50, 10, 0x010000, 0x010040), (0x82B000, 7, 0, 0x0A0000, 0x0A0006)])
```

- [ ] **Step 3: Run, expect FAIL** (`No module named 'trace_diff'`).

- [ ] **Step 4: Implement** `scripts/trace_diff.py`

```python
"""Show PCs that are new (or much busier) in ACTIVE vs BASE per-PC aggregates.

    python -I scripts/trace_diff.py work/trace/idle_rom.csv work/trace/print_rom.csv
"""
import csv, sys


def load(path):
    with open(path, encoding="utf-8") as f:
        return {int(r["pc"], 16): (int(r["n"]), int(r["lo"], 16), int(r["hi"], 16)) for r in csv.DictReader(f)}


def diff(base, active, ratio=4.0):
    out = []
    for pc, (n, lo, hi) in sorted(active.items()):
        nb = base.get(pc, (0,))[0]
        if nb == 0 or n >= ratio * nb:
            out.append((pc, n, nb, lo, hi))
    return out


if __name__ == "__main__":
    for pc, n, nb, lo, hi in diff(load(sys.argv[1]), load(sys.argv[2])):
        print(f"{pc:06X}  n={n:<7} base={nb:<7} {lo:06X}-{hi:06X}")
```

- [ ] **Step 5: Run, expect PASS.**

- [ ] **Step 6: Capture two traces from dialogue1.** One is idle, ideally after the line finishes printing. The other advances text so new lines print.

```
python -I scripts/mesen.py scripts/mesen/trace.lua FROM=dialogue1 NAME=idle FRAMES=120 ADVANCE=0
python -I scripts/mesen.py scripts/mesen/trace.lua FROM=dialogue1 NAME=print FRAMES=600 ADVANCE=45
python -I scripts/trace_diff.py work/trace/idle_rom.csv work/trace/print_rom.csv
python -I scripts/trace_diff.py work/trace/idle_wram.csv work/trace/print_wram.csv
```
Check `work/shots/print_t*.png` to confirm text advanced. If dialogue1 is mid-print, `idle` also prints; in that case extend the route by ~300 frames (save it as `dialogue1_idle`) and use that for the idle run.

- [ ] **Step 7: Answer from the outputs, writing to `notes/text-engine.md` (sections `## Font`, `## Trace candidates`)**
  - **VRAM DMA:** in `print_dma.csv`, rows with `bbus` `18`/`19` during printing. Is `src` ROM (bank ≠ 7E/7F → font read straight from ROM; record `rom.lorom_to_pc(src)` and size) or WRAM (glyphs are composed in RAM)? `vmadd` = where glyphs land in VRAM.
  - **Font tiles:** if DMA comes from WRAM, find the PCs in the WRAM diff whose `lo-hi` covers that buffer. Their ROM reads (same PC region in the ROM diff) are the font source.
  - **Script reader candidates:** ROM-diff PCs with small `n` (tens to hundreds) and a narrow `lo-hi` span outside the font region. List each as `PC n lo-hi`.
  - **Possible compression:** WRAM-diff PCs writing a contiguous buffer while ROM reads stream. Note them.

- [ ] **Step 8: Commit**

```bash
git add scripts/mesen/trace.lua scripts/trace_diff.py scripts/test_trace_diff.py notes/text-engine.md
git commit -m "Add text tracer and trace diff; record font and reader candidates"
```

---

### Task 4: Disassembler, watcher, and the text engine write-up

**Files:**
- Create: `scripts/disasm.py`, `scripts/test_disasm.py`, `scripts/mesen/watch.lua`, `scripts/mesen/dump_mem.lua`
- Modify: `notes/text-engine.md`

**Interfaces:**
- Consumes: candidate PCs from Task 3.
- Produces: `disasm.disassemble(addr:int, length:int, a16:bool, i16:bool) -> list[str]`; each line is `"%06X  %s  ; %s" % (fastrom_addr, asm, hexbytes)`. CLI `python -I scripts/disasm.py 0x81EDDA [LEN] [--a8] [--i8]`. `a16`/`i16` = accumulator/index are 16-bit (P register M/X bit **clear**).
- `watch.lua` params: `FROM`, `NAME`, `FRAMES` (default 300), `ADVANCE` (0), `PCS` (string `"81EDDA,81EDE0"`, log reads/writes those PCs perform), `CODE_LO`/`CODE_HI` (log every executed PC in range, with registers), `WRAM_LO`/`WRAM_HI` (log WRAM writes in range), `MAX_ROWS` (default 200000). Output `work/trace/<NAME>_watch.csv`: `frame,pc,kind,addr,value,a,x,y,p,db,d` (kind `x`=exec, `r`=read, `w`=write).
- `dump_mem.lua` params: `FROM`, `NAME`, `AT_PC` (number), `MEM` (`"wram"`|`"vram"`|`"rom"`), `START`, `LEN`, `FRAMES` (default 1200), `ADVANCE` (0), `HIT` (default 1: dump on the Nth hit). Writes `work/mem/<NAME>.bin` and `work/mem/<NAME>.txt` (registers at the hit), then exits 0. If not hit within FRAMES, fails with "AT_PC not hit".

- [ ] **Step 1: Write failing test** `scripts/test_disasm.py`. Expected lines were captured from this ROM on 2026-10-07.

```python
import os, unittest
import disasm, rom

@unittest.skipUnless(os.path.exists(rom.ROM_PATH), "ROM not present")
class Disasm(unittest.TestCase):
    def test_reset_area(self):
        lines = disasm.disassemble(0x808000, 0x10, a16=False, i16=False)
        self.assertEqual(lines[0], "808000  nop  ; EA")
        self.assertEqual(lines[3], "808003  bra  -2.b  ; 80 FE")
        self.assertEqual(lines[4], "808005  rep #$30  ; C2 30")
        # after rep #$30 the accumulator is 16-bit: 3-byte immediate
        self.assertEqual(lines[10], "80800C  lda #$0000.w  ; A9 00 00")
```

- [ ] **Step 2: Run, expect FAIL.**

- [ ] **Step 3: Implement** `scripts/disasm.py`

```python
"""Disassemble ROM code with the bundled snes2asm.

    python -I scripts/disasm.py 0x81EDDA 0x80 [--a8] [--i8]

--a8/--i8: accumulator/index start 8-bit (P.M / P.X set). Default 16-bit.
"""
import contextlib, io, os, sys, types
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rom
sys.path.insert(0, os.path.join(rom.ROOT, "tools"))
from snes2asm.cartridge import Cartridge
from snes2asm.disassembler import Disassembler

_OPTS = types.SimpleNamespace(hex=True, nolabel=True, hirom=None, lorom=True, fastrom=True,
                              slowrom=None, banks=None, verbose=None, empty_fill=255)
_cart = None


def _cartridge():
    global _cart
    if _cart is None:
        _cart = Cartridge(_OPTS.__dict__)
        with contextlib.redirect_stdout(io.StringIO()):
            _cart.open(rom.ROM_PATH)
    return _cart


def disassemble(addr, length, a16=True, i16=True):
    cart = _cartridge()
    d = Disassembler(cart, _OPTS)
    d.flags = (Disassembler.OP_ACC16 if a16 else 0) | (Disassembler.OP_IND16 if i16 else 0)
    start = rom.lorom_to_pc(addr)
    d.decode(start, start + length)
    return ["%06X  %s  ; %s" % (rom.pc_to_lorom(pos), ins.code, ins.comment)
            for pos, ins in d.code.items()]


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = sys.argv[1:]
    length = int(args[1], 0) if len(args) > 1 else 0x40
    print("\n".join(disassemble(int(args[0], 0), length, "--a8" not in flags, "--i8" not in flags)))
```

- [ ] **Step 4: Run, expect PASS.** If spacing differs (snes2asm emits `bra  -2.b` with two spaces), fix the test's expected string to the observed output **only if** the mnemonic, operand and bytes match.

- [ ] **Step 5: Write** `scripts/mesen/watch.lua`

```lua
-- Raw access log with registers for selected PCs / code range / WRAM range.
local frames, adv, maxRows = FRAMES or 300, ADVANCE or 0, MAX_ROWS or 200000
local snes, T, M = emu.cpuType.snes, emu.callbackType, emu.memType
local watch = {}
for h in tostring(PCS or ""):gmatch("[^,]+") do watch[tonumber(h, 16)] = true end
local lastPC, rows, start = 0, 0, 0
local out = assert(io.open(L.path("trace/" .. NAME .. "_watch.csv"), "w"))
out:write("frame,pc,kind,addr,value,a,x,y,p,db,d\n")
local function row(kind, addr, value)
  if rows >= maxRows then return end
  rows = rows + 1
  local s = emu.getState()
  out:write(string.format("%d,%06X,%s,%06X,%04X,%04X,%04X,%04X,%02X,%02X,%04X\n", L.frame - start, lastPC, kind,
    addr, value, s["cpu.a"], s["cpu.x"], s["cpu.y"], s["cpu.ps"], s["cpu.dbr"], s["cpu.d"]))
end
local function begin()
  start = L.frame
  emu.addMemoryCallback(function(a)
    lastPC = a
    if CODE_LO and a >= CODE_LO and a <= CODE_HI then row("x", a, 0) end
  end, T.exec, 0, 0xFFFFFF, snes, M.snesMemory)
  if next(watch) then
    emu.addMemoryCallback(function(a, v) if watch[lastPC] then row("r", a, v) end end, T.read, 0, 0xFFFFFF, snes, M.snesMemory)
    emu.addMemoryCallback(function(a, v) if watch[lastPC] then row("w", a, v) end end, T.write, 0, 0xFFFFFF, snes, M.snesMemory)
  end
  if WRAM_LO then
    emu.addMemoryCallback(function(a, v) row("w", 0x7E0000 + a, v) end, T.write, WRAM_LO, WRAM_HI, snes, M.snesWorkRam)
  end
  L.on_frame(function(f)
    local n = f - start
    if adv > 0 and n % adv == 0 then L.press("a", 2) end
    if n == frames then out:close(); L.finish(0) end
  end)
end
L.load_state(FROM, begin)
```

- [ ] **Step 6: Write** `scripts/mesen/dump_mem.lua`

```lua
-- Dump MEM[START, START+LEN) on the HIT-th execution of AT_PC.
local mems = { wram = emu.memType.snesWorkRam, vram = emu.memType.snesVideoRam, rom = emu.memType.snesPrgRom }
local frames, adv, want = FRAMES or 1200, ADVANCE or 0, HIT or 1
local function begin()
  local start, hits = L.frame, 0
  emu.addMemoryCallback(L.safe(function()
    hits = hits + 1
    if hits ~= want then return end
    local t = {}
    for i = 0, LEN - 1 do t[#t + 1] = string.char(emu.read(START + i, mems[MEM])) end
    L.write_file("mem/" .. NAME .. ".bin", table.concat(t))
    local s, regs = emu.getState(), {}
    for _, k in ipairs({ "cpu.a", "cpu.x", "cpu.y", "cpu.ps", "cpu.dbr", "cpu.d", "cpu.sp" }) do
      regs[#regs + 1] = string.format("%s=%X", k, s[k])
    end
    L.write_file("mem/" .. NAME .. ".txt", table.concat(regs, " ") .. "\n")
    L.finish(0)
  end), emu.callbackType.exec, AT_PC, AT_PC, emu.cpuType.snes, emu.memType.snesMemory)
  L.on_frame(function(f)
    local n = f - start
    if adv > 0 and n % adv == 0 then L.press("a", 2) end
    if n == frames then L.fail("AT_PC not hit") end
  end)
end
L.load_state(FROM, begin)
```

- [ ] **Step 7: Find the script reader.** For each Task 3 candidate:
  ```
  python -I scripts/mesen.py scripts/mesen/watch.lua FROM=dialogue1 NAME=cand PCS=<pc1>,<pc2> FRAMES=300 ADVANCE=45
  ```
  The script reader produces `r` rows whose `addr` steps forward one or two bytes per character as text prints. Its `value` sequence is the raw script bytes. Write down the ROM range and the first ~40 bytes.

- [ ] **Step 8: Read the routine.** Run `python -I scripts/disasm.py <reader_pc - 0x40> 0x100` (use `--a8`/`--i8` per the `p` column: bit `20` set → `--a8`, bit `10` set → `--i8`). If the start is unclear, get the exact flow: `watch.lua ... CODE_LO=0x<start> CODE_HI=0x<end> FRAMES=60`. Determine and record in `notes/text-engine.md`:
  - `## Encoding`: 1 or 2 bytes per glyph? Prefix bytes for kanji pages? How is a glyph index turned into a font address (the multiply/shift before the font read)?
  - `## Control codes`: each `cmp #$xx` / jump-table entry: byte value, argument count, effect (newline, wait for button, clear box, portrait/name, choice, end, jump). Confirm effects against screenshots.
  - `## Compression`: if the reader reads WRAM rather than ROM, find what fills that WRAM buffer. Use `watch.lua WRAM_LO=.. WRAM_HI=..`, then disasm the writer, and record the source ROM address and routine. State plainly "not compressed" if bytes come straight from ROM.
  - `## Pointers`: how the reader's start address is set. Watch writes to the zero-page/WRAM pointer variable the reader dereferences (`WRAM_LO/HI` on it) and disasm the code that loads it. Record pointer table ROM offset, entry size (2 or 3 bytes), bank source, count, and what indexes it (scene id).
  - `## Font`: font ROM offset, bpp, glyph size, glyph order. Fill in from DMA/reads plus the glyph-index→address formula.

- [ ] **Step 9: Commit**

```bash
git add scripts/disasm.py scripts/test_disasm.py scripts/mesen/watch.lua scripts/mesen/dump_mem.lua notes/text-engine.md
git commit -m "Add disassembler wrapper, watcher, memory dumper; document text engine"
```

---

### Task 5: Render the font sheet

**Files:**
- Create: `scripts/render_font.py`, `scripts/test_render_font.py`, `font/jp_font*.png`

**Interfaces:**
- Consumes: font offset/format from `notes/text-engine.md ## Font`.
- Produces: `render_font.decode_tile(data:bytes, off:int, bpp:int) -> list[list[int]]` (8×8 palette indices); `render_font.glyph(data, off, index, bpp, size, layout) -> list[list[int]]` (size 8 or 16; layout `"seq"` = 16×16 glyph is 4 consecutive tiles TL,TR,BL,BR; `"vram"` = tiles n, n+1, n+16, n+17 with glyph i at tile `(i//8)*32 + (i%8)*2`); `render_font.write_png(path, rgb_rows:list[bytes])`; CLI below. Sheet: 16 glyphs per row, 1-px red grid, each row labelled on the left with its first code in hex (tiny built-in 3×5 hex digits), scaled ×`--scale`.

- [ ] **Step 1: Write failing tests** `scripts/test_render_font.py`

```python
import os, struct, tempfile, unittest, zlib
import render_font as rf

class Tiles(unittest.TestCase):
    def test_2bpp_planes(self):
        t = bytes([0x80, 0x80] + [0] * 14)            # row 0: plane0 bit7, plane1 bit7
        px = rf.decode_tile(t, 0, 2)
        self.assertEqual(px[0][0], 3)
        self.assertEqual(px[0][1], 0)

    def test_4bpp_high_planes_at_16(self):
        t = bytearray(32); t[16] = 0x80               # plane2, row 0, pixel 0
        self.assertEqual(rf.decode_tile(bytes(t), 0, 4)[0][0], 4)

    def test_1bpp(self):
        t = bytes([0x01] + [0] * 7)
        self.assertEqual(rf.decode_tile(t, 0, 1)[0][7], 1)

    def test_16x16_seq_vs_vram(self):
        # tile k: plane0 all set when k is odd -> pixel value k % 2
        data = b"".join(bytes([0xFF if k % 2 else 0x00, 0] * 8) for k in range(18))
        seq = rf.glyph(data, 0, 0, 2, 16, "seq")      # tiles 0,1,2,3
        vram = rf.glyph(data, 0, 0, 2, 16, "vram")    # tiles 0,1,16,17
        self.assertEqual((seq[0][0], seq[0][8], seq[8][0], seq[8][8]), (0, 1, 0, 1))
        self.assertEqual((vram[8][0], vram[8][8]), (0, 1))

    def test_png_is_valid(self):
        fd, p = tempfile.mkstemp(suffix=".png"); os.close(fd)
        rf.write_png(p, [bytes([255, 0, 0, 0, 255, 0])] * 3)   # 2x3 px
        with open(p, "rb") as f:
            raw = f.read()
        self.assertEqual(raw[:8], b"\x89PNG\r\n\x1a\n")
        w, h = struct.unpack(">II", raw[16:24])
        self.assertEqual((w, h), (2, 3))
        idat = raw[raw.index(b"IDAT") + 4: raw.index(b"IEND") - 8]
        self.assertEqual(len(zlib.decompress(idat)), 3 * (1 + 6))
```

- [ ] **Step 2: Run, expect FAIL.**

- [ ] **Step 3: Implement** `scripts/render_font.py`

```python
"""Render SNES planar tiles as a labelled PNG sheet.

    python -I scripts/render_font.py SRC OFFSET COUNT --bpp 2 --size 16 --layout seq
           --base 0x00 --scale 3 -o font/jp_font.png
SRC is any binary (ROM or work/mem/*_vram.bin). OFFSET/COUNT accept 0x.. .
"""
import argparse, os, struct, sys, zlib

TILE_BYTES = {1: 8, 2: 16, 4: 32}
# 3x5 hex digits, rows top->bottom, 3 bits each
DIGITS = {c: rows for c, rows in zip("0123456789ABCDEF", [
    (7, 5, 5, 5, 7), (2, 6, 2, 2, 7), (7, 1, 7, 4, 7), (7, 1, 7, 1, 7), (5, 5, 7, 1, 1), (7, 4, 7, 1, 7),
    (7, 4, 7, 5, 7), (7, 1, 1, 1, 1), (7, 5, 7, 5, 7), (7, 5, 7, 1, 7), (7, 5, 7, 5, 5), (6, 5, 6, 5, 6),
    (7, 4, 4, 4, 7), (6, 5, 5, 5, 6), (7, 4, 6, 4, 7), (7, 4, 6, 4, 4)])}


def decode_tile(data, off, bpp):
    px = [[0] * 8 for _ in range(8)]
    for y in range(8):
        for plane in range(bpp):
            if bpp == 1:
                b = data[off + y]
            else:
                b = data[off + (plane // 2) * 16 + y * 2 + (plane % 2)]
            for x in range(8):
                if b & (0x80 >> x):
                    px[y][x] |= 1 << plane
    return px


def glyph(data, off, index, bpp, size, layout):
    tb = TILE_BYTES[bpp]
    if size == 8:
        return decode_tile(data, off + index * tb, bpp)
    if layout == "seq":
        tiles = [index * 4 + k for k in range(4)]
    else:
        t0 = (index // 8) * 32 + (index % 8) * 2
        tiles = [t0, t0 + 1, t0 + 16, t0 + 17]
    q = [decode_tile(data, off + t * tb, bpp) for t in tiles]
    return [q[0][y] + q[1][y] for y in range(8)] + [q[2][y] + q[3][y] for y in range(8)]


def write_png(path, rgb_rows):
    w, h = len(rgb_rows[0]) // 3, len(rgb_rows)
    def chunk(tag, body):
        return struct.pack(">I", len(body)) + tag + body + struct.pack(">I", zlib.crc32(tag + body))
    raw = b"".join(b"\x00" + bytes(r) for r in rgb_rows)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def render(data, off, count, bpp, size, layout, base, scale):
    per_row, cell, label_w = 16, size + 1, 4 * 4 + 2           # 4 hex digits of 3px + gaps
    rows = (count + per_row - 1) // per_row
    W, H = label_w + per_row * cell + 1, max(rows * cell + 1, 6)
    img = [[(0, 0, 0)] * W for _ in range(H)]
    maxv = (1 << bpp) - 1
    for r in range(rows):
        y0 = r * cell
        for i, ch in enumerate("%04X" % (base + r * per_row)):
            for dy, bits in enumerate(DIGITS[ch]):
                for dx in range(3):
                    if bits & (4 >> dx) and y0 + 1 + dy < H:
                        img[y0 + 1 + dy][i * 4 + dx] = (255, 255, 0)
        for c in range(per_row):
            idx = r * per_row + c
            if idx >= count:
                break
            g = glyph(data, off, idx, bpp, size, layout)
            for y in range(size):
                for x in range(size):
                    v = g[y][x] * 255 // maxv
                    img[y0 + 1 + y][label_w + c * cell + 1 + x] = (v, v, v)
    for y in range(H):
        for x in range(label_w, W):
            if y % cell == 0 or (x - label_w) % cell == 0:
                img[y][x] = (160, 0, 0)
    out = []
    for row in img:
        line = bytearray()
        for p in row:
            line += bytes(p) * scale
        out += [bytes(line)] * scale
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("offset"); ap.add_argument("count")
    ap.add_argument("--bpp", type=int, default=2, choices=(1, 2, 4))
    ap.add_argument("--size", type=int, default=16, choices=(8, 16))
    ap.add_argument("--layout", default="seq", choices=("seq", "vram"))
    ap.add_argument("--base", default="0")
    ap.add_argument("--scale", type=int, default=3)
    ap.add_argument("-o", required=True)
    a = ap.parse_args()
    with open(a.src, "rb") as f:
        data = f.read()
    write_png(a.o, render(data, int(a.offset, 0), int(a.count, 0), a.bpp, a.size, a.layout, int(a.base, 0), a.scale))
```

- [ ] **Step 4: Run, expect PASS.**

- [ ] **Step 5: Render the real font** using the values from `## Font`, 256 glyphs per sheet (`font/jp_font_00.png`, `_01`, …), `--base` = the code of the first glyph in each sheet. Open each sheet. Characters must look upright and unscrambled. If they look shuffled in quarters, switch `--layout`; if noisy, try another `--bpp`. Record the working command in `notes/text-engine.md ## Font`.

- [ ] **Step 6: Commit**

```bash
git add scripts/render_font.py scripts/test_render_font.py font/
git commit -m "Add font sheet renderer and render JP font"
```

---

### Task 5b (only if `## Compression` found compression): Decompressor

**Files:**
- Create: `scripts/decompress.py`, `scripts/test_decompress.py`

**Interfaces:**
- Produces: `decompress.decompress(rom:bytes, off:int) -> tuple[bytes, int]`, returning (output, compressed bytes consumed).

The algorithm is unknown until Task 4. This task fixes the **contract and test**; the body is a line-by-line Python transcription of the 65816 routine documented in `## Compression`.

- [ ] **Step 1: Capture ground truth.** Use `dump_mem.lua` to dump the decompressor's output buffer when the routine returns (`AT_PC` = its final `rts`/`rtl`, `MEM=wram`, `START`/`LEN` = buffer), for 3 different texts. Also record the source offset from registers/pointer vars:
  ```
  python -I scripts/mesen.py scripts/mesen/dump_mem.lua FROM=dialogue1 NAME=decomp1 AT_PC=0x<rtl> MEM=wram START=0x<buf> LEN=0x<len>
  ```
  Write `work/mem/decomp_cases.json`: `[{"name": "decomp1", "src": "0x<rom offset>"}, ...]`.

- [ ] **Step 2: Write the test** `scripts/test_decompress.py`

```python
import json, os, unittest
import decompress, rom, mesen

CASES = os.path.join(mesen.WORK, "mem", "decomp_cases.json")

@unittest.skipUnless(os.path.exists(CASES), "no captured decompression cases")
class Decompress(unittest.TestCase):
    def test_matches_game(self):
        data = rom.load()
        with open(CASES, encoding="utf-8") as f:
            cases = json.load(f)
        for c in cases:
            with open(os.path.join(mesen.WORK, "mem", c["name"] + ".bin"), "rb") as f:
                want = f.read()
            got, used = decompress.decompress(data, int(c["src"], 16))
            self.assertEqual(got[:len(want)], want, c["name"])
            self.assertGreater(used, 0)
```

- [ ] **Step 3: Run, expect FAIL.**
- [ ] **Step 4: Transcribe the routine** into `decompress()`, with a comment per block naming the 65816 address it mirrors.
- [ ] **Step 5: Run, expect PASS.**
- [ ] **Step 6: Commit** — `git add scripts/decompress.py scripts/test_decompress.py && git commit -m "Add text decompressor"`

If text is not compressed, skip this task and write "Task 5b skipped: not compressed" in `notes/text-engine.md`.

---

### Task 6: Table library

**Files:**
- Create: `scripts/tbl.py`, `scripts/test_tbl.py`, `nage.tbl` (control codes only for now)

**Interfaces:**
- Produces: `tbl.Table.parse(text:str) -> Table`, `tbl.Table.load(path) -> Table`, `Table.decode(data:bytes, start:int=0, end:int|None=None, stop_at_end:bool=True) -> tuple[str, int]` (text, offset after last consumed byte), `Table.encode(text:str) -> bytes` (ignores `\n`), `Table.duplicates -> list[tuple[str, list[str]]]`, `Table.break_tags` (set of tag names a newline follows in dumps: the tag names of any line marked with a trailing `/`, e.g. `F0=<NL>/`). CLI `python -I scripts/tbl.py --check nage.tbl` prints duplicates and malformed lines, exit 1 on malformed.

- [ ] **Step 1: Write failing tests** `scripts/test_tbl.py`

```python
import unittest
from tbl import Table

T = Table.parse("""# test table
00=あ
01=い
8140=亜
8141=亜
02=ます
F0=<NL>/
F2=<PORTRAIT:1>
FF=<END>!
""")

class Decode(unittest.TestCase):
    def test_basic_and_multibyte(self):
        self.assertEqual(T.decode(bytes([0x00, 0x81, 0x40, 0x01, 0xFF])), ("あ亜い<END>", 5))

    def test_stops_at_terminator(self):
        self.assertEqual(T.decode(bytes([0x00, 0xFF, 0x01])), ("あ<END>", 2))

    def test_arg_equal_to_terminator(self):
        self.assertEqual(T.decode(bytes([0xF2, 0xFF, 0x00, 0xFF])), ("<PORTRAIT:FF>あ<END>", 4))

    def test_unmapped_roundtrip(self):
        text, _ = T.decode(bytes([0x00, 0x77, 0xFF]))
        self.assertEqual(text, "あ<$77><END>")
        self.assertEqual(T.encode(text), bytes([0x00, 0x77, 0xFF]))

    def test_duplicate_glyph_roundtrip(self):
        raw = bytes([0x81, 0x40, 0x81, 0x41, 0xFF])
        text, _ = T.decode(raw)
        self.assertEqual(text, "亜<$8141><END>")
        self.assertEqual(T.encode(text), raw)
        self.assertEqual(T.duplicates, [("亜", ["8140", "8141"])])

    def test_no_stop(self):
        self.assertEqual(T.decode(bytes([0xFF, 0x00]), stop_at_end=False), ("<END>あ", 2))

    def test_end_bound(self):
        self.assertEqual(T.decode(bytes([0x00, 0x01, 0x00]), end=2, stop_at_end=False), ("あい", 2))

class Encode(unittest.TestCase):
    def test_longest_text_match_and_newlines_ignored(self):
        self.assertEqual(T.encode("ます<NL>\nあ<END>"), bytes([0x02, 0xF0, 0x00, 0xFF]))

    def test_tag_with_args(self):
        self.assertEqual(T.encode("<PORTRAIT:03>"), bytes([0xF2, 0x03]))

    def test_unknown_char_raises(self):
        with self.assertRaises(ValueError):
            T.encode("X")

    def test_break_tags(self):
        self.assertEqual(T.break_tags, {"NL"})
```

- [ ] **Step 2: Run, expect FAIL.**

- [ ] **Step 3: Implement** `scripts/tbl.py`

```python
"""Table file: HEX=text. Tags <NAME>, <NAME:n> (n arg bytes), trailing ! = terminator,
trailing / = dump inserts a newline after it. Unmapped bytes -> <$XX>."""
import os, re, sys

_TAG = re.compile(r"^<([A-Za-z0-9_]+)(?::(\d+))?>([!/]*)$")


class Table:
    def __init__(self):
        self.dec = {}        # bytes -> (text or tag name, nargs, is_end, is_tag)
        self.enc_text = {}   # text -> bytes (first definition wins)
        self.enc_tag = {}    # tag name -> (bytes, nargs)
        self.ends, self.break_tags = set(), set()
        self.duplicates, self.errors = [], []
        self.maxlen = 1

    @classmethod
    def load(cls, path):
        with open(path, encoding="utf-8") as f:
            return cls.parse(f.read())

    @classmethod
    def parse(cls, text):
        t, seen = cls(), {}
        for n, line in enumerate(text.splitlines(), 1):
            if not line.strip() or line.startswith("#"):
                continue
            if "=" not in line:
                t.errors.append(f"line {n}: no '='")
                continue
            hexpart, val = line.split("=", 1)
            try:
                code = bytes.fromhex(hexpart.strip())
            except ValueError:
                t.errors.append(f"line {n}: bad hex {hexpart!r}")
                continue
            t.maxlen = max(t.maxlen, len(code))
            m = _TAG.match(val)
            if m:
                name, nargs, flags = m.group(1), int(m.group(2) or 0), m.group(3)
                t.dec[code] = (name, nargs, "!" in flags, True)
                t.enc_tag.setdefault(name, (code, nargs))
                if "/" in flags:
                    t.break_tags.add(name)
            else:
                t.dec[code] = (val, 0, False, False)
                t.enc_text.setdefault(val, code)
                seen.setdefault(val, []).append(code.hex().upper())
        t.duplicates = [(v, codes) for v, codes in seen.items() if len(codes) > 1]
        return t

    def _render(self, code, args):
        text, nargs, _, is_tag = self.dec[code]
        if is_tag and self.enc_tag[text][0] == code:
            return f"<{text}:{args.hex().upper()}>" if nargs else f"<{text}>"
        if not is_tag and self.enc_text.get(text) == code:
            return text
        return f"<${code.hex().upper()}>"           # tag alias or duplicate glyph: keep raw

    def decode(self, data, start=0, end=None, stop_at_end=True):
        end = len(data) if end is None else end
        pos, out = start, []
        while pos < end:
            for ln in range(min(self.maxlen, end - pos), 0, -1):
                code = bytes(data[pos:pos + ln])
                if code in self.dec:
                    break
            else:
                out.append(f"<${data[pos]:02X}>")
                pos += 1
                continue
            _, nargs, is_end, _ = self.dec[code]
            args = bytes(data[pos + ln:pos + ln + nargs])
            out.append(self._render(code, args))
            pos += ln + nargs
            if is_end and stop_at_end:
                break
        return "".join(out), pos

    def encode(self, text):
        out, i = bytearray(), 0
        text = text.replace("\n", "")
        longest = max((len(k) for k in self.enc_text), default=1)
        while i < len(text):
            if text[i] == "<":
                j = text.index(">", i)
                tok = text[i + 1:j]
                if tok.startswith("$"):
                    out += bytes.fromhex(tok[1:])
                else:
                    name, _, args = tok.partition(":")
                    if name not in self.enc_tag:
                        raise ValueError(f"unknown tag <{tok}> at {i}")
                    code, nargs = self.enc_tag[name]
                    a = bytes.fromhex(args) if args else b""
                    if len(a) != nargs:
                        raise ValueError(f"<{tok}> needs {nargs} arg bytes at {i}")
                    out += code + a
                i = j + 1
                continue
            for ln in range(min(longest, len(text) - i), 0, -1):
                if text[i:i + ln] in self.enc_text:
                    out += self.enc_text[text[i:i + ln]]
                    i += ln
                    break
            else:
                raise ValueError(f"no table entry for {text[i]!r} at {i}")
        return bytes(out)


if __name__ == "__main__":
    t = Table.load(sys.argv[-1])
    for v, codes in t.duplicates:
        print(f"duplicate {v!r}: {' '.join(codes)} (later codes dump as <$XX>)")
    for e in t.errors:
        print("ERROR", e)
    sys.exit(1 if t.errors else 0)
```

- [ ] **Step 4: Run, expect PASS.** Fix the implementation, not the tests.

- [ ] **Step 5: Create `nage.tbl`** holding just the control codes from `notes/text-engine.md ## Control codes`, in this format. Names are uppercase; use `!` on terminators and `/` on line or page breaks.
```
# Nage Libre table — control codes (from notes/text-engine.md)
<code>=<NL>/
<code>=<END>!
```
Run `python -I scripts/tbl.py --check nage.tbl` → exit 0.

- [ ] **Step 6: Commit** — `git add scripts/tbl.py scripts/test_tbl.py nage.tbl && git commit -m "Add table library and control codes"`

---

### Task 7: Transcribe glyphs into `nage.tbl`

**Files:**
- Modify: `nage.tbl`, `notes/text-engine.md`

**Interfaces:**
- Consumes: `font/jp_font_*.png`, Task 4 watched script bytes (`work/trace/cand_watch.csv`), Task 6 `Table`.
- Produces: complete glyph mapping.

- [ ] **Step 1: Map kana and punctuation.** Read each sheet row by row (row label = first code in the row; column = +0..F). Write one `HEX=char` line per glyph, using the code bytes from the `## Encoding` formula (prefix byte for 2-byte codes). Use full-width forms the font draws: `、。「」！？…ー`. Glyph code order often follows the standard kana order; confirm every row against the image instead of assuming the pattern.

- [ ] **Step 2: Map kanji.** Same procedure, row by row. Keep scale ≥3 and zoom by re-rendering a sub-range with `--scale 6`. Mark any glyph you can't identify confidently as `HEX=〓` plus a `# ?` comment, and list it in `notes/text-engine.md ## Uncertain glyphs` with its code.

- [ ] **Step 3: Check the table** — `python -I scripts/tbl.py --check nage.tbl`: exit 0. Real duplicate glyphs are fine; they dump as raw codes.

- [ ] **Step 4: Verify against the game.** Decode the raw bytes from Task 4 Step 7:
  ```
  python -I -c "import sys; sys.path.insert(0,'scripts'); import tbl, rom; t=tbl.Table.load('nage.tbl'); d=rom.load(); print(t.decode(d, 0x<script offset>)[0])"
  ```
  Compare with `work/shots/print_t*.png`. Every character must match. Fix the table entries that don't.

- [ ] **Step 5: Commit** — `git add nage.tbl notes/text-engine.md && git commit -m "Transcribe font into table"`

---

### Task 8: Dumper

**Files:**
- Create: `scripts/dump.py`, `scripts/test_dump.py`, `scripts/textmap.json`

**Interfaces:**
- Consumes: `tbl.Table`, `rom.lorom_to_pc`, (if exists) `decompress.decompress`.
- Produces:
  - `scripts/textmap.json`: `{"blocks": [ {"name": str, "kind": "ptr16"|"ptr24"|"fixed", ...} ]}`. Per kind: `ptr16` → `table` (file offset hex str), `count`, `bank` (LoROM bank byte hex str, e.g. `"0x95"`); `ptr24` → `table`, `count`; `fixed` → `start`, `count`, `size` (records without terminators).
  - `dump.Entry` (dataclass: `block:str, index:int, offset:int|None, length:int, text:str, alias:int|None`).
  - `dump.extract(data:bytes, table:Table, block:dict) -> list[Entry]`.
  - `dump.format_block(entries, table) -> str`, `dump.parse_block(text:str) -> list[Entry]`.
  - `dump.gaps(entries) -> list[tuple[int,int]]` (uncovered byte ranges between consecutive non-alias messages, sorted).
  - CLI: `python -I scripts/dump.py` writes `script/jp/<block>.txt` for every block and prints gaps per block.

- [ ] **Step 1: Write failing tests** `scripts/test_dump.py`

```python
import os, tempfile, unittest
import dump
from tbl import Table

T = Table.parse("00=あ\n01=い\nF0=<NL>/\nFF=<END>!\n")

def rom_with(table_off, ptrs, blob_off, blob, size=0x200):
    d = bytearray(size)
    for i, p in enumerate(ptrs):
        d[table_off + i * 2: table_off + i * 2 + 2] = p.to_bytes(2, "little")
    d[blob_off:blob_off + len(blob)] = blob
    return bytes(d)

# bank $80: CPU $808000 + x == file offset x
BLOCK = {"name": "t", "kind": "ptr16", "table": "0x0", "count": 3, "bank": "0x80"}

class Extract(unittest.TestCase):
    def setUp(self):
        blob = bytes([0x00, 0xF0, 0x01, 0xFF, 0x01, 0xFF])          # msg A at 0x100, msg B at 0x104
        self.data = rom_with(0, [0x8100, 0x8104, 0x8100], 0x100, blob)

    def test_ptr16(self):
        e = dump.extract(self.data, T, BLOCK)
        self.assertEqual((e[0].offset, e[0].length, e[0].text), (0x100, 4, "あ<NL>い<END>"))
        self.assertEqual((e[1].offset, e[1].text), (0x104, "い<END>"))

    def test_alias_pointer(self):
        e = dump.extract(self.data, T, BLOCK)
        self.assertEqual(e[2].alias, 0)
        back = dump.parse_block(dump.format_block(e, T))
        self.assertEqual([(x.index, x.offset, x.length, x.text, x.alias) for x in back],
                         [(x.index, x.offset, x.length, x.text, x.alias) for x in e])

    def test_format_breaks_lines(self):
        s = dump.format_block(dump.extract(self.data, T, BLOCK), T)
        self.assertIn("## t 0000 @000100 len=4\nあ<NL>\nい<END>\n", s)
        self.assertIn("## t 0002 =0000\n", s)

    def test_fixed(self):
        d = bytes([0x00, 0x01, 0x01, 0x00])
        e = dump.extract(d, T, {"name": "f", "kind": "fixed", "start": "0x0", "count": 2, "size": 2})
        self.assertEqual([x.text for x in e], ["あい", "いあ"])

    def test_gaps(self):
        data = rom_with(0, [0x8100, 0x8108], 0x100, bytes([0x00, 0xFF, 0, 0, 0, 0, 0, 0, 0x01, 0xFF]))
        e = dump.extract(data, T, dict(BLOCK, count=2))
        self.assertEqual(dump.gaps(e), [(0x102, 0x108)])

    def test_utf8_roundtrip_file(self):
        s = dump.format_block(dump.extract(self.data, T, BLOCK), T)
        fd, p = tempfile.mkstemp(suffix=".txt"); os.close(fd)
        dump.write_text(p, s)
        self.assertEqual(dump.read_text(p), s)
```

- [ ] **Step 2: Run, expect FAIL.**

- [ ] **Step 3: Implement** `scripts/dump.py`

```python
"""Dump script blocks listed in scripts/textmap.json to script/jp/<block>.txt."""
import json, os, re, sys
from dataclasses import dataclass
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rom
from tbl import Table

MAP = os.path.join(rom.ROOT, "scripts", "textmap.json")
TBL = os.path.join(rom.ROOT, "nage.tbl")
OUT = os.path.join(rom.ROOT, "script", "jp")
_HEAD = re.compile(r"^## (\S+) (\d+) (?:@([0-9A-F]+) len=(\d+)|=(\d+))$")


@dataclass
class Entry:
    block: str
    index: int
    offset: int | None
    length: int
    text: str
    alias: int | None = None


def write_text(path, s):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(s)


def read_text(path):
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def _pointers(data, b):
    tab, n = int(b["table"], 16), b["count"]
    if b["kind"] == "ptr16":
        bank = int(b["bank"], 16) << 16
        return [rom.lorom_to_pc(bank | int.from_bytes(data[tab + 2 * i: tab + 2 * i + 2], "little")) for i in range(n)]
    return [rom.lorom_to_pc(int.from_bytes(data[tab + 3 * i: tab + 3 * i + 3], "little")) for i in range(n)]


def extract(data, table, b):
    if b["kind"] == "fixed":
        start, size = int(b["start"], 16), b["size"]
        return [Entry(b["name"], i, start + i * size, size,
                      table.decode(data, start + i * size, start + (i + 1) * size, stop_at_end=False)[0])
                for i in range(b["count"])]
    out, first = [], {}
    for i, off in enumerate(_pointers(data, b)):
        if off in first:
            out.append(Entry(b["name"], i, None, 0, "", alias=first[off]))
            continue
        first[off] = i
        text, end = table.decode(data, off)
        out.append(Entry(b["name"], i, off, end - off, text))
    return out


def format_block(entries, table):
    parts = []
    for e in entries:
        if e.alias is not None:
            parts.append(f"## {e.block} {e.index:04d} ={e.alias:04d}\n")
            continue
        text = e.text
        for tag in table.break_tags:
            text = re.sub(r"(<%s(?::[0-9A-F]+)?>)" % tag, r"\1\n", text)
        parts.append(f"## {e.block} {e.index:04d} @{e.offset:06X} len={e.length}\n{text.rstrip(chr(10))}\n")
    return "\n".join(parts)


def parse_block(s):
    out = []
    for chunk in re.split(r"\n(?=## )", s.strip("\n")):
        head, _, body = chunk.partition("\n")
        m = _HEAD.match(head)
        if not m:
            raise ValueError(f"bad header: {head!r}")
        name, idx = m.group(1), int(m.group(2))
        if m.group(5) is not None:
            out.append(Entry(name, idx, None, 0, "", alias=int(m.group(5))))
        else:
            out.append(Entry(name, idx, int(m.group(3), 16), int(m.group(4)), body.replace("\n", "")))
    return out


def gaps(entries):
    spans = sorted({(e.offset, e.offset + e.length) for e in entries if e.alias is None})
    out, end = [], None
    for s, e in spans:
        if end is not None and s > end:
            out.append((end, s))
        end = e if end is None else max(end, e)
    return out


if __name__ == "__main__":
    data, table = rom.load(), Table.load(TBL)
    with open(MAP, encoding="utf-8") as f:
        blocks = json.load(f)["blocks"]
    os.makedirs(OUT, exist_ok=True)
    for b in blocks:
        entries = extract(data, table, b)
        write_text(os.path.join(OUT, b["name"] + ".txt"), format_block(entries, table))
        g = gaps(entries) if b["kind"] != "fixed" else []
        unk = sum(e.text.count("<$") for e in entries)
        print(f"{b['name']}: {len(entries)} entries, {unk} raw codes, gaps: "
              + (", ".join(f"{s:06X}-{e:06X}" for s, e in g) or "none"))
```

- [ ] **Step 4: Run, expect PASS.**

- [ ] **Step 5: Fill** `scripts/textmap.json` with the dialogue pointer table(s) from `## Pointers`, run `python -I scripts/dump.py`, and open `script/jp/<block>.txt`. Text should read as Japanese with `<NL>` line breaks. For each reported gap, decode it with `tbl.decode(..., stop_at_end=False)`. If it is text, there's another pointer table or an unreferenced string: record it in `notes/text-engine.md ## Gaps` with the outcome.
  - If text is compressed (Task 5b): add `"compressed": true` to the block, and in `extract` decode `decompress.decompress(data, off)[0]` instead of `data` at `off`. Add a test with a one-entry fake decompressor passed in. Do that before touching `extract`.

- [ ] **Step 6: Commit** — `git add scripts/dump.py scripts/test_dump.py scripts/textmap.json script/jp && git commit -m "Add script dumper and dump dialogue"`

---

### Task 9: Non-dialogue text inventory

**Files:**
- Create: `scripts/mesen/routes/*.txt` (menu routes), `notes/text-inventory.md`
- Modify: `scripts/textmap.json`, `nage.tbl` (if menus use other codes), `notes/routes.md`, `script/jp/*`

**Interfaces:**
- Consumes: Tasks 2–8 tools.
- Produces: `notes/text-inventory.md`: a table with one row per text category, columns `Category | Screen | Storage (script block / graphics) | ROM location | Size | Notes`, plus every script-stored category added to `textmap.json`.

- [ ] **Step 1: Route to each screen.** Use `goto.lua` with `FROM=dialogue1` or a later state, saving states `title_menu`, `shop`, `club`, `battle_menu`, `battle_msg`, `save_screen`, `name_or_status` (whatever the game has). Guide context: after a stage, "What do you want?" → Shopping / Club Activities / Save / Start. Battle commands: Stand by, Attack, Item, Exchange, Pocketbell, Anime, Save. Cards: ATK DEF HP ESC SP CHG COS ???. Record each route in `notes/routes.md`.

- [ ] **Step 2: Classify each screen.** Run `trace.lua` on the state (`ADVANCE=0`, `FRAMES=60`), then render the screen's VRAM: `render_font.py work/mem/<name>_vram.bin 0x<vmadd*2> 256 --bpp <bpp> --size 8`. Text that appears as **whole words in VRAM** before any text routine runs is *graphics-baked*: record its VRAM tile region and the DMA `src` from `<name>_dma.csv` as its ROM location. Text drawn glyph-by-glyph through the Task 4 reader (or a second reader; use `trace_diff` against `idle`) is *script*: find its table/strings with `watch.lua` as in Task 4.

- [ ] **Step 3: Add script categories** to `textmap.json` (`fixed` for fixed-width name lists, `ptr16`/`ptr24` otherwise). Run `python -I scripts/dump.py`. Fix new codes in `nage.tbl` (menu fonts sometimes use a separate 8×8 font with its own codes. If so, give that block its own table file `nage_menu.tbl` and add `"tbl": "nage_menu.tbl"` to the block. `dump.py` main loads `Table.load(os.path.join(rom.ROOT, b.get("tbl", "nage.tbl")))` per block. Make that change with a test in `test_dump.py` first).

- [ ] **Step 4: Write `notes/text-inventory.md`** covering at least: dialogue, choice prompts, shop, club activities, card names, item names, battle commands, battle messages, character names, save/load screen, title screen, credits (via the guide's ending; if reaching it by route is impractical, find the credits by searching the ROM with the table: `python -I -c "...t.encode('<a known credits word>')..."` then `data.find(...)`).

- [ ] **Step 5: Commit** — `git add scripts/mesen/routes notes scripts/textmap.json nage.tbl script/jp && git commit -m "Inventory non-dialogue text and dump menus"`

---

### Task 10: Round-trip, spot check, coverage

**Files:**
- Create: `scripts/test_roundtrip.py`
- Modify: `notes/text-engine.md`

**Interfaces:**
- Consumes: `script/jp/*.txt`, `textmap.json`, `nage.tbl`, `dump.parse_block`, `dump.read_text`, `tbl.Table`.

- [ ] **Step 1: Write** `scripts/test_roundtrip.py`

```python
import glob, json, os, unittest
import dump, rom
from tbl import Table

@unittest.skipUnless(os.path.exists(rom.ROM_PATH) and glob.glob(os.path.join(dump.OUT, "*.txt")), "no ROM or dump")
class RoundTrip(unittest.TestCase):
    def test_every_message_reencodes_identically(self):
        data = rom.load()
        with open(dump.MAP, encoding="utf-8") as f:
            blocks = {b["name"]: b for b in json.load(f)["blocks"]}
        failures, count = [], 0
        for path in sorted(glob.glob(os.path.join(dump.OUT, "*.txt"))):
            name = os.path.splitext(os.path.basename(path))[0]
            table = Table.load(os.path.join(rom.ROOT, blocks[name].get("tbl", "nage.tbl")))
            for e in dump.parse_block(dump.read_text(path)):
                if e.alias is not None:
                    continue
                count += 1
                if table.encode(e.text) != data[e.offset:e.offset + e.length]:
                    failures.append(f"{name} {e.index:04d} @{e.offset:06X}")
        self.assertGreater(count, 0)
        self.assertEqual(failures, [], f"{len(failures)}/{count} messages differ")
```
(For compressed blocks, compare against `decompress.decompress(data, e.offset)[0][:e.length]` instead. Branch on `blocks[name].get("compressed")`.)

- [ ] **Step 2: Run** `python -I -m unittest discover -s scripts -v`. Everything must PASS. Fix the table or dumper on failures; never edit the dumped text by hand to make it pass.

- [ ] **Step 3: Spot check 3 scenes.** For `dialogue1` and two later scenes (route to them, or reach Stage 2/3 openings with `goto.lua`), compare screenshots to the matching entries in `script/jp`. Record in `notes/text-engine.md ## Spot checks`: scene, block/index, match yes/no.

- [ ] **Step 4: Coverage.** In `notes/text-engine.md ## Coverage`, record per block: entry count, raw `<$XX>` count with reasons (the dump CLI prints them), and gaps with their outcomes. Also list any categories from `text-inventory.md` not yet dumped, with the reason (e.g. graphics-baked → sub-project 4).

- [ ] **Step 5: Commit** — `git add scripts/test_roundtrip.py notes script/jp && git commit -m "Verify round-trip and record coverage"`
