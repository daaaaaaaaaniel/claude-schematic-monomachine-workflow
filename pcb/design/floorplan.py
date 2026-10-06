#!/usr/bin/env python3
"""Two-board floorplan (rev beta, d 2026-10-06), and the pin assignments that follow from it.

CONTROL board (hand-soldered; behind the panel, 70 x 107 mm): the jacks, pots and LEDs on its front; on its back the
pot multiplexer U6 and the CV-LED drivers U7/U8 (SOIC, hand-soldered), their through-hole resistors and capacitors,
and two female 1xN headers.
MAIN board (JLC PCBA, at most 100 x 100 mm): every SMD part, the Daisy Seed3 on sockets, the power and expansion
headers, and two male 1xN headers on its front that plug into the control board's.

Placement rules, in order of importance:
  1. Sensitive (low-level) paths short: CV op-amp output -> Seed3 ADC pin (the 0-3.3 V side, where a millivolt is
     six on the jack), codec pin -> audio op-amp. The Seed3's position on the main board is chosen for this.
  2. Only robust signals cross between the boards: jack-level CV and audio, slow pot signals, LED and supply lines.
  3. Blocks whose two ends are on the control board stay there (LED drivers: CV jack -> LED; multiplexer: pots).
Pin assignments are minimum-length matchings (in the plane, a minimum-length matching has no crossing pairs):
CV channels to op-amp sections, signals to Seed3 ADC pins, pots to multiplexer channels. The firmware maps ADC pins
and mux channels to functions (d: any analog input may go to any ADC pin).

Run from pcb/: python3 design/floorplan.py   -> design/pinmap.py, out/floorplan-control.png, out/floorplan-main.png
"""
import itertools
import os
import sys

import numpy as np
from scipy.optimize import linear_sum_assignment

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import boards  # noqa: E402
from geom import Board, courtyard, dist, load, pads, put  # noqa: E402
import headers as H  # noqa: E402

CV = boards.CV_NAMES
# 74xx / LM324 geometry: section -> (out, -, +) pins; 74HC4051 channel pins
SECTION = {1: ("1", "2", "3"), 2: ("7", "6", "5"), 3: ("8", "9", "10"), 4: ("14", "13", "12")}
MUX_CH_PIN = {0: "13", 1: "14", 2: "15", 3: "12", 4: "1", 5: "5", 6: "2", 7: "4"}
ADC_PINS = [str(k) for k in range(22, 33)]          # A0-A10; pin 35 (A11) left free: next to USB D- (pin 36)
CODEC = {"CODEC_IN_L": "16", "CODEC_IN_R": "17", "CODEC_OUT_L": "18", "CODEC_OUT_R": "19"}

# Board-to-board headers: three or four single rows, found by design/headers.py (d, 2026-10-06). JA = control
# (female, on its back), JB = main (male, on its front); pin k of JAn meets pin k of JBn.
SEED_START = (29.805, 90.585, 180)   # the first round's Seed3 position: USB end down, USB_MIN from the edge
CB_OUTLINE = (boards.BOARD_X[0], boards.BOARD_Y[0], boards.BOARD_X[1], boards.BOARD_Y[1])   # 70 x 107
MB_OUTLINE = (boards.BOARD_X[0], 14.0, boards.BOARD_X[1], 114.0)                            # 70 x 100
THT_R = "Resistor_THT:R_Axial_DIN0204_L3.6mm_D1.6mm_P5.08mm_Horizontal"
THT_C = "Capacitor_THT:C_Disc_D3.0mm_W1.6mm_P2.50mm"
SOIC = {8: "filter-module:SOIC-8_3.9x4.9mm_Pitch1.27mm", 14: "filter-module:SOIC-14_3.9x8.65mm_Pitch1.27mm",
        16: "filter-module:SOIC-16_3.9x9.9mm_Pitch1.27mm"}
W_SENSITIVE, W_1VOCT, W_ROBUST, W_SLOW = 3.0, 6.0, 1.0, 0.5
W_SIG = dict(robust=W_ROBUST, slow=W_SLOW, power=0.3)
# Small passives (resistors, small capacitors, ferrite beads) are not placed: the layout places them by
# docs/placement-guide.md (d, 2026-10-06). The floorplan keeps the ICs, connectors, the Seed3 and the bulky parts
# (100 uF electrolytics, the power-entry diodes), which decide whether the boards fit and how pins are assigned.
PLACE_SMALL_PASSIVES = False


def front_rotation(p):                  # the panel parts' orientations (alpha gen_pcb.py; checked against the panel)
    x, y = p.xy
    if p.kind == "POT" and y > 100:
        return 180
    if p.kind == "JACK" and y < boards.IN_Y:
        return 180
    if p.kind in ("JACK_CV", "LEDRG"):
        return 90
    return 0


def match(rows, cols, cost):
    C = np.array([[cost(r, c) for c in cols] for r in rows])
    ri, ci = linear_sum_assignment(C)
    return {rows[i]: cols[j] for i, j in zip(ri, ci)}, float(C[ri, ci].sum())


