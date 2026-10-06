"""MACHINE FILTER, Seed3 build: the circuit as data, for the drawn schematics (gen_sch.py) and the PCB scripts.
machine_filter.py (SKiDL) describes the same circuit independently; tools/check_netlist.py holds the two together.

Rev beta (d, 2026-10-06): two boards joined by 2.54 mm headers.
  CONTROL (hand-soldered): front = jacks, pots, LEDs; back = pot multiplexer U6, CV-LED drivers U7/U8 (SOIC), their
          through-hole resistors and capacitors, female headers JA1-JA3 (from pinmap.py).
  MAIN (JLC PCBA, <= 100 x 100 mm): every SMD part, the Daisy Seed3 on sockets, the power and expansion headers,
          male headers JB1-JB3 (from pinmap.py).
Pin assignments (Seed3 ADC pins, op-amp sections, mux channels, header pin order) come from design/pinmap.py,
written by design/floorplan.py.
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
    "R120k_25": R("120k 25ppm", "C862537", "RT0603DRD07120KL"),     # 1V/OCT offset: 0.5 %, 25 ppm/K thin film
    "R51k": R("51k", "C23196", "0603WAF5102T5E"),
    "R47k": R("47k", "C25819", "0603WAF4702T5E"),
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
    "C47p": C("47p", "C1671", "CL10C470JB8NNNC"),
    "SDCARD": dict(lib=f"{FM}:MicroSD_TF-01A", fp=f"{FM}:TF-01A", value="TF-01A", lcsc="C91145",
                   mpn="HRO TF-01A microSD socket, push-push (optional, DNP)"),
    "C10u": C("10u 25V", "C15850", "CL21A106KAYNNNE", fp=f"{FM}:C_0805"),
    "C100u": dict(lib="Device:C_Polarized", fp="Capacitor_SMD:CP_Elec_6.3x7.7", value="100u 35V", lcsc="C72478",
                  mpn="RVT1V101M0607"),
    "FB": dict(lib="Device:FerriteBead_Small", fp=f"{FM}:R_0805_2012Metric", value="600R@100MHz 0.5A", lcsc="C1017",
               mpn="GZ2012D601TF"),   # JLC basic, 0805, 500 mA (the Dev Kit's 1 A C108301 is extended; the 0603
                                      # basic C1002 is only 200 mA; the +12 V rail draws about 0.2 A worst case)
    "SCHOTTKY": dict(lib="Device:D_Schottky", fp=f"{FM}:D_SOD-123", value="B5819W", lcsc="C8598", mpn="B5819W SL"),
    "TL072": dict(lib=f"{FM}:TL072", fp=f"{FM}:SOIC-8_3.9x4.9mm_Pitch1.27mm", value="TL072", lcsc="C6961", mpn="TL072CDT"),   # JLC basic (ST)
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
    # control board (rev beta): through-hole passives, hand-soldered
    "R10k_T": dict(lib="Device:R", fp="Resistor_THT:R_Axial_DIN0204_L3.6mm_D1.6mm_P5.08mm_Horizontal", value="10k",
                   lcsc=None, mpn="10k 1/8 W 1% metal film, axial DIN0204"),
    "R1M_T": dict(lib="Device:R", fp="Resistor_THT:R_Axial_DIN0204_L3.6mm_D1.6mm_P5.08mm_Horizontal", value="1M",
                  lcsc=None, mpn="1M 1/8 W 1% metal film, axial DIN0204"),
    "R1k5_T": dict(lib="Device:R", fp="Resistor_THT:R_Axial_DIN0204_L3.6mm_D1.6mm_P5.08mm_Horizontal", value="1.5k",
                   lcsc=None, mpn="1.5k 1/8 W 1% metal film, axial DIN0204"),
    "C100n_T": dict(lib="Device:C", fp="Capacitor_THT:C_Disc_D3.0mm_W1.6mm_P2.50mm", value="100n", lcsc=None,
                    mpn="100 nF 50 V X7R ceramic, 2.5 mm pitch"),
    # board-to-board headers (rev beta)
    **{f"HDR_F{n}": dict(lib=f"Connector_Generic:Conn_01x{n:02d}",
                         fp=f"Connector_PinSocket_2.54mm:PinSocket_1x{n:02d}_P2.54mm_Vertical", value=f"1x{n} socket",
                         lcsc=None, mpn=f"2.54 mm female header 1x{n}, 8.5 mm (as the Seed3 sockets)") for n in range(1, 41)},
    **{f"HDR_M{n}": dict(lib=f"Connector_Generic:Conn_01x{n:02d}",
                         fp=f"Connector_PinHeader_2.54mm:PinHeader_1x{n:02d}_P2.54mm_Vertical", value=f"1x{n} header",
                         lcsc=None, mpn=f"2.54 mm male pin header 1x{n}") for n in range(1, 41)},
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
    board: str = "main"         # "main" (JLC PCBA) or "control" (hand-soldered)
    dnp: bool = False           # do not populate (an option: fit it per build)

    @property
    def cat(self):
        return CAT[self.kind]


def _flag(ref, net, block="Power flags", board="main"):
    return Part(ref, "FLAG", {"1": net}, block, board=board)


def _pinmap():
    """design/pinmap.py (from floorplan.py), or None while floorplan.py is being run for the first time."""
    try:
        import pinmap
        return pinmap
    except ImportError:
        return None


SECTION_PINS = [("1", "2", "3"), ("7", "6", "5"), ("8", "9", "10"), ("14", "13", "12")]   # unit 1-4: out, -, +


def _controls():
    """The control board's front: jacks, pots and LEDs, all through-hole and hand-soldered."""
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
    for p in P:
        p.board = "control"
    return P


