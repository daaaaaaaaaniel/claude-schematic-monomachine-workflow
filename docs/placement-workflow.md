# PCB layout workflow (rev 2026-10-07)

**The governing process is the `pcb-layout-review` skill** (d, 2026-10-07: it has primacy over the flow we built on
2026-10-06, which needed too much oversight). It is vendored in `.claude/skills/pcb-layout-review/` (MIT, from
Keitark/pcba-design-skills; see `VENDORED.md`), so it loads for any agent session in this repo. Read its `SKILL.md`
and references first. Its records live in `.pcba-workflow/`:
- `layout-review.json`: the review record (status, connectivity, DRC, placement and fanout gates, unresolved items);
- `layout-experiments.jsonl`: one line per experiment, written by the skill's `scripts/score_experiment.py`;
- `layout-lessons.md`: this project's lessons, written by the skill's `scripts/record_lesson.py`.

This document holds only what the skill can't know: d's decisions and constraints (§4), how to drive KiCad here
(§5), what went wrong before (§6, and the lessons file), costs (§7) and how the skill's steps map onto our tools (§8).
Where anything below conflicts with the skill, the skill wins.

## 1. Where things stand (2026-10-07)

Placement is **not frozen**. On the main board (back side): the Seed3, U1–U5, J13, J14, J15, the decoupling and
secondary parts (C6, C20, C21, C70–C73, C7, C100, the power-entry chain), and the ten CV input resistors are placed;
the 47 other minor parts are parked beside the board; the board-to-board headers, the control board's ICs and the
standoffs are not placed. Routed so far, all checked: the eight CV op-amp outputs to the ADC pins, the codec lines at
R52/R60, VIN to C6, USB D−/D+ to J14, U5 to R28, J13 to FB1, and the ten input-resistor links. DRC: 0 problems.
Best safe candidate: `explore/candidates/c01-parked` (metrics in its `metrics.json`).

History of the 2026-10-06 steps: git log of branch `pcb-first-placement` and the pictures in `pcb/out/`.

**What the skill changes about our earlier flow** (superseded, kept here so nobody revives them by accident):
- *Placing one primary at a time and drawing its critical trace before the rest is placed.* The skill freezes
  placement from the architecture first, including critical locality (decoupling, feedback, protection at their
  function), and only then routes. The traces already drawn stay as fixed routes unless an experiment shows they
  block something.
- *"A minor part doesn't exist until it has a trace."* Superseded: minor parts get placed at their function as part
  of the placement freeze, before routing. `drc_summary.py`'s ignore rule is only a convenience while they are
  parked.
- *Routing by hand-computed coordinates, trace by trace, with d reviewing each.* Remaining routing is done as measured
  experiments (Freerouting, or explicit lanes for a few nets), each scored against the best safe candidate.
- *"Groups as one block" and the fixed placement order.* Groups (`pcb/design/groups.py`) remain the architecture
  input, but placement follows the skill's review order, not our step list.

**Next, in the skill's order:**
1. *Establish truth:* record hashes, stackup (2 layers), net classes, raw and classified DRC, top/bottom renders.
   Decide with d the open constraints (net-class widths, ground strategy, header positions): the rules table d was
   sent on 2026-10-06 lists proposed defaults.
2. *Architecture placement, then critical locality:* place every remaining part (minor parts at their function,
   headers, control-board ICs, standoffs) and freeze placement.
3. *Layer and reference strategy, fanout:* ground fill and stitching on 2 layers; a legal escape for every power and
   GND pad.
4. *Routing* as experiments, *power and zones*, *manufacturing* (JLC limits), *independent visual pass*, release gate.

## 4. Decisions and constraints from d (2026-10-06)

