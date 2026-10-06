# Project library sources

Built by `../design/build_lib.py`. Priority (d, 2026-10-05): parts from the repos d linked before KiCad's stock
libraries.

| Part | Footprint (`filter-module:`) | Symbol | Source | Licence |
|---|---|---|---|---|
| Thonkiconn PJ398SM | `PJ398SM_Jack_ES` (+ courtyard added) | `EURO_JACK` | Electrosmith Seed3 Eurorack Dev Kit Rev3 (`b4479f9`), read from its board and schematic | MIT, © Electrosmith |
| 9 mm pot | `Pot_9mm_SnapIn_ES` (+ courtyard added) | `POT_9MM` | same | MIT, © Electrosmith |
| Daisy Seed3 | `Daisy_Seed_ES` | `Daisy_Seed3` | Electrosmith DaisyKiCad (d's copy) | MIT, © 2025 Electrosmith |
| Daisy Seed3, used on the board | `Daisy_Seed_ES_Sockets` | — | `Daisy_Seed_ES` with its courtyard cut to the two sockets (flat parts go under the module); written by `design/gen_pcb.py` | MIT, © 2025 Electrosmith |
| microSD socket HRO TF-01A (LCSC C91145) | `TF-01A` | `MicroSD_TF-01A` | Electrosmith Seed3 Eurorack Dev Kit Rev3 (`b4479f9`), `libs/TF-01A` (SnapEDA origin); symbol renamed, SnapEDA fields dropped, reference J | MIT, © Electrosmith (SnapEDA's terms for the original) |
| Eurorack power 2×5 shrouded | `Pins_2x05_2.54mm_TH_EurorackPower_Shrouded` | `Eurorack_Power_10pin_Shrouded` | 4ms-kicad-lib `e11c8bf` (2026-10-05) | Unlicense |
| Expansion 2×4 unshrouded | `Pins_2x04_2.54mm_TH` | stock `Conn_02x04_Odd_Even` | 4ms | Unlicense |
| Thonkiconn PJ398SM, CV jacks (sleeve leg bent) | `PJ398SM_Jack_4ms_BentGND` (pads renamed TIP / NORM / GND; tip and switch pins moved to Electrosmith's positions, so all 12 jacks sit alike) | `EURO_JACK` | 4ms `EighthInch_PJ398SM_Alt-GND` | Unlicense |
| 3 mm LED | `LED_3mm_C1A2` | `Red_3mm_TH` | 4ms | Unlicense |
| 3 mm red/green LED, by the CV jacks | `LED_3mm_Raised` (4ms `LED_3mm_C1A2`, courtyard shrunk to the pads: the LED stands up to the panel) | stock `LED_Dual_Bidirectional` (none in the repos) | 4ms | Unlicense / CC BY-SA 4.0 + exception |
| TL072 | `SOIC-8_3.9x4.9mm_Pitch1.27mm` | `TL072` | 4ms | Unlicense |
| LMV324, LM324, 74HC4051 | `SOIC-14_…`, `SOIC-16_…` | stock | 4ms footprints; KiCad stock symbols (none in the repos) | Unlicense / CC BY-SA 4.0 + exception |
| R, C 0603 / 0805 / 1206 | `R_0603`, `C_0603`, `C_0805`, `R_1206_3216Metric` | stock `Device:R`, `Device:C` | 4ms footprints | Unlicense |
| SOT-23, SOD-123 | `SOT-23`, `D_SOD-123` | stock | 4ms | Unlicense |
| 100 µF, headers 1×N, M3 hole | — | stock | KiCad stock (`CP_Elec_6.3x7.7` is also what the Dev Kit uses) | CC BY-SA 4.0 + exception |
| PWR_FLAG | — | `PWR_FLAG` | 4ms | Unlicense |

3D models are stripped from the copies (their paths point into the original libraries).

Not used, and why:
- **nebs/eurocad:** no licence file; its jack and pot footprints have ~0.1 mm copper rings (not manufacturable); its
  Eurorack power symbol has ±12 V reversed.
- **benjiaomodular/KiCadLibraries:** its jack and 9 mm pot footprints are copies of KiCad's stock ones; CC BY-SA 4.0
  (share-alike) with no design exception; no 14HP panel template.
- **GregBurns/sm_kicad:** only a Patch SM footprint, for the later Patch SM build.
- 4ms's 9 mm pots (Alps RK09K geometry) and its PJ398SM (pins 0.3–0.7 mm off the stock and Electrosmith geometry).

3D models: none are copied into this library. Each footprint refers to a model in KiCad 10's own 3D library
(`${KICAD10_3DMODEL_DIR}`, CC BY-SA 4.0 with KiCad's library exception), the one KiCad's matching stock footprint
uses, placed onto our pads by `design/models.py`. The source libraries' own model references were dropped by
`build_lib.py`: they pointed at KiCad 4–6 folders or 4ms's own model folder, not at KiCad 10's.
