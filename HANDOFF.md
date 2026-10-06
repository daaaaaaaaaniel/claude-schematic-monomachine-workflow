# MACHINE FILTER: handoff (rev beta schematic, two boards, 2026-10-06)

A 14HP Eurorack filter module built around an Electrosmith Daisy Seed3. This folder holds:
- the schematic source and the project library;
- the floorplan that sets the pin assignment;
- the build and check scripts;
- the notes needed to carry on toward the two PCBs in another session.

## State

| Stage | Status |
|---|---|
| Circuit (rev alpha) | audited against primary sources: `docs/design-review.md` |
| Construction | **two boards** (d, 2026-10-06): MAIN = JLC SMD assembly, ≤ 100 × 100 mm; CONTROL = hand-soldered (jacks, pots, LEDs; mux and LED drivers as SOIC; through-hole R/C) |
| Floorplan | feasibility level only: `pcb/design/floorplan.py` → `pcb/design/pinmap.py`, pictures in `pcb/out/floorplan-*.png`. Its header search is retired (see the post-mortem below) |
| KiCad project | **one** project, `pcb/machine-filter/` (KiKit multiboard workflow): one schematic for both boards, one PCB file with both outlines side by side |
| Schematic rev beta | done: `pcb/out/machine-filter.pdf` (12 pages: overview, main 2–7, control 8–12); ERC 0 |
| Source of truth for connectivity | `pcb/machine_filter.py` (SKiDL) |
| Readable drawings | `pcb/design/gen_sch.py` (draws from `boards.py`); checked identical to SKiDL by `tools/check_netlist.py` |
| BOM | one for the whole module: `pcb/out/bom.csv` (Board, Assembly and DNP columns); per-board BOMs come with `tools/separate.sh` |
| PCB file | outlines only: `pcb/machine-filter/machine-filter.kicad_pcb` (from `design/pcb_skeleton.py`); separation tested with KiKit |
| Fabrication | `tools/separate.sh` → `pcb/fab/main/`, `pcb/fab/control/` (separated board + BOM); gerbers and CPL **not yet** (after layout) |
| Placement plan | `docs/placement-guide.md` |
| PCB layout | **step 1 done** on branch `pcb-first-placement`: all 154 footprints are in the PCB file (Konnect, update from schematic), sorted into function groups beside their boards (`design/groups.py`, `design/stage_groups.py`, `tools/konnect_stage.py`), plus 8 optional standoff holes. Zone sketch: `pcb/out/zone-sketch.png` (`design/zone_sketch.py`). **Step 2 done:** the Seed3 at its USB-rule spot (back), its supply filter by VIN and R70 by pin 12, and the VIN pin 39 → C6 trace (`design/placement.py`, applied by `tools/konnect_place.py seed3`; picture `pcb/out/step2-seed3-kicad.png`). Note: KiCad flips back-side parts top-to-bottom, so their rotation is 180° off `floorplan.py`'s |
| Firmware | three table changes: `docs/firmware-changes.md` |