| Topic | Decision |
|---|---|
| Layers | Both boards are **2-layer**. The 4-layer plan was for the single-board module. The PCB file is set to 2. |
| Seed3 position | USB end down, the USB socket at least 25 mm inside the control board's edge. Pin 1 at panel (33.615, 89.49). |
| Cables | **Not a constraint.** The power ribbon and USB cable are long and flexible; only connector bodies (J13's shroud with its plug, the USB plug) must not collide. |
| Case depth | **Not a factor** in this exercise. |
| Pin map | Follows the layout. `pinmap.py` is edited to match the PCB, then rebuilt (`build.sh` without `FLOORPLAN=1`). |
| Pitch channels | WIDTH moved to U1 section D (EQ FREQ to U2 D), so each quad has one 1V/OCT input. |
| Traces | Orthogonal only (no diagonals). **Front horizontal, back vertical**; pad escapes up to 2.5 mm are exempt (d, 2026-10-07). `score_candidate.py` counts diagonals and longer off-convention segments as hard failures. Ignore untraced minor-part pads while routing. |
| Standoffs | **None** (d, 2026-10-07: removed). The boards are held by the board-to-board headers and the panel. |
| Process | Transparency: before a run, say what it changes and how long it takes; report results in mm or plain units, with pictures; no long opaque searches. |

**Rules from the sources (accepted by d, 2026-10-07)** — community guide (`docs/community-pcb-layout-guide.md`
§3–4) and Eddy Bergman's KiCad tutorials (eddybergman.com, 2025/05 quick guide and 2025/10 part 2):
- *Ground:* no ground traces; a ground fill on both layers, stitched with vias but not overdone, "remove islands"
  on; any GND pad the fill can't reach gets a short track or via (both sources). Fill pieces should join each other,
  preferably along one path, to avoid ground loops (Bergman). Unfill before moving parts, refill and re-run DRC after.
- *Track widths:* signals at least 0.3 mm (community; our existing signal traces are 0.25 mm and would be widened
  where clearance allows); power 0.4–0.5 mm for an analog module (community) or 0.4–0.5 mm everywhere (Bergman's
  preference); power between connectors and through-hole parts 1 mm, narrowing to 0.5 mm at SMD pads (community).
- *Small passives on the fill:* keep the copper on both pads balanced (thermal reliefs) to avoid tombstoning.
- *Edges:* keep parts a few mm from the board edge (Bergman). U5's column currently sits about 0.4 mm from the right
  edge.
  **Exception (d, 2026-10-07): the board-to-board headers may sit right at the edge**; only the fab's copper-to-edge
  minimum applies to their pads.
- *Board-to-board connectors (d, 2026-10-07):* up to 4 straight lines, horizontal or vertical, each line **one
  header cut to length** (2 to 40 pins; d can buy 40-pin runs; butted 1×2/1×3 pieces would be equivalent in
  assembly, d: "do whichever one is easier to script", so one piece: stock KiCad footprints, no courtyard variant).
  Pin order is free (swap groups). Found by an exhaustive search over the legal straight runs once the other parts
  are placed.
  **Hand soldering (d, 2026-10-07):** header pads keep 1.25 mm (edge to edge) from every other pad on both boards
  and from the box around each jack, pot and LED; the control board's through-hole pads keep 1.25 mm from each other.
- *Board-to-board headers:* ~11 mm stack (Bergman's example matches ours); extra GND pins for solid ground and next
  to analog signals (both); put header pins under the points where force is applied (jacks, pots), so the boards
  don't seesaw or bend (Bergman). This gives the header placement a rule.
- *Initial placement:* arrange parts as the schematic draws them (Bergman uses KiCad's "Place by Schematic"
  plugin), then route.
- *Multi-board DRC:* Bergman warns DRC misreports across two boards in one file; this project avoids that with the
  `CTL_` net prefix (see HANDOFF.md).

In the board since 2026-10-07: net classes in `machine-filter.kicad_pro` (written with Konnect's `create_netclass` /
`assign_net_to_class`): **Default** (signals) 0.3 mm, clearance 0.2 mm, via 0.6/0.3 mm; **Power** 0.5 mm (GND, ±12V,
+3V3_A, +3V3_D, VIN and their `CTL_` twins); **PowerEntry** 1.0 mm, clearance 0.25 mm, via 0.8/0.4 mm (J13 → FB1/FB2 →
D10/D11: `Net-(FB1-Pad1)`, `Net-(FB2-Pad1)`, `Net-(D10-A)`, `Net-(D11-K)`). Router sizes 0.3/0.5/1.0 mm. -10V_REF stays a
signal (it carries almost no current). The existing traces were widened to their class; the 1 mm J13–FB1 trace then
crowded C2's pad, so it now leaves J13 pin 10 upward and runs straight into FB1 (DRC 0).

**Approval and locks (from d, 2026-10-07; advice from another session).** Revisions are incremental: d approves the
board one block (function group) at a time; `pcb/tools/lock_block.py <group>` sets KiCad's own locked flag on that
block's placed parts and the approval is committed, so git records what was approved. Every later candidate is checked
mechanically: `pcb/tools/check_locks.py HEAD` (or score_candidate.py, which runs it against the best candidate) rejects
any candidate that moved a locked part, without asking d. To revise an approved block, unlock only that block. Nothing
is locked yet: no block has been approved.

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
- Freerouting (autorouter, driven by Konnect's `route_specctra_dsn`): the jar can't be downloaded here (GitHub release
  and Maven downloads are blocked); d attached `freerouting-2.3.0.jar`, installed at `/opt/freerouting/freerouting.jar`.
  It needs Java 25 (`apt-get install openjdk-25-jre-headless`, then `update-alternatives --set java
  /usr/lib/jvm/java-25-openjdk-amd64/bin/java`). Konnect's `check_freerouting` (toolset `integration`) confirms it.
- After a session restart, Xvfb and the editor are gone (files survive): restart both as above; the first-run dialog
  comes back (Cancel, then Yes).
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
- **Back-side headers need the opposite rotation.** JAn (control, back) at JBn's rotation has its pins in reverse
  order after KiCad's flip; turn it 180° so pin k sits on pin k. `tools/rematch.py headers` checks every pair.
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

## 8. How the skill's steps map onto our tools

| Skill step | Tool here |
|---|---|
| Establish truth: hashes, DRC, connectivity | `sha256sum`; `pcb/tools/drc_summary.py`; `pcb/tools/score_candidate.py <name>` (also keeps a board copy in `explore/candidates/`) |
| Placement edits | `pcb/tools/konnect_place.py <step>` from `pcb/design/placement.py` (rotation chosen by pad position; pads checked before routing) |
| Routing experiments | Freerouting via Konnect (`export_specctra_dsn` → `route_specctra_dsn` → `plan_specctra_ses_import`/`apply_specctra_ses`), or explicit lanes in `placement.py` |
| Experiment ledger | `python3 .claude/skills/pcb-layout-review/scripts/score_experiment.py --ledger .pcba-workflow/layout-experiments.jsonl ...` with before/after counts from `score_candidate.py` (opens = unrouted between placed parts; real_drc; power_disconnects; layout_fails; manufacturing_defects) |
| Lessons | `python3 .claude/skills/pcb-layout-review/scripts/record_lesson.py --file .pcba-workflow/layout-lessons.md ...` |
| Renders | `kicad-cli pcb render` (3D, both sides), `kicad-cli pcb export svg` (layers); the GUI only when the ratsnest matters |
| Review record | `.pcba-workflow/layout-review.json` (status stays BLOCKED until every gate refers to the same saved board) |
