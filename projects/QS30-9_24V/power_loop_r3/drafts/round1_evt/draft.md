# NXT-PWR-EVT01 — Round 1 Design-Input Review Checklist (Draft)

Status: **DRAFT / EVT design-input review only. No manufacturing approval. No physical action implied.** R2 ideal-12V AUX bias is a modeling assumption, not a frozen design. Exact clearance/creepage remains an open blocker (insulation/material/pollution/altitude/standard dependent). All H01–H10, 24V07–24V10, and manufacturing remain **HOLD**.

## 1. Requirements (measurable, with raw-record expectation)
| ID | Requirement | Acceptance (measurable) |
|---|---|---|
| RQ-01 | Mean raw output | 164.9–175.1 V (defined load/line set) |
| RQ-02 | Raw ripple | ≤1.0 Vpp normal (scope raw record) |
| RQ-03 | Normal peak | ≤180 V |
| RQ-04 | Cold start | 0 V → regulation ≤1 s |
| RQ-05 | Fault recovery | ≤100 ms after designated fault clear |
| RQ-06 | Designated-fault peak | ≤195 V |
| RQ-07 | Device stress | Independent of above limits; each device stress separately evidenced |
| RQ-08 | HV access | No bare header; shrouded rated connector or enclosed probe attachment behind cover/interlock |
| RQ-09 | Probe qualification | Differential probes qualified for differential, common-mode, transient; instrument earth maintained; no scope ground to switching/RTN |
| RQ-10 | Independent protection | CV/CC lab source does **not** substitute output-independent protection or residual measurement |
| RQ-11 | Bleed single-fault | Meets residual-energy target with one bleed branch faulted |
| RQ-12 | Passive-path energy | Evidenced with frontend stuck-on and MOSFET short |
| RQ-13 | Default state | Hardware latch, manual fresh start, default OFF verified |

## 2. Module Mapping (candidate → module)
| Module | Candidate(s) |
|---|---|
| Controller/AUX | LT3757A (internal LDO); R2 ideal-12V bias = assumption |
| Main switch | STP9NK50Z (TO220) — tab/heatsink live |
| Rectifier | US1G-E3/61T (SMA) |
| Inductor | MSS1583-154KED (150 µH) |
| Current sense | 62 mΩ shunt — exact part **pending** |
| Gate/snubber | 22 Ω / 4.7 nF |
| FB divider | 2×100 k + 1900.6 Ω equivalent — **manufacturable composition pending** |
| Compensation | 22 k / 6.8 nF / 100 pF |
| Output caps | 2× ECQE2106JF10U (250 V nominal) + optional 300 n emulator |
| Bleed | Dual 181.8 kΩ, each 2×90.9 kΩ |
| Hotswap/OVP | TPS26601RHFR (U100/U101); independent OVP |
| Excluded | 9 tubes, 3×HV5622, ESP32 |

## 3. Test Matrix (EVT01, raw records required)
| ID | Test | Key measurement |
|---|---|---|
| TM-01 | Line/load regulation + mean | Vmean per RQ-01 |
| TM-02 | Ripple/peak | Vpp, Vpk raw scope |
| TM-03 | Cold start | t(0→reg) ≤1 s |
| TM-04 | Designated fault inject/clear | t(recover) ≤100 ms, Vpk ≤195 V |
| TM-05 | Frontend stuck-on | peak, stress records |
| TM-06 | MOSFET short | passive-path energy |
| TM-07 | Bleed single-fault | residual energy/t |
| TM-08 | Latch/default-off/restart | state evidence |
| TM-09 | OVP independent trip | trip record |
| TM-10 | Probe/earth qualification | probe + earth record |
| TM-11 | Disconnected-module condition | defined state record |
| TM-12 | Power-rail sequencing, USB absent | sequence record |

## 4. BOM Candidates (MPN status; budgeting allowance only, not quotes)
Known MPN: LT3757A, STP9NK50Z, US1G-E3/61T, MSS1583-154KED, TPS26601RHFR, ECQE2106JF10U. **Pending/exact-part unknown:** 62 mΩ shunt; FB resistor composition; remaining passives exact MPN. Budget allowances to be listed separately as planning figures — not supplier pricing.

## 5. Layout Constraints
HV node and MOS heatsink/tab treated as live; differential/common-mode/transient-driven isolation; no scope ground to switching/RTN; no bare HV testpoints; interconnected modules and USB/sequencing assumptions defined; passive-path and bleed paths routed for single-fault evidence; **exact clearance/creepage = OPEN**.

## 6. Release Blockers
1. Real safety design incomplete. 2. R2 AUX bias not frozen. 3. Shunt exact part pending. 4. FB composition non-manufacturable as stated. 5. Clearance/creepage standard/material/altitude unresolved. 6. Single-fault/passive-energy evidence absent. 7. H01–H10, 24V07–10, manufacturing **HOLD**. No approval granted.