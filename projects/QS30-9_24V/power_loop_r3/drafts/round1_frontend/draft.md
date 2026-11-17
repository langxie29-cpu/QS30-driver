# QS30 Power-Loop R3 — Frontend Independent Calculation Draft (Round 1)

**Status: STUDY ONLY. Not a protection proof. No manufacturing approval. No executable simulation performed.** Guaranteed vs typical values are separated below; wherever the datasheet gives only TYP, the calculation carries a flag.

---

## 1. Assumed constants and provenance flags

| Symbol | Value | Type | Source flag |
|---|---|---|---|
| VIN | 24 V nominal (step external) | condition | principal |
| I_LIM8k (full −40..125 °C) | 1.425 / 1.5 / 1.575 A | **guaranteed table** (VIN24, 1 V/5 V drop) | **resistor tolerance additional** → real min lower, max higher |
| I_OCP_margin | ±? | unknown | **not bounded** — rejection criterion |
| I_chg | 4.0 / 4.7 / 5.5 µA | min/typ/max | CDVdT gain 23.75/24.6/25.5 |
| CdVdT | 47 nF, −10 % → 42.3 nF | nominal pending **exact MPN** | tolerance of real part unknown |
| RON | 80–250 mΩ | full range | IOL = (VIN−VOUT)/RON when RON-limited |
| I_FT | 1.87·IOL + 0.015 A | **TYP only** | no guaranteed max → cannot be used as protection limit |
| t_FT_delay | 250 ns | **TYP only** | no max |
| t_FLT | 10 µs | TYP | SHDN entry → FLT |
| t_REV | 1.5 µs | TYP | reverse cutoff |
| T_thermal | 157 °C | TYP | |
| RθJA | 30.2 °C/W | JEDEC board, **not pulse SOA** | **cannot be used for short-event SOA** |
| L | 150 µH −10 % → 135 µH | min used | hot L(I,T) **unknown** |
| I_sat(−10..−30 %) | 3.1 / 3.6 / 3.9 A | cold | hot derating **unbounded** |
| COUT | 20.3 µF nom, 24.36 µF max | exploratory | |
| CIN downstream | 1 µF candidate vs 47 µF | comparison | |
| R2 fast | 26.4 V passive | IL 9.557 A linear | passive path **not a limiter** |
| R2 precharge | 33 Ω | cannot supply 6 W continuous | |
| Upstream U100 | ~1 A (12 kΩ) | coordination | |
| Upstream U101 | ~0.6 A (20 kΩ) | coordination | |
| F100 | 1 A fuse | coordination | |

---

## 2. Controlled passive current (B-current, STUDY model)

The proposed behavioral series pass is

I_B = min( I_lim, (VIN−VOUT)/R_ON, servo(V_target−VOUT) ), clamped ≥ 0.

### 2.1 Current-limit branch I_lim

Using the datasheet **table** (guaranteed) but with **unbounded resistor tolerance**:

- Nominal target: I_lim,typ = 1.575 A at VB(1 V drop). 1.5 A is the middle row; 1.425 A is the min.
- **Guaranteed lower bound** (table only, ignoring resistor tol): 1.425 A.
- **Guaranteed upper bound**: **unknown** — table max is 1.575 A but resistor tolerance is additive and not quantified in the received evidence. → flag.

The proposal states “min(current limit 1.591 A)”. **This conflicts with the received table.** 1.591 A sits *above* the table max 1.575 A and is not derivable from the table as stated. That number is rejected inside this study unless the principal supplies the exact resistor/MODE network math. See §7, flaw F1.

### 2.2 RON branch

I_RON = (VIN − VOUT)/R_ON, R_ON ∈ [80 mΩ, 250 mΩ] (full range).

- R_ON path is *not* a current limit; it is a passive impedance. At a bolted output short (VOUT→0), I_RON = 24/0.08 = **300 A** (upper), 24/0.25 = **96 A** (lower) *if the part were linear and persistent*. The TPS2660 is not; the R_ON figure is for normal operation, **not short-circuit impedance**. → reject any calculation that uses 250 mΩ as short-circuit current limiting (F2).

### 2.3 Servo branch

Servo = gain·(V_target − VOUT). No finite gain or saturation bound given → **cannot bound servo overshoot** (F3). Behavioral model only; not real silicon.

### 2.4 Effective I_B conclusion

