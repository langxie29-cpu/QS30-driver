# lt3757a_reference — LT3757A official reference: native replay inventory

Task: `lt3757a_reference` (round_02, role `reference_replayer`, kind `spice`).
All output of this worker lives inside this directory only. Nothing was committed, pushed,
downloaded, installed or physically operated.

## 1. Simulator actually used (native, locally installed, pre-signature-verified)

| item | value |
|---|---|
| simulator | LTspice 24.0.12 for Windows, `SPICE Simulator w/ Schematic Capture` |
| vendor | Analog Devices Incorporated (file version 24.0.12.0) |
| executable | `D:/PROJECTS/dsharness/QS30-1/projects/QS30-9_24V/toolchain/ltspice26/extracted/LTspice.exe` |
| sha256 | `17f5efb978c0df2e164328b7352801fdc1ed0225827e41669bd9da25893fe96d` |
| native solver | LTspice built-in engine, `solver = Normal`, `method = modified trap`, `temp/tnom = 27` |
| invocation | `LTspice.exe -b -ascii <netlist> -I<private lib/sub>` (timeout 120 s per case) |
| signature | Authenticode `Status 0 / Signature verified`, subject `CN=Analog Devices International UC` (from `evidence/preflight/ltspice_signature.json`) |

NGspice was **not** used: the LT3757A model bytes are an ADI-encoded binary model that only the
native LTspice engine consumes, so any other engine would be a conversion, not a native replay.

## 2. Vendor sources — extracted byte-for-byte (Python `zipfile`, round-trip re-read proven)

Archives come from the already-extracted ADI signed distribution in the historical toolchain
(`.../toolchain/ltspice26/extracted/lib.zip`, `examples.zip`); no network fetch.

| component | archive member | bytes | crc32 | sha256 | local file |
|---|---|---|---|---|---|
| LT3757A.sub (native binary model) | `lib/sub/LT3757A.sub` | 2572 | `1d44a014` | `c03284243ac3b8e500e5bed3696deb8ebbde10eb8cb2a58b6e37929d9d18b634` | `vendor_original/LT3757A.sub` |
| LT3757A.asy (schematic symbol) | `lib/sym/PowerProducts/LT3757A.asy` | 948 | `fbdb5582` | `4ed5078ebd77e5e697bc61b9124d34b350cdccc7be9a0d32e7def830660c9d76` | `vendor_original/LT3757A.asy` |
| LT3757A.asc (vendor reference) | `examples/Applications/LT3757A.asc` | 2890 | `3ae68b0d` | `867ea5d1f8f90aa56f4dacfadfa4108bfddf0e619c06941bb711d890dba40cb6` | `vendor_original/LT3757A.asc` |
| standard.mos | `lib/cmp/standard.mos` | — | — | `adfdcda82e1b6186f907df2dc3905659a2ea2be2a0887a016d1fd9f1b3b1b40e` | `sim_profile/LTspice/lib/cmp/standard.mos` |
| standard.dio | `lib/cmp/standard.dio` | — | — | `696d34dfe538966c80cfe1da259c1043f408777be79f59e4f1c47d82f3af320a` | `sim_profile/LTspice/lib/cmp/standard.dio` |

Archive hashes: `lib.zip` `dd0028bb12e3f432ef022570cb7cf64d3c87288c35d1e8159658a4ff986ce094`,
`examples.zip` `319ac0e9adcce7e156aa47050a659919dbd901f1e82ab42fdb156bcefcd54ad6`.

Model licence / provenance: Analog Devices / Linear Technology LTspice distribution, governed by the
LTspice licence shipped with the installer (`extracted/License.txt`). The `.sub` is an **encoded
binary model**: begins `<Binary File>` with NUL bytes, internals are not text-auditable and are
consumed **only** by the native LTspice engine at version 24.0.12.0. It was never rewritten,
patched, converted or re-encoded. All three vendor bytes were re-hashed **after** every simulator
invocation and still match (`run_manifest.json → vendor_schematic_unchanged_by_replay`).

All hashes agree with the independent `evidence/preflight` and round_01 `vendor_models`
inventory (same three values) — re-verified here, not copied.

## 3. Replay chain (original design replayed first, unmodified)

1. `LTspice.exe -netlist vendor_original/LT3757A.asc -I<.../lib/sym>` → rc 0, 1.16 s.
   Netlist written by the **native netlister** next to the `.asc`; copied unmodified to
   `LT3757A.net` and `LT3757A.original.net` (763 B, identical).
2. **R0 (the unmodified replay)** — `LTspice.exe -b -ascii LT3757A.net -I<.../lib/sub>` → rc 0.
   Raw + log preserved: `R0_original_tran.raw`, `R0_original_tran.log` (= `run.log`).
3. **A (output-fidelity control)** — identical netlist plus one line `.options plotwinsize=0`
   (no waveform-point compression; no circuit change): `caseA_no_compression.cir`,
   `A_tran_nocompress.raw/.log/.op.raw`.
4. **B (operating point)** — identical netlist plus `.op` + `.save all`: `caseB_op.cir`,
   `B_op.raw/.log/.op.raw`.

`circuit.cir` is the native netlist content with only the leading absolute-path comment replaced
by a provenance comment and the symbol `.lib` path parameterised as `%LIBSYM%`; the untouched
absolute-path original stays as `LT3757A.original.net`. The vendor `.asc` itself was never edited.

