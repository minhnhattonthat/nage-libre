"""SNES LoROM image helpers: header checksum and expansion."""


def checksum(data):
    """16-bit byte sum; a non-power-of-two tail is mirrored up to the next power of two."""
    size = 1 << (len(data) - 1).bit_length()
    if size == len(data):
        return sum(data) & 0xFFFF
    base = 1 << (len(data).bit_length() - 1)
    tail = data[base:]
    return (sum(data[:base]) + sum(tail) * ((size - base) // len(tail))) & 0xFFFF


def set_checksum(img):
    img[0x7FDC:0x7FE0] = b"\xff\xff\x00\x00"        # neutral pair contributes 0x1FE like any valid pair
    c = checksum(img)
    img[0x7FDC:0x7FE0] = (c ^ 0xFFFF).to_bytes(2, "little") + c.to_bytes(2, "little")


def expand(data, size):
    return bytearray(data) + b"\xff" * (size - len(data))
