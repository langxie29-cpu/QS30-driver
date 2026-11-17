# acceptance_budget — reconciled acceptance thresholds, bleeder delta and cold-start budget

- **Task ID:** `acceptance_budget` (role: `requirements_engineer`, kind: `analysis`)
- **Run:** `20261117T051440Z` / `round_01`
- **Worker:** deepseek-flash (low-cost execution agent)
- **Classification:** `ANALYTIC_BUDGET_ONLY_NO_SIMULATION_NO_MEASUREMENT`
- **Status of this document:** requirement reconciliation only. **No threshold was changed. No PASS is claimed for any electrical criterion.** Every status below is a preliminary `WORKER_CLAIM` pending deterministic audit and Codex review.
- **Physical operations performed:** none. No HV energisation, no fabrication, no purchase, no programming, no instruments.
- **Simulations executed by this worker:** **none.** No simulator was invoked; no waveform, log, raw file or metric was produced here. No file in either workspace contains a COUT = 0 V closed-loop startup waveform (see §7).

> **Numerics provenance.** The intended driver `reconcile_acceptance.py` is preserved in this directory but **could not be executed**: process launch of every local Python interpreter is denied by the sandbox (§1). The identical arithmetic and assertions were therefore executed with PowerShell `[double]` and `Get-FileHash`; raw results are in `assertions_raw.json` and `source_hashes.json`. `reconcile_acceptance.py` remains for Codex to re-run independently where Python is permitted.

---

## 1. Tooling, tooling failure and reproducibility

| Item | Result |
|---|---|
| Intended tool | `reconcile_acceptance.py` (Python 3 stdlib only: `hashlib`, `json`, `os`, `sys`) |
| Interpreter tried | `python` → `D:\Espressif\tools\python\python.exe`; also `D:\PROJECTS\dsharness\QS30-1\tools\review_venv\Scripts\python.exe` |
| Exact error | `ResourceUnavailable: Program 'python.exe' failed to run: 拒绝访问。` (access denied); via `System.Diagnostics.Process.Start`: `拒绝访问。` |
| PowerShell variants fails similarly | redirecting stdout gives `StandardOutputEncoding is only supported when standard output is redirected` on the same call path |
| Fallback actually used | PowerShell 7 `[double]` arithmetic + `Get-FileHash -Algorithm SHA256` → `assertions_raw.json`, `source_hashes.json`, `reconcile_stdout.txt` |
| Independent re-run command (Codex) | `python <OUTPUT_DIR>\reconcile_acceptance.py` (recomputes the same 26 assertions and writes `acceptance_budget.json`) |
| Simulators / solvers used | **none** (`solver: none`) |
| External URLs fetched | **none** — this task needed only local repository evidence |

No result below depends on a simulator, a download or a vendor document. Nothing was invented: every threshold literal is read from a hashed file, and every derived number is a closed-form expression reproduced in §3–§4.

---

## 2. Threshold reconciliation — controlling register

All acceptance thresholds are inherited **unchanged**. Two independent committed sources agree on the HV window, fault peak and startup limit; the remaining criteria come from the S05 baseline with its prose requirements file.

**Sources (all hashed, see `source_hashes.json`):**

