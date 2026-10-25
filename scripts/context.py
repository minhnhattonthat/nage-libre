"""Per-entry translation context from the scene bytecode: speaker (last op 08/02 id; op 13 slot k -> id k+1),
box, print op.

    python -I scripts/context.py scene_310 [scene_311 ...]     # worksheet: header, [speaker] box op, JP
"""
import json, os, re, sys
from dataclasses import dataclass
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bytecode, dump, rom, wrap

SPEAKERS = os.path.join(rom.ROOT, "docs", "speakers.json")
PORTRAIT_OPS = (0x08, 0x02)          # first operand = character id


@dataclass(frozen=True)
class Ctx:
    speaker: int | tuple | None     # tuple of ids when several op-13 slots share the entry
    box: wrap.Box
    op: int
    slot: int | None                # first op-13 slot
    slots: tuple = ()               # every op-13 slot that prints the entry


def context(data, name, m=None):
    blk = dump.source(data, name, m or dump.load_map())
    entries = dump.parse_block(dump.read_text(os.path.join(dump.OUT, name + ".txt")))
    by_off = {e.offset: e for e in entries if e.alias is None}
    boxes = wrap.entry_boxes(blk)
    out, speaker = {}, None
    for o in bytecode.parse(blk):
        if o.opcode in PORTRAIT_OPS:
            speaker = o.operands[0]
        if o.opcode not in wrap.BOXES:
            continue
        for k in o.offset_operands:
            e = by_off.get(o.operands[k - 1])
            if e is None:
                continue
            prev = out.get(e.index)
            if o.opcode == 0x13 and (prev is None or prev.op == 0x13):
                slots = tuple(sorted(set(prev.slots if prev else ()) | {k - 1}))
                ids = tuple(s + 1 for s in slots)
                out[e.index] = Ctx(ids[0] if len(ids) == 1 else ids, boxes.get(e.offset, wrap.FULL), 0x13, slots[0], slots)
            elif prev is None:
                out[e.index] = Ctx(speaker, boxes.get(e.offset, wrap.FULL), o.opcode, None)
    return out


def _speakers():
    try:
        with open(SPEAKERS, encoding="utf-8") as f:
            return {int(k, 16): v for k, v in json.load(f).items()}
    except FileNotFoundError:
        return {}


def speaker_name(sid, names=None):
    if sid is None:
        return "-"
    names = _speakers() if names is None else names
    if isinstance(sid, tuple):
        return "any member" if len(sid) == 5 else "/".join(speaker_name(s, names) for s in sid)
    return names.get(sid, f"id 0x{sid:03X} (?)")


def worksheet(data, name, m=None):
    ctx, names = context(data, name, m), _speakers()
    lines = []
    for e in dump.parse_block(dump.read_text(os.path.join(dump.OUT, name + ".txt"))):
        if e.alias is not None or e.data or e.text.strip() == "<END>":
            continue
        c = ctx.get(e.index)
        where = f"[{speaker_name(c.speaker, names)}] {c.box.cols}x{c.box.lines} op{c.op:02X}" if c else "[unreferenced]"
        head = f"## {name} {e.index:04d} @{e.offset:06X} len={e.length}"
        lines.append(f"{head}\n# {where}\n{re.sub('　+', ' ', e.text)}\n")
    return "\n".join(lines)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    d, m = rom.load(), dump.load_map()
    for n in sys.argv[1:]:
        print(worksheet(d, n, m))
