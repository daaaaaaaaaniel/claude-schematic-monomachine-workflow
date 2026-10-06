"""MACHINE FILTER, Seed3 build: the circuit board as data. The single source for the schematic, PCB and BOMs.

One 4-layer board (d, 2026-10-06; it was a control board and a main board until then). Its front faces the panel and
carries the jacks, pots and LEDs (hand-soldered); its back carries every SMD part (JLC), the Daisy Seed3 on sockets,
the power header and the expansion header (hand-soldered).
Panel frame: x right, y down, mm, from the panel's top-left corner (as panels/gen_o3_machine.py), seen from the front.
"""
import math
from dataclasses import dataclass, field

W = 70.8                       # 14HP panel width
BOARD_X = (0.4, 70.4)          # panel frame
BOARD_Y = (10.75, 117.75)      # inside the ~10.25-118.25 band the rails leave

# ---------------------------------------------------------------- panel positions (from panels/gen_o3_machine.py)
# 2026-10-06 (d): panel I/O mock-up "E14"; jacks, knobs and LEDs 0.5 mm left of the first layout; CV rows 1 mm lower
# at the top (52.2 ... 110.8); a bicolour LED by every CV jack. design/check_panel.py checks these against the panel.
COLS, ROWS = (12.9, 32.9), (18.5, 41.5, 64.5, 87.5, 110.5)
KNOB = {"VOL": (0, 0), "BASE": (0, 1), "WIDTH": (1, 1), "HPRES": (0, 2), "LPRES": (1, 2),
        "EQF": (0, 3), "EQG": (1, 3), "DIST": (0, 4), "SRR": (1, 4)}
JX = (50.7, 63.2)
CV_Y = tuple(52.2 + i * (110.8 - 52.2) / 3 for i in range(4))
CV_JACK = {"BASE": (JX[0], CV_Y[0]), "WIDTH": (JX[1], CV_Y[0]), "HPRES": (JX[0], CV_Y[1]), "LPRES": (JX[1], CV_Y[1]),
           "EQF": (JX[0], CV_Y[2]), "EQG": (JX[1], CV_Y[2]), "DIST": (JX[0], CV_Y[3]), "SRR": (JX[1], CV_Y[3])}
CV_LED_OFF = (-2.5, -6.8)          # 11 o'clock, 7.2 mm from the jack's centre
CV_LED = {n: (x + CV_LED_OFF[0], y + CV_LED_OFF[1]) for n, (x, y) in CV_JACK.items()}
OUT_Y, IN_Y = 19.8, 32.8           # OUT over IN (E14), 13 mm apart: the OUT jacks turned round, legs up
AUDIO_JACK = {"IN_L": (JX[0], IN_Y), "IN_R": (JX[1], IN_Y), "OUT_L": (JX[0], OUT_Y), "OUT_R": (JX[1], OUT_Y)}
def knob_xy(k):
    c, r = KNOB[k]
    return COLS[c], ROWS[r]
LED_XY = (COLS[0] + 9.0 * math.sin(math.radians(60)), 18.5 - 9.0 * math.cos(math.radians(60)))   # 2 o'clock from VOLUME

CV_NAMES = ["BASE", "WIDTH", "HPRES", "LPRES", "EQF", "EQG", "DIST", "SRR"]
CV_LABEL = {"BASE": "BASE · 1V/OCT", "WIDTH": "WIDTH (1V/OCT)", "HPRES": "HP RES", "LPRES": "LP RES",
            "EQF": "EQ FREQ", "EQG": "EQ GAIN", "DIST": "DISTORTION", "SRR": "SMPL RATE"}
ONE_V_OCT = {"BASE", "WIDTH"}

# ---------------------------------------------------------------- parts catalogue
# lib_id, footprint, value, LCSC (None = hand-soldered, not in the JLC BOM), MPN
FM = "filter-module"
def R(v, lcsc, mpn, fp=f"{FM}:R_0603"):
    return dict(lib="Device:R", fp=fp, value=v, lcsc=lcsc, mpn=mpn)
def C(v, lcsc, mpn, fp=f"{FM}:C_0603"):
    return dict(lib="Device:C", fp=fp, value=v, lcsc=lcsc, mpn=mpn)
