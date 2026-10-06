"""Netlist checks; exits non-zero if any fails. Run from pcb/: python3 tools/check_netlist.py

1. The drawn schematic (out/drawn.net, exported by kicad-cli from machine-filter/) must match the two SKiDL board
   netlists (out/main.net + out/control.net) exactly: the same multi-pin nets, the same parts, values and
   footprints. This also proves no drawn net spans both boards (the control board's nets carry the CTL_ prefix).
2. The two boards joined through their headers (JAn pin k = JBn pin k, headers then removed) must be exactly the
   one-circuit SKiDL netlist (out/logical.net): nothing lost or shorted in the split.
3. Against rev alpha (reference/boards_rev_alpha.py), the logical netlist may differ only at the pins the rev beta
   changes touch (EXPECTED). Anything else is an unintended change.

Connectivity is compared as sets of (ref, pin), so net names don't matter. Power flags (#FLG, #PWR) are ignored.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out")
sys.path.insert(0, os.path.join(ROOT, "reference"))

# Pins whose connections rev beta changes on purpose (machine_filter.py, "Changes from rev alpha"; design/pinmap.py).
EXPECTED = {
    "A1": {"2", "3", "4", "5", "6", "7", "14", "15"} | {str(k) for k in range(22, 36)},   # SDMMC (new); ADC pins
    "U6": {"1", "2", "4", "5", "12", "13", "14", "15"},                  # pot multiplexer channels
    **{u: {"1", "2", "3", "5", "6", "7", "8", "9", "10", "12", "13", "14"} for u in ("U1", "U2", "U7", "U8")},
}
NEW_PARTS = {"J15", "R100", "R101", "R102", "R103", "R104", "C100"}   # the optional microSD socket and its parts


def parse_sexpr(text):
    tokens = re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+', text)
    stack = [[]]
    for t in tokens:
        if t == "(":
            stack.append([])
        elif t == ")":
            done = stack.pop()
            stack[-1].append(done)
        else:
            stack[-1].append(t[1:-1] if t.startswith('"') else t)
    return stack[0][0]


def _section(tree, key):
    return next(x for x in tree if isinstance(x, list) and x and x[0] == key)


def read_netlist(path):
    """KiCad s-expression netlist -> ({net name: {(ref, pin)}}, {ref: (value, footprint)})."""
    tree = parse_sexpr(open(path).read())
    nets = {}
    for net in _section(tree, "nets")[1:]:
        name = next(x[1] for x in net if isinstance(x, list) and x[0] == "name")
        nodes = set()
        for x in net:
            if isinstance(x, list) and x[0] == "node":
                d = {y[0]: y[1] for y in x[1:] if isinstance(y, list)}
                nodes.add((d["ref"], d["pin"]))
        nets[name] = nodes
    parts = {}
    for c in _section(tree, "components")[1:]:
        d = {x[0]: x[1] for x in c[1:] if isinstance(x, list) and len(x) > 1 and isinstance(x[1], str)}
        if not d["ref"].startswith("#"):
            parts[d["ref"]] = (d.get("value"), d.get("footprint"))
    return nets, parts


def groups(nets):
    out = set()
    for nodes in nets.values():
        nodes = frozenset((r, p) for r, p in nodes if not r.startswith("#"))
        if len(nodes) >= 2:
            out.add(nodes)
    return out


def fmt(g):
    return " ".join(f"{r}.{p}" for r, p in sorted(g))


def check_drawn_vs_skidl():
    s_groups, s_parts = set(), {}
    for b in ("main", "control"):
        nets, parts = read_netlist(os.path.join(OUT, f"{b}.net"))
        s_groups |= groups(nets)
        s_parts.update(parts)
    d_nets, d_parts = read_netlist(os.path.join(OUT, "drawn.net"))
    s, d = s_groups, groups(d_nets)
    ok = True
    for g in sorted(s - d, key=sorted):
        print("  in SKiDL, not in the drawing:", fmt(g))
        ok = False
    for g in sorted(d - s, key=sorted):
        print("  in the drawing, not in SKiDL:", fmt(g))
        ok = False
    for r in sorted(set(s_parts) | set(d_parts)):
        if s_parts.get(r) != d_parts.get(r):
            print(f"  part {r}: SKiDL {s_parts.get(r)}  drawing {d_parts.get(r)}")
            ok = False
    print(f"1. drawing vs SKiDL (main + control): {len(d)} / {len(s)} nets, {len(d_parts)} / {len(s_parts)} parts:",
          "identical" if ok else "DIFFERENT")
    return ok


def check_split():
    """Join main + control through the headers, drop the headers, compare with the logical netlist."""
    parent = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        parent[find(a)] = find(b)

    parts = {}
    for b in ("main", "control"):
        nets, p = read_netlist(os.path.join(OUT, f"{b}.net"))
        dup = set(parts) & set(p)
        if dup:
            print(f"  parts on both boards: {sorted(dup)}")
            return False
        parts.update(p)
        for nodes in nets.values():
            nodes = [(f"{b}:{r}" if r.startswith("#") else r, pin) for r, pin in nodes]
            for n in nodes:
                find(n)
            for n in nodes[1:]:
                union(nodes[0], n)
    hdr = [r for r in parts if r.startswith("JA")]
    for ra in hdr:
        rb = "JB" + ra[2:]
        pins = {p for r, p in parent if r == ra}
        for pin in pins:
            union((ra, pin), (rb, pin))
    comp = {}
    for n in list(parent):
        comp.setdefault(find(n), set()).add(n)
    joined = set()
    for nodes in comp.values():
        nodes = frozenset((r, p) for r, p in nodes if not r.startswith(("#", "main:", "control:", "JA", "JB")))
        if len(nodes) >= 2:
            joined.add(nodes)
    l_nets, l_parts = read_netlist(os.path.join(OUT, "logical.net"))
    logical = groups(l_nets)
    ok = joined == logical
    for g in sorted(logical - joined, key=sorted):
        print("  logical, not in the joined boards:", fmt(g))
    for g in sorted(joined - logical, key=sorted):
        print("  joined boards, not in logical:", fmt(g))
    split_parts = {r: v for r, v in parts.items() if not r.startswith(("JA", "JB"))}
    if split_parts != l_parts:
        ok = False
        for r in sorted(set(split_parts) ^ set(l_parts)):
            print(f"  part {r} only in", "the boards" if r in split_parts else "logical")
    print(f"2. main + control joined through {len(hdr)} header pairs vs logical: {len(joined)} / {len(logical)} nets,",
          "identical" if ok else "DIFFERENT")
    return ok


def check_against_alpha():
    import boards_rev_alpha as alpha
    a = groups(alpha.nets(alpha.board()))
    b = groups(read_netlist(os.path.join(OUT, "logical.net"))[0])
    b = {h for h in (frozenset(n for n in g if n[0] not in NEW_PARTS) for g in b) if len(h) >= 2}   # new parts out
    changed = (a - b) | (b - a)
    bad = [g for g in changed if not any(p in EXPECTED.get(r, set()) for r, p in g)]
    print(f"3. logical vs rev alpha: {len(a - b)} nets out, {len(b - a)} in;",
          "all at intended pins" if not bad else "UNINTENDED CHANGES:")
    for g in sorted(bad, key=sorted):
        print("   ", fmt(g))
    if "-v" in sys.argv:
        for g in sorted(a - b, key=sorted):
            print("   alpha:", fmt(g))
        for g in sorted(b - a, key=sorted):
            print("   beta: ", fmt(g))
    return not bad


if __name__ == "__main__":
    ok = check_drawn_vs_skidl()
    ok = check_split() and ok
    ok = check_against_alpha() and ok
    sys.exit(0 if ok else 1)