# ================================================================================================= control board
def control_board(parts, headers=None):
    """The control board: its front parts at their panel positions, the multiplexer U6 between the pot columns; with
    `headers`, also the sockets JA*, the LED drivers U7/U8 and (optionally) their passives."""
    B = Board(*CB_OUTLINE)
    front = {}
    for p in parts.values():
        if p.xy:
            fp = load(p.cat["fp"])
            put(fp, *p.xy, front_rotation(p), False)
            front[p.ref] = B.add(p.ref, fp, "front", label="")
    tip = {f"CV_{n}": front[f"J{5 + i}"]["TIP"][0][:2] for i, n in enumerate(CV)}
    tip.update({"IN_L": front["J1"]["TIP"][0][:2], "IN_R": front["J2"]["TIP"][0][:2],
                "OUT_L": front["J3"]["TIP"][0][:2], "OUT_R": front["J4"]["TIP"][0][:2]})
    wiper = {n: front[f"RV{2 + i}"]["2"][0][:2] for i, n in enumerate(CV)}
    led = {n: front[f"D{2 + i}"]["1"][0][:2] for i, n in enumerate(CV)}

    # pot multiplexer between the pot columns; pots -> channels by matching
    u6 = B.place("U6", SOIC[16], (22.9, 77.0), "back", rots=(0,), gap=0.4)
    mux_pin, _ = match(CV, list(MUX_CH_PIN.values()), lambda n, pin: dist(wiper[n], u6[pin][0][:2]))
    res = dict(board=B, front=front, tip=tip, wiper=wiper, led=led, mux_pin=mux_pin, u6=u6)
    if headers is None:
        return res
    hdr = {}
    for h in headers:
        fp = load(f"Connector_PinSocket_2.54mm:PinSocket_1x{len(h['pins']):02d}_P2.54mm_Vertical")
        put(fp, h["x"], h["y"], h["rot_back"], True)
        hdr[h["name"]] = B.add(f"JA{h['name']}", fp, "back")
        assert all(dist(hdr[h["name"]][str(k + 1)][0][:2], h["xy"][k]) < 0.01 for k in range(len(h["pins"])))
    res.update(headers=headers, hdr=hdr)

    # LED drivers by the CV jacks; channels -> sections (and quads) by matching (CV tip -> + input, LED -> output)
    u7 = B.place("U7", SOIC[14], (57.0, 66.0), "back", rots=(0, 90), gap=0.4)
    u8 = B.place("U8", SOIC[14], (57.0, 101.0), "back", rots=(0, 90), gap=0.4)
    quads = {"U7": u7, "U8": u8}
    slots = [(q, s) for q in quads for s in SECTION]
    led_unit, _ = match(CV, slots, lambda n, qs: dist(tip[f"CV_{n}"], quads[qs[0]][SECTION[qs[1]][2]][0][:2])
                        + dist(led[n], quads[qs[0]][SECTION[qs[1]][0]][0][:2]))
    # through-hole passives, nearest the pins they serve (body on the back, leads clear of every front body)
    tht = []
    for i, n in enumerate(CV):
        q, s = led_unit[n]
        o, m, p = SECTION[s]
        tht += [(f"R{80 + i}", THT_R, quads[q][p][0][:2]), (f"R{90 + i}", THT_R, quads[q][p][0][:2]),
                (f"R{71 + i}", THT_R, quads[q][m][0][:2])]
    tht += [("C80", THT_C, u6["16"][0][:2]), ("C81", THT_C, u7["4"][0][:2]), ("C82", THT_C, u7["11"][0][:2]),
            ("C83", THT_C, u8["4"][0][:2]), ("C84", THT_C, u8["11"][0][:2])]
    for ref, fpid, tgt in (tht if PLACE_SMALL_PASSIVES else ()):
        B.place(ref, fpid, tgt, "back", rots=(0, 90, 180, 270), through_hole=True, gap=0.2)
    res.update(led_unit=led_unit)
    return res


# ================================================================================================= main board
USB_MIN = 25.0       # d (2026-10-06): the Seed3's USB socket at least 20-25 mm inside the control board's edge
USB_OVERHANG = 2.0   # USB end of the module beyond the pin-1 row (approx.)
PLUG_W = 12.0        # width of the plug path kept free of tall parts, socket to board edge


def usb_end(seed_pos):
    """(x, y) of the Seed3's USB end and the direction (+1 down, -1 up) its plug points."""
    x1, y1, rot = seed_pos
    xc = x1 - 7.62 if rot == 0 else x1 + 7.62
    return (xc, y1 - USB_OVERHANG, -1) if rot == 0 else (xc, y1 + USB_OVERHANG, 1)


def usb_clearance(seed_pos):
    x, y, d = usb_end(seed_pos)
    return y - CB_OUTLINE[1] if d < 0 else CB_OUTLINE[3] - y


