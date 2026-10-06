"""MACHINE FILTER (Daisy Seed3 build), rev beta: the circuit as a SKiDL description, the source of truth.

Two boards (d, 2026-10-06):
  MAIN    (JLC SMD assembly, <= 100 x 100 mm): Seed3, power, CV ADC stages U1/U2, audio U3/U4, -10 V reference.
  CONTROL (hand-soldered): jacks, pots, LEDs on the front; the pot multiplexer U6 and the CV-LED drivers U7/U8
          (SOIC) with through-hole resistors and capacitors on the back.
  The boards meet through two 1-row 2.54 mm headers, JAn (female, control) on JBn (male, main), pin k to pin k.
  Only robust signals cross: jack-level signals, slow pot wipers and mux selects, the clip-LED drive and the supplies.

Changes from rev alpha:
  1. The split into two boards, with the headers and through-hole passives on the control board.
  2. Pin assignment follows the floorplan (design/floorplan.py -> design/pinmap.py): which Seed3 ADC pin each CV and
     pot signal uses, which op-amp section each CV channel uses in U1/U2 (ADC) and U7/U8 (LED), and which
     74HC4051 channel each pot uses. The firmware maps them (docs/firmware-changes.md).
  3. Audio output gain x5.1 instead of x10 (R61/R65 51k, C60/C62 47p; d, 2026-10-06): 0 dBFS = +/-7.1 V, and the
     TL072 can no longer clip. The 1V/OCT offset resistors R12/R16 are 25 ppm/K parts.
  4. An optional microSD socket J15 (DNP) on SDMMC1, Seed3 pins 2-7, as the Dev Kit. MIDI stays on pins 14/15
     (USART1, libDaisy's default), as rev alpha.

Run (SKiDL venv, see tools/setup-toolchain.sh): python machine_filter.py
  writes out/logical.net (both boards as one circuit, no headers), out/main.net and out/control.net (each board
  with its headers). BOARD=all|main|control builds just one (each build runs in its own process).
  tools/build.sh runs this, draws the schematics and checks that everything agrees.
"""
import os
import subprocess
import sys

from skidl import (KICAD10, POWER, Net, Part, generate_netlist, generate_schematic, lib_search_paths,
                   set_default_tool, subcircuit)

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "design"))
import pinmap as PM          # noqa: E402  (design/floorplan.py writes it)

BOARD = os.environ.get("BOARD", "")          # "all" (logical), "main", "control"; "" = run all three
set_default_tool(KICAD10)
lib_search_paths[KICAD10].extend([os.path.join(HERE, "lib"), "/usr/share/kicad/symbols"])

FM = "filter-module"

# ------------------------------------------------------------------------------------------------- catalogue
# value, footprint, LCSC, MPN (all as rev alpha's BOM)
CAT = {
    "R100k": ("100k", "R_0603", "C25803", "0603WAF1003T5E"),
    "R100k_01": ("100k 0.1%", "R_0603", "C122538", "RT0603BRD07100KL"),
    "R20k": ("20k", "R_0603", "C4184", "0603WAF2002T5E"),
    "R20k_01": ("20k 0.1%", "R_0603", "C723637", "RT0603BRD0720KL"),
    "R120k": ("120k", "R_0603", "C25808", "0603WAF1203T5E"),
    "R120k_25": ("120k 25ppm", "R_0603", "C862537", "RT0603DRD07120KL"),   # 1V/OCT offset: 0.5 %, 25 ppm/K
    "R51k": ("51k", "R_0603", "C23196", "0603WAF5102T5E"),
    "R47k": ("47k", "R_0603", "C25819", "0603WAF4702T5E"),
    "R10k": ("10k", "R_0603", "C25804", "0603WAF1002T5E"),
    "R1k": ("1k", "R_0603", "C21190", "0603WAF1001T5E"),
    "R1k5": ("1.5k", "R_0603", "C22843", "0603WAF1501T5E"),
    "R1M": ("1M", "R_0603", "C22935", "0603WAF1004T5E"),
    "R100": ("100", "R_0603", "C22775", "0603WAF1000T5E"),
    "R3R3": ("3.3 0.75W", "R_1206_3216Metric", "C2577888", "SG73P2BTTD3R30F"),
    "C100n": ("100n", "C_0603", "C14663", "CC0603KRX7R9BB104"),
    "C1n": ("1n", "C_0603", "C1588", "CL10B102KB8NNNC"),
    "C330p": ("330p", "C_0603", "C1664", "CL10C331JB8NNNC"),
    "C33p": ("33p", "C_0603", "C1663", "CL10C330JB8NNNC"),
    "C47p": ("47p", "C_0603", "C1671", "CL10C470JB8NNNC"),
    "C10u": ("10u 25V", "C_0805", "C15850", "CL21A106KAYNNNE"),
    # control board: through-hole, hand-soldered
    "R10k_T": ("10k", "Resistor_THT:R_Axial_DIN0204_L3.6mm_D1.6mm_P5.08mm_Horizontal", None,
               "10k 1/8 W 1% metal film, axial DIN0204"),
    "R1M_T": ("1M", "Resistor_THT:R_Axial_DIN0204_L3.6mm_D1.6mm_P5.08mm_Horizontal", None,
              "1M 1/8 W 1% metal film, axial DIN0204"),
    "R1k5_T": ("1.5k", "Resistor_THT:R_Axial_DIN0204_L3.6mm_D1.6mm_P5.08mm_Horizontal", None,
               "1.5k 1/8 W 1% metal film, axial DIN0204"),
    "C100n_T": ("100n", "Capacitor_THT:C_Disc_D3.0mm_W1.6mm_P2.50mm", None, "100 nF 50 V X7R ceramic, 2.5 mm pitch"),
}


