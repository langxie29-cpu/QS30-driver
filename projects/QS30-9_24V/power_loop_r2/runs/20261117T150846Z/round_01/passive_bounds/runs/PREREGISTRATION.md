# Preregistration — passive_bounds (six diagnostic runs) — QS30-9 / startup_forensics / round_01

Written BEFORE any new simulation was executed. No result file existed in this directory when this page was written.

## 1. Toolchain and provenance (read-only, unchanged)
- Simulator: LTspice 24.0.12.0 Windows, native binary `OLD/toolchain/ltspice26/extracted/LTspice.exe`, invoked non-interactively (`-b`), method=Gear, solver=Normal, tnom=25, temp=25.
- `OLD` = `D:/PROJECTS/dsharness/QS30-1/projects/QS30-9_24V`; `R2` = `D:/PROJECTS/dsharness/QS30-power-loop-r2/projects/QS30-9_24V/power_loop_r2`.
- All new runs use the shared helper `R2/lab.py`. `lab.full(path, stop, step, method)` builds the extended-observability cell: it copies the four vendor model files from `OLD/sim/s06c_current_cell_v3/ST_AUX12_1ns` and derives `circuit.cir` from the R1 baseline `nominal_24V_gear_resource600/circuit.cir`, replacing only the `.tran` line and the `.save` line.
- `lab.execute(path, hypothesis, variable, timeout)` refuses to run if `preregister.json` already exists, refuses if the four model hashes differ from the R1 baseline, and refuses if the solver tolerances are not the original `reltol=.001 abstol=1n vntol=1u`.
- Vendor model files are copied byte-identical and never edited: `controller.sub`, `st.lib`, `diode.lib`, `ss14.lib`.

## 2. Fixed base cell (per run, before the single approved per-run edit)
`VINPUT vin 0 PWL(0 0 1e-06 24)` — 1 us linear source ramp to 24 V; `RINPUT vin in .1`;
`LPOWER in drain 150u Rser=.16`; `XQ ... STP9NK50V` (STP9NK50Z model); `RSRC src 0 .062`;
`XNEG/RNEG` 2 Ω + SS14 negative gate clamp; `DREC drain hv US1G` boost rectifier;
`RSNUB 330 / CSNUB 100p` across the rectifier; `COUT hv 0 20.3u Rser=.1 IC=0`;
`RLOAD 5200` plus two 181.8 kΩ bleeder strings and the LT3757A feedback divider;
`VAUX aux 0 PWL(0 0 1m 12)` explicit fixture AUX rail; `REN1 200k / REN2 12.8k`;
controller `XU ... LT3757A` with SS 100 nF, VC comp 22k/6.8n/100p, RT 140k.
Controller SHDN (pin 9) is held at 0 V by the netlist divider and is never exercised in these runs.

## 3. Per-run observation window
`.tran 5e-08 0.003 0 5e-08 uic` (stop = 3 ms, max step = 50 ns), method=gear, unchanged original tolerances.
`lab.execute(..., timeout=30)` for every run.

## 4. Exactly six runs, one approved edit each
| run | base | the ONE variable | edit applied to generated circuit.cir |
|---|---|---|---|
| `p1_fast_24V` | base fast 1 µs source ramp | none (reference) | none |
| `p2_slow_1ms` | base slow 1 ms source ramp | source ramp duration only | `PWL(0 0 1e-06 24)` → `PWL(0 0 1m 24)` |
| `p3_fast_vin_26p4` | p1 | source plateau voltage | `PWL(0 0 1e-06 24)` → `PWL(0 0 1e-06 26.4)` |
| `p4_fast_rinput_1ohm` | p1 | input series resistance | `RINPUT vin in .1` → `RINPUT vin in 1` |
| `p5_fast_cout_24p36` | p1 | HV output capacitance | `COUT hv 0 20.3u` → `COUT hv 0 24.36u` |
| `p6_fast_lpower_135u` | p1 | boost inductance | `LPOWER in drain 150u` → `LPOWER in drain 135u` |

`Rser` on LPOWER (.16 Ω) and on COUT (.1 Ω) are part of the base cell and are NOT changed by runs p4–p6.
p3 (26.4 V = 24 V × 1.10) is a source-tolerance corner probe only; it is not a new acceptance voltage.

## 5. Predeclared analysis quantities (measured from each native `.raw`)
- `t_peak`, `IL_peak` = max of `I(LPOWER)`; `VOUT_peak` = max of `V(hv)`; `VOUT_final` = `V(hv)` at 3 ms.
- `dVdt_inc_10_90` = 10 %→90 % rise time of `V(hv)` over its first monotonic segment; `dVdt_max` = max `dV/dt` of `V(hv)` in the 0–3 ms window.
- `divider_share` = `RSOURCE_total / (RSOURCE_total + Z_cell)` where `Z_cell = Rser(.16) + DCR + Rds_on(STP9NK50Z) + RSRC(.062)`, taken at 0.162 Ω and 1.062 Ω for p1/p4 — a DC-level bound, not the dynamic answer.
- Energy check: `E_s = L·I_peak²/2` vs stored/charge energy of `COUT`; `Ideal_peak = VIN/sqrt(L/COUT)`.
- Convergence: compare each run's `IL_peak`/`VOUT_peak` with its base and record the relative difference.

## 6. Predeclared interpretation rules (fixed before execution)
1. **Linear peak is NOT saturation evidence.** (Declaration, not a result.) `IL_peak > 3.1 A` does not mean the MSS1583-154KED saturates; it only means the peak exceeds the datasheet 25 °C 10 %-drop Isat and that a linear L model is therefore outside its qualified domain.
2. **Controlled-slew qualification** requires BOTH: (a) `VOUT_peak ≤ 195 V` (fault_peak_V from the R1 preregister is the source of record, not a new limit); (b) `IL_peak` below the magnetically-referenced current ceiling for the device/corner being considered. Below (b) it is reported `CONSTRAINED_UNQUALIFIED`.
3. A run is `SOLVER_UNREVIEWED` whenever `command.json` rc ≠ 0 or `circuit.raw` is absent/unreadable.
4. No result of this task changes any HOLD or any electrical acceptance threshold.

## 7. Explicit limits of this task
- No TPS26601 vendor model executes in this session: the archived TI TPS26601 libraries are encrypted (SLVMBY3/SLVMBY4) and OLD records no successful dynamic TPS26601 qualification in ngspice; this is an analysis task, not a four-terminal eFuse simulation.
- No thermal model, no nonlinear/hot core-loss inductor model, no wiring inductance, no wiring resistance beyond `RINPUT`, no short-circuit event, no delayed-disable event, no measurement of a physical board.
