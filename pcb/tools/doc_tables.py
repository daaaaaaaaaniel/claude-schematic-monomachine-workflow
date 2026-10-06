"""Print the pinmap-derived tables used in the docs, so they can be pasted after a floorplan change instead of being
edited by hand. Run from pcb/: python3 tools/doc_tables.py

  1. ADC pins (docs/firmware-changes.md, section 1)
  2. CV ADC stages (docs/placement-guide.md, section 3)
  3. Board-to-board headers (docs/placement-guide.md, section 7)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "design"))
sys.path.insert(0, os.path.join(HERE, "..", "reference"))
import boards  # noqa: E402
import pinmap as PM  # noqa: E402

SECTION = {1: ("A", "1", "2", "3"), 2: ("B", "7", "6", "5"), 3: ("C", "8", "9", "10"), 4: ("D", "14", "13", "12")}
DAISY = {str(22 + k): f"A{k}" for k in range(11)}
DAISY["35"] = "A11"
LABEL = {"BASE": "CV 1 BASE (1V/OCT)", "WIDTH": "CV 2 WIDTH (1V/OCT)", "HPRES": "CV 3 HP RES", "LPRES": "CV 4 LP RES",
         "EQF": "CV 5 EQ FREQ", "EQG": "CV 6 EQ GAIN", "DIST": "CV 7 DIST", "SRR": "CV 8 SMPL RATE",
         "POT_VOL": "POT_VOL (VOLUME pot)", "POT_MUX": "POT_MUX (pot multiplexer)"}


def alpha_adc():
    import boards_rev_alpha as a
    p = {x.ref: x for x in a.board()}["A1"]
    return {k: v for k, v in p.pins.items() if v and 22 <= int(k) <= 35}


def adc_table():
    al = alpha_adc()
    beta = {pin: sig for sig, pin in PM.SEED_ADC.items()}
    name = lambda sig: LABEL.get(sig.replace("ADC_", ""), sig) if sig else "—"
    print("| Seed3 pin | Daisy name | rev alpha | **rev beta** |\n|---|---|---|---|")
    for pin in sorted(set(al) | set(beta) | set(DAISY), key=int):
        print(f"| {pin} | {DAISY[pin]} | {name(al.get(pin))} | **{name(beta.get(pin))}** |")


def cv_table():
    hdr = {s: (h, k + 1) for h, pins in PM.HEADER_PINS.items() for k, s in enumerate(pins)}
    print("| CV | Section: − / out / + | R_in at − pin | R_f | C_f | Offset | From header pin | To Seed3 pin |")
    print("|---|---|---|---|---|---|---|---|")
    for i, n in enumerate(boards.CV_NAMES):
        u, unit = PM.ADC_UNIT[n]
        L, o, m, p = SECTION[unit]
        rin = f"R{13 + 4 * i} (R{10 + 4 * i} behind it)" if n in boards.ONE_V_OCT else f"R{10 + 4 * i}"
        h, k = hdr[f"CV_{n}"]
        print(f"| {LABEL[n][3:]} | {u}{L}: {m} / {o} / {p} | {rin} | R{11 + 4 * i} | C{10 + i} | R{12 + 4 * i} | "
              f"JB{h}.{k} | {PM.SEED_ADC['ADC_' + n]} |")


def header_table():
    orient = {0: "vertical, pin 1 at the top", 90: "horizontal, pin 1 at the left", 180: "vertical, pin 1 at the bottom",
              270: "horizontal, pin 1 at the right"}
    print("| Header | Pins | Pin 1 (panel frame, mm) | Orientation (main side) | Pin order |\n|---|---|---|---|---|")
    for h in sorted(PM.HEADER_PINS):
        x, y, rot, _ = PM.HEADER_POS[h]
        print(f"| JA{h} / JB{h} | {len(PM.HEADER_PINS[h])} | ({x}, {y}) | {orient[rot]} | "
              f"{', '.join(PM.HEADER_PINS[h])} |")


if __name__ == "__main__":
    for title, f in (("ADC pins", adc_table), ("CV ADC stages", cv_table), ("Headers", header_table)):
        print(f"## {title}\n")
        f()
        print()
