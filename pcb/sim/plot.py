import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
B, O = "#2a78d6", "#eb6834"
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e6e5e0", "#fcfcfb"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": INK2, "axes.labelcolor": INK2, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.titlecolor": INK, "figure.facecolor": SURF, "axes.facecolor": SURF})
def load(f, cols=(0, 1)):
    d = np.loadtxt(f); return d[:, cols[0]], d[:, cols[1]]
fig, ax = plt.subplots(2, 2, figsize=(12, 8.5))
for a in ax.flat:
    a.grid(True, color=GRID, lw=0.8); [a.spines[s].set_visible(False) for s in ("top", "right")]
# 1 output stage transfer
a = ax[0, 0]
x, y = load("p_dc51.txt"); a.plot(x, y, color=B, lw=2, label="×5.05 (51k / 47p)")
x, y = load("p_dc100.txt"); a.plot(x, y, color=O, lw=2, label="×10 (100k / 33p, Dev Kit)")
for v in (-1.414, 1.414): a.axvline(v, color=INK2, ls="--", lw=1)
a.text(1.47, 9.0, "0 dBFS\n(1 Vrms)", color=INK2, fontsize=9)
a.set(title="Audio out (U4, TL072): output vs codec voltage", xlabel="codec output (V)", ylabel="jack (V)")
a.legend(frameon=False, loc="lower left")
a.text(-3.0, 4.4, "×10 clips\nat ±10.2 V\n(−2.8 dBFS)", color=INK2, fontsize=9)
# 2 frequency response
a = ax[0, 1]
f, g = load("p_ac51.txt"); a.semilogx(f, g - g[np.argmin(abs(f - 1e3))], color=B, lw=2, label="out, ×5.05 (51k / 47p)")
f, g = load("p_ac100.txt"); a.semilogx(f, g - g[np.argmin(abs(f - 1e3))], color=O, lw=2, label="out, ×10 (Dev Kit)")
f, g = load("acin.txt"); a.semilogx(f, g - g[np.argmin(abs(f - 1e3))], color="#1baf7a", lw=2, label="in, ×0.1 (100k / 10k ∥ 330p)")
a.axvline(20e3, color=INK2, ls="--", lw=1); a.text(21e3, -9.5, "20 kHz", color=INK2, fontsize=9)
a.set(title="Audio stages: frequency response (relative to 1 kHz)", xlabel="frequency (Hz)", ylabel="dB", ylim=(-12, 1.5), xlim=(10, 1e6))
a.legend(frameon=False, loc="lower left")
# 3 CV stage
a = ax[1, 0]
d = np.loadtxt("dccv2.txt"); x, adc, inv = d[:, 0], d[:, 1], d[:, 3]
a.axhspan(0, 3.3, color="#cde2fb", alpha=0.5, lw=0); a.text(-1.5, 3.4, "ADC range 0–3.3 V", color=INK2, fontsize=9)
a.plot(x, adc, color=B, lw=2, label="ADC pin")
a.plot(x, inv, color=O, lw=2, label="LMV324 − input")
a.axhline(-0.2, color=INK2, ls="--", lw=1); a.text(-7.5, -0.5, "−0.2 V: LMV324 input abs. max", color=INK2, fontsize=9)
for v in (-8, 8): a.axvline(v, color=INK2, ls=":", lw=1)
a.set(title="CV input (LMV324 on 3.3 V, datasheet-limited swing)", xlabel="CV at the jack (V)", ylabel="V", ylim=(-0.8, 3.6))
a.legend(frameon=False, loc="center left")
# 4 LED driver
a = ax[1, 1]
d = np.loadtxt("dcled.txt"); x, i = d[:, 0], d[:, 1] * 1e3
a.plot(x, i, color=B, lw=2)
a.axhline(0, color=INK2, lw=0.8)
a.text(1, -4.5, "green (+CV): levels off at 5.4 mA\nred (−CV): levels off at 6.6 mA\n0.5 V CV → 0.33 mA, 2 V → 1.3 mA", color=INK2, fontsize=9)
a.set(title="CV LED driver (LM324): LED current vs CV", xlabel="CV at the jack (V)", ylabel="LED current (mA)")
fig.suptitle("MACHINE FILTER: ngspice checks (TL072 / LM324: TI macromodels; LMV324: behavioural, TI datasheet limits)", color=INK, fontsize=11)
fig.tight_layout(rect=(0, 0, 1, 0.96))
fig.savefig("ngspice-checks.png", dpi=130)
