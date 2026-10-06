#!/usr/bin/env python3
"""Draw the MACHINE FILTER schematic: one KiCad project (machine-filter/) holding both boards (KiKit's multiboard
workflow), the way an engineer would draw it by hand.

  1      Overview (root sheet): the two boards, how they meet, and the sheet symbols
  MAIN board (JLC PCBA), one functional area per page:
  2      power entry, Seed3 supply, -10 V reference
  3      Daisy Seed3, expansion header, clip-LED resistor
  4, 5   CV inputs 1-4 and 5-8: the ADC stages
  6      audio inputs and outputs
  7      board connectors JB1..JBn (count and pin order from pinmap.py)
  CONTROL board (hand-soldered):
  8      jacks and clip LED
  9      pots and pot multiplexer
  10, 11 CV LEDs 1-4 and 5-8: the LED drivers
  12     board connectors JA1..JAn
Pin k of JAn meets pin k of JBn. Each board's nets are its own copper: the control board's carry the prefix CTL_
(Sheet.nn), so no net spans both boards and the PCB file's DRC stays meaningful.

Parts are joined by wires inside a block (signal flow left to right, feedback above the op-amp); supply rails are
power symbols; global labels where a net leaves its page; local labels only for the expansion header.
Connectivity comes from the drawing, so it is checked afterwards against SKiDL (tools/check_netlist.py) and with
kicad-cli's ERC. Every coordinate is on the 1.27 mm grid; wires are split wherever another wire end, a pin or a
label lands on them, and junctions are added wherever three or more connections meet.

Run from the pcb directory: python3 design/gen_sch.py
"""
import math, os, sys, uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kicadlib
from kicadlib import load_symbol, pins as sym_pins
from sexpr import dump, parse, Sym, find, findall
import boards
PM = boards._pinmap()
assert PM, 'design/pinmap.py missing: run design/floorplan.py first'

HERE = os.path.dirname(os.path.abspath(__file__))
LIBDIR = os.path.join(HERE, "..", "lib")
kicadlib.SYMDIRS.insert(0, LIBDIR)
PROJECT = boards.BOARD
CTL = "CTL_"            # the control board's nets: its own copper, joined to the main board's only through JAn/JBn
# page numbers, for the cross-references printed on the sheets
PG = dict(overview=1, power=2, seed=3, cv1=4, cv2=5, audio=6, mconn=7, jacks=8, controls=9, led1=10, led2=11, cconn=12)
DATE = "2026-10-06"
REV = "beta"
FS = 1.27                                   # default text size, mm

PARTS = {p.ref: p for p in boards.board()}
NOT_DRAWN = set()       # boards.py parts deliberately left off the drawing (none)

# custom power symbols (added to the project library): name -> (stock symbol it is drawn like, description)
CUSTOM_POWER = {"+3V3_A": ("+3V3", "Power symbol: +3.3 V analog rail, from the Seed3's 3V3_A pin"),
                "+3V3_D": ("+3V3", "Power symbol: +3.3 V digital rail, from the Seed3's 3V3_D pin"),
                "VIN": ("+3V3", "Power symbol: Seed3 VIN, +12 V through R1/C5/R2/C6"),
                CTL + "GND": ("GND", "Power symbol: control board ground, joined to GND through the board connector"),
                CTL + "+12V": ("+12V", "Power symbol: control board +12 V, from the main board through the connector"),
                CTL + "-12V": ("-12V", "Power symbol: control board -12 V, from the main board through the connector"),
                CTL + "+3V3_A": ("+3V3", "Power symbol: control board +3.3 V analog, from the main board through the connector")}
STOCK_POWER = {"GND": "power:GND", "+12V": "power:+12V", "-12V": "power:-12V"}


def U():
    return str(uuid.uuid4())


def K(v):
    """Integer key (0.01 mm) for comparing coordinates."""
    return int(round(v * 100))


def on_grid(v, g=1.27):
    return abs(v / g - round(v / g)) < 1e-6


def r4(v):
    return round(v + 0.0, 4)


def font(size=FS, bold=False, italic=False):
    f = [Sym("font"), [Sym("size"), size, size]]
    if bold:
        f.append([Sym("bold"), Sym("yes")])
    if italic:
        f.append([Sym("italic"), Sym("yes")])
    return f


# ----------------------------------------------------------------------------------------- symbol geometry
def xform(px, py, rot, mirror):
    """Library point (y up) -> schematic offset (y down) for a symbol at angle rot (CCW, degrees), then mirrored
    ('x': about the x axis, 'y': about the y axis); KiCad rotates first, then mirrors."""
    x, y = px, -py
    c, s = round(math.cos(math.radians(rot))), round(math.sin(math.radians(rot)))
    x, y = x * c + y * s, -x * s + y * c
    if mirror == "x":
        y = -y
    elif mirror == "y":
        x = -x
    return r4(x), r4(y)


def _walk_pts(e, out):
    if not isinstance(e, list):
        return
    if e and e[0] in ("xy", "start", "end", "mid"):
        out.append((float(e[1]), float(e[2])))
    if e and e[0] == "circle":
        c = find(e, "center")
        rad = float(find(e, "radius")[1])
        out += [(float(c[1]) - rad, float(c[2]) - rad), (float(c[1]) + rad, float(c[2]) + rad)]
    for x in e:
        if isinstance(x, list) and x and x[0] not in ("pin", "property"):
            _walk_pts(x, out)


def body_bbox(lib, unit, rot, mirror):
    """Bounding box of a unit's graphics (not its pins), as schematic offsets (x0, y0, x1, y1)."""
    sym = load_symbol(lib)
    name = sym[1].split(":")[1]
    pts = []
    for sub in findall(sym, "symbol"):
        u = int(sub[1][len(name) + 1:].split("_")[0])
        if u in (0, unit):
            _walk_pts(sub, pts)
    if not pts:
        return (-1.27, -1.27, 1.27, 1.27)
    tp = [xform(x, y, rot, mirror) for x, y in pts]
    return (min(p[0] for p in tp), min(p[1] for p in tp), max(p[0] for p in tp), max(p[1] for p in tp))


def field_angle_and_just(rot, mirror, just):
    """For a field shown horizontally on a symbol at (rot, mirror): the angle to store, and the justification to store
    so that it shows as `just` ('left' / 'right' / None) on the sheet (KiCad applies the symbol's transform to both)."""
    a = rot % 180
    if just is None:
        return a, None
    dx, _ = xform(math.cos(math.radians(a)), math.sin(math.radians(a)), rot, mirror)
    if dx < 0:
        just = {"left": "right", "right": "left"}[just]
    return a, just


def prop(key, val, x, y, angle=0, hide=False, just=None, size=FS, bold=False):
    eff = [Sym("effects"), font(size, bold)]
    if just:
        eff.append([Sym("justify"), Sym(just)])
    if hide:
        eff.append([Sym("hide"), Sym("yes")])
    return [Sym("property"), key, val, [Sym("at"), r4(x), r4(y), angle], eff]


def sym_prop(sym, key):
    return next((p for p in findall(sym, "property") if p[1] == key), None)


# ----------------------------------------------------------------------------------------- custom power symbols
def custom_power_symbol(name):
    """A stock power symbol renamed: a global power symbol whose value (and so its net) is `name`."""
    bname, desc = CUSTOM_POWER[name]
    base = load_symbol(f"power:{bname}")
    s = [Sym("symbol"), f"filter-module:{name}"]
    for x in base[2:]:
        if isinstance(x, list) and x and x[0] == "property":
            x = list(x)
            if x[1] == "Value":
                x[2] = name
            elif x[1] == "Description":
                x[2] = desc
        elif isinstance(x, list) and x and x[0] == "symbol":
            x = list(x)
            x[1] = name + x[1][len(bname):]
        s.append(x)
    return s


def ensure_custom_power_in_lib():
    """Append the custom power symbols to lib/filter-module.kicad_sym if they are missing (a text insertion before
    the file's closing parenthesis: nothing else in the file changes), so KiCad finds them in the project library."""
    path = os.path.join(LIBDIR, "filter-module.kicad_sym")
    text = open(path).read()
    have = {s[1] for s in findall(parse(text)[0], "symbol")}
    add = []
    for name in CUSTOM_POWER:
        if name not in have:
            s = custom_power_symbol(name)
            s[1] = name
            add.append(dump(s, 1))
    if add:
        end = text.rstrip().rfind(")")
        text = text[:end].rstrip("\n") + "\n" + "".join("\t" + a + "\n" for a in add) + ")\n"
        open(path, "w").write(text)
    kicadlib._cache.pop("filter-module", None)


def lib_symbol(lib_id):
    lib, name = lib_id.split(":")
    if lib == "filter-module" and name in CUSTOM_POWER:
        return custom_power_symbol(name)
    return load_symbol(lib_id)


# ----------------------------------------------------------------------------------------- sheets
ROOT_UUID = U()
PLACED = {}            # (ref, unit) -> sheet name
PWR_COUNT = [0]


