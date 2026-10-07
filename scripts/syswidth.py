"""Width budget (half-columns) per system-text category; English must fit where the string is drawn.

Initial budgets: names/bosses = the name builder's buffer (10 half-width letters); others = the Japanese maximum.
Updated from on-screen measurements in notes/system-text.md.
"""
CATEGORIES = {
    "names": (0, 220, 10),          # enemy surnames + given names (name builder buffer 0x140 = 10 half-width)
    "boss_names": (221, 226, 10),
    "clubs": (227, 243, 10),
    "battle": (244, 277, 28),       # battle messages, stat-up lines, yes/no
    "prompts": (278, 294, 26),      # save/load/shop/birthday prompts
    "birthstones": (295, 306, 14),
    "menu_items": (307, 318, 14),   # after-stage menu, jewels
}


def width(encoded):
    return sum(1 if int.from_bytes(encoded[i:i + 2], "little") < 0x80 else 2 for i in range(0, len(encoded) - 2, 2))


def check(index, encoded):
    for name, (first, last, cols) in CATEGORIES.items():
        if first <= index <= last:
            w = width(encoded)
            if w > cols:
                raise ValueError(f"system entry {index} ({name}): {w} columns > {cols}")
            return
    raise ValueError(f"system entry {index}: no width category")
