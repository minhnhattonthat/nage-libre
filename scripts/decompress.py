"""Nage Libre nibble decompressor: Python transcription of $80F8DC (see docs/re/text-engine.md ## Compression)."""


def decompress(rom, off):
    """Return (output bytes, compressed bytes consumed) for the block at file offset `off`."""
    pos = off
    flags = rom[pos]; pos += 1                  # 80F8EA: first byte = flag byte ($02DB)
    lits = 0                                    # $02D9
    ring, idx = [0xFF] * 4, 0                   # $02DF-$02E2, $02DD (80FA27)
    half, cur = False, 0                        # $02DC parity, $02E9
    out = bytearray()

    def nibble():                               # 80FA42: high nibble first
        nonlocal pos, half, cur
        half = not half
        if half:
            cur = rom[pos]; pos += 1
            return cur >> 4
        return cur & 0x0F

    def byte():
        return nibble() << 4 | nibble()

    def put(b):                                 # 80FA11: write + remember in ring
        nonlocal idx
        out.append(b)
        ring[idx] = b
        idx = (idx + 1) & 3

    while True:
        n = nibble()                            # 80F8F5 dispatch via $80F909
        if n < 8:                               # 80F92B literal
            put((n << 4 | nibble()) | (flags & 0x80))
            flags = (flags << 1) & 0xFF
            lits += 1
            if lits == 8:
                flags, lits = byte(), 0
        elif n == 8:                            # 80F97C word run
            count = 0
            while True:
                b = byte()
                count += b
                if b != 0xFF:
                    break
            pair = bytes([ring[(idx + 2) & 3], ring[(idx + 3) & 3]])
            out += pair * (count & 0xFFFF or 0x10000)
        elif n == 9:                            # 80F9E1 end
            return bytes(out), pos - off
        elif n == 0xA:
            put(0x00)
        elif n == 0xB:
            put(0xFF)
        else:                                   # C-F: ring slots 0-3
            put(ring[n - 0xC])
