# Design review: what was checked, what is still open

d's note (2026-10-06): the rev alpha scripts were "written based on poor research". This records which facts in the
design were checked against primary sources, and which questions remain. Checked 2026-10-06.

## Checked and correct

| Item | Source checked | Result |
|---|---|---|
| Every Seed3 pin used (audio 16–19, AGND 20, 3V3_A 21, ADC A0–A9 on 22–31, USB 36/37, 3V3_D 38, VIN 39, GND 40, GPIO 2/3, 8–10, 12) | Electrosmith `Seed3_pinout.csv` | all match |
| Project symbol `Daisy_Seed3` pin numbers and names | same CSV | match |
| Seed3 footprint: two rows 15.24 mm apart, 2.54 mm pitch, DIP numbering | Daisy Seed datasheet v1.0.5 (Seed3 is pin-compatible per Electrosmith) | match |
| MIDI on USART3 at PC10/PC11 | libDaisy `src/per/uart.cpp` | supported |
| 74HC4051 pinout (channels 0–7 on pins 13, 14, 15, 12, 1, 5, 2, 4; S0–S2 on 11/10/9; enable 6, VEE 7) | 74HC4051 datasheet, KiCad stock symbol | match |
| LMV324 / LM324 (SOIC-14) and TL072 (SOIC-8) pinouts | standard pinouts, symbols | match |
| LM4040-10 polarity (K to GND, A to −10 V via R3 from −12 V) | SOT-23 pinout | correct for a negative shunt reference |
| −10 V reference current: (12 − 0.4 − 10) V / 1 kΩ ≈ 1.6 mA, 0.67 mA to the offsets | arithmetic | ample margin |
| B5819W orientation (D10 anode at input, D11 cathode at input) | SOD-123 pin 1 = cathode | correct |
| Eurorack header: pins 1/2 = −12 V (stripe), 3–8 GND, 9/10 +12 V; pad 1 square | footprint | correct |
| Jack symbol pins TIP / NORM / GND = footprint pads, both jack footprints | library files | match |
| Pot pins 1/2/3 = footprint pads; pin 3 is the CW end when viewed from the front | footprint geometry | match |
| LED_3mm_C1A2 pad 1 = cathode = symbol pin 1 | library files | match |
| VIN: +12 V through 2 × 3.3 Ω | Daisy Seed datasheet: VIN 4–17 V | within range |
| Op-amp input common-mode: LMV324 on 0–3.3 V with + input at GND; LM324 on ±12 V | datasheets | fine |
| TL072 phase reversal (d, 2026-10-06). Classic TL07x (our TL072IDR) has a common-mode range of ±11 V min (−12…+15 V typ) at ±15 V; its output can flip to the wrong rail if an input goes below that range, near V−. All four TL072 sections here are inverting with + at GND, so both inputs sit at ≈ 0 V. U3 (×0.1) can't saturate even at ±12 V in. U4 at ×3.9 needs ±5.5 V, well inside its swing. Even an overdriven ×10 stage would only move its − input to about −0.4 V | TI TL072 datasheet (SLOS080) | no risk |
| Related edge case, LM324 LED drivers: a −12 V CV puts the + input ≈ 0.2–0.3 V below the −11.7 V rail (after D11), through 10k (≈ 20 µA). That's at the LM324's −0.3 V limit, where phase reversal can begin; harmless current, worst case the LED flickers wrong colour at a −12 V input. Optional fix: a small Schottky clamp from the + input to the −12 V rail | arithmetic, LM324 datasheet limits | marginal, low risk |

## Open questions (not wiring errors)

