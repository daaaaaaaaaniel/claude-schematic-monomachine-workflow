# Toolchain: KiCad 10 + ngspice 47

How the simulation toolchain for this repo is installed, and why each step is the way it is.
Recorded 2026-10-02.

**Where it runs:** Claude's cloud workspace — a disposable Ubuntu 24.04 (noble) x86_64 container
with root. **Not on d's Mac** (d's decision). The container is reclaimed after inactivity, so the
toolchain has to be reinstalled in each new workspace:

```bash
tools/setup-toolchain.sh          # ~9 min on 2 cores, almost all of it the two ngspice builds
```

The script is idempotent (skips what is already installed) and ends with an end-to-end check.
`FORCE_BUILD=1` rebuilds ngspice; `NGSPICE_TAG=ngspice-48` picks another tag.

## What gets installed

| Component | Version | Source | Location |
|---|---|---|---|
| KiCad (+ symbols, footprints) | 10.0.6 | official PPA `kicad/kicad-10.0-releases` | `/usr/bin`, `/usr/share/kicad` |
| ngspice CLI | 47 (tag `ngspice-47`, `a80f6e3`, 2026-08-11) | GitHub mirror `imr/ngspice`, built from source | `/usr/local/bin/ngspice` |
| libngspice (shared) | 47 | same, built with `--with-ngshared` | `/usr/local/lib/libngspice.so.0` |
| ngspice code models / scripts | 47 | same | `/usr/local/lib/ngspice/*.cm`, `/usr/local/share/ngspice/scripts/spinit` |

Ubuntu's own `ngspice` / `libngspice0` 42 also get installed (KiCad depends on them). They stay in
`/usr/bin` and `/lib/x86_64-linux-gnu` and are shadowed by the 47 builds (see "Which ngspice wins").

## Step by step

### 1. KiCad 10 from the official PPA

`add-apt-repository` is not used: the sandbox's proxy blocks plain-HTTP `ppa.launchpad.net`, but
allows `https://ppa.launchpadcontent.net`, `api.launchpad.net` and `keyserver.ubuntu.com`. So the
source is added by hand with a pinned key:

```bash
FPR=$(curl -s https://api.launchpad.net/1.0/~kicad/+archive/ubuntu/kicad-10.0-releases \
      | python3 -c "import json,sys;print(json.load(sys.stdin)['signing_key_fingerprint'])")
# expect FDA854F61C4D0D9572BB95E5245D5502FAD7A805 ("Launchpad PPA for KiCad")
curl -s "https://keyserver.ubuntu.com/pks/lookup?op=get&options=mr&search=0x$FPR" \
  | gpg --dearmor > /usr/share/keyrings/kicad-10.gpg
echo "deb [signed-by=/usr/share/keyrings/kicad-10.gpg] https://ppa.launchpadcontent.net/kicad/kicad-10.0-releases/ubuntu noble main" \
  > /etc/apt/sources.list.d/kicad-10.list
apt-get update
apt-get install -y --no-install-recommends kicad kicad-symbols kicad-footprints
```

`--no-install-recommends` skips `kicad-packages3d` (several GB of 3D models, useless for simulation).
`apt-get update` may warn about an unrelated docker source the proxy refuses; that's harmless.

### 2. ngspice 47 CLI

