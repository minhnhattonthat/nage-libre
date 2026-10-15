"""Debug warps to the screens that normal play routes don't reach (notes/playtest.md, Debug screens).

    python -X utf8 -I scripts/debug_screens.py [--rom build/nage_en.sfc] [--tag en] [screen ...]

Cold boot -> dialogue1 -> stage1 (birthday screen), then:
- map screens: mash A until the unit-control loop 828BC0 runs (state <tag>_ctl), then the screen's route;
  FORCE / CHEATS fake what stage 1 can't offer (a second party member, stock cards);
- after-stage menu screens: redirect.lua jumps from the stage routine 828000 to the menu 87CA0F.
Shots: work/shots/<tag>_<screen>_final.png, all of them in work/shots/<tag>_debug_sheet.png.
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mesen, rom

ROUTES = os.path.join(rom.ROOT, "scripts", "mesen", "routes")
LUA = os.path.join(rom.ROOT, "scripts", "mesen")
CTL = "828BC0"                          # unit-control loop: Y free look, X Rest?, A command menu
STOCK = ",".join("7E%04X%02X" % (0x27C + i, i % 6) for i in range(25))    # stock cards $027C: types 0-5
MAP = {   # screen: (route from <tag>_ctl, extra params)
    "status": ("dbg_status.txt", {}),                                   # Y, cursor on Yui, A
    "stats": ("dbg_stats.txt", {}),                                     # ... A again: HP/ST/DEF/SPD/SPI
    "terrain": ("dbg_terrain.txt", {}),                                 # Y, A on ground: 0x295 panel
    "rest": ("dbg_rest.txt", {"FORCE": "828C2E:a=0"}),                  # X; needs 2+ awake members
    "pager": ("dbg_pager.txt", {}),                                     # command menu Pager -> WHO
    "trade": ("dbg_trade.txt", {"FORCE": "828263:a=1,82844D:a=1", "CHEATS": STOCK}),  # Trade -> card types
}
MENU = {"menu": "dbg_menu.txt", "shop": "dbg_shop.txt", "club": "dbg_club.txt", "save": "dbg_save.txt"}


def _run(script, rom_path, **params):
    rc = mesen.run(os.path.join(LUA, script), params, rom_path=rom_path)
    if rc != 0:
        raise RuntimeError(f"{script} {params.get('SAVE') or params.get('NAME')}: exit {rc}")


def run(rom_path, tag, screens):
    route = lambda n: os.path.join(ROUTES, n)
    _run("goto.lua", rom_path, ROUTE=route("dialogue1.txt"), SAVE=f"{tag}_d1", SHOT_EVERY=100000)
    _run("goto.lua", rom_path, ROUTE=route("stage1.txt"), SAVE=f"{tag}_stage1", FROM=f"{tag}_d1", SHOT_EVERY=100000)
    if any(s in MAP for s in screens):
        _run("until_pc.lua", rom_path, FROM=f"{tag}_stage1", AT_PC=CTL, SAVE=f"{tag}_ctl", LIMIT=12000)
    for s in screens:
        if s in MAP:
            r, extra = MAP[s]
            _run("goto.lua", rom_path, FROM=f"{tag}_ctl", ROUTE=route(r), SAVE=f"{tag}_{s}", SHOT_EVERY=30, **extra)
        else:
            _run("redirect.lua", rom_path, FROM=f"{tag}_stage1", MASH="a", ROUTE2=route(MENU[s]),
                 NAME=f"{tag}_{s}", AT_PC="828000", TO_PC="87CA0F", SHOT_EVERY=60)


def sheet(tag, screens):
    from PIL import Image
    shots = os.path.join(mesen.WORK, "shots")
    ims = []
    for s in screens:
        p = os.path.join(shots, f"{tag}_{s}_final.png")
        if not os.path.exists(p):                   # redirect.lua names shots by frame; take the last one
            frames = sorted(f for f in os.listdir(shots) if f.startswith(f"{tag}_{s}_0"))
            p = os.path.join(shots, frames[-1])
        ims.append(Image.open(p).convert("RGB"))
    cols = 4
    out = Image.new("RGB", (256 * cols, 224 * ((len(ims) + cols - 1) // cols)))
    for i, im in enumerate(ims):
        out.paste(im, ((i % cols) * 256, (i // cols) * 224))
    path = os.path.join(shots, f"{tag}_debug_sheet.png")
    out.save(path)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rom", default=os.path.join(rom.ROOT, "build", "nage_en.sfc"))
    ap.add_argument("--tag", default="en")
    ap.add_argument("screens", nargs="*", default=list(MAP) + list(MENU))
    a = ap.parse_args()
    bad = [s for s in a.screens if s not in MAP and s not in MENU]
    if bad:
        sys.exit(f"unknown screens {bad}; known: {list(MAP) + list(MENU)}")
    run(a.rom, a.tag, a.screens)
    print(sheet(a.tag, a.screens))


if __name__ == "__main__":
    main()
