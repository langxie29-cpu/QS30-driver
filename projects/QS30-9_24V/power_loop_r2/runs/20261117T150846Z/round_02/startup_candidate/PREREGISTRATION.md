# Preregistration — startup_candidate (three approved worst-scenario cases) — QS30-9 / Round2

Written BEFORE any simulation of this task existed. **No simulation was executed in this session**
(the Round2 override forbids shell/simulator execution); this page fixes the contract that the
principal will honour when it copies `build_startup.py` to the execution area.

## 1. Authorization
`ROUND1_REVIEW.md` line 8 authorizes exactly three cases and explicitly refuses qualification:

> "Three worst-scenario diagnostic runs: 26.4 V, C 24.36 u, L 135 u, Rsource .1, gate inhibited;
> uncontrolled 1 us; same plus 33 ohm; same no 33 ohm with 8.49 ms fastest datasheet-derived
> 47 nF-10 % slew. Each changes one variable relative to uncontrolled reference; no ideal slew
> qualification of real eFuse. Do not equate a source ramp to a validated device."

No fourth case, no thermal scan, no compensation scan, no retry, no extra fixture.

## 2. Toolchain and provenance (unchanged, read-only)
- Solver: **LTspice 24.0.12.0 Windows, Normal**, `OLD/toolchain/ltspice26/extracted/LTspice.exe`,
  sha256 `17f5efb978c0df2e164328b7352801fdc1ed0225827e41669bd9da25893fe96d`.
- All new runs go through the shared `R2/lab.py`: `lab.full()` builds the cell (copies the four
  vendor models byte-identical, derives `circuit.cir` from the R1 baseline with only `.tran`
  and `.save` replaced), `lab.execute()` preregisters full hashes/settings, refuses a second run
  in the same directory, refuses changed vendor bytes and refuses changed tolerances.
- Vendor models (byte-frozen, copied but never edited):
  `controller.sub` `c03284243ac3b8e500e5bed3696deb8ebbde10eb8cb2a58b6e37929d9d18b634`,
  `diode.lib` `f8669a85e8f3ed412ba97ab72bc6b7b0facbdf57111187ede39a365801324ec3`,
  `ss14.lib` `3288afb62761edfc9e9095127e92e5f9d0e52cd79c1ec948db82bec9ed1f8ae2`,
  `st.lib` `6ad61988b9e045684dc8271bc51ddfdca00d65b745e6edd6c4492a42df1ad7a4`.
- **No TPS26601 vendor model executes here.** The archived TI libraries are encrypted; the TPS26601
  is *not* a simulated part in any approved case.

## 3. Shared corner (identical for all three cases)
`26.4 V` source plateau, `COUT 24.36 µF` (Rser .1), `LPOWER 135 µH` (Rser .16), `RINPUT .1 Ω`,
gate inhibited, `.tran 5e-8 1.008e-2 0 5e-8 uic`, `method=gear`, solver **Normal**,
`tnom=25`, `reltol=.001 abstol=1n vntol=1u` (original, untouched), 25 °C, timeout 30 s per case.

## 4. The exactly three cases — one variable each relative to case A
| case | variable | netlist edit (applied after `lab.full()`, before `lab.execute()`) |
|---|---|---|
| A `startup_A_uncontrolled_ref` | none (uncontrolled 1 µs source ramp = reference) | gate inhibit `REN1 in en 200k / REN2 en 0 12.8k` → `VEN en 0 0`; VIN `1m` plateau → `1us` rise to 26.4; COUT → 24.36u; LPOWER → 135u |
| B `startup_B_precharge_33ohm` | +33 Ω 5 % series precharge resistor | A, plus `RPRE in drain 33` |
| C `startup_C_slow_slew_8p49ms` | source ramp 1 µs → 8.49 ms, no 33 Ω | A, plus `PWL(0 0 1us 26.4)` → `PWL(0 0 8.49m 26.4)` |

Hard assertions enforced by `build_startup.py` before each run (a failure aborts, nothing is run):
anchor found exactly once; `.tran` line exactly as specified; `REN1` absent and `VEN en 0 0`
present; case B has `RPRE` and no `8.49m`; case C has `8.49m` and no `RPRE`; case A has neither.

## 5. Predeclared measurement (in `measure_startup.py`, fixed before execution)
`V(hv)` peak and its time; `I(LPOWER)` peak and its time; `V(in)` plateau; source charge
`∫I(RSRC)dt`; time to reach 10 % and 90 % of the **frozen** analytic bound; final values.
Frozen bound, written down now: `V_pk = I_pk = 26.4 × sqrt(24.36 µF / 135 µH) = 11.22` — a
lossless zero-damping upper bound, not a predicted waveform.

## 6. Predeclared interpretation rules (fixed before execution)
1. **Linear peak is not saturation evidence.** `MSS1583-154KED` Isat is 3.9–4.4 A (datasheet, and
   the drop criterion is not recoverable from the archived extraction); the SPICE cell is linear
   with no saturation. Crossing Isat only means the linear model is outside its qualified domain.
2. **`fault_peak_V ≤ 195 V` is NOT EVALUABLE** in these three cases. The regulator cannot switch
   with the gate inhibited, so the HV ceiling has no domain. Not evaluable is never reported as pass.
3. Same for `ripple ≤ 1 Vpp`, mean 165–175 V, `startup ≤ 1 s`: the converter never regulates here.
4. **Case C is a source ramp, not a device.** A benign 8.49 ms ramp says nothing about the
   TPS26601's dVdT, current limit, SOA, thermal behaviour or shutdown delay. No such claim may be
   derived from it (review line 8, verbatim).
5. Any case with `rc ≠ 0` or a missing/truncated raw is `SOLVER_UNREVIEWED` / `TRACE_INCOMPLETE`;
   it is preserved as-is and **never retried** inside this task.
6. No result of this task changes any HOLD or any electrical acceptance threshold.

## 7. Budget
3 runs × 30 s timeout, no retries. This is within the ≤24 combined simulation-attempt cap and
does not touch the deleted round_01 attempts.
