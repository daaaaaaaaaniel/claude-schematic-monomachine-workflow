# Placement workflow (agreed with d, 2026-10-06)

How the PCB layout is being done, why, and how to run it in a fresh cloud session. Read this before touching the
PCB. The post-mortem that led here is in `HANDOFF.md`.

## 1. Where things stand

| Step | What | Status |
|---|---|---|
| 1 | Footprints in the PCB, sorted into function groups beside the boards; area budget; zone sketch | done |
| 2 | Seed3 placed with its group; first trace (VIN pin 39 → C6) | done |
| 3 | U2 with its CV group (BASE, HP RES, LP RES, EQ FREQ), right of the ADC pins, pin 1 level with Seed3 pin 23; trace: U2 pin 1 (BASE out) → Seed3 pin 23, straight, 3 mm | done |
| 4 | U1 with its CV group below U2; ADC pins re-matched to the placed chips (`tools/rematch_adc.py`; d: keep it); trace: U1 pin 1 (WIDTH out) → Seed3 pin 29, straight, 3 mm | done |
| 5 | U3, U4 (audio) left of the Seed3, by the codec pins 16–19; traces: Seed3 pin 16 → R52, pin 18 → R60 (the codec lines pass through series resistors; there is no direct Seed3–op-amp pin pair) | done |
| 6 | U5 (−10 V ref) at the right edge beside the CV groups, not under the Seed3 (8 offset lines would cross the socket row); trace U5 → R28 | done |
| 7 | J13 power entry (bottom left, sideways), J15 microSD (left middle), J14 (bottom right), each as one packed block; trace J13 → FB1 | done |
| 8 | All eight CV op-amp outputs → Seed3 ADC pins (4 on the back, 4 via the front) | done |
| 9 | Control board panel parts (12 jacks, 9 pots, 9 LEDs) at their fixed panel positions, front | done |
| 10 | Headers (main front + control back, same panel spot, clear of the panel parts) | **next** |
| 11 | U6, U7, U8 as blocks on the control board's back; standoffs | later (d: main board first) |

Round-one flags for d (`pcb/out/round1-main-board.png`):
- the J15 and J14 critical traces were drawn and deleted: their last leg ran along the connector's own pin row
  (DRC shorts); they need a deliberate route;
- R70 (Seed3 group) overlaps R100 (microSD block): minor parts, for the minor-parts round;
- U5 is not where the zone sketch put it (see step 6).

Branch: `pcb-first-placement`. Pictures: `pcb/out/zone-sketch.png`, `pcb/out/step1-groups-kicad.png`,
`pcb/out/step2-seed3-kicad.png`, `pcb/out/step3-u2-kicad.png`, `pcb/out/step3-u2-closeup.png`, `pcb/out/step4-u1-closeup.png`, `pcb/out/step5-audio-closeup.png`.
DRC after step 3: no courtyard or clearance problems; only reference labels overlapping on silkscreen (tidy at the
end), and 17 footprints flagged as differing from their library copies (pre-existing; check before fabrication).

## 2. The method (d)

1. **Groups first, off the board.**
   - Every part belongs to one function group around one *primary* part (`pcb/design/groups.py`).
   - Parts that must sit close to the primary are its *secondaries*: decoupling, the parts at an op-amp section's
     − input, the protection chain at the power header.
   - The remaining small parts join the group whose primary they connect to.
   - Within a function, groups are balanced: each CV quad carries four channels and one 1V/OCT input, and audio in
     and audio out have 11 parts each.
2. **Area budget and zones, before anything goes on a board.**
   - Each group gets an area estimate: courtyards × 2.5 for routing on 2 layers (a rule of thumb).
   - Each group gets a zone: quiet (CV, audio, the reference) or noisy (power entry, microSD, USB/MIDI, the Seed's
     supply).
   - The goal: noisy currents never flow under quiet parts. See `pcb/out/zone-sketch.png`.
