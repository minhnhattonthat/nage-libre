"""Summarise WRAM bank $7F page usage from wram_map.lua traces.

    python -I scripts/wram_free.py work/trace
"""
import glob, os, sys


def load(trace_dir):
    used = {}
    for p in glob.glob(os.path.join(trace_dir, "wram7f_*.txt")):
        with open(p, encoding="utf-8") as f:
            for line in f:
                page, pc = line.split()
                used.setdefault(int(page, 16), set()).add(pc)
    return used


def free_spans(used):
    """[(first_free_page, first_used_page_after), ...] for page runs never written."""
    spans, start = [], None
    for page in range(0x100):
        if page not in used and start is None:
            start = page
        elif page in used and start is not None:
            spans.append((start, page))
            start = None
    if start is not None:
        spans.append((start, 0x100))
    return spans


if __name__ == "__main__":
    used = load(sys.argv[1])
    for page in sorted(used):
        print(f"$7F:{page:02X}00 written by {' '.join(sorted(used[page]))}")
    for a, b in free_spans(set(used)):
        print(f"FREE $7F:{a:02X}00-$7F:{b * 0x100 - 1:04X} ({(b - a) * 0x100:#x} bytes)")