| Key | Path | SHA256 | Tracking |
|---|---|---|---|
| `s05_config` | `projects/QS30-9_24V/config/sprint05.json` | `bce00036315e8119a4ecb27bcf94ba0a7882aa4e91bb2fd495b1b21c2c9fb86e` | COMMITTED (matches `calculations.json:"config_sha256"`) |
| `s05_requirements_md` | `projects/QS30-9_24V/docs/S05_REQUIREMENTS.md` | `b3566452f8e25c9bbe338f22feef5fb7cf2a7d30710a711732091a18269b49a9` | COMMITTED per wave-1 provenance scan |
| `safety_requirements` | `projects/QS30-9_24V/safety_r1/architecture/requirements.json` | `c354c0d926e16505f8ce896db9a034f3f209cc33cd33c675cc3827fbbf5a39df` | `COMMITTED_CLEAN` (wave-1) |
| `s06c_power_rails_json_uncommitted` | `HISTORICAL_Q/projects/QS30-9_24V/docs/sprint06c/POWER_RAILS.json` | `4f12bde1d1127a314860396c7623e03dfa2e6138a06afc85485d274fd250420d` | **UNCOMMITTED_PROVENANCE** |
| `sprint06_power_rails_csv_committed` | `projects/QS30-9_24V/docs/sprint06/POWER_RAILS.csv` | `8d898d91d824427e69904c0b58a9ac1dcd5a8b8b6ee4004aacc67fa7796d45d6` | COMMITTED |
| `sprint05_calculations` | `projects/QS30-9_24V/docs/sprint05/calculations.json` | `6f495d591bb37ab9da193d1080dcc59e90fd001aa7de587ee80e0209fe3a4165` | COMMITTED |
| `power_loop_calculations_independent` | `projects/QS30-9_24V/power_loop_r1/evidence/independent/calculations.json` | `867dc5015f29f88bb826935af4531dcbc079b36a0d396607b4203ea201102fb9` | TRACKED in new repo |
| `lo_r1_engineering_context` | `projects/QS30-9_24V/power_loop_r1/engineering_context.md` | `ffd4f115a101de461c3121f49955f7d12ece080fb1f13e5a7b38483025a7a31d` | UNTRACKED (run context; used only as *statement of intent*, superseded by the committed files for the numbers) |
| `round01_baseline_audit_result` | `.../round_01/baseline_audit/result.json` | `d9e5e931a23fb3ac92ef816fda19dfae1e347459541fed3e666fa891eb65ea01` | this run, worker output |
| `round01_baseline_math_worker_error_preserved` | `.../round_01/baseline_audit/baseline_math.json` | `c0be5f392b2aa447bf71182df557cb6992f487f4d46a2c0bdaba0384e3cb94b8` | this run, **contains preserved error** |
| `round01_hv_budget_reconciliation` | `.../round_01/baseline_audit/hv_budget_reconciliation.json` | `023ba40c72d890fb496a8020092851ec42078f55c04ae42b2fbeafaa18617b54` | this run |
| `safety_governance_holds` | `projects/QS30-9_24V/safety_r1/governance/holds.json` | `93a8eb434ad81029ab2c3577b3750777b6d0f4326708de06ef2f746e1c125e65` | `COMMITTED_CLEAN` |

> Note: `round01_baseline_audit/result.json` and `baseline_math.json` are hashed as they were **read by this worker**; `baseline_math.json` is deliberately **not** modified (its per-resistor error is preserved as instructed). Any hash drift here means a concurrent edit, which should be re-checked.

### 2.1 The reconciled register

