# loop_candidate — Round 2 corrected loop analysis (CODE ONLY)

Task `loop_candidate`, role `approved_loop_fix`, Round 2, QS30-9 24 V power loop R2.

**This worker executed nothing.** No shell, no jobs, no LTspice, no simulator, no
git, no network, no recursive agents, no deletions. Only files inside this output
directory were written. Zero simulations were run by this session, so nothing
here consumes the ≤24 R2 simulation cap.

**Scope executed:** exactly the `loop_candidate` line of the ROUND2 code-only
override — (a) draft `analyze_independent.py` correcting R_eff and the
time-weighted / true-pp statistics, (b) make it perform no simulation, (c) write
the **blocked** `matrix.json` for P2 actual loads vs a resistor. Nothing else.

**Worker status is `INCONCLUSIVE`, deliberately.** The contract maps
"simulation absent ⇒ INCONCLUSIVE". Reporting `PASS` here would be a claim that
this task settled something; it did not. Worker `PASS` would in any case mean
*evidence delivered only*, never electrical acceptance. **All HOLD remain. No
electrical threshold was read, changed or argued with.**

## Evidence basis (read-only, outside this output dir)

| item | path | sha256 |
|---|---|---|
| original 60 ms raw (6 331 931 pts, 13 vars) | `R1_LOCAL/evidence/candidate_diagnostic/nominal_24V_gear_resource600/circuit.raw` | `d8b11ebedbb1125bbd968bdaf3a4c6e6f691e7dae1872cf76b6d8411e8d260ba` (matches ROUND1_REVIEW.md l.2; the script refuses to proceed on a mismatch) |
| original netlist | same dir `circuit.cir` | hashed by the script |
| controller model | `controller.sub` | `c03284243ac3b8e500e5bed3696deb8ebbde10eb8cb2a58b6e37929d9d18b634` |
| MOSFET model (ST STP9NK50Z, level-3, 25 °C) | `st.lib` | `6ad61988b9e045684dc8271bc51ddfdca00d65b745e6edd6c4492a42df1ad7a4` |
| rectifier model (US1G) | `diode.lib` | `f8669a85e8f3ed412ba97ab72bc6b7b0facbdf57111187ede39a365801324ec3` |
| clamp model (SS14) | `ss14.lib` | `3288afb62761edfc9e9095127e92e5f9d0e52cd79c1ec948db82bec9ed1f8ae2` |

Hashes above are transcribed from the round-01 archive record and are re-computed
by the script on every run. Models are opened read-only; not one byte is written
back. Native solver of record: **LTSpice 24.0.12.0 Windows, real double, forward,
nocompression, method=gear**, original tolerances `reltol=.001 abstol=1n vntol=1u`
— unchanged.

## 1. R_eff — corrected, with an honest caveat about the review's number

R1 used **4560.74 Ω** and R2 round-01 (`settling_analysis/analysis.py`) reproduced
it. The review rejects it because each bleeder string is 90.9 k + 90.9 k =
**181.8 k**, and **two** such strings in parallel give **90.9 k**, not 45.45 k.

Reproducing the review's own arithmetic, though, exposes a discrepancy that I
must report rather than paper over:

| grouping | R_eff |
|---|---:|
| R1 rejected: 5200 ∥ 45.45 k ∥ 201.9 k | 4560.74 Ω |
| exact ideal resistors: 5200 ∥ 90.9 k ∥ (100 k + 100 k + 1900.6) | **4475.91 Ω** |
| review quote | 4801.65043 Ω |

The review figure is not reproducible from its stated inputs; the residual is a
sub-ohm design choice in how the divider tail is grouped, i.e. a hand-computation
artefact. **4560.74 Ω is definitively rejected** (wrong bleed leg by 2×). The
corrected value is carried as the **band 4475.9–4801.7 Ω (±3.5 %)**, and every
load-dependent quantity is reported across that band, so no conclusion here rests
on the sub-ohm choice. I am not overriding the review's decision — I am flagging
that its quoted precision is not defensible and should not be copied forward as a
point value.

## 2. Statistics — time-weighted mean (not arithmetic)

`lab.stats()` trapezoid-weights the mean but takes min/max from raw samples only,
and the native trace is **non-uniform** (adaptive solver, dt from ~1e-17 s to the
2e-7 s max step), so a plain arithmetic mean of those samples is biased toward
densely stepped regions. The correction implemented in `window_stats()`:

* **trapezoid time-weighted mean** with interpolated window endpoints — no sample
  dropped, nothing extrapolated;
* **density-weighted** mean reported alongside as a cross-check;
* **cluster-robust standard error** — samples arrive in runs of near-equal dt, so
  `s/√N` understates the error; the SE is inflated by the design effect from a
  lag-1 autocorrelation estimate;
