"""Package the release: BPS patch, README, manifest (local only; nothing is uploaded).

    python -I scripts/release.py [--version 1.0] [--out release]
"""
import hashlib, os, subprocess, sys, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bps, build, coverage, dump, rom

TEMPLATE = os.path.join(rom.ROOT, "docs", "README.release.txt")
KNOWN_ISSUES = """- Some graphics labels on screens not reached in testing are still Japanese: costume and floor words,
  battle-command words, the status screen's "next", and a row of small kanji near the battle HUD
  (see notes/graphics.md).
- Shop, club select and later-stage menus were checked statically, not in play (see notes/playtest.md).
- One temple name uses a glyph that could not be read with certainty; the English avoids naming the temple."""


def crc32_bytes(b):
    return zlib.crc32(b) & 0xFFFFFFFF


def _commit():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=rom.ROOT, capture_output=True,
                              text=True, check=True).stdout.strip()
    except Exception:
        return "unknown"


def make(out_dir, version="1.0"):
    if coverage.missing(dump.OUT, coverage.EN) or coverage.avoided(coverage.EN, coverage.GLOSSARY):
        raise SystemExit("coverage gate failed: run python -I scripts/coverage.py --check")
    clean = rom.load()
    gfx = build.GFX_EDITS if os.path.exists(build.GFX_EDITS) else None
    img = build.build(clean, coverage.EN, gfx=gfx)
    patch = bps.create(clean, img)
    if bps.apply(clean, patch) != img:
        raise SystemExit("BPS round-trip failed")
    os.makedirs(out_dir, exist_ok=True)
    names = {"bps": f"NageLibre_EN_v{version}.bps", "readme": "README.txt", "manifest": "manifest.txt"}
    paths = {k: os.path.join(out_dir, v) for k, v in names.items()}
    with open(paths["bps"], "wb") as f:
        f.write(patch)
    fields = {"version": version, "base_crc32": f"{crc32_bytes(clean):08X}", "base_sha1": hashlib.sha1(clean).hexdigest(),
              "patched_crc32": f"{crc32_bytes(img):08X}", "known_issues": KNOWN_ISSUES}
    with open(TEMPLATE, encoding="utf-8") as f:
        text = f.read().format(**fields)
    with open(paths["readme"], "w", encoding="utf-8", newline="\r\n") as f:
        f.write(text)
    with open(paths["manifest"], "w", encoding="utf-8", newline="\n") as f:
        f.write(f"version {version}\ncommit {_commit()}\nbase_crc32 {fields['base_crc32']}\nbase_sha1 {fields['base_sha1']}\n"
                f"patched_crc32 {fields['patched_crc32']}\npatched_sha1 {hashlib.sha1(img).hexdigest()}\nbps_bytes {len(patch)}\n")
    return {**paths, "patched_crc32": crc32_bytes(img)}


def main():
    version = sys.argv[sys.argv.index("--version") + 1] if "--version" in sys.argv else "1.0"
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else os.path.join(rom.ROOT, "release")
    try:
        r = make(out, version)
    except build.BuildError as e:
        raise SystemExit(f"BUILD FAILED: {e}")
    print(r["bps"], f"patched CRC32 {r['patched_crc32']:08X}")


if __name__ == "__main__":
    main()