| ID | Criterion | Value (UNCHANGED) | Machine sources | Assertion | Status |
|---|---|---|---|---|---|
| AC-1 | Input connector window | **21.6 … 26.4 V** | `sprint05.json:input.connector_continuous_V`; `S05_REQUIREMENTS.md` row 2 | `A01_vin_matches_sources` ✔ | UNPROVEN |
| AC-2 | HV steady mean | **164.9 … 175.1 V** | `sprint05.json:acceptance.HV_mean_V`; `requirements.json:thresholds_inherited.HV_mean_V`; `S05_REQUIREMENTS.md` row 5 | `A02_mean_matches_sources` ✔ | UNPROVEN |
| AC-2a | HV target (informative) | 170 V | `acceptance.HV_target_V` | `A08_target_inside_window` ✔ | informational — **not** an acceptance limit, and 172.18 V from earlier sprints is explicitly not a target |
| AC-3 | HV ripple | **≤ 1 Vpp**, 20 MHz-band limited, short ground spring | `acceptance.HV_ripple_Vpp_max`; `S05_REQUIREMENTS.md` row 5 | `A05_ripple_1Vpp` ✔ | UNPROVEN |
| AC-4 | Normal peak (startup + load step) | **≤ 180 V** | `acceptance.HV_normal_overshoot_V_max`; `S05_REQUIREMENTS.md` rows 5,6 | — | UNPROVEN |
| AC-5 | OVP actual trip | 183 … 190 V (allocation, no circuit) | `acceptance.OVP_trip_V`; `thresholds_inherited.OVP_trip_V` | `A07_ovp_gap_180_to_183` ✔ (3.0 V gap) | UNPROVEN, NO CIRCUIT |
| AC-6 | Specified-fault HV peak | **≤ 195 V** (target) | `acceptance.HV_fault_peak_V_max`; `thresholds_inherited.fault_peak_V_max` | `A03_fault_peak_matches_sources` ✔ | UNPROVEN — H05 P0 open |
| AC-7 | Cold startup | **COUT = 0 V → inside AC-2 window ≤ 1 s** | `acceptance.startup_s_max`; `thresholds_inherited.startup_s_max` | `A04_startup_matches_sources` ✔ | UNPROVEN — no simulation exists |
| AC-8 | Load-step recovery | **≤ 100 ms** (0.1 s) | `acceptance.load_step_recovery_s_max`; `S05_REQUIREMENTS.md` row 6 | `A06_recovery_100ms` ✔ | UNPROVEN |
| AC-8a | Load-step envelope | 160 … 180 V transient | `acceptance.load_step_envelope_V` | — | UNPROVEN |
| AC-9 | Load steps | 9 tubes × {0, 1.5, 2.25, 3} mA (blanking ↔ single ↔ nine) | `sprint05.json:loads`; `S05_REQUIREMENTS.md` row 6 | — | definitions only |
| AC-10 | Ambient | 0 … 50 °C; Tj ≤ 110 °C; inductor surface ≤ 100 °C | `acceptance.ambient_C`, `junction_C_max`, `inductor_surface_C_max` | — | UNPROVEN, no thermal evidence |
| AC-11 | Bleed observation target | ≤ 60 V in ≤ 5 s — **design only**, touch standard UNRESOLVED | `acceptance.bleed_design_only_V`, `thresholds_inherited.touch_safety_standard` | — | partially modelled at scaled 24 V (topology_r1/r2), not at HV |

**Nothing was retuned.** The run-context wording, the earlier `5.88985 W` floor, and every legacy figure are treated as *descriptions*, never as replacements for the committed literals above.

---

## 3. Bleeder delta — the two voltages must not be mixed

Topology (safety baseline): **two parallel strings of 2 × 90.9 kΩ = 181.8 kΩ each → R_total = 90 900 Ω**, replacing a single 200 kΩ bleeder.

| Quantity | Expression | Value | Assertion |
|---|---|---|---|
| P_total @170 V (all four resistors) | 170²/90900 | **0.3179317932 W** | `B02` ✔ |
| P per resistor @170 V (**corrected**) | (170/2)²/90900 | **0.0794829483 W** | `B03` ✔ |
| P per resistor @170 V (worker quoted, **WRONG**) | — | 0.0198707371 W | `B04` ✔ (error reproduced, file left unmodified) |
| P old 200 kΩ @170 V | 170²/200000 | 0.1445000000 W | — |
| **ΔP @170 V** | 0.3179317932 − 0.1445000000 | **0.1734317932 W** | `B05` ✔ |
| P_total @175.1 V | 175.1²/90900 | 0.3373426734 W | `B11` (rail V·I consistent) ✔ |
| P old 200 kΩ @175.1 V | 175.1²/200000 | 0.1533000500 W | — |
| **ΔP @175.1 V** | 0.3373426734 − 0.1533000500 | **0.1839937894 W** | `B06` ✔ |
| S06C HV_BUS @175.1 V (UNCOMMITTED allocation) | `POWER_RAILS.json:HV_BUS` | 5.7164233823 W (0.0326466213 A @175.1 V) | `B10` ✔ (self-labelled "allocations not measured") |
| **Revised upper-voltage HV budget** | 5.7164233823 + 0.1839937894 | **5.9004171717 W** | `B07` ✔ |
| Mixed-voltage lower-bound floor (context only) | 5.71642 (175.1 V base) + 0.17343 (170 V delta) | 5.8898517932 W (context quoted 5.88985) | `B08`, `B09` ✔ |
| Single resistor surviving a partner short @195 V, R−1 % | 195²/(90900×0.99) | 0.4225422542 W | `B12` ✔ |

