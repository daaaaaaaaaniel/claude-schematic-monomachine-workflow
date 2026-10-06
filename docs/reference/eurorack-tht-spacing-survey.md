# Component spacing near jacks and pots: THT vs SMD

Measured from 53 KiCad layouts (panels excluded) in three open-source Eurorack repos:
[Thorinair/Avalon-Harmonics](https://github.com/Thorinair/Avalon-Harmonics),
[QuinnFreedman/modular](https://github.com/QuinnFreedman/modular) and
[Allen-Synthesis/EuroPi](https://github.com/Allen-Synthesis/EuroPi). All the boards are 2-layer. The three repos are pooled.

## How it was measured

- **Outlines.** A jack or pot's outline is its footprint's drawn body outline: Fab layer where it exists, silkscreen otherwise. That comes to about 9 × 10.5 mm for Thonkiconn-style jacks and 9.5 × 11.3 mm for Alpha 9 mm pots. A resistor, capacitor, diode or IC's outline is its body outline plus its pads.
- **Which parts count.** Only parts within 5 mm of a jack or pot are included, so parts elsewhere on the board don't skew the figures.
- **"Same side"** means the part and the jack or pot are on the same face of the board.
- **"Opposite side"** means the part is on the back and the jack or pot is on the front. That is the control-board case.
  - A THT part's leads come through to the front and are soldered there, so the gap is measured from its pads to the jack or pot outline.
  - The jack or pot's pins come through to the back, so the gap is also measured from those pins to the part.
- **"Closest 10%"** means one part in ten sits closer than that figure. All distances are in mm.

## Results

| Situation | THT parts | SMD parts |
|---|---|---|
| **Same side as the jack:** part → jack outline | min 0.02, closest 10% 0.60, median 1.87 (n=40) | min 0.35, closest 10% 1.36, median 2.78 (n=20) |
| **Same side as the pot:** part → pot outline | min 0.89, closest 10% 0.89, median 2.41 (n=14) | min 0.56, closest 10% 1.36, median 2.45 (n=53) |
| **Opposite side:** part's leads → jack outline | min 0.05, closest 10% 0.10, median 0.60 (n=83) | doesn't apply (no leads come through) |
| **Opposite side:** part's leads → pot outline | min 0, closest 10% 0.57, median 2.45 (n=75) | doesn't apply |
| **Opposite side:** jack's solder pins → part | closest 10% 1.11, median 3.34 (n=83) | min 0.20, closest 10% 0.62, median 1.32 (n=123) |
| **Opposite side:** pot's solder pins → part | closest 10% 0.51, median 2.01 (n=75) | min 0.04, closest 10% 0.44, median 1.61 (n=152) |
| **Opposite side:** sits under the jack/pot outline? | 33 of 158 overlap the edge, at most 11% of the body; **none fully under** | 173 of 275 overlap; **106 fully under** |
| **Nearest neighbour of the same type:** body gap | closest 10% 0.54, median 0.69 (n=959) | closest 10% 0.55, median 0.99 (n=865) |
| **Nearest neighbour of the same type:** courtyard gap | closest 10% 0.02, median 0.18 | closest 10% 0.11, median 0.49 |

## What the data shows

- **THT parts on the back stop at the jack or pot's edge.** The leads are what limit them: lead holes go 0.1–0.6 mm outside the outline. The body may overhang the edge a little (at most 11% of its area). No THT part sits fully under a jack or pot.
- **SMD parts on the back go anywhere except onto the jack or pot's pins.** Most sit fully under a jack or pot. The only gap that matters is to its solder pins, about 0.4–0.6 mm for the closest 10%.
- **THT parts pack tighter than SMD.** Neighbouring courtyards touch or nearly touch (median 0.18 mm). Parallel 0207 resistors most often sit 3.17 mm apart (1/8 inch), with 3.05 and 3.81 mm next most common.
- **Standing resistors fit narrow gaps.** Vertically mounted 0207 resistors (2.54 mm lead spacing) are used to fill the 2–3 mm gutters between jack columns.

## Suggested rules for a THT control board (parts on the back, jacks and pots on the front)

1. **A back-side THT part's lead holes stay at least 1.0 mm outside any jack or pot outline.** The boards go as close as 0.1 mm, but then the iron touches the jack's plastic when you solder on the front. The 1.0 mm figure is a judgement for comfortable hand-soldering, not a measured value.
2. **A back-side THT part's body may overhang a jack or pot outline**, as long as its lead holes stay outside it (rule 1).
3. **A back-side THT part's body stays at least 0.5–1.0 mm from the jack or pot's own solder pins**, so you can still reach them with the iron. The data's closest 10% is 0.5–1.1 mm.
4. **Neighbouring THT parts may have touching courtyards.** Put parallel 0207 resistors at 3.17 mm pitch.
5. **On the panel side**, THT parts sit as close as about 0.6 mm from a jack body (courtyards touching), and about 0.9 mm from a pot.

These match the existing rule "no R/C may sit under a jack or pot body" when it is applied to lead holes. Rule 2 adds the overhang allowance.

## Limits

- Distances are to the drawn footprint outlines, not to measured part dimensions. Silkscreen outlines usually sit slightly outside the real body.
- Part heights weren't measured. Tall parts on the back of a stacked board need checking against the gap between the boards.