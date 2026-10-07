"""Translation coverage: text entries still without English, and glossary avoid-list spellings in the English.

    python -I scripts/coverage.py [--check] [scene_310 | scene_30F..scene_325 | system ...]
"""
import glob, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dump, rom

EN = os.path.join(rom.ROOT, "script", "en")
GLOSSARY = os.path.join(rom.ROOT, "notes", "glossary.md")
JAPANESE = re.compile(r"[぀-ヿ一-鿿０-９Ａ-Ｚａ-ｚ]")   # kana, kanji, full-width alnum
TAG = re.compile(r"<[^>]*>")


def needs_english(e):
    return e.alias is None and not e.data and bool(JAPANESE.search(TAG.sub("", e.text)))


def _names(d):
    return sorted(os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(d, "*.txt")))


def expand(args, jp_dir=dump.OUT):
    all_names, out = _names(jp_dir), []
    for a in args:
        if ".." in a:
            lo, hi = a.split("..")
            out += [n for n in all_names if lo <= n <= hi]
        else:
            out.append(a)
    return out


def _read(path):
    return dump.parse_block(dump.read_text(path), joiner=" ") if os.path.exists(path) and dump.read_text(path).strip() else []


def missing(jp_dir, en_dir, names=None):
    out = []
    for name in names or _names(jp_dir):
        en = {e.index: e.text for e in _read(os.path.join(en_dir, name + ".txt"))}
        for e in _read(os.path.join(jp_dir, name + ".txt")):
            if needs_english(e) and (e.index not in en or JAPANESE.search(TAG.sub("", en[e.index]))):
                out.append((name, e.index))
    return out


def avoid_list(glossary):
    words, cols = [], None
    for line in dump.read_text(glossary).splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.lstrip().startswith("|") else None
        if not cells:
            cols = None
            continue
        if "Avoid" in cells:
            cols = cells.index("Avoid")
        elif cols is not None and cols < len(cells) and not set(cells[cols]) <= set("-: "):
            words += [w.strip() for w in cells[cols].split(",") if w.strip()]
    return words


def avoided(en_dir, glossary):
    words = [(w, re.compile(r"\b" + re.escape(w) + r"\b")) for w in avoid_list(glossary)]
    out = []
    for name in _names(en_dir):
        for e in _read(os.path.join(en_dir, name + ".txt")):
            out += [(name, e.index, w) for w, rx in words if rx.search(e.text)]
    return out


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    args = [a for a in sys.argv[1:] if a != "--check"]
    names = expand(args) if args else None
    miss = missing(dump.OUT, EN, names)
    bad = avoided(EN, GLOSSARY) if os.path.exists(GLOSSARY) else []
    total = sum(needs_english(e) for n in (names or _names(dump.OUT)) for e in _read(os.path.join(dump.OUT, n + ".txt")))
    print(f"translated {total - len(miss)}/{total} entries; {len(miss)} missing; {len(bad)} avoided spellings")
    if "--check" in sys.argv:
        for n, i in miss[:200]:
            print(f"missing {n} {i:04d}")
        for n, i, w in bad:
            print(f"avoid {n} {i:04d}: {w}")
        sys.exit(1 if miss or bad else 0)
