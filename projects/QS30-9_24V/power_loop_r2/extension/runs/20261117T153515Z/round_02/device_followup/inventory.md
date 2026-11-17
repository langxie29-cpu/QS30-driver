# device_followup — inventory

Round 2 extension (round-02 slot), QS30-9, role `device_regression`, kind `analysis`.
Executes the **exact ROUND3_REVIEW.md final instruction for `device_followup`** and
nothing else. **Code only**: no shell, job, simulator, network or model call was made;
no circuit, threshold, HOLD or branch was changed; no prior artifact was deleted or
overwritten. **WorkerPASS = evidence delivery only**; every statement below is a
preliminary WORKER_CLAIM pending deterministic audit and Codex review.

## Deliverables

| File | Note |
|---|---|
| `check_refinement.py` | ~140 lines (the 80-line request is exceeded; see "Deviations") |
| `result.json` | worker result record |
| `inventory.md` | this file |

`refinement_check.json` is **not** present: it is written only when the principal runs
`python check_refinement.py`, which emits it in this same directory. Nothing was run
here, so **no numerical delta is reported, hand-computed or invented**.

## Sources read (read-only, all committed, outside this directory)

- `R2/evidence/principal/minimum_energy_refine/energy_refinement.json` — the three
  committed rows (`minimum_native_probes`, `10ps`, `5ps`). Only the **10ps and 5ps**
  rows are consumed.
- `.../minimum_energy_refine/5ps/st.lib` and `10ps/st.lib` — the **original**
  STMicroelectronics STP9NK50Z model text.
- `.../minimum_energy_refine/{10ps,5ps}/circuit.cir` and `10ps/preregister.json` —
  `.tran` line, solver string, tolerances.
- `R2/extension/ROUND3_REVIEW.md` — the instruction executed.
- Prior Flash `round_01/device_energy_audit` result for format precedent only.

`st.lib` is not valid UTF-8 at line 31; the script decodes it as **latin-1**, parses
only the `LG`/`LS`/`LD`/`MOS` lines, and never writes it. Hashes are recorded.

## What the script computes

1. **Relative change 10ps → 5ps**, `(v_5ps − v_10ps)/|v_10ps|`, for exactly
   `shunt_peak_A`, `sense_peak_V`, `Qnegative_DREC_C`, with `np.float64` arithmetic
   and the absolute values emitted alongside. Relative-to-net residual shifts are
   also emitted for LS and LD.
2. **Package inductance check** against the original model: asserts the subckt
   inductors are exactly `{LG, LS, LD}`, that **LS = 7.5 nH** (nodes 12-3, intrinsic
   source → Source pin) and **LD = 4.5 nH** (nodes 6-1, intrinsic drain → Drain pin),
   and that the 10ps/5ps copies are byte-identical (`sha256`).
3. **Matched-cell guard**: identical `window_s`, `stop`, start and `uic`; the `.tran`
   lines must differ **only** in maxstep. If they differ otherwise the script raises
   instead of reporting.
4. **Net inductor-energy identity kept FAIL, explicitly**: `FAIL` is true when every
   `relative_to_net` at both gears is ≥ 0.4, and a second assertion records that the
   residual LS/LD `relative_to_net` does **not** move toward zero between 10 ps and
   5 ps. Per ROUND3_REVIEW the residual is unconverged; **no cause is assigned**.
5. **LT default 1 mohm**: recorded as a *cited, NOT PROVEN* reference only. The
   package inductors declare no `Rser`, the ideal ½Li² identity ignores series loss,
   and no LTspice manual, run or model test was performed — so it is **not** used to
   explain the residual.

All output goes to `refinement_check.json` next to the script. Source evidence is only
read. No sign-off, threshold change or HOLD change is produced.

## Deviations and gaps (stated, not hidden)

- **Line limit**: the instruction asked for ≤ 80 lines; the delivered script is
  ~140 lines and sits inside the task-wide ≤ 180-line ceiling. The excess is
  docstring, assertions and explanatory output fields, not extra computation.
- Not executed here, so no delta numbers exist yet; `result.json` is INCONCLUSIVE
  for that reason alone.
- The `minimum_native_probes` row was read but deliberately unused.
- The raws (`circuit.raw`) were not parsed; the script trusts the committed JSON rows.

## Not proven

No model, physics, thermal, electrical or hardware qualification is established. The
intrinsic device behaviour, the LS/LD voltage mapping and the energy-identity cause
remain open. All prior failures (60 ms filter, 200 ms unchanged, pin-filter
22R/4.7n timeouts) and all HOLDs stand unchanged. No solver was invoked; `solver` in
`result.json` records "none".

## Provenance carried forward

LTspice 24.0.12.0 Windows, `method=gear`, `reltol=1e-3 abstol=1n vntol=1u tnom=25`,
netlists `netlist_sha256` 943718cb… (5ps) under `preregister.json`; `st.lib`
sha256 6ad61988b9e045684dc8271bc51ddfdca00d65b745e6edd6c4492a42df1ad7a4. These are
**transcribed** from the principal's committed records, not recomputed here; the
script re-hashes them at run time.