class Sheet:
    """One schematic page. Coordinates are sheet millimetres, y down."""

    def __init__(self, name, fname, page, heading, paper="A3", board=None):
        self.name, self.fname, self.page, self.heading, self.paper = name, fname, page, heading, paper
        self.board = board              # "main", "control", or None (the overview)
        self.file_uuid = ROOT_UUID if page == 1 else U()
        self.sym_uuid = None if page == 1 else U()        # uuid of this sheet's symbol on the root sheet
        self.items, self.wires, self.pinpts, self.labelpts = [], [], [], []
        self.libs = {}
        self.summary = []

    def nn(self, net):
        """The net name as drawn on this sheet: the control board's nets carry the CTL_ prefix."""
        return CTL + net if self.board == "control" else net

    @property
    def path(self):
        return f"/{ROOT_UUID}" if self.page == 1 else f"/{ROOT_UUID}/{self.sym_uuid}"

    # ---------------------------------------------------------------- symbols
    def _symbol(self, lib, x, y, rot, mirror, unit, ref, fields, flags, pins_all):
        assert on_grid(x) and on_grid(y), (ref, x, y)
        if lib not in self.libs:
            self.libs[lib] = lib_symbol(lib)
        e = [Sym("symbol"), [Sym("lib_id"), lib], [Sym("at"), r4(x), r4(y), rot]]
        if mirror:
            e.append([Sym("mirror"), Sym(mirror)])
        e += [[Sym("unit"), unit], [Sym("exclude_from_sim"), Sym("no")],
              [Sym("in_bom"), Sym(flags[0])], [Sym("on_board"), Sym(flags[1])],
              [Sym("dnp"), Sym(flags[2] if len(flags) > 2 else "no")],
              [Sym("uuid"), U()]] + fields
        for num in pins_all:
            e.append([Sym("pin"), num, [Sym("uuid"), U()]])
        e.append([Sym("instances"), [Sym("project"), PROJECT,
                                     [Sym("path"), self.path, [Sym("reference"), ref], [Sym("unit"), unit]]]])
        self.items.append(e)

    def place(self, ref, x, y, unit=1, rot=0, mirror=None, ref_at=None, val_at=None):
        """Place unit `unit` of boards part `ref` with its origin at (x, y). ref_at / val_at = (dx, dy, just): field
        positions as sheet offsets from the origin (just: 'left', 'right' or None = centred).
        Returns {pin number: (x, y)} of the unit's pin ends."""
        p = PARTS[ref]
        lib = p.cat["lib"]
        sym = load_symbol(lib)
        assert (ref, unit) not in PLACED, f"{ref} unit {unit} drawn twice"
        assert p.board == self.board, f"{ref} ({p.board} board) drawn on a {self.board} sheet"
        PLACED[(ref, unit)] = self.name
        pins, allpins = {}, []
        for (u, num, name, typ, px, py, ang, ln, hidden) in sym_pins(sym):
            if u not in (0, unit):
                continue
            allpins.append(num)
            if hidden:
                continue
            dx, dy = xform(px, py, rot, mirror)
            pins[num] = (r4(x + dx), r4(y + dy))
            self.pinpts.append(pins[num])
        c = p.cat
        is_flag = p.kind == "FLAG"
        bb = body_bbox(lib, unit, rot, mirror)
        if ref_at is None:
            ref_at = ((bb[0] + bb[2]) / 2, bb[1] - 1.9, None)
        if val_at is None:
            val_at = ((bb[0] + bb[2]) / 2, bb[3] + 1.9, None)
        fields = []
        for key, val, at, hide in (("Reference", ref, ref_at, is_flag), ("Value", c["value"], val_at, False)):
            a, j = field_angle_and_just(rot, mirror, at[2])
            fields.append(prop(key, val, x + at[0], y + at[1], a, hide=hide, just=j))
        a = rot % 180
        fields += [prop("Footprint", c["fp"], x, y, a, hide=True), prop("Datasheet", "", x, y, a, hide=True),
                   prop("Description", p.note, x, y, a, hide=True)]
        if c.get("lcsc"):
            fields.append(prop("LCSC", c["lcsc"], x, y, a, hide=True))
        if c.get("mpn"):
            fields.append(prop("MPN", c["mpn"], x, y, a, hide=True))
        fields.append(prop("Assembly", "JLC (SMD)" if c.get("lcsc") and p.board == "main" else "hand", x, y, a,
                          hide=True))
        fields.append(prop("Board", p.board, x, y, a, hide=True))
        flags = ("no" if c.get("bom") is False or is_flag else "yes", "no" if c.get("board") is False else "yes")
        self._symbol(lib, x, y, rot, mirror, unit, ref, fields, flags + ("yes" if p.dnp else "no",), allpins)
        for num, xy in pins.items():                 # no-connect flags on deliberately unused pins
            if num in p.pins and p.pins[num] is None:
                self.nc(*xy)
        return pins

    def two(self, ref, x, y, axis="h", first="1", text=None):
        """A two-pin part centred at (x, y): horizontal ('h', pin `first` on the left) or vertical ('v', pin `first`
        on top). text: 'split' / 'above' / 'below' (h), 'right' / 'left' (v).
        Returns (left or top pin end, right or bottom pin end)."""
        p = PARTS[ref]
        sym = load_symbol(p.cat["lib"])
        ps = {q[1]: q for q in sym_pins(sym) if not q[8]}
        other = next(n for n in ps if n != first)
        for rot in (0, 90, 180, 270):
            fx, fy = xform(ps[first][4], ps[first][5], rot, None)
            if (axis == "h" and fx < 0 and fy == 0) or (axis == "v" and fy < 0 and fx == 0):
                break
        else:
            raise ValueError(ref)
        bb = body_bbox(p.cat["lib"], 1, rot, None)
        text = text or ("split" if axis == "h" else "right")
        ra, va = {"split": ((0, bb[1] - 1.6, None), (0, bb[3] + 1.6, None)),
                  "above": ((0, bb[1] - 3.9, None), (0, bb[1] - 1.6, None)),
                  "below": ((0, bb[3] + 1.6, None), (0, bb[3] + 3.9, None)),
                  "right": ((bb[2] + 1.0, -1.27, "left"), (bb[2] + 1.0, 1.27, "left")),
                  "left": ((bb[0] - 1.0, -1.27, "right"), (bb[0] - 1.0, 1.27, "right"))}[text]
        pins = self.place(ref, x, y, rot=rot, ref_at=ra, val_at=va)
        return pins[first], pins[other]

    def pwr(self, net, x, y, rot=None):
        """A power symbol for `net` with its pin at (x, y). Default: GND and -12V point down, the rest up."""
        shape, net = net, self.nn(net)
        lib = STOCK_POWER.get(net) or f"filter-module:{net}"
        if rot is None:
            rot = 180 if shape == "-12V" else 0
        PWR_COUNT[0] += 1
        ref = f"#PWR{PWR_COUNT[0]:03d}"
        sym = lib_symbol(lib)
        vat, rat = find(sym_prop(sym, "Value"), "at"), find(sym_prop(sym, "Reference"), "at")
        vx, vy = xform(float(vat[1]), float(vat[2]), rot, None)
        rx, ry = xform(float(rat[1]), float(rat[2]), rot, None)
        a = rot % 180
        vjust = None
        if rot in (90, 270):                         # pointing sideways: the value just beyond the tip
            tx, _ = xform(0, -1 if shape == "GND" else 1, rot, None)
            vx, vy = 3.3 * tx, 0
            _, vjust = field_angle_and_just(rot, None, "left" if tx > 0 else "right")
        fields = [prop("Reference", ref, x + rx, y + ry, a, hide=True),
                  prop("Value", net, x + vx, y + vy, a, just=vjust),
                  prop("Footprint", "", x, y, a, hide=True), prop("Datasheet", "", x, y, a, hide=True),
                  prop("Description", sym_prop(sym, "Description")[2], x, y, a, hide=True)]
        self._symbol(lib, x, y, rot, None, 1, ref, fields, ("yes", "yes"), ["1"])
        self.pinpts.append((r4(x), r4(y)))
        return (x, y)

    def flag(self, ref, x, y, rot=0):
        """A boards.py PWR_FLAG with its pin at (x, y), pointing up (rot 0) or down (rot 180)."""
        self.place(ref, x, y, rot=rot, ref_at=(0, -1.9 if rot == 0 else 1.9, None),
                   val_at=(0, -3.81 if rot == 0 else 3.81, None))

    # ---------------------------------------------------------------- wires, labels, text
    def wire(self, *pts):
        """A polyline of horizontal and vertical wires through pts."""
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            assert on_grid(x1) and on_grid(y1) and on_grid(x2) and on_grid(y2), (self.name, x1, y1, x2, y2)
            assert K(x1) == K(x2) or K(y1) == K(y2), (self.name, "diagonal wire", x1, y1, x2, y2)
            if (K(x1), K(y1)) != (K(x2), K(y2)):
                self.wires.append((r4(x1), r4(y1), r4(x2), r4(y2)))

    def nc(self, x, y):
        self.items.append([Sym("no_connect"), [Sym("at"), r4(x), r4(y)], [Sym("uuid"), U()]])

    def glabel(self, net, x, y, toward="right", shape="passive"):
        """A global label attached at (x, y), its body pointing `toward` ('right', 'left', 'up', 'down')."""
        ang, just = {"right": (0, "left"), "left": (180, "right"), "up": (90, "left"), "down": (270, "right")}[toward]
        net = self.nn(net)
        self.labelpts.append((r4(x), r4(y)))
        self.items.append([Sym("global_label"), net, [Sym("shape"), Sym(shape)], [Sym("at"), r4(x), r4(y), ang],
                           [Sym("fields_autoplaced"), Sym("yes")],
                           [Sym("effects"), font(), [Sym("justify"), Sym(just)]], [Sym("uuid"), U()],
                           [Sym("property"), "Intersheetrefs", "${INTERSHEET_REFS}", [Sym("at"), r4(x), r4(y), ang],
                            [Sym("effects"), font(), [Sym("justify"), Sym(just)], [Sym("hide"), Sym("yes")]]]])

    def label(self, net, x, y, toward="right"):
        """A local label (a connection within this page) at (x, y); its text sits on the wire, extending `toward`."""
        ang, just = {"right": (0, "left"), "left": (180, "right")}[toward]
        net = self.nn(net)
        self.labelpts.append((r4(x), r4(y)))
        self.items.append([Sym("label"), net, [Sym("at"), r4(x), r4(y), ang],
                           [Sym("effects"), font(), [Sym("justify"), Sym(just), Sym("bottom")]], [Sym("uuid"), U()]])

    def text(self, s, x, y, size=FS, bold=False, just="left", italic=False):
        eff = [Sym("effects"), font(size, bold, italic)]
        if just:
            eff.append([Sym("justify"), Sym(just)])
        self.items.append([Sym("text"), s, [Sym("exclude_from_sim"), Sym("no")], [Sym("at"), r4(x), r4(y), 0], eff,
                           [Sym("uuid"), U()]])

    def frame(self, x0, y0, x1, y1, title=None, sub=None):
        """A dashed grey block outline with a bold title (and an italic subtitle) in its top-left corner."""
        self.items.append([Sym("rectangle"), [Sym("start"), r4(x0), r4(y0)], [Sym("end"), r4(x1), r4(y1)],
                           [Sym("stroke"), [Sym("width"), 0.1524], [Sym("type"), Sym("dash")],
                            [Sym("color"), 132, 132, 132, 1]],
                           [Sym("fill"), [Sym("type"), Sym("none")]], [Sym("uuid"), U()]])
        if title:
            self.text(title, x0 + 2.0, y0 + 3.6, size=1.8, bold=True)
        if sub:
            self.text(sub, x0 + 2.0, y0 + 6.8, italic=True)

    # ---------------------------------------------------------------- finishing
    def _finish_wires(self):
        """Split wires wherever a wire end, pin or label lands inside them; a junction where 3+ connections meet."""
        pts = set()
        for (x1, y1, x2, y2) in self.wires:
            pts |= {(K(x1), K(y1)), (K(x2), K(y2))}
        pts |= {(K(x), K(y)) for x, y in self.pinpts + self.labelpts}
        segs = []
        for (x1, y1, x2, y2) in self.wires:
            a, b = (K(x1), K(y1)), (K(x2), K(y2))
            if a[0] == b[0]:
                lo, hi = sorted((a[1], b[1]))
                cuts = sorted({lo, hi} | {p[1] for p in pts if p[0] == a[0] and lo < p[1] < hi})
                segs += [((a[0], c), (a[0], d)) for c, d in zip(cuts, cuts[1:])]
            else:
                lo, hi = sorted((a[0], b[0]))
                cuts = sorted({lo, hi} | {p[0] for p in pts if p[1] == a[1] and lo < p[0] < hi})
                segs += [((c, a[1]), (d, a[1])) for c, d in zip(cuts, cuts[1:])]
        seen = set()
        for s in segs:
            k = tuple(sorted(s))
            assert k not in seen, f"{self.name}: overlapping wires at {k}"
            seen.add(k)
        count, wire_ends = {}, {}
        for a, b in segs:
            for k in (a, b):
                count[k] = count.get(k, 0) + 1
                wire_ends[k] = wire_ends.get(k, 0) + 1
        for x, y in self.pinpts:
            k = (K(x), K(y))
            count[k] = count.get(k, 0) + 1
        lbl = {(K(x), K(y)) for x, y in self.labelpts}
        for k in wire_ends:
            if count[k] == 1 and k not in lbl:
                raise SystemExit(f"{self.name}: dangling wire end at {k[0] / 100}, {k[1] / 100}")
        out = []
        for (a, b) in segs:
            out.append([Sym("wire"), [Sym("pts"), [Sym("xy"), a[0] / 100, a[1] / 100], [Sym("xy"), b[0] / 100, b[1] / 100]],
                        [Sym("stroke"), [Sym("width"), 0], [Sym("type"), Sym("default")]], [Sym("uuid"), U()]])
        for k, n in sorted(count.items()):
            if n >= 3:
                out.append([Sym("junction"), [Sym("at"), k[0] / 100, k[1] / 100], [Sym("diameter"), 0],
                            [Sym("color"), 0, 0, 0, 0], [Sym("uuid"), U()]])
        return out

    def sexpr(self, extra=()):
        tb = [Sym("title_block"), [Sym("title"), "MACHINE FILTER"], [Sym("date"), DATE], [Sym("rev"), REV],
              [Sym("company"), "MACHINE FILTER (Seed3 build): " + (f"{self.board} board" if self.board else "both boards")],
              [Sym("comment"), 1, "Drawn by pcb/design/gen_sch.py from boards.py; netlist checked against machine_filter.py (SKiDL)."],
              [Sym("comment"), 2, "Circuit blocks after Electrosmith's Seed3 Eurorack Dev Kit Rev3 (MIT)."],
              [Sym("comment"), 3, f"Page {self.page}: {self.heading}"]]
        self.text(f"{self.page}   {self.heading}", 20.32, 24.13, size=3.0, bold=True)
        head = [Sym("kicad_sch"), [Sym("version"), Sym("20250114")], [Sym("generator"), "eeschema"],
                [Sym("generator_version"), "10.0"], [Sym("uuid"), self.file_uuid], [Sym("paper"), self.paper], tb,
                [Sym("lib_symbols")] + [self.libs[k] for k in sorted(self.libs)]]
        body = self.items + self._finish_wires() + list(extra)
        tail = []
        if self.page == 1:
            tail.append([Sym("sheet_instances"), [Sym("path"), "/", [Sym("page"), "1"]]])
        tail.append([Sym("embedded_fonts"), Sym("no")])
        return head + body + tail


