"""ROM location and LoROM address helpers."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROM_PATH = os.path.join(ROOT, "rom", "Nage Libre - Seijaku no Suishin (Japan).sfc")


def load():
    with open(ROM_PATH, "rb") as f:
        return f.read()


def lorom_to_pc(addr):
    """CPU address ($00-$7D / $80-$FF banks, $8000-$FFFF) -> file offset."""
    if addr & 0x8000 == 0 or (addr >> 16) & 0xFE == 0x7E:
        raise ValueError(f"${addr:06X} is not a LoROM ROM address")
    return ((addr & 0x7F0000) >> 1) | (addr & 0x7FFF)


def pc_to_lorom(off):
    """File offset -> FastROM CPU address (bank $80+)."""
    return 0x800000 | ((off << 1) & 0x7F0000) | 0x8000 | (off & 0x7FFF)
