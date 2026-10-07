"""Width budget (half-columns) per system-text category; English must fit where the string is drawn.

Measured in the emulator (notes/system-text.md):
- names: the name builder writes surname + given name into ONE 5-cell buffer (10 half-width letters), so
  enemy names (random surname + random given name) need  widest surname + widest given name <= NAME_FIELD.
- prompts: the birthday-confirmation window holds 24 half-columns.
"""
NAME_FIELD = 10
SURNAMES, GIVEN = (0, 99), (100, 220)
CATEGORIES = {
    "surnames": (0, 99, NAME_FIELD),
    "given_names": (100, 220, NAME_FIELD),
    "boss_names": (221, 226, NAME_FIELD),
    "clubs": (227, 243, 10),
    "battle": (244, 277, 28),       # battle messages, stat-up lines, yes/no
    "prompts": (278, 294, 24),      # save/load/shop/birthday prompts (measured: confirmation window = 24)
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


def check_names(texts):
    """Translated surnames and given names share one field: widest surname + widest given name must fit."""
    sur = [(width(b), i) for i, b in texts.items() if SURNAMES[0] <= i <= SURNAMES[1]]
    giv = [(width(b), i) for i, b in texts.items() if GIVEN[0] <= i <= GIVEN[1]]
    if sur and giv and max(sur)[0] + max(giv)[0] > NAME_FIELD:
        (ws, s), (wg, g) = max(sur), max(giv)
        raise ValueError(f"name field: widest surname (entry {s}, {ws}) + widest given name (entry {g}, {wg}) "
                         f"> {NAME_FIELD} columns; enemy names pair any surname with any given name")