def seed_candidates(headers):
    """Vertical Seed3 positions on the main board's back, USB end up or down and at least USB_MIN inside the control
    board's edge, the module inside the main board, every socket pin at least headers.SEED_MIN from every header pin.
    Returns [(x of pin 1, y of pin 1, rotation)]."""
    hdr = [p for h in headers for p in h["xy"]]
    out = []
    for rot in (0, 180):
        for y1 in np.arange(MB_OUTLINE[1] + 3.1, MB_OUTLINE[3] - 3.1 + 1e-6, 1.27):
            far = y1 + 19 * 2.54 if rot == 0 else y1 - 19 * 2.54
            if not (MB_OUTLINE[1] + 3.1 - 1e-6 <= min(y1, far) and max(y1, far) <= MB_OUTLINE[3] - 3.1 + 1e-6):
                continue
            if usb_clearance((0.0, y1, rot)) < USB_MIN:
                continue
            for x1 in np.arange(2.5, 68.0, 0.635):
                xo = x1 - 15.24 if rot == 0 else x1 + 15.24
                if not (MB_OUTLINE[0] + 2.0 < min(x1, xo) and max(x1, xo) < MB_OUTLINE[2] - 2.0):
                    continue
                rows = [(x1, y1 + (k if rot == 0 else -k) * 2.54) for k in range(20)] + \
                       [(xo, y1 + (k if rot == 0 else -k) * 2.54) for k in range(20)]
                if all(dist(a, b) >= H.SEED_MIN for a in rows for b in hdr):
                    out.append((round(float(x1), 3), round(float(y1), 3), rot))
    return out


def seed_pads(seed_pos):
    seed = load("filter-module:Daisy_Seed_ES_Sockets")
    put(seed, seed_pos[0], seed_pos[1], seed_pos[2], True)
    return {n: v[0][:2] for n, v in pads(seed).items()}


def main_board(ctl, seed_pos=None, final=False):
    B = Board(*MB_OUTLINE)
    jb = {}
    for h in ctl["headers"]:
        fp = load(f"Connector_PinHeader_2.54mm:PinHeader_1x{len(h['pins']):02d}_P2.54mm_Vertical")
        put(fp, h["x"], h["y"], h["rot"], False)
        jb[h["name"]] = B.add(f"JB{h['name']}", fp, "front")
    hpin = {s: jb[h["name"]][str(k + 1)][0][:2] for h in ctl["headers"] for k, s in enumerate(h["pins"]) if s != "GND"}
    seed = load("filter-module:Daisy_Seed_ES_Sockets")
    put(seed, seed_pos[0], seed_pos[1], seed_pos[2], True)
    sp = {n: v[0][:2] for n, v in B.add("A1", seed, "back").items()}
    xs = [v[0] for v in sp.values()]
    ys = [v[1] for v in sp.values()]
    B.mark_flat_only((min(xs) - 1.8, min(ys) - 3.1, max(xs) + 1.8, max(ys) + 3.1))   # under the module: flat only
    ux, uy, ud = usb_end(seed_pos)                                                       # the plug's path: flat only
    B.mark_flat_only((ux - PLUG_W / 2, min(uy, B.y1 if ud > 0 else B.y0), ux + PLUG_W / 2, max(uy, B.y1 if ud > 0 else B.y0)))
    mid = lambda *ps: (sum(sp[p][0] for p in ps) / len(ps), sum(sp[p][1] for p in ps) / len(ps))
    # audio op-amps at the codec pins; CV op-amps at the ADC pins; the reference between them
    u3 = B.place("U3", SOIC[8], mid("16", "17"), "back", rots=(0, 90, 180, 270))
    u4 = B.place("U4", SOIC[8], mid("18", "19"), "back", rots=(0, 90, 180, 270))
    u1 = B.place("U1", SOIC[14], mid("27", "28", "29", "30", "31"), "back", rots=(0, 90, 180, 270))
    u2 = B.place("U2", SOIC[14], mid("22", "23", "24", "25", "26"), "back", rots=(0, 90, 180, 270))
    u5 = B.place("U5", "filter-module:SOT-23", mid("26", "27"), "back", rots=(0, 90))
    quads = {"U1": u1, "U2": u2}
    P = lambda pp, pin: pp[pin][0][:2]
    # CV channels -> sections: header pin (jack side) -> - input
    slots = [(q, s) for q in quads for s in SECTION]
    adc_unit, _ = match(CV, slots, lambda n, qs: dist(hpin[f"CV_{n}"], P(quads[qs[0]], SECTION[qs[1]][1])))
    # signals -> ADC pins (weighted: the scaled side is sensitive; the 1V/OCT inputs most of all)
    src = {f"ADC_{n}": P(quads[adc_unit[n][0]], SECTION[adc_unit[n][1]][0]) for n in CV}
    src.update(POT_MUX=hpin["POT_MUX"], POT_VOL=hpin["POT_VOL"])
    w = {s: (W_1VOCT if s[4:] in boards.ONE_V_OCT else W_SENSITIVE) if s.startswith("ADC_") else W_SLOW for s in src}
    adc_pin, adc_cost = match(list(src), ADC_PINS, lambda s, p: w[s] * dist(src[s], sp[p]))
    codec_cost = W_SENSITIVE * (dist(P(u3, "1"), sp["16"]) + dist(P(u3, "7"), sp["17"]) +
                                dist(P(u4, "2"), sp["18"]) + dist(P(u4, "6"), sp["19"]))
    robust = W_ROBUST * (sum(dist(hpin[f"CV_{n}"], P(quads[q], SECTION[s][1])) for n, (q, s) in adc_unit.items()) +
                         dist(hpin["IN_L"], P(u3, "2")) + dist(hpin["IN_R"], P(u3, "6")) +
                         dist(P(u4, "1"), hpin["OUT_L"]) + dist(P(u4, "7"), hpin["OUT_R"]))
    slow = W_SLOW * (dist(hpin["MUX_A"], sp["8"]) + dist(hpin["MUX_B"], sp["9"]) + dist(hpin["MUX_C"], sp["10"]) +
                     dist(hpin["LED_A"], sp["12"]))
    res = dict(board=B, seed=seed_pos, sp=sp, adc_unit=adc_unit, adc_pin=adc_pin, src=src, hpin=hpin,
               cost=adc_cost + codec_cost + robust + slow,
               parts=dict(adc=adc_cost, codec=codec_cost, robust=robust, slow=slow))
    if final:
        place_main_rest(B, sp, quads, u3, u4, u5, adc_unit, hpin)
    return res


