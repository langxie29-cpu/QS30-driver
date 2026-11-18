# NXT-PWR-EVT01 — R4 Scope/Interface Review (Convergence Only, No Release)

## 0. Status and boundary

- R4 is **engineering convergence**, **not** safety release. Frozen baseline: **R3 `98b6f819`**.
- Verified domain inputs (treated as given): LT3757A real loop; COUT0; internal 7.1755 V; nominal 169.985183 V / 0.090472 Vpp / SENSE 0.103961 / IL 1.649249 A; TPS26601RHFR U100 ILIM 12 k ≈ 1 A with 1 A fuse; U101 originally 20 k, MODE open; proposed 8 k + 402 k.
- **All H01–H10 and 24V07–10 HOLD items remain HOLD.** Nothing below clears a HOLD. No physical experiment, purchase, or manufacturing.
- Comparator/reference/latch/isolator/regulator **pinouts and maximum propagation delays were not supplied** → **UNKNOWN**. The items below are *interface scopes with net/pin checks to be completed against the installed part-verification source*, not finished netlists.
- **No PCB/DRC claim.** No uniform 2/3 mm insulation rule asserted or implied.
- **No MCU, no Boolean block, is accepted as a physical protection element** anywhere in this scope.

---

## 1. Bound-set points (treat as fixed for this review)

| Item | Bound | Meaning |
|---|---|---|
| U100 ILIM 12 k | ≈1 A | device current limit; 1 A fuse upstream |
| U101 (8 k + 402 k proposed) | active limit + **thermal latch** | **not** timed-overcurrent |
| TPS266x fast-trip delay | **not guaranteed** | cannot be relied on for bounding |
| SHDN↔FLT | 10 µs **typical only** | not a max |
| 1 µF/47 µF behind U101 | IL ≈ 3.5788 / 14.1715 A (PWM-off, output short) | instantaneous pass limit 1.591 A **cannot** bound downstream C |
| MSS1583-154KED | 150 µH ±10 %, DCR max 0.159 Ω; 3.1/3.6/3.9 A = 25 °C 10/20/30 % L-drop; Irms 1.55/2.2 A at 20/40 °C rise | **hot L UNKNOWN** |
| STP9NK50Z | RDS-on max specified at 10 V, not 7.2 V; VGS ±30 V / 500 V; model is 25 °C | 7.2 V drive margin **UNKNOWN** |
| US1G | 400 V old-TT 123 ns model ~400 V recovery; port negative charge 112 nC **not** guaranteed Qrr | intrinsic model anomaly → **SOA UNKNOWN** |
| ECQE2106JF | 10 µF 250 V ±5 %; 85 °C +1.25 %/°C → 187.5 V at 105 °C | 187.5 V < 195 V fault level → **derate HOLD** |

**Conclusion (bound-set):** downstream C inrush and hot-L/7.2 V-drive/US1G-SOA/105 °C-cap-derate remain **unbounded**. The independent OVP/latch/inhibit scope below is required to *prevent* a fault from depending on U100/U101 timing or on TPS fast-delay/SHDN-FLT.

---

## 2. Required independent functions (separation map)

| # | Function | Independent of | Physical realization required |
|---|---|---|---|
| F1 | OVP divider/ref/comparator | LT3757A COMP/FB, U100/U101 timing | own divider → own ref → own comparator with hysteresis |
| F2 | Set-priority fault latch | MCU, U101 thermal state | hard-set dominant latch, reset only by explicit RESET |
| F3 | Default inhibit | power state, MCU boot | fail-inhibited at power-up |
| F4 | Manual START / RESET | MCU | two distinct physical actions |
| F5 | UV / POR | comparator ref alone | own UV threshold + POR window |
| F6 | Temp open / short window | single sensor | window detector: open and short both → safe state |
| F7 | Two independent residual channels + validity HOLD | each other | ch A and ch B independently validated; either invalid → HOLD |
| F8 | Dual bleeds | single bleed | two independent discharge paths |
| F9 | Controlled load interfaces | bare gate drive | defined on/off, no float |

Candidate exact part numbers named in the task are listed as **candidate scope only**; pinouts and max tpd are **UNKNOWN** until independently verified against the installed KiCad 10.0.8 library and the principal-verified datasheets. No pin number or propagation maximum is asserted here.

---

## 3. Failure-mode analysis (explicit)

