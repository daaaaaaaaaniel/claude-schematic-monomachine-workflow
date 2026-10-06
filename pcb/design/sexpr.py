"""Minimal KiCad s-expression reader/writer, as used by gen_sch.py and kicadlib.py.

parse(text) -> list of top-level expressions. An expression is a list; atoms are Sym (unquoted: keywords and
numbers, kept as text so they round-trip exactly) or str (quoted strings). dump(expr, level) writes one back, with
Python ints/floats written as numbers.
"""
import re

_TOKEN = re.compile(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+')


class Sym(str):
    """An unquoted atom."""
    __slots__ = ()


def parse(text):
    stack = [[]]
    for t in _TOKEN.findall(text):
        if t == "(":
            stack.append([])
        elif t == ")":
            done = stack.pop()
            stack[-1].append(done)
        elif t.startswith('"'):
            stack[-1].append(t[1:-1].replace('\\"', '"').replace("\\\\", "\\"))
        else:
            stack[-1].append(Sym(t))
    if len(stack) != 1:
        raise ValueError("unbalanced parentheses")
    return stack[0]


def _atom(x):
    if isinstance(x, Sym):
        return str(x)
    if isinstance(x, bool):
        return "yes" if x else "no"
    if isinstance(x, int):
        return str(x)
    if isinstance(x, float):
        s = f"{x:.4f}".rstrip("0").rstrip(".")
        return "0" if s in ("-0", "") else s
    s = str(x).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{s}"'


def dump(e, level=0):
    """Write an expression. Lists without sub-lists go on one line; otherwise one sub-list per line, order kept."""
    if not isinstance(e, list):
        return _atom(e)
    if not any(isinstance(x, list) for x in e):
        return "(" + " ".join(_atom(x) for x in e) + ")"
    pad = "\t" * (level + 1)
    out = "("
    for k, x in enumerate(e):                    # order preserved: KiCad's grammar is order-sensitive in places
        if isinstance(x, list):
            out += "\n" + pad + dump(x, level + 1)
        else:
            out += ("" if k == 0 else " ") + _atom(x)
    return out + "\n" + "\t" * level + ")"


def find(e, key):
    return next((x for x in e if isinstance(x, list) and x and x[0] == key), None)


def findall(e, key):
    return [x for x in e if isinstance(x, list) and x and x[0] == key]
