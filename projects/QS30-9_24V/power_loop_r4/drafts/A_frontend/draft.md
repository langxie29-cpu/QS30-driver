## R4 engineering convergence review — no safety release

**Scope:** Conceptual review only. No new sources, measurements, tool access, or physical validation claimed. Frozen R3 98b6f819 retained as the configuration baseline; this is development-route convergence, not qualification.

---

### 1. Governing limits carried forward

- **Downstream capacitance fault energy is the dominant unresolved constraint.** With U101 behind 1 µF/47 µF sources, R3 computed IL3.578762 A / 14.171475 A paths and a 1.591 A instantaneous pass limit. **A series pass element cannot bound downstream capacitor charging at the instant of a fault if the pass element is not itself the limiter** — charge flows from bulk C through the pass element and any bypass immediately.
- TPS26601 fast-trip/delay timings are **not guaranteed maxima**; 250 ns and 10 µs SHDN–FLT are typical/illustrative only. **No invented delay maxima.**
- US1G: intrinsic model anomaly; **SOA UNKNOWN**; 112 nC is not a guaranteed Qrr. Port-negative charge handling UNKNOWN.
- STP9NK50Z: RDS(max) specified at 10 V, operation at 7.2 V gate drive → **effective RDS(max) UNKNOWN**; model is 25 °C.
- ECQE2106JF: at 105 °C, derated rating ≈187.5 V < 195 V fault → **margin insufficient**; remains flagged.
- MSS1583 hot L UNKNOWN; DCRmax 0.159 Ω only at 25 °C model.
- All H01–H10 and 24V07–10 findings remain open. No physical experiments, purchases, or manufacturing.

---

### 2. Option A — TPS26601RHFR (U100/U101) re-configuration

**Proposed change:** U100 ILIM 12 kΩ (~1 A clamp), fuse 1 A; U101 20 kΩ→8 kΩ (active current limit) and MODE open→402 kΩ (thermal latch / circuit-breaker mode).

**What the proposal actually buys:**
- 8 kΩ on U101 lowers its active current limit below the 20 kΩ setting; with MODE set for latch, overcurrent trips to a latched off state rather than a timed retry. That converts U101 from "timed overcurrent" to "bounded active limit then thermal latch."
- 402 kΩ is a configuration resistor; its exact MODE decode must be read from the datasheet table — **value-to-mode mapping UNKNOWN pending verification** (see §7).

**What it does not buy:**
- It does not bound the **instantaneous** current into downstream C at fault. Fast-trip is not guaranteed; the 1.591 A pass limit is downstream of the bulk that supplies the fault. **Active limit with a finite response time cannot make a hard guarantee about peak capacitor charging current.**
- Thermal latch is a *protection* behavior, not an energy bound. The energy delivered during the latch delay is set by bulk C, loop inductance, and the FET/controller response — none of which are guaranteed maxima.
- U100 1 A fuse + ~1 A limit gives no margin between limit and fuse; fuse I²t vs. controller limit-foldback behavior is UNKNOWN.

**Verdict A:** Improves *post-fault* state (latched) and adds a second current clamp, but **does not close the downstream-C/peak-current gap** and retains deliberate 1 µF/47 µF behind the final branch cut. Defensible only as a supervisory layer, not as the branch-cut authority.

---

### 3. Option B — Independent precharge + bypass

**Concept:** Separate precharge path brings downstream bulk up slowly under a bounded current; bypass (e.g., relay/FET) closes only after precharge completes, so the main pass element never sees the inrush.

**Strengths:**
- Directly attacks the root problem: **inrush energy is bounded by the precharge resistor/current source, not by a fast-trip guarantee.** Precharge current can be set by a passive resistor whose tolerance and power rating are deterministic.
- Bypass closure can be sequenced on a measured downstream voltage, giving a defined handoff instead of relying on an unguaranteed trip time.
- Compatible with moving controller VIN bypass upstream of the final branch cut (§6).

