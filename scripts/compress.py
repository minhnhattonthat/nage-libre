"""Encoder for the Nage Libre nibble compression (inverse of decompress.py). Greedy; size is secondary."""


def _tokens(data):
    """Token list replaying the decoder's ring: ("lit", b), ("op", nibble), ("run", count)."""
    ring, idx, toks, i = [0xFF] * 4, 0, [], 0
    while i < len(data):
        pair = bytes([ring[(idx + 2) & 3], ring[(idx + 3) & 3]])
        k = 0
        while k < 0xFFFF and data[i + 2 * k: i + 2 * k + 2] == pair:
            k += 1
        if k >= 2:
            toks.append(("run", k))
            i += 2 * k
            continue
        b = data[i]
        if b == 0x00:
            toks.append(("op", 0xA))
        elif b == 0xFF:
            toks.append(("op", 0xB))
        elif b in ring:
            toks.append(("op", 0xC + ring.index(b)))
        else:
            toks.append(("lit", b))
        ring[idx] = b
        idx = (idx + 1) & 3
        i += 1
    return toks


def compress(data):
    toks = _tokens(bytes(data))
    bits = [v >> 7 for kind, v in toks if kind == "lit"]

    def flag(group):                           # flag byte for literals 8*group .. 8*group+7, MSB first
        g = (bits[8 * group: 8 * group + 8] + [0] * 8)[:8]
        return sum(bit << (7 - j) for j, bit in enumerate(g))

    nib, lits = [], 0

    def byte(v):
        nib.extend((v >> 4, v & 0xF))

    for kind, v in toks:
        if kind == "lit":
            nib.extend(((v >> 4) & 7, v & 0xF))
            lits += 1
            if lits % 8 == 0:
                byte(flag(lits // 8))
        elif kind == "run":
            nib.append(8)
            while v >= 0xFF:
                byte(0xFF)
                v -= 0xFF
            byte(v)
        else:
            nib.append(v)
    nib.append(9)
    if len(nib) % 2:
        nib.append(0)
    return bytes([flag(0)]) + bytes(nib[k] << 4 | nib[k + 1] for k in range(0, len(nib), 2))