BOARD = "machine-filter"
CAT = {
    "R100k": R("100k", "C25803", "0603WAF1003T5E"),
    "R100k_01": R("100k 0.1%", "C122538", "RT0603BRD07100KL"),
    "R20k": R("20k", "C4184", "0603WAF2002T5E"),
    "R20k_01": R("20k 0.1%", "C723637", "RT0603BRD0720KL"),
    "R120k": R("120k", "C25808", "0603WAF1203T5E"),
    "R10k": R("10k", "C25804", "0603WAF1002T5E"),
    "R1k": R("1k", "C21190", "0603WAF1001T5E"),
    "R1k5": R("1.5k", "C22843", "0603WAF1501T5E"),
    "R1M": R("1M", "C22935", "0603WAF1004T5E"),
    "R100": R("100", "C22775", "0603WAF1000T5E"),
    "R3R3": R("3.3 0.75W", "C2577888", "SG73P2BTTD3R30F", fp=f"{FM}:R_1206_3216Metric"),   # Dev Kit's anti-surge part
    "C100n": C("100n", "C14663", "CC0603KRX7R9BB104"),
    "C1n": C("1n", "C1588", "CL10B102KB8NNNC"),
    "C330p": C("330p", "C1664", "CL10C331JB8NNNC"),
    "C33p": C("33p", "C1663", "CL10C330JB8NNNC"),
    "C10u": C("10u 25V", "C15850", "CL21A106KAYNNNE", fp=f"{FM}:C_0805"),
    "C100u": dict(lib="Device:C_Polarized", fp="Capacitor_SMD:CP_Elec_6.3x7.7", value="100u 35V", lcsc="C72478",
                  mpn="RVT1V101M0607"),
    "FB": dict(lib="Device:FerriteBead_Small", fp=f"{FM}:R_0603", value="600R@100MHz 1A", lcsc="C108301",
               mpn="PBY160808T-601Y-N"),   # the Dev Kit's; the basic C1002 is only rated 200 mA
    "SCHOTTKY": dict(lib="Device:D_Schottky", fp=f"{FM}:D_SOD-123", value="B5819W", lcsc="C8598", mpn="B5819W SL"),
    "TL072": dict(lib=f"{FM}:TL072", fp=f"{FM}:SOIC-8_3.9x4.9mm_Pitch1.27mm", value="TL072", lcsc="C6962", mpn="TL072IDR"),
    "LMV324": dict(lib="Amplifier_Operational:LMV324", fp=f"{FM}:SOIC-14_3.9x8.65mm_Pitch1.27mm", value="LMV324",
                   lcsc="C7974", mpn="LMV324IDR"),
    "MUX": dict(lib="74xx:74HC4051", fp=f"{FM}:SOIC-16_3.9x9.9mm_Pitch1.27mm", value="74HC4051", lcsc="C9386",
                mpn="74HC4051D,653"),
    "LM4040": dict(lib="Reference_Voltage:LM4040DBZ-10", fp=f"{FM}:SOT-23", value="LM4040-10", lcsc="C201738",
                   mpn="LM4040C10IDBZR"),
    # hand-soldered
    "JACK": dict(lib=f"{FM}:EURO_JACK", fp=f"{FM}:PJ398SM_Jack_ES", value="PJ398SM", lcsc=None, mpn="Thonkiconn PJ398SM"),
    "POT": dict(lib=f"{FM}:POT_9MM", fp=f"{FM}:Pot_9mm_SnapIn_ES", value="B10k", lcsc=None, mpn="Alpha RD901F 9 mm B10k (any shaft)"),
    "LED": dict(lib=f"{FM}:Red_3mm_TH", fp=f"{FM}:LED_3mm_C1A2", value="red 3 mm", lcsc=None, mpn="3 mm red LED, diffused"),
    "LEDRG": dict(lib="Device:LED_Dual_Bidirectional", fp=f"{FM}:LED_3mm_Raised", value="red/green 3 mm",
                  lcsc=None, mpn="3 mm red/green bicolour LED, 2 leads (anti-parallel), diffused"),
    "JACK_CV": dict(lib=f"{FM}:EURO_JACK", fp=f"{FM}:PJ398SM_Jack_4ms_BentGND", value="PJ398SM", lcsc=None,
                    mpn="Thonkiconn PJ398SM, sleeve leg bent to the footprint"),
    "LM324": dict(lib="Amplifier_Operational:LM324", fp=f"{FM}:SOIC-14_3.9x8.65mm_Pitch1.27mm", value="LM324",
                  lcsc="C71035", mpn="LM324DT"),
    "SEED": dict(lib=f"{FM}:Daisy_Seed3", fp=f"{FM}:Daisy_Seed_ES_Sockets", value="Daisy Seed3", lcsc=None,
                 mpn="Electrosmith Daisy Seed3 on 2x 1x20 2.54 mm sockets"),
    "PWR": dict(lib=f"{FM}:Eurorack_Power_10pin_Shrouded", fp=f"{FM}:Pins_2x05_2.54mm_TH_EurorackPower_Shrouded",
                value="EURO PWR 2x5", lcsc=None, mpn="2x5 2.54 mm shrouded box header"),
    "EXP": dict(lib="Connector_Generic:Conn_02x04_Odd_Even", fp=f"{FM}:Pins_2x04_2.54mm_TH",
                value="EXPANSION 2x4", lcsc=None, mpn="2x4 2.54 mm pin header, unshrouded (d)"),
    "FLAG": dict(lib=f"{FM}:PWR_FLAG", fp="", value="PWR_FLAG", lcsc=None, mpn="", bom=False, board=False),
}


