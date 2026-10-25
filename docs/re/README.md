# Reverse-engineering notes

One file per subsystem (text engine, pointers, compression, font, graphics). Mark every finding with how far it is
proven, so a later session doesn't build on a guess:

- **verified** - and how: a decoded known string, a corrupt-and-boot test, a breakpoint hit on the drawing path, a
  passing roundtrip test. Name the test or savestate.
- **guess** - and why it seems likely (byte pattern, another game, an earlier patch's notes). Promote it to verified
  before code depends on it.

Addresses are for the dump in `rom.sha1` unless a note says otherwise.

| File | Covers | State |
|---|---|---|
| text-engine.md | font, opcodes, encoding, compression | verified (dump roundtrip, traces) |
| text-inventory.md | every text location and its encoding | verified |
| insertion.md | rebuild pipeline (2a), WRAM window, relocation | verified (accept.py identity) |
| english.md | 8x16 English font, boxes, wrap | verified (tour, printcheck) |
| system-text.md | bank $87 system text relocated to $BF8000 | verified (debug screens) |
| wram.md | bank $7F usage, scene buffer window | verified (wram_map.lua trace) |
| graphics.md | graphics labels, deferred list | verified (debug screens) |
