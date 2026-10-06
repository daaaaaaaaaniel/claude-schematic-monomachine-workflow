# MACHINE FILTER: handoff (rev beta schematic, two boards, PCB placement started, 2026-10-06)

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
| Floorplan | done, feasibility level: `pcb/design/floorplan.py` → `pcb/design/pinmap.py`, pictures in `pcb/out/floorplan-*.png` |
| KiCad project | **one** project, `pcb/machine-filter/` (KiKit multiboard workflow): one schematic for both boards, one PCB file with both outlines side by side |
| Schematic rev beta | done: `pcb/out/machine-filter.pdf` (12 pages: overview, main 2–7, control 8–12); ERC 0 |
| Source of truth for connectivity | `pcb/machine_filter.py` (SKiDL) |
| Readable drawings | `pcb/design/gen_sch.py` (draws from `boards.py`); checked identical to SKiDL by `tools/check_netlist.py` |
| BOM | one for the whole module: `pcb/out/bom.csv` (Board, Assembly and DNP columns); per-board BOMs come with `tools/separate.sh` |
| PCB file | `pcb/machine-filter/machine-filter.kicad_pcb`: both outlines + all 154 footprints with nets, linked to the schematic (DRC schematic parity: clean). 54 at decided positions, 100 small passives parked below their board (`design/place_first.py`, run once). Picture: `pcb/out/pcb-placement.png` (`tools/render_pcb.py`) |
| Fabrication | `tools/separate.sh` → `pcb/fab/main/`, `pcb/fab/control/` (separated board + BOM); gerbers and CPL **not yet** (after layout) |
| Placement plan | `docs/placement-guide.md` |
| PCB layout | **step 1 done** (footprints in, fixed parts placed); next: place the parked passives, board by board |
| Firmware | three table changes: `docs/firmware-changes.md` |

## Status (2026-10-06, second session): schematic frozen, PCB work started

- **The schematic is done** (d: "100% done, with moderate confidence it stays that way"). Don't regenerate it to
  explore ideas. `FLOORPLAN=1` is off the table: it changes pin assignments and so the whole schematic.
