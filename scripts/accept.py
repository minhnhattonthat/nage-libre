"""Emulator acceptance for the built ROM.

    python -I scripts/accept.py identity   # clean vs identity build: final screens of each route must match
    python -I scripts/accept.py growth     # build with a long English scene_341 0000; screenshots for review
    python -I scripts/accept.py english    # build with scripts/fixtures/en_sample; screenshots for review
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
    """chain items: (route, from_route) or (route, from_route, cheats)."""
    for route, src, *rest in chain:
        params = {"ROUTE": os.path.join(ROUTES, route + ".txt").replace("\\", "/"), "SAVE": f"{tag}_{route}", "SHOT_EVERY": 30}
        if src:
            params["FROM"] = f"{tag}_{src}"
        if rest and rest[0]:
            params["CHEATS"] = rest[0]
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
    """Identity build vs a reference = clean ROM + the same English font patches (no block relocation),
    so any difference comes from rebuilding/recompressing/relocating the scene blocks."""
    clean = rom.load()
    ref = bytearray(clean)
    for off, old, new in build.english_patches(clean):
        ref[off:off + len(new)] = new
    d, built = write_rom(build.build(clean))
    rd, reference = write_rom(bytes(ref))
    try:
        play("clean", reference)
        play("built", built)
    finally:
        shutil.rmtree(d)
        shutil.rmtree(rd)
    ok = True
    for route in COMPARE:
        same = final("clean", route) == final("built", route)
        ok &= same
        print(f"{route}: {'MATCH' if same else 'DIFF'}")
    return ok


def growth():
    en = tempfile.mkdtemp()
    with open(os.path.join(en, "scene_341.txt"), "w", encoding="utf-8") as f:
        f.write("## scene_341 0000 @000000 len=0\n<BR>In a distant world, far away… a voice echoes in the dark…<END>\n")
    d, built = write_rom(build.build(rom.load(), en))
    play("growth", built, [("dialogue1", None), ("narration_next", "dialogue1")])
    shutil.rmtree(d)
    shutil.rmtree(en)
    print("review work/shots/growth_narration_next_*.png")
    return True


def english():
    fixtures = os.path.join(rom.ROOT, "scripts", "fixtures", "en_sample")
    d, built = write_rom(build.build(rom.load(), fixtures))
    try:
        play("english", built, [("dialogue1", None), ("narration_next", "dialogue1"),
                                ("stage1", "dialogue1"), ("map1", "stage1"), ("settle240", "map1")])
    finally:
        shutil.rmtree(d)
    print("review work/shots/english_narration_next_*.png (scene_341 0000/0002/0004) and "
          "work/shots/english_settle240_final.png (scene_310 0012, portrait 22x4 filled)")
    return True


BATTLE_CHEATS = "7E10CCFF,7E10D163"
SYS_CHAIN = CHAIN + [("stage1b", "stage1"), ("battle_a", "stage1b", BATTLE_CHEATS)]
SYS_COMPARE = COMPARE + ["battle_a"]
OLDREADS = os.path.join(rom.ROOT, "scripts", "mesen", "oldreads.lua")


def system():
    """2c: identity relocation vs font-patched reference, zero reads of the old system block, English samples."""
    clean = rom.load()
    ref = bytearray(clean)
    for off, old, new in build.english_patches(clean):
        ref[off:off + len(new)] = new
    d, built = write_rom(build.build(clean))
    rd, reference = write_rom(bytes(ref))
    ok = True
    try:
        play("sysref", reference, SYS_CHAIN)
        play("sysbuilt", built, SYS_CHAIN)
        for route in SYS_COMPARE:
            same = final("sysref", route) == final("sysbuilt", route)
            ok &= same
            print(f"identity {route}: {'MATCH' if same else 'DIFF'}")
        for route, src, *rest in SYS_CHAIN:
            params = {"ROUTE": os.path.join(ROUTES, route + ".txt").replace("\\", "/"), "NAME": route}
            if src:
                params["FROM"] = f"sysbuilt_{src}"
            if rest and rest[0]:
                params["CHEATS"] = rest[0]
            mesen.run(OLDREADS, params, rom_path=built)
            with open(os.path.join(mesen.WORK, "trace", f"oldreads_{route}.txt"), encoding="utf-8") as f:
                n, pc = f.read().split()
            ok &= n == "0"
            print(f"oldreads {route}: {n}" + ("" if n == "0" else f" (first reader {pc})"))
    finally:
        shutil.rmtree(d)
        shutil.rmtree(rd)
    fixtures = os.path.join(rom.ROOT, "scripts", "fixtures", "en_sample")
    d, built = write_rom(build.build(clean, fixtures))
    try:
        play("sysen", built, SYS_CHAIN)
    finally:
        shutil.rmtree(d)
    print("review work/shots/sysen_stage1_final.png (birthday prompt) and work/shots/sysen_battle_a_*.png (names, messages)")
    return ok


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode not in ("identity", "growth", "english", "system"):
        raise SystemExit("usage: accept.py identity|growth|english|system")
    ok = {"identity": identity, "growth": growth, "english": english, "system": system}[mode]()
    sys.exit(0 if ok else 1)
