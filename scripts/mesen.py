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
