# Placement workflow (agreed with d, 2026-10-06)

How the PCB layout is being done, why, and how to run it in a fresh cloud session. Read this before touching the
PCB. The post-mortem that led here is in `HANDOFF.md`.

## 1. Where things stand

| Step | What | Status |
|---|---|---|
| 1 | Footprints in the PCB, sorted into function groups beside the boards; area budget; zone sketch | done |
| 2 | Seed3 placed with its group; first trace (VIN pin 39 → C6) | done |
| 3 | U2 with its CV group (BASE, HP RES, LP RES, EQ FREQ), right of the ADC pins; trace: BASE op-amp output → its ADC pin | **next** |
| 4… | U1; U3, U4; U5; J13; J15, J14; headers; standoffs (the order in §3) | to do |

Branch: `pcb-first-placement`. Pictures: `pcb/out/zone-sketch.png`, `pcb/out/step1-groups-kicad.png`,
`pcb/out/step2-seed3-kicad.png`.

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
