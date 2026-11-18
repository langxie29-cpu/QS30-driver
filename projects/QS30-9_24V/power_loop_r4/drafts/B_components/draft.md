# R4 Engineering Convergence Proposals — 4 Categories

Scope note: convergence guidance only; no safety release, no manufacturing release. R3 98b6f819 frozen. All values below are derived from supplied facts or marked UNKNOWN. No new sources obtained.

---

## Category 1 — HV Switch: STP9NK50Z configuration

**Proposal: HOLD (configuration), RETAIN (part usage only under 12 V rail), CANDIDATE (rail redesign)**

Findings from supplied facts:
- STP9NK50Z RDS(max) is specified at VGS = 10 V; 7.2 V logic drive is not a guaranteed datasheet operating point for the RDS(max) used in loss work.
- VGS ±30 V and VDSS 500 V ratings are stated; model is 25 °C only.
- `external real12V rail vs7.2V logic HV MOS` — no exact model recalled → **UNKNOWN**.

Therefore:
- **RETAIN** STP9NK50Z **only** if gate drive is the external real 12 V rail (≥10 V at the gate across tolerance, including driver droop). RDS loss budget may then reference datasheet RDS(max); hot RDS still UNKNOWN (no junction-temperature model).
- **REPLACE / reconfigure** 7.2 V logic-drive path: RDS(max) at 7.2 V is **UNKNOWN**, and no exact model is recalled. Do not use 10 V RDS(max) for loss/thermal margin at 7.2 V. A dedicated ≥10 V gate rail or a logic-level HV MOS with a primary-verified RDS(max) at the actual drive is required before convergence.
- **HOLD** any claim that the existing device bounds SOA at 7.2 V. SOA at 7.2 V is UNKNOWN.

Data needed before R5:
1. Principal-verified STP9NK50Z datasheet curves: RDS(on) vs VGS at 7.2 V and 12 V, at Tj = 25/100/125 °C.
2. Gate driver output high under worst-case supply, load, and temperature (real 12 V rail tolerance and droop).
3. Switching-loss model at the actual VGS and VDS, with Tj iteration.
4. Exact model/part identity if 7.2 V logic drive is retained.

Rejected shortcuts:
- Applying 10 V RDS(max) to a 7.2 V gate (invalid extrapolation).
- Using 25 °C model for thermal margin.
- Claiming SOA from a model that lacks temperature and VGS coverage.
- Assuming a 12 V “rail” exists without verifying it reaches the gate.

Thermal/loss impact: 7.2 V drive raises RDS and conduction loss by an UNKNOWN factor; switching loss and gate charge behavior also UNKNOWN at that VGS. Until resolved, thermal margin is **UNKNOWN**; do not close.

BOM impact: If 12 V rail retained → no BOM change for Q, but gate-drive network/rail must be verified. If logic-level replacement required → new HV MOS MPN, new gate resistor/network, new thermal analysis; BOM line changes pending principal selection.

---

## Category 2 — AUX Buck: LM5164DDAR

**Proposal: CANDIDATE (not PASS; no ideal AUX system PASS)**

Supplied: LM5164DDAR buck candidate; “no ideal AUX system PASS.”

Findings:
- LM5164DDAR is a **candidate only**. No verified datasheet values, pinout, compensation, or boundary conditions were supplied in this review.
- No ideal AUX system PASS is claimed; AUX system remains **HOLD** for convergence.
- Interaction with the LT3757A loop and the 7.1755 V internal / 169.985183 V nominal domain is **UNKNOWN** at the AUX level.

Data needed:
1. Primary-verified LM5164DDAR datasheet: VIN range, VOUT set, switching frequency, current limit, dropout, UVLO, soft-start, thermal pad/Rθ.
2. AUX load budget: startup/inrush, steady-state, transient, and fault load, including gate-drive current if the 12 V rail is used for the HV MOS.
3. Input source behavior and sequencing relative to LT3757A loop, COUT0, and SENSE node.
4. EMI/ripple limit at AUX output and coupling to the 0.090472 Vpp output ripple budget.
5. Worst-case efficiency/loss stack and junction temperature at max ambient.

Rejected shortcuts:
- Declaring LM5164DDAR a PASS from part familiarity.
- Assuming AUX is independent of the main loop without sequencing/ripple analysis.
- Using typical efficiencies for thermal closure.

Thermal/ESR/loss impact: **UNKNOWN** pending datasheet and load budget. Do not claim ideal AUX.

BOM impact: CANDIDATE line only; no BOM freeze. Inductor, input/output caps, feedback divider, and compensation values are UNKNOWN.

---

## Category 3 — HV Diode: at most 2 alternatives

**Proposal: CANDIDATE ×2 (both require primary verification), HOLD on SOA/recovery claims**

Context facts retained:
- US1G 400 V old TT123 ns model has ~400 V recovery; port negative charge 112 nC is **not** guaranteed Qrr; intrinsic model anomaly → **SOA UNKNOWN**. Do not use US1G for margin claims.

