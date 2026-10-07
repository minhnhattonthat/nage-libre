"""Table file: HEX=text (HEX in ROM byte order). Tags <NAME>, <NAME:n> (n arg bytes),
trailing ! = terminator, trailing / = dump inserts a newline after it. Unmapped bytes -> <$XX>.

    python -I scripts/tbl.py --check nage.tbl
"""
import re, sys

_TAG = re.compile(r"^<([A-Za-z0-9_]+)(?::(\d+))?>([!/]*)$")


class Table:
    def __init__(self):
        self.dec = {}        # bytes -> (text or tag name, nargs, is_end, is_tag)
        self.enc_text = {}   # text -> bytes (first definition wins)
        self.enc_tag = {}    # tag name -> (bytes, nargs)
        self.break_tags = set()
        self.duplicates, self.errors = [], []
        self.maxlen = 1

    @classmethod
    def load(cls, path):
        with open(path, encoding="utf-8") as f:
            return cls.parse(f.read())

    @classmethod
    def parse(cls, text):
        t, seen = cls(), {}
        for n, line in enumerate(text.splitlines(), 1):
            if not line.strip() or line.startswith("#"):
                continue
            if "=" not in line:
                t.errors.append(f"line {n}: no '='")
                continue
            hexpart, val = line.split("=", 1)
            try:
                code = bytes.fromhex(hexpart.strip())
            except ValueError:
                t.errors.append(f"line {n}: bad hex {hexpart!r}")
                continue
            if not code or not val:
                t.errors.append(f"line {n}: empty code or value")
                continue
            t.maxlen = max(t.maxlen, len(code))
            m = _TAG.match(val)
            if m:
                name, nargs, flags = m.group(1), int(m.group(2) or 0), m.group(3)
                t.dec[code] = (name, nargs, "!" in flags, True)
                t.enc_tag.setdefault(name, (code, nargs))
                if "/" in flags:
                    t.break_tags.add(name)
            else:
                t.dec[code] = (val, 0, False, False)
                t.enc_text.setdefault(val, code)
                seen.setdefault(val, []).append(code.hex().upper())
        t.duplicates = [(v, codes) for v, codes in seen.items() if len(codes) > 1]
        return t

    def _render(self, code, args):
        text, nargs, _, is_tag = self.dec[code]
        if is_tag and self.enc_tag[text][0] == code:
            return f"<{text}:{args.hex().upper()}>" if nargs else f"<{text}>"
        if not is_tag and self.enc_text.get(text) == code:
            return text
        return f"<${code.hex().upper()}>"           # tag alias or duplicate glyph: keep raw

    def decode(self, data, start=0, end=None, stop_at_end=True):
        end = len(data) if end is None else end
        pos, out = start, []
        while pos < end:
            for ln in range(min(self.maxlen, end - pos), 0, -1):
                code = bytes(data[pos:pos + ln])
                if code in self.dec:
                    break
            else:
                out.append(f"<${data[pos]:02X}>")
                pos += 1
                continue
            _, nargs, is_end, _ = self.dec[code]
            args = bytes(data[pos + ln:pos + ln + nargs])
            out.append(self._render(code, args))
            pos += ln + nargs
            if is_end and stop_at_end:
                break
        return "".join(out), pos

    def encode(self, text):
        out, i = bytearray(), 0
        text = text.replace("\n", "")
        longest = max((len(k) for k in self.enc_text), default=1)
        while i < len(text):
            if text[i] == "<":
                j = text.index(">", i)
                tok = text[i + 1:j]
                if tok.startswith("$"):
                    out += bytes.fromhex(tok[1:])
                else:
                    name, _, args = tok.partition(":")
                    if name not in self.enc_tag:
                        raise ValueError(f"unknown tag <{tok}> at {i}")
                    code, nargs = self.enc_tag[name]
                    a = bytes.fromhex(args) if args else b""
                    if len(a) != nargs:
                        raise ValueError(f"<{tok}> needs {nargs} arg bytes at {i}")
                    out += code + a
                i = j + 1
                continue
            for ln in range(min(longest, len(text) - i), 0, -1):
                if text[i:i + ln] in self.enc_text:
                    out += self.enc_text[text[i:i + ln]]
                    i += ln
                    break
            else:
                raise ValueError(f"no table entry for {text[i]!r} at {i}")
        return bytes(out)


if __name__ == "__main__":
    t = Table.load(sys.argv[-1])
    for v, codes in t.duplicates:
        print(f"duplicate {v!r}: {' '.join(codes)} (later codes dump as <$XX>)")
    for e in t.errors:
        print("ERROR", e)
    print(f"{len(t.dec)} entries, {len(t.duplicates)} duplicates, {len(t.errors)} errors")
    sys.exit(1 if t.errors else 0)
