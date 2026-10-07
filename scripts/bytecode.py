"""Scene bytecode: opcode table (scripts/opcodes.json) and parser.

    python -I scripts/bytecode.py --generate   # draft table from the interpreter's compare chain
    python -I scripts/bytecode.py --check      # parse every scene block, report failures
"""
import json, os, sys
from dataclasses import dataclass
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rom

TABLE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "opcodes.json")
ADC_SITES = [0x83840D, 0x838463, 0x838755, 0x8388E9, 0x838C13, 0x8396A9, 0x83978F, 0x839BAD]


@dataclass
class Op:
    pos: int
    opcode: int
    operands: list
    offset_operands: list


def load_table(path=TABLE):
    with open(path, encoding="utf-8") as f:
        return {int(k, 16): v for k, v in json.load(f)["ops"].items()}


def code_end(block):
    for i in range(0, len(block) - 1, 2):
        if block[i:i + 2] == b"\xff\xff":
            return i + 2
    raise ValueError("no FFFF terminator in block")


def parse(block, table=None):
    table = load_table() if table is None else table
    ops, pos = [], 0
    while True:
        if pos + 2 > len(block):
            raise ValueError(f"ran off the block end at {pos:#x} without a terminator")
        op = int.from_bytes(block[pos:pos + 2], "little")
        if op == 0xFFFF:
            break
        if op not in table:
            raise ValueError(f"unknown opcode {op:04X} at {pos:#x}")
        n = table[op]["words"]
        if not isinstance(n, int) or n < 1:
            raise ValueError(f"opcode {op:04X} at {pos:#x}: table entry has words={n!r} (must be >= 1)")
        words =[int.from_bytes(block[pos + 2 * k: pos + 2 * k + 2], "little") for k in range(1, n)]
        ops.append(Op(pos, op, words, list(table[op].get("offsets", []))))
        pos += 2 * n
    if pos + 2 != code_end(block):
        raise ValueError(f"terminator mismatch: parse ends at {pos:#x}, first FFFF word at {code_end(block) - 2:#x}")
    return ops


def generate():
    """Draft table: chain -> handlers; words = inc $06 pairs up to the next handler; offsets from adc #$64C0."""
    d = rom.load()
    chain = {}
    for i in range(0x18000, 0x1C000 - 11):
        if d[i] == 0xC9 and d[i + 2] == 0 and d[i + 3] == 0xD0 and d[i + 4] == 6 and d[i + 5] == 0x20 and d[i + 8] == 0x82:
            chain.setdefault(d[i + 1], 0x830000 | d[i + 6] | d[i + 7] << 8)
    hs = sorted(set(chain.values()))
    ops = {}
    for op, h in sorted(chain.items()):
        nxt = hs[hs.index(h) + 1] if hs.index(h) + 1 < len(hs) else h + 0x80
        body = d[rom.lorom_to_pc(h):rom.lorom_to_pc(nxt)]
        incs = [k for k in range(len(body) - 1) if body[k] == 0xE6 and body[k + 1] == 0x06]
        offsets = []
        for site in ADC_SITES:
            if h <= site < nxt:
                lda = body.rfind(b"\xa7\x06", 0, site - h)          # lda [$06] feeding the adc
                offsets.append(sum(1 for k in incs if k < lda) // 2)
        ops[f"0x{op:02X}"] = {"handler": f"{h:06X}", "words": len(incs) // 2, "offsets": offsets,
                              "note": "draft (naive inc $06 count)"}
    return {"ops": ops}


def check():
    import glob, dump
    d, m = rom.load(), dump.load_map()
    bad = 0
    for p in sorted(glob.glob(os.path.join(dump.OUT, "scene_*.txt"))):
        name = os.path.splitext(os.path.basename(p))[0]
        blk = dump.source(d, name, m)
        try:
            parse(blk)
        except ValueError as e:
            bad += 1
            words = [int.from_bytes(blk[i:i + 2], "little") for i in range(0, min(len(blk), 0x40), 2)]
            print(f"{name}: {e}\n    head: {' '.join(f'{w:04X}' for w in words)}")
    print(f"{333 - bad}/333 blocks parse")


if __name__ == "__main__":
    if "--generate" in sys.argv:
        with open(TABLE, "w", encoding="utf-8", newline="\n") as f:
            json.dump(generate(), f, indent=1)
    if "--check" in sys.argv:
        check()