def place_main_rest(B, sp, quads, u3, u4, u5, adc_unit, hpin):
    """The other main-board parts, nearest what they connect to (a feasibility check, not the final layout)."""
    P = lambda pp, pin: pp[pin][0][:2]
    R, C = "filter-module:R_0603", "filter-module:C_0603"
    todo = [("C20", C, P(quads["U1"], "4")), ("C21", C, P(quads["U2"], "4")),
            ("C70", C, P(u3, "8")), ("C71", C, P(u3, "4")), ("C72", C, P(u4, "8")), ("C73", C, P(u4, "4")),
            ("C7", C, P(u5, "2")), ("R3", R, P(u5, "2"))]
    for i, n in enumerate(CV):
        q, s = adc_unit[n]
        o, m, _ = SECTION[s]
        todo += [(f"R{11 + 4 * i}", R, P(quads[q], m)), (f"C{10 + i}", C, P(quads[q], m)),
                 (f"R{12 + 4 * i}", R, P(quads[q], m)), (f"R{10 + 4 * i}", R, P(quads[q], m))]
        if n in boards.ONE_V_OCT:
            todo.append((f"R{13 + 4 * i}", R, P(quads[q], m)))
    for u, ins, outs in ((u3, ("R50", "R54"), ("R52", "R56")), (u4, ("R60", "R64"), ("R62", "R66"))):
        todo += [(ins[0], R, P(u, "2")), (ins[1], R, P(u, "6")), (outs[0], R, P(u, "1")), (outs[1], R, P(u, "7"))]
    todo += [("R51", R, P(u3, "2")), ("C50", C, P(u3, "2")), ("R55", R, P(u3, "6")), ("C52", C, P(u3, "6")),
             ("R61", R, P(u4, "2")), ("C60", C, P(u4, "2")), ("R65", R, P(u4, "6")), ("C62", C, P(u4, "6")),
             ("R70", R, sp["12"])]
    for ref, fpid, tgt in (todo if PLACE_SMALL_PASSIVES else [t for t in todo if t[0][0] == "U"]):
        B.place(ref, fpid, tgt, "back", rots=(0, 90), gap=0.2)
    # power entry: the box header at a free spot near the board's edge away from the codec, then its parts
    far = (8.0, 100.0) if sp["16"][1] < 64 else (8.0, 28.0)
    j13 = B.place("J13", "filter-module:Pins_2x05_2.54mm_TH_EurorackPower_Shrouded", far, "back", rots=(0, 90),
                  through_hole=True, tall=True, gap=0.5)
    c = P(j13, "5")
    for ref, fpid in (("FB1", "filter-module:R_0805_2012Metric"), ("FB2", "filter-module:R_0805_2012Metric"), ("D10", "filter-module:D_SOD-123"), ("D11", "filter-module:D_SOD-123"),
                      ("C1", "filter-module:C_0805"), ("C3", "filter-module:C_0805"),
                      ("C2", "Capacitor_SMD:CP_Elec_6.3x7.7"), ("C4", "Capacitor_SMD:CP_Elec_6.3x7.7"),
                      ("R1", "filter-module:R_1206_3216Metric"), ("R2", "filter-module:R_1206_3216Metric"),
                      ("C5", "Capacitor_SMD:CP_Elec_6.3x7.7"), ("C6", "Capacitor_SMD:CP_Elec_6.3x7.7")):
        B.place(ref, fpid, c if ref[0] != "R" and ref not in ("C5", "C6") else sp["39"], "back", rots=(0, 90),
                tall=fpid.startswith("Capacitor_SMD:CP"), gap=0.3) \
            if PLACE_SMALL_PASSIVES or ref[0] == "D" or fpid.startswith("Capacitor_SMD:CP") else None
    B.place("J14", "filter-module:Pins_2x04_2.54mm_TH", mid2(sp, "36", "37"), "back", rots=(0, 90),
            through_hole=True, tall=True, gap=0.5)
    # optional microSD socket (DNP), as the Dev Kit: near SDMMC1 on pins 2-7, its pull-ups between socket and Seed
    sd_pins = ("2", "3", "4", "5", "6", "7")
    sd = B.place("J15", "filter-module:TF-01A", mid2(sp, *sd_pins), "back", rots=(0, 90, 180, 270), gap=0.5)
    j15 = B.items[-1]
    if PLACE_SMALL_PASSIVES:
        for ref, pin in (("R100", "3"), ("R101", "2"), ("R102", "6"), ("R103", "5"), ("R104", "4")):
            B.place(ref, R, sp[pin], "back", rots=(0, 90), gap=0.2)
        B.place("C100", C, P(sd, "4"), "back", rots=(0, 90), gap=0.2)
    sd_len = sum(dist(sp[p], P(sd, q)) for p, q in zip(sd_pins, ("2", "1", "8", "7", "3", "5")))
    print(f"microSD socket J15 at {j15['x']}, {j15['y']} rot {j15['rot']}; "
          f"SDMMC pin-to-pad distances total {sd_len:.0f} mm (6 lines)")