# ========================================================================================= page 1: power
def power_entry(S, JX, JY):
    """J13 with its paired pins joined: +12 V pins 9/10 by a loop over the top (the P12_IN rail at JY - 10.16), -12 V
    pins 1/2 by a loop under the bottom (the N12_IN rail), and GND pins 3-8 bussed to GND on each side."""
    p = S.place("J13", JX, JY, ref_at=(0, -16.51, None), val_at=(0, -13.97, None))
    top, bot = JY - 10.16, JY + 10.16
    xl, xr = JX - 11.43, JX + 11.43
    S.wire(p["9"], (xl, p["9"][1]), (xl, top), (xr, top))
    S.wire(p["10"], (xr, p["10"][1]), (xr, top))
    S.wire(p["1"], (xl, p["1"][1]), (xl, bot), (xr, bot))
    S.wire(p["2"], (xr, p["2"][1]), (xr, bot))
    for pins_, sx in ((("7", "5", "3"), -1), (("8", "6", "4"), 1)):
        bx = JX + sx * 8.89
        for n in pins_:
            S.wire(p[n], (bx, p[n][1]))
        S.wire((bx, p[pins_[0]][1]), (bx, p[pins_[2]][1]))
        gx = JX + sx * 16.51
        S.wire((bx, JY + 2.54), (gx, JY + 2.54))
        S.pwr("GND", gx, JY + 2.54)
    S.flag("#FLG3", JX - 16.51, JY + 2.54)
    S.text("Eurorack 10-pin,", JX - 13.97, bot + 6.35)
    S.text("-12 V on the red stripe", JX - 13.97, bot + 8.89)
    return top, bot, xr


def cap_down(S, ref, x, rail_y, first="1", text="right"):
    """A capacitor hanging from a rail at (x, rail_y): a 2.54 stub, pin `first` on top, GND at the bottom."""
    a, b = S.two(ref, x, rail_y + 6.35, "v", first, text)
    S.wire((x, rail_y), a)
    S.pwr("GND", *b)


