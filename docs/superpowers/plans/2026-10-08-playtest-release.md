# Scripted Playtest and Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Visually verify every scene's English by forcing each scene in the emulator (English vs Japanese reference), fix what the tour finds, try to reach the deeper menus, and package the release.

**Architecture:**
- `scene_hook.lua` overrides the scene loader's A register.
- `tour.py` drives Mesen per scene and per ROM, keeps the frames where text changed, and writes EN|JP strips.
- `shots.py` holds the PNG helpers.
- `release.py` builds the release folder.

Issues go to `notes/playtest.md`; fixes go through `script/en` / `gfx/edits.json` and the existing build.

**Tech Stack:** Python 3.12 stdlib, unittest, Mesen2 headless (`scripts/mesen.py`), existing `build` / `bps` / `accept` / `coverage`.

**Spec:** `docs/superpowers/specs/2026-10-08-playtest-release-design.md`

## Global Constraints

- `python -I`; tests: `python -I -m unittest discover -s scripts`. Use Write/Edit (not heredocs) for Python containing `\n` / `\x` literals.
- Scenes are numbered `0x00-0x14C`; resource = scene + `0x30F`; file `script/jp/scene_{scene+0x30F:03X}.txt`.
- Japanese reference ROM: clean ROM + `build.english_patches(clean)` (2b font only), written via `accept.write_rom`.
- Staff credits stay in kanji. Nothing is uploaded or published; `release/` is local only (gitignored).
- Long emulator runs go in background shells, in batches of about 40 scenes per command.

## Review Focus

1. **Context artifacts vs real bugs:** a garbage box that appears on both ROMs is an artifact, not a translation bug. Only EN-only defects get fixed. Covered by the paired strips in Task 2 and the cause column in Task 4.
2. **Op-13 member variants:** forced scenes run with the stage-1 party (Yui, Ryoko), so other members' variants are not shown. Record this as a known limit in `notes/playtest.md` rather than calling those lines verified.
3. **Frame selection missing a short-lived box:** a 2% band-change threshold at 15-frame intervals could skip a box shown for less than 15 frames. Test: `test_select_keeps_changed_frames` (Task 2). The per-scene frame count is in the tour index for sanity.
4. **Release integrity:** the BPS must reproduce the exact built ROM from the clean ROM, and the README CRC must match the clean ROM. Test: `test_release_bps_reproduces_build` (Task 6).
5. **Re-tour after fixes:** a fix must not break neighbouring entries in the same block (offsets shift). Every fixed scene is rebuilt and re-toured (Task 5) and the full suite is re-run.

---

### Task 1: PNG helpers

**Files:** Create `scripts/shots.py`, `scripts/test_shots.py`

**Interfaces:**
- `shots.read_png(path) -> (w, h, bpp, rows)` (rows are bytes, RGB or RGBA)
- `shots.write_png(path, w, h, rows_rgb)`
- `shots.sheet(paths, cols, out, div=1)`
- `shots.band_diff(a, b, y0, y1) -> float` (fraction of pixels differing in rows y0..y1-1)

- [ ] **Step 1: Write the failing test** (`scripts/test_shots.py`)

```python
import os, shutil, tempfile, unittest
import shots


def solid(path, w, h, rgb):
    shots.write_png(path, w, h, [bytes(rgb) * w for _ in range(h)])


class Shots(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, self.d)

    def test_roundtrip(self):
        p = os.path.join(self.d, "a.png"); solid(p, 4, 3, (10, 20, 30))
        w, h, bpp, rows = shots.read_png(p)
        self.assertEqual((w, h, bpp), (4, 3, 3))
        self.assertEqual(rows[2][:3], bytes([10, 20, 30]))

    def test_band_diff(self):
        a, b = os.path.join(self.d, "a.png"), os.path.join(self.d, "b.png")
        solid(a, 8, 8, (0, 0, 0)); solid(b, 8, 8, (0, 0, 0))
        self.assertEqual(shots.band_diff(a, b, 0, 8), 0.0)
        rows = [bytes(24) for _ in range(8)]; rows[6] = b"\xff" * 24
        shots.write_png(b, 8, 8, rows)
        self.assertAlmostEqual(shots.band_diff(a, b, 4, 8), 0.25)

    def test_sheet(self):
        ps = []
        for i in range(3):
            p = os.path.join(self.d, f"{i}.png"); solid(p, 4, 4, (i * 50, 0, 0)); ps.append(p)
        out = os.path.join(self.d, "s.png")
        shots.sheet(ps, 2, out)
        self.assertEqual(shots.read_png(out)[:2], (2 * 6, 2 * 6))
```

