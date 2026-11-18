# R4 Principal Review — Arithmetic / Feasibility Check (evidence-only)

## 1. Scope statement
- Reviewed the supplied R4 facts and INDEPENDENT_CALCS. No new sources, simulation/model calls, or execution were used.
- R4 remains **unsigned qualification evidence**. All R1/R2/R3 read-only; all H01–H10/manufacturing HOLD retained.
- No fabrication PCB, no signed qualification, no PASS claim.

## 2. Arithmetic re-derivations (sample checks against supplied values)

### 2.1 Capacitor / bleed
- Vop at 105 °C: 450 × (1 − 0.0133 × (105−85)) = 450 × (1 − 0.266) = 450 × 0.734 = **330.3 V**. Matches [330.3].
- Bleed string: 3 × 49.9 kΩ = **149.7 kΩ**. Matches.
- Bleed power at 170 V: 170² / 149.7 k = 28 900 / 149 700 ≈ **0.1931 W per string**. Two strings ≈ **0.3861 W**. Matches.
- At 195 V: 38 025 / 149 700 ≈ **0.2540 W per string**; ×2 ≈ **0.5080 W**. Matches.
- Single-resistor short worst case (≈ half-bus domestic, conservative): supplied 0.19243 W; consistent with per-string power order. Accept as conservative bound only if bus/derating model confirmed; exact node voltage UNKNOWN.
- CRCW2512 linear derate at 100 °C: 1 W × (155−100)/(155−70) = 55/85 ≈ **0.6471 W**. Matches. 100 °C ambient with 0.647 W capability: single-resistor short bound 0.192 W is within; **but that does not prove whole-string hardware robustness** (short location, bus division, parasitic, transients UNKNOWN).
- Bleed RC time constant (single-string open, assumed C values as listed): nominal ≈ **3.98 s** and 1 %/100 ppm variant ≈ **4.01 s** to 195→60 V. Arithmetic consistent with 149.7 kΩ × ≈26.6 µF order. Actual effective capacitance including module/parasitics: **UNKNOWN**; treat as nominal-informative only.
- Max initial + optional module capacitance 2.2315e-5 F = **22.315 µF** total effective assumption. Arithmetically consistent; hardware verification HOLD.

### 2.2 Feedback / OVP
- Nominal FB with 1.91 kΩ vs 1.9006 kΩ: supplied 169.139 V vs 169.985 V cap-base. Both arithmetic carry ref × divider; ref source UNKNOWN from supplied facts beyond used value.
- OVP window [180.93, 192.11] V; residual trip [54.90, 58.28] V; branch-off [1.564, 1.645] V; bias12 supervisor [10.66, 11.30] V; raw24 [19.07, 20.23] V. These are internally consistent interval arithmetic; **component tolerances and reference accuracy beyond typical are UNKNOWN** unless separately sourced. No PASS.

### 2.3 Temperature model
- Electrical NTC trip model [81.59, 89.41] °C: plausible interval arithmetic given R25/B. **Cable drop, sensor adhesion, thermal hot-spot lag UNKNOWN**; existing 100 °C engineering limit unchanged. No thermal PASS.

### 2.4 LM5069 feasibility
- Stable Ilim [0.960, 1.242] A; breaker threshold [1.584, 2.626] A; timer component s [0.000282, 0.000897] s. These are component-form interval calculations only. Total cutoff **UNKNOWN** (TIMER→GATE 12 µs typical; breaker 1.2 µs only under stated unloaded VIN48 condition; no pass FET). No full-cutoff max exists in supplied facts.
- Feasibility disjointness: max Rs to avoid current limit ≈ **0.02912 Ω**; min Rs to trip by 3.1× cold before any delay ≈ **0.04236 Ω**. Since 0.02912 < 0.04236, the two constraints are indeed **disjoint for the unchanged R3 peak policy**. This rejects any guarantee based only on fast breaker with unchanged R3 current policy — **not** all possible LM5069 designs. Valid narrow conclusion; requires new current policy/frequency/magnetics qualification for any alternative.
- Note: LM electrical table default VIN 48 V; applicability to 21.6–26.4 V range is not independently guaranteed. Keep as UNKNOWN.

