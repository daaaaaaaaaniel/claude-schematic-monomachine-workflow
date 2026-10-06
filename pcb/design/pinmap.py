"""Pin assignments and placement. Since 2026-10-06 the pin map follows the PCB layout: edit this file to match the
layout (FLOORPLAN=1 would overwrite it). What may be swapped, and what a swap costs: design/swap_groups.py.

Used by machine_filter.py (SKiDL) and design/boards.py. Units: 1 = A (pins 1-3), 2 = B (5-7), 3 = C (8-10),
4 = D (12-14). Positions: panel frame seen from the front, mm: (x, y, rotation) of the footprint origin
as pcbnew's SetPosition takes it (KiCad = panel + (100, 50)); back-side parts are then flipped left-right."""

HEADER_PINS = {'1': ['OUT_R', 'GND', 'OUT_L', 'GND', 'IN_R', 'IN_L', 'GND', '+3V3_A', 'GND', 'CV_BASE', 'GND', 'CV_WIDTH', 'GND', '+12V', 'GND', 'POT_VOL', 'POT_MUX', 'GND', 'CV_HPRES', 'GND', 'CV_LPRES', 'GND', 'CV_SRR', 'GND', 'CV_EQF', 'GND', 'CV_DIST', 'GND', '-12V', 'GND'], '2': ['LED_A', 'MUX_A', 'MUX_C', 'MUX_B', 'GND'], '3': ['CV_EQG', 'GND']}
HEADER_POS = {'1': (43.18, 25.4, 0, 180), '2': (21.59, 57.15, 270, 90), '3': (64.77, 100.33, 90, 270)}   # pin 1 panel x, y; rotation of JBn (main, front) and of JAn (control, back), from tools/connector_search.py
SEED = (14.565, 110.9, 180)   # main board, back; rotation 0 = USB end up, 180 = down
# 2026-10-06: ADC_UNIT and SEED_ADC re-matched to the placed U1/U2 (tools/rematch_adc.py); each quad carries one 1V/OCT channel, on section A
ADC_UNIT = {"BASE": ("U2", 1), "WIDTH": ("U1", 1), "HPRES": ("U2", 2), "LPRES": ("U2", 3), "EQF": ("U2", 4), "EQG": ("U1", 2), "DIST": ("U1", 3), "SRR": ("U1", 4)}
LED_UNIT = {"BASE": ("U7", 4), "WIDTH": ("U7", 1), "HPRES": ("U7", 3), "LPRES": ("U7", 2), "EQF": ("U8", 4), "EQG": ("U8", 1), "DIST": ("U8", 3), "SRR": ("U8", 2)}
SEED_ADC = {"ADC_HPRES": "22", "ADC_BASE": "23", "ADC_LPRES": "24", "ADC_EQF": "25", "ADC_EQG": "26", "ADC_DIST": "27", "POT_VOL": "28", "ADC_WIDTH": "29", "ADC_SRR": "30", "POT_MUX": "31"}
MUX_PIN = {"BASE": "15", "WIDTH": "1", "HPRES": "14", "LPRES": "2", "EQF": "13", "EQG": "4", "DIST": "12", "SRR": "5"}
MUX_SELECT = ["EQF", "HPRES", "BASE", "DIST", "WIDTH", "SRR", "LPRES", "EQG"]   # firmware: select 0..7 -> pot
MIDI = {"MIDI_TX": "14", "MIDI_RX": "15"}   # D13 / D14 = USART1 TX / RX (PB6 / PB7), libDaisy's default
CONTROL_PLACEMENT = {'U6': (22.85, 76.95, 0), 'U7': (56.94, 72.62, 0), 'U8': (56.94, 96.32, 0)}
MAIN_PLACEMENT = {'U3': (9.6, 71.5, 90), 'U4': (9.6, 63.3, 90), 'U1': (35.74, 82.97, 0), 'U2': (35.74, 70.27, 0), 'U5': (33.8, 63.25, 90), 'J13': (8.0, 27.95, 0), 'D10': (14.5, 27.9, 90), 'D11': (14.5, 33.3, 90), 'C2': (19.6, 27.25, 90), 'C4': (6.75, 42.9, 0), 'C5': (35.6, 108.35, 90), 'C6': (35.6, 98.25, 90), 'J14': (42.75, 104.4, 0), 'J15': (48.05, 89.67, 90)}
