# ngspice checks (2026-10-06)

Run from this folder: `ngspice -b <file>.cir` (ngspice 42 from Ubuntu's apt; `setup-toolchain.sh` can also build
ngspice 47). `python3 plot.py` (after `plotdata.cir`, `audio_in.cir`, `cv_in2.cir`, `led.cir`) draws
`ngspice-checks.png`. Results are in `docs/design-review.md`, "ngspice checks".

| File | What it checks |
|---|---|
| `audio_out.cir`, `audio_out51.cir` | U4 output stage: clip points, frequency response, THD at 0 dBFS, for 39k/100p, 100k/33p (Dev Kit), 49.9k/47p, 51k/47p, 51k/68p |
| `audio_in.cir` | U3 input stage at ±12 V in; frequency response |
| `cv_in2.cir` | CV ADC stage with a behavioural LMV324 at TI's datasheet swing limits; also the − input voltage at ±12 V |
| `cv_in.cir`, `lmv_swing.cir` | the same with the National LMV324 macromodel, kept to show why it isn't used: it tops out at 2.5 V on a 3.3 V supply, which contradicts TI's datasheet (VCC − 0.1 V min) |
| `led.cir` | LM324 CV-LED driver: LED current vs CV, and the + input at −12 V CV |
| `mc1voct.cir` | 1V/OCT stage Monte Carlo (2000 runs, uniform within tolerance): scale and offset spread before calibration |
| `drift.cir` | worst-case temperature drift of the 1V/OCT stage, with and without a 25 ppm/K offset resistor |

**Models** (`models/`), from the KiCad-Spice-Library collection (github.com/kicad-spice-library, GPL-3.0 collection
of vendor models): `tl072.mod` and `lm324.mod` are TI's 1989 Boyle-type macromodels; `lmv324.mod` is National's.
Boyle macromodels reproduce gain, bandwidth and output swing roughly; they do **not** model input common-mode limits or
phase reversal, so they can't confirm or rule those out. Rails: ±11.7 V (Eurorack ±12 V minus the B5819W drops).