### 2.5 R12/R33 stress arithmetic
- R12p4 cold passive Vmax/Rmin = 2.1505 A; continuous short power 56.77 W; deliverable at 21.6 V = V²/R = 466.56/R. Supplied 9.313 W and R33 3.366 W imply specific resistances; arithmetic consistent with those. **These are topology/assumption-derived, not measured stress evidence.** Thermal/fault duration window UNKNOWN.

### 2.6 Source energy / inductor copper
- Source constant-fault energy: UNBOUNDED without source current/time/thermal qualification — accepted as a statement of missing constraints, not an energy value.
- Normal inductor copper from R3 RMS at 25 °C ≈ 0.0264 W: arithmetic plausible; actual L(I,T) copper, skin/proximity, and temperature rise UNKNOWN.

### 2.7 LT3757 SENSE
- SENSE 100/110/120 mV min/typ/max. The calc correctly warns not to use 110 mV typ as max. For guaranteed peak screening, use 120 mV if the policy is "trip at or below max allowed." With R3 peak 1.649249 A and Rs 62 mΩ: nominal VSENSE ≈ 0.10225 V, which sits between min and typ; it is **not** below 100 mV min, so worst-case min threshold would trip earlier than intended. This is consistent with the supplied "cannot use 110 typ as max" caution. Actual hardware peak current, R tolerance, and dI/dt-sampling delay UNKNOWN.
- Guard: Rs 62 mΩ must be qualified for pulse energy and tolerance if used as the screening resistor; the single point 62 mΩ is not itself an interval.

### 2.8 SiC STPSC4H065D / UCC27511 / US1G
- Local IC Vds 89.17 V / IL 1.4 A / Qneg 5.53988 nC: these are simulation-derived local-condition numbers. They are **not** a datasheet Qrr or BV proof. STPSC4H065D active 650 V 4 A factory v13 TT0 **no BV** — existing qualification gap.
- Shunt 5.04184 A vs original US1G ≈112.607 nC / 10.55 A under R3-matched cell: local/model evidence only, not hardware Qrr. Original UCC27511 executed unchanged with ideal 12 V + 7.2 V logic; VGS range −11.35 to 12.26 V is **not real-rail PASS**.
- UCC physical pinout 1 VDD 2 OUTH 3 OUTL 4 GND 5 IN− 6 IN+ vs macro order IN+ IN− GND VDD OUTH OUTL: if the macro order was carried into a physical footprint/net mapping, this is a **pin-mapping hazard**. Native 14-sheet netlist may or may not encode it; must be resolved against real symbol/footprint basis — HOLD.

### 2.9 TPS7A1601
- Adjustable ref 1.193 V, 319 k/100 k → Vout = 1.193 × (1 + 319/100) ≈ 1.193 × 4.19 = **4.99867 V**. Arithmetic confirmed. This is **not** a validated fixed-5 V MPN; regulator transient accuracy, load, and stability UNKNOWN.

### 2.10 Fault/run FF logic
- FF1: async PRE = FAULT_RAW_N, CLR = V5, D1 = RESET_DISALLOW, CLK = raw manual RESET; invalid reset clocks set Q1. FF2: CLR = FAULT_FREE & STOP_OK, D2 = HOLD_FULL_SAFETY_VALID, CLK = manual START, PRE2 = V5. No health gating on clock. This is a logical/topological concern, not an arithmetic PASS. Physical RESET residual/watchdog states remain HOLD-low. **No change to HOLD conclusion.**

### 2.11 TPS3700 / grounding
- Residual A+ low-asserting OD only below 56.57 V; unpowered floating not low proof. Common-ground/upper-open diagnosis HOLD. U100 RTN100 and EP separate PGND; all its SET/SHDN returns via RTN100; permitted by VOS618A-3X001T; FLT isolated DIAG only, not health. LM5069 same PGND, no RTN101. These do not establish fault-reaction or safety performance.

