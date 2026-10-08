"""Run a Mesen2 Lua script headless.

    python -I scripts/mesen.py scripts/mesen/goto.lua ROUTE=... SAVE=dialogue1

ROM=<path> runs another ROM (e.g. build/nage_en.sfc). lib.lua is prepended, preceded by WORK=<abs work dir> and the KEY=VALUE params
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


def script_paths(name, tag):
    """Per-run combined Lua script and error file, so parallel runs of one script don't clobber each other."""
    return {"lua": os.path.join(WORK, "run", f"{name}_{tag}.lua"), "err": os.path.join(WORK, "run", f"{name}_{tag}.err")}


def run(script, params=None, timeout=600, rom_path=None):
    for d in SUBDIRS:
        os.makedirs(os.path.join(WORK, d), exist_ok=True)
    name = os.path.splitext(os.path.basename(script))[0]
    paths = script_paths(name, f"{os.getpid()}_{id(params)}")
    combined, err = paths["lua"], paths["err"]
    head = ['WORK = "%s/"' % WORK.replace("\\", "/"), 'ERRFILE = "%s"' % err.replace("\\", "/")]
    head += ["%s = %s" % (k, lua_value(v)) for k, v in (params or {}).items()]
    with open(LIB, encoding="utf-8") as f:
        lib = f.read()
    with open(script, encoding="utf-8") as f:
        body = f.read()
    with open(combined, "w", encoding="utf-8") as f:
        f.write("\n".join(head) + "\n" + lib + "\n" + body)
    if os.path.exists(err):
        os.remove(err)
    p = subprocess.run([MESEN, "--testRunner", rom_path or rom.ROM_PATH, combined], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=timeout)
    with open(combined[:-4] + ".out", "w", encoding="utf-8") as f:
        f.write(p.stdout + p.stderr)
    if os.path.exists(err):
        with open(err, encoding="utf-8") as f:
            raise RuntimeError("Lua error: " + f.read())
    return p.returncode


if __name__ == "__main__":
    params = dict(a.split("=", 1) for a in sys.argv[2:])
    rom_path = params.pop("ROM", None)
    rc = run(sys.argv[1], params, rom_path=rom_path)
    print("exit", rc)
    sys.exit(rc)
