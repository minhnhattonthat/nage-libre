"""Resource table access: 3-byte LoROM pointers at RES_TABLE, nibble-compressed blocks (docs/re/text-engine.md)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decompress, rom

RES_TABLE = 0x50000
COUNT = 0x530
SCENES = range(0x30F, 0x45C)


def pointer(data, rid):
    return rom.lorom_to_pc(int.from_bytes(data[RES_TABLE + 3 * rid: RES_TABLE + 3 * rid + 3], "little"))


def load(data, rid):
    return decompress.decompress(data, pointer(data, rid))[0]


def compressed_len(data, rid):
    return decompress.decompress(data, pointer(data, rid))[1]