**Weaknesses / missing:**
- Precharge path itself must survive a **downstream short during precharge** — the precharge element becomes the limiter and its SOA/power is the new binding constraint. **UNKNOWN** until precharge element chosen and its fault energy computed.
- Bypass contact/FET must not weld or hot-switch into a fault; bypass-closed-into-short is a new single fault. Sequence/ interlock UNKNOWN.
- Adds parts and a state machine failure surface; retrigger policy must be defined (§5).

**Verdict B:** The only option that **structurally** bounds downstream-C charging energy with deterministic passive elements. Residual gaps are the precharge element's fault SOA and bypass interlock — both addressable and verifiable.

---

### 4. Option C — LM5069-1 + external FET (single bounded alternative)

**Guaranteed/typical values as supplied (to be independently verified):**

| Parameter | Value | Type |
|---|---|---|
| Current-limit threshold | 48.5–61.5 mV | min/max (guaranteed span) |
| Circuit-breaker threshold | 80–130 mV | min/max |
| Breaker→GATE low, no-load, <150 mV step | **max 1.2 µs** | guaranteed max |
| Current regulation response | 45 µs | **TYP** |
| FAULT/TIMER threshold | 3.76–4.16 V | min/max |
| TIMER current | 51–120 µA | min/max |
| TIMER→GATE | 12 µs | **TYP** |

**What this gives that A lacks:**
- A **guaranteed 1.2 µs maximum** breaker-to-GATE-low under a defined <150 mV step — the first hard timing bound in the chain. This is the only guaranteed turn-off max among the options.
- Guaranteed threshold spans let you compute worst-case limit window and breaker window.
- External FET choice is free, so RDS(on)/SOA can be selected for the actual 7.2 V-class drive and hot conditions.

**What remains missing under gate charge / SOA:**
- **1.2 µs is no-load.** With real gate charge, breaker-to-GATE-low extends by Qg/Igate. Gate drive current, Qg at the operating point, and the resulting worst-case turn-off are **UNKNOWN** — must be computed, not assumed. Do not invent a max.
- **45 µs current regulation is TYP.** No guaranteed max → the energy absorbed while the FET is in linear regulation is **not bounded by a datasheet guarantee**. This is the critical SOA gap: the FET sees current-limited operation for an unbounded-by-spec interval.
- **TIMER→GATE 12 µs TYP.** No guaranteed max. Worst-case fault energy during TIMER expiry is **UNKNOWN**.
- FET SOA at the actual VDS (post-branch-cut, downstream C discharged) and the actual pulse width is **UNKNOWN** until a specific FET with a hot SOA curve is selected and the pulse computed from guaranteed + computed (not typical) times.
- Breaker threshold 80–130 mV spread = ~1.6:1 limit window; sense resistor tolerance and Kelvin layout add to it. Worst-case I_limit vs. I_breaker separation must be verified to ensure regulation (not breaker) engages first at intended currents.

**Verdict C:** Best *timing* guarantee (1.2 µs breaker max) and best flexibility, but the **current-regulation and TIMER paths are TYP only**, so linear-mode SOA energy is not fully bounded by spec. Viable if the FET is chosen with adequate SOA margin against a computed worst-case pulse using guaranteed breaker time + *computed* (not assumed) regulation/timer uncertainty, and if the regulation phase is short by design.

---

### 5. Energy partition and single-fault review

**Energy partition (fault event, downstream short):**
1. **Bulk C discharge into fault** — through pass element + any bypass. Governed by C, ESR/ESL, loop L; this is the term A fails to bound and B/C bound only by element response.
2. **Source-to-fault through pass element** — bounded by current limit × response time; guaranteed only for LM5069 breaker (1.2 µs max), TYP elsewhere.
3. **Pass-element linear-mode dissipation** — integral of VDS×I during limit/regulation; **unbounded by spec for TPS and for LM5069 regulation/TIMER (TYP)**.
4. **Precharge element dissipation** (Option B) during precharge-into-fault — deterministic if passive.
5. **Downstream damping resistor** (if adopted, §7) — dissipates a bounded share of (1), deliberately.

