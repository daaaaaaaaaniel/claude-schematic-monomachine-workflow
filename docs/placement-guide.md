# MACHINE FILTER: component placement guide (two boards)

This guide says which parts should sit next to which other parts, for the **rev beta** two-board schematic (`pcb/out/machine-filter.pdf`: main board pages 2–7, control board pages 8–12). Net names here are the main board's; on the control board the same nets carry the prefix `CTL_` (`CTL_CV_BASE`, `CTL_GND`, …), because each board's copper is its own net, joined only through the headers. Sections run from most to least important. Each one opens with the rule it applies, then names every part and pin it affects.

**The boards** (d, 2026-10-06):
- **MAIN** is assembled by JLC (SMD only), 70 × 100 mm, 2 layers (d, 2026-10-06). Its back carries every SMD part, the Seed3 on sockets, the power header J13, the expansion header J14 and the optional microSD socket J15 (DNP). Its front carries only the male board-to-board headers JB1–JB4.
- **CONTROL** is hand-soldered, 70 × 107 mm, 2 layers is fine. Its front faces the panel and carries the jacks, pots and LEDs. Its back carries the pot multiplexer U6, the LED drivers U7/U8 (SOIC), their through-hole resistors and capacitors, and the female headers JA1–JA3.
- The control board's JA1–JA4 plug onto the main board's JB1–JB4 (JAn onto JBn, pin k to pin k). With 8.5 mm sockets on 2.5 mm header plastic the boards sit about 11 mm apart.

**Coordinates:** everything is in the panel frame seen from the front, in mm (x right, y down), as in `pcb/design/boards.py`. Parts on a board's back are seen mirrored from the front. "Left" and "right" mean as seen from the front panel.

**Where the numbers come from:** `pcb/design/floorplan.py` places the parts with KiCad's own footprints, chose the original board-to-board headers (since 2026-10-07 `pcb/tools/connector_search.py` chooses them from the placed boards, section 7), then picks the pin assignments that make the short connections shortest. It writes them to `pcb/design/pinmap.py`, which lists the floorplan position of every IC, connector and bulky part (`CONTROL_PLACEMENT`, `MAIN_PLACEMENT`); resistors, small capacitors and ferrite beads are left to the layout, following this guide. The pictures are `pcb/out/floorplan-main.png` and `pcb/out/floorplan-control.png`. The floorplan only proves the parts fit and sets the pin assignment. The PCB step should refine it, not copy it blindly. If a chip ends up somewhere else, re-run `floorplan.py` (or edit its rules), then `tools/build.sh`.

**Where the rules come from:**
- *(guide: name)* marks rules from the Sourcery Studios #pcb-creation channel (`docs/community-pcb-layout-guide.md`).
- *(general practice)* marks standard analog layout practice that the channel didn't discuss.

**Pinouts used**
- **LMV324 / LM324 (SOIC-14):**
  - A: out 1, − 2, + 3.
  - B: + 5, − 6, out 7.
  - C: out 8, − 9, + 10.
  - D: + 12, − 13, out 14.
  - V+ is pin 4. V− is pin 11 (GND on the LMV324s).
- **TL072 (SOIC-8):** A = out 1, − 2, + 3. B = + 5, − 6, out 7. V− is pin 4, V+ is pin 8.
- **74HC4051 (SOIC-16):**
  - VCC 16, GND 8, VEE 7, enable 6, common 3, S0/S1/S2 on 11/10/9.
  - Channels 0–7 are on pins 13, 14, 15, 12, 1, 5, 2, 4.
- **LM4040 (SOT-23):** pin 1 = K, pin 2 = A.

---

## 1. What goes on which board, and why

**Rule:** keep each sensitive node short and on one board. Only robust signals cross the connector *(general practice; guide: The2dCour, keep nets short)*.

**Sensitive nodes, all on the main board:**
- Each op amp's − input.
- The path from each CV op-amp output to its ADC pin.
- The codec lines to and from U3/U4.
- −10V_REF.

**What crosses the connector:**
- Jack-level signals: CV and audio, low impedance, ±10 V.
- Slow pot wipers.
- The mux select lines.
- The clip-LED drive.
- The supplies.