def page_power(S):
    JX, JY = 40.64, 76.2
    S.frame(15.24, 33.02, 170.18, 129.54, "Power entry", "Eurorack header, filters, reverse-polarity diodes, bulk caps")
    top, bot, xr = power_entry(S, JX, JY)
    # +12 V: P12_IN -> FB1 -> D10 -> +12V -> R1 -> VIN_F -> R2 -> VIN
    S.flag("#FLG5", 62.23, top)
    a, b = S.two("FB1", 81.28, top, "h", "1")
    S.wire((xr, top), a)
    c, d = S.two("D10", 101.6, top, "h", "2")            # anode on the left
    S.wire(b, c)
    r1a, r1b = S.two("R1", 185.42, top, "h", "1")
    S.wire(d, r1a)
    S.pwr("+12V", 114.3, top)
    S.flag("#FLG1", 127.0, top)
    cap_down(S, "C1", 139.7, top)
    cap_down(S, "C2", 154.94, top)
    # Seed3 VIN filter
    S.frame(175.26, 33.02, 271.78, 83.82, "Seed3 supply", "+12 V -> Seed3 VIN, as the Dev Kit")
    r2a, r2b = S.two("R2", 214.63, top, "h", "1")
    S.wire(r1b, r2a)
    cap_down(S, "C5", 200.66, top)
    S.wire(r2b, (259.08, top))
    cap_down(S, "C6", 231.14, top)
    S.pwr("VIN", 246.38, top)
    S.flag("#FLG4", 259.08, top)
    # -12 V: N12_IN -> FB2 -> D11 -> -12V
    S.flag("#FLG6", 62.23, bot, rot=180)
    a, b = S.two("FB2", 81.28, bot, "h", "1")
    S.wire((xr, bot), a)
    c, d = S.two("D11", 101.6, bot, "h", "1")            # cathode on the left
    S.wire(b, c)
    RX = 203.2
    S.wire(d, (RX, bot))
    S.pwr("-12V", 114.3, bot)
    S.flag("#FLG2", 127.0, bot, rot=180)
    cap_down(S, "C3", 139.7, bot, first="2")
    cap_down(S, "C4", 154.94, bot, first="2")
    S.text("D10, D11: reverse-polarity protection", 73.66, 119.38)
    S.text("FB1, FB2: 600 R at 100 MHz, 1 A", 73.66, 123.19)
    # -10 V reference: -12V -> R3 -> -10V_REF, LM4040 shunt to GND, C7
    S.frame(175.26, 88.9, 271.78, 129.54, "-10 V reference")
    a, b = S.two("R3", RX, bot + 6.35, "v", "2")
    S.wire((RX, bot), a)
    ref = bot + 12.7
    S.wire(b, (RX, ref))
    u, k = S.two("U5", RX, ref + 6.35, "v", "2", text="left")       # anode on top
    S.wire((RX, ref), u)
    S.pwr("GND", *k)
    c1, c2 = S.two("C7", RX + 12.7, ref + 6.35, "v", "1")
    S.wire((RX, ref), (RX + 12.7, ref), c1)
    S.pwr("GND", *c2)
    S.wire((RX + 12.7, ref), (RX + 25.4, ref))
    S.glabel("-10V_REF", RX + 25.4, ref, "right", "output")
    S.text("R3 1k, not the Dev Kit's 2k:", 223.52, ref + 17.78)
    S.text("eight 120k offsets draw 0.67 mA", 223.52, ref + 21.59)
    # where the rails go
    x, y = 280.67, 40.64
    S.text("Rails", x, y, size=1.8, bold=True)
    for k, (rail, use) in enumerate([("+12V, -12V", f"audio op-amps U3, U4 (page {PG['audio']}); to the control"),
                                     ("", f"board's LED drivers U7, U8 (connector, page {PG['mconn']})"),
                                     ("VIN", f"Seed3 supply input (page {PG['seed']})"),
                                     ("+3V3_A", "from the Seed3's 3V3_A pin: CV op-amps U1, U2;"),
                                     ("", "to the control board's pots and multiplexer"),
                                     ("+3V3_D", "from the Seed3's 3V3_D pin: expansion"),
                                     ("", f"header J14 (page {PG['seed']})"),
                                     ("-10V_REF", f"CV input offsets (pages {PG['cv1']}-{PG['cv2']})")]):
        S.text(rail, x, y + 5.08 + k * 3.81, bold=True)
        S.text(use, x + 19.05, y + 5.08 + k * 3.81)


def root_sheet_symbols(S, rows, w=58.42, h=30.48, gap=5.08):
    """The sub-sheet symbols on the overview: one row per board, rows = [(y, title, [sheets])]."""
    out = []
    for y, title, sheets in rows:
        S.text(title, 20.32, y - 8.89, size=2.2, bold=True)
        x = 20.32
        for sh in sheets:
            out.append([Sym("sheet"), [Sym("at"), x, y], [Sym("size"), w, h],
                        [Sym("exclude_from_sim"), Sym("no")], [Sym("in_bom"), Sym("yes")], [Sym("on_board"), Sym("yes")],
                        [Sym("dnp"), Sym("no")], [Sym("fields_autoplaced"), Sym("yes")],
                        [Sym("stroke"), [Sym("width"), 0.1524], [Sym("type"), Sym("solid")]],
                        [Sym("fill"), [Sym("color"), 0, 0, 0, 0.0]], [Sym("uuid"), sh.sym_uuid],
                        [Sym("property"), "Sheetname", sh.name, [Sym("at"), x, r4(y - 0.7116), 0],
                         [Sym("effects"), font(1.6, True), [Sym("justify"), Sym("left"), Sym("bottom")]]],
                        [Sym("property"), "Sheetfile", sh.fname, [Sym("at"), x, r4(y + h + 0.5884), 0],
                         [Sym("effects"), font(), [Sym("justify"), Sym("left"), Sym("top")]]],
                        [Sym("instances"), [Sym("project"), PROJECT,
                                            [Sym("path"), f"/{ROOT_UUID}", [Sym("page"), str(sh.page)]]]]])
            S.text(f"page {sh.page}", x + 2.54, y + 5.08, bold=True)
            for i, line in enumerate(sh.summary):
                S.text(line, x + 2.54, y + 10.16 + i * 3.81)
            x += w + gap
    return out


def HDR_TEXT(prefix):
    """'JB1 (15 pins), JB2 (13 pins), ...' from pinmap.py."""
    return ", ".join(f"{prefix}{h} ({len(PM.HEADER_PINS[h])} pins)" for h in sorted(PM.HEADER_PINS))


def page_overview(S):
    """Page 1: what the two boards are, how they meet, and the net-naming rule."""
    S.frame(15.24, 33.02, 404.86, 101.6, "Two boards, one module",
            "one KiCad project; the PCB file holds both boards side by side, cut apart for fabrication by tools/separate.sh (KiKit)")
    lines = [
        ("MAIN board", True),
        ("JLC SMD assembly, 70 x 100 mm. Back: Daisy Seed3 on sockets, power entry, CV ADC stages U1/U2, audio U3/U4,", False),
        ("-10 V reference U5, expansion header J14, optional microSD J15 (DNP). Front: male headers " + HDR_TEXT("JB") + ".", False),
        ("CONTROL board", True),
        ("Hand-soldered, 70 x 107 mm. Front: 12 jacks, 9 pots, 9 LEDs. Back: pot multiplexer U6, LED drivers U7/U8 (SOIC),", False),
        ("through-hole resistors and capacitors, female headers " + ", ".join("JA" + h for h in sorted(PM.HEADER_PINS)) + ".", False),
        ("How they meet", True),
        ("JAn plugs onto JBn, pin k to pin k, about 11 mm apart. Every net on the control board is its own copper, so it has its", False),
        ("own name: the main board's name with the prefix CTL_ (CTL_GND, CTL_+12V, CTL_CV_BASE, ...). CTL_x meets x only at", False),
        ("the header pins (pages %d and %d), as in the hardware. tools/check_netlist.py checks that the boards joined there are" % (PG["mconn"], PG["cconn"]), False),
        ("exactly the one-circuit SKiDL netlist (machine_filter.py).", False),
    ]
    y = 48.26
    for text, bold in lines:
        if bold:
            y += 1.27
        S.text(text, 20.32, y, size=1.6 if bold else FS, bold=bold)
        y += 4.45 if bold else 3.81



def opamp_supply(S, ref, unit, X, Y, caps):
    """An op-amp's power unit at (X, Y) with its rails as power symbols and its decoupling caps wired to its pins:
    one cap (rail to GND) or two (V+ to GND, GND to V-) stacked to the right."""
    p = PARTS[ref]
    pins = S.place(ref, X, Y, unit=unit, ref_at=(-6.35, -1.27, "right"), val_at=(-6.35, 1.27, "right"))
    (tn, top), (bn, bot) = sorted(pins.items(), key=lambda kv: kv[1][1])
    px = top[0]
    jt, jb = top[1] - 2.54, bot[1] + 2.54
    S.wire(top, (px, jt - 2.54))
    S.pwr(p.pins[tn], px, jt - 2.54)
    S.wire(bot, (px, jb + 2.54))
    S.pwr(p.pins[bn], px, jb + 2.54)
    cx = px + 10.16
    mid = (jt + jb) / 2
    if len(caps) == 1:
        a, b = S.two(caps[0], cx, mid, "v", "1")
        S.wire((px, jt), (cx, jt), a)
        S.wire((px, jb), (cx, jb), b)
    else:
        a, b = S.two(caps[0], cx, mid - 3.81, "v", "1")
        c, d = S.two(caps[1], cx, mid + 3.81, "v", "1")
        S.wire((px, jt), (cx, jt), a)
        S.wire((px, jb), (cx, jb), d)
        S.wire((cx, mid), (cx + 12.7, mid))
        S.pwr("GND", cx + 12.7, mid)


