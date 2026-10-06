"""Pin assignments and placement, written by design/floorplan.py: edit floorplan.py, not this file.

Used by machine_filter.py (SKiDL) and design/boards.py. Units: 1 = A (pins 1-3), 2 = B (5-7), 3 = C (8-10),
4 = D (12-14). Positions: panel frame seen from the front, mm: (x, y, rotation) of the footprint origin
as pcbnew's SetPosition takes it (KiCad = panel + (100, 50)); back-side parts are then flipped left-right."""

HEADER_PINS = {'1': ['GND', 'OUT_L', 'OUT_R', 'GND', 'IN_L', 'IN_R', 'GND'], '2': ['GND', 'POT_VOL', 'POT_MUX', 'GND', 'LED_A', 'MUX_C', 'GND', 'MUX_B', 'MUX_A', 'GND'], '3': ['GND', 'CV_WIDTH', 'CV_BASE', 'GND', 'CV_LPRES', 'CV_HPRES', 'GND', 'CV_EQG', 'CV_SRR', 'GND', 'CV_EQF', 'CV_DIST', 'GND', '+3V3_A', 'GND', '-12V', 'GND', '+12V', 'GND']}
HEADER_POS = {'1': (43.54, 29.835, 0, 0), '2': (23.855, 46.345, 0, 0), '3': (43.54, 50.79, 0, 0)}   # pin 1 x, y; rotation of JBn (main, front) and of JAn (control, back)
SEED = (33.615, 88.22, 180)   # main board, back; rotation 0 = USB end up, 180 = down
ADC_UNIT = {"BASE": ("U2", 3), "WIDTH": ("U2", 4), "HPRES": ("U2", 2), "LPRES": ("U2", 1), "EQF": ("U1", 1), "EQG": ("U1", 4), "DIST": ("U1", 2), "SRR": ("U1", 3)}
LED_UNIT = {"BASE": ("U7", 4), "WIDTH": ("U7", 1), "HPRES": ("U7", 3), "LPRES": ("U7", 2), "EQF": ("U8", 4), "EQG": ("U8", 1), "DIST": ("U8", 3), "SRR": ("U8", 2)}
SEED_ADC = {"ADC_WIDTH": "22", "ADC_LPRES": "23", "POT_VOL": "24", "ADC_BASE": "25", "ADC_HPRES": "26", "ADC_EQG": "27", "ADC_EQF": "28", "POT_MUX": "29", "ADC_SRR": "30", "ADC_DIST": "31"}
MUX_PIN = {"BASE": "15", "WIDTH": "1", "HPRES": "14", "LPRES": "2", "EQF": "13", "EQG": "4", "DIST": "12", "SRR": "5"}
MUX_SELECT = ["EQF", "HPRES", "BASE", "DIST", "WIDTH", "SRR", "LPRES", "EQG"]   # firmware: select 0..7 -> pot
MIDI = {"MIDI_TX": "14", "MIDI_RX": "15"}   # D13 / D14 = USART1 TX / RX (PB6 / PB7), libDaisy's default
CONTROL_PLACEMENT = {'U6': (22.85, 76.95, 0), 'U7': (56.94, 72.62, 0), 'U8': (56.94, 96.32, 0)}
MAIN_PLACEMENT = {'U3': (28.6, 48.8, 90), 'U4': (28.6, 40.6, 90), 'U1': (54.74, 60.27, 0), 'U2': (54.74, 47.56, 0), 'U5': (60.85, 53.9, 0), 'J13': (8.0, 99.95, 0), 'D10': (14.5, 99.9, 90), 'D11': (14.5, 105.3, 90), 'C2': (19.6, 99.95, 90), 'C4': (17.2, 89.85, 90), 'C5': (54.6, 85.65, 90), 'C6': (52.35, 95.3, 0), 'J14': (53.95, 74.9, 0), 'J15': (22.47, 79.75, 0)}
