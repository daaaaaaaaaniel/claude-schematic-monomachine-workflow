"""Pin assignments and placement, written by design/floorplan.py: edit floorplan.py, not this file.

Used by machine_filter.py (SKiDL) and design/boards.py. Units: 1 = A (pins 1-3), 2 = B (5-7), 3 = C (8-10),
4 = D (12-14). Positions: panel frame seen from the front, mm: (x, y, rotation) of the footprint origin
as pcbnew's SetPosition takes it (KiCad = panel + (100, 50)); back-side parts are then flipped left-right."""

HEADER_PINS = {'1': ['GND', 'OUT_L', 'OUT_R', 'GND', 'IN_L', 'IN_R', 'GND', '-12V', 'GND', 'CV_BASE', 'CV_WIDTH', 'GND', 'CV_LPRES', 'CV_HPRES', 'GND', 'CV_EQG', 'CV_EQF', 'GND', 'CV_SRR', 'CV_DIST', 'GND'], '2': ['GND', '+12V', 'GND', '+3V3_A', 'GND', 'POT_VOL', 'POT_MUX', 'GND'], '3': ['GND', 'LED_A', 'MUX_C', 'GND', 'MUX_B', 'MUX_A', 'GND']}
HEADER_POS = {'1': (41.635, 33.645, 0, 0), '2': (23.855, 43.805, 0, 0), '3': (21.95, 84.445, 0, 0)}   # pin 1 x, y; rotation of JBn (main, front) and of JAn (control, back)
SEED = (14.565, 110.9, 180)   # main board, back; rotation 0 = USB end up, 180 = down
ADC_UNIT = {"BASE": ("U2", 4), "WIDTH": ("U2", 3), "HPRES": ("U2", 2), "LPRES": ("U2", 1), "EQF": ("U1", 1), "EQG": ("U1", 4), "DIST": ("U1", 2), "SRR": ("U1", 3)}
LED_UNIT = {"BASE": ("U7", 4), "WIDTH": ("U7", 1), "HPRES": ("U7", 3), "LPRES": ("U7", 2), "EQF": ("U8", 4), "EQG": ("U8", 1), "DIST": ("U8", 3), "SRR": ("U8", 2)}
SEED_ADC = {"POT_VOL": "22", "ADC_BASE": "23", "ADC_LPRES": "24", "POT_MUX": "25", "ADC_WIDTH": "26", "ADC_HPRES": "27", "ADC_EQG": "28", "ADC_EQF": "29", "ADC_SRR": "30", "ADC_DIST": "31"}
MUX_PIN = {"BASE": "15", "WIDTH": "1", "HPRES": "14", "LPRES": "2", "EQF": "13", "EQG": "4", "DIST": "12", "SRR": "5"}
MUX_SELECT = ["EQF", "HPRES", "BASE", "DIST", "WIDTH", "SRR", "LPRES", "EQG"]   # firmware: select 0..7 -> pot
MIDI = {"MIDI_TX": "14", "MIDI_RX": "15"}   # D13 / D14 = USART1 TX / RX (PB6 / PB7), libDaisy's default
CONTROL_PLACEMENT = {'U6': (22.85, 76.95, 0), 'U7': (56.94, 72.62, 0), 'U8': (56.94, 96.32, 0)}
MAIN_PLACEMENT = {'U3': (9.6, 71.5, 90), 'U4': (9.6, 63.3, 90), 'U1': (35.74, 82.97, 0), 'U2': (35.74, 70.27, 0), 'U5': (33.8, 63.25, 90), 'J13': (8.0, 27.95, 0), 'D10': (14.5, 27.9, 90), 'D11': (14.5, 33.3, 90), 'C2': (19.6, 27.95, 90), 'C4': (18.35, 19.0, 0), 'C5': (35.6, 108.35, 90), 'C6': (36.75, 99.4, 0), 'J14': (37.4, 92.25, 90), 'J15': (46.85, 104.37, 90)}
