# Nage Libre EN — Sub-project 5: Scripted Playtest and Release

Date: 2026-10-08
Status: approved (standing approval). User decisions: Claude scripts the playtest (no human play); staff credits stay in kanji.

## Context

Sub-projects 1-4 are done:
- the full script is translated (2572/2572 entries) and fit-checked by the build
- system text is relocated and English
- the command menu and WHO graphics are English; the status screen and the 眠りますか？ prompt are edited but unverified

What remains:
- **visual verification** of text the build can't judge: layout of 30×4 banners and narration, multi-print boxes, inserted names, op-13 member variants
- **screens the stage-1 routes don't reach:** after-stage menu, shop, club select, status, later stages, ending
- **a release package**

### Facts this design relies on (probes, 2026-10-08)

- **Scene forcing works.** The scene loader `8380DB` is entered with A = scene number (resource = scene + `0x30F`).
  - `scripts/mesen/scene_hook.lua` replaces A on the first call. From state `stage1` with the `map1.txt` A-mash route (first call at frame 590, scene 1), forcing scene `0x0A` (`scene_319`) plays it in the stage-1 map context: English text boxes and party portraits. Example: `force0A_00900.png` shows "Impressive, making it this far! But… yo…".
  - Some boxes show garbage tiles when a scene runs out of its context (graphics not loaded, data-table ops); see `force0A_00720.png`. To tell a context artifact from a translation bug, the same scene must be forced on the Japanese reference ROM.
- **Glyph-read logging is not a reliable detector.** Full-width reads straddle two code slots, and the Japanese ROM shows almost no font reads. It is dropped; verification is visual.
- **Emulator speed:** about 100 frames/s headless (`accept.py system` played about 25k frames in 4 minutes).

## Goal and success criteria

1. **Scene tour:** every scene `0x00-0x14C` (333) is forced on the English build and on the Japanese reference (clean ROM + 2b font patches), with screenshots.
   - Text frames are selected automatically (the box region changed since the previous shot).
   - Per-scene contact strips are written for both ROMs side by side.
   - Every strip is reviewed. Each issue is logged in `notes/playtest.md` as scene / frame / issue / cause (translation, layout, context artifact) / fix.
2. **Fixes:** every issue caused by the translation or layout is fixed in `script/en` or `gfx/edits.json`, then rebuilt and re-toured for that scene. Context artifacts (garbage in both ROMs) are noted, not fixed.
3. **Deeper screens (time-boxed):** reach at least one of the after-stage menu, the shop, the club select or the status screen programmatically:
   - find the game-mode / stage-progress WRAM variables (trace writes around the stage-1 boss defeat with cheats)
   - or force the menu routine
   - verify its English or graphics; fix or record

   Whatever stays unreached goes in `notes/playtest.md` "Known unverified".
4. **Release:** `python -I scripts/release.py` writes `release/`:
   - `NageLibre_EN_v1.0.bps`
   - `README.txt`: patching instructions, base ROM CRC32/SHA-1, credits, known issues
   - `release/manifest.txt`: patched ROM CRC32/SHA-1, version, build commit

   Nothing is uploaded or published.

## Components

| File | Responsibility | Interface |
|---|---|---|
| `scripts/mesen/scene_hook.lua` | Force a scene at the loader; screenshots | params FROM, ROUTE, NAME, SCENE, SHOT_EVERY; writes `trace/scene_hook_NAME.txt` (loader calls) |
| `scripts/shots.py` | PNG read/write and contact sheets (promoted from `work/sheet.py`) | `read_png(path) -> (w, h, rows_rgb)`; `sheet(paths, cols, out, scale_div=1)`; `region_changed(a, b, box) -> bool` |
| `scripts/tour.py` | Scene tour driver | `run(rom_path, tag, scenes, presses)` → `work/tour/<tag>/<scene>/NNNNN.png`; `select(tag, scene) -> list[path]`; `strip(scene) -> png path` (EN beside JP); CLI `tour.py run --tag en --rom build/nage_en.sfc [--scenes 0x00..0x14C]`, `tour.py strips` |
| `scripts/release.py` | Release packaging | `crc32(path)`, `sha1(path)`; writes `release/` from a fresh build; refuses if the build fails or the coverage gate fails |
| `notes/playtest.md` | Issue log, known unverified screens | tables |
| `docs/README.release.txt` | README template | placeholders `{version}`, `{base_crc32}`, `{base_sha1}`, `{patched_crc32}` |

## Tour mechanics

- **Base state:** `stage1`, route `map1.txt`-style A-mash with the override at the first loader call.
- **Press count per scene:** `presses = 6 × text entries + 20`, at 30 frames per press. Screenshots every 15 frames. Scene text entry counts come from `script/jp`.
- **Text-frame selection:**
  - box region = the 16-224 × 160-224 px band, plus the top band 0-64 for banners
  - a frame is kept when its band differs from the last kept frame by more than 2% of pixels
  - at most 40 frames per scene
- **Run time:** both ROMs, about 333 × 1500 frames → about 2 × 85 minutes. The tour runs in background shells, in batches of about 40 scenes per command.

## Error handling

- **A scene that never calls the loader** (forced too early or crashed): logged as "no loader call" and retried once from a later state. If it still fails, it goes to "Known unverified".
- **Emulator crash or timeout:** the scene is marked failed, and the tour continues.
- **release.py:** stops on build or coverage failure, a missing clean ROM, or a checksum mismatch.

## Testing

- `shots.py`: read/write round-trip of a generated PNG; `region_changed` true and false cases.
- `tour.py`: `presses()` for a known scene; `select()` on a synthetic 3-frame set keeps the changed frames only.
- `release.py`: on a temp output dir it produces the bps, README and manifest; applying the bps (`bps.apply`) to the clean ROM yields the built ROM; the README contains the base CRC.
- **Emulator:** the tour of scenes `0x01` (`scene_310`, natural context) and `0x0A` produces strips. `0x01` must match the natural `map1` run.

## Out of scope

- A full human-equivalent playthrough of all 22 stages.
- New translation passes beyond fixing the issues the tour finds.
- Publishing the patch anywhere (outward-facing; the user decides).