def mid2(sp, *ps):
    return sum(sp[p][0] for p in ps) / len(ps), sum(sp[p][1] for p in ps) / len(ps)


# ================================================================================================= output
def write_pinmap(ctl, mb):
    chan = {v: k for k, v in MUX_CH_PIN.items()}
    L = ['"""Pin assignments and placement, written by design/floorplan.py: edit floorplan.py, not this file.', "",
         "Used by machine_filter.py (SKiDL) and design/boards.py. Units: 1 = A (pins 1-3), 2 = B (5-7), 3 = C (8-10),",
         "4 = D (12-14). Positions: panel frame seen from the front, mm: (x, y, rotation) of the footprint origin",
         "as pcbnew's SetPosition takes it (KiCad = panel + (100, 50)); back-side parts are then flipped left-right.\"\"\"",
         "",
         "HEADER_PINS = " + repr({h["name"]: h["pins"] for h in ctl["headers"]}),
         "HEADER_POS = " + repr({h["name"]: (h["x"], h["y"], h["rot"], h["rot_back"]) for h in ctl["headers"]})
         + "   # pin 1 x, y; rotation of JBn (main, front) and of JAn (control, back)",
         "SEED = " + repr(mb["seed"]) + "   # main board, back; rotation 0 = USB end up, 180 = down",
         "ADC_UNIT = {" + ", ".join(f'"{n}": ("{q}", {s})' for n, (q, s) in mb["adc_unit"].items()) + "}",
         "LED_UNIT = {" + ", ".join(f'"{n}": ("{q}", {s})' for n, (q, s) in ctl["led_unit"].items()) + "}",
         "SEED_ADC = {" + ", ".join(f'"{s}": "{p}"' for s, p in sorted(mb["adc_pin"].items(), key=lambda kv: int(kv[1]))) + "}",
         "MUX_PIN = {" + ", ".join(f'"{n}": "{p}"' for n, p in ctl["mux_pin"].items()) + "}",
         "MUX_SELECT = [" + ", ".join(f'"{n}"' for n, _ in sorted(ctl["mux_pin"].items(), key=lambda kv: chan[kv[1]]))
         + "]   # firmware: select 0..7 -> pot",
         'MIDI = {"MIDI_TX": "14", "MIDI_RX": "15"}   # D13 / D14 = USART1 TX / RX (PB6 / PB7), libDaisy\'s default',
         "CONTROL_PLACEMENT = " + repr({i["ref"]: (i["x"], i["y"], i["rot"]) for i in ctl["board"].items if "x" in i}),
         "MAIN_PLACEMENT = " + repr({i["ref"]: (i["x"], i["y"], i["rot"]) for i in mb["board"].items if "x" in i}), ""]
    open(os.path.join(HERE, "pinmap.py"), "w").write("\n".join(L))



SIG_GROUP = {"IN_L": "audio", "IN_R": "audio", "OUT_L": "audio", "OUT_R": "audio", "POT_VOL": "pots", "POT_MUX": "pots",
             "MUX_A": "digital", "MUX_B": "digital", "MUX_C": "digital", "LED_A": "digital",
             "+12V": "power", "-12V": "power", "+3V3_A": "power"}   # anything else: cv
GROUP_COLOR = {"audio": "#2b7bd6", "cv": "#e67e22", "pots": "#8e44ad", "digital": "#d64545", "power": "#7f7f7f"}