3. **One primary at a time, most consequential first.** Place it in its zone, a general area rather than an exact
   spot, and bring its group with it.
4. **Draw its critical trace**: the one connection that matters most for that group (e.g. VIN pin → C6, the BASE
   op-amp output → its ADC pin). It proves the shortest important path exists.
5. **Stop for d's review** after each step or batch, with one picture of the board and its ratsnest.
6. Then, in order:
   - the small parts inside each group (by `docs/placement-guide.md`, decoupling first);
   - power routing; ground pours; the rest of the routing;
   - the headers, last, with their pin order set to suit the routing; rebuild the schematic;
   - DRC; an autorouter run (Freerouting) as a routability test; gerbers.

**How to judge a placement:** the ratsnest. KiCad draws a thin straight line for every connection still to be made.
- Good: short lines running the same general way.
- Bad: long lines across the board, crossing bundles, many lines squeezing through one gap, a decoupling capacitor
  far from its pin.

**Scope of a placement step (d, 2026-10-06):** place the primary with its group in a general area, and draw its
critical trace. Resistors and other small parts are not arranged until every primary and secondary part is placed:
no fine-tuning of passives during these steps. (Step 5 overdid it: the codec resistors were lined up level with
their Seed3 pins after a first trace crossed a resistor's other pad.)

**How a group goes onto the board (d, 2026-10-06):** like dragging and dropping the whole group in one gesture.
The group's cluster, as staged beside the board, moves as one block (its parts keep their positions relative to
each other) so that the primary lands where it should; on the back side the block is mirrored with it. No
part-by-part arranging: minor parts (resistors, small capacitors) are sorted out only after every primary and
secondary part is on the board. The one deliberate placement in a step: when the critical trace passes through a
minor part, that one part is put where the trace needs it, and the report says so with the screenshot, e.g.
"critical trace would be U4 to the Seed3, but it needs R60, placed provisionally". d gives feedback on where it
should go. Steps 2-5 arranged their groups part by part, before this rule; they stay as they are.

**Routing rules (d, 2026-10-06):**
- Horizontal and vertical segments only; no diagonals.
- Layer convention (community guide, routing §): front mostly horizontal, back mostly vertical. Short hops inside a
  group go whichever way they need.