- **Header layout is parked** (d: it doesn't matter until much more progress is made). The PCB uses candidate **A**
  as drawn (JB1/JB3 between the Seed3's socket rows; USB end ~5 mm from the main board's bottom edge, short of d's
  25 mm rule). Revisit it later as one deliberate change, not a search. The other candidates stay in
  `explore/header-candidates/` for reference.
- **Schematic uuids are now deterministic** (`gen_sch.py`: keyed by sheet file, reference, unit and pin). A rebuild
  with unchanged input gives byte-identical schematics, so the PCB's footprint-to-symbol links survive `build.sh`.
  (Before this, every build gave new random uuids, which would have orphaned every placed footprint.)
- **Work in small steps**, each one reviewed by d before the next.

## The two boards

- **MAIN** (70 × 100 mm, panel y 14–114; 4 layers recommended):
  - Back: Seed3 on sockets (USB end at the bottom edge), power entry J13, CV ADC stages U1/U2, audio U3/U4, the −10 V reference U5, expansion header J14, every SMD R/C.
  - Front: male headers JB1 (15 pins), JB2 (13 pins), JB3 (10 pins). JB1 and JB3 stand between the Seed3's socket rows, 7.5 mm from them; JB2 is right of the CV ADC stages.
- **CONTROL** (70 × 107 mm, the panel's board area; 2 layers):
  - Front: 12 jacks, 9 pots, 9 LEDs.
  - Back: pot mux U6, LED drivers U7/U8 (SOIC), through-hole R/C, female headers JA1–JA3.
- **Stack:** JAn plugs onto JBn, pin k to pin k, about 11 mm apart. Only robust signals cross: jack-level CV and audio, pot wipers, mux selects, clip-LED drive, and the supplies. 17 of the 38 pins are ground. JB1: audio, POT_VOL, LED_A, ±12 V. JB2: the eight CVs. JB3: POT_MUX, the mux selects, +3V3_A. The floorplan chose the grouping, the count (3 of 2–4 tried) and the sites (`design/headers.py`).
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
    headers.py            board-to-board header search for floorplan.py: groups, pin order, legal sites, best combination
    geom.py               footprint geometry and occupancy grids for floorplan.py
    pinmap.py             GENERATED by floorplan.py: header pins/positions, ADC pins, sections, mux channels, placements
    boards.py             parts and nets as data (with board = main/control); drives the drawing
    gen_sch.py            draws the hierarchical schematic (both boards) from boards.py
    pcb_skeleton.py       creates the PCB file with both outlines (once; refuses to overwrite); separation boxes
    place_first.py        brings every footprint into the PCB file, with nets and schematic links (once; refuses if footprints exist)
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
    render_pcb.py         picture of the PCB file for review -> out/pcb-placement.png
    wxstub/               empty wx module so KiKit runs where wxPython won't import (see toolchain.md)
  out/                    logical/main/control.net, drawn.net, erc.rpt, machine-filter.pdf, bom.csv,
                          floorplan-main.png, floorplan-control.png
docs/
  placement-guide.md      which part goes next to which, per board, by priority
  design-review.md        what was verified, open questions (audio levels, LED colour, stack height, …)
  firmware-changes.md     ADC pin table, mux table, MIDI UART
  community-pcb-layout-guide.md   layout advice from the Sourcery Studios #pcb-creation channel
  toolchain.md            how the toolchain is installed and why
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
- **Placement or pin assignment:** edit `design/floorplan.py` (its rules and fixed positions), then run `FLOORPLAN=1 build.sh`. Both `machine_filter.py` and `boards.py` read `pinmap.py`. Then update `docs/firmware-changes.md` from the new `pinmap.py`.
- **Don't edit by hand:** `machine-filter/*.kicad_sch` (`gen_sch.py` overwrites them) or `pinmap.py` (`floorplan.py` overwrites it). The PCB file is the opposite: it's hand-edited (or script-edited) layout, and `pcb_skeleton.py` won't overwrite it.

**Why two sources:** SKiDL's own schematic generator (`--skidl-schematic`) fell back to a labels-only, unreadable drawing on this design. So SKiDL owns connectivity, `gen_sch.py` owns the drawing, and the netlist check holds them together.

## Next steps toward the PCBs

1. **Done (rev beta, second revision, 2026-10-06):** MIDI back to Seed3 pins 14/15; an optional microSD socket J15
   (DNP) on pins 2–7; audio output ×5.1 (R61/R65 51k, C60/C62 47p); R12/R16 25 ppm/K; BOM checked against JLC basic
   parts (TL072 and ferrites swapped to basic ones; see `docs/design-review.md`). Still open: stack height against
   the case, and the bicolour LED part (polarity, brightness at low CV).
2. **Done (2026-10-06): footprints in the PCB file** (`design/place_first.py`, from `out/drawn.net`). Panel parts,
   headers, the Seed3, ICs, connectors and bulky capacitors are at their positions; the other 100 parts are parked
   below their board, one row per schematic page. Check: `kicad-cli pcb drc --schematic-parity` (only silkscreen
   warnings and unrouted connections). Later schematic edits come in with KiCad's "Update PCB from schematic".
3. **Place each part on its own board's outline** (the `Board` field says which).
   - **Offsets:** KiCad (x, y) = panel (x, y) + `CONTROL_OFFSET` (100, 50) for the control board, or + `MAIN_OFFSET` (180, 50) for the main board (`design/pcb_skeleton.py`). `design/floorplan.py` used (100, 50) for both, so main-board positions from `pinmap.py` get +80 mm in x.
   - **Front parts** come from `boards.py` (`KNOB`, `CV_JACK`, `AUDIO_JACK`, `CV_LED`, `LED_XY`).
   - **Headers** come from `pinmap.py` (`HEADER_POS` = pin-1 x, y, main-side rotation, control-side rotation; `HEADER_PINS` = pin order): the same panel position on both boards. The Seed3 comes from `pinmap.SEED`.
   - **ICs, connectors and bulky parts** start from `pinmap.MAIN_PLACEMENT` / `CONTROL_PLACEMENT` (footprint origin x, y, rotation; back-side parts flipped left-right). The floorplan doesn't place resistors, small capacitors or ferrite beads (d, 2026-10-06): place those by the placement guide.
   - Then refine following `docs/placement-guide.md`: decoupling first, then each − input node.
4. **One layer stack for both boards:** the file has 4 copper layers. Keep inner-layer copper (In1/In2 planes) inside the MAIN outline only. The control board can then be ordered as 2 layers by exporting just F.Cu/B.Cu for it. If you'd rather not manage that, make both boards 2-layer, or both 4-layer.
5. **Route, DRC** (`kicad-cli pcb drc`). Every component lives on one board, and no net spans both, so the DRC is meaningful as it stands.
6. **Fabrication outputs:**
   - Run `pcb/tools/separate.sh`. It cuts each board out with `kikit separate` into `pcb/fab/main/` and `pcb/fab/control/`, and writes their BOMs (`bom-jlc.csv` is JLC's upload format).
   - Then export gerbers, drill and CPL from each separated board: `kicad-cli pcb export gerbers`, `… drill`, `… pos` (CPL, main board only).
   - The Seed3 sockets, J13, J14 and JB1–JB3 are hand-soldered after assembly. Solder JB1 and JB3 before the Seed3 sockets: their pins sit between the socket rows.
7. **Firmware:** apply `docs/firmware-changes.md`.

## Tool notes

- **KiCad 10.0.6** (`kicad-cli`): ERC, netlist, PDF, BOM. kicad-cli needs global library tables in `~/.config/kicad/10.0/` (setup-toolchain.sh installs KiCad's defaults) and each project's own tables.
- **KiKit 1.8** in a venv at `/opt/kikit` (with system site-packages, for pcbnew): `kikit separate` for the multiboard split. On this container wxPython won't import under Python 3.13, so `separate.sh` puts an empty `wx` stand-in on the path. KiKit only needs `import wx` to succeed when there's no display.
- **pcbnew Python module** (ships with KiCad): used by `floorplan.py` and `pcb_skeleton.py`. A footprint must be added to a `BOARD()` before you query it, or pcbnew segfaults.
- **SKiDL 2.3.0** lives in a venv at `/opt/sk`, because a system-wide pip install fails on Ubuntu 24.04's Python 3.13. It runs one process per board, because SKiDL keeps one global circuit per process.
- **atopile** wasn't used: it doesn't produce a schematic and works best with its own parts ecosystem, not this project library. A trial on 2026-10-06 was blocked: the CLI now needs sign-in to atopile's servers, which the cloud container can't reach (`docs/toolchain.md`). **Konnect** (a KiCad MCP plugin) could drive interactive placement from a Claude session on a machine with KiCad's GUI.
