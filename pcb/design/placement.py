"""Placement decisions, step by step (d, 2026-10-06): the record of what has been put on the boards, so the layout
can be rebuilt or reviewed. Panel frame (boards.py: mm, seen from the front panel); KiCad (x, y) = panel (x, y) +
the board's offset (pcb_skeleton.py). Footprint origin, rotation in degrees as KiCad shows it, side "front" or
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
]