class _Skip:
    """Stands in for a part that belongs to the other board: connections to it are dropped."""
    def __getitem__(self, k):
        return self

    def __setitem__(self, k, v):
        pass

    def __iadd__(self, other):
        return self


def here(board):
    return BOARD in ("all", board)


def _fields(p, lcsc, mpn, board):
    if lcsc:
        p.fields["LCSC"] = lcsc
    if mpn:
        p.fields["MPN"] = mpn
    p.fields["Assembly"] = "JLC (SMD)" if lcsc and board == "main" else "hand"
    return p


def RC(kind, ref, a, b, board="main"):
    """A resistor or capacitor from the catalogue, pin 1 to net a, pin 2 to net b."""
    if not here(board):
        return _Skip()
    value, fp, lcsc, mpn = CAT[kind]
    fp = fp if ":" in fp else f"{FM}:{fp}"
    p = Part("Device", "R" if kind.startswith("R") else "C", ref=ref, value=value, footprint=fp, tag=ref)
    p[1] += a
    p[2] += b
    return _fields(p, lcsc, mpn, board)


def stock(lib, name, ref, value, fp, lcsc=None, mpn=None, board="main"):
    if not here(board):
        return _Skip()
    return _fields(Part(lib, name, ref=ref, value=value, footprint=fp, tag=ref), lcsc, mpn, board)


# ------------------------------------------------------------------------------------------------- nets
def pnet(name):
    n = Net(name)
    n.drive = POWER
    return n


GND, P12, N12 = pnet("GND"), pnet("+12V"), pnet("-12V")
VIN, A33, D33 = pnet("VIN"), pnet("+3V3_A"), pnet("+3V3_D")
VREF = Net("-10V_REF")

CV_NAMES = ["BASE", "WIDTH", "HPRES", "LPRES", "EQF", "EQG", "DIST", "SRR"]
ONE_V_OCT = {"BASE", "WIDTH"}
CV = {n: Net(f"CV_{n}") for n in CV_NAMES}
ADC = {n: Net(f"ADC_{n}") for n in CV_NAMES}
POT = {n: Net(f"POT_{n}") for n in CV_NAMES}

# Change 2 (design/pinmap.py, from the floorplan). LM324 / LMV324 sections, unit 1-4 = A-D, as (out, -in, +in).
SECTION_PINS = [("1", "2", "3"), ("7", "6", "5"), ("8", "9", "10"), ("14", "13", "12")]
ADC_UNIT, LED_UNIT = PM.ADC_UNIT, PM.LED_UNIT
MUX_PIN = PM.MUX_PIN                     # pot -> 74HC4051 pin
MUX_CHANNEL_OF_PIN = {"13": 0, "14": 1, "15": 2, "12": 3, "1": 4, "5": 5, "2": 6, "4": 7}   # 74HC4051 datasheet

