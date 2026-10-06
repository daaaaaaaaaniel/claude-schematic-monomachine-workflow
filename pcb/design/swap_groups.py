"""Swap groups: which pins and sub-units are truly interchangeable, and what a swap costs (d, 2026-10-07).

KiCad has no swap-group metadata (Altium and Allegro do), so this file plays that role. A layout-driven swap is made
by editing the table named in `edit`, rebuilding (pcb/tools/build.sh, without FLOORPLAN=1) and updating the board
from the schematic; never by KiCad's Swap Pad Nets + Update Schematic from PCB, which would edit the generated
schematics. pcb/tools/check_swaps.py checks the current assignment against these groups on every build.

Seed3 facts are from Electrosmith's pinout CSV, fetched 2026-10-07:
https://daisy.nyc3.cdn.digitaloceanspaces.com/products/seed3/Seed3_pinout.csv (linked from docs.daisy.audio/hardware/Seed3/).
"""

# Seed3 pin -> (Daisy name, STM32 pin, functions that matter here), from the CSV.
SEED3 = {
    "1": ("D0", "PB12", "GPIO; USB_HS_ID"), "2": ("D1", "PC11", "GPIO; SDMMC1_D3"), "3": ("D2", "PC10", "GPIO; SDMMC1_D2"),
    "4": ("D3", "PC9", "GPIO; SDMMC1_D1"), "5": ("D4", "PC8", "GPIO; SDMMC1_D0"), "6": ("D5", "PD2", "GPIO; SDMMC1_CMD"),
    "7": ("D6", "PC12", "GPIO; SDMMC1_CK"), "8": ("D7", "PG10", "GPIO"), "9": ("D8", "PG11", "GPIO"),
    "10": ("D9", "PB4", "GPIO"), "11": ("D10", "PB5", "GPIO"), "12": ("D11", "PB8", "GPIO; TIM4_CH3, TIM16_CH1 (PWM)"),
    "13": ("D12", "PB9", "GPIO; TIM4_CH4, TIM17_CH1 (PWM)"), "14": ("D13", "PB6", "GPIO; USART1_TX"),
    "15": ("D14", "PB7", "GPIO; USART1_RX"), "16": ("", "", "AUDIO IN L"), "17": ("", "", "AUDIO IN R"),
    "18": ("", "", "AUDIO OUT L"), "19": ("", "", "AUDIO OUT R"), "20": ("", "", "AGND"), "21": ("", "", "+3V3A"),
    "22": ("A0", "PC0", "ADC"), "23": ("A1", "PA3", "ADC; TIM2_CH4"), "24": ("A2", "PB1", "ADC; TIM3_CH4"),
    "25": ("A3", "PA7", "ADC; TIM3_CH2"), "26": ("A4", "PA6", "ADC; TIM3_CH1"), "27": ("A5", "PC1", "ADC"),
    "28": ("A6", "PC4", "ADC"), "29": ("A7", "PA5", "ADC; DAC1_OUT2; TIM2_CH1"), "30": ("A8", "PA4", "ADC; DAC1_OUT1"),
    "31": ("A9", "PA1", "ADC; TIM2_CH2"), "32": ("A10", "PA0", "ADC; TIM2_CH1"), "33": ("D26", "PD11", "GPIO"),
    "34": ("D27", "PG9", "GPIO"), "35": ("A11", "PA2", "ADC; TIM2_CH3"), "36": ("D29", "PB14", "USB_HS_D-"),
    "37": ("D30", "PB15", "USB_HS_D+"), "38": ("", "", "+3V3D"), "39": ("", "", "VIN"), "40": ("", "", "GND"),
}
ADC_PINS = ["22", "23", "24", "25", "26", "27", "28", "29", "30", "31", "32", "35"]   # A0-A11, the CSV's ADC column
FREE_GPIO = ["1", "11", "13", "33", "34"]          # plain GPIO not used by rev beta (plus any ADC pin left over)
PWM_PINS = ["12", "13", "23", "24", "25", "26", "29", "31", "32", "35"]   # GPIO with a timer channel (CSV)

