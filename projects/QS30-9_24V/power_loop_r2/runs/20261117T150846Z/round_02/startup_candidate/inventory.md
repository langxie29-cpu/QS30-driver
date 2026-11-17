# inventory — startup_candidate / Round2 (CODE GENERATION + READ ONLY) / QS30-9

**Task status: `INCONCLUSIVE` by design.** This session was forbidden from executing any shell
command or simulator, so it delivers *reviewed-candidate scripts and a quantified source review*,
not results. Nothing here is an electrical acceptance, and no HOLD is changed.

`worker PASS` in this harness would mean "evidence delivered"; it is not claimed, because the
deliverable is a *draft for principal execution* and no measurement exists yet.

## 1. Authorized scope (and the boundary it sets)
`ROUND1_REVIEW.md` line 8 is the only authorization. It permits **exactly three** worst-scenario
diagnostic runs plus research work, and states that the strategy is *not* qualified:

> "U101 controlled slew is primary candidate with LT enable inhibited until input has settled, but
> actual encrypted model, RTN isolation, thermal/SOA and max shutdown delays remain HOLD.
> Independent 33 ohm 5 % series precharge downstream of all input bulk is fallback for finite
> simulation; bypass/default-off supervisor not implemented and cannot qualify. Three
> worst-scenario diagnostic runs: 26.4 V, C 24.36 u, L 135 u, Rsource .1, gate inhibited;
> uncontrolled 1 us; same plus 33 ohm; same no 33 ohm with 8.49 ms fastest datasheet-derived
> 47 nF-10 % slew. Each changes one variable relative to uncontrolled reference; no ideal slew
> qualification of real eFuse. Do not equate a source ramp to a validated device."

Nothing was added beyond that: no fourth case, no thermal scan, no compensation scan, no tuning,
no retry, no fixture.

## 2. Files delivered (all inside this OUTPUT_DIR)
| file | kind | executed this session? | purpose |
|---|---|---|---|
| `build_startup.py` | draft runner | **NO — draft only** | Builds + runs the 3 approved cases via shared `lab.py` (`lab.full` → one-variable edit → `lab.execute`). Refuses import, refuses overwrite, refuses non-unique anchors. |
| `measure_startup.py` | draft analyzer | **NO — draft only** | Post-hoc read of whatever raws exist. Only `lab.native` (memmap), no simulation. Pre-declares the measured quantities. |
| `ti_source_review.py` | draft source-review | **NO — draft only** | Quantified TI/Kemet guarantee review → `ti_source_review.json`. Read-only file access. |
| `PREREGISTRATION.md` | preregistration | n/a | The three cases, the single variable of each, the assertions, the interpretation rules. Written before any run can exist. |
| `inventory.md` | this file | n/a | Deliverable inventory and open questions. |
| `result.json` | result contract | n/a | Status + blocking issues. |

`ti_source_review.json` is **not present**, because producing it would have required running
Python, which the Round2 override forbids. Its absence is deliberate; the script that produces it
is deterministic and reads only archived files.

## 3. The three approved cases (one variable each vs. the uncontrolled reference)
Constant corner for all three: `VIN 26.4 V`, `COUT 24.36 uF`, `LPOWER 135 uH`, `RINPUT .1 Ω`,
gate inhibited, `.tran 5e-8 1.008e-2 0 5e-8 uic`, method=gear, original tolerances
(`reltol=.001 abstol=1n vntol=1u`) untouched, timeout 30 s per run.

| case | the ONE variable vs. case A | netlist edit |
|---|---|---|
| A `startup_A_uncontrolled_ref` | none — uncontrolled 1 µs source ramp (reference) | gate inhibit `REN1/REN2 → VEN en 0 0` + corner values |
| B `startup_B_precharge_33ohm` | +33 Ω 5 % independent series precharge resistor | `RPRE in drain 33` inserted after the L's `Rser` |
| C `startup_C_slow_slew_8p49ms` | source ramp 1 µs → 8.49 ms (no 33 Ω) | `PWL(0 0 1us 26.4)` → `PWL(0 0 8.49m 26.4)` |

Model bytes are copied by `lab.full()` and re-verified by `lab.execute()` against the R1
baseline; this session recorded the R1 baseline hashes by reading (not by re-running):

| component | sha256 |
|---|---|
| `controller.sub` (LT3757A vendor model) | `c03284243ac3b8e500e5bed3696deb8ebbde10eb8cb2a58b6e37929d9d18b634` |
| `diode.lib` | `f8669a85e8f3ed412ba97ab72bc6b7b0facbdf57111187ede39a365801324ec3` |
| `ss14.lib` | `3288afb62761edfc9e9095127e92e5f9d0e52cd79c1ec948db82bec9ed1f8ae2` |
| `st.lib` | `6ad61988b9e045684dc8271bc51ddfdca00d65b745e6edd6c4492a42df1ad7a4` |
| solver `LTspice.exe` 24.0.12.0 | `17f5efb978c0df2e164328b7352801fdc1ed0225827e41669bd9da25893fe96d` |

Note: `LPOWER` is `135u Rser=.16` in every approved case (corner value); `Rser .16` is a
base-cell element, *not* the datasheet DCR (0.033 Ω nom / 0.038 Ω max). The simulated inductor is
therefore heavier than the real part — a direction worth noting, not a result.