**Placement is under way: read `docs/placement-workflow.md` first** (method, d's decisions, KiCad + Konnect setup in the cloud, gotchas, costs, next step).

## Post-mortem (2026-10-06): the board-to-board headers were treated as a design driver. They aren't one.

**What happened.**
- **The headers became a gate on the schematic.** Splitting the module into two boards in one KiCad project put the
  board-to-board headers (JA1–JA3 / JB1–JB3) into the schematic, on their own connector pages. The build generates
  the schematic and the BOM in one pass from `pinmap.py`, so the schematic couldn't be finished until every header
  pin was decided.
- **The floorplan worked backwards.** It searched header layouts first (`design/headers.py`), then placed the Seed3
  to suit them, alternating. That was Claude's choice, not d's.
- **Hours went into comparing near-identical layouts.** They're in `explore/header-candidates/`.
  - The weighted trace totals differ by about 6%, and only on tolerant traces: jack-level CV and audio, pots,
    digital, power.
  - The traces that matter came out the same in every candidate: op-amp output → Seed3 ADC, and codec ↔ audio
    op-amp, each 9 mm or less.
  - Claude kept refining the score after the numbers showed this.

**Findings (d).**
- **In the schematic, the headers are just wires with a part number.** They matter for the BOM, not for the circuit.
- **In the layout, they come last.** The Seed3, the op-amps and the other major parts are placed first. The headers
  go where there's room, and their pin order is set to suit the routing.
- **The fixation came from coupling.** Schematic, BOM and header pin order are generated together, so the pin order
  looked like a prerequisite. Normal practice is a provisional pin order in the schematic, pin swaps during layout,
  then an update of the schematic.

**What still holds.**
- **The Seed3's area is set by d's USB rule.** The USB socket sits at least 25 mm inside the control board's edge,
  and the plug's path stays clear of tall parts (`USB_MIN`, `PLUG_W` in `design/floorplan.py`). That puts the Seed3
  right of centre, USB end down, with pin 1 near panel (33.6, 89). The three USB-rule runs (A2, B2, C2) agree
  within 1.3 mm. The schematic's `pinmap.SEED` (14.6, 110.9) predates the rule: don't use it.
- **The op-amps go beside the pins they serve.** U1/U2 sit beside the ADC pins, U3/U4 beside the codec pins 16–19.
  This is what keeps the sensitive traces short.
- **The headers still need a legal spot, checked at the end.**
  - Clear of the panel parts on the control board's front.
  - At the same position on both boards.
  - At least 5.08 mm from the Seed3's socket pins (room for an iron).
  - GND pins between audio pairs and between digital and analog lines.

**Direction.**
- **The header pin order in the schematic is provisional.** It's candidate A's. Don't run more header searches; the
  "pocket" rule isn't being pursued.
- **Place in order of importance, to a general area first, not an exact spot** (branch `pcb-first-placement`):
  1. the Seed3;
  2. U1/U2 and U3/U4, then U5;
  3. the power entry J13, the expansion header J14 and the microSD socket J15;
  4. the small parts, by `docs/placement-guide.md`;
  5. the headers, last.
- **Schematic IDs are stable** (2026-10-06): `gen_sch.py` derives every sheet and symbol UUID from its name, so a
  rebuild leaves the PCB's footprint links intact (Konnect's update from schematic reports nothing to do). Before
  this, each build made new random IDs, which would have cut every link.
- **Then match the schematic to the layout.**
  - Once the headers are placed, set their pin order in `pinmap.py` to suit the routing.
  - Set the ADC pins, the op-amp sections and the mux channels to suit where the parts actually landed.
  - Rebuild (`tools/build.sh`, about a minute) and refresh the doc tables (`tools/doc_tables.py`).
  - From here on, `pinmap.py` records decisions taken in the layout. It is no longer regenerated by
    `FLOORPLAN=1`, which would overwrite them.

## The two boards

