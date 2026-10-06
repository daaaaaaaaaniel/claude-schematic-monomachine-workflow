"""Placement groups (d, 2026-10-06): every part belongs to one function group, around one primary part.

A group's secondary parts are the ones that must sit close to its primary (decoupling, the parts at an op-amp
section's - input, the protection chain at the power header). The other small parts join the group whose primary
they connect to; within a function, groups are balanced (each CV quad carries four channels and one 1V/OCT input).

ORDER is the placement order agreed with d: the most consequential primary first. The control board's panel parts
(jacks, pots, LEDs) are fixed by the panel and are not a placement decision.
Standoffs are board-only (no schematic symbol): pairs of M3 holes at the same panel position on both boards.
"""

# CV channel -> its parts at the op-amp section (R_in [, series R behind it], R_f, C_f, offset R)
CV_PARTS = {
    "BASE": ["R10", "R13", "R11", "C10", "R12"], "WIDTH": ["R14", "R17", "R15", "C11", "R16"],
    "HPRES": ["R18", "R19", "C12", "R20"], "LPRES": ["R22", "R23", "C13", "R24"],
    "EQF": ["R26", "R27", "C14", "R28"], "EQG": ["R30", "R31", "C15", "R32"],
    "DIST": ["R34", "R35", "C16", "R36"], "SRR": ["R38", "R39", "C17", "R40"],
}

MAIN = {   # name: (primary, [secondary and other parts])
    "seed3": ("A1", ["R70", "C6", "R2", "C5", "R1"]),           # Seed3 supply filter ends at pin 39 (C6 at the pin)
    "cv_u2": ("U2", ["C21"] + sum((CV_PARTS[n] for n in ("BASE", "HPRES", "LPRES", "EQF")), [])),
    "cv_u1": ("U1", ["C20"] + sum((CV_PARTS[n] for n in ("WIDTH", "EQG", "DIST", "SRR")), [])),
    "audio_in": ("U3", ["C70", "C71", "R50", "R51", "C50", "R52", "R54", "R55", "C52", "R56"]),
    "audio_out": ("U4", ["C72", "C73", "R60", "R61", "C60", "R62", "R64", "R65", "C62", "R66"]),
    "ref_u5": ("U5", ["C7", "R3"]),
    "power": ("J13", ["FB1", "D10", "C1", "C2", "FB2", "D11", "C3", "C4"]),
    "microsd": ("J15", ["C100", "R100", "R101", "R102", "R103", "R104"]),
    "expansion": ("J14", []),
    "headers": ("JB1", ["JB2", "JB3"]),
}
CONTROL = {
    "mux_u6": ("U6", ["C80"]),
    "leds_u7": ("U7", ["C81", "C82", "R71", "R72", "R73", "R74", "R80", "R81", "R82", "R83", "R90", "R91", "R92", "R93"]),
    "leds_u8": ("U8", ["C83", "C84", "R75", "R76", "R77", "R78", "R84", "R85", "R86", "R87", "R94", "R95", "R96", "R97"]),
    "headers": ("JA1", ["JA2", "JA3"]),
    "panel": ("J1", ["J2", "J3", "J4", "J5", "J6", "J7", "J8", "J9", "J10", "J11", "J12", "D1", "D2", "D3", "D4",
                     "D5", "D6", "D7", "D8", "D9", "RV1", "RV2", "RV3", "RV4", "RV5", "RV6", "RV7", "RV8", "RV9"]),
}
STANDOFFS = {"main": ["H1", "H2", "H3", "H4"], "control": ["H11", "H12", "H13", "H14"]}   # optional (d)
STANDOFF_FP = "MountingHole:MountingHole_3.2mm_M3"

# Secondary parts (d, 2026-10-06): placed in the same step as their primary because they must sit close to it.
# Everything else in a group is a minor part, placed only after every primary and secondary is on the board. The
# one exception: when a primary's critical trace passes through a minor part, that one part is placed (provisionally)
# so the trace can be drawn, and the report says so.
SECONDARY = {
    "seed3": ["C6"],                                        # at VIN (pin 39)
    "cv_u2": ["C21"], "cv_u1": ["C20"],                     # decoupling
    "audio_in": ["C70", "C71"], "audio_out": ["C72", "C73"],
    "ref_u5": ["C7"],
    "power": ["FB1", "D10", "C1", "C2", "FB2", "D11", "C3", "C4"],   # protection and bulk, in chain order
    "microsd": ["C100"], "expansion": [], "headers": [],
    "mux_u6": ["C80"], "leds_u7": ["C81", "C82"], "leds_u8": ["C83", "C84"],
}

# Placement order (d agreed, 2026-10-06): 1 Seed3; 2 U2 then U1; 3 U3, U4; 4 U5; 5 J13; 6 J15, J14; 7 headers;
# 8 standoffs (optional)
ORDER = ["seed3", "cv_u2", "cv_u1", "audio_in", "audio_out", "ref_u5", "power", "microsd", "expansion", "headers",
         "standoffs"]