## 3. Counterexamples / weak points in the supplied arithmetic claims
1. **Bleed single-resistor short**: 0.192 W worst case is a lower-order number; a short at a different string node or simultaneous with bus upper fault could exceed it. Do not state as "proven safe."
2. **Bleed time-to-60 V**: 3.98–4.01 s is valid only for the assumed effective C and simple exponential discharge; parasitic/module and leakage UNKNOWN.
3. **LM5069 disjoint inequality**: correct for unchanged R3 peak policy; not a design impossibility proof. Preserve the supplied caveat.
4. **LT3757**: using 120 mV as screening max means 62 mΩ × 1.649 A ≈ 102 mV is below max but close to min 100 mV; with tolerance this can trip at/below policy. Treat as a real screening ambiguity, not PASS.
5. **R12/R33 21.6 V deliverable watts**: depend on assumed R and continuous-short model; not validated against package/thermal pulse.
6. **Cap RMS**: 8 A at 70 °C/10 kHz is not 100 kHz max and not a whole-cap ripple guarantee; ESR/ESL values are typical. No PASS.
7. **EDA feedback 1.91 k not 1900.6**: small divergence; if both used in different documents, trace which governs. UNKNOWN which is authoritative.
8. **UCC pin-order mismatch**: possible netlist/footprint hazard; do not mark resolved.
9. **TPS3700 unpowered floating**: not low proof; logic could falsely appear safe.
10. **No full cutoff max** for LM5069 and **no BV** for STPSC4H065D: both remain open.

## 4. Targeted corrections (no new calls)
- Change any language "0.192 W single-resistor short safe" → "conservative partial bound only; node-level fault and transients UNKNOWN."
- Replace "LT3757 peak 1.649 A guaranteed below SENSE max" with "102 mV nominal sense is within 100–120 mV window; worst-case min can trip earlier; policy needs explicit max/min screening and tolerance basis." Do not invent a new resistor.
- Keep "no feasible Rs" disabled-claim wording: "disjoint for unchanged R3 peak policy only."
- Correct "TPS7A1601DGNR 5 V" to "adjustable ref 1.193 V, divider 319 k/100 k ≈ 4.999 V; not a validated fixed-5 V MPN."
- Flag UCC macro-vs-physical pin order as **HOLD pin-mapping check**, not resolved.
- Preserve 1.91 k vs 1.9006 k divergence as open document-trace item; do not silently reconcile.
- Do not use 110 mV typ as max; do not use 8 A/10 kHz as 100 kHz or continuous maximum.
- Keep 100 °C thermal limit; electrical NTC model [81.6, 89.4] °C is scope-limited.
- Keep TPS3700 unpowered/floating, common-ground/upper-open, RESET residual/watchdog all HOLD-low; no health gating claim.

## 5. Optional netlist draft
No real-component-basis netlist draft is provided. The only supplied component set (B32774D4106K000450, CRCW2512 49.9 k, TPS7A1601DGNR divider, STPSC4H065D, UCC27511, etc.) lacks confirmed footprints, pin mapping, or full connectivity; drafting would create a fake-guarantee risk. Withheld.

## 6. Residual UNKNOWNs (unchanged holds)
Actual pass-FET/cutoff max; STPSC4H065D BV/qualification; hardware Qrr; real UCC rail behavior; parasitic C/Eoss/probe effects; thermal adhesion/lag; source energy and fault duration; component tolerances beyond listed; UCC pin mapping; 1.91 k vs 1.9006 k authority; LM5069 21.6–26.4 V applicability; H01–H10 and manufacturing.

## 7. Status
- R4 arithmetic: mostly internally consistent; several claims need the narrow corrections above.
- Feasibility disjointness: valid only under stated unchanged R3 peak policy.
- No PASS. No fabrication. All HOLD retained. Six LT calls remain the completed set; no further calls proposed.