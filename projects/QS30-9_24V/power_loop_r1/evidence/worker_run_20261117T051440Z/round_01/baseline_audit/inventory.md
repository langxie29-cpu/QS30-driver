# baseline_audit — Committed 24V/S06C + safety R1 baseline and control-variant inventory

- **Task ID:** `baseline_audit` (role: `historical_auditor`, kind: `analysis`)
- **Run:** `20261117T051440Z` / `round_01`
- **Worker:** deepseek-flash (low-cost execution agent)
- **Status of this document:** inventory only. **No claim herein is a design approval.** All vendor/electrical entries remain preliminary `WORKER_CLAIMS`.
- **Physical operations performed:** none. No HV energisation, no fabrication, no part purchase, no device programming, no instrument connection.
- **Simulations executed by this worker:** none. This is a read-only documentary audit; no simulator was invoked and no waveform, log or metric was generated here. Every numeric value below is **transcribed from a source file that already existed**, with its SHA256 recorded.

> **Reading rule applied throughout.** A value appearing in a *committed* file and the same value appearing in an *uncommitted* file are **not** interchangeable evidence. Uncommitted material is reported as `UNCOMMITTED_PROVENANCE` and is never promoted to PASS.

---

## 1. Method and tooling provenance

`git.exe` **cannot be launched** in this sandbox (the process spawn is denied: `Program 'git.exe' failed to run: 拒绝访问` / *access denied*). Provenance was therefore established **without git**, by parsing the git index binary format directly with Python 3.11.15:

| Artefact | Purpose |
|---|---|
| `read_git_index.py` | Parses the `QS30-power-loop-r1` worktree index (`.git/worktrees/QS30-power-loop-r1/index`, `DIRC` v2) → `index_entries.json`, `index_parse.txt` |
| `scan_provenance.py` | Walks the worktree, recomputes the git blob SHA (`sha1("blob <len>\0" + bytes)`) per file, compares to the index → `provenance_scan.json`, `provenance_scan.txt` |
| `read_git_index_historical.py` | Same index parse for the historical repo `QS30-1/.git/index` → `index_entries_historical.json`, `index_parse_historical.txt` |
| `scan_provenance_historical.py` | Provenance scan of the read-only historical workspace → `provenance_scan_historical.json`, `provenance_scan_historical.txt` |
| `hash_cited.py` | SHA256 of every artefact cited here → `cited_artifact_hashes.json`, `cited_artifact_hashes.txt` |

Repository/worktree identity, read from git metadata files:

| Item | Value |
|---|---|
| Worktree `.git` | `gitdir: D:/PROJECTS/dsharness/QS30-1/.git/worktrees/QS30-power-loop-r1` (linked worktree of the historical repo) |
| Worktree HEAD ref | `refs/heads/nxt/qs30-power-loop-engineering-r1` |
| Worktree HEAD commit | `6be8cbbf4729dacae8aced5981f9d5f32703f27b` (`ORIG_HEAD` identical; reflog shows `reset: moving to HEAD`) |
| Historical repo HEAD | `refs/heads/nxt/qs30-hv-safety-r1` → `b12cd112ad6a204bfb50c41266cf287fa971a8ce` |
| Safety-r1 stated work branch | `nxt/qs30-hv-safety-r1`; baseline `nxt/reva9-electrical-sprint03` @ `ee53f81c3f93539906445482bd17e564829338ef` |

Because `git status` could not run, the commit/branch metadata above are read as **files**, not as a verified git query. This is stated as a limitation, not hidden.

---

## 2. Provenance results — what is actually committed

### 2.1 Prospective repo (`QS30-power-loop-r1`), `projects/QS30-9_24V/**`

| State | Count |
|---|---|
| `COMMITTED_CLEAN` (index blob SHA == worktree blob SHA) | **1483** |
| `TRACKED_MODIFIED` | **3** |
| `UNTRACKED` | **17** |

The 3 tracked-modified and the only non-output untracked files are harness scaffolding, **not** electrical evidence:

