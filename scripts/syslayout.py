"""Lay out the system text block in bank $BF and build the reference patches."""
BASE_FILE, BASE_CPU, MAX = 0x1F8000, 0xBF8000, 0x8000
BLANK, END, MARK = bytes([0xFE, 0x03]), bytes([0xFF, 0xFF]), bytes([0xFC, 0x03])   # 03FE blank, FFFF, 03FC ■


def layout(entries, texts, data, strides):
    """Concatenate entries in index order (translated bytes or original), return (blob, {index: CPU address})."""
    blob, new = bytearray(), {}
    for e in entries:
        b = texts.get(e.index, bytes(data[e.offset:e.offset + e.length]))
        stride = strides.get(e.index)
        if stride:
            if len(b) > stride:
                raise ValueError(f"system entry {e.index}: {len(b)} bytes > stride {stride}")
            b = b[:-2] + BLANK * ((stride - len(b)) // 2) + END
        new[e.index] = BASE_CPU + len(blob)
        blob += b
    if len(blob) > MAX:
        raise ValueError(f"system text is {len(blob):#x} bytes, more than one bank ({MAX:#x})")
    return bytes(blob), new


def patches(refs, new, data):
    """(file offset, original bytes, new bytes) for every reference."""
    out = []
    for r in refs:
        a = new[r.index]
        if r.kind == "split":            # A9 lo 85 dp A9 hi 85 dp+1 A9 87 85 dp+2: operands at +1, +5, +9
            for k, v in ((1, a & 0xFF), (5, (a >> 8) & 0xFF), (9, a >> 16)):
                out.append((r.at + k, bytes(data[r.at + k:r.at + k + 1]), bytes([v])))
        elif r.kind == "ptr24":
            out.append((r.at, bytes(data[r.at:r.at + 3]), a.to_bytes(3, "little")))
        elif r.kind == "imm16":
            out.append((r.at + 1, bytes(data[r.at + 1:r.at + 3]), (a & 0xFFFF).to_bytes(2, "little")))
        else:
            raise ValueError(f"unknown reference kind {r.kind}")
    return out


def marker_fill(entries, data):
    """Overwrite the old block with ■ glyphs, keeping every entry's length and terminator."""
    return [(e.offset, bytes(data[e.offset:e.offset + e.length]), MARK * (e.length // 2 - 1) + END) for e in entries]
