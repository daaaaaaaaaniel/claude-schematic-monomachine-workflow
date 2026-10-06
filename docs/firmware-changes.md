# Firmware changes for rev beta (two boards)

Rev beta moves which Seed3 pin and mux channel each control arrives on, so the PCB traces can be short (d, 2026-10-06: "the firmware can handle sorting that out"). Two tables change (ADC pins, mux channels); the audio output level and an optional SD card are new. The codec, MIDI (pins 14/15), the clip LED (pin 12), USB and the mux select pins are unchanged.

All of this is generated: `pcb/design/floorplan.py` writes `pcb/design/pinmap.py`, and `python machine_filter.py` prints the mux table. If the floorplan changes, regenerate these tables from `pinmap.py` rather than editing this file by hand.

## 1. ADC pins (must change)

| Seed3 pin | Daisy name | rev alpha | **rev beta** |
|---|---|---|---|
| 22 | A0 | POT_MUX (pot multiplexer) | **CV 3 HP RES** |
| 23 | A1 | CV 1 BASE (1V/OCT) | **CV 1 BASE (1V/OCT)** |
| 24 | A2 | CV 2 WIDTH (1V/OCT) | **CV 4 LP RES** |
| 25 | A3 | CV 3 HP RES | **CV 5 EQ FREQ** |
| 26 | A4 | CV 4 LP RES | **CV 6 EQ GAIN** |
| 27 | A5 | CV 5 EQ FREQ | **CV 7 DIST** |
| 28 | A6 | CV 6 EQ GAIN | **POT_VOL (VOLUME pot)** |
| 29 | A7 | CV 7 DIST | **CV 2 WIDTH (1V/OCT)** |
| 30 | A8 | CV 8 SMPL RATE | **CV 8 SMPL RATE** |
| 31 | A9 | POT_VOL (VOLUME pot) | **POT_MUX (pot multiplexer)** |
| 32 | A10 | — | **—** |
| 35 | A11 | — | **—** |

Pin 29 (A7) is now unused (the matching found the other pins shorter); it's free for a future input.

The CV scaling is unchanged: reading = 1.667 V − CV/6, so +8 V reads 0.33 V and −8 V reads 3.0 V. The reading is inverted.

## 2. Pot multiplexer channel table (must change)

The U6 (74HC4051) select lines are unchanged: MUX_A = S0 on Seed3 pin 8 (D7), MUX_B = S1 on pin 9 (D8), MUX_C = S2 on pin 10 (D9). The common output POT_MUX moves to pin 31 (A9, see the table above). The pot behind each channel changes:

| Select (S2 S1 S0) | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|---|
| rev alpha | BASE | WIDTH | HP RES | LP RES | EQ FREQ | EQ GAIN | DIST | SMPL RATE |
| **rev beta** | **EQ FREQ** | **HP RES** | **BASE** | **DIST** | **WIDTH** | **SMPL RATE** | **LP RES** | **EQ GAIN** |

## 3. MIDI UART (no change)

MIDI stays on Seed3 pins 14/15 (D13/D14, PB6/PB7, USART1), as rev alpha and Electrosmith's Dev Kit: libDaisy's
default MIDI UART setup works as is. (An earlier rev beta draft moved it to pins 3/2; d chose to keep pins 2–7 free
for the SD card, 2026-10-06.)

## 4. Optional microSD card (new)

J15, a microSD socket on SDMMC1, is on the main board but not fitted by default (DNP). Seed3 pins 2–7: D3 (pin 2),
D2 (3), D1 (4), D0 (5), CMD (6), CK (7), with 47k pull-ups on CMD and D0–D3 (fitted), as the Dev Kit. Firmware should
enable SD only when the socket is fitted (for example, a compile-time option, or treat a failed mount as "no card").

## 5. Audio output level (changes)

The output stage gain is ×5.1 instead of the Dev Kit's ×10 (R61/R65 = 51k): digital full scale (0 dBFS) is about
±7.1 V at the jack, and the op amp can't clip. The input stays ×0.1 (±10 V in → about −3 dBFS). For a signal to come
out at the voltage it went in, firmware applies about +5.9 dB (× 1.98) of gain; inputs hotter than about ±7 V then
exceed full scale at unity, so limit or soft-clip there.

## 6. Op-amp sections (no firmware change)

The sections inside U1/U2 (ADC stages) and U7/U8 (LED drivers) moved for layout. That's invisible to software beyond the ADC table above.
