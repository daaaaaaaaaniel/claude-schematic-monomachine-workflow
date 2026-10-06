#!/usr/bin/env bash
# Install KiCad 10 (official PPA) and SKiDL (in a venv); optionally build ngspice 47 (CLI + shared library).
#
# Target: a disposable Ubuntu 24.04 (noble) x86_64 environment with root, such as Claude's
# cloud workspace. NOT meant for d's Mac. See docs/toolchain.md for the why behind each step.
#
# Idempotent: steps whose result is already present are skipped.
#   WITH_NGSPICE=1 also build ngspice (~9 min; only needed for simulation, not for the schematic/PCB flow)
#   SK_VENV=...    SKiDL's venv (default /opt/sk; tools/build.sh uses $SK_VENV/bin/python)
#   FORCE_BUILD=1  rebuild ngspice even if ngspice-47 is already installed
#   BUILD_DIR=...  where sources are cloned/built (default /opt/src)
#   NGSPICE_TAG=…  git tag to build (default ngspice-47)
set -euo pipefail

NGSPICE_TAG="${NGSPICE_TAG:-ngspice-47}"
NGSPICE_REPO="https://github.com/imr/ngspice.git"   # GitHub mirror; SourceForge is not reachable from the sandbox
BUILD_DIR="${BUILD_DIR:-/opt/src}"
FORCE_BUILD="${FORCE_BUILD:-0}"
KICAD_PPA="kicad/kicad-10.0-releases"
KICAD_KEY_FPR_EXPECTED="FDA854F61C4D0D9572BB95E5245D5502FAD7A805"  # Launchpad PPA for KiCad, checked 2026-10-02
CONFIGURE_FLAGS=(--with-x=no --enable-xspice --enable-cider --enable-osdi --disable-debug)

export DEBIAN_FRONTEND=noninteractive
SUDO=""; [ "$(id -u)" -eq 0 ] || SUDO="sudo"
log() { printf '\n== %s\n' "$*"; }

# ---------------------------------------------------------------- KiCad 10
if dpkg -s kicad 2>/dev/null | grep -q '^Version: 10\.'; then
  log "KiCad $(dpkg -s kicad | awk '/^Version/{print $2}') already installed — skipping"
else
  log "Adding KiCad 10 PPA"
  . /etc/os-release
  FPR=$(curl -fsS "https://api.launchpad.net/1.0/~${KICAD_PPA%%/*}/+archive/ubuntu/${KICAD_PPA##*/}" \
        | python3 -c "import json,sys;print(json.load(sys.stdin)['signing_key_fingerprint'])")
  if [ "$FPR" != "$KICAD_KEY_FPR_EXPECTED" ]; then
    echo "PPA signing key changed: got $FPR, expected $KICAD_KEY_FPR_EXPECTED — verify before trusting" >&2
    exit 1
  fi
  curl -fsS "https://keyserver.ubuntu.com/pks/lookup?op=get&options=mr&search=0x$FPR" \
    | gpg --dearmor | $SUDO tee /usr/share/keyrings/kicad-10.gpg >/dev/null
  echo "deb [signed-by=/usr/share/keyrings/kicad-10.gpg] https://ppa.launchpadcontent.net/${KICAD_PPA}/ubuntu ${VERSION_CODENAME} main" \
    | $SUDO tee /etc/apt/sources.list.d/kicad-10.list >/dev/null
  $SUDO apt-get update -qq || true      # unrelated broken sources (e.g. docker) only warn
  log "Installing KiCad 10 (no 3D model package: it is several GB and not needed for simulation)"
  $SUDO apt-get install -y -qq --no-install-recommends kicad kicad-symbols kicad-footprints
fi