- [ ] **Step 2: Run, expect** `No module named 'shots'`.
- [ ] **Step 3: Write `scripts/shots.py`**
  - `read_png` / `write_png` are taken from `work/sheet.py`, with the filter decoding unchanged.
  - `sheet` is the same layout: tiles of (w/div + 2) × (h/div + 2), background `0x40 0x00 0x40`.
  - `band_diff` compares rows y0..y1 of two same-size images (first 3 channels per pixel) and returns the differing-pixel fraction.
- [ ] **Step 4: Run, expect** `OK` (3 tests).
- [ ] **Step 5: Commit** `git add scripts/shots.py scripts/test_shots.py && git commit -m "Add PNG helpers for screenshots"`.

---

### Task 2: Scene tour driver

**Files:**
- Create `scripts/tour.py` and `scripts/test_tour.py`
- Commit `scripts/mesen/scene_hook.lua` without the glyph logging (remove the `glyphs` callback and `dump_glyphs`)
- Create `scripts/mesen/routes/mash.txt` (`4 a` / `26 -` repeated 400 times)

**Interfaces:**
- Consumes: `shots.*`, `mesen.run(script, params, rom_path)`, `accept.write_rom`, `build.english_patches`, `dump.parse_block`.
- Produces:
  - `tour.presses(scene) -> int` (6 × non-empty, non-data entries + 20)
  - `tour.run(rom_path, tag, scenes)`: per scene, writes a route `work/tour/route_<presses>.txt` (`590 -` wait, then presses × (`4 a` / `26 -`)) and runs `scene_hook.lua` (FROM `stage1`, SCENE, SHOT_EVERY 15, NAME `tour_<tag>_<SS>`)
  - `tour.select(paths, max_frames=40, threshold=0.02) -> list[str]`: keeps the first frame and every frame whose bands (rows 160-224, plus rows 0-64) differ from the last kept frame by more than the threshold
  - `tour.strip(scene, out_dir) -> str`: EN selected frames in the top row, JP below them, at 1/2 scale
  - CLI: `tour.py ref` writes the JP reference ROM to `work/tour/jp.sfc`; `tour.py run TAG ROM FIRST LAST`; `tour.py strips FIRST LAST`

- [ ] **Step 1: Write the failing test** (`scripts/test_tour.py`)

```python
import os, shutil, tempfile, unittest
import shots, tour, rom


class Tour(unittest.TestCase):
    def test_presses(self):
        self.assertGreater(tour.presses(0x0A), 20)

    def test_select_keeps_changed_frames(self):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d)
        def img(name, box):
            rows = [bytes(256 * 3) for _ in range(224)]
            if box:
                for y in range(170, 200):
                    rows[y] = b"\xff" * (256 * 3)
            p = os.path.join(d, name); shots.write_png(p, 256, 224, rows); return p
        a, b, c = img("a.png", False), img("b.png", False), img("c.png", True)
        self.assertEqual(tour.select([a, b, c]), [a, c])
```

- [ ] **Step 2: Run, expect** `No module named 'tour'`.
- [ ] **Step 3: Write `scripts/tour.py`** to the interface above. Shots land in `work/shots/tour_<tag>_<SS>_NNNNN.png`. `select` reads them sorted.
- [ ] **Step 4: Run, expect** `OK`.
- [ ] **Step 5: Emulator check**
  - `python -I scripts/tour.py ref`
  - `python -I scripts/tour.py run en build/nage_en.sfc 0x01 0x01`, `… run jp work/tour/jp.sfc 0x01 0x01`, then `tour.py strips 0x01 0x01`
  - The strip for scene `0x01` (`scene_310`) shows "Something about the school…" in EN and the Japanese in JP.
  - Repeat for `0x0A`.
- [ ] **Step 6: Commit** `git add scripts/tour.py scripts/test_tour.py scripts/mesen/scene_hook.lua scripts/mesen/routes/mash.txt && git commit -m "Add forced-scene tour driver"`.

---

### Task 3: Full tour

