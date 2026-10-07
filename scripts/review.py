"""Side-by-side review page: per file, index / speaker / box / Japanese / English; untranslated rows highlighted.

    python -I scripts/review.py [--out build/review.html]
"""
import html, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import context, coverage, dump, rom

STYLE = """body{font:14px sans-serif;margin:16px;background:#fff;color:#111}
table{border-collapse:collapse;width:100%;margin-bottom:24px}td,th{border:1px solid #ccc;padding:4px;vertical-align:top}
td.jp{width:38%}td.en{width:38%}tr.missing td.en{background:#fdd}h2{margin-top:32px}
@media (prefers-color-scheme:dark){body{background:#111;color:#eee}td,th{border-color:#444}tr.missing td.en{background:#522}}"""


def page(data, jp_dir, en_dir, names=None):
    m, speakers = dump.load_map(), context._speakers()
    out = [f"<!doctype html><meta charset=utf-8><title>Nage Libre review</title><style>{STYLE}</style>"]
    for name in names or coverage._names(jp_dir):
        en = {e.index: e.text for e in coverage._read(os.path.join(en_dir, name + ".txt"))}
        ctx = context.context(data, name, m) if name.startswith("scene_") else {}
        rows = []
        for e in coverage._read(os.path.join(jp_dir, name + ".txt")):
            if not coverage.needs_english(e):
                continue
            c = ctx.get(e.index)
            t = en.get(e.index)
            miss = t is None or bool(coverage.JAPANESE.search(coverage.TAG.sub("", t)))
            rows.append(f'<tr{" class=\"missing\"" if miss else ""}><td>{e.index:04d}</td>'
                        f"<td>{html.escape(context.speaker_name(c.speaker, speakers) if c else '-')}</td>"
                        f"<td>{f'{c.box.cols}x{c.box.lines}' if c else ''}</td>"
                        f'<td class="jp">{html.escape(e.text)}</td><td class="en">{html.escape(t or "")}</td></tr>')
        if rows:
            out.append(f"<h2>{name}</h2><table><tr><th>#</th><th>Speaker</th><th>Box</th><th>Japanese</th><th>English</th></tr>"
                       + "".join(rows) + "</table>")
    return "\n".join(out)


if __name__ == "__main__":
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else os.path.join(rom.ROOT, "build", "review.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(page(rom.load(), dump.OUT, coverage.EN))
    print(out)
