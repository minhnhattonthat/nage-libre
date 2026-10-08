"""Forced-scene tour: play every scene by overriding the scene loader (scene_hook.lua), keep the frames where text
changed, and write EN-above-JP contact strips for review (notes/playtest.md).

    python -I scripts/tour.py ref                          # Japanese reference ROM -> work/tour/jp.sfc
    python -I scripts/tour.py run TAG ROM FIRST LAST        # e.g. run en build/nage_en.sfc 0x00 0x27
    python -I scripts/tour.py strips FIRST LAST             # work/tour/strips/scene_XXX.png + index.txt
"""
import glob, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dump, mesen, rom, shots

ROOT = os.path.join(rom.ROOT, "work", "tour")
HOOK = os.path.join(rom.ROOT, "scripts", "mesen", "scene_hook.lua")
BASE_ROUTE = os.path.join(rom.ROOT, "scripts", "mesen", "routes", "tour_base.txt")   # reaches the first loader call (frame 590)
FIRST_LOADER_FRAME = 585
BANDS = [(160, 224), (0, 64)]                 # dialogue box band, banner band
WAIT_OP = "0x83859C"                          # op 06 handler (wait for key): one screenshot per finished text page


def _shots(tag, scene):
    return sorted(p for p in glob.glob(os.path.join(mesen.WORK, "shots", f"tour_{tag}_{scene:03X}_*.png"))
                  if int(p[-9:-4]) >= FIRST_LOADER_FRAME)


def run(rom_path, tag, scenes, every=None):
    """every: shoot every N frames instead of on op 06 (timed narration scenes have no key waits)."""
    failed = []
    for s in scenes:
        for old in glob.glob(os.path.join(mesen.WORK, "shots", f"tour_{tag}_{s:03X}_*.png")):
            os.remove(old)
        params = {"FROM": "stage1", "ROUTE": BASE_ROUTE.replace("\\", "/"), "NAME": f"tour_{tag}_{s:03X}", "AUTO": 1,
                  "SCENE": str(s), **({"SHOT_EVERY": every, "IDLE": 9000, "PRINTLOG": 1} if every else {"SHOT_ON": WAIT_OP})}
        rc = mesen.run(HOOK, params, rom_path=rom_path)
        print(f"{tag} scene {s:03X}: rc={rc} shots={len(_shots(tag, s))}", flush=True)
        if rc != 0:
            failed.append(s)
    return failed


def select(paths, max_frames=40, threshold=0.02):
    kept, last = [], None
    for p in paths:
        img = shots.read_png(p)
        if last is None or any(shots.band_diff(img, last, y0, y1) > threshold for y0, y1 in BANDS):
            kept.append(p)
            last = img
            if len(kept) >= max_frames:
                break
    return kept


def pages(log):
    """Typed pages from a PRINTLOG trace: (start, end frame or None if cut off mid-typing, frames the finished page
    stays up before the next page starts: an upper bound on reading time; 0 if cut off, None for the last page)."""
    out = []
    for line in log:
        k = line.split()
        if k[0] == "S":
            out.append([int(k[1]), None])
        elif k[0] == "E" and out and out[-1][1] is None:
            out[-1][1] = int(k[1])
    return [(s, e, (0 if e is None else nxt[0] - e) if nxt else None)
            for (s, e), nxt in zip(out, out[1:] + [None])]


def _blank():
    p = os.path.join(ROOT, "blank.png")
    if not os.path.exists(p):
        shots.write_png(p, 256, 239, [b"\x40\x00\x40" * 256 for _ in range(239)])
    return p


def strip(scene, cols=8):
    en, jp = select(_shots("en", scene)), select(_shots("jp", scene))
    pad = lambda xs: xs + [_blank()] * (-len(xs) % cols or (cols if not xs else 0))
    out_dir = os.path.join(ROOT, "strips")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"scene_{scene + 0x30F:03X}.png")
    shots.sheet(pad(en) + pad(jp), cols, out, div=2)
    return out, len(en), len(jp)


def _range(a, b):
    return range(int(a, 16), int(b, 16) + 1)


def main():
    cmd = sys.argv[1]
    if cmd == "ref":
        # identity build (relocated scene buffer, Japanese text): the original small buffer crashes on scenes forced
        # out of context, so it can't serve as reference; hiragana show as Latin letters (2b font), which is fine for
        # telling context artifacts (garbage on both) from translation bugs
        import build
        ref = build.build(rom.load())
        os.makedirs(ROOT, exist_ok=True)
        with open(os.path.join(ROOT, "jp.sfc"), "wb") as f:
            f.write(bytes(ref))
        print(os.path.join(ROOT, "jp.sfc"))
    elif cmd == "run":
        tag, rom_path, a, b = sys.argv[2:6]
        failed = run(rom_path, tag, _range(a, b))
        print("failed:", " ".join(f"{s:03X}" for s in failed) or "none")
    elif cmd == "run-timed":
        # python -I scripts/tour.py run-timed TAG ROM 032,033,... : timed narration scenes, a shot every 60 frames
        tag, rom_path, lst = sys.argv[2:5]
        failed = run(rom_path, tag, [int(x, 16) for x in lst.split(",")], every=60)
        print("failed:", " ".join(f"{s:03X}" for s in failed) or "none")
    elif cmd == "printcheck":
        # python -I scripts/tour.py printcheck TAG 032,033,... : pages cut off mid-typing or up < 30 frames (timed runs)
        tag, lst = sys.argv[2:4]
        for x in lst.split(","):
            with open(os.path.join(mesen.WORK, "trace", f"scene_hook_tour_{tag}_{int(x, 16):03X}.txt")) as f:
                ps = pages(f.read().splitlines())
            bad = [f"{st}:{'CUT' if e is None else g}" for st, e, g in ps if e is None or (g is not None and g < 30)]
            print(f"{tag} {int(x, 16):03X} pages={len(ps)} short: {' '.join(bad) or '-'}")
    elif cmd == "strips":
        with open(os.path.join(ROOT, "index.txt"), "a", encoding="utf-8") as idx:
            for s in _range(*sys.argv[2:4]):
                out, ne, nj = strip(s)
                idx.write(f"{s:03X} scene_{s + 0x30F:03X} en={ne} jp={nj}\n")
                print(out, ne, nj)
    elif cmd == "sheets":
        # full-size 4x4 pages per scene and ROM, legible for text review: work/tour/review/<tag>_<SSS>_<k>.png
        out_dir = os.path.join(ROOT, "review")
        os.makedirs(out_dir, exist_ok=True)
        for s in _range(*sys.argv[2:4]):
            for tag in ("en", "jp"):
                ps = select(_shots(tag, s), max_frames=200, threshold=0.003)   # keep completed timed lines
                for k in range(0, len(ps), 16):
                    shots.sheet(ps[k:k + 16], 4, os.path.join(out_dir, f"{tag}_{s + 0x30F:03X}_{k // 16}.png"))


if __name__ == "__main__":
    main()