### 3.1 Unpowered open-drain falsely healthy
An open-drain “OK/FAULT” line that is pulled up to a rail which is *itself* unpowered can read as a valid level through parasitic/leak paths or through a second rail. **Hazard:** system appears “healthy” while the monitoring rail is dead.
**Required:** open-drain outputs must be interpreted as *asserted-when-pulled-low only within a defined powered domain*; add a **power-good gate** so that “no pull-down” is NOT decoded as healthy. Default state of the decode path at loss of the monitor rail must be **INHIBIT/FAULT**, not “clear.” Net/pin check: identify every pull-up rail; confirm pull-up rail is derived from the *same* monitored domain or has its own POR; confirm no cross-domain leakage path can source a false “healthy.”

### 3.2 RTN100 / RTN101 crossing
Two return nodes (RTN100, RTN101) crossing or sharing a path creates a single-point return that can carry fault current through a monitor reference, corrupting residual-channel readings and latch state.
**Required:** reviewable net check that RTN100 and RTN101 are not shorted by any net in the review set; verify each residual channel’s reference is tied to exactly one defined return; verify no monitor return crosses a power return in a way that lets fault current flow through a sense element. **Do not** accept a schematic net label as proof — list the actual copper nets and confirm the crossing is either intentional (documented) or eliminated. HOLD if the crossing is unresolved.

### 3.3 POR / held-button
A held START or RESET button at POR can defeat default inhibit (button holds START active through power-up) or lock the latch in reset (button holds RESET, suppressing fault capture).
**Required:** at POR the logic must resolve to **INHIBIT regardless of button state**; START must require a *fresh* edge after POR (release-then-press), not a level. RESET must not be able to mask a set event that occurs during reset; set-priority (F2) must win. Net/pin check: confirm button is edge-detect (or RC+Schmitt) and that the POR window dominates the button node.

### 3.4 Fault vs reset
A single button or single line that both resets the latch and clears the fault indication conflates “operator acknowledged” with “fault physically gone.”
**Required:** RESET clears *latch state* only; it must not clear the *fault cause* indication until the monitored condition (OVP/UV/temp/residual) is actually gone and re-validated. If the fault persists, reclose must be blocked (see 3.5). Net check: latch set input and reset input are separate nets; reset cannot also drive the fault-validity chain.

### 3.5 Reclose
After a fault clears the latch state, the system must not auto-reclose into a still-present downstream condition.
**Required:** any reclose requires **fresh manual START** plus re-validated residual channels (F7) and temp window (F6) *after* the event. Auto-retry is not permitted in this scope; U101 thermal latch and TPS fast-delay are not used as reclose timers. Net check: latch Q output gates the enable path; no self-resetting timer or RC can re-enable.

### 3.6 Common-reference failure
If OVP comparator, UV/POR, and residual channels share one reference, a reference failure can make all channels read “healthy” simultaneously.
**Required:** the reference used by the safety comparators must be **independent** of the reference used by the residual channels, or a reference-failure detector must force INHIBIT. Common single reference for *all* protection functions is not acceptable in this scope. Net check: enumerate reference nets; confirm no single reference net is the sole authority for both OVP and residual-validity. Candidate REF3425IDBVR is a **scope candidate only**; its pinout/behavior is UNKNOWN here and must be independently verified.

### 3.7 Feedback open
An open feedback divider (OVP divider or loop feedback) removes the sensed voltage while the power stage continues.
**Required:** open divider → comparator input must go to the **inhibit** state, not to “below threshold = healthy.” Add a defined pull so that an open divider produces an over-threshold or explicitly invalid reading. Net check: divider bottom leg open → confirm comparator output direction is fault-side; confirm no floating comparator input can sit in the “OK” window.

### 3.8 Ground open
An open ground in a monitor channel floats its reference, potentially reading zero differential and appearing healthy.
**Required:** each residual/OVP channel must have a defined behavior on loss of its local ground (fault-side, not clear-side), or a ground-continuity check must force INHIBIT. Net check: verify each monitor ground is a single defined net with a reviewable return path; confirm no channel can report “healthy” with its ground open.

---

## 4. Reviewable net/pin checks (to complete against verified pinouts)

These are **checks**, not a netlist. Pin numbers are intentionally omitted as UNKNOWN.

**OVP (F1)**
- [ ] Divider top/bottom values and tolerance documented; threshold with hysteresis stated.
- [ ] Comparator input common-mode range covers 0…fault level.
- [ ] Output polarity: over-voltage → fault assert; open divider → fault assert (3.7).
- [ ] Hysteresis prevents chatter at threshold.
- [ ] Reference net independent of residual reference (3.6).