- [ ] **Step 1:** Run the EN tour in background batches: `python -I scripts/tour.py run en build/nage_en.sfc 0x00 0x27`, `0x28 0x4F`, … up to `0x14C`.
- [ ] **Step 2:** Run the JP tour the same way with `work/tour/jp.sfc`.
- [ ] **Step 3:** `python -I scripts/tour.py strips 0x00 0x14C`
  - Expected: `work/tour/strips/scene_XXX.png` for each scene, plus `work/tour/index.txt` (scene, frames kept EN/JP, failures).
- [ ] **Step 4:** Record failures (no loader call, crash) in `notes/playtest.md` and retry them once.
- [ ] **Step 5:** Commit `notes/playtest.md` ("Tour run" section: counts, failures).

---

### Task 4: Review

- [ ] **Step 1:** View every strip, in batches.
- [ ] **Step 2:** For each problem, log a row in `notes/playtest.md` (scene / frame / issue / cause / fix):
  - EN-only garbage
  - text outside the box frame
  - wrong line structure in banners
  - Japanese characters
  - clipped or odd English
  - wrong voice
  - a missing box compared with JP

  Garbage present on both ROMs is "context artifact".
- [ ] **Step 3:** Commit `notes/playtest.md`.

---

### Task 5: Fixes

- [ ] **Step 1:** Fix each translation or layout issue in `script/en` (or `gfx/edits.json`).
- [ ] **Step 2:** Run `python -I scripts/build.py --en script/en` and `python -I scripts/coverage.py --check`.
- [ ] **Step 3:** Re-tour each fixed scene (EN only) and check its strip.
- [ ] **Step 4:** Full suite, then commit per batch of fixes: `git commit -m "Playtest fixes: <scenes>"`.

---

### Task 6: Deeper screens (time-boxed) and release

- [ ] **Step 1 (time box: one investigation pass):** Find the stage-progress or game-mode variable.
  - With `trace.lua` from state `s1c` (party at the school door, cheats), log WRAM writes around a boss fight.
  - Alternatively, find the caller of the after-stage menu: system string 307 (どうしますか？) has a split reference; disassemble its routine and look for a reachable entry.
  - If the after-stage menu, shop or club select is reached, screenshot it, check its English, and fix or record. Otherwise list it in "Known unverified".
- [ ] **Step 2: Write the failing release test** (`scripts/test_release.py`)

```python
import os, shutil, tempfile, unittest
import bps, release, rom


@unittest.skipUnless(os.path.exists(rom.ROM_PATH), "ROM not present")
class Release(unittest.TestCase):
    def test_release_bps_reproduces_build(self):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d)
        out = release.make(d, version="test")
        clean = rom.load()
        patched = bps.apply(clean, open(out["bps"], "rb").read())
        self.assertEqual(release.crc32_bytes(patched), out["patched_crc32"])
        readme = open(out["readme"], encoding="utf-8").read()
        self.assertIn(f"{release.crc32_bytes(clean):08X}", readme)
```

- [ ] **Step 3: Run, expect** `No module named 'release'`.
- [ ] **Step 4: Write `scripts/release.py`** and `docs/README.release.txt`
  - `make(out_dir, version)`:
    - checks the coverage gate (`coverage.missing` empty, `coverage.avoided` empty)
    - builds with `script/en` and `gfx/edits.json`
    - writes `NageLibre_EN_v<version>.bps`, `README.txt` (template filled with `{version}`, `{base_crc32}`, `{base_sha1}`, `{patched_crc32}`) and `manifest.txt` (git commit, CRCs)
    - returns `{"bps", "readme", "manifest", "patched_crc32"}`
  - `crc32_bytes` uses `zlib.crc32`.
  - CLI: `python -I scripts/release.py [--version 1.0] [--out release]`.
  - README sections: title, what's translated, how to patch (Flips / beat, unheadered ROM), required ROM CRC/SHA-1, known issues (from `notes/playtest.md` Known unverified, `notes/graphics.md` deferred list, the temple glyph), credits (Varie original; translation by Claude with the user as reviewer).
  - Add `release/` to `.gitignore`.
- [ ] **Step 5: Run, expect** `OK`; then `python -I scripts/release.py --version 1.0` → `release/` written.
- [ ] **Step 6: Commit** `git add scripts/release.py scripts/test_release.py docs/README.release.txt .gitignore notes/playtest.md && git commit -m "Release packaging"`.