I_B in the study is **favorable instantaneous regulation**, not a conservative protection limit. TPS2660 fast-trip is 1.87·IOL+0.015 A **TYP**, delay 250 ns **TYP**, and there is **no guaranteed max**. Therefore the *study* I_B curve cannot be used to prove the real device limits fault current. That is exactly the principal's warning: **need separate unbounded fault calculation** (§4, §5).

---

## 3. Startup: from V_OUT = 0 V, C_OUT and INTVCC

### 3.1 Controlled passive current ceiling

At startup V_OUT=0:
- R_ON branch would demand ⇒ clamp by I_lim.
- So I_start ≈ I_lim (table 1.425–1.575 A) **modified by upstream 1 A limit**.

### 3.2 Upstream 1 A limitation (U100 ~1 A, U101 ~0.6 A, F100 1 A)

If upstream source cannot deliver I_lim, the branch never reaches its setpoint:
- Effective charge current ≤ upstream limit; if I_up,lim < I_B, the TPS2660 output voltage collapses and the part sits in its own current-limit region for longer, **increasing** dissipation time.
- Coordination check: I_lim,max(1.575 A) > I_up,U100(1 A) > I_up,U101(0.6 A). A **1.5 A branch limit cannot be enforced behind a 1 A source** — the upstream converter will either current-limit (soft) or latch/trip. That changes the dominant loss location from the TPS2660 to the upstream U100. → real requirement: document which upstream converter is the actual limiter during start and fault.

### 3.3 dV/dt charge estimate

INTERNAL CdVdT path: I_chg = 4.0/4.7/5.5 µA into CdVdT (42.3 nF min), gain 23.75/24.6/25.5.

- Nominal: I_chg·gain = 4.7 µA·24.6 ≈ **115.6 µA** equivalent.
- Worst-low: 4.0 µA·23.75 ≈ **95.0 µA**.
- Worst-high: 5.5 µA·25.5 ≈ **140.3 µA**.

Charge time from 0 to V_target:
t_charge = C_OUT·V_target / I_eff.

- Nominal: 20.3 µF·V_target / 115.6 µA ≈ 175.6 ms·(V_target/1 V). At V_target = 19 V (permit): **≈ 3.34 s**.
- Worst-low: 20.3·V_target/95.0e-6 ≈ 213.7 ms/V ⇒ at 19 V ≈ **4.06 s**.
- Worst-high (fastest): 20.3·V_target/140.3e-6 ≈ 144.7 ms/V ⇒ ≈ **2.75 s**.

C_OUT max 24.36 µF increases these by 24.36/20.3 ≈ **1.20×**: worst-low ⇒ **≈ 4.87 s** to 19 V.

**Guaranteed?** No — I_chg and gain have individual min/max, but whether min·min and max·max can co-occur is not guaranteed. Treat the range as *plausible envelope*, not guaranteed. CdVdT tolerance of the actual MPN unknown → F4.

### 3.4 INTVCC load

INTVCC powers internal LDO gate drive. If downstream LT3757A is powered from the switched branch instead of AUX12, INTVCC current depends on the unchanged MOS gate charge and switching frequency. **Not quantified** → the CdVdT charge budget must reserve headroom for gate drive; that reserve is currently unbounded (F5).

### 3.5 Energy stored in capacitors during controlled ramp (CIN + COUT)

E_C = ½·C·V_target².

- COUT (20.3 µF, 19 V): ½·20.3e-6·361 ≈ **3.66 mJ**. Max C 24.36 µF ⇒ ≈ 4.40 mJ.
- Downstream CIN 1 µF: ½·1e-6·361 ≈ **0.18 mJ**.

Total controlled capacitive energy at 19 V: COUT(1 µF CIN case) ≈ **3.84 mJ**; with 47 µF CIN: ½·47e-6·361 ≈ 8.48 mJ ⇒ total ≈ **12.1 mJ**. The 47 µF CIN choice nearly triples startup charge energy and lengthens the ramp by the same ratio as C addition (equations above scale with total C).

**Flaw:** the “capacitive charge energy including CIN” is small in joules, but the *time* at I_lim is what drives die temperature. Both must be assessed; the study only quotes energy.

---

## 4. Short-circuit / unbounded fault case (passive only)

### 4.1 Immediate bolted short

