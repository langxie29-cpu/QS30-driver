# inventory — startup_followup (Round 4, CODE ONLY) / QS30-9

**Worker status intent: `PASS` = evidence delivery only.** One corrected calculator was written and
**not executed** (this task forbids shell/jobs/simulator/network/model calls). Zero simulations, zero
model invocations, zero writes outside `OUTPUT_DIR`, no HOLD and no threshold touched.

## 1. What the review asked for and what was delivered

`ROUND3_REVIEW.md` L4 records the exact defect this task fixes:

> "StartupcalculatorconfusesP6WwithVin26.4V: Pmax calculation6^2/(4*33), riseuses6V etc invalid."

Delivered: `startup_calc_v2.py` (110 lines, numpy, writes `startup_calc_v2.json` next to itself).

Corrections applied versus `round_01/startup_path_audit/startup_arith.py`:

| old defect | new handling |
|---|---|
| Symbols `PIN = 6.0` (W) and `PMAX = 26.4` (V) — swapped meanings | Explicit `V = 26.4`, `P = 6.0`; the names `PIN`/`PMAX` no longer appear (grep-verified) |
| `Pmax = PIN**2/(4*R)` = 6²/(4·33) — volts lost | `PmaxVs = [21.6, 24, 26.4]**2/(4*R)` — V²/(4R), an array |
| `rise_0_to_26p4V = PIN / rate` — 6 V instead of 26.4 V | `rise = V / dvdt` with `dvdt = Iprog*G/Cmin` |
| Copy of an assumed 0.5 Ω series element | Removed; no `0.5` and no USB voltage anywhere in the script |
| Hand-written literals presented as results | Only datasheet/prompt constants are literals; all 6 W and ramp arithmetic is numpy |

## 2. Inputs (every one is a prompt or datasheet constant — none invented)

`V = 26.4` (V, worst fixed input), `P = 6.0` (W), `R = 33.0` (Ω), `Iprog = 5.5e-6` (A),
`G = 25.5` (V/V, `OLD/sources/TPS2660.txt` **L453** GAIN(dVdT) 23.75/24.6/**25.5**),
`Cmin = 42.3e-9` (F), `V_BIAS = 1.0` (V, L457), factory ramp `23.9 V / 1.6 ms` (L1365).

Emitted quantities: `dvdt`, `rise`, `PmaxVs`, `load_A = P/V`, `R_loss = load_A²·R`, and the factory
cross-check. The principal executes the script; **no numeric value is transcribed in this inventory**
and none was hand-computed by the worker.

## 3. Statements the calculator asserts (booleans, not prose)

- `max_Pmax_lt_6W` and `all_Pmax_lt_6W` on the array above: **a permanent series R cannot deliver 6 W**.
  The permanent-R route is recorded as `cannot_deliver_6W: True` with the V²/(4R) reason.
- `series_loss_positive`, `dvdt_positive`, `rise_finite_positive`, `load_finite_positive`.
- `precharge_bypass`: `hardware_missing: True`, `actual_device_MPN: None`, `bypass_model: None`,
  `max_delay: None`. No bypass device, MPN or vendor maximum delay exists in the repository. MODE=open
  TPS26601 is circuit-breaker + latch (TPS2660.txt L170, L1717–L1719), and every protection delay is
  TYP-only (L615, L635, L642, L644), so **no max delay may be quoted**.

## 4. New finding raised (UNRESOLVED, not a pass)

The factory ramp `23.9 V / 1.6 ms` (14.9375 V/ms) with `Iprog = 5.5 µA` and `Gmax = 25.5 V/V` implies a
ramp capacitor of `Iprog·G / rate`, which the script computes as `C_for_factory_rate_F`, alongside
`ratio_Cmin_over_C_for_factory`. Emitted verbatim by the script rather than asserted here, but the point is:
the prompt's `Cmin = 42.3 nF` and the factory rate are **not mutually consistent** at 5.5 µA unless
42.3 nF is a factory-trim value and not the external ramp capacitor. Consequently the calculator
**makes no native-slew claim**. `Iprog = 5.5 µA` is carried as a prompt constant and is explicitly labelled
in the JSON as *not* a TPS2660.txt current specification.

## 5. Copied literals (no recomputation, no upgraded qualification)

Only three `metrics.json` files are read, and their values are copied unchanged with their `src` path:
`uncontrolled` (IL peak 9.557… A, Vout peak 45.06…), `precharge` (`bound_A`, `precharge_energy_J`,
`precharge_peak_W`), `slew_corrected_7p962ms` (IL peak 0.1022… A). These files are hash-recorded in the
JSON (`source_hashes`), including `models/st.lib` and `OLD/sources/TPS2660.txt`. The precharge band is
carried with the original caveat: part pulse rating, duration and bypass design remain HOLD.

The `uncontrolled_budget_ceiling_V` field is a **ratio** (`PmaxVs / copied passive peak`) explaining how
much source voltage the 6 W budget can pay for at that peak. It is not a converter result and is labelled
as such.

## 6. Not done / not claimed

- No simulation, no LTspice, no model execution, no network, no git, no deletion.
- No approval requirement was created; no electrical threshold, manufacturing HOLD or branch was changed.
- The corrected calculator's output is arithmetic evidence only; the principal must execute it and review it.
  Nothing here is an independent design approval.

## 7. Files in this directory

| file | kind | executed? |
|---|---|---|
| `startup_calc_v2.py` | corrected numpy calculator (110 lines) | **NO — written only** |
| `inventory.md` | this file | n/a |
| `result.json` | result contract | n/a |

`startup_calc_v2.json` is deliberately absent: producing it requires running Python, which this task
forbids. Its absence is deliberate, not a placeholder.
