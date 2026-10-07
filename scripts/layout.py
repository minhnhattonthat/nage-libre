"""Rebuild one scene block: new string bytes, original order and adjacency, every block-offset operand repointed."""
import bytecode


def rebuild(block, entries, texts, table=None):
    ops = bytecode.parse(block, table)
    end = bytecode.code_end(block)
    moved, area, pos = {}, bytearray(), end
    for e in entries:
        if e.index in texts:
            if e.data:
                raise ValueError(f"entry {e.index:04d} is a data entry; it cannot be replaced")
            b = texts[e.index]
            if b[-2:] != b"\xff\xff":
                raise ValueError(f"entry {e.index:04d}: new text must end with FFFF (<END>)")
        else:
            b = block[e.offset:e.offset + e.length]
        moved[e.offset] = pos
        area += b
        pos += len(b)
    out = bytearray(block[:end])
    for op in ops:
        for k in op.offset_operands:
            at = op.pos + 2 * k
            old = int.from_bytes(out[at:at + 2], "little")
            if old not in moved:
                raise ValueError(f"op {op.opcode:02X} at {op.pos:#x}: operand {k} = {old:#x} is not an entry start")
            out[at:at + 2] = moved[old].to_bytes(2, "little")
    return bytes(out + area)