def crossing_report(ctl, mb, S):
    """Every crossing signal: its group, header pin, and straight-line length on each board (mm, unweighted).
    Control end: jack tip, pot wiper, U6 pin, clip LED, or the LED driver's supply pin. Main end: the op-amp pin
    (CV, audio), the Seed3 pin (pots, digital, +3V3_A) or the power header (+/-12 V)."""
    item = lambda B, ref: next(i for i in B.items if i["ref"] == ref)["pads"]
    M, C = mb["board"], ctl["board"]
    P = lambda pp, pin: tuple(pp[pin][0][:2])
    q = {r: item(M, r) for r in ("U1", "U2", "U3", "U4", "J13")}
    u7 = item(C, "U7")
    sp = mb["sp"]
    pin_of = {v: k for k, v in mb["adc_pin"].items()}
    main_end = {"IN_L": P(q["U3"], "2"), "IN_R": P(q["U3"], "6"), "OUT_L": P(q["U4"], "1"), "OUT_R": P(q["U4"], "7"),
                "POT_VOL": sp[mb["adc_pin"]["POT_VOL"]], "POT_MUX": sp[mb["adc_pin"]["POT_MUX"]],
                "MUX_A": sp["8"], "MUX_B": sp["9"], "MUX_C": sp["10"], "LED_A": sp["12"], "+3V3_A": sp["21"],
                "+12V": P(q["J13"], "9"), "-12V": P(q["J13"], "1")}
    for n, (u, sec) in mb["adc_unit"].items():
        main_end[f"CV_{n}"] = P(q[u], SECTION[sec][1])
    ctl_end = {s: tuple(S[s][0]) for s in S}
    ctl_end.update({"+12V": P(u7, "4"), "-12V": P(u7, "11")})
    rows = []
    for h in ctl["headers"]:
        for k, s in enumerate(h["pins"]):
            if s == "GND":
                continue
            xy = tuple(h["xy"][k])
            rows.append(dict(signal=s, group=SIG_GROUP.get(s, "cv"), header=h["name"], pin=k + 1, xy=xy,
                             ctl_end=ctl_end[s], main_end=tuple(main_end[s]),
                             ctl_mm=round(dist(ctl_end[s], xy), 1), main_mm=round(dist(xy, main_end[s]), 1)))
    return rows


def internal_report(mb):
    """Main-board traces that never cross a header but move with the floorplan: op-amp output -> Seed3 ADC pin for
    each CV, and the codec lines between U3/U4 and Seed3 pins 16-19 (straight-line mm)."""
    item = lambda ref: next(i for i in mb["board"].items if i["ref"] == ref)["pads"]
    sp, u3, u4 = mb["sp"], item("U3"), item("U4")
    P = lambda pp, pin: tuple(pp[pin][0][:2])
    rows = [dict(kind="adc_1voct" if s[4:] in boards.ONE_V_OCT else "adc", signal=s, seed_pin=p,
                 mm=round(dist(mb["src"][s], sp[p]), 1)) for s, p in mb["adc_pin"].items() if s.startswith("ADC_")]
    for name, a, pin in (("codec IN_L", P(u3, "1"), "16"), ("codec IN_R", P(u3, "7"), "17"),
                         ("codec OUT_L", P(u4, "2"), "18"), ("codec OUT_R", P(u4, "6"), "19")):
        rows.append(dict(kind="codec", signal=name, seed_pin=pin, mm=round(dist(a, sp[pin]), 1)))
    return rows


def header_seed_clearance(headers, sp):
    return min(dist(p, q) for h in headers for p in h["xy"] for q in sp.values())