- **MAIN** (70 × 100 mm, panel y 14–114; 2 layers, d 2026-10-06: the 4-layer plan was for the single-board module):
  - Back: Seed3 on sockets (USB end down, at least 25 mm inside the control board's edge: see the post-mortem), power entry J13, CV ADC stages U1/U2, audio U3/U4, the −10 V reference U5, expansion header J14, every SMD R/C.
  - Front: male headers JB1–JB3. The schematic has candidate A's provisional headers: JB1 15 pins, JB2 13 pins, JB3 10 pins. Their count, pin order and sites get settled after the major parts are placed.
- **CONTROL** (70 × 107 mm, the panel's board area; 2 layers):
  - Front: 12 jacks, 9 pots, 9 LEDs.
  - Back: pot mux U6, LED drivers U7/U8 (SOIC), through-hole R/C, female headers JA1–JA3.
- **Stack:** JAn plugs onto JBn, pin k to pin k, about 11 mm apart. Only robust signals cross: jack-level CV and audio, pot wipers, mux selects, clip-LED drive, and the supplies. In the provisional version, 17 of the 38 pins are ground. JB1 carries audio, POT_VOL, LED_A and ±12 V; JB2 the eight CVs; JB3 POT_MUX, the mux selects and +3V3_A.
- **Net names:** each board's nets are its own copper, so the control board's nets carry the prefix `CTL_` (`CTL_GND`, `CTL_+12V`, `CTL_CV_BASE`, …). `CTL_x` meets `x` only at JAn/JBn pin k. That's what lets one PCB file hold both boards without the design-rule check reporting every crossing net as unrouted. The cost: ERC can't see the header joins, so `tools/check_netlist.py` checks them.
- **Why LED drivers on CONTROL:** LED current stays off the main board's analog ground, the 1 MΩ inputs sit at the jacks, and they're hand-solderable.

## Rev beta changes from rev alpha

1. **The split:** the headers are added, and the control-board passives become through-hole (same values).
2. **Pin assignment from the floorplan:**
   - which Seed3 ADC pin each CV and pot uses;
   - which op-amp section each CV uses (U1/U2, U7/U8);
   - which 74HC4051 channel each pot uses.
   This keeps the short connections short and uncrossed. The firmware remaps them.
3. **Audio output ×5.1** instead of ×10, and 25 ppm/K offset resistors on the 1V/OCT inputs.
4. **An optional microSD socket** (DNP) on Seed3 pins 2–7. MIDI stays on pins 14/15, as rev alpha.

`tools/check_netlist.py` proves three things:
- each drawing equals its SKiDL netlist;
- the two boards joined through their headers equal the one-circuit netlist;
- every change from rev alpha is at an intended pin.

## Layout of this folder

```
HANDOFF.md                this file
CLAUDE.md                 working rules for agent sessions
pcb/
  machine_filter.py       SKiDL: THE source of truth for connectivity (BOARD=all|main|control)
  design/
    floorplan.py          places both boards with KiCad footprints (pcbnew), matches pins -> pinmap.py, pictures
    headers.py            board-to-board header search for floorplan.py (retired: see the post-mortem)
    geom.py               footprint geometry and occupancy grids for floorplan.py
    pinmap.py             header pins/positions, ADC pins, sections, mux channels, placements. First generated by
                          floorplan.py; from layout onward it is edited to match the PCB
    boards.py             parts and nets as data (with board = main/control); drives the drawing
    gen_sch.py            draws the hierarchical schematic (both boards) from boards.py
    pcb_skeleton.py       creates the PCB file with both outlines (once; refuses to overwrite); separation boxes
    kicadlib.py, sexpr.py helpers (KiCad library reader, s-expression read/write)
  lib/                    project library: filter-module.kicad_sym, filter-module.pretty, SOURCES.md (provenance)
  machine-filter/         THE KiCad 10 project: *.kicad_sch (generated, 12 pages), machine-filter.kicad_pcb (both boards),
                          .kicad_pro, sym-lib-table, fp-lib-table
  fab/                    made by tools/separate.sh: main/ and control/, each the separated board + its BOM
                          (later: + gerbers, drill, CPL)
  reference/              boards_rev_alpha.py: rev alpha, for the netlist comparison
  sim/                    ngspice checks of the audio, CV and LED stages, with models (README.md)
  tools/
    setup-toolchain.sh    KiCad 10, SKiDL (/opt/sk), KiKit (/opt/kikit), numpy/scipy/matplotlib; ngspice optional
    build.sh              (floorplan) → SKiDL netlists → drawings → ERC → checks → PDFs + BOMs
    check_netlist.py      the three checks above
    separate.sh           KiKit: cut each board out of the PCB file into fab/<board>/, plus per-board BOMs
    split_bom.py          whole-module BOM -> fab/main/bom.csv, fab/main/bom-jlc.csv (JLC upload), fab/control/bom.csv
    doc_tables.py         prints the ADC-pin, CV-stage and header tables for the docs from pinmap.py
    wxstub/               empty wx module so KiKit runs where wxPython won't import (see toolchain.md)
  out/                    logical/main/control.net, drawn.net, erc.rpt, machine-filter.pdf, bom.csv,
                          floorplan-main.png, floorplan-control.png
docs/
  placement-workflow.md   how the layout is done: method, order, d's decisions, KiCad + Konnect setup, gotchas, costs
  placement-guide.md      which part goes next to which, per board, by priority
  design-review.md        what was verified, open questions (audio levels, LED colour, stack height, …)
  firmware-changes.md     ADC pin table, mux table, MIDI UART
  community-pcb-layout-guide.md   layout advice from the Sourcery Studios #pcb-creation channel
  toolchain.md            how the toolchain is installed and why
explore/
  header-candidates/      the header layouts compared on 2026-10-06 (A-D, A2-C2), kept for reference (post-mortem)
```

## How to build (fresh Ubuntu 24.04 container)

```bash
pcb/tools/setup-toolchain.sh        # KiCad 10.0.x from the official PPA, SKiDL 2.3 in /opt/sk (~3 min)
pcb/tools/build.sh                  # must end with "OK"
FLOORPLAN=1 pcb/tools/build.sh      # also re-derive pinmap.py from the floorplan first (~2 min more)
```

## How to change things

- **The circuit:** edit **both** `pcb/machine_filter.py` and `pcb/design/boards.py`, then run `build.sh`.
  - The build fails unless the drawings and SKiDL agree exactly, the boards join to the logical circuit, and every change from rev alpha touches only the pins in `EXPECTED` (`tools/check_netlist.py`).
  - A deliberate new change means adding its pins to `EXPECTED`, with a comment saying why.
- **Pin assignment** (header pin order, ADC pins, op-amp sections, mux channels): from layout onward these follow the PCB.
  1. Edit `pinmap.py` to match the layout, then run `build.sh` without `FLOORPLAN=1`. Both `machine_filter.py` and `boards.py` read `pinmap.py`.
  2. Update `docs/firmware-changes.md` and `docs/placement-guide.md` from `tools/doc_tables.py`, and the `EXPECTED` pins in `tools/check_netlist.py`.
  3. Don't run `FLOORPLAN=1` once layout has started: it would overwrite those decisions.
- **Don't edit by hand:** `machine-filter/*.kicad_sch`, which `gen_sch.py` overwrites. The PCB file is the opposite: it's hand-edited (or script-edited) layout, and `pcb_skeleton.py` won't overwrite it.

**Why two sources:** SKiDL's own schematic generator (`--skidl-schematic`) fell back to a labels-only, unreadable drawing on this design. So SKiDL owns connectivity, `gen_sch.py` owns the drawing, and the netlist check holds them together.

## Next steps toward the PCBs

1. **Done (rev beta, second revision, 2026-10-06):** MIDI back to Seed3 pins 14/15; an optional microSD socket J15
   (DNP) on pins 2–7; audio output ×5.1 (R61/R65 51k, C60/C62 47p); R12/R16 25 ppm/K; BOM checked against JLC basic
   parts (TL072 and ferrites swapped to basic ones; see `docs/design-review.md`). Still open: stack height against
   the case, and the bicolour LED part (polarity, brightness at low CV).
2. **Bring the footprints into the PCB file.** In KiCad, open `pcb/machine-filter/` and run "Update PCB from schematic", or use a `pcbnew` script reading `out/drawn.net`.
3. **Place each part on its own board's outline** (the `Board` field says which), most important first. See the
   post-mortem: major parts go to a general area first, and the headers come last.
   - **Offsets:** KiCad (x, y) = panel (x, y) + `CONTROL_OFFSET` (100, 50) for the control board, or + `MAIN_OFFSET` (180, 50) for the main board (`design/pcb_skeleton.py`). `design/floorplan.py` used (100, 50) for both, so main-board positions from `pinmap.py` get +80 mm in x.
   - **Front parts** of the control board are fixed by the panel: they come from `boards.py` (`KNOB`, `CV_JACK`, `AUDIO_JACK`, `CV_LED`, `LED_XY`).
   - **Main board, in order:**
     1. the Seed3, in the area set by the USB rule. Don't use `pinmap.SEED`, which predates the rule.
     2. U1/U2 beside the ADC pins and U3/U4 beside the codec pins, then U5;
     3. J13, J14 and J15;
     4. the small parts, following `docs/placement-guide.md`: decoupling first, then each − input node.
   - **`pinmap.MAIN_PLACEMENT` / `CONTROL_PLACEMENT` are a rough guide at most.** They come from candidate A's floorplan, built around the old Seed3 position.
   - **Headers last:** a spot that's legal on both boards, then the pin order to suit the routing (see the post-mortem's last step).
4. **Both boards are 2-layer** (d, 2026-10-06); the PCB file is set to 2 copper layers. `design/pcb_skeleton.py` still creates 4 if it is ever re-run on an empty file: change `SetCopperLayerCount` first.
5. **Route, DRC** (`kicad-cli pcb drc`). Every component lives on one board, and no net spans both, so the DRC is meaningful as it stands.
6. **Fabrication outputs:**
   - Run `pcb/tools/separate.sh`. It cuts each board out with `kikit separate` into `pcb/fab/main/` and `pcb/fab/control/`, and writes their BOMs (`bom-jlc.csv` is JLC's upload format).
   - Then export gerbers, drill and CPL from each separated board: `kicad-cli pcb export gerbers`, `… drill`, `… pos` (CPL, main board only).
   - The Seed3 sockets, J13, J14 and JB1–JB3 are hand-soldered after assembly. If any header ends up between the Seed3's socket rows, solder it before the sockets.
7. **Firmware:** apply `docs/firmware-changes.md`.

## Tool notes

- **KiCad 10.0.6** (`kicad-cli`): ERC, netlist, PDF, BOM. kicad-cli needs global library tables in `~/.config/kicad/10.0/` (setup-toolchain.sh installs KiCad's defaults) and each project's own tables.
- **KiKit 1.8** in a venv at `/opt/kikit` (with system site-packages, for pcbnew): `kikit separate` for the multiboard split. On this container wxPython won't import under Python 3.13, so `separate.sh` puts an empty `wx` stand-in on the path. KiKit only needs `import wx` to succeed when there's no display.
- **pcbnew Python module** (ships with KiCad): used by `floorplan.py` and `pcb_skeleton.py`. A footprint must be added to a `BOARD()` before you query it, or pcbnew segfaults.
- **SKiDL 2.3.0** lives in a venv at `/opt/sk`, because a system-wide pip install fails on Ubuntu 24.04's Python 3.13. It runs one process per board, because SKiDL keeps one global circuit per process.
- **atopile** wasn't used: it doesn't produce a schematic and works best with its own parts ecosystem, not this project library. **Konnect** (KiCad MCP server, github.com/mixelpixx/Konnect, v0.13) drives the live PCB editor. In a cloud container:
  - Build it from source (`cargo build --release -p konnect`, about 10 min; needs `protobuf-compiler` and `libprotobuf-dev`). Release downloads are blocked by the proxy.
  - Run the GUI editor on a virtual display: `Xvfb :99 &`, then `DISPLAY=:99 pcbnew pcb/machine-filter/machine-filter.kicad_pcb`. Set `api.enable_server: true` in `~/.config/kicad/10.0/kicad_common.json` first. Dismiss the first-run dialog with `xdotool` (Cancel, then Yes). Screenshots: `DISPLAY=:99 import -window root shot.png`; Ctrl+Home zooms to all objects.
  - Call Konnect from scripts with `pcb/tools/konnect_call.py` (a small MCP stdio client). Konnect's rule: board edits go through its tools, never text edits of `.kicad_pcb`.