Two `0xA1 0xEC` bytes in the native netlist are the CP1252 `µ` of `10µ`, `47µ`, `4.7µ`, `0.01µ`.
A UTF-8 re-decode silently replaces them with `??` and would corrupt the inductors/capacitors;
all derived netlists are written back as CP1252 so every value stays byte-identical.

## 4. Measured results (from the actual raws; see `metrics.json`, `waves.txt`)

| quantity | R0 (unmodified) | A (no point compression) |
|---|---|---|
| samples / endpoint | 1117 / 1.5 ms | 1117 / 1.5 ms |
| V(out) initial | 1.7456e-40 V | 1.7456e-40 V |
| V(out) peak | 8.8458e-05 V | 8.8458e-05 V |
| V(out) mean, 1.2–1.5 ms | 7.95755e-05 V | 7.95755e-05 V |
| I(L1) peak | 1.776297e-03 A | 1.776297e-03 A |
| V(N003) max (SS/VC node) | 3.335e-05 V | 3.335e-05 V |

Solver/tolerance check: after the header lines (`Date`, `Flags: … nocompression`) the raw
**value blocks of R0 and A are bit-identical**; all V(out)/I(L1) differences are exactly 0.0.
The native replay is reproducible and independent of output-point compression.

Operating point (case B) is degenerate: `V(out)=1.746e-40 V`, `V(in)=0`, `I(L1)=-2.86e-26 A`.

Independent match: this round's numbers equal those of the earlier independent replay in
`evidence/native_reference_netlist_retry/metrics.json` (7.957548738684513e-05 V mean) — two separate
executions of the native engine agree.

## 5. What the official reference actually is, and what it is NOT

The vendor `.asc` is a 12 V → ~23.9 V demo (R3/R2 = 226k/16.2k divider, Rload = 12 Ω,
`FDS6680A` 30 V FET, `MBR735` diode, `L1 = 10 µ`, `.tran 1.5m`). **It contains no 170 V net.**

Under this build of the native engine the unmodified replay **does not regulate**: the output never
exceeds 88 µV, the op point is at 0 V, and the run log records
`Direct Newton iteration failed to find .op point` then Gmin stepping, plus
`Ignoring empty pin current: Ix(u1:5)` (the model exposes 11 pin currents, none for pin 5).

Per-window finding (recorded, not used to alter the vendor design): in **every** sampled point
I(L1) is **positive** — current flows through the 12 Ω shunt R7 toward the IC's current-sense pin,
i.e. the vendor 7-pin schematic symbol places switch node Q1/D1 on the terminal the decoded native
model treats as source. The gate-driver pin current stays at the 1e-10 A leakage floor and the
gate node below 35 µV, so no switching occurs.

Sensitivity probes (`probe_series/`, **labelled modified, not the replay**): adding a 0.1 Ω series
source resistance before V1 (so that `startup` ramps V(in) from 0 V instead of starting at 12 V) for
1.5 ms gives V(out) peak 8.85e-05 V, and for 2 ms gives 1.18e-04 V, with pin-6 (gate-driver) current
≤ 1.92e-16 A and the gate node ≤ 4.5e-05 V in both. Input ramping alone does **not** make the vendor
reference regulate in this engine.

Conclusion retained as preliminary worker evidence: the official reference replay is a **valid,
reproducible native execution that reproduces the vendor deck's zero-output behaviour**. It is
neither a demonstration nor a refutation of LT3757A converter capability, and it says nothing about
the QS30 170 V design.

## 6. QS30 acceptance status (thresholds unchanged)

Vin 21.6–26.4 V, mean 164.9–175.1 V, ripple ≤ 1 Vpp, peak ≤ 180 V, cold start ≤ 1 s,
recovery ≤ 100 ms, fault peak ≤ 195 V — **none evaluated**: the vendor deck has a different input
(12 V), target (~23.9 V), load and duration, and produced no regulation at all. No threshold was
changed and no fabricated PASS is claimed.

## 7. Files

`circuit.cir`, `run.log`, `waves.txt`, `metrics.json` (required evidence),
`LT3757A.original.net`, `LT3757A.net`, `LT3757A.log`, `R0_original_tran.{raw,log}`,
`A_tran_nocompress.{raw,log,op.raw}`, `B_op.{raw,log,op.raw}`, `caseA_no_compression.cir`,
`caseB_op.cir`, `vendor_original/{LT3757A.asc,.sub,.asy,LT3757A.net}`,
`probe_series/*`, `run_manifest.json`, `reference_checks.json`, `replay.py`, `analyze.py`,
`probe.py`. `sim_profile/` and `env/` are simulator scratch (private APPDATA).

## 8. Blocking issues / not proven

* The vendor reference does not demonstrate LT3757A regulation in LTspice 24.0.12.0 (zero output).
  Root cause identified only as evidence (pin mapping / no startup source); not fixed, because the
  original reference must stay unmodified.
* No 170 V, no QS30 power stage, no real Cout = 0 V cold start, no fault/recovery coverage exists
  in this deck — all remain **HOLD**.
* The `.sub` is encoded and unauditable; its internal behaviour cannot be independently verified.
* All findings are DeepSeek worker evidence pending deterministic audit and Codex review.