@dataclass
class Part:
    ref: str
    kind: str
    pins: dict                  # pin number -> net ("" or None = no connect)
    block: str
    note: str = ""
    xy: tuple = None            # panel-frame position of the front parts (the rest are placed by gen_pcb.py)
    rot: float = 0.0
    side: str = "top"

    @property
    def cat(self):
        return CAT[self.kind]


def _flag(ref, net, block="Power flags"):
    return Part(ref, "FLAG", {"1": net}, block)


MUX_CH = {"BASE": "13", "WIDTH": "14", "HPRES": "15", "LPRES": "12", "EQF": "1", "EQG": "5", "DIST": "2", "SRR": "4"}


def _controls():
    """The front: jacks, pots and LEDs, all through-hole and hand-soldered."""
    P = []
    # jacks: TIP / NORM (switch, made when unplugged) / GND (sleeve)
    P.append(Part("J1", "JACK", {"TIP": "IN_L", "NORM": "GND", "GND": "GND"}, "Audio jacks", "IN L"))
    P.append(Part("J2", "JACK", {"TIP": "IN_R", "NORM": "IN_L", "GND": "GND"}, "Audio jacks", "IN R (normalled to IN L)"))
    P.append(Part("J3", "JACK", {"TIP": "OUT_L", "NORM": None, "GND": "GND"}, "Audio jacks", "OUT L"))
    P.append(Part("J4", "JACK", {"TIP": "OUT_R", "NORM": None, "GND": "GND"}, "Audio jacks", "OUT R"))
    for (k, xy), ref in zip(AUDIO_JACK.items(), ["J1", "J2", "J3", "J4"]):
        next(p for p in P if p.ref == ref).xy = xy
    for i, n in enumerate(CV_NAMES):
        P.append(Part(f"J{5+i}", "JACK_CV", {"TIP": f"CV_{n}", "NORM": "GND", "GND": "GND"}, "CV jacks",
                      f"{CV_LABEL[n]} CV", CV_JACK[n]))
    # pots: 1 = CCW end (GND), 3 = CW end (+3V3_A), 2 = wiper
    for i, k in enumerate(["VOL"] + CV_NAMES):
        wiper = "POT_VOL" if k == "VOL" else f"POT_{k}"
        P.append(Part(f"RV{i+1}", "POT", {"1": "GND", "2": wiper, "3": "+3V3_A"}, "Pots",
                      "VOLUME" if k == "VOL" else CV_LABEL[k], knob_xy(k)))
    P.append(Part("D1", "LED", {"1": "GND", "2": "LED_A"}, "Clip LED", "clip LED, 2 o'clock from VOLUME", LED_XY))
    # CV LEDs: driven by U7 / U8 (see board()); green for +, red for -
    for i, n in enumerate(CV_NAMES):
        P.append(Part(f"D{2+i}", "LEDRG", {"1": f"LEDDRV_{n}", "2": f"LEDFB_{n}"}, "CV LEDs",
                      f"{CV_LABEL[n]} CV LED: green +, red -", CV_LED[n]))
    return P


