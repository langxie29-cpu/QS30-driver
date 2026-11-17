# device_energy_audit — inventory

Round 1 extension, QS30-9, role device_auditor. **Code only**: no shell, jobs,
simulator, network or model calls; no circuit change. No threshold modified, no
HOLD touched. **WorkerPASS = evidence delivery only**; nothing here is a design
approval, and any device statement is a preliminary WORKER_CLAIM pending
deterministic audit and Codex review.

## Deliverables

| File | Note |
|---|---|
| `analyze_energy.py` | 178 lines, the single script (limit 2) |
| `inventory.md` | this file |
| `result.json` | worker result record |

`metrics.json` / `waves.txt` are absent. They are produced only by actually
running the script, which the principal does after code inspection. The script
was **not run here**, so **no numerical energy, current or voltage is reported,
hand-computed or invented**. INCONCLUSIVE for that reason alone.

## Sources read (read-only, outside this directory)

`circuit.cir` (probe names, `.tran`, options), `st.lib` (STP9NK50Z package L),
`internal_analysis.json` (committed ranges, raw hash), `circuit.raw` (read at run
time via `lab.native`), `circuit.log` / `process.json` / `command.json` /
`preregister.json` / `decision.txt` (provenance), and `power_loop_r2/lab.py`
(`lab.native`, `lab.sha`). `st.lib` is not valid UTF-8 and was inspected via
targeted pattern search only; it was never rewritten.

## Method

From `st.lib` STP9NK50Z: `LG 2 4 7.5n`, `LS 12 3 7.5n`, `LD 6 1 4.5n`; MOS nodes
13 (drain), 5 (gate), 9 (source). So `V(q:12)-V(src)` spans the **source package**
inductor LS (7.5 nH) and `V(q:6)-V(drain)` the **drain package** inductor LD
(4.5 nH). Values come from the file, not memory.

Exact raw probe names: `v(q:12)`, `v(q:6)`, `v(src)`, `v(drain)`, `i(vqs)`,
`i(vqd)`, plus `v(q:5)`, `v(q:9)`, `v(q:13)`. Every required probe is asserted
present; a missing one aborts instead of continuing.

Fixed windows, both required: **[1.02 µs, 1.10 µs]** and **[0, 10 µs]**. Per
window the contract identities are evaluated literally:

- `∫ (Vq12 − Vsrc)·I(VQS) dt` vs `.5·7.5n·(Iend² − Istart²)`
- `∫ (Vq6 − Vdrain)·(−I(VQD)) dt` vs `.5·4.5n·(Iend² − Istart²)`

Integration is `numpy.trapezoid` over saved points with interpolated endpoints;
out-of-extent bounds raise. The **opposite orientation** of each pair is also
integrated and reported, since a closed inductor obeys `v·i = d/dt(½Li²)` either
way and probe-label vs pin direction is not settleable from probe text.

Also emitted: intrinsic `VGS = V(q:5)−V(q:9)` and `VDS = V(q:13)−V(q:9)` over the
1.02–1.10 µs window and the full trace, `V(src)`/`V(drain)` package extremes,
per-window pin-current extrema, point count and min/max timestep, a cross-check
of intrinsic node ranges against `internal_analysis.json`, and recorded solver
tolerances (`vntol` 1 µV, `abstol` 1 nA, `reltol` 1e-3). The raw hash is compared
to the committed one. Non-matching hashes in `result.json` are **transcribed**
from the principal's records, not recomputed by this worker; the script re-hashes
them at run time.

## Caveats encoded in the output

The trace holds an extremely narrow reverse-drive event near 1.052 µs, where a
trapezoid sum over saved points can under- or over-estimate work. **Failure of
this discrete identity can therefore indicate coarse integration, not physics**;
success would not certify the model either. Disagreement is attributed to a non-L
branch, coarse integration, or an orientation/name mismatch — never to device,
thermal or model failure, and never hand-resolved. The script writes only
`metrics.json` and `waves.txt` beside itself and never mutates source evidence.

## Not proven

No energy balance is measured here; no model, physics, thermal or electrical PASS
is claimed. The sign convention of `I(VQS)`/`I(VQD)` versus LS/LD pin direction is
deliberately left open, with both orientations emitted. All prior failures
(60 ms and 200 ms qualification timeouts, pin-filter 22R/4.7n timeout) and all
HOLDs stand unchanged.

## Solver

No solver was invoked by this worker. `solver` in `result.json` records the
provenance of the existing trace (LTspice 24.0.12 Windows, Gear, per
`process.json` and `circuit.log`), not a new run.