def opamp_stage(S, u, unit, XN, Y, rf, cf):
    """An inverting op-amp stage: the - input node at (XN, Y), the op-amp (- input on top), + input to GND,
    R_f // C_f above. Returns the output node (on the output row, Y + 2.54)."""
    XO = XN + 12.7
    op = S.place(u, XO, Y + 2.54, unit=unit, mirror="x", ref_at=(1.27, 6.35, "left"), val_at=(1.27, 8.89, "left"))
    inv, plus, out = [op[k] for k in sorted(op, key=lambda k: op[k])]
    S.wire((XN, Y), inv)
    S.wire(plus, (plus[0], Y + 7.62))
    S.pwr("GND", plus[0], Y + 7.62)
    NO = XO + 12.7
    XF = (XN + NO) / 2
    S.wire((XN, Y), (XN, Y - 17.78))
    S.wire(out, (NO, Y + 2.54))
    S.wire((NO, Y + 2.54), (NO, Y - 17.78))
    a, b = S.two(rf, XF, Y - 7.62, "h", "1")
    S.wire((XN, Y - 7.62), a)
    S.wire(b, (NO, Y - 7.62))
    a, b = S.two(cf, XF, Y - 17.78, "h", "1")
    S.wire((XN, Y - 17.78), a)
    S.wire(b, (NO, Y - 17.78))
    return (NO, Y + 2.54)


# ========================================================================================= control board, page 2
def page_controls(S):
    MX, MY = 58.42, 116.84
    PY = MY - 33.02
    S.frame(15.24, 50.8, 248.92, 149.86, "Pots and pot multiplexer",
            "pots: CCW end to GND, CW end to +3V3_A (from the main board); VOLUME has its own ADC pin, the other eight share one")
    m = S.place("U6", MX, MY, ref_at=(3.81, -17.78, "left"), val_at=(3.81, -15.24, "left"))
    mux = PARTS["U6"].pins
    # Seed side: the common output and the select inputs
    for num, net in mux.items():
        x, y = m[num]
        if net in ("POT_MUX", "MUX_A", "MUX_B", "MUX_C"):
            S.wire((x, y), (x - 7.62, y))
            S.glabel(net, x - 7.62, y, "left", "output" if net == "POT_MUX" else "input")
    e = m["6"]
    S.wire(e, (e[0] - 2.54, e[1]), (e[0] - 2.54, e[1] + 2.54))
    S.pwr("GND", e[0] - 2.54, e[1] + 2.54)
    g, v = m["8"], m["7"]
    S.wire(g, (g[0], g[1] + 5.08))
    S.wire(v, (v[0], v[1] + 2.54), (g[0], v[1] + 2.54))
    S.pwr("GND", g[0], g[1] + 5.08)
    vcc = m["16"]
    S.wire(vcc, (vcc[0], vcc[1] - 15.24))
    S.pwr("+3V3_A", vcc[0], vcc[1] - 15.24)
    S.wire((vcc[0], vcc[1] - 12.7), (vcc[0] - 10.16, vcc[1] - 12.7))
    a, b = S.two("C80", vcc[0] - 10.16, vcc[1] - 8.89, "v", "1", text="left")
    S.pwr("GND", *b)
    # the eight multiplexed pots, wired as a staircase to A0 ... A7: drawn in channel order (left to right = top to
    # bottom on U6's symbol), so the staircase has no crossings; the label over each pot names it.
    pin_of = {name: next(n for n, net in mux.items() if net == f"POT_{name}") for name in boards.CV_NAMES}
    for k, name in enumerate(sorted(boards.CV_NAMES, key=lambda nm: m[pin_of[nm]][1])):
        PX = MX + 30.48 + 20.32 * k
        pp = S.place(f"RV{2 + boards.CV_NAMES.index(name)}", PX, PY, ref_at=(-2.54, -1.27, "right"), val_at=(-2.54, 1.27, "right"))
        S.pwr("+3V3_A", *pp["3"])
        S.pwr("GND", *pp["1"])
        ch = next(n for n, net in mux.items() if net == f"POT_{name}")
        w, c = pp["2"], m[ch]
        S.wire(w, (w[0], c[1]), c)
        S.text(boards.CV_LABEL[name], PX, PY - 15.24, bold=True, just=None)
    # VOLUME: its own ADC pin
    VX = 27.94
    pp = S.place("RV1", VX, PY, ref_at=(-2.54, -1.27, "right"), val_at=(-2.54, 1.27, "right"))
    S.pwr("+3V3_A", *pp["3"])
    S.pwr("GND", *pp["1"])
    S.wire(pp["2"], (pp["2"][0] + 7.62, PY))
    S.glabel("POT_VOL", pp["2"][0] + 7.62, PY, "right", "output")
    S.text("VOLUME", VX, PY - 15.24, bold=True, just=None)
    S.text("U6 passes one of the 8 pot wipers to POT_MUX; the Seed selects it with MUX_A/B/C (S0/S1/S2).",
           MX + 22.86, MY + 22.86)
    S.text(f"CTL_POT_MUX, CTL_POT_VOL, CTL_MUX_A/B/C go to the Seed3 on the main board, through the board connector (page {PG['cconn']}).",
           MX + 22.86, MY + 26.67)
    S.text("Channel order follows the floorplan (design/pinmap.py); the firmware maps it.", MX + 22.86, MY + 30.48)


# ========================================================================================= main board, page 2
def page_seed(S):
    AX, AY = 99.06, 101.6
    S.frame(15.24, 33.02, 195.58, 160.02, "Daisy Seed3", "on two 1x20 sockets, on the main board's back")
    p = S.place("A1", AX, AY, ref_at=(-21.59, -32.385, "left"), val_at=(21.59, -32.385, "right"))
    to_seed = {"POT_MUX", "POT_VOL", "CODEC_IN_L", "CODEC_IN_R"} | {f"ADC_{n}" for n in boards.CV_NAMES}
    local = {"USB_DM", "USB_DP", "MIDI_TX", "MIDI_RX", "SD_D0", "SD_D1", "SD_D2", "SD_D3", "SD_CMD", "SD_CK"}
    for num, net in PARTS["A1"].pins.items():
        if not net or net in ("GND", "VIN", "+3V3_A", "+3V3_D", "LED_CLIP"):
            continue
        x, y = p[num]
        side = -1 if x < AX else 1
        toward = "left" if side < 0 else "right"
        if net in local:
            S.wire((x, y), (x + side * 12.7, y))
            S.label(net, x + side * 12.7, y, toward)
        else:
            S.wire((x, y), (x + side * 5.08, y))
            S.glabel(net, x + side * 5.08, y, toward, "input" if net in to_seed else "output")
    vin, d3, a3 = p["39"], p["38"], p["21"]
    S.wire(vin, (vin[0], AY - 38.1), (AX - 12.7, AY - 38.1), (AX - 12.7, AY - 43.18))
    S.pwr("VIN", AX - 12.7, AY - 43.18)
    S.wire(d3, (AX, AY - 43.18))
    S.pwr("+3V3_D", AX, AY - 43.18)
    S.wire(a3, (a3[0], AY - 38.1), (AX + 12.7, AY - 38.1), (AX + 12.7, AY - 43.18))
    S.pwr("+3V3_A", AX + 12.7, AY - 43.18)
    dg, ag = p["40"], p["20"]
    S.wire(dg, (dg[0], AY + 38.1), (ag[0], AY + 38.1), ag)
    S.wire((AX, AY + 38.1), (AX, AY + 40.64))
    S.pwr("GND", AX, AY + 40.64)
    # clip LED: pin 12 -> R70 -> LED_A, through the header to D1 on the control board
    x, y = p["12"]
    a, b = S.two("R70", x + 10.16, y, "h", "1")
    S.wire((x, y), a)
    S.wire(b, (b[0] + 7.62, y))
    S.glabel("LED_A", b[0] + 7.62, y, "right", "output")
    S.text("clip LED D1 on the control board;", x + 38.1, y + 1.27)
    S.text("~1.4 mA at 3.3 V", x + 38.1, y + 3.81)
    seed_adc = sorted(PM.SEED_ADC.items(), key=lambda kv: int(kv[1]))
    for k, line in enumerate([f"ADC_*: CV inputs, pages {PG['cv1']}-{PG['cv2']}; POT_MUX, POT_VOL, MUX_*, LED_A: board connector, page {PG['mconn']}",
                              f"CODEC_IN/OUT_*: audio, page {PG['audio']};  VIN: power, page {PG['power']}",
                              "ADC pins, op-amp sections and mux channels follow the floorplan (design/pinmap.py);",
                              "the firmware maps them: " + ", ".join(f"{p}={s.replace('ADC_', '')}" for s, p in seed_adc[:5]),
                              "  " + ", ".join(f"{p}={s.replace('ADC_', '')}" for s, p in seed_adc[5:])]):
        S.text(line, 20.32, 143.51 + k * 3.81, italic=True)
    EX, EY = 241.3, 68.58
    S.frame(203.2, 33.02, 284.48, 99.06, "Expansion header", "to the 2HP USB-C / MIDI expander")
    j = S.place("J14", EX, EY, ref_at=(1.27, -6.35, None), val_at=(1.27, 8.89, None))
    for num, net in PARTS["J14"].pins.items():
        x, y = j[num]
        side = -1 if x < EX else 1
        if net in local:
            S.wire((x, y), (x + side * 17.78, y))
            S.label(net, x + side * 17.78, y, "left" if side < 0 else "right")
        else:
            S.wire((x, y), (x + side * 5.08, y))
            if net == "GND":
                S.pwr("GND", x + side * 5.08, y, rot=90 if side > 0 else 270)
            else:
                S.pwr(net, x + side * 5.08, y, rot=90 if side < 0 else 270)
    S.text("ribbon: pin = wire", EX - 6.35, EY + 15.24, italic=True)
    S.text("USB_DM/DP, MIDI_TX/RX: Seed3 pins 36/37, 14/15 (USART1)", 207.01, EY + 24.13, italic=True)
    page_sd(S)