- OUT to RTN bolted: TPS2660 fast-trip path is the only near-term cut. I_FT = 1.87·IOL+0.015 A **TYP**, delay 250 ns **TYP**.
- Assume IOL = 1.5 A (mid table): I_FT,typ ≈ 1.87·1.5+0.015 = **2.82 A**.
- But with upstream 1 A, **I_FT is never reached** on the 1 A branch; upstream limits. Conversely if the branch is behind a stiff source, a real bolted short drives I toward 1.87·IOL+... — again TYP, not guaranteed.
- Stored energy in L at fault: ½·L·I², L=135 µH min, I = I_trip.
  - I = 1.5 A ⇒ ½·135e-6·2.25 ≈ **152 µJ**.
  - I = 2.82 A (fast-trip typ) ⇒ ½·135e-6·7.95 ≈ **537 µJ**.
  - Hot L derating unknown → these are **lower-bound-ish** only if L hot ≥ 135 µH; hot 10–30 % loss could reduce L to ≈ 95–108 µH, reducing stored energy but raising di/dt.

**No guaranteed max current or delay → short-circuit energy and peak power cannot be bounded from the received evidence.** Reject any claim that the study branch bounds a bolted fault.

### 4.2 R2 26.4 V passive branch, IL 9.557 A linear

- If the R2 branch is the fast-path, its passive linear resistance was computed for I = 9.557 A at the 26.4 V point. That is a **passive current, not a limit**; with a bolted short the current is set by source and wiring, and R2 dissipates I²R. The 33 Ω precharge cannot supply 6 W continuously — the precharge path is a **startup-only** element, not a fault limiter. → F6: any fault-current calculation that relies on R2 precharge to hold the output is rejected.

### 4.3 Max short power / energy vs delay

P_short ≈ V_IN·I_trip or I²·R_ON, whichever the scenario dictates. With the TYP values:

- P_peak(TPS2660 die during fast-trip window) not given in evidence; RθJA 30.2 °C/W is JEDEC-board static, **not pulse SOA**. Cannot compute pulse temperature rise. → F7.
- Window energy W = P·t: with t = 250 ns TYP, W is numerically small, but since neither P nor t is guaranteed, the result is **not a proof** and cannot be used for rejection of the real device.

---

## 5. Downstream stored barrier (C_OUT as bypass)

If a fault occurs downstream, C_OUT discharges into the fault while the upstream branch may re-charge. Worst-case stack:
- C_OUT max 24.36 µF at 26.4 V (fast-branch clamp) stores ½·24.36e-6·697 ≈ **8.49 mJ**.
- The 47 µF CIN candidate adds ≈ 16.3 mJ at 26.4 V (½·47e-6·697). This is the dominant stored energy. The study proposal with CIN = 47 µF therefore **increases** downstream fault energy by ~2× over the 1 µF case.
- Inductor 135 µH at hot L adds bounded energy only if hot L is bounded; **not bounded here**.

Stored downstream capacitor is a passive energy reservoir; the TPS2660 reverse cutoff (1.5 µs **TYP**) and fast-trip (250 ns **TYP**) are the only events that stop recharge. Both TYP only ⇒ not a guaranteed barrier.

---

## 6. “Hot L delay ceiling”

Loss of inductance hot (10/20/30 % → 95–135 µH) raises di/dt = (VIN−VOUT)/L during fast transients and shortens L charge time:
- di/dt at 24 V, L=135 µH: ≈ 177.8 A/ms.
- At L=95 µH: ≈ 252.6 A/ms.
- Time to reach 1.5 A: 1.5/(177.8) ≈ 8.4 µs (min L), vs ≈ 5.94 µs (30 % loss). So the **hot L delay ceiling** for reaching the level at which the fast-trip path might act is on the order of **6–8 µs**, far longer than the 250 ns TYP fast-trip delay — but since fast-trip delay is TYP and hot L(I,T) is unknown, no ceiling can be proven. → F8.

---

## 7. Flaw list (rejection criteria for this draft's own numbers)

