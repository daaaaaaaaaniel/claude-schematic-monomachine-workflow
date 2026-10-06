# atopile trial (2026-10-07)

A three-part test design (two 0603 resistors and a 0603 capacitor from `pcb/lib/`) used to test atopile 0.15.9
offline. See the "atopile" section of `docs/toolchain.md` for the findings.

Reproduce (cloud container):

```bash
uv venv --python 3.14 /opt/ato159 && VIRTUAL_ENV=/opt/ato159 uv pip install atopile==0.15.9
cd explore/atopile-trial && ATO_NON_INTERACTIVE=1 /opt/ato159/bin/ato build
```

The parts in `parts/` are "atomic parts" with a pre-picked LCSC number (`has_part_picked`), so the build never calls
atopile's part-picking service, which needs sign-in.