# ---------------------------------------------------------------- KiCad global library tables
# kicad-cli resolves the stock libraries through the user's global tables; a fresh container has none, and ERC
# then reports every stock symbol as "library not in the configuration".
KCFG="$HOME/.config/kicad/10.0"
if [ ! -f "$KCFG/sym-lib-table" ]; then
  log "Installing KiCad's default global library tables"
  mkdir -p "$KCFG"
  cp /usr/share/kicad/template/sym-lib-table /usr/share/kicad/template/fp-lib-table "$KCFG/"
fi

# ---------------------------------------------------------------- floorplan dependencies (design/floorplan.py)
if ! python3 -c "import numpy, scipy, matplotlib" 2>/dev/null; then
  log "Installing numpy, scipy, matplotlib for design/floorplan.py"
  $SUDO apt-get install -y -qq --no-install-recommends python3-numpy python3-scipy python3-matplotlib
fi

# ---------------------------------------------------------------- SKiDL
# In a venv: on Ubuntu 24.04's Python 3.13, a plain `pip install --break-system-packages skidl` fails building
# its kinet2pcb / hierplace dependencies (Debian's patched setuptools: "AttributeError: install_layout").
SK_VENV="${SK_VENV:-/opt/sk}"
if "$SK_VENV/bin/python" -c "import skidl" 2>/dev/null; then
  log "SKiDL $("$SK_VENV/bin/python" -c 'import skidl; print(skidl.__version__)' 2>/dev/null) already installed — skipping"
else
  log "Installing SKiDL into $SK_VENV"
  python3 -m venv "$SK_VENV"
  "$SK_VENV/bin/pip" install -q --upgrade pip setuptools wheel
  "$SK_VENV/bin/pip" install -q skidl
fi

# ---------------------------------------------------------------- KiKit (tools/separate.sh)
# Its own venv, for the same setuptools reason, but with --system-site-packages: KiKit needs KiCad's pcbnew module.
KK_VENV="${KK_VENV:-/opt/kikit}"
if "$KK_VENV/bin/kikit" --version >/dev/null 2>&1; then
  log "KiKit already installed — skipping"
else
  log "Installing KiKit into $KK_VENV"
  python3 -m venv --system-site-packages "$KK_VENV"
  "$KK_VENV/bin/pip" install -q --upgrade pip setuptools wheel
  "$KK_VENV/bin/pip" install -q kikit
fi

if [ "${WITH_NGSPICE:-0}" != 1 ]; then
  log "Skipping ngspice (WITH_NGSPICE=1 to build it)"
  echo "kicad-cli:  $(kicad-cli version)"
  echo "skidl:      $("$SK_VENV/bin/python" -c 'import skidl; print(skidl.__version__)' 2>/dev/null)"
  echo "kikit:      $("$KK_VENV/bin/kikit" --version 2>/dev/null | tail -1)"
  exit 0
fi

# ---------------------------------------------------------------- ngspice build deps
log "Installing ngspice build dependencies"
$SUDO apt-get install -y -qq build-essential autoconf automake libtool bison flex \
  libreadline-dev libfftw3-dev git >/dev/null

have_cli()    { /usr/local/bin/ngspice -v 2>/dev/null | grep -q "${NGSPICE_TAG} "; }
have_shared() { [ -e /usr/local/lib/libngspice.so.0 ] && strings /usr/local/lib/libngspice.so.0 | grep -q "${NGSPICE_TAG}"; }

if [ "$FORCE_BUILD" != 1 ] && have_cli && have_shared; then
  log "${NGSPICE_TAG} CLI and shared library already installed — skipping build"
