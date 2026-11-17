## Round 2 Adversarial Review — Findings

**Verdict: REJECT study conclusions as a qualification basis. ACCEPT only as a drafting/arithmetic record with the corrections below. All manufacturing, H01–H10, and 24V07–10 remain HOLD.**

### Critical numeric findings

1. **Off-by-~1000× slewing error is corrected but must be applied consistently.** Slew = Iprog·gain/Cdvdt, not CdVdT·5.5 µA. With 26.4 V ramp at 7.962 ms, Coutmax displacement = 80.768 mA (arithmetic checks: 26.4/7.962e-3 ≈ 3.316 V/ms × 24.36 µF ≈ 80.8 mA). Any retained text citing 5.5 µA as capacitor charging is nonconforming and must be deleted.

2. **ILIM1.590909 A is not a guaranteed worst-case limit.** It is 1.575/0.99, assuming 1% R and inverse scaling — valid only under that assumption and not across full Vin/drop. Correction: label "assumed 1%-tolerance inverse-scaled nominal," not a guaranteed bound. ILIM margin claims built on it are unverified.

3. **On-state current-ramp filter delay uses 26.4 V/L, not 170 V/L — corrected.** τ 97.2477–109.6557 ns → 21.444/23.826 mA for 135/121.5 µH. Note 121.5 µH is a sensitivity point only; it is not a hot guarantee. Do not present 23.826 mA as a guaranteed hot-case figure.

4. **Zero current-limit delay is FAVORABLE, not conservative.** This is the single largest model-credibility defect. Results from front24/front26p4_fast cannot be treated as worst-case.

5. **Fault 1µ/47µ:** IL peak 3.57876/14.17147 A crosses the cold 3.1 A 10%-L-drop screen. Classification "ELECTRICAL_FAIL linear validity screen" is correct — must not be escalated to destructive maximum or actual saturated peak bound. Cout short-pulse 234.689 A (both 1µ and 47µ cases) is a separate loop; retain correctly separated.

6. **ECQE 250 V at 105 °C:** 1.25 %/°C above 85 °C → 187.5 V, below 195 V. Conditional failure stands. Jcap 24.36 µF is an extra +20 % exploration, not manufacturing tolerance (5 % nominal). R3 dual 181.8 kΩ each: 21.315 µF one-open = 4.613 s (t195→60); 24.36 µF = 5.272 s extra exploration. Arithmetic checks.

7. **Cell internal inference (worst):** channel peak 10.5214 A / 8.32056 µJ is derived across unchanged Rj = 0.000141 Ω by Ohm/KCL. A −92,071 A inferred excursion at 0.9841368 µs lies outside the commutation window and is not physically credible as a conductor current. Native terminal KCL residual 2.571 mA > R2's 1 mA screen. **Therefore: internal loss/SOA conclusions explicitly INCONCLUSIVE; 8.32056 µJ and any nonconvergent dv/dt are not physical guarantees.** The 10 ps vs 5 ps VDS-minimum variance supports numerical artifact, not proven physical origin.

8. **Local MOS signed-port energy 11.4147 µJ is not pure heat** and must not be multiplied by 100 kHz as a repetitive budget. No thermal energy budget may be inferred from it.

### Model credibility / scope

- Probe1 omits instance → smoke-only. Probe2 (instantiated encrypted TI body) → parser "Too few nodes," MODEL_FAIL rc1. **No real TPS qualification; do not use tps cases for any decision.**
- Native internal 7.2 V LDO removes the ideal 12 V AUX node assumption. STP9NK50Z RDS(on) is guaranteed at 10 V only; **no 7.2 V thermal guarantee exists.** Highest priority model gap.
- Unmodeled and blocking: U100/fuse, RTN/permit, thermal latch, independent OVP. Front24/front26p4 windows (169.7–170.0 V in 0.06–0.08 s) pass only within the limited model, not with real loop impedances.

### Arithmetic spot-checks (consistent with corrections)

- Front-ending times 0.035–0.040 s and steady ~169.99 V are internally consistent across front21p6/front24/front26p4.
- i(cout) peak 2.16 A and i(lpower) max 1.653 A are consistent; no re-derivation issues found in provided metrics.

### Component/vendor evidence

- QS30 maker scans (Uzmax150, Uxmin100, Eamin170, Ra20k, Ik 1.5/2.25/3 mA) are used correctly. **Extinction 100 V is not a maintaining voltage — no claim of sustained 100 V operation.**
- Freeze 164.9 V below maker-recommended 170 V supply remains a **real-load test gap.**
- HV5622: recommended 220 V / abs 230 V, VDD 10.8–13.2, VIH VDD−2, low-current VOL unknown. Qualify only on real part.

### Priority missing items (must remain blockers)

1. **Independent OVP/latch/manual-fresh/default-off/residual-validity: still blockers — not modeled, not verified.**
2. **U100/fuse, RTN/permit, thermal latch: unmodeled.** Highest-priority additions before any predictive claim.
3. **STP9NK50Z at 7.2 V:** obtain vender driver/RDS(on)/thermal data at actual gate drive or re-establish a 10 V–capable gate drive with verification.
4. **Real TPS model / real load** — required before any front-end conclusion.
5. **Clearance rule numeric still pending applicable insulation conditions.** No build action.
6. **Real-load test at ≥170 V** and real 105 °C ECQE derating verification for 195 V target.
7. **BOM:** precise MPNs + explicit PENDING rows; budget allowances are not quotes or stock claims.
8. **HV safety:** no bare HV headers; rated shrouded/enclosed probes with cover/interlock; differential/common-mode/transient-rated scope; scope earth maintained; no ground clip to SW/RTN. CV/CC source is not output protection.

### Disposition

- **Arithmetic conclusions:** accepted with the four corrections above (slew, ILIM labeling, 26.4 V/L filter, 121.5 µH sensitivity only).
- **Model-based electrical conclusions (cell, front-end, SOA, thermal):** **REJECTED as physical**; retained as raw INCONCLUSIVE/LIMITED_PASS evidence only.
- **ECQE 105 °C fail:** accepted as explicit conditional failure.
- **Fault-induced IL peak classifications:** accepted as electrical-fail screens only; do not escalate to destructive or saturation claims.
- **All manufacturing and H01–H10/24V07–10:** remain **HOLD**. No PCB manufacturing approval. No claim of independent browsing, simulation, or vendor confirmation.