GROUPS = {
    "seed_adc": {
        "what": "the ten analog inputs: eight CV stages (ADC_*), POT_VOL, POT_MUX",
        "slots": "any Seed3 ADC pin A0-A11 (pins 22-32 and 35); 12 slots, 10 used",
        "constraints": "none beyond being an ADC pin; libDaisy reads any of A0-A11. Pins 29/30 are also the DAC "
                       "outputs, so leaving one of them free keeps a DAC available.",
        "firmware": "ADC pin table (docs/firmware-changes.md section 1)",
        "edit": "pinmap.SEED_ADC",
        "rematch": "python3 pcb/tools/rematch.py adc [--write] (tools/rematch_adc.py)",
    },
    "seed_gpio_out": {
        "what": "digital outputs: MUX_A/B/C (mux selects S0-S2, pins 8/9/10) and LED_CLIP (pin 12, via R70)",
        "slots": "these four pins plus FREE_GPIO and any unused ADC pin",
        "constraints": "LED_CLIP needs a PWM-capable pin (PWM_PINS) only if the firmware dims it. Which GPIO drives "
                       "S0, S1 or S2 is free too, with the firmware's select-bit order changed to match.",
        "firmware": "the GPIO pin constants (and the select-bit order)",
        "edit": "machine_filter.SEED_PINS and boards.py (not yet in pinmap.py)",
    },
    "seed_fixed": {
        "what": "pins tied to one peripheral: SDMMC1 2-7 (D3, D2, D1, D0, CMD, CK), MIDI on USART1 14/15 (TX/RX), "
                "codec 16-19, AGND 20, +3V3A 21, USB 36/37, +3V3D 38, VIN 39, GND 40",
        "slots": "none", "constraints": "not swappable: the peripheral or the module fixes them",
        "firmware": "-", "edit": "-",
    },
    "cv_opamp_sections": {
        "what": "which LMV324 section (U1/U2, sections A-D) takes which CV channel; the section's resistors and "
                "capacitor follow it automatically",
        "slots": "8 sections for 8 channels; within a section, out / - / + are not interchangeable (inverting stage)",
        "constraints": "exactly one 1V/OCT channel (BASE, WIDTH) per quad (d, 2026-10-06); which section is free",
        "firmware": "none", "edit": "pinmap.ADC_UNIT",
    },
    "led_driver_sections": {
        "what": "which LM324 section (U7/U8, A-D) drives which CV's bicolour LED; passives follow",
        "slots": "8 sections for 8 LEDs", "constraints": "none", "firmware": "none", "edit": "pinmap.LED_UNIT",
    },
    "audio_opamp_sections": {
        "what": "TL072 sections: U3 A/B = input L/R, U4 A/B = output L/R; passives follow",
        "slots": "L and R can trade sections within a chip", "constraints": "none",
        "firmware": "none", "edit": "machine_filter.py and boards.py (not yet in pinmap.py)",
    },
    "mux_channels": {
        "what": "which 74HC4051 channel (U6, channels 0-7) reads which pot",
        "slots": "8 channels for 8 pots", "constraints": "none",
        "firmware": "mux select table (docs/firmware-changes.md section 2; pinmap.MUX_SELECT)",
        "edit": "pinmap.MUX_PIN (keep MUX_SELECT in step: check_swaps.py verifies it)",
    },
    "board_headers": {
        "what": "pin order of the board-to-board headers JA1-JA3 / JB1-JB3, and which header carries which net",
        "slots": "15 + 13 + 10 pins; JAn pin k = JBn pin k by construction",
        "constraints": "ground pins keep their places; no two kinds of signal (audio, CV, pot, digital) side by "
                       "side without a ground between; a supply pin has grounds on both sides (never +12 V next to "
                       "-12 V); JAn on the back must be turned so its pin k sits on JBn pin k. Headers may sit "
                       "right at the board edge (d, 2026-10-07). Changing a header's "
                       "pin count changes its footprint (a board update re-adds it)",
        "firmware": "none", "edit": "pinmap.HEADER_PINS",
        "rematch": "python3 pcb/tools/rematch.py headers [--write]: best order by orthogonal distance on both boards",
    },
    "expansion_j14": {
        "what": "pin order of the 2x4 expansion header J14",
        "slots": "8 pins", "constraints": "a plug turned 180 degrees joins pin k to pin 9-k: keep +3V3_D off the "
                                          "pins opposite D-/D+ where possible (pin 2 <-> 7 is accepted, d 2026-10-06)",
        "firmware": "none", "edit": "machine_filter.py and boards.py",
    },
    "not_swappable": {
        "what": "Eurorack power J13 (standard pinout), microSD J15 (socket + SDMMC1), jacks (tip/switch/sleeve), "
                "bicolour LEDs (swapping legs swaps the colours), pots (pin 1 = CCW/ground end: swapping ends "
                "reverses the knob, which firmware could undo, but the convention stays)",
        "slots": "none", "constraints": "-", "firmware": "-", "edit": "-",
    },
}
