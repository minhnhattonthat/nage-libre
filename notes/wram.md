# WRAM bank $7F usage (scene buffer window)

Measured 2026-10-08 with `scripts/mesen/wram_map.lua` on route `wram_tour.txt`: a single run from power-on through the opening narration, birthday screen, Stage 1 map and first battle (~11.6k frames). Summary: `python -I scripts/wram_free.py work/trace`.

## Used pages (first writer)

| Range | Writer | Meaning |
|---|---|---|
| `$7F:0000-11FF`, `2C00-6CFF`, `8800-8FFF` | `80F948/80F9C7/80FA11/80F9D2` | decompressor output (scene blocks at `$64C0`, other resources elsewhere) |
| `$7F:1600-2BFF` | `82BD9C 82DB68 82BDB0 81D4E2 81BA8F` | map / sprite work buffers |
| `$7F:7800-87FF` | `82BC48 82BF2E` | tilemap buffers (first used page after the scene buffer) |
| `$7F:9000-AAFF` | `82C191` | |
| `$7F:C000-FFFF` | `82BDD3 82BDF5` | |

## Free spans (never written)

- `$7F:1200-15FF` (`0x400`)
- `$7F:6D00-77FF` (`0xB00`), the tail of the scene buffer window
- `$7F:AB00-BFFF` (`0x1500`)

## Hard-coded buffer base

A full scan of banks `$80-$83` finds exactly 9 sites: `adc #$64C0` at `83840D 838463 838755 8388E9 838C13 8396A9 83978F 839BAD`, and the split `lda #$C0 … lda #$64` loader at `8380F0`. `build.relocation_patches()` covers all of them.

## Decision

**Keep `BASE = $64C0`, `WINDOW = 0x1340`** (buffer `$7F:64C0-$7F:77FF`):
- `$7F:6D00-77FF` is never written by anything else, and `$7F:7800` is the first used page.
- No larger free span exists. `$7F:AB00-BFFF` is only `0x1500` bytes, a marginal gain for an untested relocation.

Unvisited screens (shop, club select, save/load, ending, extra stage) were not measured. If 2b/translation needs more room, the fallback is the 2b option of keeping strings in ROM.