# Seed3 pins (Electrosmith Seed3_pinout.csv). ADC pins from the floorplan; MIDI on D2/D1 (USART3).
SEED_PINS = {"2": "SD_D3", "3": "SD_D2", "4": "SD_D1", "5": "SD_D0", "6": "SD_CMD", "7": "SD_CK", "8": "MUX_A", "9": "MUX_B", "10": "MUX_C", "12": "LED_CLIP",
             "16": "CODEC_IN_L", "17": "CODEC_IN_R", "18": "CODEC_OUT_L", "19": "CODEC_OUT_R",
             "36": "USB_DM", "37": "USB_DP"}
SEED_PINS.update({pin: sig for sig, pin in PM.SEED_ADC.items()})
SEED_PINS.update({pin: sig for sig, pin in PM.MIDI.items()})


def N(name, _cache={}):
    """A signal net by name (one Net object per name)."""
    for d in (CV, ADC, POT):
        for n in d.values():
            if n.name == name:
                return n
    if name not in _cache:
        _cache[name] = Net(name)
    return _cache[name]


# ------------------------------------------------------------------------------------------------- blocks
@subcircuit
def power():
    """Eurorack power entry, Seed3 VIN filter, -10 V reference (as Electrosmith's Seed3 Eurorack Dev Kit)."""
    j = stock(FM, "Eurorack_Power_10pin_Shrouded", "J13", "EURO PWR 2x5",
              f"{FM}:Pins_2x05_2.54mm_TH_EurorackPower_Shrouded", mpn="2x5 2.54 mm shrouded box header")
    p12_in, n12_in, p12_f, n12_f, vin_f = (Net(x) for x in ("P12_IN", "N12_IN", "P12_F", "N12_F", "VIN_F"))
    p12_in.drive = n12_in.drive = POWER
    j[1, 2] += n12_in
    j[3, 4, 5, 6, 7, 8] += GND
    j[9, 10] += p12_in
    fb = dict(value="600R@100MHz 0.5A", fp=f"{FM}:R_0805_2012Metric", lcsc="C1017", mpn="GZ2012D601TF")   # JLC basic
    for ref, a, b in (("FB1", p12_in, p12_f), ("FB2", n12_in, n12_f)):
        f = stock("Device", "FerriteBead_Small", ref, fb["value"], fb["fp"], fb["lcsc"], fb["mpn"])
        f[1] += a
        f[2] += b
    d = dict(value="B5819W", fp=f"{FM}:D_SOD-123", lcsc="C8598", mpn="B5819W SL")
    d10 = stock("Device", "D_Schottky", "D10", **{"value": d["value"], "fp": d["fp"], "lcsc": d["lcsc"], "mpn": d["mpn"]})
    d10["A"] += p12_f
    d10["K"] += P12
    d11 = stock("Device", "D_Schottky", "D11", d["value"], d["fp"], d["lcsc"], d["mpn"])
    d11["K"] += n12_f
    d11["A"] += N12
    RC("C10u", "C1", P12, GND)
    RC("C10u", "C3", GND, N12)
    bulk = ("100u 35V", "Capacitor_SMD:CP_Elec_6.3x7.7", "C72478", "RVT1V101M0607")
    for ref, plus, minus in (("C2", P12, GND), ("C4", GND, N12), ("C5", vin_f, GND), ("C6", VIN, GND)):
        c = stock("Device", "C_Polarized", ref, *bulk)
        c[1] += plus
        c[2] += minus
    RC("R3R3", "R1", P12, vin_f)
    RC("R3R3", "R2", vin_f, VIN)
    u5 = stock("Reference_Voltage", "LM4040DBZ-10", "U5", "LM4040-10", f"{FM}:SOT-23", "C201738", "LM4040C10IDBZR")
    u5["K"] += GND
    u5["A"] += VREF
    RC("R1k", "R3", VREF, N12)
    RC("C100n", "C7", VREF, GND)