### Alternative A — Wolfspeed C3D02060F
Supplied: official datasheet 600 V, 2 A, TO220F-2; supplier search indicates obsolete → **risk flag**.
- **CANDIDATE**, with obsolescence risk. Ratings supplied are factual but must be primary-checked against the exact revision; no pins/package details beyond TO220F-2 asserted here.
- Qrr/recovery behavior, thermal derating, and SOA at the actual dV/dt and di/dt remain **UNKNOWN**.

### Alternative B — STPSC2H065D
Supplied: 650 V, 2 A SiC candidate; “factual ratings need primary check.”
- **CANDIDATE only.** No verified VRRM/IF/trr/Qc/thermal values supplied. Do not assert ratings.
- SiC recovery charge and ringing with the 600–650 V class and layout are **UNKNOWN** until verified.

Data needed for either diode:
1. Primary datasheet revision: VRRM, IF(AV), IFSM, trr/Qrr or SiC Qc, VF vs IF vs Tj, Rθjc, SOA/repetitive peak.
2. Actual circuit dV/dt, di/dt, reverse voltage overshoot including 400 V-class recovery anomaly context, and snubber need.
3. Junction temperature at worst-case ambient and load; derating.
4. Lifecycle/obsolescence status for C3D02060F; second-source plan.
5. Port negative charge 112 nC handling: confirm it is not used as guaranteed Qrr.

Rejected shortcuts:
- Treating 112 nC as guaranteed Qrr.
- Using model SOA in place of datasheet SOA.
- Assuming SiC “has no recovery” without verified Qc/trr and ringing analysis.
- Selecting an obsolete part without lifecycle risk acceptance.

Thermal/ESR/loss impact: **UNKNOWN** for both until VF(Tj), recovery loss, and Rθ are verified. Diode loss affects local thermal and possibly the 0.090472 Vpp ripple path via layout coupling — coupling UNKNOWN.

BOM impact: Up to two CANDIDATE lines; no freeze. C3D02060F carries obsolescence/supply risk; STPSC2H065D requires primary verification before BOM entry.

---

## Category 4 — HV Film Cap and Magnetics

### 4a — Cap
**Proposal: CANDIDATE (one provisional, one primary-sourced MPN required)**

Context facts retained:
- ECQE2106JF: 10 µF, 250 V, ±5%; 85 °C +1.25 %/°C derate gives 187.5 V at 105 °C < 195 V fault → insufficient margin at 105 °C fault condition. Do not RETAIN for that duty; **REPLACE** for fault-Voltage margin.
- Candidate Panasonic ECWFD2W106J: **not verified exact MPN** → CANDIDATE with UNKNOWN status; do not assert ratings.
- Alternative: source-backed 400 V or 450 V film with accurate MPN after principal research. **CANDIDATE placeholder**, no MPN invented.

Findings:
- At 105 °C fault, 250 V-class derated to 187.5 V is below the 195 V fault reference — margin is **negative**. Replace.
- 400/450 V class is the rational direction, but exact MPN, ESR, ESL, ripple current, and self-heating are **UNKNOWN**.

Data needed:
1. Principal-verified MPN for ECWFD2W106J or an accurate 400/450 V film MPN: capacitance tolerance, voltage rating, temperature derating curve, ESR vs frequency, ESL, Irms at temperature, self-heating, dimensions, life.
2. Fault voltage waveform and duration at the cap location; 195 V fault reference and any transient overshoot.
3. Ripple current from the LT3757A loop at COUT0/SENSE and the 0.090472 Vpp output; cap current share UNKNOWN.
4. ESR contribution to output ripple and loop stability (COUT0 relationship).

Rejected shortcuts:
- RETAINING 250 V ECQE2106JF for 105 °C fault duty.
- Assuming “400/450 V” suffices without ESR/ESL/ripple verification.
- Using a guessed Panasonic MPN suffix.
- Ignoring ESR effect on 0.090472 Vpp ripple and loop compensation.

Thermal/ESR/loss impact: 250 V part has negative voltage margin at fault; ESR heating and ripple rating **UNKNOWN**. 400/450 V candidate may change ESR and loop behavior — **UNKNOWN** until verified. No PASS.

BOM impact: ECQE2106JF replacement required for fault duty; one CANDIDATE film line pending principal-sourced MPN. Mechanical/footprint change possible — UNKNOWN.

### 4b — Magnetics (MSS1583-154KED)
**Proposal: RETAIN for nominal research; HOLD for fault; fault L(I,T) UNKNOWN**

Supplied facts:
- 150 µH ±10 %, DCR max 0.159 Ω.
- 3.1 / 3.6 / 3.9 A correspond to 25 °C 10/20/30 % L drop.
- Irms 1.55 / 2.2 A for 20/40 °C rise.
- Hot L **UNKNOWN**.