**The LED drivers sit on the control board** because:
- The LED current never flows in the main board's analog ground.
- Their 1 MΩ inputs sit right at the jacks.
- They're hand-solderable SOICs with through-hole passives.

---

## 2. Decoupling capacitors at the IC power pins

**Rules**
- Every IC power pin gets its 100 nF cap as close to the pin as it will go *(guide: Luther; twig's checklist)*.
- The cap's ground end goes straight into the ground pour through its own via (main board), or straight to the ground plane side (control board) *(general practice)*.
- On the dual-supply parts, V+ and V− are on opposite sides of the chip. Each pin gets its own cap.

| Board | IC | Cap | Goes at | Ground end |
|---|---|---|---|---|
| main | U3 (TL072, audio in) | C70 | pin 8 (+12 V) | via at C70 |
| main | U3 | C71 | pin 4 (−12 V) | via at C71 |
| main | U4 (TL072, audio out) | C72 | pin 8 (+12 V) | via at C72 |
| main | U4 | C73 | pin 4 (−12 V) | via at C73 |
| main | U1 (LMV324, CV ADC) | C20 | pin 4 (+3V3_A) | via at C20; pin 11 gets its own GND via |
| main | U2 (LMV324, CV ADC) | C21 | pin 4 (+3V3_A) | via at C21; pin 11 gets its own GND via |
| main | U5 (LM4040) | C7 | across pin 2 (−10V_REF) and pin 1 (GND) | see section 5 |
| control | U7 (LM324, LED drivers) | C81 (THT) | pin 4 (+12 V) | short to GND |
| control | U7 | C82 (THT) | pin 11 (−12 V) | short to GND |
| control | U8 (LM324, LED drivers) | C83 (THT) | pin 4 (+12 V) | short to GND |
| control | U8 | C84 (THT) | pin 11 (−12 V) | short to GND |
| control | U6 (74HC4051) | C80 (THT) | pin 16 (+3V3_A) | pins 6, 7 and 8 also to GND, each by the shortest path |

**Detail:** the through-hole caps (2.5 mm disc) can't sit as close as an 0603. Put them right beside the pin with leads trimmed short, so the trace from cap to pin is a few millimetres.

---

## 3. CV ADC stages (main board): the parts at each inverting input

**Rules**
- The op amp's − input is the most noise-sensitive point in the stage. Everything on it goes right at the pin, and the node is no bigger than those parts' pads *(general practice)*.
- The feedback pair (R_f and C_f) goes directly across the − pin and the output pin *(general practice)*.
- Long traces go on the low-impedance side of a resistor, never between the resistor and the − pin *(general practice; guide: The2dCour, keep nets short)*.
- Lay out one channel well, then copy it *(guide: Locrius, multi-channel; The2dCour, work in blocks)*.

**Worked example: CV 1 (BASE, 1V/OCT), on U2 section A (pins 1, 2, 3)**
- **R11 (20k 0.1%) and C10 (1n)** sit side by side across U2 pin 2 (−) and pin 1 (out).
- **R13 (20k 0.1%)** has one end on pin 2. **R10 (100k 0.1%)** sits directly behind it. R10's far end takes the trace from the board-to-board connector (CV_BASE; pin in the table below).
- **R12 (120k offset, 25 ppm/K)** has one end on pin 2. The −10V_REF trace comes to R12's other end, not to the pin.
- **Pin 3 (+)** gets a ground via right next to the pin.
- **Pin 1 (out)** runs to Seed3 pin 23 (ADC_BASE). This trace is the one the floorplan keeps short: it's the ADC's input, and the Seed's ADC samples it.

**All eight channels**

| CV | Section: − / out / + | R_in at − pin | R_f | C_f | Offset | From header pin | To Seed3 pin |
|---|---|---|---|---|---|---|---|
| 1 BASE (1V/OCT) | U2A: 2 / 1 / 3 | R13 (R10 behind it) | R11 | C10 | R12 | JB1.10 | 23 |
| 2 WIDTH (1V/OCT) | U1A: 2 / 1 / 3 | R17 (R14 behind it) | R15 | C11 | R16 | JB1.12 | 29 |
| 3 HP RES | U2B: 6 / 7 / 5 | R18 | R19 | C12 | R20 | JB1.19 | 22 |
| 4 LP RES | U2C: 9 / 8 / 10 | R22 | R23 | C13 | R24 | JB1.21 | 24 |
| 5 EQ FREQ | U2D: 13 / 14 / 12 | R26 | R27 | C14 | R28 | JB1.25 | 25 |
| 6 EQ GAIN | U1B: 6 / 7 / 5 | R30 | R31 | C15 | R32 | JB3.1 | 26 |
| 7 DIST | U1C: 9 / 8 / 10 | R34 | R35 | C16 | R36 | JB1.27 | 27 |
| 8 SMPL RATE | U1D: 13 / 14 / 12 | R38 | R39 | C17 | R40 | JB1.23 | 30 |

**Detail**
- **U2 serves CV 1, 3, 4 and 5; U1 serves CV 2 and 6–8**, so each chip carries one 1V/OCT channel (BASE on U2, WIDTH on U1; d, 2026-10-06). Which section feeds which ADC pin is re-matched once U1/U2 are placed, so no output trace crosses another.
- The ADC pins and sections come from the floorplan's minimum-length matching, so the ADC pin order isn't the jack order. The firmware maps it (`docs/firmware-changes.md`).
- **1V/OCT precision group:** keep R10, R13 and R11 touching each other, and the same for R14, R17 and R15. Their ratio sets the tracking, so they should all sit at the same temperature. Keep both groups away from R1/R2 (section 8) and U5/R3 (section 5).

---

## 4. Audio stages (main board)

**Rules**
- The same − pin rules as section 3 apply *(general practice)*.
- The small series resistor at each op-amp output goes at the output pin *(general practice)*.
- Audio runs connector → op amp → Seed and back in one direction, without detours *(guide: trevortjes, input to output)*.

**Audio in, U3 (gain −0.1)**
- **IN L, U3 section A:**
  - R51 (10k) and C50 (330p) go across pin 2 (−) and pin 1 (out).
  - R50 (100k) has one end on pin 2. Its far end takes the trace from JB1 pin 2.
  - R52 (100 Ω) runs from pin 1 to Seed3 pin 16.
  - Pin 3 gets a ground via.
- **IN R, U3 section B:**
  - R55 and C52 go across pins 6 and 7.
  - R54 runs from pin 6 to JB1 pin 3.
  - R56 runs from pin 7 to Seed3 pin 17.
  - Pin 5 gets a ground via.
- **Normalling (IN R to IN L)** happens at the jacks on the control board. Nothing here.

**Audio out, U4 (gain −10)**
- **OUT L, U4 section A:**
  - R61 (51k) and C60 (47p) go across pins 2 and 1 (gain ×5.1).
  - R60 (10k) runs from pin 2 to Seed3 pin 18.
  - R62 (100 Ω) runs from pin 1 to JB1 pin 6.
  - Pin 3 gets a ground via.
- **OUT R, U4 section B:**
  - R65 and C62 go across pins 6 and 7.
  - R64 runs from pin 6 to Seed3 pin 19.
  - R66 runs from pin 7 to JB1 pin 5.
  - Pin 5 gets a ground via.

**Detail**
- U4's − pins (2 and 6) multiply any noise they pick up by 10. Make them the tightest nodes on the board.
- U3 and U4 sit right beside the Seed3's codec pins 16–19. The audio pins of JB1 (2, 3, 5, 6) sit between and just above the Seed3's socket rows, so the traces from JB1 to R50/R54 and from R62/R66 to JB1 cross the left socket row: between two socket pins on an inner layer, or round the Seed's upper end (JB1 pins 5/6 are already above it). They're low impedance, so the extra length is fine.

---

## 5. The −10 V reference and its eight offset resistors (main board)

**Rules**
- Keep Vref away from high currents and fast digital signals *(guide: Locrius)*.
- A shunt reference's filter cap goes right across the reference *(general practice)*.
- The reference trace goes to the far ends of the offset resistors, never to the op-amp pins.

**Placement**
- **U5, R3 and C7 form one tight group:**
  - U5 pin 1 (K) goes to ground with a via at the pin.
  - C7 sits across U5 pins 2 and 1.
  - R3 (1k) runs from pin 2 to −12 V.
- **The −10V_REF trace** runs from U5 pin 2 to R12, R16, R20, R24 (at U2) and R28, R32, R36, R40 (at U1).
- In the floorplan, U5 sits just above U2, so the trace is a short bus down past both chips.
- Keep it away from the LED_A line (Seed3 pin 12 → R70 → JB3 pin 1) and from the USB and MIDI lines to J14. MUX_A/B/C run from Seed3 pins 8/9/10 to JB3, away from U5.

---

## 6. LED drivers (control board): the high-impedance 1 MΩ nodes

**Rules**
- High-impedance nodes pick up noise, so the parts on them go right at the pin *(general practice)*.
- The LED current comes from a low-impedance op-amp output, so longer LED traces are fine.

**Worked example: CV 1 (BASE), on U7 section D (pins 12, 13, 14)**
- **R90 (1M)** runs from U7 pin 12 (+) to ground, right at the pin.
- **R80 (10k)** has one end on pin 12. Its far end goes to J5's tip.
- **R71 (1.5k)** runs from pin 13 (−) to ground, right at the pin.
- **D2** connects pin 14 (out) to D2 pin 1, and pin 13 to D2 pin 2.

**All eight channels**

| CV | Section: + / − / out | R8x at + pin | 1M at + pin | LED R at − pin | LED |
|---|---|---|---|---|---|
| 1 BASE | U7D: 12 / 13 / 14 | R80 | R90 | R71 | D2 |
| 2 WIDTH | U7A: 3 / 2 / 1 | R81 | R91 | R72 | D3 |
| 3 HP RES | U7C: 10 / 9 / 8 | R82 | R92 | R73 | D4 |
| 4 LP RES | U7B: 5 / 6 / 7 | R83 | R93 | R74 | D5 |
| 5 EQ FREQ | U8D: 12 / 13 / 14 | R84 | R94 | R75 | D6 |
| 6 EQ GAIN | U8A: 3 / 2 / 1 | R85 | R95 | R76 | D7 |
| 7 DIST | U8C: 10 / 9 / 8 | R86 | R96 | R77 | D8 |
| 8 SMPL RATE | U8B: 5 / 6 / 7 | R87 | R97 | R78 | D9 |

**Detail**
- Each jack tip feeds two places: its LED driver's R8x, on this board, and a JA2 pin that carries the CV to the ADC stage on the main board. Split the trace at the jack.
- In the floorplan, U7 sits by the top two CV jack rows and U8 by the bottom two, in the gap between the jack columns.

---

## 7. Board-to-board connector

**Rules** (d, 2026-10-07; `pcb/design/swap_groups.py`, `docs/placement-workflow.md` section 4)
- Up to 4 straight lines, horizontal or vertical, each one header pair cut to length (2–40 pins): JAn female on the
  control board's back over JBn male on the main board's front, pin k on pin k. Lines may sit right at the board edge.
- Every connector has a ground; every audio or CV signal has a ground beside it; a supply pin has grounds on both
  sides; two kinds of signal never sit side by side without a ground between them *(guides: David Haillant, plenty of
  ground pins; Eddy Bergman, extra ground pins)*.

**The connectors.** Found by `pcb/tools/connector_search.py` once every other part was placed: it tries straight
runs of pin sites that are legal on both boards (clear of copper, of the jack/pot/LED bodies on the control front,
of the socket bodies and leads on the control back, and of the Seed3's socket strips) and minimises the orthogonal
distance from each signal's pin to its pads on both boards. `pcb/tools/sync_headers.py` put them on the board;
`python3 pcb/tools/doc_tables.py` prints this table.

| Header | Pins | Pin 1 (panel frame, mm) | Orientation (main side) | Pin order |
|---|---|---|---|---|
| JA1 / JB1 | 30 | (43.18, 25.4) | vertical, pin 1 at the top | OUT_R, GND, OUT_L, GND, IN_R, IN_L, GND, +3V3_A, GND, CV_BASE, GND, CV_WIDTH, GND, +12V, GND, POT_VOL, POT_MUX, GND, CV_HPRES, GND, CV_LPRES, GND, CV_SRR, GND, CV_EQF, GND, CV_DIST, GND, -12V, GND |
| JA2 / JB2 | 5 | (21.59, 57.15) | horizontal, pin 1 at the right | LED_A, MUX_A, MUX_C, MUX_B, GND |
| JA3 / JB3 | 2 | (64.77, 100.33) | horizontal, pin 1 at the left | CV_EQG, GND |

**Detail**
- **37 pins, 16 of them ground** (the old three headers had 38 and 17).
  - **J1 (30 pins)** runs down the channel between the right pot column and the CV jacks (panel x 43.18,
    y 25–99); on the main board it stands between the Seed3's socket rows. It carries the audio, the supplies,
    both pot signals and seven CVs, each CV with its own ground.
  - **J2 (5 pins, horizontal)** sits between the pot columns and carries the mux selects and the clip-LED drive.
  - **J3 (2 pins, horizontal)** sits at the right edge between two jack rows and carries CV EQ GAIN.
- **Hand-soldering clearance (d, 2026-10-07):** every header pad keeps at least 1.25 mm (edge to edge) from every
  other pad on both boards and from the whole box around each jack, pot and LED, so there is room for the iron and
  no bridge to a pot or jack leg. The first search had put a connector 1.7 mm from pot RV5's snap-in tab, inside
  the pot's box, and another in the 3 mm gap between two CV jacks; both are gone. The control board's own
  through-hole parts keep the same 1.25 mm between pads.
- **Hand soldering.** JB1's pins come out on the main board's back between the Seed3's socket rows, under the module:
  solder JB1 before the Seed3 sockets and trim the pins flush; the Seed sits 8.5 mm up on its sockets.
- **Orientation.** JAn on the back is turned 180° from JBn (KiCad flips back-side parts top-to-bottom); the tools
  check that every pin k of JAn sits on pin k of JBn.
- **Current:** the ±12 V pins feed only U7/U8 and their LEDs (under 50 mA each way), and +3V3_A feeds only the pots
  and U6. One 2.54 mm pin each is ample.

---

## 8. Power entry chain (main board)

**Rules**
- The power header is the deepest part of the module, so put it where it clears the case *(guide: Ed Random)*.
- Put plenty of ground connections at power connectors *(guide: David Haillant)*.
- Put the bulk caps right after the protection diodes, before the rails go anywhere *(general practice)*.

**Placement**
- **+12 V chain, in order and touching:** J13 pins 9/10 → FB1 → D10 → C1 (10u) and C2 (100u).
- **−12 V chain, in order and touching:** J13 pins 1/2 (red stripe) → FB2 → D11 → C3 (10u) and C4 (100u).
- **J13 ground pins 3–8** each get a via into the ground pour, at the header.
- **Seed3 supply filter:**
  - +12V → R1 (3.3 Ω) → C5 → R2 (3.3 Ω) → C6 → Seed3 pin 39 (VIN).
  - Put C6 at pin 39. With the Seed3's USB end down, pin 39 is near the bottom edge, so this chain sits there.
  - This keeps R1/R2 (they run slightly warm) about 30 mm from the 1V/OCT group.
- In the floorplan, J13 sits at the top-left of the main board, and its filter parts sit beside it.

---

## 9. Block placement (both boards)

**Rules**
- Group each circuit block, route it, then arrange the blocks *(guide: The2dCour)*.
- Signal flow runs input → output *(guide: trevortjes)*.
- Digital lines stay local and away from analog *(guide: The2dCour, keep clocks local)*.

**Main board** (`floorplan-main.png`)
- **Seed3:** vertical, USB end at the bottom edge, socket rows at x 14.57 and 29.81 (left of centre).
  - The codec pins 16–19 (left row) and the ADC pins 22–32 (right row) are at the Seed's upper end.
  - USB 36/37 and VIN 39 are at the bottom.
  - JB1 stands between the socket rows (section 7).
- **U3/U4 (audio):** left of the Seed3, beside the codec pins.
- **U2 then U1 (CV ADC):** right of the Seed3, between the ADC pins and JB2. U5 sits just above U2.
- **J13 and the power chain:** top-left. **J14:** bottom, right of the Seed's USB end, near USB 36/37.
- **J15 (microSD, DNP):** right of JB2, at about (48, 90). That's far from SDMMC pins 2–7 (the Seed's left row, bottom end): about 255 mm of trace over the six lines, roughly 40 mm each. There's no room for the socket left of the Seed. SD at the default clock tolerates this; the layout can move J15 nearer (below U1, say) if room appears. Turn it so the card slot opens toward the right edge.
- The top-right of the main board is spare room.

**Control board** (`floorplan-control.png`)
- **Front, fixed by the panel:** the pots (two columns plus VOLUME), the audio jacks top-right, and the CV jacks in two columns below them.
- **Back:**
  - U6 between the two pot columns.
  - U7 and U8 by the CV jacks.
  - The through-hole R/C beside their chips.
  - JA1 and JA3 in the channel between the pot columns (above and below U6), JA2 between the right pot column and the CV jacks.
- Through-hole leads come out on the front, so no R/C may sit under a jack or pot body. The floorplan enforces this.
- The audio jacks (top right) are about 40 mm from JA1. Those are low-impedance jack-level lines, so the length is fine; keep them clear of U6's select lines.

---

## 10. Pot multiplexer and pots (control board)

**Rules**
- Put the multiplexer where its eight inputs are short, so only one wire runs back to the Seed3 *(general practice)*.
- Keep the digital select lines away from the analog lines *(guide: The2dCour)*.

**Placement**
- **U6** sits on the back between the two pot columns, long axis vertical.
  - **Left column** goes down one side, to pins 15, 14, 13, 12: RV2 (BASE), RV4 (HP RES), RV6 (EQ FREQ), RV8 (DIST).
  - **Right column** goes down the other side, to pins 1, 2, 4, 5: RV3 (WIDTH), RV5 (LP RES), RV7 (EQ GAIN), RV9 (SMPL RATE).
  - Mind the back-side mirroring when you turn U6.
- **U6 pin 3 (POT_MUX)** runs to JA1 pin 16, then on the main board from JB1 pin 16 to Seed3 pin 31.
- **MUX_A/B/C** (U6 pins 11/10/9) run to JA3 pins 4/2/3. On the main board they go from JB3 to Seed3 pins 8/9/10.
- **RV1 (VOLUME)** wiper runs to JA1 pin 8, then from JB1 pin 8 to Seed3 pin 28.
- **C80** at pin 16. Pins 6, 7, 8 to GND.

**Detail:** the firmware's channel table is select 0–7 = EQ FREQ, HP RES, BASE, DIST, WIDTH, SMPL RATE, LP RES, EQ GAIN (`docs/firmware-changes.md`; `python machine_filter.py` prints it).

---

## 11. Digital odds and ends: clip LED, expansion header, microSD

**Rules:** keep digital and fast lines short and at the digital end of the Seed3 *(guide: The2dCour)*.

- **R70 (1k)** sits at Seed3 pin 12 (main board). LED_A runs from R70 to JB3 pin 1, then on the control board from JA3 pin 1 to **D1** (the clip LED). Keep it away from U3/U4 and −10V_REF.
- **J14 (expansion 2×4)** sits by the Seed3's USB end. Route USB_DP and USB_DM side by side as a pair, from pins 36/37.
- **MIDI_TX/RX** leave Seed3 pins 14/15 (USART1) and run to J14. Pins 14/15 sit next to the codec pins 16–19: keep the MIDI traces off the U3/U4 side and on the other layer where they pass the codec lines.
- **J15 (microSD, optional):** the six SDMMC lines (pins 2–7) run short and direct to the socket, CK (pin 7) kept away from the others where possible; the 47k pull-ups R100–R104 sit by the Seed pins, C100 at the socket's VDD pin. The socket is DNP by default; its footprint and traces are always there.
- J14's ground pins 1, 3 and 8 each get a via at the header *(guide: David Haillant)*.
