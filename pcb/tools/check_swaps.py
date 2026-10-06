#!/usr/bin/env python3
"""Check the current pin assignment (design/pinmap.py, machine_filter.SEED_PINS) against design/swap_groups.py.

Fails (exit 1) if a swap broke a rule: an analog input off an ADC pin, a Seed3 pin used twice, a fixed peripheral
pin moved, two 1V/OCT channels in one quad, an op-amp or mux slot used twice, MUX_SELECT out of step with MUX_PIN,
or a header that lost or doubled a net.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "design"))
import pinmap as PM  # noqa: E402
import swap_groups as SG  # noqa: E402

FIXED = {"2": "SD_D3", "3": "SD_D2", "4": "SD_D1", "5": "SD_D0", "6": "SD_CMD", "7": "SD_CK", "14": "MIDI_TX",
         "15": "MIDI_RX", "16": "CODEC_IN_L", "17": "CODEC_IN_R", "18": "CODEC_OUT_L", "19": "CODEC_OUT_R",
         "36": "USB_DM", "37": "USB_DP"}
MUX_CHANNEL_OF_PIN = {"13": 0, "14": 1, "15": 2, "12": 3, "1": 4, "5": 5, "2": 6, "4": 7}   # 74HC4051 datasheet
ONE_V_OCT = {"BASE", "WIDTH"}


def main():
    bad = []
    sys.path.insert(0, os.path.join(HERE, ".."))
    import machine_filter as MF                       # its SEED_PINS = every Seed3 pin the circuit uses
    used = MF.SEED_PINS
    for sig, pin in PM.SEED_ADC.items():
        if pin not in SG.ADC_PINS:
            bad.append(f"seed_adc: {sig} on pin {pin}, not an ADC pin")
    for pin, sig in FIXED.items():
        if used.get(pin) != sig:
            bad.append(f"seed_fixed: pin {pin} must carry {sig}, carries {used.get(pin)}")
    want = set(FIXED.values()) | set(PM.SEED_ADC) | {"MUX_A", "MUX_B", "MUX_C", "LED_CLIP"}
    missing = want - set(used.values())
    if missing:
        bad.append(f"seed: signals lost (two on one pin?): {sorted(missing)}")
    for sig in ("MUX_A", "MUX_B", "MUX_C", "LED_CLIP"):
        pin = next((p for p, s in used.items() if s == sig), None)
        if pin is None or not SG.SEED3[pin][2].startswith("GPIO"):
            bad.append(f"seed_gpio_out: {sig} on pin {pin}, not a GPIO")
    for table, name in ((PM.ADC_UNIT, "cv_opamp_sections"), (PM.LED_UNIT, "led_driver_sections")):
        slots = list(table.values())
        if len(set(slots)) != len(slots) or any(u not in (1, 2, 3, 4) for _, u in slots):
            bad.append(f"{name}: a section is used twice or doesn't exist: {table}")
    for chip in ("U1", "U2"):
        n = [c for c, (u, _) in PM.ADC_UNIT.items() if u == chip and c in ONE_V_OCT]
        if len(n) != 1:
            bad.append(f"cv_opamp_sections: {chip} carries {len(n)} 1V/OCT channels {n}, must be 1")
    if len(set(PM.MUX_PIN.values())) != 8 or set(PM.MUX_PIN.values()) - set(MUX_CHANNEL_OF_PIN):
        bad.append(f"mux_channels: MUX_PIN must use each channel pin once: {PM.MUX_PIN}")
    sel = [None] * 8
    for pot, pin in PM.MUX_PIN.items():
        sel[MUX_CHANNEL_OF_PIN[pin]] = pot
    if sel != PM.MUX_SELECT:
        bad.append(f"mux_channels: MUX_SELECT {PM.MUX_SELECT} should be {sel} (firmware table)")
    nets = [n for sigs in PM.HEADER_PINS.values() for n in sigs if n != "GND"]
    if len(nets) != len(set(nets)):
        bad.append(f"board_headers: a net appears twice: {sorted({n for n in nets if nets.count(n) > 1})}")
    for h, sigs in PM.HEADER_PINS.items():
        for k, n in enumerate(sigs):
            if n in ("+12V", "-12V", "+3V3_A") and "GND" not in sigs[max(0, k - 1):k + 2]:
                bad.append(f"board_headers: JB{h} pin {k + 1} ({n}) has no ground beside it")
    print("swap groups:", "all assignments legal" if not bad else "PROBLEMS:")
    for b in bad:
        print("   ", b)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
