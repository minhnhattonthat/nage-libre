"""Max Japanese line count per print opcode (Japanese widths: code < 0x10 -> 1, else 2), to confirm wrap.BOXES.

    python -I scripts/boxcheck.py
"""
import collections, glob, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bytecode, dump, rom, wrap


def jp_lines(raw, cols):
    codes = [int.from_bytes(raw[i:i + 2], "little") for i in range(0, len(raw) - 2, 2)]
    while codes and codes[-1] == 0x03FE:
        codes.pop()
    col, n = 0, 1 if codes else 0
    for c in codes:
        w = 1 if c < 0x10 else 2
        if col + w > cols:
            n, col = n + 1, 0
        col += w
    return n


if __name__ == "__main__":
    d, m = rom.load(), dump.load_map()
    dist = collections.defaultdict(collections.Counter)
    for p in glob.glob(os.path.join(dump.OUT, "scene_*.txt")):
        name = os.path.splitext(os.path.basename(p))[0]
        blk = dump.source(d, name, m)
        es = {e.offset: e for e in dump.parse_block(dump.read_text(p))}
        for o in bytecode.parse(blk):
            box = wrap.BOXES.get(o.opcode)
            for k in (o.offset_operands if box else []):
                e = es[o.operands[k - 1]]
                dist[o.opcode][jp_lines(blk[e.offset:e.offset + e.length], box.cols)] += 1
    for op in sorted(dist):
        print(f"op {op:02X} box {wrap.BOXES[op]}: JP lines {dict(sorted(dist[op].items()))}")