@subcircuit
def seed():
    """Daisy Seed3 on sockets, the clip-LED resistor, the expansion header, and the optional microSD socket."""
    a1 = stock(FM, "Daisy_Seed3", "A1", "Daisy Seed3", f"{FM}:Daisy_Seed_ES_Sockets",
               mpn="Electrosmith Daisy Seed3 on 2x 1x20 2.54 mm sockets")
    for pin, net in SEED_PINS.items():
        a1[pin] += N(net)
    a1["20", "40"] += GND
    a1["21"] += A33
    a1["38"] += D33
    a1["39"] += VIN
    r70 = RC("R1k", "R70", N("LED_CLIP"), N("LED_A"))
    d1 = stock(FM, "Red_3mm_TH", "D1", "red 3 mm", f"{FM}:LED_3mm_C1A2", mpn="3 mm red LED, diffused", board="control")
    d1["2"] += N("LED_A")
    d1["1"] += GND
    j14 = stock("Connector_Generic", "Conn_02x04_Odd_Even", "J14", "EXPANSION 2x4", f"{FM}:Pins_2x04_2.54mm_TH",
                mpn="2x4 2.54 mm pin header, unshrouded")
    for pin, net in {"2": "USB_DM", "3": "USB_DP", "5": "MIDI_TX", "6": "MIDI_RX"}.items():
        j14[pin] += N(net)
    j14[1, 4, 8] += GND
    j14[7] += D33
    # optional microSD socket (as the Dev Kit): SDMMC1 on pins 2-7, 47k pull-ups on CMD and D0-D3; the socket is DNP
    j15 = stock(FM, "MicroSD_TF-01A", "J15", "TF-01A", f"{FM}:TF-01A", "C91145",
                "HRO TF-01A microSD socket, push-push (optional, DNP)")
    for pin, net in {"1": "SD_D2", "2": "SD_D3", "3": "SD_CMD", "5": "SD_CK", "7": "SD_D0", "8": "SD_D1"}.items():
        j15[pin] += N(net)
    j15["4"] += D33
    j15["6", "MP1", "MP2", "MP3", "MP4"] += GND
    j15["CD1"] += Net("NC_J15_CD")
    for ref, net in (("R100", "SD_D2"), ("R101", "SD_D3"), ("R102", "SD_CMD"), ("R103", "SD_D0"), ("R104", "SD_D1")):
        RC("R47k", ref, N(net), D33)
    RC("C100n", "C100", D33, GND)
    # Unused Seed3 pins: explicit no-connects
    used = set(SEED_PINS) | {"20", "21", "38", "39", "40"}
    for k in range(1, 41):
        if str(k) not in used:
            a1[str(k)] += Net(f"NC_A1_{k}")


@subcircuit
def cv_channel(i, quads, leds):
    """CV input i: jack (control) -> inverting stage into the ADC (main; Vout = 1.667 V - Vin/6), and an LM324
    (control) driving the bicolour LED in its feedback loop (LED current = CV / 1.5k)."""
    n = CV_NAMES[i]
    j = stock(FM, "EURO_JACK", f"J{5 + i}", "PJ398SM", f"{FM}:PJ398SM_Jack_4ms_BentGND",
              mpn="Thonkiconn PJ398SM, sleeve leg bent to the footprint", board="control")
    j["TIP"] += CV[n]
    j["NORM", "GND"] += GND
    # ADC stage (main)
    q, unit = ADC_UNIT[n]
    out, inv, plus = SECTION_PINS[unit - 1]
    inv_n = Net(f"INV_{n}")
    if n in ONE_V_OCT:
        rin = Net(f"RIN_{n}")
        RC("R100k_01", f"R{10 + 4 * i}", CV[n], rin)
        RC("R20k_01", f"R{13 + 4 * i}", rin, inv_n)
        RC("R20k_01", f"R{11 + 4 * i}", inv_n, ADC[n])
    else:
        RC("R120k", f"R{10 + 4 * i}", CV[n], inv_n)
        RC("R20k", f"R{11 + 4 * i}", inv_n, ADC[n])
    RC("R120k_25" if n in ONE_V_OCT else "R120k", f"R{12 + 4 * i}", inv_n, VREF)
    RC("C1n", f"C{10 + i}", inv_n, ADC[n])
    u = quads[q]
    u[out] += ADC[n]
    u[inv] += inv_n
    u[plus] += GND
    # LED driver (control)
    ql, unit = LED_UNIT[n]
    out, inv, plus = SECTION_PINS[unit - 1]
    cvb, drv, fbk = Net(f"CVB_{n}"), Net(f"LEDDRV_{n}"), Net(f"LEDFB_{n}")
    RC("R10k_T", f"R{80 + i}", CV[n], cvb, board="control")
    RC("R1M_T", f"R{90 + i}", cvb, GND, board="control")
    ul = leds[ql]
    ul[out] += drv
    ul[inv] += fbk
    ul[plus] += cvb
    d = stock("Device", "LED_Dual_Bidirectional", f"D{2 + i}", "red/green 3 mm", f"{FM}:LED_3mm_Raised",
              mpn="3 mm red/green bicolour LED, 2 leads (anti-parallel), diffused", board="control")
    d[1] += drv
    d[2] += fbk
    RC("R1k5_T", f"R{71 + i}", fbk, GND, board="control")