**Reconciliation statement.** The **5.9004171717 W** figure is the controlling revised HV budget: it adds a bleeder delta evaluated at the *same* 175.1 V at which the S06C rail is declared. The **5.88985 W** figure mixes a 175.1 V base with a 170 V delta; it is a lower bound of **documentary context only**, is **not** an electrical acceptance criterion, and must never be substituted for 5.9004171717 W. The `B09` assertion records only that the correct figure is larger than the mixed floor — that inequality is not a performance claim.

**Caveats that keep this a budget, not a result:** both the S06C rail and the committed `sprint06/POWER_RAILS.csv` (5.71560370189665 W, also at 175.1 V) self-describe as *allocations*; neither is measured. The base is additionally uncommitted (`baseline_audit` BI-02/BI-03). The bleeder delta itself is a pure linear-resistor result and is exact for those resistances.

---

## 4. Cold (0 V) startup — analytic budget against the 1 s limit

Definition enforced (AC-7): COUT starts at exactly **0 V**; converter, controller bias, soft-start and OVP all evolve from t = 0. **Excluded** as autonomous-startup evidence: ideal HV precharge, forced gate PWM, forced VC/SS commands, and a 195 V absorbing/sourcing fixture (the S06F 195 V unit demonstrably *supplied* ≈10.317 µJ in a 140 ns window — `baseline_audit` BI-08).

| Quantity | Expression | Value | Assertion |
|---|---|---|---|
| C nominal (COUT 20 µF + module 0.3 µF) | `HV_candidate.COUT_F + module_C_F` | 20.3 µF | `C01` ✔ |
| C screen (Cmain +5 %, module +10 %) | `sprint05/storage.Ctotal_max_screen_F` | 21.33 µF | `C02` ✔ |
| Energy to reach 164.9 V, nominal | ½·20.3 µF·164.9² | **0.2759989015 J** | `C01` ✔ |
| Energy to reach 164.9 V, screen | ½·21.33 µF·164.9² | **0.2900027867 J** | `C03` ✔ |
| Minimum *net* charge power for 1 s, nominal | 0.2759989015 / 1 s | **0.2759989015 W** | `C04` ✔ |
| Minimum *net* charge power for 1 s, screen | 0.2900027867 / 1 s | **0.2900027867 W** | `C04` ✔ |
| Unavoidable load at the window floor (bleeders only) | 164.9²/90900 | 0.2991420242 W | `C05` ✔ |
| Minimum source power before conversion loss, screen | 0.2900027867 + 0.2991420242 | **0.5891448109 W** | `C05` ✔ |

**Feasibility statement (necessary, not sufficient).** To satisfy AC-7 the converter must average **≥ 0.276–0.290 W *net*** into COUT for a full second **while also** supplying **≥ 0.299 W** of bleeder load at the window floor and every switching, gate, core, snubber and bias loss — i.e. **≥ 0.589 W** of delivered power with zero margin for loss, at the *screen* capacitance and the *worst* cold condition, for the entire first second. Because HV power-stage efficiency is only *allocated* (≥ 0.75 in `sprint05.json:efficiency_allocations`), the required input-side power is at least ≈0.79 W at 21.6 V, before loss-model error. These numbers are arithmetic bounds from the hashed capacitance and bleeder values; they are **not** a startup simulation, they say nothing about loop stability, current limit, demagnetisation or clamp during the ramp, and no file in either workspace shows such a waveform.

---

## 5. Test-window obligations attached to each threshold

A threshold means nothing without the corners at which it is asserted. The following obligations are derived from `S05_REQUIREMENTS.md` plus the existing (but unrelated) corner matrices, and are issued as **requirements for the later simulation tasks**, not as results.

