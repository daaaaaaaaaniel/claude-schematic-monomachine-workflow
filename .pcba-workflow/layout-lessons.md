# Project layout lessons

<!-- PROJECT-LAYOUT-LESSONS -->
### passives-before-routing
- **Trigger:** routing a group
- **Rule:** freeze the placement of all its parts, minor ones included, before routing; arranging passives after critical traces caused repeated rework
- **Evidence:** U3/U4 codec resistors and the input resistors were re-placed several times (2026-10-06)
- **Check:** placement frozen in placement.py before routes

### l-bend-routes
- **Trigger:** drawing pad-to-pad routes
- **Rule:** Konnect route_pad_to_pad ignores other pads; route by explicit lanes and run DRC after each batch
- **Evidence:** codec and connector traces crossed neighbouring pads (2026-10-06)
- **Check:** drc_summary.py

### no-gui-typing
- **Trigger:** any edit through the KiCad GUI
- **Rule:** never type into the editor window; use Konnect or kicad-python; File > Revert to the last save if it happens
- **Evidence:** a missed click sent code to the board as hotkeys (2026-10-06)
- **Check:** manual

### orphan-vias
- **Trigger:** deleting or redrawing a routed net
- **Rule:** delete its vias too (kicad-python); KiCad re-nets an orphaned via to a pad it touches, which becomes a short
- **Evidence:** ADC vias became GND and -10V_REF and shorted new traces (2026-10-06)
- **Check:** drc_summary.py

### multi-unit-identity
- **Trigger:** moving an op-amp unit to another schematic page
- **Rule:** the chip footprint changes identity; delete it, update from schematic, re-place
- **Evidence:** U1 after the WIDTH re-match (2026-10-06): reference_identity_conflict
- **Check:** update_pcb_from_schematic dry run

### stable-schematic-uuids
- **Trigger:** rebuilding the generated schematic
- **Rule:** sheet and symbol UUIDs must be name-derived, or every rebuild cuts the PCB links
- **Evidence:** gen_sch.py used uuid4; fixed 2026-10-06; Konnect update reports noop after a rebuild
- **Check:** update_pcb_from_schematic dry run = noop

### kicad-back-flip
- **Trigger:** placing a part on the back side
- **Rule:** KiCad flips top-to-bottom; set the side first, then the rotation, and check a pad position before drawing anything
- **Evidence:** Seed3 came out upside down (2026-10-06); konnect_place.py pad check caught it
- **Check:** konnect_place.py check_pads


## lock-approved-blocks (2026-10-07)
Revisions stay small only if approved work can't drift. Approve per block, set KiCad's locked flag on its parts
(`lock_block.py`), commit, and check every candidate against the approved board (`check_locks.py`); reject
violations automatically instead of trusting the placer/router to honour locks.

## widen-then-drc (2026-10-07)
Widening traces to net-class widths can create clearance errors that the thin trace didn't have (the 1 mm J13–FB1
trace hit C2's pad). Re-run DRC after any width change and reroute the offender rather than narrowing the class.

## layer-convention-check (2026-10-07)
With every main-board SMD part on the back, every trace starts on the back, so horizontal runs drift onto the back
unless a via is planned. 23 of 49 segments broke "front horizontal, back vertical" before anyone counted. Through-hole
ends (Seed pins, J13, J14) can take the front directly with no via. Now measured: `off_convention_long` in
score_candidate.py (segments over 2.5 mm).
