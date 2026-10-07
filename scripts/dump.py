"""Dump script blocks listed in scripts/textmap.json to script/jp/<block>.txt.

Kinds: ptr16 / ptr24 / fixed / list (text in ROM), scene (compressed event blocks: resource table entries
FIRST..LAST, one file per resource `scene_XXX.txt`, offsets relative to the decompressed block).
"""
import json, os, re, sys
from dataclasses import dataclass
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rom
from tbl import Table

MAP = os.path.join(rom.ROOT, "scripts", "textmap.json")
TBL = os.path.join(rom.ROOT, "nage.tbl")
OUT = os.path.join(rom.ROOT, "script", "jp")
_HEAD = re.compile(r"^## (\S+) (\d+) (?:@([0-9A-F]+) len=(\d+)|=(\d+))$")
END = b"\xff\xff"


@dataclass
class Entry:
    block: str
    index: int
    offset: int | None
    length: int
    text: str
    alias: int | None = None


def write_text(path, s):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(s)


def read_text(path):
    with open(path, encoding="utf-8") as f:          # universal newlines: CRLF checkouts/editors read as LF
        return f.read()


def _pointers(data, b):
    tab, n = int(b["table"], 16), b["count"]
    if b["kind"] == "ptr16":
        bank = int(b["bank"], 16) << 16
        return [rom.lorom_to_pc(bank | int.from_bytes(data[tab + 2 * i: tab + 2 * i + 2], "little")) for i in range(n)]
    return [rom.lorom_to_pc(int.from_bytes(data[tab + 3 * i: tab + 3 * i + 3], "little")) for i in range(n)]


def extract(data, table, b):
    if b["kind"] == "fixed":
        start, size = int(b["start"], 16), b["size"]
        return [Entry(b["name"], i, start + i * size, size,
                      table.decode(data, start + i * size, start + (i + 1) * size, stop_at_end=False)[0])
                for i in range(b["count"])]
    if b["kind"] == "list":                      # consecutive terminated strings in [start, end)
        pos, end, out = int(b["start"], 16), int(b["end"], 16), []
        while pos < end:
            text, nxt = table.decode(data, pos, end)
            out.append(Entry(b["name"], len(out), pos, nxt - pos, text))
            pos = nxt
        return out
    out, first = [], {}
    for i, off in enumerate(_pointers(data, b)):
        if off in first:
            out.append(Entry(b["name"], i, None, 0, "", alias=first[off]))
            continue
        first[off] = i
        text, end = table.decode(data, off)
        out.append(Entry(b["name"], i, off, end - off, text))
    return out


def extract_scene(blk, table, name):
    """Strings = everything after the bytecode's first FFFF word, one entry per FFFF-terminated unit."""
    pos = next((i for i in range(0, len(blk) - 1, 2) if blk[i:i + 2] == END), None)
    if pos is None:
        return []
    out, pos = [], pos + 2
    while pos < len(blk) - 1:
        text, end = table.decode(blk, pos)
        out.append(Entry(name, len(out), pos, end - pos, text))
        pos = end
    return out


def scene_names(b):
    return [f"scene_{r:03X}" for r in range(int(b["first"], 16), int(b["last"], 16) + 1)]


def scene_block(data, b, name):
    import decompress
    r = int(name.split("_")[1], 16)
    ptr = int.from_bytes(data[int(b["res_table"], 16) + 3 * r:][:3], "little")
    return decompress.decompress(data, rom.lorom_to_pc(ptr))[0]


def wrap_text(text, table, width):
    """Insert display newlines every `width` half-columns (code < 0x10 = 1, else 2). Encoder ignores them."""
    out, col, i = [], 0, 0
    longest = max((len(k) for k in table.enc_text), default=1)
    while i < len(text):
        if text[i] == "<":
            j = text.index(">", i) + 1
            out.append(text[i:j]); i = j
            continue
        for ln in range(min(longest, len(text) - i), 0, -1):
            code = table.enc_text.get(text[i:i + ln])
            if code is not None:
                break
        else:
            ln, code = 1, b"\xff\xff"
        w = 1 if int.from_bytes(code, "little") < 0x10 else 2
        if col + w > width:
            out.append("\n"); col = 0
        out.append(text[i:i + ln]); col += w; i += ln
    return "".join(out)


def format_block(entries, table, wrap=None):
    parts = []
    for e in entries:
        if e.alias is not None:
            parts.append(f"## {e.block} {e.index:04d} ={e.alias:04d}\n")
            continue
        text = wrap_text(e.text, table, wrap) if wrap else e.text
        for tag in table.break_tags:
            text = re.sub(r"(<%s(?::[0-9A-F]+)?>)" % tag, r"\1\n", text)
        parts.append(f"## {e.block} {e.index:04d} @{e.offset:06X} len={e.length}\n{text.rstrip(chr(10))}\n")
    return "\n".join(parts)


def parse_block(s):
    out = []
    for chunk in re.split(r"\n(?=## )", s.strip("\n")):
        head, _, body = chunk.partition("\n")
        m = _HEAD.match(head)
        if not m:
            raise ValueError(f"bad header: {head!r}")
        name, idx = m.group(1), int(m.group(2))
        if m.group(5) is not None:
            out.append(Entry(name, idx, None, 0, "", alias=int(m.group(5))))
        else:
            out.append(Entry(name, idx, int(m.group(3), 16), int(m.group(4)), body.replace("\n", "")))
    return out


def gaps(entries):
    spans = sorted({(e.offset, e.offset + e.length) for e in entries if e.alias is None})
    out, end = [], None
    for s, e in spans:
        if end is not None and s > end:
            out.append((end, s))
        end = e if end is None else max(end, e)
    return out


def load_map():
    with open(MAP, encoding="utf-8") as f:
        return json.load(f)["blocks"]


def source(data, name, blocks):
    """Bytes that entry offsets of dump file `name` refer to (ROM, or the decompressed scene block)."""
    for b in blocks:
        if b["kind"] == "scene" and name in scene_names(b):
            return scene_block(data, b, name)
    return data


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    data, table = rom.load(), Table.load(TBL)
    os.makedirs(OUT, exist_ok=True)
    for b in load_map():
        if b["kind"] == "scene":
            total = unk = 0
            for name in scene_names(b):
                entries = extract_scene(scene_block(data, b, name), table, name)
                write_text(os.path.join(OUT, name + ".txt"), format_block(entries, table, wrap=30))
                total += len(entries)
                unk += sum(e.text.count("<$") for e in entries)
            print(f"{b['name']}: {len(scene_names(b))} scene files, {total} entries, {unk} raw codes")
            continue
        entries = extract(data, table, b)
        write_text(os.path.join(OUT, b["name"] + ".txt"), format_block(entries, table))
        g = gaps(entries) if b["kind"] in ("ptr16", "ptr24") else []
        unk = sum(e.text.count("<$") for e in entries)
        print(f"{b['name']}: {len(entries)} entries, {unk} raw codes, gaps: "
              + (", ".join(f"{s:06X}-{e:06X}" for s, e in g) or "none"))
