# loop_followup — inventory (Round 4, CODE ONLY)

Task `loop_followup`, role `loop_regression`, QS30-9 power_loop_r2 extension.
**Code only**: no shell, job, simulator, network, or model call was made by this
worker. Nothing was executed, so **no waveform, current, voltage, ripple or
recovery time is measured, estimated or hand-computed here**. WorkerPASS is
**evidence delivery only**; every downstream number becomes a preliminary
WORKER_CLAIM pending deterministic audit and Codex review.

## Deliverables

| File | Note |
|---|---|
| `build_regression.py` | 176 lines, single script, **function-only**: no `__main__`, no filesystem write, no import of `lab`, no simulator call. Exports `mutate(s, kind)` and `describe(kind)`. |
| `inventory.md` | this file |
| `result.json` | worker result record |

No `circuit.cir` / `run.log` / `waves.txt` / `metrics.json` are fabricated: those
belong to the principal's `lab.execute` runs, which this task forbids.

## Source read (read-only, outside OUTPUT_DIR)

`R2/evidence/principal/filter22R_4p7n_60ms/circuit.cir` — the completed
filter-cell text used as the base cell (44 lines: `VINPUT vin 0 PWL(0 0 1m 24)`,
`RLOAD hv 0 5200`, `.tran 2e-07 0.06 0 2e-07 uic`, `.temp 25`, `.options tnom=25
reltol=.001 abstol=1n vntol=1u method=gear plotwinsize=0 numdgt=15`,
`.save …`, `XU … LT3757A`). Also read: that cell's `preregister.json`
(netlist sha256 `796b3466…cca4e`, recorded model hashes, `method=gear`), its
`decision.txt`, `R2/evidence/principal/filter22R_4p7n_200ms/preregister.json`
(same `.options`, `method=gear`), `R2/lab.py` (`native`, `sha`, `execute`
anchor/tolerance guards), `extension/engineering_context.md`, and
`extension/ROUND3_REVIEW.md`. `controller.sub`, `st.lib`, `ss14.lib`,
`diode.lib` were **not** read, edited or hashed by this worker; `controller.sub`
is an encrypted vendor stub and is left untouched.

## Mutator contract

`mutate(s, kind)` takes the base netlist **as text from the caller** and returns
a new string. It is pure — it does not read, write, or mutate anything.

Anchors are asserted **exactly once** before and after mutation; any 0 or ≥2
match raises instead of emitting a guessed netlist. Also rejected: CRLF input,
missing trailing newline, a pre-existing `RLOAD`/`BLOAD` other than the
registered one, and changed solver tolerances.

| kind | mutation | `.tran` stop | final raw-ripple window |
|---|---|---|---|
| `vin21p6` | `VINPUT` plateau `24` → `21.6` only | 0.2 s | 0.15–0.20 s |
| `vin26p4` | `VINPUT` plateau `24` → `26.4` only | 0.2 s | 0.15–0.20 s |
| `load_step` | `RLOAD hv 0 5200` removed → `BLOAD hv 0 I=V(hv)/(if(time<80m,10400,if(time<180m,5200,10400)))` | 0.3 s | 0.26–0.30 s |
| `overload` | `RLOAD hv 0 5200` removed → `BLOAD hv 0 I=V(hv)/(if(time<80m,5200,1000))` | 0.16 s | 0.14–0.16 s |

Only the `.tran` stop field is rewritten (`START`/`MAXSTEP`/`UIC` preserved).

**Asserts are enforced** that RF stays `22`, CF `4.7n`, RG `22`, RSRC
`.062`, and RCOMP `22k` / CCOMP `6.8n` / CHF `100p` are present unchanged; that
all four `.include` lines survive; that no `.model` or `.lib` card is introduced;
and that `reltol=.001 abstol=1n vntol=1u method=gear` remains. No threshold, no
compensation value and no vendor model is touched, and the base `circuit.cir` is
never written back — the source evidence stays byte-identical.

`mutate` returns only a string; the descriptive metadata (stop, final window,
`thresholds_changed=False`, `acceptance_invented=False`, `extra_cases=0`,
`runtime_budget_s=900`) is assembled in the same function's local `out` dict for
the principal to attach, and is mirrored by `describe(kind)`. Nothing is
auto-signed-off.

## Scope limits carried into the output

The load is an **equivalent resistive sink** `I = V(hv)/R`; it is **not** nine
glow tubes, not a measured lamp, and no glow-tube behaviour is claimed. The
`overload` case is a **screen of current-limit behaviour only** — it is *not*
normal-regulation qualification and *not* 195 V OVP qualification. The
`load_step` intent (recovery ≤ 100 ms against the 164.9–175.1 V band, ≤ 180 V
peak, ≤ 1 Vpp raw in the fixed final windows) is a **pre-registered test
intent** recorded as text; no acceptance value is created or altered here, and
the original 200 ms / 60 ms qualification failures, the 22R/4.7n timeouts and
every HOLD stand unchanged.

## Runtime

The script is not run by this worker. The principal runs each case as a single
LTspice run with the pre-registered 900 s budget; per-case attempts count
against the 36-attempt deterministic allowance.