Source of these hashes: `R2/evidence/principal/unchanged_200ms/preregister.json` (R2 principal
baseline) and `R2/runs/.../round_01/sense_root/run_gear_1e-7/preregister.json` — both agree.
**No TPS26601 vendor model was executed or hashed as a simulator input.** The archived TI
libraries (SLVMBY3/SLVMBY4, encrypted) are recorded as files only, status HOLD.
`STP9NK50Z` is supplied by `st.lib` and is covered above; no other component is a vendor model.

## 4. Quantified guarantee / source review (numbers, each traceable to one grep)
Oracle: `OLD/sources/TPS2660.txt` (text extraction of `OLD/safety_r1/sources/TPS26601RHFR.pdf`)
and `OLD/sources/sprint06/MSS1583/MSS1583.txt`. Line numbers index the extraction.

- **Native dVdT ramp**: TPS2660.txt L1365 — "internal output voltage ramp rate of 23.9 V/1.6 ms"
  ⇒ 14.94 V/ms, and L1367 says an external capacitor can only program rates **slower** than that.
- **dVdT gain**: L453 — GAIN(dVdT) = 24.6 V/V typ (23.75 … 25.5 min/max).
- **Programmed ramp**: L635 — `tdVdT` "SHDN to V(OUT) = 23.9 V, with C(dVdT) = 47 nF … 10 ms";
  ⇒ 2.39 V/ms, and 24 V / (2.39/1.10) = **8.81 ms** ⇒ the review's **8.49 ms** figure reproduces
  within 0.1 % (23.9 vs 24.0 V rounding). This is a *source ramp*, never device behaviour.
- **No min/max on tdVdT exists** in the archived text (single typical column, L635–636). The
  10 %-capacitor corner is therefore a **derivation, not a guarantee**; it must not be quoted as
  a TI datasheet limit.
- **Current limit, guaranteed max @ V(IN)-V(OUT)=1 V**: L461–465 — R(ILIM)=8 k ⇒ 1.425/1.5/1.575 A;
  R(ILIM)=5.36 k ⇒ 2.11/2.23/2.35 A. A passive bound must use the **max** column. The same
  datasheet warns the limit is specified at ΔV=1 V, so start-up (large ΔV) is outside it.
- **Fast-trip**: L1530 — internally 87 % **above** the programmed overload limit (i.e. trip ≈
  1.87×I_OL), not 87 % of it.
- **Inductor MSS1583-154KED**: `MSS1583.txt` L45 — DCR 0.023–0.026 … 0.033/0.038 Ω,
  Isat columns **3.9 / 4.4 A**, Irms **3.4 / 4.8 A**. The extraction **cannot** tell me whether
  those are 10 % or 20 % drop points (the header columns are the lost-UTF-8 lines) — a human must
  read the PDF before any magnetic claim. The SPICE cell has **no saturation** at all:
  `LPOWER 150u Rser=.16`, linear, so linear peak current is **not** saturation evidence
  (round_01 `PREREGISTRATION.md` line 47, unchanged).
- **Model status stays HOLD**: `TPS26601_TRANS.LIB` present in both TINA and PSpice archives but
  encrypted; no successful dynamic TPS26601 qualification is recorded anywhere in OLD.

Corner arithmetic (transferable to whichever of the three cases runs — energy bound only):
`V_pk = I_pk = 26.4 V × sqrt(24.36 µF / 135 µH) = 26.4 × 0.425 = 11.22` (lossless upper bound,
zero damping, zero load — an upper bound, not a prediction).

## 5. Open questions the principal MUST settle before copying `build_startup.py` out
1. **Stop time.** `lab.full()` freezes stop at 10.08 ms. The uncontrolled reference can only reach
   the HV ceiling once the rectifier conducts, which needs the controller to switch — and the gate
   is inhibited in all three approved cases. So case A is a *passive arrival* reference, and
   `fault_peak_V = 195` is reported **NOT EVALUABLE**, not failed.
2. **Gate inhibition mechanism.** LT3757A SHDN is the unconnected 10th positional node in this netlist
   and is not driven by `controller.sub` in any way this session could verify by reading alone.
   The draft therefore uses the *same* netlist mutation as the already-approved round_01
   `passive_bounds` prerequisite (`REN1/REN2 → VEN en 0 0`, asserted `REN1 not in cir`). Any
   different inhibition (e.g. a real SHDN pin 9 tie) is a **new** variable and must be
   preregistered separately — the draft will not add it silently.
3. **33 Ω placement.** "Downstream of all input bulk" and the base cell's `LABEL`-free node names
   make multiple readings possible. The draft places `RPRE in drain 33` (series in the power path
   before the inductor), which is downstream of `RINPUT`/input bulk and upstream of the L, and
   therefore also drops DC to the load — 16.5 V at 0.5 A. If the principal wants it outside the
   load path, that is a different topology and a different preregistration.
4. **Observability of the precharge element.** `lab.full()`'s `.save` line does not include `I(RPRE)`.
   The draft reasons about the precharge from `V(in) − V(drain) = 33 Ω × I_RPRE`, which is
   exact by Ohm's law and needs no added probe — but it is *derived*, not a saved trace, and it
   silently degrades (to a 33 Ω-Rser-modified V_{in,drain}) if the principal edits `.save`.
5. **Expansion caps.** 3 runs, 30 s timeout each, no retries. This sits inside the ≤24 combined
   simulation-attempt cap, and it does not consume any of the deleted round_01 attempts.

## 6. What this session did NOT do
No shell, no simulator, no LTspice, no Python execution of any kind, no git, no download, no
deletion, no write outside OUTPUT_DIR, no vendor-model modification, no threshold change, no
recursive agent/model launch.