def board():
    pm = _pinmap()
    P = _controls()
    S = {str(i): None for i in range(1, 41)}
    S.update({"2": "SD_D3", "3": "SD_D2", "4": "SD_D1", "5": "SD_D0", "6": "SD_CMD", "7": "SD_CK",
              "8": "MUX_A", "9": "MUX_B", "10": "MUX_C", "12": "LED_CLIP",
              "16": "CODEC_IN_L", "17": "CODEC_IN_R", "18": "CODEC_OUT_L", "19": "CODEC_OUT_R",
              "20": "GND", "21": "+3V3_A", "36": "USB_DM", "37": "USB_DP", "38": "+3V3_D", "39": "VIN", "40": "GND"})
    if pm:      # rev beta: ADC pins and MIDI (D2/D1 = USART3, off the pins next to the codec) from the floorplan
        for sig, pin in pm.SEED_ADC.items():
            S[pin] = sig
        for sig, pin in pm.MIDI.items():
            S[pin] = sig
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
        u, unit = pm.ADC_UNIT[n] if pm else ("U1" if i < 4 else "U2", i % 4 + 1)
        unit -= 1
        out, inv, plus = [("1", "2", "3"), ("7", "6", "5"), ("8", "9", "10"), ("14", "13", "12")][unit]
        blk = f"CV {i+1}: {CV_LABEL[n]}"
        prec = n in ONE_V_OCT
        if prec:
            P += [Part(f"R{10+4*i}", "R100k_01", {"1": f"CV_{n}", "2": f"RIN_{n}"}, blk, "R_in, part 1 (0.1%)"),
                  Part(f"R{13+4*i}", "R20k_01", {"1": f"RIN_{n}", "2": f"INV_{n}"}, blk, "R_in, part 2 (0.1%)")]
        else:
            P.append(Part(f"R{10+4*i}", "R120k", {"1": f"CV_{n}", "2": f"INV_{n}"}, blk, "R_in"))
        P += [Part(f"R{11+4*i}", "R20k_01" if prec else "R20k", {"1": f"INV_{n}", "2": f"ADC_{n}"}, blk, "R_f"),
              Part(f"R{12+4*i}", "R120k_25" if prec else "R120k", {"1": f"INV_{n}", "2": "-10V_REF"}, blk,
                   "offset (25 ppm/K on the 1V/OCT inputs)" if prec else "offset"),
              Part(f"C{10+i}", "C1n", {"1": f"INV_{n}", "2": f"ADC_{n}"}, blk, "8 kHz")]
        P.append(Part(f"{u}.{unit+1}", None, {out: f"ADC_{n}", inv: f"INV_{n}", plus: "GND"}, blk))
    for u in ("U1", "U2"):
        P.append(Part(f"{u}.5", None, {"4": "+3V3_A", "11": "GND"}, "CV op-amp supply"))
    P += [Part("C20", "C100n", {"1": "+3V3_A", "2": "GND"}, "CV op-amp supply", "U1"),
          Part("C21", "C100n", {"1": "+3V3_A", "2": "GND"}, "CV op-amp supply", "U2")]
    # audio: in x0.1 (Dev Kit values), out x5.1 (d, 2026-10-06: 51k // 47p; the Dev Kit's x10 clips above -3 dBFS)
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
              Part(f"R{61 if side=='L' else 65}", "R51k", {"1": f"AOUT_{side}_INV", "2": f"AOUT_{side}_OUT"}, b),
              Part(f"C{60 if side=='L' else 62}", "C47p", {"1": f"AOUT_{side}_INV", "2": f"AOUT_{side}_OUT"}, b),
              Part(f"R{62 if side=='L' else 66}", "R100", {"1": f"AOUT_{side}_OUT", "2": f"OUT_{side}"}, b),
              Part(f"U4.{1 if side=='L' else 2}", None, {o: f"AOUT_{side}_OUT", m: f"AOUT_{side}_INV", p: "GND"}, b)]
    for u in ("U3", "U4"):
        P.append(Part(f"{u}.3", None, {"8": "+12V", "4": "-12V"}, "Audio op-amp supply"))
    P += [Part("C70", "C100n", {"1": "+12V", "2": "GND"}, "Audio op-amp supply", "U3 V+"),
          Part("C71", "C100n", {"1": "GND", "2": "-12V"}, "Audio op-amp supply", "U3 V-"),
          Part("C72", "C100n", {"1": "+12V", "2": "GND"}, "Audio op-amp supply", "U4 V+"),
          Part("C73", "C100n", {"1": "GND", "2": "-12V"}, "Audio op-amp supply", "U4 V-")]
    P.append(Part("J14", "EXP", {"1": "GND", "2": "USB_DM", "3": "GND", "4": "USB_DP", "5": "MIDI_TX", "6": "MIDI_RX",
                                "7": "+3V3_D", "8": "GND"}, "Expansion header",
                  "to the 2HP USB-C / MIDI expander (ribbon: pin = wire)"))
    # pot multiplexer: 8 wipers -> POT_MUX; S0/S1/S2 = MUX_A/B/C
    mux = {"3": "POT_MUX", "6": "GND", "7": "GND", "8": "GND", "16": "+3V3_A", "11": "MUX_A", "10": "MUX_B", "9": "MUX_C"}
    for k, pin in (pm.MUX_PIN if pm else {}).items():
        mux[pin] = f"POT_{k}"
    P.append(Part("U6", "MUX", mux, "Pot multiplexer", "8 pot wipers -> POT_MUX", board="control"))
    P.append(Part("C80", "C100n_T", {"1": "+3V3_A", "2": "GND"}, "Pot multiplexer", "U6 decoupling", board="control"))
    P.append(Part("R70", "R1k", {"1": "LED_CLIP", "2": "LED_A"}, "Clip LED", "LED current ~1.4 mA at 3.3 V"))
    # optional microSD socket (as the Dev Kit): SDMMC1 on Seed3 pins 2-7, 47k pull-ups on CMD and D0-D3, 3V3_D
    P.append(Part("J15", "SDCARD", {"1": "SD_D2", "2": "SD_D3", "3": "SD_CMD", "4": "+3V3_D", "5": "SD_CK", "6": "GND",
                                    "7": "SD_D0", "8": "SD_D1", "CD1": None, "MP1": "GND", "MP2": "GND", "MP3": "GND",
                                    "MP4": "GND"}, "microSD (optional)", "DNP: fit per build", dnp=True))
    for ref, net in (("R100", "SD_D2"), ("R101", "SD_D3"), ("R102", "SD_CMD"), ("R103", "SD_D0"), ("R104", "SD_D1")):
        P.append(Part(ref, "R47k", {"1": net, "2": "+3V3_D"}, "microSD (optional)", "pull-up"))
    P.append(Part("C100", "C100n", {"1": "+3V3_D", "2": "GND"}, "microSD (optional)", "J15 decoupling"))
    # CV LEDs (d, 2026-10-06): each jack's CV drives a 2-lead red/green LED by the jack, green for +, red for
    # -, with the LED inside an LM324's feedback loop (as Mutable Instruments' Shades): CV -> 10k -> + input (1M to
    # GND), the LED from the output to the - input, 1.5k from the - input to
    # GND. LED current = CV / 1.5k (0.7 mA at 1 V, 3.3 mA at 5 V), no dead zone, levelling off near 5.5-6 mA from about
    # +/-8.5 V; the + input loads nothing. 10k: input protection; 1M: an undriven cable reads 0 V, LED dark.
    for i, n in enumerate(CV_NAMES):
        u, unit = pm.LED_UNIT[n] if pm else (("U7", "U8")[i // 4], i % 4 + 1)
        out, inv, plus = SECTION_PINS[unit - 1]
        blk = f"CV LED {i+1}: {CV_LABEL[n]}"
        P.append(Part(f"R{80+i}", "R10k_T", {"1": f"CV_{n}", "2": f"CVB_{n}"}, blk, "input protection", board="control"))
        P.append(Part(f"R{90+i}", "R1M_T", {"1": f"CVB_{n}", "2": "GND"}, blk, "holds an undriven cable at 0 V",
                      board="control"))
        P.append(Part(f"{u}.{unit}", None, {out: f"LEDDRV_{n}", inv: f"LEDFB_{n}", plus: f"CVB_{n}"}, blk,
                      board="control"))
        P.append(Part(f"R{71+i}", "R1k5_T", {"1": f"LEDFB_{n}", "2": "GND"}, blk, "sets the LED current: CV / 1.5k",
                      board="control"))
    for u in ("U7", "U8"):
        P.append(Part(f"{u}.5", None, {"4": "+12V", "11": "-12V"}, "CV LED driver supply", board="control"))
    P += [Part("C81", "C100n_T", {"1": "+12V", "2": "GND"}, "CV LED driver supply", "U7 V+", board="control"),
          Part("C82", "C100n_T", {"1": "GND", "2": "-12V"}, "CV LED driver supply", "U7 V-", board="control"),
          Part("C83", "C100n_T", {"1": "+12V", "2": "GND"}, "CV LED driver supply", "U8 V+", board="control"),
          Part("C84", "C100n_T", {"1": "GND", "2": "-12V"}, "CV LED driver supply", "U8 V-", board="control")]
    P += [_flag("#FLG1", "+12V"), _flag("#FLG2", "-12V"), _flag("#FLG3", "GND"), _flag("#FLG4", "VIN"),
          _flag("#FLG5", "P12_IN"), _flag("#FLG6", "N12_IN")]
    # the control board's supplies arrive through the headers: flagged there for ERC
    P += [_flag("#FLG11", "+12V", board="control"), _flag("#FLG12", "-12V", board="control"),
          _flag("#FLG13", "+3V3_A", board="control"), _flag("#FLG14", "GND", board="control")]
    # board-to-board headers (rev beta): JA* female on the control board's back, JB* male on the main board's front;
    # pin k of JAn meets pin k of JBn
    if pm:
        for h, sigs in pm.HEADER_PINS.items():
            pins = {str(k + 1): s for k, s in enumerate(sigs)}
            P.append(Part(f"JA{h}", f"HDR_F{len(sigs)}", pins, "Board connector",
                          "to the main board (female, on the control board's back)", board="control"))
            P.append(Part(f"JB{h}", f"HDR_M{len(sigs)}", dict(pins), "Board connector",
                          "to the control board (male, on the main board's front)"))
    # attach op-amp units to their package part
    return _merge_units(P, {"U1": "LMV324", "U2": "LMV324", "U3": "TL072", "U4": "TL072", "U7": "LM324", "U8": "LM324"})


def _merge_units(P, kinds):
    """Op-amp units are listed as 'U1.n'; fold them into one Part per package, remembering each unit's block."""
    out, pk = [], {}
    for p in P:
        if "." in p.ref and p.kind is None:
            ref, unit = p.ref.split(".")
            if ref not in pk:
                pk[ref] = Part(ref, kinds[ref], {}, p.block, board=p.board)
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