def page_sd(S):
    """The optional microSD socket J15 (DNP), as the Dev Kit: SDMMC1 on Seed3 pins 2-7, 47k pull-ups on CMD and
    D0-D3 to +3V3_D, CK direct, card detect unused."""
    X0, Y0 = 289.56, 33.02
    S.frame(X0, Y0, 406.4, 104.14, "microSD (optional)", "J15 DNP: fit per build; the pull-ups are always fitted")
    JX, JY = X0 + 76.2, Y0 + 45.72
    j = S.place("J15", JX, JY, ref_at=(-12.7, -12.7, "left"), val_at=(-12.7, 12.7, "left"))
    RY = JY - 20.32                                              # the +3V3_D rail for the pull-ups
    pulls = {"SD_D2": "R100", "SD_D3": "R101", "SD_CMD": "R102", "SD_D0": "R103", "SD_D1": "R104"}
    net_of = PARTS["J15"].pins
    rx = X0 + 12.7
    xs = [rx + 7.62 + 7.62 * k for k in range(5)]
    for num in sorted((n for n in j if (net_of.get(n) or "").startswith("SD_")), key=lambda n: j[n][1]):
        x, y = j[num]
        net = net_of[num]
        S.wire((x, y), (rx, y))
        S.label(net, rx, y, "left")
        if net in pulls:
            px = xs[list(pulls).index(net)]
            a, b = S.two(pulls[net], px, RY + 6.35, "v", "2", text="right")
            S.wire(b, (px, y))
            S.wire(a, (px, RY))
    S.wire((xs[0], RY), (xs[-1], RY), (xs[-1] + 5.08, RY))
    S.pwr("+3V3_D", xs[-1] + 5.08, RY)
    # right side: VDD to +3V3_D with C100; VSS and the shield to GND
    vx = JX + 25.4
    vdd, vss, sh = j["4"], j["6"], j["MP1"]
    S.wire(vdd, (vx, vdd[1]), (vx, RY))
    S.pwr("+3V3_D", vx, RY)
    S.wire((vx, RY + 2.54), (vx + 7.62, RY + 2.54))
    cap_down(S, "C100", vx + 7.62, RY + 2.54)
    gx = vss[0] + 2.54
    S.wire(vss, (gx, vss[1]))
    S.wire(sh, (gx, sh[1]))
    S.wire((gx, sh[1]), (gx, vss[1] + 5.08))
    S.pwr("GND", gx, vss[1] + 5.08)
    S.text("SD_*: Seed3 pins 2-7 (SDMMC1). Firmware enables SD only if the socket is fitted.", X0 + 2.54, 101.6,
           italic=True)


# ========================================================================================= main board, pages 3-4
def cv_adc(S, i, X, Y):
    """CV input i's ADC stage (main board): CV_n from the board connector -> R_in -> inverting stage (R_f // C_f
    above, R_off to -10V_REF below) -> ADC_n. Vout = 1.667 V - Vin / 6."""
    n = boards.CV_NAMES[i]
    prec = n in boards.ONE_V_OCT
    u, unit = PM.ADC_UNIT[n]
    S.frame(X - 15.24, Y - 30.48, X + 107.95, Y + 22.86, f"CV {i + 1}: {boards.CV_LABEL[n]}",
            "R_in = 100k + 20k, both 0.1 % (1V/OCT input)" if prec else "from the jack, via the board connector")
    XA = X + 15.24
    S.glabel(f"CV_{n}", XA, Y, "left", "input")
    XN = XA + 27.94
    if prec:
        a, b = S.two(f"R{10 + 4 * i}", XA + 7.62, Y, "h", "1")
        c, d = S.two(f"R{13 + 4 * i}", XA + 20.32, Y, "h", "1")
        S.wire((XA, Y), a)
        S.wire(b, c)
        S.wire(d, (XN, Y))
    else:
        a, b = S.two(f"R{10 + 4 * i}", XA + 12.7, Y, "h", "1")
        S.wire((XA, Y), a)
        S.wire(b, (XN, Y))
    XN2, XO = XN + 5.08, XN + 17.78
    op = S.place(u, XO, Y + 2.54, unit=unit, mirror="x", ref_at=(1.27, 6.35, "left"), val_at=(1.27, 8.89, "left"))
    inv, plus, out = [op[k] for k in sorted(op, key=lambda k: op[k])]
    S.wire((XN, Y), (XN2, Y), inv)
    S.wire(plus, (plus[0], Y + 7.62))
    S.pwr("GND", plus[0], Y + 7.62)
    NO = XO + 12.7
    S.wire(out, (NO, Y + 2.54), (NO + 7.62, Y + 2.54))
    S.glabel(f"ADC_{n}", NO + 7.62, Y + 2.54, "right", "output")
    XF = XN + 15.24
    S.wire((XN, Y), (XN, Y - 17.78))
    S.wire((NO, Y + 2.54), (NO, Y - 17.78))
    a, b = S.two(f"R{11 + 4 * i}", XF, Y - 7.62, "h", "1")
    S.wire((XN, Y - 7.62), a)
    S.wire(b, (NO, Y - 7.62))
    a, b = S.two(f"C{10 + i}", XF, Y - 17.78, "h", "1")
    S.wire((XN, Y - 17.78), a)
    S.wire(b, (NO, Y - 17.78))
    a, b = S.two(f"R{12 + 4 * i}", XN2, Y + 6.35, "v", "1", text="left")
    S.wire((XN2, Y), a)
    S.wire(b, (XN2, Y + 12.7), (XN2 - 2.54, Y + 12.7))
    S.glabel("-10V_REF", XN2 - 2.54, Y + 12.7, "left", "input")
    S.text("Vout = 1.667 V - Vin / 6:", NO + 2.54, Y + 8.89)
    S.text("±8 V -> 0.33 ... 3.0 V", NO + 2.54, Y + 11.43)
    S.text("C_f: 8 kHz low-pass", NO + 2.54, Y + 13.97)


def supplies_frame(S, quads, kind, X0=289.56, Y0=38.1):
    """The power units of `quads` (each drawn on the first page that uses it) with their decoupling caps."""
    S.frame(X0, Y0, X0 + 110.49, Y0 + 68.58, "Op-amp supplies")
    for k, q in enumerate(quads):
        x = X0 + 5.08 + k * 50.8
        if kind == "adc":
            S.text(f"{q}: LMV324, ADC stages", x, Y0 + 12.7, bold=True)
            opamp_supply(S, q, 5, x + 17.78, Y0 + 38.1, [{"U1": "C20", "U2": "C21"}[q]])
        else:
            S.text(f"{q}: LM324, LED drivers", x, Y0 + 12.7, bold=True)
            opamp_supply(S, q, 5, x + 17.78, Y0 + 38.1, {"U7": ["C81", "C82"], "U8": ["C83", "C84"]}[q])