| ID | Flaw | Consequence |
|---|---|---|
| F1 | Proposed 1.591 A min current limit **not derivable** from received 1.425/1.5/1.575 A table | Any calc keyed to 1.591 A min is **rejected** until principal supplies MODE/RILIM math |
| F2 | R_ON 80–250 mΩ is normal-operation impedance, not short impedance | Any short-current calc using R_ON as limiter is rejected |
| F3 | Servo gain/saturation unbounded | Servo branch cannot bound overshoot |
| F4 | CdVdT 47 nF exact MPN pending; tolerance unknown | All ramp-time numbers are *plausible envelope*, not guaranteed |
| F5 | INTVCC gate-drive budget not quantified (LT3757A on switched branch, unchanged MOS) | Startup headroom unproven; could starve CdVdT gain |
| F6 | R2 26.4 V/9.557 A is passive; 33 Ω precharge cannot hold 6 W | Can't use R2/precharge as fault limiter |
| F7 | RθJA 30.2 °C/W JEDEC static, **not pulse SOA** | Short-event die heating uncomputable |
| F8 | Hot L(I,T) unknown; fast-trip threshold/delay/FLT/reverse/thermal all **TYP only** | No guaranteed protection bound anywhere |
| F9 | Upstream 1 A / 0.6 A / F100 1 A vs branch 1.5 A | Dominant limiter may migrate upstream during fault; coordination not proven |
| F10 | “Favorable instantaneous current regulation” model is **behavioral** and no native vendor frontend exists (PSpice/TINA encrypted) | Study cannot claim silicon-equivalence |

**Rejection rule:** any result in this draft that depends on I_FT, t_FT, t_REV, t_FLT, thermal 157 °C, or hot L is flagged **typical-only** and may not be used as a pass/fail margin against a guaranteed spec.

---

## 8. Real implementation requirements (not approvals)

1. Provide **exact CdVdT MPN + tolerance** and exact MODE/ILIM resistor network math, so the 1.425–1.575 A table can be mapped to the actual setpoint. 1.591 A must be re-derived or withdrawn.
2. Provide **guaranteed max** (or vendor statement that none exists) for fast-trip threshold, fast-trip delay, reverse cutoff, and FLT timing; otherwise design must assume worst-case unbounded and add an **external independent limiter** (e.g., upstream converter with guaranteed current limit, fuse coordination, or series eFuse) outside this study.
3. Reconcile branch limit (target 1.5 A) with upstream U100 1 A / U101 0.6 A / F100 1 A. If branch > upstream, document that upstream is the actual fault limiter and characterize its fault energy.
4. Quantify INTVCC load with LT3757A powered from switched branch (gate charge × fsw × margin). Reserve before trusting CdVdT ramp.
5. Obtain **pulse SOA or short-circuit energy rating** (not RθJA) for TPS2660 QFN, or add external energy clamp.
6. Decide CIN = 1 µF vs 47 µF **before** final energy/thermal calc; 47 µF roughly doubles downstream stored fault energy and triples/lengthens the ramp accordingly.
7. Establish **hot L(I,T)** and hot saturation current for the 150 µH part; cold-only 3.1–3.9 A is insufficient.
8. Document RTN-vs-system-GND isolation and reverse behavior for SHDN/FLT/IMON relative to **own RTN**; any monitor connection to system GND is a reverse-bias hazard.
9. R2 33 Ω precharge: confirm it is disconnected or bypassed after startup; it cannot be in the 6 W path.
10. PWM off until switched input ≥ 19 V: the “permission” claim is **unqualified** in the received evidence — no UVLO/permit guaranteed timing was supplied. Add a guaranteed UVLO threshold/hysteresis spec or external supervisor.

---

## 9. Bounded conclusions (no PASS)

- Startup charge from 0 V to 19 V: **≈ 2.8 s (fast envelope) to ≈ 4.9 s (slow envelope, C_OUT max)**; these are **plausible, not guaranteed**.
- Controlled capacitive energy at 19 V: **≈ 3.7–4.4 mJ (C_OUT) + 0.18 mJ (1 µF CIN)** or **+ 8.5 mJ (47 µF CIN)**.
- Inductor stored energy at 1.5 A, 135 µH: **≈ 152 µJ** nominal-ish, but hot L unknown.
- Bolted fault: **cannot be bounded** with TYP-only fast-trip data; max power/energy vs delay is **undefined within received evidence**.
- Upstream 1 A limit will likely dominate over the 1.5 A branch setpoint during fault and start — **coordination unproven**.
- No result in this draft constitutes protection-duration or SOA evidence.

**Verdict of this bounded review: STUDY inputs are partially consistent but contain F1 (1.591 A unsupported) and F2/F8/F9/F10 blocking flaws for any protection claim. Round 2 must supply exact resistor math, guaranteed maxima or explicit “no max” statements, pulse SOA, CdVdT MPN, and hot-L data before any calculation can be promoted beyond exploratory envelope.**