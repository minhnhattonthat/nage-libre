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
CHAIN = [("dialogue1", None), ("dialogue1_idle", "dialogue1"), ("stage1", "dialogue1"), ("settle60", "stage1"), ("map1", "stage1")]
# Recompressed blocks decompress in a different number of cycles, so screens can lag a few frames mid-fade.
# Compare settled screens: stage1 is compared after 60 idle frames (settle60).
COMPARE = ["dialogue1", "dialogue1_idle", "settle60", "map1"]


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
    for route in COMPARE:
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
