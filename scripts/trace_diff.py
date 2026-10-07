"""Show PCs that are new (or much busier) in ACTIVE vs BASE per-PC aggregates.

    python -I scripts/trace_diff.py work/trace/idle_rom.csv work/trace/print_rom.csv
"""
import csv, sys


def load(path):
    with open(path, encoding="utf-8") as f:
        return {int(r["pc"], 16): (int(r["n"]), int(r["lo"], 16), int(r["hi"], 16)) for r in csv.DictReader(f)}


def diff(base, active, ratio=4.0):
    out = []
    for pc, (n, lo, hi) in sorted(active.items()):
        nb = base.get(pc, (0,))[0]
        if nb == 0 or n >= ratio * nb:
            out.append((pc, n, nb, lo, hi))
    return out


if __name__ == "__main__":
    for pc, n, nb, lo, hi in diff(load(sys.argv[1]), load(sys.argv[2])):
        print(f"{pc:06X}  n={n:<7} base={nb:<7} {lo:06X}-{hi:06X}")
