# settling_analysis — R1 raw waveform forensics (loop_forensics)

Task `settling_analysis`, Round 1, QS30-9 24V power loop R2. **Analysis only.
ZERO simulations were run** (none permitted in Round 1 for this task). No circuit
component, no vendor model, no acceptance threshold and no existing branch was
modified. **60 ms is NOT qualified as settled.** This worker PASS would mean
"evidence delivered", never electrical acceptance.

## Evidence basis (all read-only, outside this output dir)

| item | location | sha256 |
|---|---|---|
| original full raw, 6 331 931 pts, 13 vars, 0→0.06 s | R1 `evidence/candidate_diagnostic/nominal_24V_gear_resource600/circuit.raw` | `d8b11ebedbb1125bbd968bdaf3a4c6e6f691e7dae1872cf76b6d8411e8d260ba` |
| netlist | same dir `circuit.cir` | hashed in `analysis.json` |
| controller model | `controller.sub` | `c03284243ac3b8e500e5bed3696deb8ebbde10eb8cb2a58b6e37929d9d18b634` |
| MOSFET model | `st.lib` (ST STP9NK50Z, level-3, 25 °C only) | `6ad61988b9e045684dc8271bc51ddfdca00d65b745e6edd6c4492a42df1ad7a4` |
| rectifier model | `diode.lib` (US1G, Thomatronik) | `f8669a85e8f3ed412ba97ab72bc6b7b0facbdf57111187ede39a365801324ec3` |
| clamp model | `ss14.lib` (SS14, Thomatronik) | `3288afb62761edfc9e9095127e92e5f9d0e52cd79c1ec948db82bec9ed1f8ae2` |

Reader: `lab.native()` (R2 shared helper, uncompressed-double memmap). Native
solver that produced the raw: **LTSpice, real double, forward, nocompression**,
`method=gear`, `.tran 2e-07 0.06 0 2e-07 uic`, reltol .001 / abstol 1n / vntol 1u
(unchanged source tolerances). The archived model bytes are exactly the R1 copies
and were not touched by this task.

`controller.sub` is stored in the R1 archive as a **“<Binary File>” placeholder
stub**, not decryptable LT3757A text. Its sha256 is recorded, and no conclusion
in this task rests on reading its internals.

## 1. Successive fixed 5 ms windows — time-weighted mean and TRUE raw Vpp

Mean is trapezoid time-weighted (interpolated endpoints, no sample dropped); Vpp
is the raw peak-to-peak of the samples actually inside the window. No smoothing,
no decimation, no filtering.

| window | time-weighted mean | true raw Vpp | min | max | arith − weighted |
|---|---:|---:|---:|---:|---:|
| 40–45 ms | 162.179 V | 6.571 V | 158.616 V | 165.187 V | 24.9 mV |
| 45–50 ms | 166.941 V | 5.789 V | 163.788 V | 169.577 V | 12.6 mV |
| 50–55 ms | **170.442 V** | 3.906 V | 168.172 V | **172.079 V** | 8.5 mV |
| 55–60 ms | **169.812 V** | **2.431 V** | 168.573 V | 171.004 V | 16.1 mV |

Reconciliation with R1: the 50–55 ms and 55–60 ms figures reproduce R1's
`settled_window_review.json` to <0.01 V, and the global peak 172.0787 V matches
`independent_metrics.json`. The 40–60 ms whole-window span (13.463 V) is **not a
ripple metric** — it spans the measured startup-band entry at 46.2019 ms, as R1
already stated.

### Is it settled? No.
* A 10 mV band is used *only* to test that question (it is not an acceptance
  threshold): the trace leaves ±10 mV of its own 50–60 ms mean **at the very last
  sample (0.060 s)** — zero margin to the end of the record.
* Successive window means are **-629.6 mV** apart (50–55 → 55–60 ms), i.e. the
  mean is still moving and reverses sign relative to the 45–50 → 50–55 ramp
  (+3.50 V). A monotonic settling tail is contradicted.
* Even the quietest 2 ms bin (58–60 ms) has 1.474 V raw Vpp, ~150× the 10 mV band.

Verdict: **NOT_SETTLED_IN_OBSERVED_60MS**. No settling time is claimed.

## 2. FFT on uniformly resampled data

* Native samples are **not uniform** (adaptive solver, dt from 1e-17 s to the
  2e-7 s max step; mean rate ≈ 105 kHz). Any FFT therefore requires an
  interpolation step, which is a documented smearing/alias source.
* Resample: linear onto a uniform grid at **fs = 20 MHz**, **Nyquist = 10 MHz**.
  Consequence: envelope content below 1 kHz is resolved; switching content above
  10 MHz (e.g. V(drain) 171.6 V edges) is **aliased and NOT resolved**.
* Window: **Hann**, amplitude-corrected by 1/Σw. Detrend: **mean subtraction**
  (DC removed). Bin ≈ 200 Hz for the 5 ms windows.
* Limit of resolution: the 5 ms window resolves structure down to ~200 Hz; a
  slower trend below that is absorbed into the window mean, so the FFT is *not*
  a substitute for the trend test in §1.

