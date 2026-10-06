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
]