| State | Path |
|---|---|
| `TRACKED_MODIFIED` | `power_loop_r1/.gitignore` |
| `TRACKED_MODIFIED` | `power_loop_r1/config.json` |
| `TRACKED_MODIFIED` | `power_loop_r1/orchestrate.py` |
| `UNTRACKED` | `power_loop_r1/engineering_context.md` |
| `UNTRACKED` | `power_loop_r1/local_live.py`, `power_loop_r1/local_probe.py` |
| `UNTRACKED` | `power_loop_r1/runs/20261117T051440Z/**` (this run's own output) |
| `UNTRACKED` | `power_loop_r1/.local/**` (sandbox home, credentials — **not inspected, not copied**) |

**All `safety_r1/**` files in the prospective repo are `COMMITTED_CLEAN`.**

### 2.2 Historical workspace (`QS30-1/projects/QS30-9_24V`), read-only

| State | Count |
|---|---|
| `COMMITTED_CLEAN` | **1474** |
| `TRACKED_MODIFIED` | **3** |
| `UNTRACKED` | **1557** |

### 2.3 The decisive finding — S06C–F are uncommitted there too

Only **two** S06C documentation artefacts are tracked in the index:

| Path | Index blob |
|---|---|
| `docs/S06C_PLAN.md` | `d251ee6e4618…` |
| `docs/sprint06c/input_snapshot.json` | `6a9eea15e9c7…` |

Everything else is **`UNTRACKED`**: `SPRINT06C_REPORT.md`, `SPRINT06D_REPORT.md`, `SPRINT06E_REPORT.md`, `SPRINT06F_REPORT.md`, all of `docs/sprint06{c,d,e,f}/`, all of `design/s06{c,d,e,f}_*.py`, and `config/sprint06{c,d,e,f}.json`.

> **Therefore there is no "committed 24V/S06C" power budget.** The S06C *results* — including the very `5.71642 W` figure quoted in the run context — exist only as uncommitted working-tree files. The committed 24V electrical state is S06/S06B.

The committed S06C artefacts are a **plan** (pre-registration) and an **input snapshot** — i.e. intent and inputs, not outcomes. S06C itself records this honestly: its `final_verification.json` carries `"status": "PRESERVATION_AND_SCOPED_UNIT_REVIEW_NOT_RELEASE"` and `"native_generated": false`.

### 2.4 Historical workspace git provenance caveat (quoted, not resolved)

`safety_r1/governance/BASELINE.md` (committed) states the historical repo was taken over with `README.md`, `project.json` and `TASKS.csv` already modified plus "大量S06C–F未跟踪成果" (*a large body of untracked S06C–F results*) — all preserved and deliberately **not** committed. `BASELINE.md` also warns explicitly that a later LT3757A alternative candidate exists, so the UCC-based S06 power scheme **cannot be assumed to remain the only valid baseline**. That warning is honoured in §5.

---

## 3. Baseline and control-variant table

The table separates **committed** from **uncommitted**, and records each source's *own* verdict verbatim. `—` means the source states no such value.

### 3.1 Power / budget baseline

| # | Quantity | Value | Evaluated at | Provenance | Source's own scope string |
|---|---|---|---|---|---|
| B1 | `HV_BUS` rail power | **5.71560 W** (5.71560370189665) | **175.1 V**, 32.642 mA | **COMMITTED** `docs/sprint06/POWER_RAILS.csv` | "31mA-class load; changed feedback consumption included" |
| B2 | `HV_BUS` rail power | **5.71642 W** (5.716423382277459) | **175.1 V**, 32.647 mA | `UNCOMMITTED_PROVENANCE` `docs/sprint06c/POWER_RAILS.json` | "external24V candidate, **allocations not measured**" |
| B3 | `AUX12` rail | 1.24861 W (committed) vs 1.20154 W (uncommitted) | 12.6 V | both as above | subset relations differ between the two |
| B4 | `VIN24` total | 13.86282 W (committed) vs 13.80507 W (uncommitted) | 21.6 V | both as above | "total with efficiency allocations; not measured" |
| B5 | Mainboard bleeder, revised | **0.31793 W** | 170 V, R=90.9 kΩ | **COMMITTED** `safety_r1/circuit/bleeder_revision.csv` (8 × 90.9 kΩ) | independently recomputed, §3.3 |
| B6 | Mainboard bleeder, old single 200 kΩ | 0.14450 W | 170 V | run context / derived | independently recomputed |
| B7 | Bleeder delta | **+0.17343 W** | 170 V | derived | independently recomputed |

**Critical reconciliation (my arithmetic, `hv_budget_reconciliation.json`).** The run-context wording "S06C updated HV budget 5.71642 W" **traces to the uncommitted S06C file, not to the committed baseline**, and neither figure is evaluated at 170 V — both use the 175.1 V upper acceptance bound.

| Base used | Base + 0.17343 W delta | vs stated floor 5.88985 W |
|---|---|---|
| **Committed** 5.71560370189665 | **5.88904 W** | **FAILS** the floor by 0.00081 W |
| Uncommitted 5.716423382277459 | 5.88986 W | passes, by +0.00001 W (1×10⁻⁵ W — effectively at the boundary) |

The two figures differ by only 0.00082 W, and the pass/fail of the quoted ≥5.88985 W statement depends entirely on which base is adopted. This is **not** a threshold change request — the floor is untouched. It is a provenance defect that must be resolved by the owner of the budget before the number is used downstream. Flagged as blocking issue **BI-02**.

### 3.2 Control variants actually exercised (all uncommitted)

| Variant | Fixture | Qualification string (verbatim) | Measured values | Provenance |
|---|---|---|---|---|
| LT3757AIMSE#PBF + original-byte ST STP9NK50Z | forced-CS gate cell, **resistor load**, 25 °C, AUX12/12.6 V | `PASS_NOMINAL_FORCED_CS_GATE_CELL_ONLY` | delay 230.8792 ns (AUX12) / 233.4645 ns (AUX12.6); half-step Δ 0.31978 ns / 0.18052 ns; current rel. Δ 0.0635 % / 0.0906 % | `UNCOMMITTED_PROVENANCE` `docs/sprint06c/NOMINAL_GATE_QUALIFICATION.json` |

The cell's own `scope` field disclaims exactly the extensions a reader might assume: *"Only original ADI+ST25C forced-CS transistor resistor-load cell. Does not qualify real current feedback, hot magnetics, source-loss, startup, short circuit or voltage loop."* `SPRINT06C_REPORT.md` reinforces it: *"独立强制CS门驱的约230ns不能替代这些真实采样证据"* — the independent ~230 ns forced-CS figure cannot replace real sampling evidence. It also records that the ~110 mV nominal hard-comparator threshold is **not** demonstrated (1.66 A corresponds to ~103 mV, below the 110 mV threshold) and that VC is model-clamped near 1.78 V, so hard current limiting is **unproven**.
| Original topology, Gear 0.5 ns | real sampling cell | execution `PASS` | VGS_min −5.4710 V, SENSE_peak 0.115699 V, IL_peak 1.66243 A, gate_peak 1.49871 A, snubber mean 0.24321 W | `UNCOMMITTED_PROVENANCE` `docs/sprint06d/observer_control.json` |
| Original topology, Gear 0.25 ns | real sampling cell | execution `PASS` | VGS_min **−8.1587 V**, SENSE_peak **0.192456 V**, IL_peak 1.66247 A, gate_peak 2.21740 A, snubber mean 0.24559 W | `UNCOMMITTED_PROVENANCE` same file |
| Trap 0.125 / 0.25 ns, port-control | original topology | execution `PASS` (0–60 µs) | not tabulated here | `UNCOMMITTED_PROVENANCE` `docs/sprint06e/final_verification.json` |

The two `execution: PASS` rows are **solver-execution** verdicts, not electrical ones. Halving the timestep moves `SENSE_peak` from 115.7 mV to 192.5 mV (+66 %) and `VGS_min` from −5.47 V to −8.16 V, with `IL_peak` essentially unchanged (1.6624 A) — i.e. **the fast extrema are not step-converged**, which is exactly why every sprint refuses to pass the cell. `sprint06d` states `"electrical_qualification": "NOT_PASSED_FAST_EXTREMA_CONVERGENCE"`.

### 3.3 Independent recomputation of the safety baseline (`recompute_baseline.py`, `baseline_math.json`)

| Assertion | Expected | Measured | Result |
|---|---|---|---|
| R per string = 2 × 90.9 kΩ | 181 800 Ω | 181 800 Ω | **ok** |
| 170 V bleeder power (2 strings) | 0.31793 W | 0.31793 W | **ok** |
| Old single 200 kΩ @170 V | 0.1445 W | 0.14450 W | **ok** |
| Delta | 0.17343 W | 0.17343 W | **ok** |
| S06C + delta ≥ 5.88985 W | ≥ 5.88985 W | 5.88985 W (uncommitted base) | **ok** *only on the uncommitted base* — see §3.1 |

Per-unit dissipation 19.87 mW; per string 158.97 mW. Topology (`bleeder_revision.csv`) confirmed as **two parallel strings** `RBL_A1+A2` (HV_BUS→BLEED_A_MID→HV_RETURN_A) and `RBL_B1+B2` (HV_BUS→BLEED_B_MID→HV_RETURN_B) — matching the run-context description exactly. Every row is `HOLD_EXACT_MPN` / `HOLD_CANDIDATE_ONLY`.

### 3.4 Sprint status matrix — every layer refuses to pass

| Source | 24V-07 | 24V-08 | 24V-09 | 24V-10 | manufacturing | native_generated | ERC/DRC | Provenance |
|---|---|---|---|---|---|---|---|---|
| sprint06 (committed) | NOT_PASSED | NOT_ENTERED | — | — | **HOLD** | false | NOT_RUN_NO_NATIVE24V_DESIGN | **COMMITTED** |
| sprint06b (committed) | NOT_PASSED | NOT_ENTERED | — | — | **HOLD** | false | NOT_RUN_NO_QUALIFIED_NATIVE_DESIGN | **COMMITTED** |
| sprint06c | NOT_PASSED | NOT_ENTERED | — | — | **HOLD** | false | NOT_RUN_NO_QUALIFIED_NATIVE_DESIGN | `UNCOMMITTED` |
| sprint06d | NOT_PASSED | NOT_ENTERED | — | — | **HOLD** | false | NOT_RUN_NO_QUALIFIED_NATIVE_DESIGN | `UNCOMMITTED` |
| sprint06e | NOT_PASSED | NOT_ENTERED | — | — | **HOLD** | false | NOT_RUN_NO_QUALIFIED_NATIVE_DESIGN | `UNCOMMITTED` |
| sprint06f | NOT_PASSED | NOT_ENTERED | — | — | **HOLD** | false | NOT_RUN_NO_QUALIFIED_NATIVE_DESIGN | `UNCOMMITTED` |
| **safety_r1** | NOT_PASSED | NOT_ENTERED | **NOT_PASSED** | **NOT_PASSED** | **HOLD** | — | — | **COMMITTED** |

There is **no disagreement to adjudicate**: committed and uncommitted sources independently reach the same NOT_PASSED / HOLD state, and safety_r1 additionally fails 24V-09 and 24V-10. The uncommitted sprints therefore cannot be used to *elevate* the baseline — they only add detail on *why* it fails.

---

## 4. Uncommitted S06D/E/F claims — flagged, not adopted

These exist as real files, were opened and hashed. They are recorded as **`UNCOMMITTED_PROVENANCE` claims** and are **not** evidence for any PASS.

| ID | Claim | Source | Source's own verdict | Auditor classification |
|---|---|---|---|---|
| C05 | Real sampling cell unqualified; 0.5→0.25 ns refinement failed | `sprint06d/final_verification.json` | `NOT_PASSED_FAST_EXTREMA_CONVERGENCE` | `UNCOMMITTED_CLAIM_FOR_INFO_ONLY` — consistent with committed NOT_PASSED |
| C06 | Gear 0.5 ns: VGS_min −5.471 V, SENSE_peak 115.699 mV | `sprint06d/observer_control.json` | execution PASS | `UNCOMMITTED`, superseded by C07 at finer step |
| C07 | Gear 0.25 ns: VGS_min −8.159 V, SENSE_peak 192.456 mV | `sprint06d/observer_control.json` | execution PASS | `UNCOMMITTED`, **shows non-convergence** |
| C08 | Cross-method SENSE delta 5.476 mV exceeds pre-registered 5 mV | `sprint06e/final_verification.json` | `FAIL_CONVERGENCE` | `UNCOMMITTED`, a **failure** not a pass |
| C09 | US1G commutation fixture: original recovery 50.353 ns, reverse peak 1.000 A | `sprint06f/diode_unit_results.json` | original `PASS`; `TT0_DIAGNOSTIC` `FAIL` (0.672 A vs required 1.0 A) | `UNCOMMITTED`; TT0 explicitly "NOT actual components" |
| C10 | TT0 intervention inconclusive | `sprint06f/final_verification.json` | `INCONCLUSIVE` (3 of 4 comparisons) | `UNCOMMITTED_INCONCLUSIVE` |
| C11 | 195 V ideal source supplied ≈10.317 µJ in one 140 ns window | `SPRINT06F_REPORT.md` | stated as a boundary caveat | `UNCOMMITTED`; directly supports "195 V absorbing source ≠ autonomous operation" |

**Explicitly not adopted.** No S06D/E/F number is used to close a hold, to justify a component choice, or to assert convergence. C09's `PASS` is a *fixture-conditions* pass on a vendor diode model, self-labelled by its own file as "no replication/qualification claim". Where C06 and C07 disagree, C07 (finer step) is reported as evidence of **instability**, not as the better result.

---

## 5. Preserved HOLDs (unchanged by this audit)

`safety_r1/governance/holds.json` (committed, SHA256 `93a8eb43…`) — **all ten P0 blockers remain OPEN, verbatim, unmodified**:

| ID | Subject (abridged) |
|---|---|
| H01 | Complete-request, manual events, window watchdog, power-valid, set-dominant fault hardware unqualified |
| H02 | eFuse encrypted dynamic model, RTN isolation incl. FLT/IMON, hot leakage, shutdown maxima missing |
| H03 | Physical MOS short, branch stuck-on, input passive path, fuse coordination not contained by logic proof |
| H04 | Independent residual-measurement divider-open/ground-open coverage incomplete |
| H05 | **OVP peak-195 V total detection/actuation/remaining energy not validated** |
| H06 | Real current limit, hot magnetics, controller startup/demagnetisation, closed loop 07/08 unqualified |
| H07 | USB/5 V failure OVP, brownout, partial-power backfeed not electrically qualified |
| H08 | Bleeder single faults / modules removed and touch criterion; five-second envelope can fail |
| H09 | Thermal sensor exact MPN, tolerance, coupling and lead faults unqualified |
| H10 | Native EDA/ERC/DRC, footprints/LCSC mapping, HV spacing basis incomplete |

`release_policy`: *"No automatic HOLD closure; green software CI only validates its documented finite scope."*

Additionally `HOLD_REGISTER9.md` at repo root lists H9-01 … H9-12, **all `OPEN`** (H9-04 OVP polarity, H9-06 native EDA/ERC/DRC, H9-09 HV bench, H9-11 light-load DCM stability). `manufacturing = HOLD` is preserved and untouched.

Note the layering discipline safety_r1 itself enforces: *"保护逻辑模型通过、低压行为SPICE通过、厂商器件单元通过、完整硬件安全验证是四个不同层级。前两层不得关闭24V-07/08/09或制造HOLD"* — logic-model pass, low-voltage behavioural SPICE pass, vendor cell pass, and full hardware safety verification are four different levels, and the first two may never close 24V-07/08/09 or the manufacturing HOLD. This audit applies that rule to the uncommitted sprints.

`safety_r1/verification/verification_summary.json`: 245 software tests, 0 failures; 45 native process attempts; 41 saved-execution validation passes / 4 fails. Those failures are retained, not repaired: four `spice_r1` cases have repeated timestamps in rounded ASCII, so strict-order validation FAIL is kept and the missing electrical classification is **INCONCLUSIVE, not PASS**.

---

## 6. Toolchain and model provenance (hashed, unmodified)

All model/executable bytes were **hashed only**. Nothing was extracted, rewritten, converted or executed by this worker.

| Component | SHA256 | Notes |
|---|---|---|
| `LTspice.exe` | `17f5efb978c0df2e164328b7352801fdc1ed0225827e41669bd9da25893fe96d` | **Reproduces S06C's independently recorded `exe_sha256`** |
| `LTspice64.msi` | `62a9f20b630738e6ade20a37551baa91b20760bfb718807d8a2be4caa3421a36` | **Reproduces S06C's recorded MSI hash**; origin `https://ltspice.analog.com/download/latest/LTspice64.msi` |
| `extracted/lib.zip` | `dd0028bb12e3f432ef022570cb7cf64d3c87288c35d1e8159658a4ff986ce094` | located at `toolchain/ltspice26/extracted/lib.zip` |
| `extracted/examples.zip` | `319ac0e9adcce7e156aa47050a659919dbd901f1e82ab42fdb156bcefcd54ad6` | located at `toolchain/ltspice26/extracted/examples.zip` |
| `License.txt` | `a3c9a713f97ee80f5731b7f13b00ad87f69a17fe505a8ad837dc6ff66c391c4e` | model/tool license artefact, preserved |
| `ngspice_con.exe` | `22d5cae2bd32b2e39157a8d27bf457122f68285b72a9ebefdf41551b628233ab` | present; version string **not verified by execution** |
| STP9NK50Z vendor model | `6ad61988b9e045684dc8271bc51ddfdca00d65b745e6edd6c4492a42df1ad7a4` | `sources/sprint06b/ST_model_cn/unpacked/stp9nk50z.lib` |
| Vishay US1G model | `f8669a85e8f3ed412ba97ab72bc6b7b0facbdf57111187ede39a365801324ec3` | **matches `model_sha256` recorded inside S06F's diode results** |
| UCC28C43 PSpice (unencrypted) | `ab3cd5bb484570e3e719d7f1d1a5dcf9e0ef48161a9d00eaa84d34dcf5ec26b8` | `UCCx8C43_unencrypted/…/ucc28c43_trans_unencrypted.lib` |
| UCC28C43 PSpice (2008 dist.) | `546fab4c7b9208394122f7f4e886496d15e2811af37b4e32cb9edff2eddeaadd` | `UCC28C43_pspice/…/ucc28c43.lib` |
| UCC28C43 TINA | `7b00c5326308d7203d75fa0e77870ed0dd2482305199f88eff67682827d9526a` | `UCC28C43_startup/…/UCC28C43_START.LIB` |

**Known version caveat, quoted from S06C and preserved:** the folder is named `ltspice26` and the URL says `latest`, but the actual executable version is **24.0.12.0**. S06C records `"folder_name_is_not_version": true`. This audit adopts 24.0.12.0 as the real version. The TI UCC28C43 PSpice/TINA archives are **present as bytes**; whether any native TI solver can execute them is **not established here** and is left to `vendor_models` / `ucc28c43_reference`.

---

## 7. Blocking issues (things this audit did not prove)

1. **BI-01 — No committed S06C electrical result exists.** S06C's report, evidence tree, configs and scripts are `UNTRACKED` in both repos. The committed 24 V state is S06/S06B only. Any downstream task consuming "S06C" numbers is consuming uncommitted working-tree material.
2. **BI-02 — The quoted 5.71642 W traces to an uncommitted file and changes the floor verdict.** Committed base yields 5.88904 W against a 5.88985 W floor (**fails**); uncommitted base yields 5.88986 W (passes by 10⁻⁵ W). Base must be designated before use.
3. **BI-03 — Neither HV budget is measured.** Both sources self-label the rail as an allocation ("allocations not measured" / "not measured"). No wattage here is a measurement.
4. **BI-04 — Fast-extrema non-convergence is unresolved.** Refining 0.5→0.25 ns moves SENSE_peak +66 % and VGS_min −5.47→−8.16 V while IL_peak is flat; S06E's 5.476 mV cross-method delta exceeds the pre-registered 5 mV. The real sampling cell is unqualified at every step tried.
5. **BI-05 — No native 24 V design exists.** Every sprint reports `native_generated: false` and `ERC_DRC: NOT_RUN_*`. Nothing here supports native EDA/ERC/DRC.
6. **BI-06 — git could not be invoked.** Provenance rests on direct binary index parsing plus file-level blob-SHA comparison; branch/HEAD values are read from metadata files, not from a git query. Re-verification with a working `git` is recommended.
7. **BI-07 — S06D/E/F remain uncommitted and inconclusive.** Per C10, three of four S06F comparisons are `INCONCLUSIVE` and two executions did not complete. Nothing in S06D–F closes 24V-07/08.
8. **BI-08 — H05/peak-195 V unvalidated, and the 195 V source is not an absorber.** S06F measured the ideal 195 V source *supplying* ≈10.317 µJ in a 140 ns window, confirming by direct evidence that the existing fixture cannot stand in for autonomous startup or for a genuine clamp.
9. **BI-09 — Mandatory acceptance criteria remain entirely untested.** Vin 21.6–26.4 V, mean 164.9–175.1 V, ripple ≤1 Vpp, normal peak ≤180 V, genuine C_out(0 V) startup ≤1 s, recovery ≤100 ms and fault peak ≤195 V have **no** supporting simulation anywhere in the committed or uncommitted evidence reviewed.

---

## 8. Conclusion

The committed baseline is **S06/S06B at 24V-07 `NOT_PASSED`, 24V-08 `NOT_ENTERED`, manufacturing `HOLD`**, with `HV_BUS` = **5.71560 W @ 175.1 V** as an *allocation*. The safety baseline (two parallel 2 × 90.9 kΩ strings, 0.31793 W @ 170 V, delta +0.17343 W over the old 200 kΩ) is **independently reproduced** and correct, but the composite "≥5.88985 W" statement depends on adopting the **uncommitted** S06C base.

S06C–F genuinely exist and are genuinely uncommitted. They are detailed, self-critical, and they report **failure or inconclusive at every level**. They are recorded here as `UNCOMMITTED_PROVENANCE` claims; none has been promoted. The committed safety_r1 HOLDs (H01–H10, H9-01–H9-12) are preserved unmodified.

**This document is an inventory, not an approval.** It contains no PASS recommendation for any electrical, thermal, model, or manufacturing item.

---

## 9. Evidence files (all inside this output directory)

| File | Contents |
|---|---|
| `inventory.md` | **This document** |
| `result.json` | Machine-readable result |
| `provenance_scan.json` / `.txt` | Worktree vs git-index provenance, 1500+ files |
| `provenance_scan_historical.json` / `.txt` | Historical workspace provenance, 3000+ files |
| `index_entries.json`, `index_parse.txt` | Parsed worktree git index |
| `index_entries_historical.json`, `index_parse_historical.txt` | Parsed historical git index |
| `cited_artifact_hashes.json` / `.txt` | SHA256 of every cited artefact |
| `baseline_math.json` | Bleeder/budget arithmetic with explicit assertions |
| `hv_budget_reconciliation.json` | Committed-vs-uncommitted HV budget reconciliation |
| `claim_register.json` | S06C–F claim register with provenance labels |
| `control_variants_raw.json` | Control-variant values as extracted |
| `read_git_index.py`, `scan_provenance.py` | Worktree provenance tooling |
| `read_git_index_historical.py`, `scan_provenance_historical.py` | Historical provenance tooling |
| `recompute_baseline.py`, `reconcile_hv_budget.py` | Independent arithmetic |
| `extract_controls.py`, `build_claim_register.py`, `hash_cited.py` | Extraction tooling |