- A minor part (resistor or capacitor that isn't a secondary part) counts as absent until one of its pads has a
  trace on its own net (d): ignore its pads and courtyard while routing; those parts move later.
  `tools/drc_summary.py` runs DRC and lists clashes with such parts separately from real problems.
- Pending: four dangling vias (from the first ADC routing, at the op-amp pins' level, x 58.8) to delete in the
  editor (Konnect has no via delete; KiCad: Tracks > Cleanup Tracks & Vias, or select and Delete).

## 3. Placement order (d agreed)

1. **Seed3.** Its area is set by d's USB rule.
2. **U2, then U1.** They carry the CV lines into the ADC, including the pitch inputs, where a millivolt at the ADC is
   audible. With WIDTH moved to U1, they tie.
3. **U3 and U4.** The codec lines.
4. **U5.** It feeds every CV stage; it sits under the Seed between the socket rows.
5. **J13 power entry.** It has to stay away from the audio.
6. **J15 microSD and J14 expansion.** Optional; they fill the remaining room.
7. **The board-to-board headers.** Last: in the schematic they are just wires with a part number.
8. **Standoffs.** Optional (d): M3 holes at the same panel position on both boards; board-only parts H1–H4 and
   H11–H14.

## 4. Decisions and constraints from d (2026-10-06)

| Topic | Decision |
|---|---|
| Layers | Both boards are **2-layer**. The 4-layer plan was for the single-board module. The PCB file is set to 2. |
| Seed3 position | USB end down, the USB socket at least 25 mm inside the control board's edge. Pin 1 at panel (33.615, 89.49). |
| Cables | **Not a constraint.** The power ribbon and USB cable are long and flexible; only connector bodies (J13's shroud with its plug, the USB plug) must not collide. |
| Case depth | **Not a factor** in this exercise. |
| Pin map | Follows the layout. `pinmap.py` is edited to match the PCB, then rebuilt (`build.sh` without `FLOORPLAN=1`). |
| Pitch channels | WIDTH moved to U1 section D (EQ FREQ to U2 D), so each quad has one 1V/OCT input. |
| Process | Transparency: before a run, say what it changes and how long it takes; report results in mm or plain units, with pictures; no long opaque searches. |

## 5. Tools: KiCad 10 GUI + Konnect in the cloud container

Konnect (github.com/mixelpixx/Konnect, v0.13) is an MCP server that edits the board open in KiCad's PCB editor
through KiCad 10's IPC API. KiCad's own operations do the work, and each change is one undo step.

**Setup in a fresh container (about 15 min, mostly the build):**

```bash
pcb/tools/setup-toolchain.sh                          # KiCad 10.0.6 (GUI + kicad-cli + pcbnew Python), SKiDL
apt-get install -y protobuf-compiler libprotobuf-dev xdotool
git clone --depth 1 https://github.com/mixelpixx/Konnect.git /tmp/Konnect
cd /tmp/Konnect && RUSTUP_TOOLCHAIN=stable cargo build --release -p konnect    # ~10 min
cp target/release/konnect /usr/local/bin/
# enable KiCad's API server: ~/.config/kicad/10.0/kicad_common.json -> "api": {"enable_server": true}
Xvfb :99 -screen 0 1920x1200x24 &
cd pcb/machine-filter && DISPLAY=:99 pcbnew machine-filter.kicad_pcb &
# first-run "Welcome" dialog: click Cancel, then Yes (xdotool); the socket appears at /tmp/kicad/api.sock
```

- Konnect's release downloads are blocked by the container's proxy, so it is built from source. Rust's pinned
  1.96 toolchain can't be downloaded either; the installed stable toolchain works (`RUSTUP_TOOLCHAIN=stable`).
- 3D view: `apt-get install kicad-packages3d` (280 MB download, 3.3 GB; not in setup-toolchain.sh), then
  `KICAD10_3DMODEL_DIR=/usr/share/kicad/3dmodels kicad-cli pcb render <pcb> --side bottom --rotate "-35,0,30"
  --perspective --quality high -o out.png` (a few seconds). KiCad has no Daisy Seed model (the footprint's model path
  points at a file KiCad doesn't ship), and the microSD socket has none, so both render flat.
- Pictures without the GUI: `kicad-cli pcb export svg <pcb> --layers B.Cu,B.Silkscreen,B.Courtyard,Edge.Cuts
  --mode-single --fit-page-to-board` takes about 0.5 s; no ratsnest. Use the GUI only when the ratsnest matters.
- Screenshot: `DISPLAY=:99 import -window root shot.png`. Ctrl+Home zooms to all objects; scroll (xdotool click 4)
  zooms in at the mouse.

**Scripts (in `pcb/tools/`):**

| Script | What it does |
|---|---|
| `konnect_call.py` | Minimal MCP stdio client. Loads the toolsets and keeps Konnect's log at warn. `call <tool> '<json>'` runs one call. |
| `konnect_stage.py` | Step 1: places every part in its group cluster beside its board (from `out/stage-groups.json`, written by `design/stage_groups.py`), then adds the standoff holes and group labels. `PARTS_ONLY=1` moves just the parts. |
| `konnect_place.py <step>` | Applies one step from `design/placement.py`: sets positions in one undo step, flips parts to the back, **checks pad positions before drawing anything**, draws the step's traces (L-bend pad to pad), saves. |

**Rules Konnect insists on:**
- Board edits go through its tools, never text edits of `.kicad_pcb`.
- `update_pcb_from_schematic` is a dry run first; apply only with the returned `plan_revision`.
- On a conflict it changes nothing.

## 6. Gotchas found (each cost time once)

- **KiCad flips back-side parts top-to-bottom.** `floorplan.py` mirrored left-to-right. So a back-side part needs
  KiCad rotation = floorplan rotation + 180°. The Seed3 is rotation 0 in KiCad (180 in `floorplan.py`).
  `konnect_place.py` checks pads, which caught this.
- **Schematic IDs must be stable.** `gen_sch.py` used random UUIDs on every build, and KiCad links each footprint to
  its symbol by UUID path, so every rebuild would have cut all links. Now sheets and symbols get name-derived UUIDs:
  rebuilds are byte-identical, and Konnect's update reports `noop`. If links ever break again, Konnect's dry run
  reports `reference_identity_conflict` and changes nothing.
- **Footprint origin ≠ courtyard centre** for some footprints (the Seed3, the THT resistors). `stage_groups.py`
  offsets by the courtyard centre measured from the library (an early version added +100/+50 mm by mistake).
- **Clicking KiCad dialogs is fragile and token-expensive.** The Board Setup dialog widens when its page changes, so
  a remembered OK position hit Cancel. Use Konnect or scripts for edits. If a GUI dialog is unavoidable, screenshot
  before each click.
- **A multi-unit chip changes identity when its first unit moves to another schematic page** (the KiCad link uses
  that unit's sheet path). Konnect's update then refuses with `reference_identity_conflict` for that chip. Fix:
  `delete_component` the chip, run the update (it re-adds it), re-run its placement step. This happened to U1 when
  WIDTH (its unit A) moved to the CV 1–4 page.
  Considered and declined for now (d, 2026-10-06, "let's see if we regret it"): a separate flat one-page
  schematic, made for machines, for the PCB to link to, with the 12-page drawing kept for people only. It would
  end these identity changes for good; about 45 min plus one automated re-link of all parts. Revisit if they
  recur.
- **The ratsnest display comes back on after an update from the schematic.** Its toggle is the left-toolbar button at
  screen (322, 331); check the screenshot after clicking.
- **Scope (d):** say before each step what it will change. If that goes beyond the agreed step (e.g. the ADC
  re-match), wait for d's OK; announcing it is what let d catch it.
- **Flip first, then rotate.** `konnect_place.py` now sets a part's side before its position and rotation, so a
  step gives the same result however often it runs. (Rotating first and then flipping gave 180° different
  orientations on re-runs.) On the back at rotation 90, a 0603's pad 2 is the upper one.
- **Konnect's pad-to-pad route is an L-bend that ignores other pads.** Check DRC after drawing; a leg crossing a
  pad shows up as `shorting_items`.
- **Regenerating the PCB skeleton is blocked** (`pcb_skeleton.py --force`) as a destructive overwrite. Change board
  settings in place instead.

## 7. Cost (d asked; estimates, 2026-10-06)

- **Compute.**
  - KiCad's GUI uses about 1.8 GB of memory, near-zero CPU when idle; Xvfb about 90 MB.
  - A headless pcbnew script would use a few hundred MB, only while it runs.
  - Per-operation speed is the same: Konnect calls take 0.1–2 s.
- **Tokens (the cost that matters).**
  - A full-screen screenshot is about 3,000 tokens; a cropped one 1,000–1,500.
  - A filtered Konnect call is a few hundred tokens; an unfiltered one is far more (the full parts list is about
    10k tokens).
  - Clicking through a GUI dialog ran 10–15k tokens.
  - Practice: edits by Konnect or scripts, one cropped screenshot per step for d, no GUI navigation unless
    unavoidable. A placement step then costs a few thousand tokens.
- **Why keep the GUI:**
  - KiCad's own update from schematic (it caught the UUID problem safely);
  - one undo step per change;
  - pictures of KiCad's real view, ratsnest included.