**Fault latch (F2)**
- [ ] Set input dominates reset (set-priority) proven by gate-level truth, not by MCU.
- [ ] Latch state survives loss of POR domain as **fault**, not clear.
- [ ] Reset is manual and cannot re-enable without fresh START (3.4, 3.5).

**Default inhibit (F3)**
- [ ] Enable path default state at power-up is INHIBIT (pull direction documented).
- [ ] Held button at POR cannot produce START (3.3).

**Manual START/RESET (F4)**
- [ ] Two distinct physical controls; START edge-triggered post-POR; RESET separate net.

**UV/POR (F5)**
- [ ] UV threshold and POR window stated; POR dominates button (3.3).
- [ ] UV and OVP do not share a single failure point that yields “healthy.”

**Temp window (F6)**
- [ ] Open sensor → INHIBIT; shorted sensor → INHIBIT; only in-window → permitted.
- [ ] Window detector independent of MCU.

**Residual channels (F7)**
- [ ] Channel A and Channel B independent sense elements and independent references.
- [ ] Each channel has a **validity** output; invalid → HOLD, not “zero = OK.”
- [ ] No single net can force both channels “valid” (3.6, 3.8).

**Bleeds (F8)**
- [ ] Two independent bleed paths; each rated for the fault voltage/energy in scope.
- [ ] Loss of one bleed does not leave the node above the derate HOLD level (ECQE 187.5 V @105 °C < 195 V fault).

**Load interfaces (F9)**
- [ ] Gate/enable has defined pull to OFF; no float; no MCU gate.
- [ ] STP9NK50Z 7.2 V-drive margin remains **UNKNOWN** → HOLD; interface must not assume 10 V RDS spec.

---

## 5. ERC meaning (KiCad 10.0.8)

- ERC clean ≠ functional safety. ERC checks connectivity/electrical-rule classes, **not** set-priority, POR dominance, open-divider direction, ground-open behavior, or reference independence.
- **ERC errors that remain meaningful here:** unconnected enable/input pins that are supposed to default-inhibit; power-input pins with no driver; conflicting output drivers on a latch net; missing no-connect on unused comparator channels (must still be tied to a defined state, not left floating).
- **ERC warnings that must NOT be waived without review:** “input not driven” on any monitor input (could float to “healthy”), “power output not driven,” and any single-net reference shared across protection functions.
- Do **not** interpret a clean ERC as clearance of any H01–H10 or 24V07–10 HOLD. Do **not** present ERC as DRC or PCB evidence.

---

## 6. Common-reference / independence verdict

A design in which OVP, UV/POR, temp window, and both residual channels share one reference (or one comparator package supply with no reference-failure detection) does **not** meet F1/F5/F6/F7 independence as scoped. Either separate references with cross-check, or a reference-failure detector that forces INHIBIT, is required. This is a **scope convergence criterion**, not a release.

---

## 7. Explicit UNKNOWNs (must not be filled by assumption)

- Pinouts of TLV1704IPWR, REF3425IDBVR, SN74HC279DR, SN74HCS74DR, LM5164DDAR, TPS7A1650DGNR, VO617A-3X017T — **UNKNOWN**.
- Maximum propagation delays for comparator, latch, Schmitt, isolator — **UNKNOWN**; typical-only values (250 ns, 10 µs SHDN-FLT) are **not** bounds.
- Hot inductance of MSS1583-154KED — **UNKNOWN**.
- STP9NK50Z behavior at 7.2 V gate drive — **UNKNOWN**.
- US1G SOA / true Qrr — **UNKNOWN** (intrinsic model anomaly).
- ECQE2106JF 105 °C margin vs 195 V fault — **fails derate as stated**; HOLD retained.

---

## 8. Result

- R4 scope review is **converged in structure**: independent OVP/ref/comparator, set-priority latch, default inhibit, manual START/RESET, UV/POR, temp open/short window, two independent residual channels with validity HOLD, dual bleeds, and controlled load interfaces are each assigned a physical, MCU-free function with explicit failure-mode handling for unpowered open-drain, RTN100/101 crossing, POR/held-button, fault-vs-reset, reclose, common-reference failure, feedback open, and ground open.
- **Not converged to release:** bound-set items (downstream C inrush, hot L, 7.2 V drive, US1G SOA, 105 °C cap derate) and all part pinout/tpd UNKNOWNs remain open.
- **All H01–H10 and 24V07–10 remain HOLD.** R4 is not a safety release; no manufacturing, purchase, or physical experiment is authorized by this review. Principal must independently verify every source and pinout before any net is committed to the installed KiCad 10.0.8 project.