def board():
    P = _controls()
    S = {str(i): None for i in range(1, 41)}
    S.update({"8": "MUX_A", "9": "MUX_B", "10": "MUX_C", "12": "LED_CLIP", "14": "MIDI_TX", "15": "MIDI_RX",
              "16": "CODEC_IN_L", "17": "CODEC_IN_R", "18": "CODEC_OUT_L", "19": "CODEC_OUT_R",
              "20": "GND", "21": "+3V3_A", "22": "POT_MUX", "31": "POT_VOL", "36": "USB_DM", "37": "USB_DP",
              "38": "+3V3_D", "39": "VIN", "40": "GND"})
    for i, n in enumerate(CV_NAMES):
        S[str(23 + i)] = f"ADC_{n}"
    P.append(Part("A1", "SEED", S, "Daisy Seed3", "on two 1x20 sockets"))
    # power entry (as Electrosmith's Seed3 Eurorack Dev Kit)
    P.append(Part("J13", "PWR", {"1": "N12_IN", "2": "N12_IN", **{str(i): "GND" for i in range(3, 9)},
                                "9": "P12_IN", "10": "P12_IN"}, "Power", "Eurorack 10-pin, -12 V on the red stripe"))
    P += [Part("FB1", "FB", {"1": "P12_IN", "2": "P12_F"}, "Power"),
          Part("FB2", "FB", {"1": "N12_IN", "2": "N12_F"}, "Power"),
          Part("D10", "SCHOTTKY", {"2": "P12_F", "1": "+12V"}, "Power", "reverse-polarity, +12 V"),    # 1 = K, 2 = A
          Part("D11", "SCHOTTKY", {"1": "N12_F", "2": "-12V"}, "Power", "reverse-polarity, -12 V"),
          Part("C1", "C10u", {"1": "+12V", "2": "GND"}, "Power"),
          Part("C2", "C100u", {"1": "+12V", "2": "GND"}, "Power"),
          Part("C3", "C10u", {"1": "GND", "2": "-12V"}, "Power"),
          Part("C4", "C100u", {"1": "GND", "2": "-12V"}, "Power"),
          Part("R1", "R3R3", {"1": "+12V", "2": "VIN_F"}, "Seed3 supply", "+12 V -> Seed3 VIN, as the Dev Kit"),
          Part("C5", "C100u", {"1": "VIN_F", "2": "GND"}, "Seed3 supply"),
          Part("R2", "R3R3", {"1": "VIN_F", "2": "VIN"}, "Seed3 supply"),
          Part("C6", "C100u", {"1": "VIN", "2": "GND"}, "Seed3 supply"),
          Part("U5", "LM4040", {"1": "GND", "2": "-10V_REF", "3": None}, "-10 V reference"),
          Part("R3", "R1k", {"1": "-10V_REF", "2": "-12V"}, "-10 V reference",
               "1k, not the Dev Kit's 2k: eight 120k offsets draw 0.67 mA"),
          Part("C7", "C100n", {"1": "-10V_REF", "2": "GND"}, "-10 V reference")]
    # CV inputs: inverting stage, 120k in, 20k feedback, 120k to -10 V: Vout = 1.667 - Vin/6, so +/-8 V -> 0.33..3.0 V,
    # 0.3 V clear of the LMV324's guaranteed swing (review, 2026-10-05). The 1V/OCT inputs make their 120k from
    # 100k + 20k at 0.1%, the same precision parts as the 20k feedback.
    for i, n in enumerate(CV_NAMES):
        u = "U1" if i < 4 else "U2"
        unit = i % 4
        out, inv, plus = [("1", "2", "3"), ("7", "6", "5"), ("8", "9", "10"), ("14", "13", "12")][unit]
        blk = f"CV {i+1}: {CV_LABEL[n]}"
        prec = n in ONE_V_OCT
        if prec:
            P += [Part(f"R{10+4*i}", "R100k_01", {"1": f"CV_{n}", "2": f"RIN_{n}"}, blk, "R_in, part 1 (0.1%)"),
                  Part(f"R{13+4*i}", "R20k_01", {"1": f"RIN_{n}", "2": f"INV_{n}"}, blk, "R_in, part 2 (0.1%)")]
        else:
            P.append(Part(f"R{10+4*i}", "R120k", {"1": f"CV_{n}", "2": f"INV_{n}"}, blk, "R_in"))
        P += [Part(f"R{11+4*i}", "R20k_01" if prec else "R20k", {"1": f"INV_{n}", "2": f"ADC_{n}"}, blk, "R_f"),
              Part(f"R{12+4*i}", "R120k", {"1": f"INV_{n}", "2": "-10V_REF"}, blk, "offset"),
              Part(f"C{10+i}", "C1n", {"1": f"INV_{n}", "2": f"ADC_{n}"}, blk, "8 kHz")]
        P.append(Part(f"{u}.{unit+1}", None, {out: f"ADC_{n}", inv: f"INV_{n}", plus: "GND"}, blk))
    for u in ("U1", "U2"):
        P.append(Part(f"{u}.5", None, {"4": "+3V3_A", "11": "GND"}, "CV op-amp supply"))
    P += [Part("C20", "C100n", {"1": "+3V3_A", "2": "GND"}, "CV op-amp supply", "U1"),
          Part("C21", "C100n", {"1": "+3V3_A", "2": "GND"}, "CV op-amp supply", "U2")]
    # audio: in x0.1, out x10 (Dev Kit values)
    for side, (u_in, unit_pins) in {"L": ("A", ("1", "2", "3")), "R": ("B", ("7", "6", "5"))}.items():
        o, m, p = unit_pins
        b = f"Audio in {side}"
        P += [Part(f"R{50 if side=='L' else 54}", "R100k", {"1": f"IN_{side}", "2": f"AIN_{side}_INV"}, b),
              Part(f"R{51 if side=='L' else 55}", "R10k", {"1": f"AIN_{side}_INV", "2": f"AIN_{side}_OUT"}, b),
              Part(f"C{50 if side=='L' else 52}", "C330p", {"1": f"AIN_{side}_INV", "2": f"AIN_{side}_OUT"}, b),
              Part(f"R{52 if side=='L' else 56}", "R100", {"1": f"AIN_{side}_OUT", "2": f"CODEC_IN_{side}"}, b),
              Part(f"U3.{1 if side=='L' else 2}", None, {o: f"AIN_{side}_OUT", m: f"AIN_{side}_INV", p: "GND"}, b)]
        b = f"Audio out {side}"
        P += [Part(f"R{60 if side=='L' else 64}", "R10k", {"1": f"CODEC_OUT_{side}", "2": f"AOUT_{side}_INV"}, b),
              Part(f"R{61 if side=='L' else 65}", "R100k", {"1": f"AOUT_{side}_INV", "2": f"AOUT_{side}_OUT"}, b),
              Part(f"C{60 if side=='L' else 62}", "C33p", {"1": f"AOUT_{side}_INV", "2": f"AOUT_{side}_OUT"}, b),
              Part(f"R{62 if side=='L' else 66}", "R100", {"1": f"AOUT_{side}_OUT", "2": f"OUT_{side}"}, b),
              Part(f"U4.{1 if side=='L' else 2}", None, {o: f"AOUT_{side}_OUT", m: f"AOUT_{side}_INV", p: "GND"}, b)]
    for u in ("U3", "U4"):
        P.append(Part(f"{u}.3", None, {"8": "+12V", "4": "-12V"}, "Audio op-amp supply"))
    P += [Part("C70", "C100n", {"1": "+12V", "2": "GND"}, "Audio op-amp supply", "U3 V+"),
          Part("C71", "C100n", {"1": "GND", "2": "-12V"}, "Audio op-amp supply", "U3 V-"),
          Part("C72", "C100n", {"1": "+12V", "2": "GND"}, "Audio op-amp supply", "U4 V+"),
          Part("C73", "C100n", {"1": "GND", "2": "-12V"}, "Audio op-amp supply", "U4 V-")]
    P.append(Part("J14", "EXP", {"1": "GND", "2": "USB_DM", "3": "USB_DP", "4": "GND", "5": "MIDI_TX", "6": "MIDI_RX",
                                "7": "+3V3_D", "8": "GND"}, "Expansion header",
                  "to the 2HP USB-C / MIDI expander (ribbon: pin = wire)"))
    # pot multiplexer: 8 wipers -> POT_MUX; S0/S1/S2 = MUX_A/B/C
    mux = {"3": "POT_MUX", "6": "GND", "7": "GND", "8": "GND", "16": "+3V3_A", "11": "MUX_A", "10": "MUX_B", "9": "MUX_C"}
    for k, pin in MUX_CH.items():
        mux[pin] = f"POT_{k}"
    P.append(Part("U6", "MUX", mux, "Pot multiplexer", "8 pot wipers -> POT_MUX"))
    P.append(Part("C80", "C100n", {"1": "+3V3_A", "2": "GND"}, "Pot multiplexer", "U6 decoupling"))
    P.append(Part("R70", "R1k", {"1": "LED_CLIP", "2": "LED_A"}, "Clip LED", "LED current ~1.4 mA at 3.3 V"))
    # CV LEDs (d, 2026-10-06): each jack's CV drives a 2-lead red/green LED by the jack, green for +, red for
    # -, with the LED inside an LM324's feedback loop (as Mutable Instruments' Shades): CV -> 10k -> + input (1M to
    # GND), the LED from the output to the - input, 1.5k from the - input to
    # GND. LED current = CV / 1.5k (0.7 mA at 1 V, 3.3 mA at 5 V), no dead zone, levelling off near 5.5-6 mA from about
    # +/-8.5 V; the + input loads nothing. 10k: input protection; 1M: an undriven cable reads 0 V, LED dark.
    for i, n in enumerate(CV_NAMES):
        u, unit = ("U7", "U8")[i // 4], i % 4
        out, inv, plus = [("1", "2", "3"), ("7", "6", "5"), ("8", "9", "10"), ("14", "13", "12")][unit]
        blk = f"CV LED {i+1}: {CV_LABEL[n]}"
        P.append(Part(f"R{80+i}", "R10k", {"1": f"CV_{n}", "2": f"CVB_{n}"}, blk, "input protection"))
        P.append(Part(f"R{90+i}", "R1M", {"1": f"CVB_{n}", "2": "GND"}, blk, "holds an undriven cable at 0 V"))
        P.append(Part(f"{u}.{unit+1}", None, {out: f"LEDDRV_{n}", inv: f"LEDFB_{n}", plus: f"CVB_{n}"}, blk))
        P.append(Part(f"R{71+i}", "R1k5", {"1": f"LEDFB_{n}", "2": "GND"}, blk, "sets the LED current: CV / 1.5k"))
    for u in ("U7", "U8"):
        P.append(Part(f"{u}.5", None, {"4": "+12V", "11": "-12V"}, "CV LED driver supply"))
    P += [Part("C81", "C100n", {"1": "+12V", "2": "GND"}, "CV LED driver supply", "U7 V+"),
          Part("C82", "C100n", {"1": "GND", "2": "-12V"}, "CV LED driver supply", "U7 V-"),
          Part("C83", "C100n", {"1": "+12V", "2": "GND"}, "CV LED driver supply", "U8 V+"),
          Part("C84", "C100n", {"1": "GND", "2": "-12V"}, "CV LED driver supply", "U8 V-")]
    P += [_flag("#FLG1", "+12V"), _flag("#FLG2", "-12V"), _flag("#FLG3", "GND"), _flag("#FLG4", "VIN"),
          _flag("#FLG5", "P12_IN"), _flag("#FLG6", "N12_IN")]
    # attach op-amp units to their package part
    return _merge_units(P, {"U1": "LMV324", "U2": "LMV324", "U3": "TL072", "U4": "TL072", "U7": "LM324", "U8": "LM324"})


def _merge_units(P, kinds):
    """Op-amp units are listed as 'U1.n'; fold them into one Part per package, remembering each unit's block."""
    out, pk = [], {}
    for p in P:
        if "." in p.ref and p.kind is None:
            ref, unit = p.ref.split(".")
            if ref not in pk:
                pk[ref] = Part(ref, kinds[ref], {}, p.block)
                pk[ref].unit_blocks = {}
                out.append(pk[ref])
            pk[ref].pins.update(p.pins)
            pk[ref].unit_blocks[int(unit)] = p.block
        else:
            out.append(p)
    return out


def nets(parts):
    n = {}
    for p in parts:
        for pin, net in p.pins.items():
            if net:
                n.setdefault(net, []).append((p.ref, pin))
    return n


if __name__ == "__main__":
    for name, fn in ((BOARD, board),):
        P = fn()
        N = nets(P)
        print(name, len(P), "parts,", len(N), "nets")
        for k, v in sorted(N.items()):
            if len(v) < 2:
                print("   single-pin net:", k, v)