else
  $SUDO mkdir -p "$BUILD_DIR"; $SUDO chown "$(id -u):$(id -g)" "$BUILD_DIR"
  SRC="$BUILD_DIR/ngspice"
  [ -d "$SRC/.git" ] || git clone -q "$NGSPICE_REPO" "$SRC"
  git -C "$SRC" fetch -q --tags
  git -C "$SRC" rev-parse -q --verify "refs/tags/${NGSPICE_TAG}" >/dev/null \
    || { echo "tag ${NGSPICE_TAG} not found in mirror" >&2; exit 1; }

  # Two separate checkouts: an in-tree ./configure blocks out-of-tree builds from the same tree,
  # and the CLI and the shared library need different configure flags.
  build() {  # $1 = checkout dir, $2.. = extra configure flags
    local dir="$1"; shift
    [ -d "$dir" ] || git -C "$SRC" worktree add -q --detach "$dir" "${NGSPICE_TAG}"
    git -C "$dir" checkout -q --detach "${NGSPICE_TAG}"
    ( cd "$dir"
      [ -f Makefile ] && make -s distclean >/dev/null 2>&1 || true
      ./autogen.sh >/dev/null 2>&1
      ./configure "${CONFIGURE_FLAGS[@]}" "$@" >/dev/null
      make -s -j"$(nproc)" >/dev/null 2>&1
      $SUDO make -s install >/dev/null )
  }
  log "Building ngspice CLI (${NGSPICE_TAG})";            build "$BUILD_DIR/ngspice-cli"
  log "Building ngspice shared library (${NGSPICE_TAG})"; build "$BUILD_DIR/ngspice-shared" --with-ngshared
  $SUDO ldconfig
fi

# ---------------------------------------------------------------- verify (end to end)
log "Verifying"
hash -r
echo "kicad-cli:  $(kicad-cli version)"
echo "ngspice:    $(ngspice -v | grep -o 'ngspice-[0-9.]*' | head -1)  ($(command -v ngspice))"
echo "libngspice: $(ldconfig -p | awk '/libngspice.so.0 /{print $NF; exit}')"

T=$(mktemp -d)
cat > "$T/rc.cir" <<'EOF'
RC step: v(out) at t = RC must be 5*(1-1/e) = 3.1606 V
V1 in 0 PULSE(0 5 0 1n 1n 10m 20m)
R1 in out 10k
C1 out 0 100n
.tran 10u 5m
.control
run
meas tran vtau find v(out) at=1m
.endc
.end
EOF
ngspice -b "$T/rc.cir" 2>&1 | grep -E '^vtau'

# Load the shared library exactly the way KiCad does: dlopen("libngspice.so.0").
cat > "$T/sh.c" <<'EOF'
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
typedef int (*SC)(char*,int,void*); typedef int (*SS)(char*,int,void*);
typedef int (*CE)(int,bool,bool,int,void*);
typedef int (*Init)(SC,SS,CE,void*,void*,void*,void*); typedef int (*Cmd)(char*);
static int pc(char*s,int i,void*u){ if(strstr(s,"** ngspice-")||strstr(s,"v(out)")) printf("  %s\n",s+7); return 0; }
static int ps(char*s,int i,void*u){ return 0; }
static int ex(int a,bool b,bool c,int d,void*u){ return 0; }
int main(void){
  void*h=dlopen("libngspice.so.0",RTLD_NOW); if(!h){ printf("dlopen failed: %s\n",dlerror()); return 1; }
  Dl_info i; dladdr(dlsym(h,"ngSpice_Init"),&i); printf("  dlopen(libngspice.so.0) -> %s\n",i.dli_fname);
  ((Init)dlsym(h,"ngSpice_Init"))(pc,ps,ex,NULL,NULL,NULL,NULL);
  Cmd c=(Cmd)dlsym(h,"ngSpice_Command");
  c("version -f");
  c("circbyline xspice gain check (expect 2.5)"); c("circbyline V1 in 0 1"); c("circbyline a1 in out amp");
  c("circbyline .model amp gain(gain=2.5)"); c("circbyline R1 out 0 1k"); c("circbyline .op"); c("circbyline .end");
  c("run"); c("print v(out)"); return 0; }
EOF
gcc -o "$T/sh" "$T/sh.c" -ldl && "$T/sh"
rm -rf "$T"
log "Done"
