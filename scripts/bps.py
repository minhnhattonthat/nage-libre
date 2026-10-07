"""Minimal BPS patch create/apply (byuu's BPS1 format)."""
import zlib


def _num(n):
    out = bytearray()
    while True:
        x = n & 0x7F
        n >>= 7
        if n == 0:
            out.append(0x80 | x)
            return bytes(out)
        out.append(x)
        n -= 1


def _read(buf, i):
    data, shift = 0, 1
    while True:
        x = buf[i]
        i += 1
        data += (x & 0x7F) * shift
        if x & 0x80:
            return data, i
        shift <<= 7
        data += shift


def create(src, dst):
    """SourceRead for unchanged bytes, TargetCopy for runs of a repeated byte, TargetRead otherwise."""
    out = bytearray(b"BPS1" + _num(len(src)) + _num(len(dst)) + _num(0))
    lit, tgt_rel, i, n = bytearray(), 0, 0, len(dst)

    def flush():
        if lit:
            out.extend(_num(((len(lit) - 1) << 2) | 1) + lit)
            lit.clear()

    while i < n:
        if i < len(src) and src[i] == dst[i]:
            j = i
            while j < n and j < len(src) and src[j] == dst[j]:
                j += 1
            if j - i >= 4 or j == n:
                flush()
                out += _num(((j - i - 1) << 2) | 0)
                i = j
                continue
        if i > 0 and dst[i] == dst[i - 1]:
            j = i
            while j < n and dst[j] == dst[i - 1]:
                j += 1
            if j - i >= 8:
                flush()
                delta = (i - 1) - tgt_rel
                out += _num(((j - i - 1) << 2) | 3) + _num((abs(delta) << 1) | (delta < 0))
                tgt_rel = (i - 1) + (j - i)
                i = j
                continue
        lit.append(dst[i])
        i += 1
    flush()
    out += zlib.crc32(src).to_bytes(4, "little") + zlib.crc32(dst).to_bytes(4, "little")
    out += zlib.crc32(out).to_bytes(4, "little")
    return bytes(out)


def apply(src, patch):
    if patch[:4] != b"BPS1":
        raise ValueError("not a BPS1 patch")
    if zlib.crc32(patch[:-4]) != int.from_bytes(patch[-4:], "little"):
        raise ValueError("patch CRC mismatch (corrupt patch)")
    ssize, i = _read(patch, 4)
    tsize, i = _read(patch, i)
    msize, i = _read(patch, i)
    i += msize
    if len(src) != ssize or zlib.crc32(src) != int.from_bytes(patch[-12:-8], "little"):
        raise ValueError("source ROM does not match this patch")
    out, src_rel, tgt_rel, end = bytearray(), 0, 0, len(patch) - 12
    while i < end:
        data, i = _read(patch, i)
        action, length = data & 3, (data >> 2) + 1
        if action == 0:
            out += src[len(out):len(out) + length]
        elif action == 1:
            out += patch[i:i + length]
            i += length
        else:
            d, i = _read(patch, i)
            delta = -(d >> 1) if d & 1 else d >> 1
            if action == 2:
                src_rel += delta
                out += src[src_rel:src_rel + length]
                src_rel += length
            else:
                tgt_rel += delta
                for _ in range(length):
                    out.append(out[tgt_rel])
                    tgt_rel += 1
    if len(out) != tsize or zlib.crc32(out) != int.from_bytes(patch[-8:-4], "little"):
        raise ValueError("target CRC mismatch")
    return bytes(out)