* **TRUE ppt** (peak-to-peak-to-peak) = min-max span **plus** the largest
  excursion the adaptive solver could have hidden between two adjacent samples.
  This is a **bound**, reported separately, and is never used to claim a pass.

The raw window figures quoted in round-01 (means 162.179 / 166.941 / 170.442 /
169.812 V over the four 5 ms windows; −629.6 mV step into the last window) are
not re-derived here, because deriving them requires reading the raw, which
requires running the script. They remain **round-01 evidence**, not new evidence.

## 3. The 200 Hz claim — withdrawn, not re-argued

Round-01 reported the largest first FFT bin at 200 Hz in each 5 ms window. The
review rejects treating that as a physical oscillation: 5 ms resolution cannot
support it. `resolution_report()` encodes the rule mechanically:

* 5 ms window ⇒ 200 Hz is **exactly 1 cycle** — the minimum resolvable
  oscillation is 400 Hz (≥2 cycles);
* a single largest bin at 1/T is therefore **never** evidence of an oscillation at
  1/T, and `single_bin_at_1_over_T_is_evidence` is hard-coded `False`.

The envelope is instead characterised as a **trend** via a moving-block bootstrap
(blocks resampled, not points, so within-block correlation is preserved). A slope
whose 95 % interval excludes zero is a **drift**; it is still not a spectral line
and no oscillation is claimed anywhere.

## 4. Conduction mode — measured cycles, no RHP formula

The review forbids the duty-based CCM RHP estimate. `rhp_zero_evaluated = False`
is asserted, and the formula appears **nowhere** in the script.
`cycle_analysis()` instead measures, **per switching cycle from the raw**: period,
duty, I_L peak / valley / mean, zero-crossing count, and the conduction class from
the measured valley sign and crossing count. It reports `CCM_DOMINANT` /
`DCM_DOMINANT` / `BOUNDARY` plus DCM and CCM fractions. In DCM the
control-to-output transfer has no RHP zero, so no RHP-zero conclusion is offered
for either mode.

## 5. `matrix.json` — BLOCKED (P2 actual loads vs resistor)

Six cells, **all `BLOCKED`, zero allowed**: `P2-R0` (the existing resistor
fixture, kept only as a reference), `P2-CP-24`, `P2-CP-26p4` (constant-power
sinks — **negative** incremental resistance −V²/P), `P2-CC` (constant-current,
0 dB), `P2-ILIM` (current-limited at 1.7742 A, R left **null** rather than
invented), `P2-PULSE` (spec **not supplied** by any approved source, so left
empty rather than fabricated).

The central point recorded as data: a resistor presents **+R** while a
constant-power sink presents **−R**; the damping terms have opposite sign, so the
output pole migrates and **stability conclusions from the resistor fixture do not
transfer to P2**. Unblocking requires a written principal authorization per cell,
a P0-resolution round, and a budget line inside the ≤24 cap.

`matrix.json` here is hand-authored as a document; when the principal runs
`analyze_independent.py` the script regenerates the same path from the real
netlist, and script output supersedes this copy.

## Files in this directory

| file | content | executed? |
|---|---|---|
| `analyze_independent.py` | the corrected analysis; **requires `--run` + a principal approval file**, otherwise exits INCONCLUSIVE having simulated nothing | **no** — draft only |
| `matrix.json` | blocked P2 load matrix, 6 cells, 0 allowed | no (hand-authored data) |
| `inventory.md` | this document | — |
| `result.json` | machine-readable result (evidence delivery only) | — |

## Blocking issues / not proven

* `analyze_independent.py` has **never been executed** — not even a syntax or
  dry-run pass, because Round 2 disables shell for this worker. The principal must
  inspect before running; the two known cosmetic-risk spots are the `TRAPZ`
  lookup (numpy 2.x rename guarded by a `getattr`, so a numpy-1.x environment
  would raise a `TypeError` at the first window rather than fail silently) and the
  `trend_bootstrap` block-fit path on sparse blocks.
* R_eff exact point value: the review's 4801.65043 Ω is not reproducible; only a
  4475.9–4801.7 Ω band is defensible.
* Conduction mode, actual power-stage topology, gain margin and phase margin:
  **none measured**; no Bode or loop-gain run exists.
* Whether the 200–600 Hz envelope decays or persists: **unresolved**, and it is
  not an oscillation claim.
* Physical credibility (P0): **not established** — SENSE above the LT3757A
  absolute maximum, US1G ~400 V reverse excursion of unproven physical amplitude.
* Electrical acceptance: **unchanged, still failing**. All HOLD remain.