**Single faults to enumerate (all remain open):**
- Pass FET short (D-S) → bulk connects directly to downstream; only fuse/upstream protection remains. **UNKNOWN** whether 1 A fuse clears before downstream damage.
- Controller stuck-on / GATE stuck high → same as above.
- Bypass welded closed (B) → precharge protection bypassed.
- Sense resistor open/shifted → limit miscalibrated; **UNKNOWN** failure mode.
- TIMER capacitor open/shorted → premature or never trip.
- Gate drive open → FET off (safe-ish) or linear (unknown).
- US1G port-negative event → SOA **UNKNOWN**; do not credit.

**No single-fault closure is claimed.** Every path above terminates in UNKNOWN until measured or datasheet-verified.

---

### 6. Moving controller VIN bypass upstream of the final branch cut

**Proposed:** Relocate the controller's own VIN bypass (currently 1 µF/47 µF region) upstream of the final branch cut, so no *deliberate* bulk sits behind the cut.

**Assessment:**
- Correct in principle: it removes deliberate 1 µF/47 µF from the downstream-C fault term, reducing the instantaneous pass current that R3 computed as 3.578762/14.171475 A (those values were tied to the behind-cut bulk).
- **Do not call parasitic storage zero.** PCB trace inductance/capacitance, FET Coss/Coss(er), controller pin capacitance, and any unlisted decoupling still store and deliver charge. The post-move fault current is **reduced but not zero and not yet quantified**. Must be bounded by layout extraction or measurement — **UNKNOWN** now.
- Moving bypass upstream puts it on the source side of the pass element, so its discharge is limited by the pass element's current limit — which is the desired topology. Confirm the controller still meets its own VIN transient/decoupling needs with the longer feed; **UNKNOWN** until checked.
- This change is **compatible with B and C**, and should be adopted in all routes as a topology improvement — but it is not, by itself, an energy bound.

---

### 7. Permanent finite 12.4 Ω downstream-of-all-bulk damping resistor — research option

**Proposed:** A permanent 12.4 Ω resistor downstream of all bulk, explicitly inefficient, as a bounded research option. Not 33 Ω. Not prequalified.

**Capability at 21.6 V:**
- P = V²/R = 21.6²/12.4 ≈ **37.6 W continuous** if 21.6 V is sustained across it. A 6 W part cannot carry that continuously.
- 6 W capability implies max continuous V = √(6×12.4) ≈ **8.6 V** across the resistor, or a duty/derating scheme. At 21.6 V sustained, **6 W is insufficient by ~6×** → the resistor must be rated for the actual worst-case continuous voltage or be provably not exposed to it. This is a **hard gap**, not a tolerance issue.
- Heat: 37.6 W in a small resistor → junction/case rise **UNKNOWN** without a thermal model; enclosure ambient and derating **UNKNOWN**. Efficiency loss is deliberate but must be quantified against the energy it removes from the fault term.