def page_cv_main(S, first, drawn_supplies):
    XS, YS = (35.56, 167.64), (73.66, 165.1)
    for k in range(4):
        cv_adc(S, first + k, XS[k % 2], YS[k // 2])
    quads = [q for q in dict.fromkeys(PM.ADC_UNIT[n][0] for n in boards.CV_NAMES[first:first + 4])
             if q not in drawn_supplies]
    drawn_supplies |= set(quads)
    if quads:
        supplies_frame(S, quads, "adc")
    for k, line in enumerate(["Each CV jack (control board) arrives here through the board connector and feeds",
                              "an inverting stage that scales ±8 V into the Seed's 0 ... 3.3 V ADC range",
                              f"(ADC_* go to page {PG['seed']}). The same CV drives its LED on the control board.",
                              "Op-amp sections and ADC pins follow the floorplan (design/pinmap.py)."]):
        S.text(line, 292.1, 119.38 + k * 3.81, bold=(k == 0))


# ========================================================================================= control board, pages 3-4
def cv_led(S, i, X, Y):
    """CV i's LED driver (control board): CV_n -> 10k -> LM324 + input (1M to GND); the bicolour LED from the output
    to the - input, 1.5k from the - input to GND: LED current = CV / 1.5k, green +, red -."""
    n = boards.CV_NAMES[i]
    ul, unit = PM.LED_UNIT[n]
    S.frame(X - 15.24, Y - 12.7, X + 107.95, Y + 33.02, f"CV {i + 1}: {boards.CV_LABEL[n]} LED")
    XA = X + 15.24
    S.glabel(f"CV_{n}", XA, Y, "left", "input")
    a, b = S.two(f"R{80 + i}", XA + 7.62, Y, "h", "1")
    S.wire((XA, Y), a)
    XB, XO2 = XA + 17.78, XA + 45.72
    op2 = S.place(ul, XO2, Y + 2.54, unit=unit, ref_at=(1.27, -7.62, "left"), val_at=(1.27, -5.08, "left"))
    plus2, minus2, out2 = [op2[k] for k in sorted(op2, key=lambda k: op2[k])]
    assert plus2 == (r4(XO2 - 7.62), r4(Y))
    S.wire(b, (XB, Y), plus2)
    c, d = S.two(f"R{90 + i}", XB, Y + 6.35, "v", "1")
    S.wire((XB, Y), c)
    S.pwr("GND", *d)
    LR = Y + 15.24
    XD, XC = XO2 - 12.7, XO2 + 12.7
    led = S.place(f"D{2 + i}", XO2 + 5.08, LR, ref_at=(0, 6.35, None), val_at=(0, 8.89, None))
    assert led["1"] == (r4(XC), r4(LR))
    S.wire(minus2, (XD, minus2[1]), (XD, LR), led["2"])
    S.wire(out2, (XC, out2[1]), led["1"])
    a, b = S.two(f"R{71 + i}", XD, LR + 3.81, "v", "1", text="left")
    assert a == (r4(XD), r4(LR))
    S.pwr("GND", *b)
    S.text("LED current = CV / 1.5k", XC + 5.08, Y + 7.62)
    S.text("green +, red -", XC + 5.08, Y + 10.16)


def page_cv_control(S, first, drawn_supplies):
    XS, YS = (35.56, 167.64), (66.04, 124.46)
    for k in range(4):
        cv_led(S, first + k, XS[k % 2], YS[k // 2])
    quads = [q for q in dict.fromkeys(PM.LED_UNIT[n][0] for n in boards.CV_NAMES[first:first + 4])
             if q not in drawn_supplies]
    drawn_supplies |= set(quads)
    if quads:
        supplies_frame(S, quads, "led")
    for k, line in enumerate(["Each CV jack also lights a 2-lead red/green LED by it:",
                              "an LM324 with the LED in its feedback loop (after Mutable Instruments' Shades):",
                              "LED current = CV / 1.5k, no dead zone, levelling off near 5.5-6 mA from about ±8.5 V.",
                              "10k: input protection; 1M: an undriven cable reads 0 V, LED dark.",
                              "Through-hole resistors and capacitors (hand-soldered); U7, U8 SOIC (hand-soldered)."]):
        S.text(line, 292.1, 119.38 + k * 3.81, bold=(k == 0))


# ========================================================================================= main board, page 5
def audio_in(S, side, X, Y):
    """IN_side from the board connector -> inverting stage, gain -0.1 (100k in, 10k // 330p) -> 100R -> CODEC_IN."""
    s = {"L": dict(rin="R50", rf="R51", cf="C50", rs="R52", u=1),
         "R": dict(rin="R54", rf="R55", cf="C52", rs="R56", u=2)}[side]
    XA = X + 15.24
    S.glabel(f"IN_{side}", XA, Y, "left", "input")
    a, b = S.two(s["rin"], XA + 8.89, Y, "h", "1")
    S.wire((XA, Y), a)
    XN = XA + 20.32
    S.wire(b, (XN, Y))
    no = opamp_stage(S, "U3", s["u"], XN, Y, s["rf"], s["cf"])
    a, b = S.two(s["rs"], no[0] + 8.89, no[1], "h", "1")
    S.wire(no, a)
    S.wire(b, (no[0] + 20.32, no[1]))
    S.glabel(f"CODEC_IN_{side}", no[0] + 20.32, no[1], "right", "output")


def audio_out(S, side, X, Y):
    """CODEC_OUT -> inverting stage, gain -5.1 (10k in, 51k // 47p) -> 100R -> OUT_side, to the board connector."""
    s = {"L": dict(rin="R60", rf="R61", cf="C60", rs="R62", u=1),
         "R": dict(rin="R64", rf="R65", cf="C62", rs="R66", u=2)}[side]
    S.glabel(f"CODEC_OUT_{side}", X, Y, "left", "input")
    a, b = S.two(s["rin"], X + 8.89, Y, "h", "1")
    S.wire((X, Y), a)
    XN = X + 17.78
    S.wire(b, (XN, Y))
    no = opamp_stage(S, "U4", s["u"], XN, Y, s["rf"], s["cf"])
    a, b = S.two(s["rs"], no[0] + 8.89, no[1], "h", "1")
    S.wire(no, a)
    S.wire(b, (no[0] + 20.32, no[1]))
    S.glabel(f"OUT_{side}", no[0] + 20.32, no[1], "right", "output")


def page_audio(S):
    YL, YR = 68.58, 116.84
    X = 20.32
    S.frame(15.24, 33.02, 142.24, 137.16, "Audio in", "gain -0.1 (100k / 10k), as the Dev Kit")
    audio_in(S, "L", X, YL)
    audio_in(S, "R", X, YR)
    S.frame(147.32, 33.02, 279.4, 137.16, "Audio out", "gain -5.1 (10k / 51k): 0 dBFS = ±7.1 V, below the TL072's swing")
    audio_out(S, "L", 167.64, YL)
    audio_out(S, "R", 167.64, YR)
    S.frame(15.24, 142.24, 142.24, 194.31, "Op-amp supplies")
    S.text("U3: TL072, inputs", 25.4, 151.13, bold=True)
    opamp_supply(S, "U3", 3, 43.18, 172.72, ["C70", "C71"])
    S.text("U4: TL072, outputs", 83.82, 151.13, bold=True)
    opamp_supply(S, "U4", 3, 101.6, 172.72, ["C72", "C73"])
    for k, line in enumerate(["IN_L / IN_R / OUT_L / OUT_R: the audio jacks, on the control board,",
                              f"through the board connector (page {PG['mconn']}). IN R is normalled to IN L there."]):
        S.text(line, 147.32, 151.13 + k * 3.81, italic=True)


# ========================================================================================= both boards: connector page
def page_connectors(S, board):
    """The board-to-board headers, each pin to its net. JAn (control) pin k meets JBn (main) pin k."""
    prefix = "JA" if board == "control" else "JB"
    names = sorted(PM.HEADER_PINS)
    S.frame(15.24, 33.02, 279.4, 162.56, "Board-to-board connector",
            f"{len(names)} single-row 2.54 mm headers: JA* female on the control board's back, JB* male on the main "
            "board's front")
    orient = {0: "pins run down", 90: "pins run right", 180: "pins run up", 270: "pins run left"}
    for k, h in enumerate(names):
        ref = f"{prefix}{h}"
        X, Y = 60.96 + k * 66.04, 83.82
        p = S.place(ref, X, Y, ref_at=(1.27, -2.54 * (len(PM.HEADER_PINS[h]) / 2 + 2.5), None),
                    val_at=(1.27, -2.54 * (len(PM.HEADER_PINS[h]) / 2 + 1.5), None))
        for num, net in PARTS[ref].pins.items():
            x, y = p[num]
            side = -1 if x < X else 1
            S.wire((x, y), (x + side * 7.62, y))
            if net == "GND":
                S.pwr("GND", x + side * 7.62, y, rot=90 if side > 0 else 270)
            elif net in ("+12V", "-12V", "+3V3_A"):
                S.pwr(net, x + side * 7.62, y, rot=90 if side < 0 else 270)
            else:
                S.glabel(net, x + side * 7.62, y, "left" if side < 0 else "right", "passive")
        x0, y0, rot, _ = PM.HEADER_POS[h]
        yb = max(v[1] for v in p.values()) + 6.35
        S.text(f"{ref}: pin 1 at ({x0}, {y0}) mm,", X - 22.86, yb, italic=True)
        S.text(f"panel frame; {orient[rot]} (main side)", X - 22.86, yb + 3.81, italic=True)
    if board == "control":       # the control board's supplies arrive through the headers: a PWR_FLAG on each
        S.text("Supplies from the main board (PWR_FLAG: driven through the connector)", 20.32, 133.35, italic=True)
        for k, (net, fl) in enumerate((("+12V", "#FLG11"), ("-12V", "#FLG12"), ("+3V3_A", "#FLG13"), ("GND", "#FLG14"))):
            x, y = 27.94 + k * 30.48, 144.78
            S.wire((x, y), (x + 12.7, y))
            S.pwr(net, x, y)
            S.flag(fl, x + 12.7, y)
    S.text("Header groups, positions and pin order come from the floorplan (design/headers.py): analog pairs, then "
           "digital pairs, a GND after each pair; supplies between GNDs.", 20.32, 158.75, italic=True)


# ========================================================================================= control board, page 1
def page_jacks(S):
    """Control board root page: the twelve jacks (tips to the connector), the audio input normalling, the clip LED."""
    S.frame(15.24, 33.02, 160.02, 129.54, "Audio jacks", "IN R normalled to IN L; OUT jacks' switch unused")
    for k, (ref, net) in enumerate((("J3", "OUT_L"), ("J4", "OUT_R"), ("J1", "IN_L"), ("J2", "IN_R"))):
        X, Y = 38.1 + (k % 2) * 63.5, 55.88 + (k // 2) * 40.64
        j = S.place(ref, X, Y + 2.54, mirror="y", ref_at=(-1.27, -5.08, None), val_at=(-1.27, 7.62, None))
        S.text(PARTS[ref].note.split(" (")[0], X - 7.62, Y + 3.0, just="right", bold=True)
        S.wire(j["TIP"], (X + 15.24, Y))
        S.glabel(net, X + 15.24, Y, "right", "passive")
        g = j["GND"]
        if ref == "J1":
            S.wire(j["NORM"], (X + 10.16, Y + 2.54), (X + 10.16, Y + 7.62))
            S.wire(g, (X + 10.16, Y + 5.08))
            S.pwr("GND", X + 10.16, Y + 7.62)
        elif ref == "J2":
            S.wire(j["NORM"], (X + 12.7, Y + 2.54), (X + 12.7, Y + 12.7), (X + 15.24, Y + 12.7))
            S.glabel("IN_L", X + 15.24, Y + 12.7, "right", "passive")
            S.text("normal: IN L", X + 25.4, Y + 16.51, italic=True)
            S.wire(g, (X + 10.16, Y + 5.08), (X + 10.16, Y + 7.62))
            S.pwr("GND", X + 10.16, Y + 7.62)
        else:
            S.wire(g, (X + 10.16, Y + 5.08), (X + 10.16, Y + 7.62))
            S.pwr("GND", X + 10.16, Y + 7.62)
    S.frame(165.1, 33.02, 396.24, 129.54, "CV jacks", "unplugged: the switch grounds the input (0 V, LED dark)")
    for i, n in enumerate(boards.CV_NAMES):
        X, Y = 187.96 + (i % 2) * 106.68, 50.8 + (i // 2) * 20.32
        j = S.place(f"J{5 + i}", X, Y + 2.54, mirror="y", ref_at=(-1.27, -5.08, None), val_at=(-1.27, 7.62, None))
        S.text(boards.CV_LABEL[n], X - 7.62, Y + 3.0, just="right", bold=True)
        S.wire(j["TIP"], (X + 15.24, Y))
        S.glabel(f"CV_{n}", X + 15.24, Y, "right", "passive")
        S.wire(j["NORM"], (X + 10.16, Y + 2.54), (X + 10.16, Y + 7.62))
        S.wire(j["GND"], (X + 10.16, Y + 5.08))
        S.pwr("GND", X + 10.16, Y + 7.62)
    S.frame(15.24, 137.16, 160.02, 182.88, "Clip LED", "driven from the Seed3 through R70 on the main board")
    d = S.place("D1", 66.04, 160.02, mirror="y", ref_at=(1.27, -5.08, None), val_at=(1.27, 6.35, None))
    S.wire(d["2"], (d["2"][0] - 7.62, 160.02))
    S.glabel("LED_A", d["2"][0] - 7.62, 160.02, "left", "input")
    S.wire(d["1"], (d["1"][0] + 5.08, 160.02), (d["1"][0] + 5.08, 165.1))
    S.pwr("GND", d["1"][0] + 5.08, 165.1)
    S.text("clip LED, 2 o'clock from VOLUME", 78.74, 160.02)


# ========================================================================================= main
def generate(outdir):
    ensure_custom_power_in_lib()
    drawn = set()
    M, C = "main", "control"
    root = Sheet("Overview", f"{PROJECT}.kicad_sch", PG["overview"], "MACHINE FILTER: two boards", "A3")
    main = [Sheet("Main: power", "main-power.kicad_sch", PG["power"], "Main board: power entry, Seed3 supply, -10 V reference",
                  board=M),
            Sheet("Main: Daisy Seed3", "main-seed3.kicad_sch", PG["seed"],
                  "Main board: Daisy Seed3, expansion header, clip-LED resistor, optional microSD", "A3", M),
            Sheet("Main: CV inputs 1-4", "main-cv-inputs-1-4.kicad_sch", PG["cv1"], "Main board: CV inputs 1-4, ADC stages",
                  board=M),
            Sheet("Main: CV inputs 5-8", "main-cv-inputs-5-8.kicad_sch", PG["cv2"], "Main board: CV inputs 5-8, ADC stages",
                  board=M),
            Sheet("Main: audio", "main-audio.kicad_sch", PG["audio"], "Main board: audio inputs and outputs", "A4", M),
            Sheet("Main: connector", "main-connector.kicad_sch", PG["mconn"], "Main board: board-to-board connector", "A4", M)]
    ctl = [Sheet("Control: jacks", "control-jacks.kicad_sch", PG["jacks"], "Control board: jacks and clip LED", board=C),
           Sheet("Control: pots", "control-pots.kicad_sch", PG["controls"], "Control board: pots and pot multiplexer", "A4", C),
           Sheet("Control: CV LEDs 1-4", "control-cv-leds-1-4.kicad_sch", PG["led1"], "Control board: CV LEDs 1-4, LED drivers",
                 board=C),
           Sheet("Control: CV LEDs 5-8", "control-cv-leds-5-8.kicad_sch", PG["led2"], "Control board: CV LEDs 5-8, LED drivers",
                 board=C),
           Sheet("Control: connector", "control-connector.kicad_sch", PG["cconn"], "Control board: board-to-board connector",
                 "A4", C)]
    summaries = [["Eurorack power entry", "Seed3 VIN filter", "-10 V reference"],
                 ["Daisy Seed3 (A1)", "expansion header J14", "clip-LED resistor R70", "microSD J15 (optional)"],
                 ["BASE, WIDTH, HP RES, LP RES", "ADC stages (U2)"],
                 ["EQ FREQ, EQ GAIN, DIST, SMPL RATE", "ADC stages (U1)"],
                 ["IN L / IN R -> U3 -> codec", "codec -> U4 -> OUT L / OUT R"],
                 [", ".join("JB" + h for h in sorted(PM.HEADER_PINS)), "to the control board"],
                 ["12 jacks", "clip LED D1"],
                 ["9 pots", "pot multiplexer U6"],
                 ["BASE, WIDTH, HP RES, LP RES", "LED drivers (U7)"],
                 ["EQ FREQ, EQ GAIN, DIST, SMPL RATE", "LED drivers (U8)"],
                 [", ".join("JA" + h for h in sorted(PM.HEADER_PINS)), "to the main board"]]
    for sh, sm in zip(main + ctl, summaries):
        sh.summary = sm
    page_overview(root)
    page_power(main[0])
    page_seed(main[1])
    page_cv_main(main[2], 0, drawn)
    page_cv_main(main[3], 4, drawn)
    page_audio(main[4])
    page_connectors(main[5], M)
    page_jacks(ctl[0])
    page_controls(ctl[1])
    page_cv_control(ctl[2], 0, drawn)
    page_cv_control(ctl[3], 4, drawn)
    page_connectors(ctl[4], C)
    for p in PARTS.values():                         # every unit of every part drawn exactly once
        if p.ref in NOT_DRAWN:
            continue
        for u in kicadlib.units(load_symbol(p.cat["lib"])):
            assert (p.ref, u) in PLACED, f"{p.ref} unit {u} not drawn"
    pages = [root] + main + ctl
    os.makedirs(outdir, exist_ok=True)
    keep = {pg.fname for pg in pages}
    for f in os.listdir(outdir):
        if f.endswith(".kicad_sch") and f not in keep:
            os.remove(os.path.join(outdir, f))
    sheets = root_sheet_symbols(root, [(129.54, "MAIN board (JLC SMD assembly)", main),
                                       (187.96, "CONTROL board (hand-soldered)", ctl)])
    for pg in pages:
        tree = pg.sexpr(sheets if pg is root else ())
        open(os.path.join(outdir, pg.fname), "w").write(dump(tree) + "\n")
    return os.path.join(outdir, root.fname)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..")
    print(generate(os.path.join(out, boards.BOARD)))
