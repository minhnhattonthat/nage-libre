"""Disassemble ROM code with the bundled snes2asm.

    python -I scripts/disasm.py 0x81EDDA 0x80 [--a8] [--i8]

--a8/--i8: accumulator/index start 8-bit (P.M / P.X set). Default 16-bit.
"""
import contextlib, io, os, sys, types
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rom
sys.path.insert(0, os.path.join(rom.ROOT, "tools"))
from snes2asm.cartridge import Cartridge
from snes2asm.disassembler import Disassembler

_OPTS = types.SimpleNamespace(hex=True, nolabel=True, hirom=None, lorom=True, fastrom=True,
                              slowrom=None, banks=None, verbose=None, empty_fill=255)
_cart = None


def _cartridge():
    global _cart
    if _cart is None:
        _cart = Cartridge(_OPTS.__dict__)
        with contextlib.redirect_stdout(io.StringIO()):
            _cart.open(rom.ROM_PATH)
    return _cart


def disassemble(addr, length, a16=True, i16=True):
    cart = _cartridge()
    d = Disassembler(cart, _OPTS)
    d.flags = (0 if a16 else 0x20) | (0 if i16 else 0x10)      # mirrors P: M/X bit set = 8-bit
    start = rom.lorom_to_pc(addr)
    d.decode(start, start + length)
    return ["%06X  %s  ; %s" % (rom.pc_to_lorom(pos), ins.code, ins.comment)
            for pos, ins in d.code.items()]


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = sys.argv[1:]
    length = int(args[1], 0) if len(args) > 1 else 0x40
    print("\n".join(disassemble(int(args[0], 0), length, "--a8" not in flags, "--i8" not in flags)))
