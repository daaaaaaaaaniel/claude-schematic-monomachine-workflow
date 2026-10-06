"""Placement decisions, step by step (d, 2026-10-06): the record of what has been put on the boards, so the layout
can be rebuilt or reviewed. Panel frame (boards.py: mm, seen from the front panel); KiCad (x, y) = panel (x, y) +
the board's offset (pcb_skeleton.py). Footprint origin, rotation in degrees as KiCad shows it on the part's final side
(konnect_place.py flips first, then sets the rotation), side "front" or
"back". KiCad flips a part top-to-bottom, so a back-side rotation differs by 180 from floorplan.py's (left-right).
tools/konnect_place.py applies every step up to the one asked for and checks the result.

A "general area" placement: parts sit in their group's zone (design/zone_sketch.py), not at a final spot.
"""

OFFSET = {"main": (180.0, 50.0), "control": (100.0, 50.0)}

STEPS = [
    # 1. Seed3 (d: "place the Seed3"): USB end down, USB socket 26 mm inside the control board's edge (A2-C2
    #    agree). Its group: the supply filter R1-C5-R2-C6 ending at VIN (pin 39, bottom of the right row), and R70
    #    at pin 12 (LED_A). Critical trace: VIN pin 39 -> C6, the filter's last capacitor, at the pin.
    {"name": "seed3",
     "parts": {"A1": ("main", 33.615, 89.49, 0, "back"),   # KiCad rotation after its own (top-bottom) flip
               "C6": ("main", 57.5, 91.0, 0, "back"),
               "R2": ("main", 57.5, 97.0, 0, "back"),
               "C5": ("main", 57.5, 102.5, 0, "back"),
               "R1": ("main", 64.5, 108.5, 0, "back"),
               "R70": ("main", 28.5, 61.5, 90, "back")},
     "check_pads": {("A1", "1"): (33.615, 89.49), ("A1", "20"): (33.615, 41.23), ("A1", "22"): (48.855, 43.77),
                    ("A1", "39"): (48.855, 86.95)},
     "traces": [("A1", "39", "C6", None, 0.5, "B.Cu")]},   # C6 pad: the one on VIN,
    # 2. U2, CV 1-4 group (d: "place the second primary part"). Back side, rotation 0: after KiCad's top-bottom
    #    flip, pins 1-7 run up the left side (facing the Seed3's ADC pins), 8-14 down the right. Pin 1 (BASE out)
    #    level with Seed3 pin 23 (ADC_BASE), so the critical trace is a straight 3 mm line. Each channel's parts sit
    #    by its section: A (BASE, pins 1-3) below, B (HP RES, 5-7) above, C (LP RES, 8-10) right-upper,
    #    D (EQ FREQ, 12-14) right-lower; C21 (decoupling) between them. The other three channels' ADC pins are
    #    re-matched once U1 is placed (pin map follows the layout).
    {"name": "cv_u2",
     "parts": {"U2": ("main", 54.6, 42.493, 0, "back"),
               "R10": ("main", 51.5, 50.0, 90, "back"), "R13": ("main", 53.3, 50.0, 90, "back"),
               "R11": ("main", 55.1, 50.0, 90, "back"), "C10": ("main", 56.9, 50.0, 90, "back"),
               "R12": ("main", 58.7, 50.0, 90, "back"),
               "R18": ("main", 51.5, 35.0, 90, "back"), "R19": ("main", 53.3, 35.0, 90, "back"),
               "C12": ("main", 55.1, 35.0, 90, "back"), "R20": ("main", 56.9, 35.0, 90, "back"),
               "R22": ("main", 60.0, 39.5, 90, "back"), "R23": ("main", 61.8, 39.5, 90, "back"),
               "C13": ("main", 63.6, 39.5, 90, "back"), "R24": ("main", 65.4, 39.5, 90, "back"),
               "R26": ("main", 60.0, 45.5, 90, "back"), "R27": ("main", 61.8, 45.5, 90, "back"),
               "C14": ("main", 63.6, 45.5, 90, "back"), "R28": ("main", 65.4, 45.5, 90, "back"),
               "C21": ("main", 61.0, 42.5, 0, "back")},
     "check_pads": {("U2", "1"): (51.89, 46.31), ("U2", "7"): (51.89, 38.69), ("U2", "14"): (57.29, 46.31)},
     "traces": [("U2", "1", "A1", "23", 0.25, "B.Cu")]},
    # 3. U1, CV 5-8 group (d: "go on to the next component"): the same column as U2, below it; rotation 0 on the
    #    back (pins 1-7 up the left side, facing the ADC pins). Pin 1 level with Seed3 pin 29 (A7, until now
    #    unused). Parts: section A's below the chip, then B's; C's (pins 8-10) right-upper, D's (12-14) right-lower;
    #    C20 between them. Which channel uses which section and ADC pin is re-matched after this step
    #    (tools/rematch_adc.py); the critical trace (the WIDTH output -> its ADC pin) is drawn after that.
    {"name": "cv_u1",
     "parts": {"U1": ("main", 54.6, 57.81, 0, "back"),
               "R14": ("main", 51.5, 66.0, 90, "back"), "R17": ("main", 53.3, 66.0, 90, "back"),
               "R15": ("main", 55.1, 66.0, 90, "back"), "C11": ("main", 56.9, 66.0, 90, "back"),
               "R16": ("main", 58.7, 66.0, 90, "back"),
               "R30": ("main", 51.5, 70.0, 90, "back"), "R31": ("main", 53.3, 70.0, 90, "back"),
               "C15": ("main", 55.1, 70.0, 90, "back"), "R32": ("main", 56.9, 70.0, 90, "back"),
               "R34": ("main", 60.0, 54.8, 90, "back"), "R35": ("main", 61.8, 54.8, 90, "back"),
               "C16": ("main", 63.6, 54.8, 90, "back"), "R36": ("main", 65.4, 54.8, 90, "back"),
               "R38": ("main", 60.0, 60.8, 90, "back"), "R39": ("main", 61.8, 60.8, 90, "back"),
               "C17": ("main", 63.6, 60.8, 90, "back"), "R40": ("main", 65.4, 60.8, 90, "back"),
               "C20": ("main", 61.0, 57.8, 0, "back")},
     "check_pads": {("U1", "1"): (51.89, 61.627), ("U1", "7"): (51.89, 54.007), ("U1", "14"): (57.29, 61.627)},
     # after the re-match (d: keep it), WIDTH is on U1 section A and Seed3 pin 29: a straight 3 mm trace
     "traces": [("U1", "1", "A1", "29", 0.25, "B.Cu")]},
    # 4. U3 (audio in) and U4 (audio out), d: "do both U3 and U4, and their critical traces". Left of the Seed3,
    #    by the codec pins (16/17 = CODEC_IN_L/R, 18/19 = CODEC_OUT_L/R). Back side, rotation 0 (pins 1-4 up the
    #    left, 8-5 up the right). U3 below U4. The four codec-side resistors stand in two columns between the
    #    op-amps and the Seed3's left row (2.54 mm pin pitch is less than a resistor's 3.25 mm courtyard), each with
    #    its codec pad level with its Seed3 pin, so every codec trace is a straight horizontal line that passes no
    #    other pad: R52 (pin 16) and R60 (18) nearest the Seed3, R56 (17) and R64 (19) behind them. On the back at
    #    rotation 90, pad 2 is the upper one. (A first try with one column made L-bend traces that crossed the
    #    resistors' other pads: DRC shorts; deleted.)
    #    Critical traces: Seed3 pin 16 -> R52 (codec input), Seed3 pin 18 -> R60 (codec output).
    {"name": "audio",
     "parts": {"U3": ("main", 23.5, 49.5, 0, "back"), "U4": ("main", 23.5, 41.5, 0, "back"),
               "R52": ("main", 30.6, 52.24, 90, "back"), "R60": ("main", 30.6, 45.46, 90, "back"),
               "R56": ("main", 28.4, 49.70, 90, "back"), "R64": ("main", 28.4, 42.92, 90, "back"),
               "R50": ("main", 13.0, 50.0, 90, "back"), "R51": ("main", 14.8, 50.0, 90, "back"),
               "C50": ("main", 16.6, 50.0, 90, "back"),
               "R54": ("main", 20.0, 55.0, 90, "back"), "R55": ("main", 21.8, 55.0, 90, "back"),
               "C52": ("main", 23.6, 55.0, 90, "back"), "C70": ("main", 25.4, 55.0, 90, "back"),
               "C71": ("main", 14.0, 46.2, 0, "back"),
               "R61": ("main", 13.0, 41.5, 90, "back"), "C60": ("main", 14.8, 41.5, 90, "back"),
               "R62": ("main", 16.6, 41.5, 90, "back"),
               "C73": ("main", 18.2, 35.5, 90, "back"), "R65": ("main", 20.0, 35.5, 90, "back"),
               "C62": ("main", 21.8, 35.5, 90, "back"), "R66": ("main", 23.6, 35.5, 90, "back"),
               "C72": ("main", 25.4, 35.5, 90, "back")},
     "check_pads": {("U3", "1"): (20.8, 51.405), ("U3", "7"): (26.2, 50.135), ("U4", "1"): (20.8, 43.405),
                    ("U4", "6"): (26.2, 40.865), ("R52", "2"): (30.6, 51.39), ("R60", "1"): (30.6, 46.31)},
     "traces": [("A1", "16", "R52", "2", 0.25, "B.Cu"), ("A1", "18", "R60", "1", 0.25, "B.Cu")]},
    # 5. U5 (-10 V reference), d: one gesture. Moved off the zone sketch's spot under the Seed3: from there all eight
    #    offset lines would have to pass between socket pins (the pocket); at the right edge it sits beside the CV
    #    groups that use it. Its group (C7, R3) comes as a block. Critical trace: to R28 (EQ FREQ offset), the
    #    nearest offset resistor (already on the board).
    #    (A straight drag of the staged cluster put C7 and R3 past the board's right edge; repacked as a column.)
    {"name": "ref_u5", "pack": "ref_u5", "at": ("main", 66.6, 47.0, "back"), "width": 3.6,
     "traces": [("L", "U5", "R28")]},
    # 6. J13, J15, J14 in one go (d: finish the first round quickly). Each group as one block packed to fit its
    #    corner; minor parts ride along unarranged.
    #    J13 power entry: bottom left, header turned sideways (rot 90) so the block fits under the microSD.
    #    Critical trace: J13 -> FB1 (the +12 V chain's first part).
    {"name": "power", "pack": "power", "at": ("main", 3.0, 86.0, "back"), "width": 31.0, "rot": {"J13": 90},
     "traces": [("L", "J13", "FB1")]},
    #    J15 microSD: left middle, beside the SD pins (2-7). Critical trace: one SD line, Seed3 -> J15, as a dogleg
    #    passing beside the socket row.
    {"name": "microsd", "pack": "microsd", "at": ("main", 3.0, 63.0, "back"), "width": 28.0,
     "traces": [("dogleg", "A1", "J15", 32.2, "SD_CK")]},
    #    J14 expansion: bottom right, beside the USB pins (36/37), turned sideways. Critical trace: USB, Seed3 -> J14.
    {"name": "expansion", "pack": "expansion", "at": ("main", 53.0, 76.0, "back"), "width": 16.0, "rot": {"J14": 90},
     "traces": [("dogleg", "A1", "J14", 50.3, "USB_D")]},
    # Feedback round (d): "rotate the SD card 90 degrees CCW" (as seen in the editor's panel-side view). J15 turned in
    #    place; its pad row now faces the Seed3's SD pins.
    {"name": "j15_rot", "parts": {"J15": ("main", 11.715, 67.52, 90, "back")}},
    # Op-amp -> Seed3 traces (d: "draw all the traces that go directly from an opamp on the main board to a daisy
    #    pin"): the CV outputs to their ADC pins (BASE and WIDTH were drawn earlier). Outputs on the op-amps' left
    #    (Seed3) side stay on the back; those on the far side drop through a via 1.5 mm right of the pin and run on
    #    the front, where only the Seed3's through-hole socket pins are, straight to the pin.
    {"name": "opamp_adc", "board": "main", "routes": [
        ("ADC_HPRES", [("B.Cu", [(51.89, 38.69), (50.4, 38.69), (50.4, 43.77), (48.855, 43.77)])]),
        ("ADC_EQG", [("B.Cu", [(51.89, 54.007), (48.855, 53.93)])]),
        ("ADC_LPRES", [("B.Cu", [(57.29, 38.69), (58.8, 38.69)]), ("F.Cu", [(58.8, 38.69), (48.855, 48.85)])]),
        ("ADC_EQF", [("B.Cu", [(57.29, 46.31), (58.8, 46.31)]), ("F.Cu", [(58.8, 46.31), (48.855, 51.39)])]),
        ("ADC_DIST", [("B.Cu", [(57.29, 54.007), (58.8, 54.007)]), ("F.Cu", [(58.8, 54.007), (48.855, 56.47)])]),
        ("ADC_SRR", [("B.Cu", [(57.29, 61.627), (58.8, 61.627)]), ("F.Cu", [(58.8, 61.627), (48.855, 64.09)])]),
    ]},
    # Control board panel parts (d: "next, do this"): jacks, pots and LEDs at their fixed panel positions and the
    #    floorplan's rotations (boards.py, floorplan.front_rotation), on the control board's front. No decisions.
    {"name": "panel", "parts": {
               "J1": ("control", 50.7, 32.8, 0, "front"),
               "J2": ("control", 63.2, 32.8, 0, "front"),
               "J3": ("control", 50.7, 19.8, 180, "front"),
               "J4": ("control", 63.2, 19.8, 180, "front"),
               "J5": ("control", 50.7, 52.2, 90, "front"),
               "J6": ("control", 63.2, 52.2, 90, "front"),
               "J7": ("control", 50.7, 71.733, 90, "front"),
               "J8": ("control", 63.2, 71.733, 90, "front"),
               "J9": ("control", 50.7, 91.267, 90, "front"),
               "J10": ("control", 63.2, 91.267, 90, "front"),
               "J11": ("control", 50.7, 110.8, 90, "front"),
               "J12": ("control", 63.2, 110.8, 90, "front"),
               "D1": ("control", 20.694, 14.0, 0, "front"),
               "D2": ("control", 48.2, 45.4, 90, "front"),
               "D3": ("control", 60.7, 45.4, 90, "front"),
               "D4": ("control", 48.2, 64.933, 90, "front"),
               "D5": ("control", 60.7, 64.933, 90, "front"),
               "D6": ("control", 48.2, 84.467, 90, "front"),
               "D7": ("control", 60.7, 84.467, 90, "front"),
               "D8": ("control", 48.2, 104.0, 90, "front"),
               "D9": ("control", 60.7, 104.0, 90, "front"),
               "RV1": ("control", 12.9, 18.5, 0, "front"),
               "RV2": ("control", 12.9, 41.5, 0, "front"),
               "RV3": ("control", 32.9, 41.5, 0, "front"),
               "RV4": ("control", 12.9, 64.5, 0, "front"),
               "RV5": ("control", 32.9, 64.5, 0, "front"),
               "RV6": ("control", 12.9, 87.5, 0, "front"),
               "RV7": ("control", 32.9, 87.5, 0, "front"),
               "RV8": ("control", 12.9, 110.5, 180, "front"),
               "RV9": ("control", 32.9, 110.5, 180, "front")}},
]
