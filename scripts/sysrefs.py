"""Find every reference to the bank-$87 system text (file 0x38077-0x38B3E).

    python -I scripts/sysrefs.py [--check]
Kinds: split (8-bit lda/sta lo,hi,#$87 into dp..dp+2), imm16 (manually confirmed), ptr24 (3-byte table entries).
"""
import json, os, re, sys
from dataclasses import dataclass
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dump, rom
from tbl import Table

MANUAL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sysrefs.json")
CODE_END = 0x60000                      # code banks $80-$8B
SPLIT = re.compile(rb"\xa9(.)\x85(.)\xa9(.)\x85(.)\xa9\x87\x85(.)", re.S)


@dataclass(frozen=True)
class Ref:
    kind: str
    at: int         # file offset of the patch site (split: first A9; imm16: opcode; ptr24: pointer)
    index: int      # system entry index


def entries(data):
    block = next(b for b in dump.load_map() if b["name"] == "system")
    return dump.extract(data, Table.load(dump.TBL), block)


def load_manual():
    with open(MANUAL, encoding="utf-8") as f:
        return json.load(f)


def scan(data):
    start = {rom.pc_to_lorom(e.offset): e.index for e in entries(data)}      # CPU $87xxxx -> index
    manual = load_manual()
    refs = []
    for m in SPLIT.finditer(data[:CODE_END]):
        lo, dp, hi, dp1, dp2 = (m.group(k)[0] for k in range(1, 6))
        addr = 0x870000 | hi << 8 | lo
        if dp1 == dp + 1 and dp2 == dp + 2 and addr in start:
            refs.append(Ref("split", m.start(), start[addr]))
    for t in manual["ptr24_tables"]:
        base, stride = int(t["at"], 16), t.get("stride", 3)
        for k in range(t["count"]):
            at = base + stride * k
            p = int.from_bytes(data[at:at + 3], "little")
            if p in start:
                refs.append(Ref("ptr24", at, start[p]))
    for x in manual["confirmed_imm16"]:
        at = int(x["at"], 16)
        addr = 0x870000 | data[at + 1] | data[at + 2] << 8
        if addr not in start:
            raise ValueError(f"confirmed imm16 at {at:#x} does not point at a system string ({addr:06X})")
        refs.append(Ref("imm16", at, start[addr]))
    return refs


def coverage(refs, es, manual):
    covered = {r.index for r in refs}
    for lst in manual["lists"]:
        if lst["base_index"] in covered:
            covered |= set(range(lst["first"], lst["last"] + 1))
    covered |= {u["index"] for u in manual["unused"]}
    return [e.index for e in es if e.index not in covered]


if __name__ == "__main__":
    d = rom.load()
    refs = scan(d)
    missing = coverage(refs, entries(d), load_manual())
    kinds = {k: sum(r.kind == k for r in refs) for k in ("split", "imm16", "ptr24")}
    print(f"refs {kinds}; uncovered entries ({len(missing)}): {missing}")
    sys.exit(1 if missing and "--check" in sys.argv else 0)
