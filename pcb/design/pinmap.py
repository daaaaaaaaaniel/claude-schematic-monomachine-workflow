"""Pin assignments and placement, written by design/floorplan.py: edit floorplan.py, not this file.

Used by machine_filter.py (SKiDL) and design/boards.py. Units: 1 = A (pins 1-3), 2 = B (5-7), 3 = C (8-10),
4 = D (12-14). Positions: panel frame seen from the front, mm: (x, y, rotation) of the footprint origin
as pcbnew's SetPosition takes it (KiCad = panel + (100, 50)); back-side parts are then flipped left-right."""

HEADER_PINS = {'1': ['GND', 'IN_L', 'IN_R', 'GND', 'OUT_R', 'OUT_L', 'GND', 'POT_VOL', 'GND', 'LED_A', 'GND', '+12V', 'GND', '-12V', 'GND'], '2': ['GND', 'CV_BASE', 'CV_WIDTH', 'GND', 'CV_HPRES', 'CV_LPRES', 'GND', 'CV_EQG', 'CV_EQF', 'GND', 'CV_SRR', 'CV_DIST', 'GND'], '3': ['GND', 'POT_MUX', 'GND', 'MUX_C', 'MUX_B', 'GND', 'MUX_A', 'GND', '+3V3_A', 'GND']}
HEADER_POS = {'1': (21.95, 69.205, 180, 180), '2': (41.635, 66.03, 0, 0), '3': (21.95, 84.445, 0, 0)}   # pin 1 x, y; rotation of JBn (main, front) and of JAn (control, back)
SEED = (14.565, 110.9, 180)   # main board, back; rotation 0 = USB end up, 180 = down
# 2026-10-06 (d): WIDTH and EQF swapped by hand so each CV quad carries one 1V/OCT channel (BASE on U2, WIDTH on U1)
ADC_UNIT = {"BASE": ("U2", 1), "WIDTH": ("U1", 4), "HPRES": ("U2", 2), "LPRES": ("U2", 3), "EQF": ("U2", 4), "EQG": ("U1", 1), "DIST": ("U1", 3), "SRR": ("U1", 2)}
LED_UNIT = {"BASE": ("U7", 4), "WIDTH": ("U7", 1), "HPRES": ("U7", 3), "LPRES": ("U7", 2), "EQF": ("U8", 4), "EQG": ("U8", 1), "DIST": ("U8", 3), "SRR": ("U8", 2)}
SEED_ADC = {"ADC_WIDTH": "22", "ADC_BASE": "23", "POT_VOL": "24", "ADC_LPRES": "25", "ADC_HPRES": "26", "ADC_EQF": "27", "ADC_EQG": "28", "ADC_DIST": "30", "ADC_SRR": "31", "POT_MUX": "32"}
MUX_PIN = {"BASE": "15", "WIDTH": "1", "HPRES": "14", "LPRES": "2", "EQF": "13", "EQG": "4", "DIST": "12", "SRR": "5"}
MUX_SELECT = ["EQF", "HPRES", "BASE", "DIST", "WIDTH", "SRR", "LPRES", "EQG"]   # firmware: select 0..7 -> pot
MIDI = {"MIDI_TX": "14", "MIDI_RX": "15"}   # D13 / D14 = USART1 TX / RX (PB6 / PB7), libDaisy's default
CONTROL_PLACEMENT = {'U6': (22.85, 76.95, 0), 'U7': (56.94, 72.62, 0), 'U8': (56.94, 96.32, 0)}
MAIN_PLACEMENT = {'U3': (9.6, 71.5, 90), 'U4': (9.6, 63.3, 90), 'U1': (35.74, 82.97, 0), 'U2': (35.74, 70.27, 0), 'U5': (33.8, 63.25, 90), 'J13': (8.0, 27.95, 0), 'D10': (14.5, 27.9, 90), 'D11': (14.5, 33.3, 90), 'C2': (19.6, 27.25, 90), 'C4': (6.75, 42.9, 0), 'C5': (35.6, 108.35, 90), 'C6': (35.6, 98.25, 90), 'J14': (42.75, 104.4, 0), 'J15': (48.05, 89.67, 90)}