@subcircuit
def cv_inputs():
    quads = {r: stock("Amplifier_Operational", "LMV324", r, "LMV324", f"{FM}:SOIC-14_3.9x8.65mm_Pitch1.27mm",
                      "C7974", "LMV324IDR") for r in ("U1", "U2")}
    leds = {r: stock("Amplifier_Operational", "LM324", r, "LM324", f"{FM}:SOIC-14_3.9x8.65mm_Pitch1.27mm",
                     "C71035", "LM324DT", board="control") for r in ("U7", "U8")}
    for u, c in (("U1", "C20"), ("U2", "C21")):
        quads[u][4] += A33
        quads[u][11] += GND
        RC("C100n", c, A33, GND)
    for u, cp, cn in (("U7", "C81", "C82"), ("U8", "C83", "C84")):
        leds[u][4] += P12
        leds[u][11] += N12
        RC("C100n_T", cp, P12, GND, board="control")
        RC("C100n_T", cn, GND, N12, board="control")
    for i in range(8):
        cv_channel(i, quads, leds, tag=f"cv{i + 1}")


@subcircuit
def audio():
    """In: gain -0.1 (100k in, 10k // 330p). Out: gain -5.1 (10k in, 51k // 47p). 100R in series with each output."""
    tl = dict(value="TL072", fp=f"{FM}:SOIC-8_3.9x4.9mm_Pitch1.27mm", lcsc="C6961", mpn="TL072CDT")   # JLC basic (ST)
    u3 = stock(FM, "TL072", "U3", **tl)
    u4 = stock(FM, "TL072", "U4", **tl)
    jack = dict(value="PJ398SM", fp=f"{FM}:PJ398SM_Jack_ES", mpn="Thonkiconn PJ398SM")
    j1, j2, j3, j4 = (stock(FM, "EURO_JACK", r, **jack, board="control") for r in ("J1", "J2", "J3", "J4"))
    j1["TIP"] += N("IN_L")
    j1["NORM", "GND"] += GND
    j2["TIP"] += N("IN_R")
    j2["NORM"] += N("IN_L")          # IN R normalled to IN L
    j2["GND"] += GND
    j3["TIP"] += N("OUT_L")
    j4["TIP"] += N("OUT_R")
    j3["GND"] += GND
    j4["GND"] += GND
    j3["NORM"] += Net("NC_J3_NORM")
    j4["NORM"] += Net("NC_J4_NORM")
    for side, (o, m, p), (rin, rf, cf, rs), (oin, rfo, cfo, rso) in (
            ("L", ("1", "2", "3"), ("R50", "R51", "C50", "R52"), ("R60", "R61", "C60", "R62")),
            ("R", ("7", "6", "5"), ("R54", "R55", "C52", "R56"), ("R64", "R65", "C62", "R66"))):
        ai, ao = N(f"AIN_{side}_INV"), N(f"AIN_{side}_OUT")
        RC("R100k", rin, N(f"IN_{side}"), ai)
        RC("R10k", rf, ai, ao)
        RC("C330p", cf, ai, ao)
        RC("R100", rs, ao, N(f"CODEC_IN_{side}"))
        u3[o] += ao
        u3[m] += ai
        u3[p] += GND
        bi, bo = N(f"AOUT_{side}_INV"), N(f"AOUT_{side}_OUT")
        RC("R10k", oin, N(f"CODEC_OUT_{side}"), bi)
        RC("R51k", rfo, bi, bo)          # x5.1 (d, 2026-10-06); the Dev Kit's 100k // 33p (x10) clips above -3 dBFS
        RC("C47p", cfo, bi, bo)
        RC("R100", rso, bo, N(f"OUT_{side}"))
        u4[o] += bo
        u4[m] += bi
        u4[p] += GND
    for u, cp, cn in ((u3, "C70", "C71"), (u4, "C72", "C73")):
        u[8] += P12
        u[4] += N12
        RC("C100n", cp, P12, GND)
        RC("C100n", cn, GND, N12)