def render_crossing(ctl, mb, rows, title, path):
    """Both boards side by side, every crossing signal drawn from its end to its header pin, coloured by group;
    header pins coloured by what they carry, GND pins grey."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    fig, axes = plt.subplots(1, 2, figsize=(11, 8.6))
    for ax, B, side in ((axes[0], ctl["board"], "ctl"), (axes[1], mb["board"], "main")):
        _draw(ax, B, (), seed_pads=mb["sp"] if side == "main" else None)
        for r in rows:
            end = r["ctl_end"] if side == "ctl" else r["main_end"]
            ax.plot([end[0], r["xy"][0]], [end[1], r["xy"][1]], color=GROUP_COLOR[r["group"]], lw=1.2, alpha=0.85)
        for h in ctl["headers"]:
            for k, s in enumerate(h["pins"]):
                x, y = h["xy"][k]
                c = "#bdbdbd" if s == "GND" else GROUP_COLOR[SIG_GROUP.get(s, "cv")]
                ax.add_patch(plt.Rectangle((x - 0.9, y - 0.9), 1.8, 1.8, color=c, lw=0, zorder=5))
            x, y = h["xy"][0]
            pre = "JA" if side == "ctl" else "JB"
            ax.text(x + 2.0, y, f"{pre}{h['name']} ({len(h['pins'])})", fontsize=7, weight="bold", zorder=6,
                    va="center", color="#111", bbox=dict(facecolor="white", alpha=0.8, lw=0, pad=0.6))
        ax.set_title("CONTROL board, back (seen from the panel)" if side == "ctl" else
                     "MAIN board, back (seen from the panel)", fontsize=9)
        ax.set_xlim(-0.5, 71.5)
        ax.set_ylim(119, 9)
        ax.set_aspect("equal")
        ax.axis("off")
    fig.legend([Line2D([], [], color=c, lw=3) for c in GROUP_COLOR.values()] + [Line2D([], [], color="#bdbdbd", lw=3)],
               list(GROUP_COLOR) + ["GND"], loc="lower center", ncol=6, fontsize=9, frameon=False)
    fig.suptitle(title, fontsize=11)
    plt.tight_layout(rect=(0, 0.04, 1, 0.97))
    plt.savefig(path, dpi=150)
    plt.close(fig)

def _draw(ax, B, lines=(), seed_pads=None, adc=(), codec=()):
    from matplotlib.patches import Rectangle
    ax.add_patch(Rectangle((B.x0, B.y0), B.x1 - B.x0, B.y1 - B.y0, fill=False, lw=1))
    for it in B.items:
        x0, y0, x1, y1 = it["box"]
        ref = it["ref"]
        if it["side"] == "front" and not ref.startswith("JB"):
            col, a = ("#d9d9d9" if ref.startswith("RV") else "#f1d9a9" if ref.startswith("J") else "#f7c6c6"), 0.55
        elif ref == "A1":
            col, a = "#3a6ea5", 0.12
        elif ref[0] in "RC" and ref[1:].isdigit() or ref.startswith(("FB", "D1")):
            col, a = "#8a8a8a", 0.9
        else:
            col, a = "#333333", 0.9
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, color=col, alpha=a, lw=0))
        if it["label"] and (ref.startswith(("U", "J", "A")) or ref in ("C80",)):
            ax.text((x0 + x1) / 2, (y0 + y1) / 2, it["label"], ha="center", va="center", fontsize=5,
                    color="white" if col == "#333333" else "#222", weight="bold")
        for num, plist in it["pads"].items():
            for x, y, w, h, th in plist:
                c = "#555"
                if seed_pads is not None and ref == "A1":
                    c = "#2e9e4f" if num in adc else "#2b7bd6" if num in codec else "#d64545" if num in ("36", "37") \
                        else "#bbbbbb"
                ax.add_patch(Rectangle((x - w / 2, y - h / 2), w, h, color=c, lw=0))
    for (a, b, c, lw) in lines:
        ax.plot([a[0], b[0]], [a[1], b[1]], color=c, lw=lw)


def render(B, title, path, lines=(), seed_pads=None, adc=(), codec=()):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Rectangle
    fig, ax = plt.subplots(figsize=(6.2, 9.4))
    _draw(ax, B, lines, seed_pads, adc, codec)
    ax.set_title(title, fontsize=8)
    ax.set_xlim(-0.5, 71.5)
    ax.set_ylim(119, 9)
    ax.set_aspect("equal")
    ax.axis("off")
    plt.tight_layout()
    plt.savefig(path, dpi=170)
    plt.close(fig)


def control_cost(ctl, S):
    """Control-board side: each crossing signal from its control-board end to its header pin (weighted)."""
    pin = {s: ctl["hdr"][h["name"]][str(k + 1)][0][:2] for h in ctl["headers"] for k, s in enumerate(h["pins"])}
    return sum(w * dist(c, pin[s]) for s, (c, m, w) in S.items())


def search_seed(ctl, S, log):
    """Seed3 positions for fixed headers, in two stages: a cheap score (header pins to the main-board ends) for every
    legal position, then the full main-board placement for the best few."""
    cands = seed_candidates(ctl["headers"])
    pin = {s: p for h in ctl["headers"] for s, p in zip(h["pins"], h["xy"])}
    cheap = []
    for c in cands:
        sp = seed_pads(c)
        S2 = H.crossing_signals(ctl, sp, CV, j13_spot(sp), W_SIG)
        cheap.append((sum(w * dist(pin[s], m) for s, (_, m, w) in S2.items()), c))
    cheap.sort()
    scored = []
    for _, c in cheap[:15]:
        try:
            scored.append((main_board(ctl, c)["cost"], c))
        except SystemExit:
            pass
    scored.sort()
    log(f"   {len(cands)} Seed3 positions legal, {min(15, len(cands))} placed in full; best {scored[0][1]}, "
        f"cost {scored[0][0]:.0f}")
    return scored


def j13_spot(sp):
    return (8.0, 100.0) if sp["16"][1] < 64 else (8.0, 28.0)


def main():
    log = print
    parts = {p.ref: p for p in boards.board()}
    outline = (max(CB_OUTLINE[0], MB_OUTLINE[0]), max(CB_OUTLINE[1], MB_OUTLINE[1]),
               min(CB_OUTLINE[2], MB_OUTLINE[2]), min(CB_OUTLINE[3], MB_OUTLINE[3]))
    seed, seen = SEED_START, set()
    for rnd in range(1, 5):
        base = control_board(parts)                      # front parts and U6: what the headers must avoid
        sp = seed_pads(seed)
        S = H.crossing_signals(base, sp, CV, j13_spot(sp), W_SIG)
        log(f"round {rnd}: headers for Seed3 at {seed}")
        hcost, headers = H.search(S, H.SiteMap(base["board"], list(sp.values()), outline), CV, log)
        ctl = control_board(parts, headers)
        scored = search_seed(ctl, S, log)
        key = (scored[0][1], tuple((h["x"], h["y"], h["rot"], tuple(h["pins"])) for h in headers))
        if scored[0][1] == seed or key in seen:
            break
        seen.add(key)
        seed = scored[0][1]
    best = scored[0][1]
    sp = seed_pads(best)
    S = H.crossing_signals(ctl, sp, CV, j13_spot(sp), W_SIG)
    mb = main_board(ctl, best, final=True)
    ccost = control_cost(ctl, S)
    log(f"headers: " + "; ".join(f"{h['name']}: {len(h['pins'])} pins at ({h['x']}, {h['y']}) rot {h['rot']}"
                                 for h in headers))
    write_pinmap(ctl, mb)
    out = os.path.join(HERE, "..", "out")
    os.makedirs(out, exist_ok=True)
    # control board picture: jack tips -> header, pots -> mux, LED drivers
    hp = {s: ctl["hdr"][h["name"]][str(k + 1)][0][:2] for h in ctl["headers"] for k, s in enumerate(h["pins"])
          if s != "GND"}
    B = ctl["board"]
    u6 = next(i for i in B.items if i["ref"] == "U6")["pads"]
    q = {i["ref"]: i["pads"] for i in B.items if i["ref"] in ("U7", "U8")}
    lines = [(ctl["tip"][s], hp[s], "#e67e22", 0.8) for s in ctl["tip"]]
    lines += [(ctl["wiper"][n], u6[p][0][:2], "#8e44ad", 0.8) for n, p in ctl["mux_pin"].items()]
    lines += [(ctl["tip"][f"CV_{n}"], q[u][SECTION[s][2]][0][:2], "#e67e22", 0.5) for n, (u, s) in ctl["led_unit"].items()]
    render(B, "CONTROL board, back (seen from the front panel): U6 mux, U7/U8 LED drivers, THT R/C, headers JA*",
           os.path.join(out, "floorplan-control.png"), lines)
    M = mb["board"]
    lines = [(mb["src"][s], mb["sp"][p], "#2e9e4f", 1.0) for s, p in mb["adc_pin"].items()]
    quads = {i["ref"]: i["pads"] for i in M.items if i["ref"] in ("U1", "U2", "U3", "U4")}
    lines += [(mb["hpin"][f"CV_{n}"], quads[u][SECTION[s][1]][0][:2], "#e67e22", 0.7) for n, (u, s) in mb["adc_unit"].items()]
    lines += [(quads["U3"]["1"][0][:2], mb["sp"]["16"], "#2b7bd6", 1.0), (quads["U3"]["7"][0][:2], mb["sp"]["17"], "#2b7bd6", 1.0),
              (quads["U4"]["2"][0][:2], mb["sp"]["18"], "#2b7bd6", 1.0), (quads["U4"]["6"][0][:2], mb["sp"]["19"], "#2b7bd6", 1.0)]
    render(M, f"MAIN board, back (seen from the front panel), 70 x 100 mm: Seed3 USB {'up' if best[2] == 0 else 'down'}",
           os.path.join(out, "floorplan-main.png"), lines, seed_pads=mb["sp"], adc=set(mb["adc_pin"].values()),
           codec=set(CODEC.values()))
    rows = crossing_report(ctl, mb, S)
    import json
    rep = dict(tag=os.environ.get("FP_TAG", ""), seed=list(best), headers=[dict(name=h["name"], x=h["x"], y=h["y"],
               rot=h["rot"], pins=h["pins"]) for h in ctl["headers"]], signals=rows,
               seed_clearance=round(header_seed_clearance(ctl["headers"], mb["sp"]), 2),
               weighted=dict(main=round(mb["cost"]), control=round(ccost)),
               internal=internal_report(mb), usb_clearance=round(usb_clearance(best), 1))
    json.dump(rep, open(os.path.join(out, "floorplan-report.json"), "w"), indent=1)
    render_crossing(ctl, mb, rows, os.environ.get("FP_TAG", "") or "Board-to-board signals",
                    os.path.join(out, "floorplan-crossing.png"))
    print(f"Seed3 {best}: main-board cost {mb['cost']:.0f} ({ {k: round(v) for k, v in mb['parts'].items()} }), "
          f"control-board cost {ccost:.0f}, total {mb['cost'] + ccost:.0f}")
    print(open(os.path.join(HERE, "pinmap.py")).read()[:2500])


if __name__ == "__main__":
    main()
