# sense_candidate — Round 2 inventory (CODE ONLY, NOTHING EXECUTED)

**Task:** `sense_candidate` / role `approved_sense_fix` / kind `analysis`
**Round-2 override:** CODE GENERATION ONLY. No shell, no simulator, no LTspice invocation, no git,
no downloads, no recursive agents. All writes are inside this OUTPUT_DIR.

## What the approved decision actually permits
Read from `power_loop_r1/engineering_context.md`, `power_loop_r2/engineering_context.md` and
`power_loop_r2/ROUND1_REVIEW.md` (lines 6 and 7):

| Item | Approved content | Status here |
|---|---|---|
| Minimum switching cell | precharged 89.17 V / IL 1.4 A, finite 20 ns gate edge, original power parts, zero-volt terminal probes | drafted in `build_minimum.py` |
| Local cases | exactly **3**: Gear 1 ns, Gear 0.5 ns, Trap 1 ns | exactly 3, no extra fixtures |
| Runtime | 30 s per local run | `TIMEOUT = 30` |
| Purpose | diagnose recovery/gate/parasitics with exact current KCL — **not** cold startup, **not** a replacement controller | no such claim made |
| SENSE candidate | keep RSRC 62 mΩ, RG 22 Ω and all power parts; change **only** the sense RC filter 10 Ω/1 nF → 22 Ω/4.7 nF as ONE design choice | drafted in `build_filter.py` |
| Candidate runs | **initial full 60 ms run only**; no automatic retuning if it fails | exactly 1 case |
| Clamps | none that hides a sustained short | built netlist is asserted free of added clamp devices |
| Models | no vendor model modification | models copied byte-for-byte and re-hashed vs R1 |

## Delivered files (all inside this directory)

| File | Kind | Purpose |
|---|---|---|
| `build_minimum.py` | DRAFT script | builds the 3 approved local-case trees + model copies + `build_receipt.json`; calls no solver |
| `build_filter.py` | DRAFT script | builds the single approved 60 ms filter-case tree + `filter_receipt.json`; calls no solver |
| `inventory.md` | required evidence | this file |
| `result.json` | required evidence | worker result |

No `circuit.cir`, `run.log`, `waves.txt`, `metrics.json` exist for this task **and none may be
claimed**: the round-2 override forbids execution. None were fabricated.

## Source evidence read (read-only, inside REPO_ROOT)

| Path | Why |
|---|---|
| `projects/QS30-9_24V/power_loop_r2/ROUND1_REVIEW.md` | the decision (lines 6, 7) and the workflow nonconformance to avoid (line 4) |
| `projects/QS30-9_24V/power_loop_r2/engineering_context.md` | R2 context + round-2 override |
| `projects/QS30-9_24V/power_loop_r2/lab.py` | shared helper API actually used (`sha`, `MODEL_SOURCE`, `BASE`, `execute`, `native`) |
| `projects/QS30-9_24V/power_loop_r2/evidence/principal/unchanged_200ms/circuit.cir` + `preregister.json` | unchanged-baseline netlist, model hashes, acceptance thresholds |
| `projects/QS30-9_24V/power_loop_r1/evidence/candidate_diagnostic/nominal_24V_gear_resource600/circuit.cir` | the `lab.BASE` text both builders transform |
| `runs/.../round_01/passive_bounds/run_passive_bounds.py` | R2 house style for anchors, overwrite refusal, receipts |

Note: the round-1 passive runner in the tree is the v2 draft that applies an **unapproved**
`REN1/REN2 → VEN en 0 0` SHDN hold. Neither builder here copies that policy: `REN1 in en 200k` /
`REN2 en 0 12.8k` are left exactly as in the baseline, because the sense-fix decision does not
authorise a SHDN change.

## Assumptions recorded so they can be audited, not buried

1. **Initial conditions for 89.17 V.** Divider string 100 k + 100 k + 1900.6 Ω:
   `I = 89.17/201900.6 = 441.65 µA`, `V(fbmid)=45.017 V`, `V(fb)=0.83948 V`. Both nodes are
   initialised (an L1/latch failure here would silently put a wrong voltage on the feedback input).
2. **Switch node is deliberately NOT initialised.** No approved value exists for `V(drain)` at
   t=0, and writing 0 would make the cell quietly wrong. B1 sources are unset for the same reason
   (`V(drain) > 89.17 V` in the recovery regime).
3. **LPOWER IC list.** LTspice takes the first numerical value of an `IC=` list, so
   `LPOWER in drain 150u Rser=.16 IC=(1.4,0,0,0,0)` (5 spans) sets exactly the 1.4 A mesh
   current. The 4-span form would instead initialise `V(in)` **and** the LPOWER current — the trap
   is documented in the script.
4. **20 ns gate edge.** It is not a new device: it is the existing RG = 22 Ω / STP9NK50Z gate
   charge driven by the controller DREC pin. Adding an edge-shaping source would be an extra
   fixture, which the task forbids.
5. **`RINPUT vin in .1 IC=0 IC=0`** annotates the existing resistor's two undefined spans; the
   component value and topology are unchanged (recorded as an edit in `build_receipt.json`).
6. **Probe names are not verified.** No simulation was run, so whether LTspice stores
   `I(XQ:LD)`, `I(XQ:LS)`, `I(XQ:LG)`, `I(XNEG:K)`, `I(COUT)` and friends is **unproven here**.
   The builders instruct the principal to report a **PARTIAL** KCL rather than a closed one if any
   term is absent. That is precisely the observability failure mode ROUND1_REVIEW line 3 rejected,
   so it must be checked in `circuit.log` before any conclusion.
7. **Quoted ramp-lag figures (12.58 mA / 18.27 mA)** are copied from the decision, not recomputed.
   `build_filter.py` back-checks their mutual consistency with the τ ratio (10 ns → 103.4 ns =
   10.34×, which would give ≈130 mA if the 12.58 mA were scaled linearly, so the quoted pair is
   **not** internally consistent under a pure τ scaling) and prints a warning; the principal must
   re-derive the figure before using it. This is flagged, not silently accepted.
8. **60 ms baseline runtime is a real risk.** The round-1 baseline 60 ms at `2e-7` max step is the
   baseline recipe; whether it fits anywhere near 300 s is unknown and untested here. A timeout
   consumes the attempt and must not be retried unless preregistered.

## Preregistration
`lab.execute()` writes `preregister.json` itself, immediately before the solver launches, including
netlist/model/solver hashes and the fixed acceptance thresholds. The builders therefore deliberately
do **not** pre-write `preregister.json` (a hand-written file would defeat the hash commit).
Fixed thresholds used, copied unchanged from `lab.py`: mean 164.9–175.1 V, ripple 1 Vpp, normal
peak 180 V, startup 1 s, recovery 0.1 s, fault peak 195 V, |sense| 0.3 V. Nothing was relaxed.

## What this worker does NOT establish
- No electrical acceptance of any kind. Every statement is a **preliminary WORKER_CLAIM**.
- No simulation, waveform, KCL residual, peak, timing or threshold measurement exists.
- The physical-source uncertainty of the R1 excursion is untouched.
- Kelvin routing, which the decision names as a prerequisite, cannot be shown by SPICE at all.
- All manufacturing **HOLD** entries remain in force.