Loop context: IL1 1.649249 A nominal; SENSE 0.103961; output 169.985183 V nominal / 0.090472 Vpp. Downstream U101 1 µ/47 µ produce IL 3.578762 / 14.171475 A with PWM-off output short; instantaneous pass limit 1.591 A cannot bound downstream C.

Findings:
- Nominal IL1 1.649249 A is below the 3.1 A 10 % L-drop point at 25 °C, but DCR loss and temperature rise must be checked at the actual RMS current, which is UNKNOWN (ripple unknown from supplied data).
- **Fault L(I,T) is UNKNOWN.** 3.1/3.6/3.9 A are 25 °C L-drop points; hot-L and saturation at 100–125 °C are not supplied. Do not use these for fault current limiting.
- 1.591 A instantaneous pass limit cannot bound downstream C during PWM-off output short; downstream fault current 3.578762/14.171475 A is not bounded by the inductor or the pass limit as stated. This is an architectural fault-energy concern — **HOLD**.

Data needed:
1. Primary-verified MSS1583-154KED L vs I vs T curves (saturation at 25/100/125 °C), DCR vs T, thermal Rθ, core loss curves.
2. Actual inductor ripple current and RMS at nominal and worst-case line/load.
3. Fault energy: PWM-off output short with 1 µ/47 µ downstream, pass limit 1.591 A, and downstream 3.578762/14.171475 A — define fault duration, energy, and inductor current path.
4. Hot L at the fault current and temperature; saturation margin.
5. Interaction with COUT0 and the LT3757A loop during fault.

Rejected shortcuts:
- Using 25 °C 10/20/30 % L-drop points as hot saturation limits.
- Assuming the 1.591 A instantaneous pass limit bounds downstream C current.
- Using 25 °C DCR for loss without temperature correction.
- Declaring magnetic fault-safe without L(I,T).

Thermal/ESR/loss impact: DCR 0.159 Ω max at 1.649249 A gives ~0.43 W conduction (P = I²R) before AC/core loss — this is arithmetic from supplied values, not a thermal PASS. Hot DCR and core loss **UNKNOWN**. Fault thermal **UNKNOWN**.

BOM impact: RETAIN line for nominal research; no BOM freeze. Fault-energy resolution may require larger saturation/hot-L part, added fault limiting, or downstream protection — **UNKNOWN** pending data.

---

## Summary Table

| Category | Proposal | Key blocker |
|---|---|---|
| HV MOS STP9NK50Z | HOLD config; RETAIN only on real 12 V gate; CANDIDATE logic-level replacement | RDS at 7.2 V and 12 V vs Tj UNKNOWN; no exact model |
| AUX buck LM5164DDAR | CANDIDATE; AUX system HOLD | No verified datasheet/load/thermal; no ideal PASS |
| HV diode (≤2) | CANDIDATE C3D02060F (obsolete risk); CANDIDATE STPSC2H065D | Primary ratings, Qrr/Qc, SOA, lifecycle UNKNOWN |
| HV film cap | REPLACE ECQE2106JF for fault; CANDIDATE 400/450 V MPN | 250 V derate 187.5 V at 105 °C < 195 V; exact MPN UNKNOWN |
| Magnetic MSS1583-154KED | RETAIN nominal research; HOLD fault | Fault L(I,T) UNKNOWN; pass limit cannot bound downstream C |

## Global holds carried forward
- All H01–H10 and 24V07–10 remain in force.
- TPS26601RHFR U100: ILIM 12 k ≈ 1 A / 1 A fuse; U101 20 k MODE open = circuit breaker + latch. Proposed 8 k and 402 k mean active limit then thermal latch — **not** timed overcurrent. TPS max fast-delay **not guaranteed**; 250 ns and SHDN–FLT 10 µs are typical only. This remains a HOLD for any fault-timing claim.
- No physical experiments, purchases, or manufacturing release.

## Rejected shortcuts (global)
- Extrapolating 10 V RDS(max) to 7.2 V.
- Treating 112 nC as guaranteed Qrr or model SOA as datasheet SOA.
- RETAINING 250 V film at 105 °C fault.
- Using 25 °C L-drop as hot saturation.
- Assuming 1.591 A pass limit bounds downstream C.
- Declaring AUX or any category PASS from familiarity.
- Inventing MPNs, prices, pins, or sources.

## Data required before R5 convergence
1. Primary STP9NK50Z RDS vs VGS/Tj and real 12 V gate-drive worst case.
2. LM5164DDAR primary datasheet + AUX load/sequencing/thermal budget.
3. One or two primary diode datasheets (C3D02060F revision + lifecycle; STPSC2H065D ratings) with dV/dt/di/dt and Tj.
4. Principal-sourced 400/450 V film MPN with ESR/ESL/Irms/derating and fault waveform at 195 V.
5. MSS1583-154KED L(I,T), DCR(T), core loss, and fault-energy definition for PWM-off output short with downstream 1 µ/47 µ.
6. Resolution of TPS26601RHFR fault-timing: guaranteed vs typical, and whether active-limit + thermal latch is the accepted protection model.