**Damping value physics:**
- 12.4 Ω is a *damping* choice; its effectiveness depends on the loop's characteristic impedance √(L/C) and ESR. If 12.4 Ω ≫ √(L/C), it dominates and heavily limits normal load current/voltage droop — **UNKNOWN** whether the load tolerates it. If ≪, it barely damps.
- It bounds fault current to ≈ V/12.4 (e.g., 21.6/12.4 ≈ 1.74 A at 21.6 V) — a *passive, deterministic* bound independent of controller timing. That is its engineering appeal: **it is the only element here whose fault current bound does not depend on an unguaranteed trip time.**
- But it dissipates continuously and must survive the fault itself (fault energy into 12.4 Ω = bounded, but the resistor's pulse/continuous rating and hot resistance drift are **UNKNOWN**).

**Verdict:** Interesting as an *explicitly inefficient* deterministic clamp, but **6 W at 21.6 V is not defensible** — it is under-rated for sustained 21.6 V by roughly 6×, and thermal/derating/damping-ratio data are missing. Keep as **research option only; not prequalified; not a release path.** If pursued, first verify: actual worst-case continuous voltage across it, √(L/C) of the loop, hot resistance, pulse rating, and enclosure thermal rise.

---

### 8. Retrigger policy (all options)

Recommend for development convergence:
- **Latch on overcurrent/breaker** (no auto-retry) for the branch-cut authority; require an explicit supervisory reset. Auto-retry into a persistent short repeatedly dumps bulk-C energy and stresses SOA.
- **Bounded retry count** only if a defined cool-down and a verified downstream-voltage check precede re-enable. Retry interval and count must be **specified**, not left to TYP timers.
- **Precharge (B):** no bypass closure unless downstream voltage reaches a verified threshold within a bounded time; on timeout, latch and do not close bypass.
- **Distinguish** breaker trip (latch) from transient limit (allow recovery only after limit clears and a defined dwell). Dwell value **UNKNOWN** — to be set from measured loop behavior, not invented.

---

### 9. Exact facts to verify (independent, by principal)

**LM5069-1:**
1. Confirm 48.5–61.5 mV and 80–130 mV are min/max guaranteed (not typ).
2. Confirm 1.2 µs breaker→GATE max conditions (no-load, <150 mV step) and the gate-drive source/sink current used.
3. Confirm 45 µs regulation and 12 µs TIMER→GATE are TYP (no max) — and whether any max exists elsewhere.
4. Confirm TIMER 51–120 µA and 3.76–4.16 V min/max.
5. Gate charge Qg of selected FET at actual VGS; compute turn-off = Qg/Igate; compare to 1.2 µs no-load.
6. Selected FET hot SOA at post-cut VDS for computed worst-case pulse.

**TPS26601:**
7. MODE decode table for 402 kΩ and 8 kΩ/20 kΩ ILIM→limit mapping (min/max, not typ).
8. Any guaranteed fast-trip max (expect none) — record as UNKNOWN.
9. Fuse I²t vs. controller limit window; margin.

**Component/hot data:**
10. STP9NK50Z RDS(on) at 7.2 V and hot — measured or curve.
11. US1G Qrr/SOA under port-negative event — measured; until then UNKNOWN.
12. ECQE2106JF at 105 °C — confirm derated rating vs. 195 V fault.
13. MSS1583 hot L and saturation at fault current.
14. Parasitic storage behind the moved branch cut — layout extraction/measurement.

**Damping resistor (if pursued):**
15. √(L/C) of loop; 12.4 Ω ratio; continuous voltage across it; pulse/continuous rating; enclosure thermal rise.

---

### 10. Selection

**Insufficient evidence to release any route.** For **development convergence**, the defensible preference is:

**Primary: Option C (LM5069-1 + external FET), combined with the §6 upstream-bypass move and the §8 latch policy.**

Rationale: it is the only route with a **guaranteed maximum breaker-to-GATE time (1.2 µs)**, guaranteed threshold spans, and a free FET choice for hot SOA. Combined with moving deliberate bypass upstream, it minimizes behind-cut bulk. Its residual gaps (TYP regulation/TIMER, computed gate-charge turn-off, FET SOA) are **bounded and verifiable**, not ignored.

**Secondary/companion: Option B precharge** as the deterministic inrush bound if C's computed linear-mode SOA margin proves inadequate — B's passive precharge gives a timing-independent bound that C lacks.

**Not preferred:** Option A alone — retains behind-cut 1 µF/47 µF and depends on unguaranteed fast-trip; usable only as a supervisory latch layer, not the branch-cut authority.

**Research only, not prequalified:** 12.4 Ω damping resistor — under-rated at 21.6 V (6 W vs ~37.6 W), damping ratio and thermal data missing.

**Status:** All H01–H10 and 24V07–10 remain open. No safety/manufacturing release. No physical experiments, purchases, or manufacturing. Frozen R3 98b6f819 unchanged. Principal to verify all datasheet values independently; no invented delay maxima.