Dominant non-DC components (amplitude, Vpp-equivalent), each 5 ms window:
40–45 ms: 200 Hz 2.467 V, 400 Hz 0.548 V, 600 Hz 0.137 V;
45–50 ms: 200 Hz 2.091 V, 400 Hz 0.465 V, 600 Hz 0.116 V;
50–55 ms: 200 Hz 2.549 V, 400 Hz 1.545 V, 600 Hz 0.515 V;
55–60 ms: 200 Hz 2.170 V, 400 Hz 1.223 V, 600 Hz 0.111 V.
Bands: 60–140 kHz (switching) amplitude ≤ 13.4 mV; 1–60 kHz ≤ 41.8 mV.

Interpretation: the content is **envelope at 200–600 Hz**, not a
switching-frequency limit cycle. This is consistent with the 1.5–2.5 V lobe width
and the ~630 mV/5 ms drift.

**Self-correction (recorded, not hidden):** a first draft computed the frequency
axis from a recomputed span expression and produced `nyquist=0.0025 Hz` with
empty peak lists. That erroneous intermediate is preserved in
`analysis.json → fft_selfcheck`, was used for no conclusion, and the corrected
axis is validated (Nyquist = fs/2, bin = fs/N, peaks populated — all true for
all four windows).

## 3. Load and switching, from the actual raw

Derived from measured V(out), V(in), I(LPOWER), V(gate)−V(src):

* Effective load R = 5200 Ω ∥ 45.45 kΩ (two bleed strings) ∥ 201.9 kΩ (FB) =
  **4560.74 Ω**; at measured V(out) ≈ 169.83 V this is **6.324 W / 37.24 mA**,
  versus the corrected budget 5.900 W / 33.70 mA at 175.1 V.
* Switching frequency **100.846 kHz** (median), period jitter 18.9 ns pp.
* Measured duty **0.272**, I_L mean 0.271 A, I_L raw min **-0.171 A**,
  I_L raw max 1.166 A over 55–60 ms.

## 4. Mode and topology caveat — the CCM RHP zero is NOT applied

The CCM boost RHP zero `(1−D)²R/(2πL)` requires D near the R1 ideal boost
estimate (0.845–0.873). The **measured** duty is 0.272 and the measured inductor
current goes negative, so that formula is outside its validity here. It is
recorded as `f_RHP_zero_CCM_formula_Hz = 2.56 MHz` **only** to show what happens
when the formula is fed measured numbers, flagged `RHP_applicable: false`, and
**not used as a plant zero or as compensation evidence**. R1 independently
reported 882/1134 late cycles with an inductor-current zero crossing, i.e. DCM
operation, where the control-to-output transfer has no RHP zero.
Actual topology/conduction mode: **INCONCLUSIVE** from this offline pass.

## 5. Current-mode averaged output pole and existing compensation

* Output pole (constant-power / input-side RC form, R1's own derivation)
  `fp = 1/(πRC) = 1/(π·4560.74·20.3µ) = **3.44 Hz**`; the passive RC pole
  `1/(2πRC) = 1.72 Hz`. This is a derivation only — no Bode run, no margins, and
  it is **not** a validated mode-resolved current-mode plant.
* Existing compensation: RCOMP 22 k, CCOMP 6.8 n → zero at **1.064 kHz**;
  CHF 100 p → pole ≈ 398 kHz; RT 140 k.

**Compensation recommendation: none. No value is proposed and
`recommendation_values_justified = false`.** Rationale: the observed residual is
a slow 200–600 Hz envelope drift, not a fast limit cycle near 100.85 kHz; the
estimated output pole (~3.4 Hz) is far below the existing 1.06 kHz zero, so the
chain is not demonstrated to be mis-compensated. Equally, nothing here proves it
adequate. Keep 22k/6.8n/100p/140k unchanged and **measure before editing**.

## 6. Recommended further observation (proposed only, not executed)

Recommend **one unchanged 200 ms observation** in a later round under principal
approval: `lab.full(stop=0.2)` via the shared helper, identical models,
tolerances and the same 200 ns max step, preregistered through `lab.execute`.
Justification (§1): the 10 mV-band excursion reaches the end of the record, the
mean still drifts −630 mV per 5 ms, and the dominant 200–600 Hz lobe is not shown
to have decayed. A crude single-exponential probe gives τ ≈ 6.25 ms, but the sign
change between windows breaks the monotonic assumption, so **no 200 ms outcome is
predicted and no settling time is extrapolated**. Cost caveat: R1 took ≈287 s for
60 ms at 200 ns max step; a 200 ms stop is ≈3.3× and must be budgeted by the
principal.

## Files in this directory

| file | content |
|---|---|
| `analysis.py` | the analysis script (no simulation, read-only on repository evidence) |
| `analysis.json` | all measured values, FFT tables, self-correction record, assertions |
| `inventory.md` | this document |
| `result.json` | machine-readable result (evidence delivery only) |

## Open / not proven

* Conduction mode and actual power-stage topology at 170 V.
* Gain margin / phase margin: never measured (no Bode/loop-gain run exists).
* Whether the 200–600 Hz envelope decays, persists or is a sustained instability.
* Physical ripple on hardware: the 20 MHz-instrument-band limitation from R1
  still applies; these are solver-trace values.
* Electrical acceptance: **unchanged, still failing** (SENSE exceeds the
  LT3757A ±0.3 V absolute rating; raw Vpp ≫ 1 V). All HOLD remain.