SourceForge (ngspice's home) is not reachable from the sandbox; the GitHub mirror is.

```bash
apt-get install -y build-essential autoconf automake libtool bison flex libreadline-dev libfftw3-dev
git clone https://github.com/imr/ngspice.git && cd ngspice
git checkout ngspice-47
./autogen.sh && ./configure --with-x=no --enable-xspice --enable-cider --enable-osdi --disable-debug
make -j$(nproc) && make install
```

### 3. ngspice 47 shared library (for KiCad's simulator)

KiCad does not run the `ngspice` executable; it `dlopen`s `libngspice.so.0`. The CLI build above
doesn't produce that, so a second build with `--with-ngshared` is needed. It must be a **separate
checkout**: once `./configure` has run in a tree, configure refuses out-of-tree builds from it
("source directory already configured"). A git worktree is the cheapest separate checkout:

```bash
git -C ngspice worktree add --detach ../ngspice-shared ngspice-47
cd ../ngspice-shared
./autogen.sh && ./configure --with-ngshared --with-x=no --enable-xspice --enable-cider --enable-osdi --disable-debug
make -j$(nproc) && make install && ldconfig
```

### Which ngspice wins

- **CLI:** `/usr/local/bin` precedes `/usr/bin` on `PATH` → `ngspice` is 47.
- **Library:** `ldconfig` lists `/usr/local/lib` before `/lib/x86_64-linux-gnu`, so
  `dlopen("libngspice.so.0")` — the exact call KiCad 10 makes on Linux (string in
  `/usr/bin/_eeschema.kiface`) — resolves to 47. Verified by a small C program that dlopens it
  and prints `** ngspice-47 shared library` (it's in `tools/setup-toolchain.sh`).
- **Code models:** KiCad's extra code-model search paths are relative to `/usr/bin`
  (`../lib/ngspice`, …) and don't exist here, so it does not pull in 42's `.cm` files; ngspice 47's
  own `spinit` loads 47's from `/usr/local/lib/ngspice`.

## Verification (what "working" means)

1. `kicad-cli version` → `10.0.6`
2. `ngspice -v` → `ngspice-47`
3. RC step (10 kΩ, 100 nF, 5 V): `v(out)` at t = RC = `3.16060` V; hand value 5·(1−e⁻¹) = 3.1606 V.
4. XSPICE code model (`gain`, 2.5×) through the shared library → `v(out) = 2.5`.

## Limits and open items

- **KiCad's GUI simulator has not been exercised** — the workspace has no display, and `kicad-cli`
  10 has no simulate command (`sch` offers only `erc`, `export`, `upgrade`). Library resolution is
  verified (above); a GUI run is not. Simulations here run as ngspice netlists; KiCad is used for
  netlist/BOM export (`kicad-cli sch export netlist --format kicadxml|spice`).
- `--enable-osdi` lets ngspice load compiled Verilog-A models, but the compiler (OpenVAF) is not
  installed.
- Build time is ~9 min on the 2-core workspace (measured 2026-10-02).
- The script's KiCad-install branch was run by hand on 2026-10-02 but has only been exercised by the
  script in its "already installed" form; the ngspice branch was run in full by the script
  (`FORCE_BUILD=1`, fresh build dir).

## Added 2026-10-06: SKiDL and kicad-cli library tables

- **SKiDL 2.3.0** is installed into a venv at `/opt/sk` by `pcb/tools/setup-toolchain.sh`. A system-wide
  `pip install --break-system-packages skidl` fails on noble's Python 3.13: its dependencies `kinet2pcb` and
  `hierplace` don't build with Debian's patched setuptools (`AttributeError: install_layout`). A venv with a
  current setuptools builds them fine.
- **kicad-cli needs global library tables.** In a fresh container `~/.config/kicad/10.0/` has no `sym-lib-table`
  or `fp-lib-table`, and ERC then flags every stock symbol as "not in the current configuration". The setup script
  copies KiCad's defaults from `/usr/share/kicad/template/`. The project's own library is registered in each
  project's `sym-lib-table` and `fp-lib-table` (`pcb/machine-filter/`;
  `${KIPRJMOD}/../lib/…`).
- **ngspice** is now optional (`WITH_NGSPICE=1`); the schematic and PCB flow doesn't need it.

## Added 2026-10-06 (later): two boards, floorplan

- `pcb/design/floorplan.py` uses KiCad's `pcbnew` Python module (installed with KiCad) plus numpy, scipy and
  matplotlib from the system Python (`apt install python3-numpy python3-scipy python3-matplotlib` if missing).
  It runs in about 2 minutes. `build.sh` skips it unless `FLOORPLAN=1`. Its output, `design/pinmap.py`, is
  committed, so the rest of the build doesn't need it.
- pcbnew pitfalls: a footprint loaded with `FootprintLoad` must be added to a `BOARD()` before its geometry is
  queried, or pcbnew segfaults. Pad sizes come from `GetBoundingBox()`; `GetSize(layer)` also segfaulted here.
- **KiKit 1.8.1** is installed into its own venv at `/opt/kikit` with `--system-site-packages`. It needs KiCad's `pcbnew`
  module, and a plain pip install hits the same setuptools failure as SKiDL. `kikit separate` imports `wx` even with
  no display. On this container `python3` is 3.13 while Ubuntu's wxPython is built for 3.12, so the import fails.
  `pcb/tools/separate.sh` then puts `pcb/tools/wxstub/` (an empty `wx` module) on `PYTHONPATH`: with no `DISPLAY`,
  KiKit does nothing else with wx. On a desktop with KiCad's own Python (macOS, Windows), install KiKit into KiCad's
  Python instead, and no stand-in is needed.

## Tried 2026-10-06 and 2026-10-07: atopile (not adopted)

d asked to try [atopile](https://github.com/atopile/atopile) (PyPI `atopile`) on the `pcb-second-placement` branch.
Test design: `explore/atopile-trial/`.
- **0.12.6** (the newest release that installs on Python 3.13) refuses to run: "atopile 0.12 is retired and can no
  longer run commands. Move to app.atopile.io (0.16+)."
- **0.15.9** (the newest on PyPI, Sept 2026; the last classic CLI; needs Python 3.14: `uv venv --python 3.14`) runs.
  - **Part picking needs sign-in**, a browser OAuth flow against `clerk.atopile.io`; picking calls
    `gateway.atopile.io`. Neither server is reachable from the cloud container.
  - **Works offline with pre-picked parts.** Parts declared as atomic parts (local `.kicad_mod` + `.kicad_sym`, a fixed
    LCSC number via `has_part_picked`) skip the picker. The build then completes with no network access. It writes a
    `.kicad_pcb` with the footprints and nets, and a BOM with LCSC numbers.
  - **Blocker: it targets KiCad 9, and this project is KiCad 10.** atopile 0.15.9 writes and reads KiCad 9 files
    (format 20241229). Once KiCad 10 saves the board (format 20260206), the next `ato build` fails to parse it
    ("UnexpectedType in kicad.pcb.Layer field 'tenting'"). Layout edits made in KiCad 10 can't go back through atopile.
    Using it would mean moving the whole project back to KiCad 9. KiCad 10 files don't open in 9.
  - The classic CLI ends at 0.15.x; new development is the browser workspace (app.atopile.io, 0.16+), so a KiCad 10
    fix for the CLI is unlikely.
- **Fit, apart from the blockers:** atopile would mean re-describing the whole circuit in `.ato`, a third source of
  connectivity beside SKiDL and `boards.py`, after the schematic was declared done. Its designators are assigned
  automatically (R1, C1, …), not the schematic's. The feature that would help this layout most, laying out one CV
  channel and repeating it, is also in KiCad 10 itself (multichannel layout tools), with no rewrite.