@subcircuit
def controls():
    """Nine pots (CCW end GND, CW end +3V3_A) and the 74HC4051 that shares one ADC pin among eight of them."""
    pot = dict(value="B10k", fp=f"{FM}:Pot_9mm_SnapIn_ES", mpn="Alpha RD901F 9 mm B10k (any shaft)")
    for i, k in enumerate(["VOL"] + CV_NAMES):
        rv = stock(FM, "POT_9MM", f"RV{i + 1}", **pot, board="control")
        rv[1] += GND
        rv[3] += A33
        rv[2] += N("POT_VOL") if k == "VOL" else POT[k]
    u6 = stock("74xx", "74HC4051", "U6", "74HC4051", f"{FM}:SOIC-16_3.9x9.9mm_Pitch1.27mm", "C9386", "74HC4051D,653",
               board="control")
    for k, pin in MUX_PIN.items():
        u6[pin] += POT[k]
    u6["3"] += N("POT_MUX")
    u6["11"] += N("MUX_A")      # S0
    u6["10"] += N("MUX_B")      # S1
    u6["9"] += N("MUX_C")       # S2
    u6["6", "7", "8"] += GND    # enable (active low), VEE, GND
    u6["16"] += A33
    RC("C100n_T", "C80", A33, GND, board="control")


@subcircuit
def connectors():
    """The board-to-board headers (rev beta), one pair per row of design/pinmap.py HEADER_PINS: JAn (female, on the
    control board's back) plugs onto JBn (male, on the main board's front), pin k to pin k."""
    for h, sigs in sorted(PM.HEADER_PINS.items()):
        n = len(sigs)
        for ref, board, fp, value, mpn in (
                (f"JA{h}", "control", f"Connector_PinSocket_2.54mm:PinSocket_1x{n:02d}_P2.54mm_Vertical",
                 f"1x{n} socket", f"2.54 mm female header 1x{n}, 8.5 mm (as the Seed3 sockets)"),
                (f"JB{h}", "main", f"Connector_PinHeader_2.54mm:PinHeader_1x{n:02d}_P2.54mm_Vertical",
                 f"1x{n} header", f"2.54 mm male pin header 1x{n}")):
            if BOARD != board:              # headers exist only in the per-board netlists
                continue
            j = stock("Connector_Generic", f"Conn_01x{n:02d}", ref, value, fp, mpn=mpn, board=board)
            for k, sig in enumerate(sigs):
                j[k + 1] += {"GND": GND, "+12V": P12, "-12V": N12, "+3V3_A": A33}.get(sig) or N(sig)


def build():
    power(tag="power")
    seed(tag="seed")
    cv_inputs(tag="cv")
    audio(tag="audio")
    controls(tag="controls")
    connectors(tag="connectors")


def firmware_mux_table():
    by_ch = {MUX_CHANNEL_OF_PIN[pin]: k for k, pin in MUX_PIN.items()}
    return [by_ch[c] for c in range(8)]


OUTFILE = {"all": "logical.net", "main": "main.net", "control": "control.net"}

if __name__ == "__main__":
    if not BOARD:                           # one process per board: SKiDL keeps one global circuit per process
        for b in OUTFILE:
            r = subprocess.run([sys.executable, __file__] + sys.argv[1:], env={**os.environ, "BOARD": b})
            if r.returncode:
                sys.exit(r.returncode)
        print("mux select 0..7 ->", firmware_mux_table())
        sys.exit(0)
    build()
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    generate_netlist(file_=os.path.join(HERE, "out", OUTFILE[BOARD]))
    if "--skidl-schematic" in sys.argv and BOARD == "all":
        os.makedirs(os.path.join(HERE, "out", "skidl-schematic"), exist_ok=True)
        generate_schematic(filepath=os.path.join(HERE, "out", "skidl-schematic"), top_name="machine_filter",
                           title="MACHINE FILTER rev beta", auto_stub=True)
