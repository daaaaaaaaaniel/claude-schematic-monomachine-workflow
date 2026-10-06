"""KiCad symbol-library access for gen_sch.py: load a symbol by lib_id, list its pins and units.

load_symbol("Lib:Name") returns the symbol as an s-expression named "Lib:Name", flattened if it `extends` another
symbol (as KiCad embeds it in a schematic's lib_symbols; e.g. stock LMV324 extends LM2902). Libraries are looked up
as <dir>/<Lib>.kicad_sym in SYMDIRS (gen_sch.py puts ../lib first).
"""
import copy
import os

from sexpr import Sym, find, findall, parse

SYMDIRS = [os.environ.get("KICAD10_SYMBOL_DIR", "/usr/share/kicad/symbols")]
_cache = {}


def _library(lib):
    if lib not in _cache:
        for d in SYMDIRS:
            path = os.path.join(d, f"{lib}.kicad_sym")
            if os.path.exists(path):
                tree = parse(open(path).read())[0]
                _cache[lib] = {s[1]: s for s in findall(tree, "symbol")}
                break
        else:
            raise FileNotFoundError(f"symbol library {lib!r} not found in {SYMDIRS}")
    return _cache[lib]


def _flatten(lib, name):
    syms = _library(lib)
    if name not in syms:
        raise KeyError(f"{lib}:{name} not found")
    s = copy.deepcopy(syms[name])
    ext = find(s, "extends")
    if not ext:
        return s
    base = _flatten(lib, ext[1])
    own = {p[1]: p for p in findall(s, "property")}
    out = [Sym("symbol"), name]
    for x in base[2:]:
        if isinstance(x, list) and x and x[0] == "property":
            out.append(own.pop(x[1], x))
        elif isinstance(x, list) and x and x[0] == "symbol":
            x = list(x)
            x[1] = name + x[1][len(base[1]):]          # Base_1_1 -> Name_1_1
            out.append(x)
        else:
            out.append(x)
    idx = max(i for i, x in enumerate(out) if isinstance(x, list) and x and x[0] == "property") + 1
    out[idx:idx] = list(own.values())                  # derived-only properties after the inherited ones
    return out


def load_symbol(lib_id):
    lib, name = lib_id.split(":", 1)
    s = _flatten(lib, name)
    s[1] = f"{lib}:{name}"
    return s


def _unit(sub, name):
    return int(sub[1][len(name) + 1:].split("_")[0])


def pins(sym):
    """[(unit, number, name, type, x, y, angle, length, hidden)] in library coordinates (y up)."""
    name = sym[1].split(":", 1)[1]
    out = []
    for sub in findall(sym, "symbol"):
        u = _unit(sub, name)
        for p in findall(sub, "pin"):
            at, ln, h = find(p, "at"), find(p, "length"), find(p, "hide")
            hidden = (h is not None and (len(h) == 1 or h[1] == "yes")) or \
                any(x == "hide" for x in p if not isinstance(x, list))
            out.append((u, str(find(p, "number")[1]), str(find(p, "name")[1]), str(p[1]),
                        float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0.0,
                        float(ln[1]) if ln else 0.0, hidden))
    return out


def units(sym):
    name = sym[1].split(":", 1)[1]
    return sorted({_unit(s, name) for s in findall(sym, "symbol")} - {0})
