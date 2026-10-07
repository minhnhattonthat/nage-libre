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


def check_names(texts, original=None):
    """Surname + given name share one 10-column buffer ($7F2A40/$7F2B80, 0x140 bytes); overflow corrupts WRAM.
    Pairs come from per-stage data, so bound by widest surname + widest given name. Once any name is translated,
    all surnames must be (an untranslated 3-kanji surname is 6 columns); untranslated given names count as Japanese."""
    if not any(SURNAMES[0] <= i <= GIVEN[1] for i in texts):
        return
    missing = [i for i in range(SURNAMES[0], SURNAMES[1] + 1) if i not in texts]
    if missing:
        raise ValueError(f"name field: surnames (entries {SURNAMES[0]}-{SURNAMES[1]}) must be translated as a "
                         f"complete set once any name is ({len(missing)} missing, first {missing[0]:04d})")
    eff = {**(original or {}), **texts}
    (ws, s) = max((width(eff[i]), i) for i in range(SURNAMES[0], SURNAMES[1] + 1))
    (wg, g) = max((width(eff[i]), i) for i in range(GIVEN[0], GIVEN[1] + 1) if i in eff)
    if ws + wg > NAME_FIELD:
        raise ValueError(f"name field: widest surname (entry {s}, {ws}) + widest given name (entry {g}, {wg}) "
                         f"> {NAME_FIELD} columns")


BATTLE_LINE = 28                  # message window = width of the line-clear string, entry 244
NAME, NUM = "name", "num"         # battle names are given names (100-220) or boss names (221-226); numbers <= 5 digits
BATTLE_LINES = [(NAME, 249, NUM, 250), (NAME, 249, NUM, 251), (NAME, 248), (NAME, 263), (NAME, 277),
                (NUM, 264), (271, NUM, 274)]


def check_battle(texts, original):
    """Battle messages are assembled from pieces; each whole line must fit the window."""
    eff = {**original, **texts}
    name = max(width(eff[i]) for i in range(GIVEN[0], 227))
    for line in BATTLE_LINES:
        w = sum(name if p == NAME else 5 if p == NUM else width(eff[p]) for p in line)
        if w > BATTLE_LINE:
            raise ValueError(f"battle line {'+'.join(str(p) for p in line)}: {w} columns > {BATTLE_LINE} "
                             f"(widest name {name}, numbers 5 digits)")
