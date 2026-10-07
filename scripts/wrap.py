"""Fit English text into a dialogue box. The engine wraps mid-word and never pages, so the build
word-wraps by padding lines with spaces and rejects text that doesn't fit."""
import re
from dataclasses import dataclass
import bytecode


@dataclass(frozen=True)
class Box:
    cols: int       # half-columns (8 px) per line
    lines: int


PORTRAIT, FULL, FULL4 = Box(22, 4), Box(30, 3), Box(30, 4)
BOXES = {0x01: PORTRAIT, 0x13: PORTRAIT, 0x0B: FULL4, 0x26: FULL, 0x2B: FULL, 0x3B: FULL}


class FitError(ValueError):
    pass


_TOK = re.compile(r"<[^>]*>|.")


def _width(tok, table):
    if tok.startswith("<$"):
        code = int.from_bytes(bytes.fromhex(tok[2:-1]), "little")
    elif tok.startswith("<"):
        return 0
    else:
        b = table.enc_text.get(tok)
        if b is None:
            raise FitError(f"no table entry for {tok!r}")
        code = int.from_bytes(b, "little")
    return 1 if code < 0x80 else 2


def fit(text, box, table):
    if not text.endswith("<END>"):
        raise FitError("text must end with <END>")
    out, cur, curw, wrapped = [], "", 0, False

    def end_line(pad):
        nonlocal cur, curw
        out.append(cur + (" " * (box.cols - curw) if pad else ""))
        cur, curw = "", 0

    for word in text[:-5].replace("<BR>", " \0 ").split():
        if word == "\0":
            if curw == 0 and wrapped:          # engine already wrapped after an exactly full line
                wrapped = False
                continue
            end_line(True)
            wrapped = False
            continue
        ww = sum(_width(t, table) for t in _TOK.findall(word))
        if ww > box.cols:
            raise FitError(f"word {word!r} is {ww} columns, box line is {box.cols}")
        if curw == 0:
            cur, curw = word, ww
        elif curw + 1 + ww <= box.cols:
            cur, curw = cur + " " + word, curw + 1 + ww
        else:
            end_line(True)
            cur, curw = word, ww
        wrapped = False
        if curw == box.cols:
            end_line(False)
            wrapped = True
    if cur:
        end_line(False)
    if len(out) > box.lines:
        raise FitError(f"{len(out)} lines, box holds {box.lines} lines of {box.cols} columns")
    return "".join(out) + "<END>"


def entry_boxes(block, ops=None):
    ops = bytecode.parse(block) if ops is None else ops
    seen = {}
    for o in ops:
        box = BOXES.get(o.opcode)
        if box is None:
            continue
        for k in o.offset_operands:
            if k not in o.data_operands:
                seen.setdefault(o.operands[k - 1], set()).add(box)
    out = {}
    for off, boxes in seen.items():
        widths = {b.cols for b in boxes}
        out[off] = Box(min(widths), 1) if len(widths) > 1 else min(boxes, key=lambda b: b.lines)
    return out