1. **Audio output gain (pending d's decision).** Checked against Electrosmith's Seed3 Eurorack Dev Kit, tag Rev3
   (github.com/daisyaudio/Seed3-DevKit-Eurorack, KiCad source exported with kicad-cli): input = 100k in, 10k ∥ 330p,
   100 Ω to the codec (×0.1); output = 10k in, 100k ∥ 33p, 100 Ω to the jack (×10); TL072s on ±12 V; no level notes
   on the schematic. Our values match exactly. ×0.1 then ×10 is unity from jack to jack, so ±10 V in can come back out
   at ±10 V. The cost: the Seed3 datasheet's 0 dBFS = 1 Vrms becomes ±14 V at ×10, past a TL072's ≈ ±10 V swing on
   ±12 V, so firmware must keep output peaks below about −3 dBFS (a limiter or soft clipper). Alternatives: ×5.6
   (56k, C ≈ 56p) or ×4 (39k, C ≈ 82p) can't clip in the op amp, but cap the output at ±7.9 V or ±5.5 V and need
   +5 or +8 dB of digital gain for unity.
   **Decided (d, 2026-10-06): ×5.1, R61/R65 = 51k, C60/C62 = 47p** (both JLC basic: 51k C23196, 47p C1671).
   10 Vpp is the useful maximum and 20 Vpp isn't a target; ×5 keeps about 3 dB below the TL072's clip point at
   digital full scale. Simulated (pcb/sim): gain ×5.05 (the codec's 100 Ω output impedance included), 0 dBFS =
   ±7.1 V, clipping at ±10.2 V (≈ +3 dB above full scale, so unreachable), −3 dB at 60 kHz, −0.45 dB at 20 kHz,
   no measurable distortion at 0 dBFS. (×10 clips at −2.8 dBFS: 12 % THD at 0 dBFS.) 47p is C1671 (basic C0G).
   Reference: the Daisy Seed datasheet, p. 25 (Fig. 3.6/3.7, "Eurorack Level Audio Input/Output"), shows the same
   circuits as the Dev Kit: input 100k / 10k ∥ 330p / 100 Ω ("Input Impedance: 100KΩ (typ.)"), output 10k / 100k ∥ 33p
   / 100 Ω ("Output Impedance: 100Ω"). ×5.1 departs only in the output feedback pair (51k ∥ 47p); both stated
   impedances and every datasheet rating still hold. It's a recommended circuit, not a limit (d to confirm).
2. **Audio input gain: keep ×0.1.** Correction to an earlier version of this review, which called ±1.8 V the
   codec's "input range" and suggested ×0.2. The Seed3 datasheet (Table 1) lists the audio inputs at −1.8 / +1.8 V
   under **absolute maximum ratings** ("AC coupled and 3.6Vpp, or approx. 1Vrms"). That's a damage limit, so a
   hot ±10 V input at ×0.2 (±2 V) would exceed it. At ×0.1 even ±12 V gives ±1.2 V. A small increase (×0.15) is
   the most that's safe. d's rule: the Seed3 datasheet is authoritative.
3. **Bicolour LED colour.** "Green for +, red for −" holds only if, on the chosen 2-lead red/green LED, the green
   LED's anode is the lead on footprint pad 1. That depends on the part; check its datasheet before ordering.
4. **Pin assignment depends on the floorplan.** ADC pins, op-amp sections and mux channels come from
   `design/floorplan.py`'s placement (`design/pinmap.py`). If the PCB placement moves a chip far from where the
   floorplan put it, re-run `floorplan.py` with the new position, or the traces will cross.
5. **Rev alpha's PCB scripts are not carried over.** d's alpha archive has `design/gen_pcb.py`, `route.py`,
   `fanout.py`, `check_panel.py`, `gen_panel_pcb.py` and others, for the old single board. d calls that placement
   stale and untrustworthy, and the split changes the board, so they aren't part of this handoff. They may still
   be useful as examples of driving `pcbnew` from Python.

## Decided or pending with d (2026-10-06)

- **MIDI vs SD card: decided (d, 2026-10-06): MIDI back to Seed3 pins 14/15 (USART1, libDaisy's default, as the
  Dev Kit), keeping pins 2–7 free for SDMMC.** Electrically the options barely differ (the codec inputs are driven
  through 100 Ω, and MIDI only switches while messages are sent). Added (second revision): a do-not-populate microSD socket J15 at the board's bottom-left edge, near
  pins 2–7 (the floorplan finds room): the Dev Kit's circuit is a TF-01A microSD
  socket, 47k pull-ups on CMD and D0–D3 to 3V3_D, CK direct, card detect unused. A breakaway section was considered
  and set aside: the SD lines would have to cross the break, and DNP gives the same "decide later" with no extra work.
- **JLC basic parts** are preferred wherever possible (d; not a hard constraint: stock decides at order time).
  Checked 2026-10-06 against the CDFER JLCPCB-Kicad-Library snapshot of June 2026 (JLC's basic and preferred
  parts; github.com/CDFER/JLCPCB-Kicad-Library). Swapped to basic: TL072 → ST TL072CDT (C6961; the C grade is rated
  0–70 °C, fine in a case), ferrites → GZ2012D601TF (C1017, 0805, 600 Ω, 500 mA; the 0603 basic one is only 200 mA,
  and the +12 V rail draws about 0.2 A worst case). New values are basic: 51k (C23196), 47p (C1671), 47k (C25819).
  Still extended, no basic equivalent: 100 µF electrolytics (C72478), the 3.3 Ω anti-surge VIN resistors
  (C2577888), the 0.1 % resistors (C122538, C723637), the 25 ppm/K 120k (C862537), LMV324 (C7974: the basic LM324
  can't swing near 3.3 V), LM4040-10 (C201738), and the DNP microSD socket (C91145). Possible later: the LMV324s
  as eight LMV321 singles (C7972, "preferred"), at the cost of more placement area.
- **CV LEDs must light visibly at small CVs (under 2 V).** The driver has no dead zone: LED current = CV / 1.5k,
  so 0.33 mA at 0.5 V and 1.3 mA at 2 V. Whether 0.3–0.7 mA is visible depends on the LED's efficiency; pick a
  high-efficiency part, or lower R71–R78 (1k gives 10 mA at ±10 V, still within an LM324 and a 3 mm LED).
- **Bent-sleeve jack footprint:** needed only if the jacks' orientation puts a leg under the CV LED. Decide at
  layout.
- **Offset resistors R12/R16 (1V/OCT): upgrade to 25 ppm/K (d, 2026-10-06).** Worst-case drift 2.7 → 1.8 cents/K
  (pcb/sim/drift.cir). Probably a JLC extended part; pick the part in the BOM check.
- **Expansion header pinout: leave as is (d, 2026-10-06).** Optional header; a future expander will probably use jumper wires, so the rotation hazard (a 2×4
  connector turned 180° puts +3V3_D on USB_DM) matters only if a one-piece 2×4 housing or ribbon is used. A
  rotation-safe pinout is free to adopt anyway.
- **Expansion header pins 3 and 4 swapped (d, 2026-10-07):** USB_DP on pin 4, GND on pin 3, so D− and D+ run straight from
  Seed3 pins 36/37 into J14's near pin column; the old pin 3 route squeezed between pins 2 and 4 (0.27 mm each side, hand-soldered).
  The 180° rotation hazard is unchanged (pin 2 ↔ pin 7).
- **LED height in the panel:** the builder's choice at assembly; not a design constraint.

## Added 2026-10-06: the two-board split

| Item | Check | Result |
|---|---|---|
| Nothing lost or shorted in the split | `tools/check_netlist.py` joins main + control through JAn/JBn pin k and compares with the one-circuit SKiDL netlist | identical, 103 nets |
| The drawing matches the two SKiDL board netlists, and no drawn net spans both boards | same script | identical (125 nets) |
| ERC on the single project | kicad-cli, all severities | 0 / 0 |
| The PCB file separates into the two boards | `tools/separate.sh` (kikit separate) on the outline-only PCB | one 70 × 100 and one 70 × 107 outline |
| Header current: ±12 V feeds only U7/U8 and the LEDs (≤ 8 × 6 mA + 2 × ~1 mA) | arithmetic | well under one 2.54 mm pin's rating |
| Through-hole resistors (DIN0204, 1/8 W) in the LED drivers | worst case 1.5k at ~6 mA: 54 mW; 10k, 1M negligible | fine |

Still open for the split:
6. **Stack height.** The boards sit ~11 mm apart (8.5 mm socket + 2.5 mm header plastic). With the Seed3 on its
   sockets and J13 on the main board's back, the module is roughly 40 mm deep behind the panel: check against the
   case before ordering.
7. **Headers between the Seed3's socket rows.** JB1 and JB3 stand between the Seed3's socket rows; their
   through-hole pins come out on the main board's back under the Seed3. Solder them before the sockets, trim them
   flush and check they clear the Seed3's underside.
8. **Header alignment.** JAn and JBn must land on exactly the same panel coordinates (`pinmap.py` `HEADER_POS`).
   Place both from that file in the PCB scripts, never by hand.
9. **microSD J15 is far from its pins.** The floorplan found no room for the socket by SDMMC pins 2–7 (the Seed's
   left row, bottom end, at the board edge), so J15 sits right of JB2: about 255 mm of trace over six lines. Fine for
   SD at default speed; the layout can move it closer if room appears.

## Board-to-board headers (2026-10-06)

d asked for the two headers to be split into three or four, any orientation and pin count, and raised hand
soldering: rev beta's first JB1 was too close to the Seed3's pins. `design/headers.py` now chooses them inside the
floorplan:
- **Groupings tried:** the four natural groups (audio + pot/LED, CVs, mux + pot, power), every 3-group merge of them,
  and k-means on the signals' two ends for 3 and 4 groups.
- **Pin order:** GND, analog pairs with a GND after each pair, digital pairs likewise, each supply between GNDs.
- **Legal sites:** inside both outlines; clear of the control board's front pins and the main board's back parts;
  every pin at least 5.08 mm from every Seed3 pin (d's hand-soldering concern); 2.5 mm from the edges.
- **Cost:** the weighted trace length of the crossing signals, both boards, plus 15 mm per header so near-ties go to
  fewer headers. The 12 best sites per group are combined without overlaps.
- **Alternation:** headers ↔ Seed3 position, until neither moves (3 rounds). The Seed3 moved 15 mm left.

**Result:** three headers, 15/13/10 pins, 17 of 38 ground. Closest header pin to a Seed3 pin: 7.46 mm. Floorplan
cost 879 (main 405, control 475). Runtime about a minute.

## ngspice checks (2026-10-06, `pcb/sim/`)

TL072 and LM324: TI's Boyle-type macromodels; LMV324: a behavioural model at TI's datasheet swing limits (the
National macromodel tops out at 2.5 V on 3.3 V, against the datasheet's VCC − 0.1 V min, so it isn't used). Rails
±11.7 V. Boyle models don't model input common-mode limits or phase reversal. Plot: `pcb/sim/ngspice-checks.png`.

| Check | Result |
|---|---|
| Audio out, ×5.1 (51k/47p) | ×5.05; 0 dBFS = ±7.1 V; clips at ±10.2 V; −3 dB at 60 kHz, −0.45 dB at 20 kHz |
| Audio out, ×10 (Dev Kit) | clips at ±10.2 V = −2.8 dBFS; 12 % THD at 0 dBFS |
| Audio in, ×0.1 | ±12 V in → ±1.19 V at the codec (under its ±1.8 V abs. max); − input stays at 0 V; −3 dB at 48 kHz, −0.7 dB at 20 kHz |
| CV input (LMV324) | 0 V → 1.667 V, +8 V → 0.333 V, −8 V → 3.000 V; linear for about ±8.8 V at worst-case swing; −3 dB at 7.9 kHz. The ADC pin can't leave 0.12–3.2 V |
| CV input, overdrive | beyond about −10.8 V of CV the op amp saturates high and its − input falls below −0.2 V (the LMV324's absolute maximum), reaching −0.35 V at −12 V, through ≈ 15 kΩ: microamps, almost certainly harmless, but outside the rating. A clamp diode there would leak into the 1V/OCT node, so leave it unless d wants strict compliance |
| CV LED driver (LM324) | LED current = CV / 1.5k: 0.33 mA at 0.5 V, 1.3 mA at 2 V; levels off at 5.4 mA (green, +CV) and 6.6 mA (red, −CV). At −12 V CV the + input sits at −11.88 V, 0.18 V below the −11.7 V rail (the model can't show phase reversal) |
| 1V/OCT Monte Carlo (2000 runs) | before calibration: scale ±2.3 cents per octave, offset −177 to +184 cents (about ±1.5 semitones), mostly R12 (1 %) and the LM4040C (0.5 %). Both calibrate out in firmware |
| 1V/OCT drift, worst case | offset 2.7 cents/K (thick-film R12 at 100 ppm/K, LM4040C at 100 ppm/K, 0.1 % parts at 25 ppm/K, all drifting the bad way); 1.8 cents/K with a 25 ppm/K R12, of which the LM4040C alone is 1.2. Scale drift 0.06 cents per octave per K. Typical drift is well below worst case |