| Axis | Obligation | Evidence that it is currently unmet |
|---|---|---|
| Vin | 21.6, **24.0**, 26.4 V | every existing corner set (`docs/sprint06b/LOSS_AWARE_DCM_CORNERS.json`, `docs/sprint06c/NEW_CONTROLLER_CORNERS.json`) uses **20.5 V** (the *inductor-side* minimum after ≤1.1 V path drop), 24 V and 26.4 V — **21.6 V is absent from every axis** (checked directly; `21.6 ∈ Vin? = False` for both) |
| L, f | 121.5/150/165 µH, 85/100/115 kHz (S06C) and 93.5/110/126.5 kHz (S06B loss-aware) | existing, but efficiency variants are screens only (η = 0.75/0.8/0.85/1), not measurements |
| Load | 0, 1.5, 2.25, 3 mA/tube × 9 tubes; steps in both directions, measured at t_step + 100 ms | no step simulation exists |
| Temperature | 0 °C and 50 °C | all existing cells are 25 °C |
| Ripple | must be reported **both** raw (unbanded) and as a 20 MHz-band-limited bound; ASCII raw is unbanded | the requirement's band-limited definition cannot be satisfied by raw SPICE alone — a band-limiting statement is mandatory |
| Startup | C(0) = 0 V exact; log V_HV, I_L, V_gate, VC/SS *and* the protected-node clamp continuously from t = 0 for ≥1 s | none |
| Fault | enumerated single faults only (feedback open, MCU runaway); no absorbing HV source; measure peak and residual energy | none; H05 open |

---

## 6. Documented worker defect carried forward (do not "fix" silently)

`baseline_audit/baseline_math.json` reports `P_per_unit_W = 0.0198707371 W` for each 90.9 kΩ resistor at 170 V. The correct value is **0.0794829483 W** — a factor 1/4 error (the correct expression is (170/2)²/90900, i.e. series-partner voltage division). The file is **left byte-identical** (hash `c0be5f39…`); this task records the correction in `B03`/`B04` and in this section rather than editing another wave's output. Any downstream consumer that multiplies `P_per_unit × 4` to obtain total bleed power gets 0.0795 W instead of 0.3179 W and would understate the safety budget by ~75 %.

---

## 7. What is proven, and what is not

**Proven by this task (analytical / documentary only):**
1. All eight mandatory acceptance literals are reproduced from two or more independent committed sources and are **unchanged** (26/26 assertions `ok` in `assertions_raw.json`).
2. The revised HV budget at 175.1 V is **5.9004171717 W** (base 5.7164233823 W + bleeder delta 0.1839937894 W at the same voltage); the mixed-voltage 5.88985 W figure is a lower-bound context value only.
3. Corrected per-resistor bleeder power at 170 V is **0.0794829483 W**; the wave-1 worker value is wrong by ~4× and preserved, not propagated.
4. A cold 0 V startup to the window floor needs **≥ 0.276 J (nominal) / ≥ 0.290 J (screen)**, i.e. ≥ 0.276–0.290 W net into COUT **plus** ≥ 0.299 W of bleeder load, for one full second — a necessary condition no existing evidence addresses.

**Not proven (blocking, see `result.json:blocking_issues`):**
- Every electrical criterion AC-1…AC-11 is **UNPROVEN**: there is no closed-loop, cold-start, corner-step, ripple, recovery or fault waveform anywhere in the committed or uncommitted evidence reviewed.
- 21.6 V (and 24.0 V in the S06C set) is missing from every existing corner axis, so even the *plan* for AC-1 corner coverage is incomplete.
- The 195 V fault-peak target has no OVP circuit and no energy accounting; H05 is P0-open and the S06F 195 V fixture is a source, not a clamp.
- No thermal evidence at 0/50 °C.
- Manufacturing **HOLD** and every `safety_r1` HOLD (H01–H10) are untouched by this document.

---

## 8. Evidence index (this directory)

| File | Contents |
|---|---|
| `inventory.md` | this document |
| `result.json` | task result contract |
| `acceptance_budget.json` | machine-readable threshold register, bleeder and cold-start reconciliation, assertions |
| `assertions_raw.json` | the 26 executed assertions (PowerShell `[double]`) |
| `source_hashes.json` | SHA256 + byte size + relative path of every cited source |
| `reconcile_acceptance.py` | intended Python driver, **not executed** (sandbox denied interpreter launch); kept for independent re-run |
| `reconcile_stdout.txt` | captured console output of the PowerShell reconciliation runs, including the Python launch failure |
